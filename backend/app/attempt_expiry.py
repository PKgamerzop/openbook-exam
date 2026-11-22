"""Expire outstanding attempts in bounded batches after downtime."""

import logging
import time

from sqlalchemy.exc import SQLAlchemyError

from app import store
from app.db import get_engine
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
    while True:
        try:
            if expire_batch() == 100:
                continue
        except SQLAlchemyError:
            logging.warning("Attempt expiry temporarily unavailable")
        time.sleep(5)
