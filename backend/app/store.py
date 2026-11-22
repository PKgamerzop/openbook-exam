from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import Connection, text

from app.db import get_engine


def transaction() -> Iterator[Connection]:
    with get_engine().begin() as db:
        yield db


def now() -> datetime:
    return datetime.now(UTC)


def rows(db, statement, **params):
    return db.execute(text(statement), params).mappings()


def one(db, statement, **params):
    return rows(db, statement, **params).first()
