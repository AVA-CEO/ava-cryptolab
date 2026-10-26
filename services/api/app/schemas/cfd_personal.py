"""Locally accepted practice evidence, distinct from synthetic read fixtures."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from app.schemas.cfd_positions import CfdPositionRequest, CfdPositionResult
from app.schemas.cfd_reads import OriginalRiskV1, ReadIntegrity, Sha
from app.schemas.financial import FinancialContract, ZonedTime
from app.schemas.instrument import Identifier


class PersonalProvenance(FinancialContract):
    kind: Literal["local_personal"] = "local_personal"
    input_kind: Literal["synthetic_practice"] = "synthetic_practice"
    accepted_calculation: Literal[True] = True
    broker_authenticated: Literal[False] = False
    signature_status: Literal["unsigned"] = "unsigned"
    approval: Literal["historical_local_approval"] = "historical_local_approval"


class PersonalReplay(FinancialContract):
    status: Literal["not_run"] = "not_run"
    availability: Literal["not_qualified"] = "not_qualified"


class CfdPersonalRead(FinancialContract):
    schema_version: Literal["cfd-personal-read-v1"] = "cfd-personal-read-v1"
    position_id: UUID
    account_id: Identifier
    revision_id: UUID
    revision_no: Literal[1] = 1
    created_at: ZonedTime
    input: CfdPositionRequest
    result: CfdPositionResult
    original_risk_basis: OriginalRiskV1
    input_sha256: Sha
    result_sha256: Sha
    original_risk_sha256: Sha
    manifest_sha256: Sha
    engine_build_sha256: Sha
    manifest: dict
    integrity: ReadIntegrity = ReadIntegrity()
    provenance: PersonalProvenance = PersonalProvenance()
    replay: PersonalReplay = PersonalReplay()


class CfdPersonalPage(FinancialContract):
    account_id: Identifier
    items: tuple[CfdPersonalRead, ...]
    next_cursor: str | None


class PersonalStatus(FinancialContract):
    schema_version: Literal["cfd-personal-status-v1"] = "cfd-personal-status-v1"
    execution_kind: Literal["local_personal"] = "local_personal"
    preview_available: Literal[True] = True
    can_create: Literal[True] = True
    release_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class PersonalPreview(FinancialContract):
    schema_version: Literal["cfd-personal-preview-v1"] = "cfd-personal-preview-v1"
    execution_kind: Literal["local_personal"] = "local_personal"
    saved: Literal[False] = False
    accepted_calculation: Literal[False] = False
    broker_authenticated: Literal[False] = False
    signature_status: Literal["unsigned"] = "unsigned"
    can_create: Literal[True] = True
    release_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    result: CfdPositionResult
