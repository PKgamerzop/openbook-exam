"""Expire outstanding attempts in bounded batches after downtime."""

from sqlalchemy.exc import SQLAlchemyError

from app import store
from app.db import get_engine
from app.operational import heartbeat, shutdown_event, worker_logger
from app.store import rows


def expire_batch():
    with get_engine().begin() as db:
        return len(
            list(
                rows(
                    db,
                    """
            WITH due AS (
                SELECT id FROM exam_attempt WHERE finalized_at IS NULL AND deadline<=:t
                ORDER BY deadline LIMIT 100 FOR UPDATE SKIP LOCKED
            )
            UPDATE exam_attempt a SET finalized_at=a.deadline, final_reason='expired'
            FROM due WHERE due.id=a.id RETURNING a.id
        """,
                    t=store.now(),
                )
            )
        )


if __name__ == "__main__":
    logger = worker_logger("expiry")
    stopped = shutdown_event()
    while not stopped.is_set():
        try:
            count = expire_batch()
            heartbeat()
            if count:
                logger.info("attempts_expired count=%d", count)
            if count == 100:
                continue
        except SQLAlchemyError:
            logger.warning("expiry_database_unavailable")
        stopped.wait(5)
