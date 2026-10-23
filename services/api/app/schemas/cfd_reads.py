"""B3B-R responses expose preserved synthetic evidence, never accepted saves."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from app.schemas.cfd import CfdExecutionInput
from app.schemas.cfd_positions import CfdPositionRequest, CfdPositionResult
from app.schemas.cfd_results import CfdRoundingPolicy, MoneyResult
from app.schemas.financial import (
    CurrencyConversionInput,
    FinancialContract,
    PositiveFinancialDecimal,
    ZonedTime,
)
from app.schemas.instrument import Identifier

Sha = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class OriginalRiskV1(FinancialContract):
    schema_version: Literal["cfd-risk-anchor-v1"] = "cfd-risk-anchor-v1"
    account_sha256: Sha
    snapshot_sha256: Sha
    direction: Literal["buy", "sell"]
    entry: CfdExecutionInput
    original_stop: PositiveFinancialDecimal | None
    rounding: CfdRoundingPolicy
    reporting_policy: Literal["native_only", "explicit_rates"]
    recognition_policy: Literal["incurred_once"]
    risk_conversion_id: Identifier | None
    risk_conversion: CurrencyConversionInput | None
    native: MoneyResult
    reporting: MoneyResult


class ReadIntegrity(FinancialContract):
    stored_hashes: Literal["verified"] = "verified"
    normalized_input: Literal["verified"] = "verified"
    original_risk: Literal["verified"] = "verified"
    result_correspondence: Literal["structural_checks_only"] = "structural_checks_only"
    financial_recalculation: Literal["not_performed"] = "not_performed"


class ReadProvenance(FinancialContract):
    kind: Literal["synthetic_fixture"] = "synthetic_fixture"
    accepted_calculation: Literal[False] = False
    broker_authenticated: Literal[False] = False


class ReadReplay(FinancialContract):
    status: Literal["not_run"] = "not_run"
    availability: Literal["runtime_unavailable"] = "runtime_unavailable"


class CfdReadResponseV1(FinancialContract):
    schema_version: Literal["cfd-read-response-v1"] = "cfd-read-response-v1"
    position_id: UUID
    account_id: Identifier
    revision_id: UUID
    revision_no: Annotated[int, Field(strict=True, ge=1)]
    current_revision_no: Annotated[int, Field(strict=True, ge=1)]
    historical: bool
    lifecycle: Literal["active", "archived", "void"]
    created_at: ZonedTime
    input: CfdPositionRequest
    result: CfdPositionResult
    original_risk_basis: OriginalRiskV1
    input_sha256: Sha
    result_sha256: Sha
    manifest_sha256: Sha
    original_risk_sha256: Sha
    canonicalizer_version: Literal["synthetic-read-json-v1"] = "synthetic-read-json-v1"
    manifest: dict
    integrity: ReadIntegrity = ReadIntegrity()
    provenance: ReadProvenance = ReadProvenance()
    replay: ReadReplay = ReadReplay()


class CfdReadSummary(FinancialContract):
    position_id: UUID
    account_id: Identifier
    revision_id: UUID
    revision_no: int
    created_at: ZonedTime
    symbol: str
    state: Literal["open", "partial", "closed"]
    lifecycle: Literal["active", "archived", "void"]
    native_net: MoneyResult
    reporting_net: MoneyResult
    integrity: ReadIntegrity = ReadIntegrity()
    provenance: ReadProvenance = ReadProvenance()


class CfdRevisionSummary(FinancialContract):
    revision_id: UUID
    revision_no: int
    historical: bool
    as_of: ZonedTime
    lifecycle: Literal["active", "archived", "void"]
    result_sha256: Sha
    integrity: ReadIntegrity = ReadIntegrity()
    provenance: ReadProvenance = ReadProvenance()


class CfdPositionPage(FinancialContract):
    schema_version: Literal["cfd-position-page-v1"] = "cfd-position-page-v1"
    account_id: Identifier
    items: tuple[CfdReadSummary, ...]
    next_cursor: str | None


class CfdRevisionPage(FinancialContract):
    schema_version: Literal["cfd-revision-page-v1"] = "cfd-revision-page-v1"
    account_id: Identifier
    position_id: UUID
    items: tuple[CfdRevisionSummary, ...]
    next_cursor: str | None


class CfdReadQuery(FinancialContract):
    account_id: Identifier
    limit: Annotated[int, Field(ge=1, le=100)] = 50
    cursor: Annotated[str, Field(min_length=1, max_length=800)] | None = None
