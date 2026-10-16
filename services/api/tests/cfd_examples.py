"""Synthetic inputs only. No broker contract or historical FX-rate claims."""

import json
from pathlib import Path

from app.schemas.cfd_snapshot import CfdSpecificationInput
from app.services.multi_asset import content_digest

EXAMPLE_PATH = Path(__file__).parent / "fixtures" / "cfd-input.synthetic.json"


def example():
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def refresh_snapshot(payload):
    """Re-sign a deliberately edited synthetic fixture, never historical data."""
    snapshot = payload["snapshot"]
    spec = CfdSpecificationInput.model_validate(snapshot["specification"])
    snapshot["content_sha256"] = content_digest(spec.model_dump(mode="json"))
    return payload


def conversion(reference, at, from_currency="JPY", to_currency="USD"):
    return {
        "conversion_id": reference,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "rate": "0.0065",
        "observed_at": at,
        "applies_at": at,
        "max_age_seconds": 0,
        "source": {"kind": "manual", "reference": "Synthetic FX example; not market data"},
    }


def jpy_example():
    data = example()
    data["snapshot"]["specification"].update(
        instrument_id="synthetic-usdjpy",
        symbol="USDJPY",
        profit_currency="JPY",
        tick_size="0.001",
        pip_size="0.01",
    )
    data["entry"]["price"] = "150.000"
    data["exits"][0]["price"] = "150.100"
    data["exits"][1]["price"] = "150.200"
    data.update(original_stop="149.900", planned_take_profit="150.300")
    data["risk_conversion_id"] = "fx-risk"
    data["conversions"] = [conversion("fx-risk", data["entry"]["executed_at"])]
    for index, fill in enumerate(data["exits"]):
        reference = f"fx-exit-{index}"
        fill["profit_conversion_id"] = reference
        data["conversions"].append(conversion(reference, fill["executed_at"]))
    return refresh_snapshot(data)
