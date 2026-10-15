"""Synthetic contract examples, not verified Bybit specifications or prices."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.account import AccountContract
from app.schemas.instrument import CfdInstrument, SpecificationSource, instrument_adapter
from app.schemas.multi_asset import JournalContract
from app.schemas.trade import TradeInput


def specification(product="cfd", category="forex", **changes):
    data = {
        "instrument_id": "synthetic-eurusd",
        "symbol": "EURUSD",
        "broker": "Synthetic broker",
        "venue": "Synthetic server",
        "product": product,
        "market_category": category,
        "calculation_mode": "forex",
        "quantity_unit": "lots",
        "profit_currency": "USD",
        "settlement_currency": "USD",
        "tick_size": "0.00001",
        "volume_min": "0.01",
        "volume_step": "0.01",
        "contract_size": "100000",
        "pip_size": "0.0001",
        "source": {
            "kind": "manual",
            "reference": "Synthetic teaching fixture; not a broker specification",
            "effective_at": "2025-01-01T02:00:00+02:00",
            "captured_at": "2025-01-02T00:00:00Z",
        },
    }
    if product in {"crypto_spot", "crypto_linear_futures"}:
        data.pop("contract_size")
        data.pop("pip_size")
        data.update(
            symbol="BTC/USDT",
            instrument_id="synthetic-btc",
            calculation_mode="spot_inventory" if product == "crypto_spot" else "linear_quote",
            quantity_unit="base_units",
            base_currency="BTC",
            quote_currency="USDT",
            profit_currency="USDT",
            settlement_currency="USDT",
        )
    if product == "tradfi_perpetual":
        data.pop("contract_size")
        data.pop("pip_size")
        data.update(
            symbol="SYNTHETIC-GOLD-PERP",
            calculation_mode="linear_contract",
            quantity_unit="contracts",
            contract_multiplier="1",
        )
    data.update(changes)
    return data


def account(**changes):
    return {
        "account_id": "practice-cfd-account",
        "name": "Synthetic practice account",
        "broker": "Synthetic broker",
        "platform": "mt5",
        "server": "Synthetic server",
        "reporting_currency": "USD",
        "settlement_currency": "USD",
        **changes,
    }


@pytest.mark.parametrize(
    ("product", "category"),
    [
        ("crypto_spot", "crypto"),
        ("crypto_linear_futures", "crypto"),
        ("cfd", "forex"),
        ("tradfi_perpetual", "metals"),
    ],
)
def test_product_discriminator_and_decimal_roundtrip(product, category):
    value = instrument_adapter.validate_python(specification(product, category))
    wire = instrument_adapter.dump_json(value)
    assert b'"tick_size":"0.00001"' in wire
    assert instrument_adapter.validate_json(wire) == value
    assert value.source.effective_at.isoformat() == "2025-01-01T00:00:00+00:00"


@pytest.mark.parametrize("symbol", ["XAUUSD", "XAGUSD"])
def test_metals_do_not_assume_forex_pip_conventions(symbol):
    value = instrument_adapter.validate_python(
        specification(
            category="metals", symbol=symbol, calculation_mode="cfd_linear", pip_size=None
        )
    )
    assert isinstance(value, CfdInstrument)
    assert value.pip_size is None
    assert value.contract_size == Decimal("100000")  # Synthetic only, not broker metadata.


@pytest.mark.parametrize(
    "changes",
    [
        {"product": "unknown"},
        {"quantity_unit": "base_units"},
        {"market_category": "crypto"},
        {"calculation_mode": "linear_quote"},
        {"pip_size": None},
        {"contract_size": "0"},
        {"contract_size": "NaN"},
        {"tick_size": "Infinity"},
        {"tick_size": "-0.01"},
        {"volume_step": "0"},
        {"volume_max": "0.001"},
        {"profit_currency": "usd"},
        {"settlement_currency": " USD/USDT "},
        {"funding": "10"},
        {"api_key": "not-a-real-key"},
        {"market_category": "metals"},
    ],
)
def test_invalid_or_ambiguous_contracts_are_rejected(changes):
    with pytest.raises(ValidationError):
        instrument_adapter.validate_python(specification(**changes))


def test_tick_calculation_requires_currency_and_time_aware_values():
    data = specification(category="indices", calculation_mode="futures_tick", pip_size=None)
    with pytest.raises(ValidationError):
        instrument_adapter.validate_python(data)
    observation = {"amount": "2.5", "currency": "USD", "observed_at": "2025-01-01T00:00:00Z"}
    data.update(tick_value_profit_per_lot=observation, tick_value_loss_per_lot=observation)
    value = instrument_adapter.validate_python(data)
    assert value.tick_value_profit_per_lot.amount == Decimal("2.5")
    data["tick_value_profit_per_lot"] = {**observation, "observed_at": "2025-01-01T00:00:00"}
    with pytest.raises(ValidationError):
        instrument_adapter.validate_python(data)


def test_pip_values_are_observations_not_assumed_dollar_constants():
    data = specification(
        pip_value_per_lot={
            "amount": "9.12",
            "currency": "EUR",
            "observed_at": "2025-01-01T00:00:00Z",
        }
    )
    value = instrument_adapter.validate_python(data)
    assert value.pip_value_per_lot.currency == "EUR"
    data.update(market_category="metals", calculation_mode="cfd_linear", pip_size=None)
    with pytest.raises(ValidationError):
        instrument_adapter.validate_python(data)


@pytest.mark.parametrize(
    "changes",
    [
        {"effective_at": "2025-01-01T00:00:00"},
        {"captured_at": "2025-01-02T00:00:00"},
        {"effective_at": "2025-01-03T00:00:00Z"},
    ],
)
def test_specification_time_is_explicit(changes):
    with pytest.raises(ValidationError):
        SpecificationSource(**{**specification()["source"], **changes})


def test_snapshot_is_immutable():
    value = instrument_adapter.validate_python(specification())
    with pytest.raises(ValidationError):
        value.contract_size = Decimal("1")
    with pytest.raises(ValidationError):
        value.source.reference = "Replacement rules"


def test_account_distinguishes_reporting_from_settlement_without_fx_assumptions():
    data = account(reporting_currency="USDX", settlement_currency="USDT")
    value = AccountContract(**data)
    assert value.reporting_currency != value.settlement_currency
    data.update(password="not-a-real-password")
    with pytest.raises(ValidationError):
        AccountContract(**data)
    with pytest.raises(ValidationError):
        AccountContract(**account(server=None))


@pytest.mark.parametrize(
    "account_changes",
    [
        {"settlement_currency": "USDT"},
        {"broker": "Other broker"},
        {"server": "Other server"},
    ],
)
def test_account_instrument_mismatch_is_rejected(account_changes):
    with pytest.raises(ValidationError):
        JournalContract(account=account(**account_changes), instrument=specification())


def test_mt5_cannot_be_misclassified_as_crypto_or_perpetual():
    with pytest.raises(ValidationError):
        JournalContract(account=account(), instrument=specification("tradfi_perpetual", "metals"))
    value = JournalContract(account=account(), instrument=specification())
    assert JournalContract.model_validate_json(value.model_dump_json()) == value


def test_crypto_contract_does_not_assume_quote_settlement_parity():
    with pytest.raises(ValidationError):
        instrument_adapter.validate_python(
            specification("crypto_linear_futures", "crypto", settlement_currency="USD")
        )


def test_current_api_rejects_cfd_instead_of_calculating_it_as_crypto(client):
    data = {
        "pair": "EURUSD",
        "exchange": "Synthetic broker",
        "currency": "USD",
        "market": "cfd",
        "direction": "buy",
        "entry_at": "2025-01-01T00:00:00Z",
        "entry_price": "1.1",
        "quantity": "0.1",
    }
    assert client.post("/api/v1/journal", json=data).status_code == 422
    assert client.get("/api/v1/journal").json()["total"] == 0
    with pytest.raises(ValidationError):
        TradeInput(**data)
