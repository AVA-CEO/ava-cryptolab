"""Disposable API/database for browser tests. Never uses the developer's journal."""

import os
import tempfile
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config

with tempfile.TemporaryDirectory(prefix="ava-browser-") as directory:
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(directory, 'tests.db').as_posix()}"
    os.environ["UPLOAD_DIR"] = str(Path(directory, "uploads"))
    os.environ["APP_ENV"] = "local"
    os.environ["ACCOUNT_MANAGEMENT_ENABLED"] = "true"
    command.upgrade(Config("alembic.ini"), "head")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001)
