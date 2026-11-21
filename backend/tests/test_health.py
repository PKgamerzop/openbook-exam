import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app import main

client = TestClient(main.app)


def test_health_reports_available_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "check_database", lambda: None)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "available"}


def test_health_hides_database_error_details(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> None:
        raise OperationalError("SELECT 1", None, RuntimeError("connection details"))

    monkeypatch.setattr(main, "check_database", fail)

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}
