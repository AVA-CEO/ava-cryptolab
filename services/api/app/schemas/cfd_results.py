"""Immutable calculator requests/results, independent of DB and broker SDKs."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, model_validator

from app.schemas.cfd import CfdTradeInput
from app.schemas.financial import CurrencyConversionInput, FinancialContract, exact_decimal
from app.schemas.instrument import CurrencyCode, Identifier

ResultDecimal = Annotated[Decimal, Field(allow_inf_nan=False), BeforeValidator(exact_decimal)]
Places = Annotated[int, Field(strict=True, ge=0, le=18)]


class CurrencyRounding(FinancialContract):
    currency: CurrencyCode
    decimal_places: Places


class CfdRoundingPolicy(FinancialContract):
    currencies: Annotated[tuple[CurrencyRounding, ...], Field(min_length=1, max_length=1002)]
    rounding: Literal["ROUND_HALF_EVEN", "ROUND_HALF_UP"]
    ratio_places: Places
    movement_places: Places

    @model_validator(mode="after")
    def distinct_currencies(self):
        if len({item.currency for item in self.currencies}) != len(self.currencies):
            raise ValueError("Each currency must have exactly one rounding definition.")
        return self


class CfdCalculationRequest(FinancialContract):
    schema_version: Literal["cfd-calculation-v1"] = "cfd-calculation-v1"
    trade: CfdTradeInput
    rounding: CfdRoundingPolicy


class Measurement(FinancialContract):
    raw: ResultDecimal | None
    rounded: ResultDecimal | None
    unavailable_reason: str | None = None

    @model_validator(mode="after")
    def value_or_reason(self):
        if (self.raw is None) != (self.rounded is None):
            raise ValueError("Raw and rounded values must be available together.")
        if (self.raw is None) != (self.unavailable_reason is not None):
            raise ValueError("Unavailable values require a reason; available values have none.")
        return self


class MoneyResult(Measurement):
    currency: CurrencyCode


class ScalarResult(Measurement):
    unit: Literal["price", "pips", "ticks", "R"]


class CurrencyPerformance(FinancialContract):
    currency: CurrencyCode
    gross_pnl: MoneyResult
    adjustments: MoneyResult
    net_pnl: MoneyResult
    original_planned_risk: MoneyResult
    realized_r: ScalarResult
    outcome: Literal["win", "loss", "breakeven", "unavailable"]

    @model_validator(mode="after")
    def labelled_amounts(self):
        values = (self.gross_pnl, self.adjustments, self.net_pnl, self.original_planned_risk)
        if any(item.currency != self.currency for item in values):
            raise ValueError("All money in a performance group must use its declared currency.")
        if self.realized_r.unit != "R":
            raise ValueError("Realized R must be labelled in R units.")
        return self


class CfdCalculationResult(FinancialContract):
    status: Literal["calculated"] = "calculated"
    engine: Literal["cfd-linear-v1"] = "cfd-linear-v1"
    precision_digits: Literal[160] = 160
    symbol: str
    calculation_mode: Literal["forex", "cfd_linear", "cfd_index"]
    snapshot_id: Identifier
    snapshot_sha256: str
    direction: Literal["buy", "sell"]
    entry_price: ResultDecimal
    exit_price: ResultDecimal
    lots: ResultDecimal
    contract_size: ResultDecimal
    signed_price_change: ScalarResult
    pips: ScalarResult
    ticks: ScalarResult
    native: CurrencyPerformance
    reporting: CurrencyPerformance
    adjustments_by_currency: tuple[MoneyResult, ...]
    conversion_evidence: tuple[CurrencyConversionInput, ...]
    reporting_policy: Literal["native_only", "explicit_rates"]
    rounding_policy: CfdRoundingPolicy


class InputIssue(FinancialContract):
    path: str
    message: str


class CalculationUnavailable(FinancialContract):
    status: Literal["unavailable"] = "unavailable"
    engine: Literal["cfd-linear-v1", "product-dispatch-v1"] = "cfd-linear-v1"
    reason_code: Literal[
        "invalid_input",
        "unsupported_product",
        "unsupported_mode",
        "unsupported_position",
        "missing_currency_precision",
        "numeric_error",
    ]
    message: str
    issues: tuple[InputIssue, ...] = ()
