"""Synthetic position ledger and comparison evidence, not broker statements."""

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from cfd_examples import conversion, refresh_snapshot

FIXTURE = Path(__file__).parent / "fixtures" / "cfd-position.synthetic.json"


def position_example(costs=False):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if costs:
        trade = data["trade"]
        template = {
            "kind": "commission",
            "currency": "USD",
            "description": "Synthetic incurred charge",
            "source": {"kind": "manual", "reference": "Synthetic teaching ledger"},
        }
        trade["adjustments"] = [
            {
                **template,
                "adjustment_id": "entry-fee",
                "execution_id": trade["entry"]["execution_id"],
                "occurred_at": trade["entry"]["executed_at"],
                "amount": "-1",
            },
            *[
                {
                    **template,
                    "adjustment_id": f"exit-fee-{i}",
                    "execution_id": fill["execution_id"],
                    "occurred_at": fill["executed_at"],
                    "amount": "-0.5",
                }
                for i, fill in enumerate(trade["exits"])
            ],
            {
                **template,
                "adjustment_id": "swap",
                "kind": "swap",
                "occurred_at": "2025-01-04T12:00:00Z",
                "amount": "-2",
            },
        ]
    return data


def jpy_position(costs=False):
    data = position_example(costs)
    trade = data["trade"]
    trade["snapshot"]["specification"].update(
        symbol="USDJPY",
        instrument_id="synthetic-usdjpy",
        profit_currency="JPY",
        tick_size="0.001",
        pip_size="0.01",
    )
    trade["entry"]["price"] = "150.000"
    trade["exits"][0]["price"] = "150.200"
    trade["exits"][1]["price"] = "150.300"
    trade.update(
        original_stop="149.800", planned_take_profit="150.400", risk_conversion_id="risk-fx"
    )
    trade["conversions"] = [conversion("risk-fx", trade["entry"]["executed_at"])]
    trade["conversions"][0]["rate"] = "0.006"
    for i, fill in enumerate(trade["exits"]):
        fill["profit_conversion_id"] = f"exit-fx-{i}"
        fx = conversion(f"exit-fx-{i}", fill["executed_at"])
        fx["rate"] = "0.0065" if i == 0 else "0.0068"
        trade["conversions"].append(fx)
    refresh_snapshot(trade)
    data["rounding"]["currencies"].append({"currency": "JPY", "decimal_places": 0})
    return data


def evidence(data, **changes):
    cutoff = datetime.fromisoformat(data["as_of"].replace("Z", "+00:00"))
    closed = sum(
        (
            Decimal(fill["lots"])
            for fill in data["trade"]["exits"]
            if datetime.fromisoformat(fill["executed_at"].replace("Z", "+00:00")) <= cutoff
        ),
        Decimal(0),
    )
    return {
        "evidence_id": "synthetic-evidence",
        "position_reference": data["position_reference"],
        "account_id": data["trade"]["account"]["account_id"],
        "instrument_id": data["trade"]["snapshot"]["specification"]["instrument_id"],
        "original_lots": data["trade"]["entry"]["lots"],
        "exited_lots": str(closed),
        "state": "closed",
        "as_of": data["as_of"],
        "reported_at": data["as_of"],
        "basis": "native",
        "recognition_policy": "incurred_once",
        "metric": "net_pnl",
        "amount": "22",
        "currency": "USD",
        "comparison_basis": "raw",
        "absolute_tolerance": "0",
        "source": {"kind": "manual", "reference": "Synthetic comparison; not a broker statement"},
        **changes,
    }
