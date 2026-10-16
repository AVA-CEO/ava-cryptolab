"""New management boundary reusing versioned identity/specification contracts."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, field_validator, model_validator

from app.schemas.account import AccountContract
from app.schemas.cfd_snapshot import CfdSpecificationInput
from app.schemas.financial import ZonedTime, is_increment
from app.schemas.instrument import ContractModel, CurrencyCode, Identifier, Instrument


class AccountCreate(ContractModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    broker: Identifier
    platform: Literal["manual", "bybit", "mt5"]
    server: Identifier | None = None
    broker_account_ref: Identifier | None = None
    reporting_currency: CurrencyCode
    settlement_currency: CurrencyCode

    @model_validator(mode="after")
    def approved_identity(self):
        AccountContract(account_id="validation-only", **self.model_dump())
        return self


def exact_payload(value):
    if isinstance(value, (float, bool)):
        raise ValueError("Use decimal strings for financial values, never floats or booleans.")
    if isinstance(value, dict):
        for nested in value.values():
            exact_payload(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            exact_payload(nested)


class SpecificationSubmission(ContractModel):
    specification: Instrument

    @field_validator("specification", mode="before")
    @classmethod
    def exact_wire_values(cls, value):
        if isinstance(value, ContractModel):
            value = value.model_dump()
        exact_payload(value)
        if isinstance(value, dict):
            source = value.get("source", {})
            if isinstance(source, dict):
                for field in ("effective_at", "captured_at"):
                    if field in source:
                        TypeAdapter(ZonedTime).validate_python(source[field])
        return value

    @model_validator(mode="after")
    def documented_specification(self):
        spec = self.specification
        if spec.source.kind not in {"manual", "statement"}:
            raise ValueError(
                "Record a manual/statement source; this application verifies no broker feed."
            )
        if not is_increment(spec.volume_min, spec.volume_step):
            raise ValueError("Minimum volume must align with the declared volume step.")
        if spec.product == "cfd":
            CfdSpecificationInput.model_validate(spec.model_dump())
        return self


class SnapshotReview(ContractModel):
    snapshot_id: str
    content_sha256: str
    created_at: datetime
    specification: Instrument
