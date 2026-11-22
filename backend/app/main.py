from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app import access, attempts, authoring, courses
from app.db import check_database

app = FastAPI(title="OpenBook API")
for feature in (access, courses, authoring, attempts):
    app.include_router(feature.router)


@app.middleware("http")
async def protect_requests(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"} and (
        request.headers.get("x-openbook-request") != "1"
        or request.headers.get("sec-fetch-site") == "cross-site"
    ):
        return JSONResponse({"detail": "Same-origin application request required"}, 403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


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
