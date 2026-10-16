"""Input precision and explicit FX evidence, with no PnL calculations."""

from datetime import datetime, timezone
from decimal import Decimal, localcontext

import pytest
from cfd_examples import conversion
from pydantic import TypeAdapter, ValidationError

from app.schemas.financial import (
    CurrencyConversionInput,
    PositiveFinancialDecimal,
    SignedMoneyDecimal,
    ZonedTime,
    is_increment,
)


@pytest.mark.parametrize(
    "value", ["0.000000000000000001", "1000000000000000000", 1, Decimal("0.10")]
)
def test_exact_positive_boundaries_and_string_serialization(value):
    adapter = TypeAdapter(PositiveFinancialDecimal)
    result = adapter.validate_python(value)
    assert result == Decimal(value)
    assert adapter.validate_json(adapter.dump_json(result)) == result
    assert adapter.dump_json(result).startswith(b'"')


@pytest.mark.parametrize(
    "value",
    [
        0.1,
        1.0,
        True,
        False,
        "NaN",
        "sNaN",
        "Infinity",
        "-Infinity",
        "0",
        "-0",
        "-1",
        "1e-19",
        "1000000000000000001",
        None,
        [],
        {},
    ],
)
def test_invalid_exact_positive_amounts(value):
    with pytest.raises(ValidationError):
        TypeAdapter(PositiveFinancialDecimal).validate_python(value)


@pytest.mark.parametrize("value", ["-3.000000000000000001", "0", "2.5", "-1000000000000000000"])
def test_cash_flows_allow_debits_credits_and_explicit_zero(value):
    assert TypeAdapter(SignedMoneyDecimal).validate_python(value) == Decimal(value)


@pytest.mark.parametrize("value", ["-1000000000000000001", "0.0000000000000000001", 0.1, True])
def test_cash_flow_precision_and_bounds(value):
    with pytest.raises(ValidationError):
        TypeAdapter(SignedMoneyDecimal).validate_python(value)


def test_grid_validation_does_not_depend_on_global_decimal_precision():
    with localcontext() as context:
        context.prec = 6
        assert is_increment(Decimal("999999999999999999.99"), Decimal("0.01"))
        assert not is_increment(Decimal("0.015"), Decimal("0.01"))
        assert context.prec == 6


@pytest.mark.parametrize("value", ["2025-01-01T00:00:00", 1735689600, True, datetime(2025, 1, 1)])
def test_ambiguous_timestamps_are_rejected(value):
    with pytest.raises(ValidationError):
        TypeAdapter(ZonedTime).validate_python(value)


def test_zoned_time_normalizes_to_utc():
    assert TypeAdapter(ZonedTime).validate_python("2025-01-01T02:00:00+02:00") == datetime(
        2025, 1, 1, tzinfo=timezone.utc
    )


def test_fx_direction_and_precision_are_preserved_without_converting():
    value = CurrencyConversionInput(**conversion("fx", "2025-01-04T00:00:00Z"))
    assert value.rate == Decimal("0.0065")
    assert value.from_currency == "JPY" and value.to_currency == "USD"
    assert CurrencyConversionInput.model_validate_json(value.model_dump_json()) == value


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"to_currency": "JPY"}, "Same-currency"),
        ({"rate": "0"}, "greater than 0"),
        ({"rate": 0.0065}, "floats/bools"),
        ({"observed_at": "2025-01-04T00:00:01Z"}, "later than"),
        ({"observed_at": "2025-01-03T23:59:59Z"}, "allowed age"),
        ({"observed_at": "2025-01-03T23:59:59.999999Z"}, "allowed age"),
        ({"max_age_seconds": -1}, "greater than or equal"),
        ({"max_age_seconds": True}, "valid integer"),
        ({"max_age_seconds": 1.5}, "valid integer"),
        ({"from_currency": "jpy"}, "pattern"),
        ({"source": {"kind": "manual", "reference": " "}}, "at least 1"),
        ({"source": {"kind": "guessed", "reference": "x"}}, "Input should be"),
    ],
)
def test_invalid_conversion_evidence(changes, message):
    with pytest.raises(ValidationError, match=message):
        CurrencyConversionInput(**{**conversion("fx", "2025-01-04T00:00:00Z"), **changes})


def test_explicit_age_boundary_and_missing_rate_or_evidence():
    data = conversion("fx", "2025-01-04T00:00:00Z")
    data.update(observed_at="2025-01-03T23:59:00Z", max_age_seconds=60)
    CurrencyConversionInput(**data)
    for field in ("rate", "source", "observed_at", "applies_at", "max_age_seconds"):
        missing = {key: value for key, value in data.items() if key != field}
        with pytest.raises(ValidationError, match="Field required"):
            CurrencyConversionInput(**missing)
