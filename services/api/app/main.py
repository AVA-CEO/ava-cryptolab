from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings

# Phase 1 has no authentication: fail closed outside local development.
if get_settings().app_env != "local":
    raise RuntimeError("Public API deployment requires authentication in a later milestone.")

app = FastAPI(title="AVA CryptoLab API", version="0.1.0")
app.include_router(router, prefix="/api/v1")
