"""Local teaching command and dependency boundary checks."""

import json
import subprocess
import sys
from pathlib import Path

from cfd_position_examples import FIXTURE, position_example

SCRIPT = Path(__file__).parents[1] / "scripts" / "calculate_cfd_position.py"


def invoke(path, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path), *args], capture_output=True, text=True
    )


def test_command_runs_owners_example_and_preserves_units_in_json():
    result = invoke(FIXTURE)
    assert result.returncode == 0, result.stderr
    assert "gross pnl: 26.00 USD" in result.stdout
    assert "realized r: 1.300000 R" in result.stdout
    output = json.loads(invoke(FIXTURE, "--json").stdout)
    assert output["state"] == "closed" and output["native"]["net_pnl"]["rounded"] == "26.00"


def test_partial_cutoff_and_invalid_input_command(tmp_path):
    path = tmp_path / "request.json"
    data = position_example(costs=True)
    data["as_of"] = "2025-01-04T00:00:00Z"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = invoke(path)
    assert result.returncode == 0 and "net pnl: 6.50 USD" in result.stdout
    data["trade"]["entry"]["lots"] = "SYNTHETIC-PRIVATE-VALUE"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = invoke(path)
    assert result.returncode == 1
    assert "SYNTHETIC-PRIVATE-VALUE" not in result.stderr


def test_missing_or_invalid_file_is_a_clear_error(tmp_path):
    path = tmp_path / "bad.json"
    assert invoke(path).returncode == 1
    path.write_text("{broken", encoding="utf-8")
    assert invoke(path).returncode == 1


def test_position_engine_imports_no_application_database_network_or_broker():
    script = (
        "from app.analytics.cfd_positions import calculate_position; import sys; "
        "assert not any(name in sys.modules for name in "
        "('app.main','app.database.session','sqlalchemy','httpx','MetaTrader5'))"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
