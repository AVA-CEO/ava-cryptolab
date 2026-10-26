"""Strict local-personal software identity and per-execution evidence contracts."""

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Sha = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Reference = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
UtcText = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")]


class StrictRelease(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SourceIdentity(StrictRelease):
    repository_id: Literal["ava-cryptolab"]
    commit: Annotated[str, Field(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")]
    calculator_tree_sha256: Sha
    dirty: bool


class PlatformIdentity(StrictRelease):
    os: Literal["windows", "linux"]
    architecture: Literal["amd64", "arm64"]
    qualification_os_build: Annotated[str, Field(pattern=r"^[a-zA-Z0-9._+-]{1,100}$")]
    compatibility_policy: Literal["exact-recorded-environment-v1"]


class PythonIdentity(StrictRelease):
    implementation: Literal["CPython"]
    version: Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+$")]
    cache_tag: Annotated[str, Field(min_length=1, max_length=100)]
    executable_sha256: Sha
    runtime_inventory_sha256: Sha
    abi_tag: Annotated[str, Field(min_length=1, max_length=100)]


class PayloadIdentity(StrictRelease):
    format: Literal["zip"]
    archive_sha256: Sha
    archive_bytes: Annotated[int, Field(gt=0, le=128 * 1024 * 1024)]
    expanded_bytes: Annotated[int, Field(gt=0, le=256 * 1024 * 1024)]
    files_inventory_sha256: Sha
    worker_entry: Literal["worker/preview.py"]


class DependencyIdentity(StrictRelease):
    name: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{0,99}$")]
    version: Annotated[str, Field(min_length=1, max_length=100)]
    origin_kind: Literal["retained_installed_tree", "retained_wheel"]
    distribution_metadata_sha256: Sha
    installed_files_sha256: Sha
    retained_artifact_sha256: Sha


class ContractIdentity(StrictRelease):
    engine_id: Literal["cfd-position-v1"]
    input: Literal["cfd-position-v1"]
    result: Literal["cfd-position-result-v1"]
    risk: Literal["cfd-risk-anchor-v1"]
    snapshot: Literal["instrument-specification-v1"]


class DecimalIdentity(StrictRelease):
    prec: Literal[160]
    rounding: Literal["ROUND_HALF_EVEN"]
    Emin: Literal[-999999]
    Emax: Literal[999999]
    capitals: Literal[1]
    clamp: Literal[0]
    traps: list[Literal["DivisionByZero", "InvalidOperation", "Overflow"]]

    @field_validator("traps")
    @classmethod
    def exact_traps(cls, value):
        if value != ["DivisionByZero", "InvalidOperation", "Overflow"]:
            raise ValueError("Exact enabled Decimal traps required")
        return value


class LimitIdentity(StrictRelease):
    input_bytes: Literal[4194304]
    output_bytes: Literal[33554432]
    stderr_bytes: Literal[65536]
    execution_seconds: Literal[10]
    queue_wait_seconds: Literal[2]
    active_workers: Literal[1]
    queued_requests: Literal[2]
    api_seconds: Literal[30]


class QualificationIdentity(StrictRelease):
    golden_set_sha256: Sha
    expected_results_sha256: Sha
    report_sha256: Sha


class BuildIdentity(StrictRelease):
    descriptor_version: Literal["ava-local-python-build-v1"]
    source: SourceIdentity
    platform: PlatformIdentity
    python: PythonIdentity
    payload: PayloadIdentity
    dependencies: Annotated[list[DependencyIdentity], Field(min_length=1, max_length=30)]
    contracts: ContractIdentity
    canonicalizer_version: Literal["local-personal-json-v1"]
    policy_version: Literal["local-personal-incurred-once-v1"]
    decimal: DecimalIdentity
    limits: LimitIdentity
    supported_modes: dict[str, list[str]]
    qualification: QualificationIdentity

    @model_validator(mode="after")
    def exact_capabilities(self):
        expected = {
            "forex": ["forex"],
            "cfd_linear": ["metals", "indices", "energy", "equities", "other"],
            "cfd_index": ["indices"],
        }
        if self.supported_modes != expected:
            raise ValueError("Unsupported calculation capabilities")
        names = [item.name for item in self.dependencies]
        if names != [
            "annotated-types",
            "pydantic",
            "pydantic-core",
            "typing-extensions",
            "typing-inspection",
        ]:
            raise ValueError("Exact supported dependency closure required")
        return self


def utc_text(value):
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    if parsed.strftime("%Y-%m-%dT%H:%M:%S.%fZ") != value:
        raise ValueError("Canonical UTC timestamp required")
    return value


class LocalReleaseManifest(StrictRelease):
    schema_version: Literal["ava-local-python-release-v1"]
    release_id: Annotated[str, Field(pattern=r"^[\x21-\x7e]{1,100}$")]
    profile: Literal["local_personal"]
    execution_kind: Literal["host_pinned_python"]
    approval_scope: Literal["local_personal"]
    signature_status: Literal["unsigned"]
    created_at: UtcText
    build: BuildIdentity

    _time = field_validator("created_at")(utc_text)


class ExecutionEvidence(StrictRelease):
    profile: Literal["local_personal"]
    execution_kind: Literal["host_pinned_python"]
    purpose: Literal["accept_save"]
    release_digest: Reference
    build_sha256: Sha
    signature_status: Literal["unsigned"]
    registry_generation: Annotated[int, Field(gt=0)]
    approval_reference: Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,199}$")]
    approved_at: UtcText
    executed_at: UtcText
    input_provenance: Literal["synthetic_example", "user_supplied_unverified"]
    broker_authenticated: Literal[False]

    _times = field_validator("approved_at", "executed_at")(utc_text)

    @model_validator(mode="after")
    def ordered_times(self):
        if self.executed_at < self.approved_at:
            raise ValueError("Execution cannot precede local approval")
        return self


class CalculationEvidence(StrictRelease):
    schema_version: Literal["ava-local-calculation-evidence-v1"]
    software_release: LocalReleaseManifest
    release_manifest_sha256: Sha
    execution: ExecutionEvidence


class RegistryEntry(StrictRelease):
    profile: Literal["local_personal"]
    release_digest: Reference
    build_sha256: Sha
    release_manifest_sha256: Sha
    manifest_location: Annotated[str, Field(min_length=1, max_length=4096)]
    payload_location: Annotated[str, Field(min_length=1, max_length=4096)]
    runtime_root: Annotated[str, Field(min_length=1, max_length=4096)]
    state: Literal["active", "retired", "revoked"]
    purposes: Annotated[list[Literal["preview", "accept_save", "replay"]], Field(max_length=3)]
    approval_reference: Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,199}$")]
    approved_at: UtcText

    _time = field_validator("approved_at")(utc_text)

    @field_validator("purposes")
    @classmethod
    def unique_purposes(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Duplicate purposes")
        return value


class RegistryDecision(StrictRelease):
    sequence: Annotated[int, Field(gt=0)]
    release_digest: Reference
    old_state: Literal["active", "retired", "revoked"] | None
    new_state: Literal["active", "retired", "revoked"]
    old_purposes: Annotated[list[Literal["preview", "accept_save", "replay"]], Field(max_length=3)]
    purposes: Annotated[list[Literal["preview", "accept_save", "replay"]], Field(max_length=3)]
    at: UtcText
    approval_reference: Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,199}$")]

    _time = field_validator("at")(utc_text)


class ApprovalRegistry(StrictRelease):
    registry_version: Literal["ava-local-release-registry-v1"]
    generation: Annotated[int, Field(gt=0)]
    entries: Annotated[list[RegistryEntry], Field(min_length=1, max_length=1)]
    decisions: Annotated[list[RegistryDecision], Field(min_length=1, max_length=10000)]

    @model_validator(mode="after")
    def history(self):
        if self.generation != len(self.decisions):
            raise ValueError("Approval generation mismatch")
        state, purposes, previous_time = None, [], ""
        for sequence, decision in enumerate(self.decisions, 1):
            if (
                decision.sequence != sequence
                or decision.release_digest != self.entries[0].release_digest
                or decision.old_state != state
                or decision.old_purposes != purposes
                or len(decision.purposes) != len(set(decision.purposes))
                or decision.at < previous_time
            ):
                raise ValueError("Approval history mismatch")
            state, purposes, previous_time = decision.new_state, decision.purposes, decision.at
        entry, last = self.entries[0], self.decisions[-1]
        if (
            entry.state != state
            or entry.purposes != purposes
            or entry.approval_reference != last.approval_reference
            or entry.approved_at != last.at
        ):
            raise ValueError("Registry entry differs from decision history")
        return self
