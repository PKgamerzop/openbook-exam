"""Run with python -m app.reference_worker from backend."""

import logging
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import get_engine
from app.operational import heartbeat, shutdown_event, worker_logger
from app.pdf_files import inspect_pdf, path_for
from app.store import one, rows


def process_one(version_id=None):
    engine = get_engine()
    token = uuid4()
    with engine.begin() as db:
        job = one(
            db,
            """SELECT j.version_id,v.storage_key FROM reference_job j
            JOIN reference_version v ON v.id=j.version_id
            WHERE (lease_until IS NULL OR lease_until<=now())
            AND (:all_jobs OR j.version_id=:v)
            ORDER BY j.version_id LIMIT 1 FOR UPDATE OF j SKIP LOCKED""",
            all_jobs=version_id is None,
            v=version_id or 0,
        )
        if not job:
            return False
        vid = job["version_id"]
        rows(
            db,
            """UPDATE reference_job SET token=:t,lease_until=now()+interval '90 seconds'
            WHERE version_id=:v""",
            v=vid,
            t=token,
        )
    try:
        pages = inspect_pdf(path_for(job["storage_key"]), extract=True)
        status = "searchable" if any(pages) else "view-only"
    except ValueError, OSError:
        pages = []
        status = "failed"
    with engine.begin() as db:
        if not one(
            db,
            """DELETE FROM reference_job WHERE version_id=:v AND token=:t
            RETURNING version_id""",
            v=vid,
            t=token,
        ):
            return True
        rows(db, "DELETE FROM reference_page WHERE version_id=:v", v=vid)
        if status == "searchable":
            db.execute(
                text("""INSERT INTO reference_page(version_id,page,content)
                VALUES (:v,:p,:c)"""),
                [dict(v=vid, p=i, c=c) for i, c in enumerate(pages, 1)],
            )
        rows(db, "UPDATE reference_version SET status=:s WHERE id=:v", s=status, v=vid)
    logging.getLogger("indexer").info("pdf_index_completed status=%s", status)
    return True


if __name__ == "__main__":
    logger = worker_logger("indexer")
    stopped = shutdown_event()
    while not stopped.is_set():
        try:
            processed = process_one()
            heartbeat()
            if processed:
                continue
        except SQLAlchemyError:
            logger.warning("indexer_database_unavailable")
        stopped.wait(2)
