import os
import secrets
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import store
from app.access import password_hash
from app.db import get_engine
from app.main import app


@pytest.fixture
def pilot(monkeypatch):
    if os.getenv("OPENBOOK_TEST_POSTGRES") != "1":
        pytest.skip("Set OPENBOOK_TEST_POSTGRES=1 to run isolated PostgreSQL tests")
    admin = get_engine()
    schema = "pilot_test_" + uuid4().hex
    with admin.begin() as db:
        db.execute(text(f"CREATE SCHEMA {schema}"))
    monkeypatch.setenv("PGOPTIONS", f"-c search_path={schema}")
    monkeypatch.setenv("OPENBOOK_LOCAL_HTTP", "1")
    get_engine.cache_clear()
    cfg = Config("alembic.ini")
    try:
        command.upgrade(cfg, "0001")
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "0001")
        with get_engine().begin() as db:
            assert not db.scalar(text("SELECT to_regclass('exam')"))
        command.upgrade(cfg, "head")
        password = secrets.token_urlsafe(24)
        encoded = password_hash(password)
        with get_engine().begin() as db:
            for name, role in [
                ("teacher", "lecturer"),
                ("other", "lecturer"),
                ("learner", "student"),
                ("outside", "student"),
            ]:
                db.execute(
                    text("""INSERT INTO account(username,password_hash,role)
                    VALUES (:name,:hash,:role)"""),
                    dict(name=name, hash=encoded, role=role),
                )
        clock = [datetime(2035, 1, 1, 12, tzinfo=UTC)]
        monkeypatch.setattr(store, "now", lambda: clock[0])
        yield password, clock
    finally:
        get_engine().dispose()
        get_engine.cache_clear()
        with admin.begin() as db:
            db.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        admin.dispose()


def client():
    return TestClient(app, headers={"X-OpenBook-Request": "1"})
