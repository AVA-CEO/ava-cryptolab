"""Create an ephemeral account-management database; never accepts a database path."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn
from alembic import command
from alembic.config import Config

if __name__ == "__main__":
    api_root = Path(__file__).resolve().parents[1]
    with TemporaryDirectory(prefix="ava-accounts-") as directory:
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(directory, 'practice.db').as_posix()}"
        os.environ["UPLOAD_DIR"] = str(Path(directory, "uploads"))
        os.environ["APP_ENV"] = "local"
        os.environ["ACCOUNT_MANAGEMENT_ENABLED"] = "true"
        config = Config(str(api_root / "alembic.ini"))
        config.set_main_option("script_location", str(api_root / "migrations"))
        command.upgrade(config, "0003")
        print("Temporary practice workspace on 127.0.0.1:8002; records removed when stopped.")
        uvicorn.run("app.main:app", host="127.0.0.1", port=8002)
