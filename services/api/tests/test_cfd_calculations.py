"""Hand-derived synthetic answers; no assertion of broker reconciliation."""

from copy import deepcopy
from decimal import Decimal
from fractions import Fraction

import pytest
from cfd_calculation_examples import calculation_example, native_jpy_example, set_spec
from cfd_examples import conversion

from app.analytics.cfd import calculate_cfd
from app.schemas.cfd_results import CfdCalculationRequest, CfdCalculationResult


def calculated(data):
    result = calculate_cfd(data)
    assert result.status == "calculated", result.model_dump()
    return result


def test_eurusd_hand_worked_example_and_roundtrip():
    data = calculation_example()
    before = deepcopy(data)
    result = calculated(data)
    assert result.native.gross_pnl.raw == Decimal("10")
    assert result.native.adjustments.raw == Decimal("-4")
    assert result.native.net_pnl.raw == Decimal("6")
    assert result.native.original_planned_risk.raw == Decimal("10")
    assert result.native.realized_r.raw == Decimal("0.6")
    assert result.pips.raw == 10 and result.ticks.raw == 100
    assert result.native == result.reporting
    assert result.native.outcome == "win"
    assert data == before
    assert CfdCalculationResult.model_validate_json(result.model_dump_json()) == result
    assert calculated(CfdCalculationRequest.model_validate(data)) == result


@pytest.mark.parametrize("symbol", ["EURUSD", "GBPUSD"])
@pytest.mark.parametrize(
    ("direction", "exit_price", "stop", "target", "gross", "net", "r"),
    [
        ("buy", "1.10100", "1.09900", "1.10300", "10", "6", "0.6"),
        ("sell", "1.09900", "1.10100", "1.09700", "10", "6", "0.6"),
        ("buy", "1.09900", "1.09900", "1.10300", "-10", "-14", "-1.4"),
        ("sell", "1.10100", "1.10100", "1.09700", "-10", "-14", "-1.4"),
        ("buy", "1.10000", "1.09900", "1.10300", "0", "-4", "-0.4"),
    ],
)
def test_linear_forex_longs_shorts_losses_and_flat_price(
    symbol, direction, exit_price, stop, target, gross, net, r
):
    data = calculation_example()
    set_spec(data, symbol=symbol)
    data["trade"].update(direction=direction, original_stop=stop, planned_take_profit=target)
    data["trade"]["exits"][0]["price"] = exit_price
    result = calculated(data)
    assert result.native.gross_pnl.raw == Decimal(gross)
    assert result.native.net_pnl.raw == Decimal(net)
    assert result.native.realized_r.raw == Decimal(r)


@pytest.mark.parametrize("symbol", ["USDJPY", "EURJPY", "GBPJPY"])
def test_jpy_gross_and_explicit_usd_conversion_keep_both_currencies(symbol):
    data = calculation_example(jpy=True)
    set_spec(data, symbol=symbol)
    result = calculated(data)
    assert result.native.currency == "JPY"
    assert result.native.gross_pnl.raw == 1000
    assert result.native.original_planned_risk.raw == 1000
    assert result.reporting.currency == "USD"
    assert result.reporting.gross_pnl.raw == Decimal("6.50")
    assert result.reporting.net_pnl.raw == Decimal("2.50")
    assert result.reporting.realized_r.rounded == Decimal("0.384615")
    assert result.native.net_pnl.raw is None  # USD costs lack a JPY valuation policy.
    assert result.native.realized_r.raw is None
    assert result.conversion_evidence[0].source.reference.startswith("Synthetic")


def test_jpy_short_and_native_only_results_are_available_without_invented_fx():
    data = native_jpy_example()
    trade = data["trade"]
    trade.update(direction="sell", original_stop="150.100", planned_take_profit="149.700")
    trade["exits"][0]["price"] = "149.900"
    result = calculated(data)
    assert result.native.gross_pnl.raw == 1000
    assert result.native.net_pnl.raw == 850
    assert result.native.realized_r.raw == Decimal("0.85")
    assert result.reporting.gross_pnl.raw is None
    assert result.reporting.net_pnl.raw is None
    assert "native_only" in result.reporting.gross_pnl.unavailable_reason


def test_cash_flows_use_their_own_rates_and_original_risk_uses_entry_time():
    data = calculation_example(jpy=True)
    trade = data["trade"]
    trade["conversions"][1]["rate"] = "0.0060"  # Entry risk; exit remains 0.0065.
    for index, item in enumerate(trade["adjustments"]):
        item.update(
            currency="JPY", amount="-100" if index == 0 else "-50", conversion_id=f"cost-{index}"
        )
        observation = conversion(f"cost-{index}", item["occurred_at"])
        observation["rate"] = "0.0060" if index == 0 else "0.0065"
        trade["conversions"].append(observation)
    result = calculated(data)
    # Independent cash ledger: 6.50 - 0.60 - 0.325 = 5.575 USD.
    assert result.reporting.net_pnl.raw == Decimal("5.575")
    assert result.reporting.net_pnl.rounded == Decimal("5.58")
    assert result.reporting.original_planned_risk.raw == Decimal("6.0")
    assert result.reporting.realized_r.rounded == Decimal("0.929167")
    assert result.native.net_pnl.raw == 850
    assert result.native.realized_r.raw == Decimal("0.85")


@pytest.mark.parametrize(
    ("symbol", "size", "tick", "entry", "exit_price", "stop", "gross", "risk"),
    [
        ("XAUUSD", "100", "0.01", "2000.00", "2005.00", "1990.00", "50", "100"),
        ("XAGUSD", "5000", "0.001", "25.000", "25.020", "24.980", "10", "10"),
    ],
)
@pytest.mark.parametrize("direction", ["buy", "sell"])
def test_metals_use_supplied_contract_units(
    symbol, size, tick, entry, exit_price, stop, gross, risk, direction
):
    data = calculation_example()
    set_spec(
        data,
        symbol=symbol,
        market_category="metals",
        calculation_mode="cfd_linear",
        contract_size=size,
        tick_size=tick,
        pip_size=None,
    )
    trade = data["trade"]
    trade.update(
        direction=direction,
        original_stop=stop if direction == "buy" else exit_price,
        planned_take_profit=None,
    )
    trade["entry"]["price"] = entry
    trade["exits"][0]["price"] = exit_price
    result = calculated(data)
    assert result.native.gross_pnl.raw == Decimal(gross) * (1 if direction == "buy" else -1)
    expected_risk = Decimal(risk) if direction == "buy" else Decimal(gross)
    assert result.native.original_planned_risk.raw == expected_risk
    assert result.pips.raw is None
    assert "not inferred" in result.pips.unavailable_reason


@pytest.mark.parametrize(
    ("kind", "amount", "expected_net"),
    [
        ("commission", "-3", "7"),
        ("commission", "3", "13"),
        ("swap", "-1", "9"),
        ("swap", "1", "11"),
        ("fee", "-10", "0"),
        ("other", "-20", "-10"),
        ("other", "0", "10"),
    ],
)
def test_signed_adjustments_and_raw_outcome(kind, amount, expected_net):
    data = calculation_example()
    item = data["trade"]["adjustments"][0]
    item.update(kind=kind, amount=amount)
    data["trade"]["adjustments"] = [item]
    result = calculated(data)
    assert result.native.gross_pnl.raw == 10
    assert result.native.net_pnl.raw == Decimal(expected_net)
    assert result.native.outcome == (
        "win" if Decimal(expected_net) > 0 else "loss" if Decimal(expected_net) < 0 else "breakeven"
    )


def test_foreign_cost_can_be_converted_into_native_profit_when_account_reports_native():
    data = calculation_example()
    item = data["trade"]["adjustments"][0]
    item.update(currency="EUR", amount="-2", conversion_id="eur-cost")
    observation = conversion("eur-cost", item["occurred_at"], "EUR")
    observation["rate"] = "1.10"
    data["trade"]["conversions"] = [observation]
    data["rounding"]["currencies"].append({"currency": "EUR", "decimal_places": 2})
    result = calculated(data)
    assert result.native.net_pnl.raw == Decimal("6.80")  # 10 - 2.20 - 1.
    assert [(item.currency, item.raw) for item in result.adjustments_by_currency] == [
        ("EUR", Decimal("-2")),
        ("USD", Decimal("-1")),
    ]


def test_native_only_does_not_drop_foreign_fees_even_if_gross_currency_matches_account():
    data = calculation_example()
    data["trade"].update(reporting_policy="native_only")
    data["trade"]["adjustments"][0]["currency"] = "EUR"
    data["rounding"]["currencies"].append({"currency": "EUR", "decimal_places": 2})
    result = calculated(data)
    assert result.native.gross_pnl.raw == 10
    assert result.native.net_pnl.raw is None and result.reporting.net_pnl.raw is None
    assert result.native.realized_r.raw is None


def test_missing_stop_has_no_invented_zero_risk_or_r():
    data = calculation_example()
    data["trade"]["original_stop"] = None
    result = calculated(data)
    assert result.native.net_pnl.raw == 6
    assert result.native.original_planned_risk.raw is None
    assert result.native.realized_r.raw is None
    assert "stop" in result.native.realized_r.unavailable_reason.lower()


@pytest.mark.parametrize("mode", ["cfd_linear", "cfd_index"])
def test_index_modes_use_explicit_contracts_not_tick_mode_formula(mode):
    data = calculation_example()
    set_spec(data, market_category="indices", calculation_mode=mode)
    assert calculated(data).native.gross_pnl.raw == 10


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_rate",
        "inverse",
        "stale",
        "future",
        "missing_contract",
        "float",
        "mismatch",
        "wrong_stop",
        "zero_stop_risk",
        "bad_digest",
        "no_rounding",
        "leverage",
        "spread",
        "unknown_mode",
    ],
)
def test_invalid_financial_requests_are_unavailable_not_guessed(mutation):
    data = calculation_example(jpy=True)
    trade = data["trade"]
    if mutation == "missing_rate":
        trade["conversions"].pop(0)
    elif mutation == "inverse":
        trade["conversions"][0].update(from_currency="USD", to_currency="JPY")
    elif mutation == "stale":
        trade["conversions"][0]["observed_at"] = "2025-01-03T23:59:59Z"
    elif mutation == "future":
        trade["conversions"][0]["observed_at"] = "2025-01-04T00:00:01Z"
    elif mutation == "missing_contract":
        del trade["snapshot"]["specification"]["contract_size"]
    elif mutation == "float":
        trade["entry"]["lots"] = 0.1
    elif mutation == "mismatch":
        trade["account"]["settlement_currency"] = "USDT"
    elif mutation in ("wrong_stop", "zero_stop_risk"):
        trade["original_stop"] = "151" if mutation == "wrong_stop" else "150"
    elif mutation == "bad_digest":
        trade["snapshot"]["specification"]["contract_size"] = "50000"
    elif mutation == "no_rounding":
        del data["rounding"]
    elif mutation in ("leverage", "spread"):
        trade[mutation] = "10"
    else:
        trade["snapshot"]["specification"]["calculation_mode"] = "guessed"
    result = calculate_cfd(data)
    assert result.status == "unavailable" and result.reason_code == "invalid_input"
    assert result.issues
    assert "native" not in result.model_dump()


@pytest.mark.parametrize("exits", [[], [{"lots": "0.04"}], [{"lots": "0.04"}, {"lots": "0.06"}]])
def test_open_partial_and_multi_exit_positions_are_not_calculated(exits):
    data = calculation_example()
    original = data["trade"]["exits"][0]
    data["trade"]["exits"] = [
        {**original, "execution_id": f"exit-{i}", **fill} for i, fill in enumerate(exits)
    ]
    result = calculate_cfd(data)
    assert result.status == "unavailable" and result.reason_code == "unsupported_position"


def test_tick_mode_and_incompatible_index_category_are_not_silently_linear():
    data = calculation_example()
    observation = {"amount": "10", "currency": "USD", "observed_at": "2025-01-01T00:00:00Z"}
    set_spec(
        data,
        market_category="indices",
        calculation_mode="futures_tick",
        pip_size=None,
        tick_value_profit_per_lot=observation,
        tick_value_loss_per_lot=observation,
    )
    assert calculate_cfd(data).reason_code == "unsupported_mode"
    set_spec(data, market_category="metals", calculation_mode="cfd_index")
    assert calculate_cfd(data).reason_code == "unsupported_mode"


@pytest.mark.parametrize("reporting", ["USDT", "USDX"])
def test_dollar_like_currency_codes_still_require_conversion(reporting):
    data = calculation_example()
    data["trade"]["account"]["reporting_currency"] = reporting
    result = calculate_cfd(data)
    assert result.status == "unavailable" and result.reason_code == "invalid_input"


@pytest.mark.parametrize(
    ("lots", "size", "entry", "exit_price"),
    [
        ("0.10", "100000", "1.10000", "1.10100"),
        ("0.20", "50000", "1.10000", "1.09950"),
        ("0.33", "70000", "1.23456", "1.23489"),
    ],
)
def test_independent_rational_cash_ledger_expected_values(lots, size, entry, exit_price):
    data = calculation_example()
    set_spec(data, contract_size=size)
    data["trade"].update(original_stop=None, planned_take_profit=None)
    data["trade"]["entry"].update(lots=lots, price=entry)
    data["trade"]["exits"][0].update(lots=lots, price=exit_price)
    # Independent oracle: exact rational cash paid at entry and received at exit.
    units = Fraction(lots) * Fraction(size)
    expected_cash = units * Fraction(exit_price) - units * Fraction(entry)
    result = calculated(data)
    assert Fraction(result.native.gross_pnl.raw) == expected_cash
    assert Fraction(result.native.net_pnl.raw) == expected_cash - 4


def test_sign_and_size_invariants_without_costs():
    data = calculation_example()
    data["trade"].update(adjustments=[], original_stop=None, planned_take_profit=None)
    base = calculated(data)
    data["trade"]["direction"] = "sell"
    assert calculated(data).native.gross_pnl.raw == -base.native.gross_pnl.raw
    data["trade"]["direction"] = "buy"
    data["trade"]["entry"]["lots"] = "0.20"
    data["trade"]["exits"][0]["lots"] = "0.20"
    assert calculated(data).native.gross_pnl.raw == 2 * base.native.gross_pnl.raw
