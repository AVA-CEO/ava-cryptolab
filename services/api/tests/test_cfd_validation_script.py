"""The learning command reads files only and does not import the live app/DB."""

import json
import subprocess
import sys
from pathlib import Path

from cfd_examples import EXAMPLE_PATH, example

SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_cfd_input.py"


def invoke(path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False
    )


def test_example_validation_command_and_import_isolation():
    result = invoke(EXAMPLE_PATH)
    assert result.returncode == 0, result.stderr
    assert "No PnL calculated or records saved" in result.stdout
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.schemas.cfd import CfdTradeInput; import sys; "
            "assert not any(name in sys.modules for name in "
            "('app.database.session', 'app.main', 'MetaTrader5', 'httpx', 'sqlalchemy'))",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_invalid_command_reports_field_without_dumping_input(tmp_path):
    path = tmp_path / "bad.json"
    data = example()
    data["entry"]["lots"] = "SYNTHETIC-PRIVATE-INPUT-DO-NOT-ECHO"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = invoke(path)
    assert result.returncode == 1
    assert "entry.lots" in result.stderr
    assert "SYNTHETIC-PRIVATE-INPUT-DO-NOT-ECHO" not in result.stderr


def test_invalid_json_and_missing_file_are_errors(tmp_path):
    path = tmp_path / "invalid.json"
    assert invoke(path).returncode == 1
    path.write_text("{ invalid json }", encoding="utf-8")
    assert invoke(path).returncode == 1
