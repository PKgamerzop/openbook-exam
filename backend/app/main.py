import logging
import os
from time import monotonic

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import access, assistance, attempts, authoring, courses, references, workspace
from app.db import check_database
from app.results import router as results_router
from app.settings import deployed, deployment_host, validate_deployment

validate_deployment()
is_deployed = deployed()
app = FastAPI(
    title="OpenBook API",
    docs_url=None if is_deployed else "/docs",
    redoc_url=None if is_deployed else "/redoc",
    openapi_url=None if is_deployed else "/openapi.json",
)
if is_deployed:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[deployment_host()])
operations = logging.getLogger("uvicorn.error")
for feature in (access, courses, authoring, attempts, references, workspace):
    app.include_router(feature.router)


if not is_deployed:
    app.include_router(assistance.router)


@app.middleware("http")
async def protect_requests(request: Request, call_next):
    started = monotonic()
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and (
        request.headers.get("x-openbook-request") != "1"
        or request.headers.get("sec-fetch-site") == "cross-site"
        or (
            is_deployed
            and origin is not None
            and origin != os.environ["OPENBOOK_ORIGIN"]
        )
    ):
        response = JSONResponse(
            {"detail": "Same-origin application request required"}, 403
        )
    else:
        try:
            response = await call_next(request)
        except Exception:
            if not is_deployed:
                raise
            operations.error('{"event":"request_failed","status":500}')
            response = JSONResponse({"detail": "Service request failed"}, 500)
    elapsed = int((monotonic() - started) * 1000)
    if is_deployed and (response.status_code >= 500 or elapsed >= 1000):
        operations.warning(
            '{"event":"request_outcome","status":%d,"duration_ms":%d}',
            response.status_code,
            elapsed,
        )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(SQLAlchemyError)
async def unavailable_database(request: Request, exc: SQLAlchemyError):
    operations.warning('{"event":"database_request_failed"}')
    return JSONResponse({"detail": "Service temporarily unavailable"}, 503)


@app.get("/api/live")
def live():
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def invalid_input(request: Request, exc: RequestValidationError):
    errors = [".".join(map(str, e["loc"][1:])) + " " + e["msg"] for e in exc.errors()]
    return JSONResponse({"detail": " / ".join(errors)}, 422)


@app.get("/api/health")
def health() -> JSONResponse:
    try:
        check_database()
    except SQLAlchemyError, KeyError, ValueError:
        return JSONResponse(
            {"status": "degraded", "database": "unavailable"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return JSONResponse({"status": "ok", "database": "available"})


app.include_router(results_router)
