"""Run from any directory. No DATABASE_URL argument; creates only synthetic data."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.database.rehearsal import run_rehearsal

if __name__ == "__main__":
    with TemporaryDirectory(prefix="ava-migration-") as root:
        result = run_rehearsal(Path(root) / "case")
        result["cleanup"] = "Temporary database, backup and screenshots removed on exit."
        print(json.dumps(result, indent=2))
