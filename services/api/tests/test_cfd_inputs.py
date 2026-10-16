"""Coherent CFD inputs, not a CFD calculator or broker reconciliation."""

from copy import deepcopy
from decimal import Decimal, localcontext

import pytest
from cfd_examples import conversion, example, jpy_example, refresh_snapshot
from pydantic import ValidationError

from app.schemas.cfd import CfdTradeInput


def test_exact_partial_execution_input_roundtrip_and_frozen_collections():
    value = CfdTradeInput(**example())
    assert value.entry.lots == Decimal("0.10")
    assert tuple(fill.lots for fill in value.exits) == (Decimal("0.04"), Decimal("0.06"))
    assert value.adjustments[0].amount == Decimal("-3")
    assert CfdTradeInput.model_validate_json(value.model_dump_json()) == value
    assert isinstance(value.exits, tuple) and isinstance(value.conversions, tuple)
    with pytest.raises(ValidationError, match="frozen"):
        value.exits[0].lots = Decimal("1")
    with pytest.raises(ValidationError, match="frozen"):
        value.account.reporting_currency = "JPY"
    with pytest.raises(ValidationError, match="frozen"):
        value.adjustments = ()


@pytest.mark.parametrize("category", ["forex", "metals", "indices", "energy", "equities", "other"])
def test_supported_cfd_categories_require_explicit_specs(category):
    data = example()
    if category != "forex":
        data["snapshot"]["specification"].update(
            market_category=category, calculation_mode="cfd_linear", pip_size=None
        )
    assert (
        CfdTradeInput(**refresh_snapshot(data)).snapshot.specification.market_category == category
    )


@pytest.mark.parametrize(
    ("symbol", "contract", "tick", "entry", "exit"),
    [
        ("XAUUSD", "100", "0.01", "2000.00", "2005.00"),
        ("XAGUSD", "5000", "0.001", "25.000", "25.020"),
    ],
)
def test_metals_use_supplied_contracts_not_forex_assumptions(symbol, contract, tick, entry, exit):
    data = example()
    data["snapshot"]["specification"].update(
        symbol=symbol,
        market_category="metals",
        calculation_mode="cfd_linear",
        contract_size=contract,
        tick_size=tick,
        pip_size=None,
    )
    data["entry"]["price"] = entry
    for fill in data["exits"]:
        fill["price"] = exit
    data.update(original_stop=None, planned_take_profit=None)
    value = CfdTradeInput(**refresh_snapshot(data))
    assert value.snapshot.specification.contract_size == Decimal(contract)
    assert value.snapshot.specification.pip_size is None


@pytest.mark.parametrize("symbol", ["USDJPY", "EURJPY", "GBPJPY"])
def test_jpy_profit_is_not_assumed_to_be_usd(symbol):
    data = jpy_example()
    data["snapshot"]["specification"]["symbol"] = symbol
    value = CfdTradeInput(**refresh_snapshot(data))
    assert value.snapshot.specification.profit_currency == "JPY"
    assert value.account.reporting_currency == "USD"
    assert value.conversions[0].from_currency == "JPY"
    assert value.snapshot.specification.pip_size == Decimal("0.01")


@pytest.mark.parametrize("field", ["account", "snapshot", "entry", "direction", "reporting_policy"])
def test_missing_required_trade_facts(field):
    data = example()
    del data[field]
    with pytest.raises(ValidationError, match="Field required"):
        CfdTradeInput(**data)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"broker": "other"}, "same broker"),
        ({"server": "other"}, "match the account server"),
        ({"settlement_currency": "USDT"}, "settlement currencies"),
        ({"reporting_currency": "usd"}, "pattern"),
        ({"password": "synthetic-forbidden-field"}, "Extra inputs"),
    ],
)
def test_account_scope_validation(changes, message):
    data = example()
    data["account"].update(changes)
    with pytest.raises(ValidationError, match=message):
        CfdTradeInput(**data)


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    [
        ("entry", "lots", "0.015", "lot step"),
        ("entry", "lots", "0.001", "outside declared bounds"),
        ("entry", "lots", "101", "outside declared bounds"),
        ("entry", "lots", "0", "greater than 0"),
        ("entry", "lots", 0.1, "floats/bools"),
        ("entry", "price", "1.100001", "tick size"),
        ("entry", "price", "0", "greater than 0"),
        ("entry", "price", "Infinity", "finite"),
        ("entry", "executed_at", "2025-01-03T00:00:00", "timezone"),
        ("exit", "execution_id", "synthetic-entry", "unique"),
        ("exit", "lots", "0.11", "cannot exceed"),
        ("exit", "lots", "0.045", "lot step"),
        ("exit", "price", "1.101001", "tick size"),
        ("exit", "executed_at", "2025-01-02T00:00:00Z", "chronological"),
    ],
)
def test_invalid_fills(section, field, value, message):
    data = example()
    target = data["entry"] if section == "entry" else data["exits"][0]
    target[field] = value
    with pytest.raises(ValidationError, match=message):
        CfdTradeInput(**data)


def test_chronological_exits_and_simultaneous_unique_fills():
    data = example()
    data["exits"].reverse()
    with pytest.raises(ValidationError, match="chronological"):
        CfdTradeInput(**data)
    data["exits"][0]["executed_at"] = data["exits"][1]["executed_at"]
    CfdTradeInput(**data)  # Input order is retained for simultaneous fills.


def test_open_and_partially_closed_inputs_do_not_invent_exits_or_stops():
    data = example()
    data.update(exits=[], original_stop=None, planned_take_profit=None)
    value = CfdTradeInput(**data)
    assert value.exits == () and value.original_stop is None
    data["exits"] = example()["exits"][:1]
    assert len(CfdTradeInput(**data).exits) == 1


def test_partial_lot_sum_is_exact_even_in_low_precision_context():
    with localcontext() as context:
        context.prec = 6
        data = example()
        data["snapshot"]["specification"].update(
            volume_min="0.000000000000000001", volume_step="0.000000000000000001"
        )
        data["entry"]["lots"] = "0.100000000000000001"
        data["exits"][0]["lots"] = "0.100000000000000000"
        data["exits"][1]["lots"] = "0.000000000000000002"
        with pytest.raises(ValidationError, match="cannot exceed"):
            CfdTradeInput(**refresh_snapshot(data))
        data["exits"][1]["lots"] = "0.000000000000000001"
        CfdTradeInput(**data)


@pytest.mark.parametrize(
    ("direction", "stop", "target"),
    [
        ("buy", "1.099", "1.103"),
        ("sell", "1.103", "1.099"),
    ],
)
def test_valid_original_stop_and_target_sides(direction, stop, target):
    CfdTradeInput(
        **{
            **example(),
            "direction": direction,
            "original_stop": stop,
            "planned_take_profit": target,
        }
    )


@pytest.mark.parametrize(
    ("field", "price"),
    [
        ("original_stop", "1.10000"),
        ("original_stop", "1.10100"),
        ("original_stop", "1.099001"),
        ("planned_take_profit", "1.09900"),
        ("planned_take_profit", "1.10000"),
    ],
)
def test_invalid_original_risk_and_target(field, price):
    with pytest.raises(ValidationError):
        CfdTradeInput(**{**example(), field: price})


def test_snapshot_cannot_introduce_future_rules_or_observations():
    data = example()
    spec = data["snapshot"]["specification"]
    spec["source"].update(effective_at="2025-01-04T00:00:00Z", captured_at="2025-01-05T00:00:00Z")
    with pytest.raises(ValidationError, match="effective on or before entry"):
        CfdTradeInput(**refresh_snapshot(data))
    spec["source"]["effective_at"] = "2025-01-01T00:00:00Z"
    spec["pip_value_per_lot"] = {
        "amount": "10",
        "currency": "USD",
        "observed_at": "2025-01-04T00:00:00Z",
    }
    with pytest.raises(ValidationError, match="future pip/tick"):
        CfdTradeInput(**refresh_snapshot(data))


@pytest.mark.parametrize("kind", ["commission", "swap", "fee", "other"])
@pytest.mark.parametrize("amount", ["-3", "0", "0.000000000000000001"])
def test_explicit_signed_cash_flows(kind, amount):
    data = example()
    data["adjustments"][0].update(kind=kind, amount=amount)
    assert CfdTradeInput(**data).adjustments[0].amount == Decimal(amount)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"adjustment_id": "synthetic-swap"}, "IDs must be unique"),
        ({"execution_id": "unknown"}, "unknown execution"),
        ({"occurred_at": "2025-01-02T00:00:00Z"}, "cannot predate"),
        ({"execution_id": "synthetic-exit-2"}, "cannot predate"),
        ({"kind": "funding"}, "Input should be"),
        ({"amount": 0.1}, "floats/bools"),
        ({"currency": "usd"}, "pattern"),
    ],
)
def test_invalid_adjustments(changes, message):
    data = example()
    data["adjustments"][0].update(changes)
    with pytest.raises(ValidationError, match=message):
        CfdTradeInput(**data)


def test_cost_conversion_uses_cost_currency_and_time_not_profit_currency():
    data = jpy_example()
    item = data["adjustments"][0]
    item.update(currency="EUR", conversion_id="fx-commission")
    data["conversions"].append(conversion("fx-commission", item["occurred_at"], "EUR"))
    assert CfdTradeInput(**data).adjustments[0].currency == "EUR"
    data["conversions"][-1]["from_currency"] = "JPY"
    with pytest.raises(ValidationError, match="currency direction"):
        CfdTradeInput(**data)


@pytest.mark.parametrize(
    "mutate",
    [
        "missing",
        "wrong_direction",
        "wrong_target",
        "wrong_time",
        "duplicate",
        "unreferenced",
        "missing_risk",
    ],
)
def test_inconsistent_conversion_bindings(mutate):
    data = jpy_example()
    if mutate == "missing":
        data["exits"][0]["profit_conversion_id"] = None
    elif mutate == "wrong_direction":
        data["conversions"][1].update(from_currency="USD", to_currency="JPY")
    elif mutate == "wrong_target":
        data["conversions"][1]["to_currency"] = "EUR"
    elif mutate == "wrong_time":
        data["conversions"][1].update(applies_at="2025-01-05T00:00:00Z", max_age_seconds=86400)
    elif mutate == "duplicate":
        data["conversions"].append(deepcopy(data["conversions"][0]))
    elif mutate == "unreferenced":
        data["conversions"].append(conversion("unused", data["entry"]["executed_at"]))
    else:
        data["risk_conversion_id"] = None
    with pytest.raises(ValidationError):
        CfdTradeInput(**data)


def test_native_only_policy_does_not_require_or_imply_conversion():
    data = jpy_example()
    data.update(reporting_policy="native_only", risk_conversion_id=None, conversions=[])
    for fill in data["exits"]:
        fill["profit_conversion_id"] = None
    value = CfdTradeInput(**data)
    assert value.conversions == () and value.snapshot.specification.profit_currency == "JPY"
    data["exits"][0]["profit_conversion_id"] = "not-permitted"
    with pytest.raises(ValidationError, match="native_only"):
        CfdTradeInput(**data)


def test_usd_usdt_and_usdx_are_not_silently_equivalent():
    for reporting in ("USDT", "USDX"):
        data = example()
        data["account"]["reporting_currency"] = reporting
        with pytest.raises(ValidationError, match=f"USD to {reporting}"):
            CfdTradeInput(**data)


def test_conversion_references_cannot_attach_to_same_currency_entry_or_missing_risk():
    data = example()
    data["entry"]["profit_conversion_id"] = "fx"
    with pytest.raises(ValidationError, match="entry has no realized profit"):
        CfdTradeInput(**data)
    data = example()
    data["exits"][0]["profit_conversion_id"] = "fx"
    with pytest.raises(ValidationError, match="Same-currency"):
        CfdTradeInput(**data)
    data = jpy_example()
    data["original_stop"] = None
    with pytest.raises(ValidationError, match="requires an original planned stop"):
        CfdTradeInput(**data)


def test_revalidation_catches_unsafe_model_copy_in_nested_new_contracts():
    value = CfdTradeInput(**example())
    unsafe = value.entry.model_copy(update={"lots": 0.1})
    with pytest.raises(ValidationError, match="floats/bools"):
        CfdTradeInput(**{**example(), "entry": unsafe})


def test_tick_mode_preserves_the_observation_currency_for_conversion_bindings():
    data = example()
    observation = {"amount": "10", "currency": "USD", "observed_at": "2025-01-01T00:00:00Z"}
    spec = data["snapshot"]["specification"]
    spec.update(
        market_category="indices",
        calculation_mode="futures_tick",
        pip_size=None,
        profit_currency="JPY",
        tick_value_profit_per_lot=observation,
        tick_value_loss_per_lot={**observation, "amount": "11"},
    )
    value = CfdTradeInput(**refresh_snapshot(data))
    assert value.snapshot.specification.profit_currency == "JPY"
    assert value.snapshot.specification.valuation_currency == "USD"
    assert value.conversions == ()  # Supplied values are already in reporting USD.


def test_large_precision_limits_and_nested_snapshot_revalidation():
    data = example()
    spec = data["snapshot"]["specification"]
    spec.update(volume_max="1000000000000000000", tick_size="0.000000000000000001")
    data["entry"]["price"] = "999999999999999999.999999999999999999"
    data.update(original_stop=None, planned_take_profit=None)
    value = CfdTradeInput(**refresh_snapshot(data))
    assert value.entry.price == Decimal("999999999999999999.999999999999999999")
    unsafe_spec = value.snapshot.specification.model_copy(update={"contract_size": 0.1})
    unsafe_snapshot = value.snapshot.model_copy(update={"specification": unsafe_spec})
    with pytest.raises(ValidationError, match="floats/bools"):
        CfdTradeInput(**{**data, "snapshot": unsafe_snapshot})


def test_raw_json_decimal_numbers_are_rejected_while_decimal_strings_are_exact():
    import json

    data = example()
    data["entry"]["lots"] = 0.1
    with pytest.raises(ValidationError, match="floats/bools"):
        CfdTradeInput.model_validate_json(json.dumps(data))
    data["entry"]["lots"] = "0.10"
    assert CfdTradeInput.model_validate_json(json.dumps(data)).entry.lots == Decimal("0.10")


def test_new_inputs_never_enable_cfd_on_current_crypto_api(client):
    assert client.post("/api/v1/journal", json=example()).status_code == 422
    assert client.get("/api/v1/journal").json()["total"] == 0
