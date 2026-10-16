"""Position ledger requests/results; no persistence or journal API changes."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.cfd import CfdAdjustmentInput, CfdTradeInput
from app.schemas.cfd_reconciliation import BrokerComparison, BrokerReportedValue
from app.schemas.cfd_results import (
    CalculationUnavailable,
    CfdRoundingPolicy,
    CurrencyPerformance,
    MoneyResult,
    ResultDecimal,
)
from app.schemas.financial import CurrencyConversionInput, FinancialContract, ZonedTime
from app.schemas.instrument import Identifier


class PositionUnavailable(CalculationUnavailable):
    engine: Literal["cfd-position-v1"] = "cfd-position-v1"


class CfdPositionRequest(FinancialContract):
    schema_version: Literal["cfd-position-v1"] = "cfd-position-v1"
    position_reference: Identifier
    trade: CfdTradeInput
    rounding: CfdRoundingPolicy
    as_of: ZonedTime
    recognition_policy: Literal["incurred_once"]
    broker_evidence: Annotated[tuple[BrokerReportedValue, ...], Field(max_length=100)] = ()

    @model_validator(mode="after")
    def cutoff_and_evidence(self):
        if self.as_of < self.trade.entry.executed_at:
            raise ValueError("Position cutoff cannot precede entry.")
        if len({item.evidence_id for item in self.broker_evidence}) != len(self.broker_evidence):
            raise ValueError("Broker evidence IDs must be unique.")
        return self


class ExitRealization(FinancialContract):
    execution_id: Identifier
    executed_at: ZonedTime
    lots: ResultDecimal
    remaining_lots_after: ResultDecimal
    native_gross: MoneyResult
    reporting_gross: MoneyResult


class CostKindResult(FinancialContract):
    kind: Literal["commission", "swap", "fee", "other"]
    native: MoneyResult
    reporting: MoneyResult


class CfdPositionResult(FinancialContract):
    status: Literal["calculated"] = "calculated"
    engine: Literal["cfd-position-v1"] = "cfd-position-v1"
    precision_digits: Literal[160] = 160
    position_reference: Identifier
    as_of: ZonedTime
    state: Literal["open", "partial", "closed"]
    eligible_for_closed_trade_statistics: bool
    original_lots: ResultDecimal
    exited_lots: ResultDecimal
    remaining_lots: ResultDecimal
    symbol: str
    snapshot_id: Identifier
    snapshot_sha256: str
    recognition_policy: Literal["incurred_once"]
    reporting_policy: Literal["native_only", "explicit_rates"]
    native: CurrencyPerformance
    reporting: CurrencyPerformance
    unrealized_pnl: MoneyResult
    exits: tuple[ExitRealization, ...]
    recognized_adjustments: tuple[CfdAdjustmentInput, ...]
    deferred_execution_ids: tuple[Identifier, ...]
    deferred_adjustment_ids: tuple[Identifier, ...]
    adjustments_by_currency: tuple[MoneyResult, ...]
    cost_breakdown: tuple[CostKindResult, ...]
    conversion_evidence: tuple[CurrencyConversionInput, ...]
    rounding_policy: CfdRoundingPolicy
    comparisons: tuple[BrokerComparison, ...] = ()
