"""Standalone examples and safe diagnostics; all inputs are synthetic."""

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

from cfd_calculation_examples import FIXTURES, calculation_example

SCRIPT = Path(__file__).parents[1] / "scripts" / "calculate_cfd.py"


def invoke(path, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path), *args], capture_output=True, text=True
    )


def test_eurusd_readable_and_json_results():
    path = FIXTURES / "cfd-calculation.synthetic.json"
    result = invoke(path)
    assert result.returncode == 0, result.stderr
    assert "net pnl: 6.00 USD" in result.stdout
    assert "realized r: 0.600000 R" in result.stdout
    output = json.loads(invoke(path, "--json").stdout)
    assert isinstance(output["native"]["gross_pnl"]["raw"], str)
    assert Decimal(output["native"]["gross_pnl"]["raw"]) == 10
    assert output["native"]["net_pnl"]["rounded"] == "6.00"


def test_jpy_example_keeps_native_currency_and_conversion_sources():
    result = invoke(FIXTURES / "cfd-jpy-calculation.synthetic.json", "--json")
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["native"]["currency"] == "JPY"
    assert output["reporting"]["net_pnl"]["rounded"] == "2.50"
    assert output["native"]["net_pnl"]["raw"] is None
    assert output["conversion_evidence"][0]["source"]["reference"].startswith("Synthetic")


def test_bad_input_fails_without_dumping_private_input(tmp_path):
    path = tmp_path / "bad.json"
    data = calculation_example()
    data["trade"]["entry"]["lots"] = "PRIVATE-INPUT-MUST-NOT-APPEAR"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = invoke(path)
    assert result.returncode == 1
    assert "trade.entry.lots" in result.stderr
    assert "PRIVATE-INPUT-MUST-NOT-APPEAR" not in result.stderr


def test_missing_invalid_or_non_utf8_files_return_errors(tmp_path):
    path = tmp_path / "missing.json"
    assert invoke(path).returncode == 1
    path.write_text("{broken", encoding="utf-8")
    assert invoke(path).returncode == 1
    path.write_bytes(b"\xff")
    assert invoke(path).returncode == 1
