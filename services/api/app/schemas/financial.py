"""Exact, immutable financial inputs. No pricing, FX lookup or database access."""

from datetime import datetime, timedelta
from decimal import Decimal, localcontext
from typing import Annotated, Literal

from pydantic import AfterValidator, BeforeValidator, ConfigDict, Field, model_validator

from app.schemas.instrument import ContractModel, CurrencyCode, Identifier, aware_utc


def exact_decimal(value):
    # A float may already have lost precision before validation sees it.
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError(
            "Use decimal text, an integer or Decimal; floats/bools are not exact inputs."
        )
    return value


FinancialDecimal = Annotated[
    Decimal,
    Field(max_digits=38, decimal_places=18, allow_inf_nan=False),
    BeforeValidator(exact_decimal),
]
PositiveFinancialDecimal = Annotated[FinancialDecimal, Field(gt=0, le=Decimal("1e18"))]
SignedMoneyDecimal = Annotated[FinancialDecimal, Field(ge=Decimal("-1e18"), le=Decimal("1e18"))]


def explicit_time(value):
    if not isinstance(value, (str, datetime)):
        raise ValueError("Use an ISO timestamp with timezone or a timezone-aware datetime.")
    return value


ZonedTime = Annotated[datetime, BeforeValidator(explicit_time), AfterValidator(aware_utc)]


class FinancialContract(ContractModel):
    model_config = ConfigDict(revalidate_instances="always", validate_default=True)


def is_increment(value: Decimal, step: Decimal) -> bool:
    """Exact grid check, independent of the caller's Decimal context precision."""
    with localcontext() as context:
        context.prec = 80
        return value % step == 0


class FinancialSource(FinancialContract):
    kind: Literal["manual", "statement", "broker_api", "terminal"]
    reference: Annotated[str, Field(min_length=1, max_length=200)]


class CurrencyConversionInput(FinancialContract):
    """Rate means target units per ONE source unit, never an implicit inverse.

    The caller explicitly chooses the allowed observation age; validation does
    not establish that a source or the quoted market rate is authentic.
    """

    conversion_id: Identifier
    from_currency: CurrencyCode
    to_currency: CurrencyCode
    rate: PositiveFinancialDecimal
    observed_at: ZonedTime
    applies_at: ZonedTime
    max_age_seconds: Annotated[int, Field(strict=True, ge=0, le=31_536_000)]
    source: FinancialSource

    @model_validator(mode="after")
    def explicit_direction_and_time(self):
        if self.from_currency == self.to_currency:
            raise ValueError("Same-currency amounts need no FX conversion; omit this observation.")
        age = self.applies_at - self.observed_at
        if age < timedelta(0):
            raise ValueError(
                "A conversion observation cannot be later than the amount it converts."
            )
        if age > timedelta(seconds=self.max_age_seconds):
            raise ValueError("Conversion observation exceeds its explicitly allowed age.")
        return self
