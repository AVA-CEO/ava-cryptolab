"""Ledger limits, unsupported modes, currency evidence and single-close parity."""

from decimal import Decimal

import pytest
from cfd_calculation_examples import calculation_example, set_spec
from cfd_position_examples import jpy_position, position_example

from app.analytics.cfd import calculate_cfd
from app.analytics.cfd_positions import calculate_position


def test_maximum_supported_exit_and_cost_counts_sum_exactly_once():
    data = position_example(costs=True)
    trade = data["trade"]
    trade["entry"]["lots"] = "10"
    base = trade["exits"][0]
    trade["exits"] = [
        {**base, "execution_id": f"exit-{i}", "lots": "0.01", "price": "1.10100"}
        for i in range(1000)
    ]
    cost = trade["adjustments"][0]
    trade["adjustments"] = [cost] + [
        {
            **cost,
            "adjustment_id": f"cost-{i}",
            "execution_id": f"exit-{i}",
            "occurred_at": base["executed_at"],
            "amount": "-0.001",
        }
        for i in range(999)
    ]
    result = calculate_position(data)
    assert result.status == "calculated"
    assert result.exited_lots == 10 and result.remaining_lots == 0
    assert result.native.gross_pnl.raw == 1000
    assert result.native.adjustments.raw == Decimal("-1.999")
    assert result.native.net_pnl.raw == Decimal("998.001")
    assert result.native.original_planned_risk.raw == 2000


def test_foreign_entry_cost_uses_supplied_entry_rate_only_once():
    data = jpy_position(costs=True)
    data["trade"]["adjustments"][0].update(currency="JPY", amount="-100", conversion_id="risk-fx")
    result = calculate_position(data)
    assert result.status == "calculated"
    assert result.reporting.adjustments.raw == Decimal("-3.6")
    assert result.reporting.net_pnl.raw == Decimal("13.84")
    assert len(result.recognized_adjustments) == 4
    assert len(result.conversion_evidence) == 3


def test_unsupported_tick_mode_and_mismatched_index_category_remain_unsupported():
    data = position_example()
    observation = {"amount": "10", "currency": "USD", "observed_at": "2025-01-01T00:00:00Z"}
    set_spec(
        data,
        market_category="indices",
        calculation_mode="futures_tick",
        pip_size=None,
        tick_value_profit_per_lot=observation,
        tick_value_loss_per_lot=observation,
    )
    assert calculate_position(data).reason_code == "unsupported_mode"
    set_spec(data, market_category="metals", calculation_mode="cfd_index")
    assert calculate_position(data).reason_code == "unsupported_mode"


def test_missing_rounding_currency_is_not_inferred():
    data = jpy_position()
    data["rounding"]["currencies"] = data["rounding"]["currencies"][:1]
    assert calculate_position(data).reason_code == "missing_currency_precision"


def test_invalid_future_exit_is_rejected_even_before_that_exit_cutoff():
    data = position_example()
    data["as_of"] = "2025-01-04T00:00:00Z"
    data["trade"]["exits"][1]["lots"] = "0.07"
    result = calculate_position(data)
    assert result.status == "unavailable" and result.reason_code == "invalid_input"


@pytest.mark.parametrize("missing_stop", [False, True])
@pytest.mark.parametrize("native_only", [False, True])
def test_single_close_parity_including_unavailable_currency_and_risk_reasons(
    missing_stop, native_only
):
    single = calculation_example(jpy=True)
    trade = single["trade"]
    if missing_stop:
        trade.update(original_stop=None, risk_conversion_id=None)
        trade["conversions"] = trade["conversions"][:1]
    if native_only:
        trade.update(reporting_policy="native_only", risk_conversion_id=None, conversions=[])
        trade["exits"][0]["profit_conversion_id"] = None
    expected = calculate_cfd(single)
    result = calculate_position(
        {
            "trade": trade,
            "rounding": single["rounding"],
            "position_reference": "synthetic-single",
            "as_of": "2025-01-06T00:00:00Z",
            "recognition_policy": "incurred_once",
        }
    )
    assert result.status == "calculated"
    assert result.native == expected.native and result.reporting == expected.reporting


def test_exact_tiny_lots_do_not_become_negative_remaining_quantity():
    data = position_example()
    set_spec(data, volume_min="0.000000000000000001", volume_step="0.000000000000000001")
    trade = data["trade"]
    trade["entry"]["lots"] = "0.100000000000000001"
    trade["exits"][0]["lots"] = "0.100000000000000000"
    trade["exits"][1]["lots"] = "0.000000000000000001"
    result = calculate_position(data)
    assert result.status == "calculated"
    assert result.remaining_lots == 0
    assert result.exits[0].remaining_lots_after == Decimal("0.000000000000000001")
