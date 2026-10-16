"""Comparison evidence, never a replacement for independently calculated PnL."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.cfd_results import MoneyResult
from app.schemas.financial import (
    FinancialContract,
    FinancialDecimal,
    FinancialSource,
    PositiveFinancialDecimal,
    SignedMoneyDecimal,
    ZonedTime,
)
from app.schemas.instrument import CurrencyCode, Identifier


class BrokerReportedValue(FinancialContract):
    evidence_id: Identifier
    position_reference: Identifier
    account_id: Identifier
    instrument_id: Identifier
    original_lots: PositiveFinancialDecimal | None = None
    exited_lots: Annotated[FinancialDecimal, Field(ge=0, le=Decimal("1e18"))] | None = None
    state: Literal["open", "partial", "closed"]
    as_of: ZonedTime
    reported_at: ZonedTime
    basis: Literal["native", "reporting"]
    recognition_policy: Literal["incurred_once", "other", "unknown"]
    metric: Literal["gross_pnl", "net_pnl", "adjustments", "commission", "swap", "fee", "other"]
    amount: SignedMoneyDecimal
    currency: CurrencyCode
    comparison_basis: Literal["raw", "display_rounded"]
    absolute_tolerance: Annotated[FinancialDecimal, Field(ge=0, le=Decimal("1e18"))]
    source: FinancialSource

    @model_validator(mode="after")
    def report_time(self):
        if self.reported_at < self.as_of:
            raise ValueError("Broker report cannot predate its declared financial cutoff.")
        return self


class BrokerComparison(FinancialContract):
    evidence: BrokerReportedValue
    status: Literal["within_tolerance", "difference", "unavailable"]
    calculated: MoneyResult
    difference: MoneyResult
    within_tolerance: bool | None
    unavailable_reason: str | None = None
