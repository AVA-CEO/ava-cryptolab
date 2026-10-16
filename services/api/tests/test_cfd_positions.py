"""Synthetic partial-close answers and exact independent cash ledgers."""

from copy import deepcopy
from decimal import Decimal, Inexact, Rounded, localcontext
from fractions import Fraction

import pytest
from cfd_calculation_examples import calculation_example, set_spec
from cfd_position_examples import jpy_position, position_example

from app.analytics.cfd import calculate_cfd
from app.analytics.cfd_positions import calculate_position
from app.schemas.cfd_positions import CfdPositionRequest, CfdPositionResult


def calculated(data):
    result = calculate_position(data)
    assert result.status == "calculated", result.model_dump()
    return result


@pytest.mark.parametrize(
    ("cutoff", "state", "closed", "left", "gross", "r"),
    [
        ("2025-01-03T00:00:00Z", "open", "0", "0.10", "0", "0"),
        ("2025-01-04T00:00:00Z", "partial", "0.04", "0.06", "8", "0.4"),
        ("2025-01-05T00:00:00Z", "closed", "0.10", "0", "26", "1.3"),
    ],
)
def test_owner_no_cost_example_at_each_state(cutoff, state, closed, left, gross, r):
    data = position_example()
    data["as_of"] = cutoff
    result = calculated(data)
    assert result.state == state
    assert result.original_lots == Decimal("0.10")
    assert result.exited_lots == Decimal(closed) and result.remaining_lots == Decimal(left)
    assert result.native.gross_pnl.raw == Decimal(gross)
    assert result.native.net_pnl.raw == Decimal(gross)
    assert result.native.original_planned_risk.raw == 20
    assert result.native.realized_r.raw == Decimal(r)
    assert result.unrealized_pnl.raw is None
    assert result.eligible_for_closed_trade_statistics == (state == "closed")
    if state != "closed":
        assert result.native.outcome == "unavailable"
    else:
        assert [fill.native_gross.raw for fill in result.exits] == [8, 18]
        assert [fill.remaining_lots_after for fill in result.exits] == [Decimal("0.06"), 0]


@pytest.mark.parametrize(
    ("cutoff", "net", "count"),
    [
        ("2025-01-03T00:00:00Z", "-1", 1),
        ("2025-01-04T00:00:00Z", "6.5", 2),
        ("2025-01-04T12:00:00Z", "4.5", 3),
        ("2025-01-05T00:00:00Z", "22", 4),
    ],
)
def test_costs_are_incurred_once_not_reallocated_each_exit(cutoff, net, count):
    data = position_example(costs=True)
    before = deepcopy(data)
    data["as_of"] = cutoff
    result = calculated(data)
    assert result.native.net_pnl.raw == Decimal(net)
    assert len(result.recognized_adjustments) == count
    assert result.native.original_planned_risk.raw == 20
    assert result.native.realized_r.raw == Decimal(net) / 20
    assert calculate_position(data) == result  # Pure replay, no accumulated fees.
    assert data["trade"] == before["trade"]
    if count == 4:
        assert result.native.adjustments.raw == -4
        assert result.native.realized_r.raw == Decimal("1.1")
        assert [item.native.raw for item in result.cost_breakdown] == [-2, -2, 0, 0]


def test_request_and_result_roundtrip_and_nested_immutability():
    data = position_example(costs=True)
    request = CfdPositionRequest.model_validate(data)
    result = calculated(request)
    assert CfdPositionResult.model_validate_json(result.model_dump_json()) == result
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        result.exits[0].lots = Decimal("1")


@pytest.mark.parametrize("direction", ["buy", "sell"])
def test_partial_losing_positions_and_forex_shorts(direction):
    data = position_example(costs=True)
    trade = data["trade"]
    trade.update(
        direction=direction,
        original_stop="1.098" if direction == "buy" else "1.102",
        planned_take_profit=None,
    )
    trade["exits"][0]["price"] = "1.098" if direction == "buy" else "1.102"
    trade["exits"][1]["price"] = "1.097" if direction == "buy" else "1.103"
    data["as_of"] = trade["exits"][0]["executed_at"]
    partial = calculated(data)
    assert partial.native.gross_pnl.raw == -8
    assert partial.native.net_pnl.raw == Decimal("-9.5")
    data["as_of"] = trade["exits"][1]["executed_at"]
    assert calculated(data).native.net_pnl.raw == -30


def test_profitable_forex_short_and_cost_credit():
    data = position_example(costs=True)
    data["trade"].update(direction="sell", original_stop="1.102", planned_take_profit=None)
    data["trade"]["exits"][0]["price"] = "1.098"
    data["trade"]["exits"][1]["price"] = "1.097"
    data["trade"]["adjustments"][-1]["amount"] = "2"  # Recorded swap credit.
    result = calculated(data)
    assert result.native.gross_pnl.raw == 26
    assert result.native.adjustments.raw == 0
    assert result.native.net_pnl.raw == 26


def test_jpy_per_exit_fx_keeps_native_gross_and_entry_risk_fixed():
    data = jpy_position(costs=True)
    result = calculated(data)
    assert [item.native_gross.raw for item in result.exits] == [800, 1800]
    assert result.native.gross_pnl.raw == 2600
    assert result.native.net_pnl.raw is None  # USD costs have no JPY valuation policy.
    assert result.reporting.gross_pnl.raw == Decimal("17.44")
    assert result.reporting.net_pnl.raw == Decimal("13.44")
    assert result.native.original_planned_risk.raw == 2000
    assert result.reporting.original_planned_risk.raw == 12
    assert result.reporting.realized_r.raw == Decimal("1.12")
    data["as_of"] = "2025-01-04T00:00:00Z"
    partial = calculated(data)
    assert partial.reporting.gross_pnl.raw == Decimal("5.2")
    assert partial.reporting.net_pnl.raw == Decimal("3.7")
    assert len(partial.conversion_evidence) == 2  # Entry risk + first exit only.


def test_native_only_missing_reporting_fx_never_drops_foreign_costs():
    data = jpy_position(costs=True)
    data["trade"].update(reporting_policy="native_only", conversions=[], risk_conversion_id=None)
    for fill in data["trade"]["exits"]:
        fill["profit_conversion_id"] = None
    result = calculated(data)
    assert result.native.gross_pnl.raw == 2600
    assert result.native.net_pnl.raw is None and result.reporting.net_pnl.raw is None
    assert result.reporting.adjustments.raw == -4


@pytest.mark.parametrize(
    ("symbol", "contract", "entry", "first", "last", "stop", "tick", "gross", "risk"),
    [
        ("XAUUSD", "100", "2000", "2002", "2003", "1998", "0.01", "26", "20"),
        ("XAGUSD", "5000", "25", "25.02", "25.03", "24.98", "0.001", "13", "10"),
    ],
)
def test_metals_partial_closures_use_declared_specifications(
    symbol, contract, entry, first, last, stop, tick, gross, risk
):
    data = position_example()
    set_spec(
        data,
        symbol=symbol,
        contract_size=contract,
        market_category="metals",
        calculation_mode="cfd_linear",
        pip_size=None,
        tick_size=tick,
    )
    data["trade"]["entry"]["price"] = entry
    data["trade"]["exits"][0]["price"] = first
    data["trade"]["exits"][1]["price"] = last
    data["trade"].update(original_stop=stop, planned_take_profit=None)
    result = calculated(data)
    assert result.native.gross_pnl.raw == Decimal(gross)
    assert result.native.original_planned_risk.raw == Decimal(risk)
    assert result.native.realized_r.raw == Decimal("1.3")


@pytest.mark.parametrize(
    "mutation",
    [
        "overclose",
        "before_entry",
        "duplicate_exit",
        "duplicate_cost",
        "unknown_execution",
        "early_cost",
        "missing_fx",
        "inverse_fx",
        "stale_fx",
        "cutoff_before_entry",
        "naive_cutoff",
        "missing_policy",
        "wrong_policy",
        "bad_snapshot",
        "float",
    ],
)
def test_invalid_ledger_is_unavailable_instead_of_negative_or_invented_totals(mutation):
    data = jpy_position(costs=True)
    trade = data["trade"]
    if mutation == "overclose":
        trade["exits"][1]["lots"] = "0.07"
    elif mutation == "before_entry":
        trade["exits"][0]["executed_at"] = "2025-01-02T00:00:00Z"
    elif mutation == "duplicate_exit":
        trade["exits"][1]["execution_id"] = trade["exits"][0]["execution_id"]
    elif mutation == "duplicate_cost":
        trade["adjustments"].append(deepcopy(trade["adjustments"][0]))
    elif mutation == "unknown_execution":
        trade["adjustments"][0]["execution_id"] = "unknown"
    elif mutation == "early_cost":
        trade["adjustments"][0]["occurred_at"] = "2025-01-02T00:00:00Z"
    elif mutation == "missing_fx":
        trade["conversions"].pop()
    elif mutation == "inverse_fx":
        trade["conversions"][1].update(from_currency="USD", to_currency="JPY")
    elif mutation == "stale_fx":
        trade["conversions"][1]["observed_at"] = "2025-01-03T00:00:00Z"
    elif mutation == "cutoff_before_entry":
        data["as_of"] = "2025-01-02T00:00:00Z"
    elif mutation == "naive_cutoff":
        data["as_of"] = "2025-01-05T00:00:00"
    elif mutation == "missing_policy":
        del data["recognition_policy"]
    elif mutation == "wrong_policy":
        data["recognition_policy"] = "guess_allocation"
    elif mutation == "bad_snapshot":
        trade["snapshot"]["specification"]["contract_size"] = "2"
    else:
        trade["entry"]["lots"] = 0.1
    result = calculate_position(data)
    assert result.status == "unavailable" and result.reason_code == "invalid_input"
    assert result.engine == "cfd-position-v1"


def test_missing_original_stop_does_not_create_zero_risk():
    data = position_example()
    data["trade"]["original_stop"] = None
    result = calculated(data)
    assert result.native.net_pnl.raw == 26
    assert result.native.original_planned_risk.raw is None and result.native.realized_r.raw is None


def test_same_time_exits_stay_distinct_and_future_costs_are_excluded():
    data = position_example(costs=True)
    data["trade"]["exits"][1]["executed_at"] = data["trade"]["exits"][0]["executed_at"]
    data["as_of"] = "2025-01-04T00:00:00Z"
    result = calculated(data)
    assert result.state == "closed" and result.remaining_lots == 0
    assert len(result.exits) == 2 and len(result.recognized_adjustments) == 2
    assert result.native.net_pnl.raw == Decimal("24.5")
    assert len(result.deferred_adjustment_ids) == 2


@pytest.mark.parametrize("jpy", [False, True])
def test_fully_closed_single_exit_matches_existing_engine(jpy):
    single = calculation_example(jpy)
    request = {
        "trade": single["trade"],
        "rounding": single["rounding"],
        "position_reference": "synthetic-single",
        "as_of": "2025-01-06T00:00:00Z",
        "recognition_policy": "incurred_once",
    }
    expected = calculate_cfd(single)
    result = calculated(request)
    assert result.native == expected.native and result.reporting == expected.reporting


def test_rounding_occurs_after_sum_and_context_does_not_leak():
    data = position_example()
    data["trade"]["exits"][0]["price"] = "1.10001"
    data["trade"]["exits"][1]["price"] = "1.10001"
    set_spec(data, contract_size="1")
    expected = calculate_position(data)
    with localcontext() as context:
        context.prec = 3
        context.traps[Inexact] = context.traps[Rounded] = True
        result = calculated(data)
        assert result == expected and context.prec == 3
    assert result.native.gross_pnl.raw == Decimal("0.000001")
    assert result.native.net_pnl.rounded == 0 and result.native.outcome == "win"
    assert result.native.realized_r.raw == Decimal("0.005")


def test_multiple_exit_totals_match_independent_exact_cash_ledger():
    data = position_example(costs=True)
    result = calculated(data)
    trade = data["trade"]
    size, entry = (
        Fraction(trade["snapshot"]["specification"]["contract_size"]),
        Fraction(trade["entry"]["price"]),
    )
    sold = sum(
        (Fraction(item["price"]) * Fraction(item["lots"]) * size for item in trade["exits"]),
        Fraction(0),
    )
    original_cost = entry * sum(
        (Fraction(item["lots"]) * size for item in trade["exits"]), Fraction(0)
    )
    assert Fraction(result.native.gross_pnl.raw) == sold - original_cost
    assert Fraction(result.native.net_pnl.raw) == sold - original_cost - 4
