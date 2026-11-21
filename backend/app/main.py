from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.db import check_database

app = FastAPI(title="OpenBook API")


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
