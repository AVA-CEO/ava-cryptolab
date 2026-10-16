"""New CFD boundary; existing instrument-v1 database storage stays unchanged."""

from copy import deepcopy
from decimal import Decimal

import pytest
from cfd_examples import example, refresh_snapshot
from pydantic import ValidationError

from app.schemas.cfd_snapshot import CfdSnapshotInput, CfdSpecificationInput
from app.schemas.instrument import instrument_adapter
from app.services.multi_asset import content_digest, load_snapshot, store_snapshot


def test_snapshot_is_compatible_with_existing_canonical_storage(db):
    payload = example()["snapshot"]
    spec = CfdSpecificationInput(**payload["specification"])
    assert content_digest(spec.model_dump(mode="json")) == payload["content_sha256"]
    assert instrument_adapter.validate_python(spec.model_dump()).contract_size == Decimal("100000")
    with db.begin():
        row = store_snapshot(db, payload["specification"])
        snapshot_id = row.id
    restored = load_snapshot(db, snapshot_id)
    value = CfdSnapshotInput(
        snapshot_id=snapshot_id,
        specification=restored.model_dump(),
        content_sha256=row.content_sha256,
    )
    assert CfdSnapshotInput.model_validate_json(value.model_dump_json()) == value


@pytest.mark.parametrize(
    "field", ["contract_size", "tick_size", "volume_step", "profit_currency", "source"]
)
def test_missing_instrument_facts_are_not_guessed(field):
    data = example()["snapshot"]["specification"]
    del data[field]
    with pytest.raises(ValidationError, match="Field required"):
        CfdSpecificationInput(**data)


@pytest.mark.parametrize(
    "field", ["contract_size", "tick_size", "volume_min", "volume_step", "pip_size", "volume_max"]
)
def test_all_specification_amounts_reject_float(field):
    data = example()["snapshot"]["specification"]
    data[field] = 0.1
    with pytest.raises(ValidationError, match="floats/bools"):
        CfdSpecificationInput(**data)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"contract_size": "0"}, "greater than 0"),
        ({"contract_size": "NaN"}, "finite"),
        ({"pip_size": None}, "explicit pip"),
        ({"pip_size": "0.000015"}, "whole multiple"),
        ({"volume_min": "0.015"}, "align"),
        ({"volume_max": "0.001"}, "below minimum"),
        ({"market_category": "crypto"}, "Input should be"),
        ({"quantity_unit": "base_units"}, "Input should be"),
        ({"calculation_mode": "linear_quote"}, "Input should be"),
        ({"product": "crypto_linear_futures"}, "Input should be"),
        ({"product": "tradfi_perpetual"}, "Input should be"),
        ({"market_category": "metals"}, "forex market category"),
        ({"api_key": "synthetic-forbidden-field"}, "Extra inputs"),
    ],
)
def test_invalid_instrument_combinations(changes, message):
    data = example()["snapshot"]["specification"]
    data.update(changes)
    with pytest.raises(ValidationError, match=message):
        CfdSpecificationInput(**data)


def observation(**changes):
    return {"amount": "10", "currency": "USD", "observed_at": "2025-01-01T00:00:00Z", **changes}


def test_tick_mode_requires_explicit_values_and_keeps_them_as_observations():
    data = example()["snapshot"]["specification"]
    data.update(market_category="indices", calculation_mode="futures_tick", pip_size=None)
    with pytest.raises(ValidationError, match="both profit and loss"):
        CfdSpecificationInput(**data)
    data.update(
        tick_value_profit_per_lot=observation(), tick_value_loss_per_lot=observation(amount="11")
    )
    value = CfdSpecificationInput(**data)
    assert value.tick_value_profit_per_lot.amount != value.tick_value_loss_per_lot.amount
    # Observation currency need not be the instrument profit currency.
    data.update(profit_currency="JPY")
    assert CfdSpecificationInput(**data).tick_value_profit_per_lot.currency == "USD"


@pytest.mark.parametrize(
    ("profit", "loss", "message"),
    [
        (observation(), None, "both profit/loss"),
        (observation(), observation(currency="JPY"), "share currency"),
        (observation(), observation(observed_at="2025-01-02T00:00:00Z"), "observation time"),
        (observation(amount=0.1), observation(), "floats/bools"),
        (observation(amount="-1"), observation(), "greater than 0"),
    ],
)
def test_inconsistent_tick_values(profit, loss, message):
    data = example()["snapshot"]["specification"]
    data.update(tick_value_profit_per_lot=profit, tick_value_loss_per_lot=loss)
    with pytest.raises(ValidationError, match=message):
        CfdSpecificationInput(**data)


def test_pip_observations_need_currency_time_and_exact_amount():
    data = example()["snapshot"]["specification"]
    for invalid in (
        observation(currency="usd"),
        observation(amount=0.1),
        observation(observed_at="2025-01-03T00:00:00Z"),
    ):
        data["pip_value_per_lot"] = invalid
        with pytest.raises(ValidationError):
            CfdSpecificationInput(**data)
    data["pip_value_per_lot"] = observation(currency="EUR")
    assert CfdSpecificationInput(**data).pip_value_per_lot.currency == "EUR"


def test_snapshot_tampering_and_missing_identity_are_rejected():
    data = example()["snapshot"]
    data["specification"]["contract_size"] = "50000"
    with pytest.raises(ValidationError, match="fingerprint"):
        CfdSnapshotInput(**data)
    data = example()["snapshot"]
    del data["snapshot_id"]
    with pytest.raises(ValidationError, match="Field required"):
        CfdSnapshotInput(**data)


def test_nested_snapshots_are_frozen_and_changes_require_new_inputs():
    original = example()
    value = CfdSnapshotInput(**original["snapshot"])
    with pytest.raises(ValidationError, match="frozen"):
        value.specification.contract_size = Decimal("1")
    with pytest.raises(ValidationError, match="frozen"):
        value.specification.source.reference = "replacement"
    with pytest.raises(ValidationError, match="frozen"):
        value.snapshot_id = "replacement"
    revised = deepcopy(original)
    revised["snapshot"]["specification"]["contract_size"] = "50000"
    revised["snapshot"]["snapshot_id"] = "synthetic-new-snapshot"
    refresh_snapshot(revised)
    assert CfdSnapshotInput(**revised["snapshot"]) != value
    assert value.specification.contract_size == Decimal("100000")
