"""Configuration gates are independent of PostgreSQL."""

import pytest

from app import assistance
from app.settings import validate_deployment


@pytest.fixture
def staging(monkeypatch):
    for key, value in {
        "OPENBOOK_ENV": "staging",
        "OPENBOOK_ORIGIN": "https://localhost:8443",
        "OPENBOOK_LOCAL_HTTP": "0",
        "OPENBOOK_AI_PROVIDER": "disabled",
        "POSTGRES_USER": "openbook",
        "POSTGRES_DB": "openbook",
        "POSTGRES_HOST": "db",
        "POSTGRES_PASSWORD": "synthetic-test-marker-" * 2,
        "OPENBOOK_PDF_DIR": str(__file__),
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_staging_config(staging):
    validate_deployment()
    assert assistance.provider() == "disabled"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("OPENBOOK_ORIGIN", "http://localhost:8443"),
        ("OPENBOOK_ORIGIN", "https://public.example.com"),
        ("OPENBOOK_LOCAL_HTTP", "1"),
        ("OPENBOOK_AI_PROVIDER", "openai"),
        ("OPENAI_API_KEY", "synthetic-key-marker"),
        ("POSTGRES_PASSWORD", "too-short"),
        ("OPENBOOK_ENV", "invalid"),
        ("OPENBOOK_PDF_DIR", "relative"),
    ],
)
def test_staging_rejects_unsafe_config(staging, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        validate_deployment()
