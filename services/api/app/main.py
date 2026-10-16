from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import StaleDataError

from app.api.journal import router as journal_router
from app.api.management import router as management_router
from app.api.routes import router
from app.core.config import get_settings
from app.core.local_security import LocalSecurityMiddleware

# Phase 1 has no authentication: fail closed outside local development.
if get_settings().app_env != "local":
    raise RuntimeError("Public API deployment requires authentication in a later milestone.")

app = FastAPI(title="AVA CryptoLab API", version="0.1.0")
app.add_middleware(LocalSecurityMiddleware)
app.include_router(router, prefix="/api/v1")
app.include_router(journal_router, prefix="/api/v1")
app.include_router(management_router, prefix="/api/v1")


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    if isinstance(exc, StaleDataError):
        return JSONResponse({"detail": "Record changed. Reload and try again."}, status_code=409)
    return JSONResponse(
        {"detail": "Database unavailable. Check migrations and try again."}, status_code=503
    )
