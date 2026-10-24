"""B3A transport contracts: references and exact inputs, never accepted saves."""

import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.cfd import CfdAdjustmentInput, CfdExecutionInput
from app.schemas.cfd_positions import CfdPositionResult, PositionUnavailable
from app.schemas.cfd_reconciliation import BrokerReportedValue
from app.schemas.cfd_results import CfdRoundingPolicy
from app.schemas.financial import (
    CurrencyConversionInput,
    FinancialContract,
    PositiveFinancialDecimal,
    ZonedTime,
)
from app.schemas.instrument import Identifier

FINANCIAL_FIELDS = {
    "price",
    "lots",
    "original_stop",
    "planned_take_profit",
    "amount",
    "rate",
    "original_lots",
    "exited_lots",
    "absolute_tolerance",
}
TIME_FIELDS = {"executed_at", "occurred_at", "observed_at", "applies_at", "as_of", "reported_at"}
ISO_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$")


def validate_wire(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FINANCIAL_FIELDS and item is not None:
                if not isinstance(item, str) or len(item) > 128:
                    raise ValueError(
                        "Financial values must be decimal strings of at most 128 characters"
                    )
            if key in TIME_FIELDS and (not isinstance(item, str) or not ISO_TIME.fullmatch(item)):
                raise ValueError(
                    "Use explicit ISO timezone timestamps with at most six fractional digits"
                )
            validate_wire(item)
    elif isinstance(value, list):
        for item in value:
            validate_wire(item)


class CfdTradeFields(FinancialContract):
    direction: Literal["buy", "sell"]
    entry: CfdExecutionInput
    exits: Annotated[tuple[CfdExecutionInput, ...], Field(max_length=1000)] = ()
    original_stop: PositiveFinancialDecimal | None = None
    planned_take_profit: PositiveFinancialDecimal | None = None
    adjustments: Annotated[tuple[CfdAdjustmentInput, ...], Field(max_length=1000)] = ()
    reporting_policy: Literal["native_only", "explicit_rates"]
    conversions: Annotated[tuple[CurrencyConversionInput, ...], Field(max_length=2001)] = ()
    risk_conversion_id: Identifier | None = None


class CfdPreviewCommandV1(FinancialContract):
    schema_version: Literal["cfd-api-command-v1"]
    account_id: Identifier
    snapshot_id: UUID
    position_reference: UUID
    trade: CfdTradeFields
    rounding: CfdRoundingPolicy
    as_of: ZonedTime
    recognition_policy: Literal["incurred_once"]
    broker_evidence: Annotated[tuple[BrokerReportedValue, ...], Field(max_length=100)] = ()
    release_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")] | None = None

    @model_validator(mode="before")
    @classmethod
    def exact_transport(cls, value):
        validate_wire(value)
        return value


class CfdStatusV1(FinancialContract):
    schema_version: Literal["cfd-status-v1"] = "cfd-status-v1"
    mode: Literal["local_cfd_practice"] = "local_cfd_practice"
    enabled: Literal[True] = True
    database_revision: Literal["0004"] = "0004"
    execution_kind: Literal["unavailable"] = "unavailable"
    approved_release: Literal[False] = False
    preview_available: Literal[False] = False
    can_create: Literal[False] = False
    can_read_saved_positions: Literal[True] = True
    read_provenance: Literal["synthetic_fixture_only"] = "synthetic_fixture_only"
    host_fallback: Literal[False] = False
    historical_replay: Literal["unverified"] = "unverified"
    postgresql: Literal["unverified"] = "unverified"
    blocked_reasons: tuple[Literal["calculation_runtime_unavailable"], ...] = (
        "calculation_runtime_unavailable",
    )


class CfdPreviewResponseV1(FinancialContract):
    """Reserved future response shape. No B3A runtime can produce it."""

    schema_version: Literal["cfd-preview-response-v1"] = "cfd-preview-response-v1"
    saved: Literal[False] = False
    position_reference: UUID
    result: CfdPositionResult | PositionUnavailable
    execution_kind: Literal["approved_container"]
    approved_release: Literal[True]
    release_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    can_create: Literal[False] = False


class CfdIssue(FinancialContract):
    path: str
    code: str
    message: str


class CfdLocalStatusV2(FinancialContract):
    schema_version: Literal["cfd-status-v2"] = "cfd-status-v2"
    execution_kind: Literal["local_personal"] = "local_personal"
    preview_available: Literal[True] = True
    can_create: Literal[False] = False
    release_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class CfdLocalPreviewV2(FinancialContract):
    schema_version: Literal["cfd-preview-response-v2"] = "cfd-preview-response-v2"
    saved: Literal[False] = False
    can_create: Literal[False] = False
    execution_kind: Literal["local_personal"] = "local_personal"
    signature_status: Literal["unsigned"] = "unsigned"
    accepted_calculation: Literal[False] = False
    broker_authenticated: Literal[False] = False
    release_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    result: CfdPositionResult | PositionUnavailable


class CfdError(FinancialContract):
    code: str
    message: str
    request_id: UUID
    issues: Annotated[tuple[CfdIssue, ...], Field(max_length=20)] = ()


class CfdErrorEnvelope(FinancialContract):
    error: CfdError
