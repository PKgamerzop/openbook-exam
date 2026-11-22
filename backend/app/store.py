from collections.abc import AsyncIterator
from datetime import UTC, datetime

from anyio import CancelScope, CapacityLimiter, to_thread
from anyio.lowlevel import RunVar
from sqlalchemy import Connection, text

from app.db import get_engine

# Let request handlers finish and return connections while other requests wait.
checkout_slots: RunVar[CapacityLimiter] = RunVar("openbook_checkout_slots")


async def transaction() -> AsyncIterator[Connection]:
    limiter = checkout_slots.get(None)
    if limiter is None:
        limiter = CapacityLimiter(16)
        checkout_slots.set(limiter)
    context = get_engine().begin()
    db = await to_thread.run_sync(context.__enter__, limiter=limiter)
    try:
        yield db
    except BaseException as exc:
        with CancelScope(shield=True):
            await to_thread.run_sync(
                context.__exit__, type(exc), exc, exc.__traceback__
            )
        raise
    else:
        with CancelScope(shield=True):
            await to_thread.run_sync(context.__exit__, None, None, None)


def now() -> datetime:
    return datetime.now(UTC)


def rows(db, statement, **params):
    return db.execute(text(statement), params).mappings()


def one(db, statement, **params):
    return rows(db, statement, **params).first()
