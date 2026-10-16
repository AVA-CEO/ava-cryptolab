"""Synthetic single-close requests, never live specifications or FX rates."""

import json
from pathlib import Path

from cfd_examples import refresh_snapshot

FIXTURES = Path(__file__).parent / "fixtures"


def calculation_example(jpy=False):
    name = "cfd-jpy-calculation.synthetic.json" if jpy else "cfd-calculation.synthetic.json"
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def set_spec(request, **changes):
    request["trade"]["snapshot"]["specification"].update(changes)
    refresh_snapshot(request["trade"])
    return request


def native_jpy_example():
    data = calculation_example(jpy=True)
    trade = data["trade"]
    trade.update(reporting_policy="native_only", conversions=[], risk_conversion_id=None)
    trade["exits"][0]["profit_conversion_id"] = None
    trade["adjustments"][0].update(amount="-100", currency="JPY")
    trade["adjustments"][1].update(amount="-50", currency="JPY")
    return data
