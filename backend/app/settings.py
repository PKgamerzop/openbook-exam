"""Validate deployment settings before any service handles application data."""

import os
import re
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit


def deployed() -> bool:
    mode = os.getenv("OPENBOOK_ENV", "development")
    if mode not in {"development", "staging", "production"}:
        raise ValueError("Invalid OPENBOOK_ENV")
    if mode == "development" and os.getenv("OPENBOOK_CONTAINER_DEPLOYMENT") == "1":
        raise ValueError("Deployment images require staging or production mode")
    return mode != "development"


def deployment_host() -> str:
    origin = os.getenv("OPENBOOK_ORIGIN", "")
    target = urlsplit(origin)
    host = target.hostname
    port = target.port
    canonical = f"https://{host}" + (f":{port}" if port else "")
    if (
        target.scheme != "https"
        or not host
        or target.username is not None
        or target.path
        or target.query
        or target.fragment
        or origin != canonical
    ):
        raise ValueError("OPENBOOK_ORIGIN must be a canonical HTTPS origin")
    if os.environ["OPENBOOK_ENV"] == "staging" and host != "localhost":
        raise ValueError("Staging requires localhost")
    if os.environ["OPENBOOK_ENV"] == "production":
        try:
            ip_address(host)
        except ValueError:
            if not re.fullmatch(
                r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", host
            ) or host.endswith((".local", ".localhost", ".test", ".invalid")):
                raise ValueError("Production requires a public DNS name") from None
        else:
            raise ValueError("Production requires a public DNS name")
    return host


def validate_deployment() -> None:
    if not deployed():
        return
    deployment_host()
    if os.getenv("OPENBOOK_CONTAINER_DEPLOYMENT") == "1":
        port = urlsplit(os.environ["OPENBOOK_ORIGIN"]).port or 443
        if port != int(os.environ.get("OPENBOOK_HTTPS_PORT", "8443")):
            raise ValueError("Gateway port must match the deployment origin")
        tls_directive = os.getenv("OPENBOOK_TLS_DIRECTIVE", "")
        if os.environ["OPENBOOK_ENV"] == "staging" and (
            os.getenv("OPENBOOK_BIND") != "127.0.0.1" or tls_directive != "tls internal"
        ):
            raise ValueError("Staging requires loopback and the local TLS issuer")
        if os.environ["OPENBOOK_ENV"] == "production" and (
            port != 443 or tls_directive
        ):
            raise ValueError("Production requires automatic public TLS on port 443")
    if os.getenv("OPENBOOK_LOCAL_HTTP", "0") != "0":
        raise ValueError("Deployed environments require secure cookies")
    if os.getenv("OPENBOOK_AI_PROVIDER", "disabled") != "disabled" or os.getenv(
        "OPENAI_API_KEY"
    ):
        raise ValueError("AI is disabled in deployed environments")
    for key in ("POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_DB"):
        if not os.getenv(key):
            raise ValueError(f"Missing {key}")
    password = os.getenv("POSTGRES_PASSWORD", "")
    if len(password) < 32 or password.startswith("replace-"):
        raise ValueError("Set a generated PostgreSQL password")
    if not Path(os.getenv("OPENBOOK_PDF_DIR", "")).is_absolute():
        raise ValueError("Private PDF storage requires an absolute path")
    for key, default, maximum in (
        ("POSTGRES_PORT", 5432, 65535),
        ("OPENBOOK_PDF_MAX_PAGES", 200, 200),
        ("OPENBOOK_PDF_MAX_BYTES", 20971520, 20971520),
    ):
        if not 1 <= int(os.getenv(key, str(default))) <= maximum:
            raise ValueError(f"Invalid {key}")
