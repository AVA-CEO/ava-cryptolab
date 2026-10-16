"""Explicit display policy, exact cash accounting, deterministic Decimal context."""

from decimal import Decimal, DefaultContext, Inexact, Rounded, localcontext
from fractions import Fraction

import pytest
from cfd_calculation_examples import calculation_example, set_spec
from cfd_examples import conversion

from app.analytics.cfd import calculate_cfd


@pytest.mark.parametrize(
    ("rounding", "cost", "raw", "shown"),
    [
        ("ROUND_HALF_EVEN", "-7.655", "2.345", "2.34"),
        ("ROUND_HALF_UP", "-7.655", "2.345", "2.35"),
        ("ROUND_HALF_EVEN", "-12.345", "-2.345", "-2.34"),
        ("ROUND_HALF_UP", "-12.345", "-2.345", "-2.35"),
    ],
)
def test_explicit_ties_for_positive_and_negative_money(rounding, cost, raw, shown):
    data = calculation_example()
    data["rounding"]["rounding"] = rounding
    data["trade"]["adjustments"] = [{**data["trade"]["adjustments"][0], "amount": cost}]
    result = calculate_cfd(data)
    assert result.status == "calculated"
    assert result.native.net_pnl.raw == Decimal(raw)
    assert result.native.net_pnl.rounded == Decimal(shown)
    assert result.native.realized_r.raw == Decimal(raw) / 10


def test_fx_costs_are_summed_unrounded_before_display_quantization():
    data = calculation_example(jpy=True)
    for i, item in enumerate(data["trade"]["adjustments"]):
        item.update(currency="JPY", amount="-1", conversion_id=f"cost-{i}")
        data["trade"]["conversions"].append(conversion(f"cost-{i}", item["occurred_at"]))
    result = calculate_cfd(data)
    assert result.status == "calculated"
    assert result.reporting.adjustments.raw == Decimal("-0.013")
    assert result.reporting.net_pnl.raw == Decimal("6.487")
    assert result.reporting.net_pnl.rounded == Decimal("6.49")


def test_rounding_to_display_zero_does_not_change_outcome_or_r():
    data = calculation_example()
    data["trade"]["adjustments"] = [{**data["trade"]["adjustments"][0], "amount": "-9.996"}]
    result = calculate_cfd(data)
    assert result.status == "calculated"
    assert result.native.net_pnl.raw == Decimal("0.004")
    assert result.native.net_pnl.rounded == 0
    assert result.native.outcome == "win"
    assert result.native.realized_r.raw == Decimal("0.0004")


def test_r_uses_unrounded_original_risk_even_when_it_displays_as_zero():
    data = calculation_example()
    set_spec(data, contract_size="1")
    data["trade"]["entry"]["lots"] = "0.01"
    data["trade"]["exits"][0]["lots"] = "0.01"
    data["trade"].update(adjustments=[], original_stop="1.09999")
    result = calculate_cfd(data)
    assert result.status == "calculated"
    assert result.native.original_planned_risk.raw == Decimal("0.0000001")
    assert result.native.original_planned_risk.rounded == 0
    assert result.native.realized_r.raw == 100


def test_repeating_pip_ratio_uses_explicit_movement_places():
    data = calculation_example()
    set_spec(data, pip_size="0.00003")
    result = calculate_cfd(data)
    assert result.status == "calculated"
    assert result.pips.rounded == Decimal("33.333333")
    assert len(result.pips.raw.as_tuple().digits) == 160


def test_calculation_does_not_inherit_or_change_callers_decimal_context():
    data = calculation_example(jpy=True)
    expected = calculate_cfd(data)
    with localcontext() as context:
        context.prec = 4
        context.Emax, context.Emin = 5, -5
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        flags = context.flags.copy()
        assert calculate_cfd(data) == expected
        assert context.prec == 4 and context.Emax == 5 and context.Emin == -5
        assert context.traps[Inexact] and context.traps[Rounded]
        assert context.flags == flags


def test_decimal_global_defaults_cannot_change_calculation_policy():
    data = calculation_example(jpy=True)
    expected = calculate_cfd(data)
    previous = DefaultContext.copy()
    try:
        DefaultContext.prec = 3
        DefaultContext.Emin, DefaultContext.Emax = -3, 3
        DefaultContext.traps[Inexact] = True
        DefaultContext.traps[Rounded] = True
        assert calculate_cfd(data) == expected
    finally:
        DefaultContext.prec = previous.prec
        DefaultContext.Emin, DefaultContext.Emax = previous.Emin, previous.Emax
        DefaultContext.traps = previous.traps


def test_extreme_conversion_products_match_independent_rational_cash_ledger():
    data = calculation_example(jpy=True)
    set_spec(
        data,
        tick_size="0.000000000000000001",
        contract_size="999999999999999999.999999999999999999",
        volume_max="1000000000000000000",
    )
    trade = data["trade"]
    trade.update(original_stop=None, planned_take_profit=None, risk_conversion_id=None)
    trade["entry"].update(price="0.000000000000000001", lots="999999999999999999.99")
    trade["exits"][0].update(
        price="999999999999999999.999999999999999999", lots=trade["entry"]["lots"]
    )
    trade["conversions"] = trade["conversions"][:1]
    trade["conversions"][0]["rate"] = "999999999999999999.999999999999999999"
    result = calculate_cfd(data)
    assert result.status == "calculated"
    units = Fraction(trade["entry"]["lots"]) * Fraction(
        trade["snapshot"]["specification"]["contract_size"]
    )
    ledger = units * Fraction(trade["exits"][0]["price"]) - units * Fraction(
        trade["entry"]["price"]
    )
    assert (
        Fraction(result.reporting.net_pnl.raw)
        == ledger * Fraction(trade["conversions"][0]["rate"]) - 4
    )


def test_large_cash_products_preserve_exact_digits_outside_input_field_bounds():
    data = calculation_example()
    set_spec(
        data,
        tick_size="0.000000000000000001",
        contract_size="999999999999999999.999999999999999999",
        volume_max="1000000000000000000",
    )
    trade = data["trade"]
    trade.update(adjustments=[], original_stop=None, planned_take_profit=None)
    trade["entry"].update(price="0.000000000000000001", lots="999999999999999999.99")
    trade["exits"][0].update(
        price="999999999999999999.999999999999999999", lots=trade["entry"]["lots"]
    )
    result = calculate_cfd(data)
    assert result.status == "calculated"
    units = Fraction(trade["entry"]["lots"]) * Fraction(
        trade["snapshot"]["specification"]["contract_size"]
    )
    expected = units * Fraction(trade["exits"][0]["price"]) - units * Fraction(
        trade["entry"]["price"]
    )
    assert Fraction(result.native.gross_pnl.raw) == expected
    assert result.native.gross_pnl.raw > Decimal("1e18")


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "float_places",
        "bool_places",
        "negative",
        "too_many",
        "unknown_mode",
        "no_ratio",
        "no_movement",
    ],
)
def test_incomplete_or_invalid_rounding_policy_is_unavailable(mutation):
    data = calculation_example()
    policy = data["rounding"]
    if mutation == "missing":
        policy["currencies"] = [{"currency": "EUR", "decimal_places": 2}]
    elif mutation == "duplicate":
        policy["currencies"].append(dict(policy["currencies"][0]))
    elif mutation == "float_places":
        policy["currencies"][0]["decimal_places"] = 2.0
    elif mutation == "bool_places":
        policy["currencies"][0]["decimal_places"] = True
    elif mutation == "negative":
        policy["ratio_places"] = -1
    elif mutation == "too_many":
        policy["movement_places"] = 19
    elif mutation == "unknown_mode":
        policy["rounding"] = "ROUND_DOWN"
    elif mutation == "no_ratio":
        del policy["ratio_places"]
    else:
        del policy["movement_places"]
    result = calculate_cfd(data)
    assert result.status == "unavailable"
    assert result.reason_code == (
        "missing_currency_precision" if mutation == "missing" else "invalid_input"
    )


def test_zero_raw_net_with_no_costs_is_breakeven_and_zero_r():
    data = calculation_example()
    data["trade"]["exits"][0]["price"] = data["trade"]["entry"]["price"]
    data["trade"]["adjustments"] = []
    result = calculate_cfd(data)
    assert result.status == "calculated"
    assert result.native.net_pnl.raw == 0
    assert result.native.realized_r.raw == 0
    assert result.native.outcome == "breakeven"
