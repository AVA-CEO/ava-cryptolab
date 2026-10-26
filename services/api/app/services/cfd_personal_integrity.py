"""Verify retained local-personal evidence without a calculator or release runtime."""

from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy import func, select

from app.models import InstrumentSnapshot, JournalAccount
from app.models.cfd import TABLES
from app.schemas.account import AccountContract
from app.schemas.cfd_personal import CfdPersonalRead
from app.schemas.cfd_positions import CfdPositionRequest, CfdPositionResult
from app.schemas.cfd_reads import OriginalRiskV1
from app.services.cfd_integrity import _correspondence, _financial_strings, instant, lineage
from app.services.cfd_personal_codec import (
    CANONICALIZER,
    POLICY,
    document,
    input_text,
    verify_evidence_envelope,
)
from app.services.cfd_read_codec import MAX_EVIDENCE_BYTES, corrupt, unsupported
from app.services.cfd_read_rows import reconstruct
from app.services.management import account_contract
from app.services.multi_asset import load_snapshot


def _verify(session, root, revision):
    chain = lineage(session, root)
    if len(chain) != 1 or chain[0]["id"] != revision["id"]:
        unsupported()
    if (
        revision["revision_no"] != 1
        or revision["operation"] != "create"
        or revision["lifecycle"] != "active"
        or revision["parent_revision_id"] is not None
        or revision["sealed_at"] is None
    ):
        corrupt()
    table = TABLES["cfd_calculations"]
    lengths = session.execute(
        select(
            func.length(table.c.canonical_input),
            func.length(table.c.canonical_result),
            func.length(table.c.manifest),
        ).filter_by(revision_id=revision["id"], position_id=root["id"])
    ).one_or_none()
    if lengths is None or any(n is None for n in lengths) or sum(lengths) > MAX_EVIDENCE_BYTES:
        corrupt()
    calc = (
        session.execute(select(table).filter_by(revision_id=revision["id"], position_id=root["id"]))
        .mappings()
        .one()
    )
    saved = document(calc["canonical_input"], calc["input_sha256"])
    result_raw = document(calc["canonical_result"], calc["result_sha256"])
    manifest = document(calc["manifest"], calc["manifest_sha256"])
    risk_raw = document(root["original_risk_basis"], root["original_risk_sha256"])
    software = manifest.get("software_release")
    if not isinstance(software, dict):
        corrupt()
    if (
        calc["canonicalizer_version"] != CANONICALIZER
        or calc["policy_version"] != POLICY
        or calc["engine_id"] != "cfd-position-v1"
        or revision["request_schema_version"] != "cfd-position-v1"
        or saved.get("schema_version") != "cfd-position-v1"
        or result_raw.get("engine") != "cfd-position-v1"
        or risk_raw.get("schema_version") != "cfd-risk-anchor-v1"
        or manifest.get("schema_version") != "ava-local-calculation-evidence-v1"
        or software.get("schema_version") != "ava-local-python-release-v1"
    ):
        unsupported()
    verified = verify_evidence_envelope(manifest, calc["engine_build_sha256"])
    build = verified["software_release"]["build"]
    if (
        build["canonicalizer_version"] != calc["canonicalizer_version"]
        or build["policy_version"] != calc["policy_version"]
        or build["contracts"]["engine_id"] != calc["engine_id"]
        or instant(calc["calculated_at"]) != calc["calculated_at"]
        or verified["execution"]["executed_at"] != calc["calculated_at"]
        or calc["calculated_at"] > revision["sealed_at"]
        or root["created_at"] != revision["created_at"]
        or revision["created_at"] != calc["calculated_at"]
    ):
        corrupt()
    if (calc["snapshot_sha256"], calc["original_risk_sha256"]) != (
        root["snapshot_sha256"],
        root["original_risk_sha256"],
    ):
        corrupt()
    source = document(root["source"])
    if (
        source
        != {
            "kind": "local_personal",
            "input_kind": "synthetic_practice",
            "broker_authenticated": False,
        }
        or verified["execution"]["input_provenance"] != "synthetic_example"
    ):
        corrupt()
    account = AccountContract.model_validate(
        document(root["account_contract"], root["account_sha256"])
    )
    current = session.get(JournalAccount, root["account_id"])
    if current is None or account.account_id != root["account_id"]:
        corrupt()
    actual = account_contract(current)
    for key in (
        "broker",
        "platform",
        "server",
        "reporting_currency",
        "settlement_currency",
        "broker_account_ref",
    ):
        if getattr(actual, key) != getattr(account, key):
            corrupt()
    spec = load_snapshot(session, root["snapshot_id"])
    snapshot_row = session.get(InstrumentSnapshot, root["snapshot_id"])
    if (
        snapshot_row is None
        or snapshot_row.content_sha256 != root["snapshot_sha256"]
        or spec.instrument_id != root["instrument_id"]
        or root["broker"] != spec.broker
        or root["broker"] != account.broker
        or root["platform"] != account.platform
        or root["server"] != account.server
        or root["venue"] != spec.venue
        or root["server"] != root["venue"]
        or root["product"] != spec.product
        or spec.product != "cfd"
        or root["settlement_currency"] != spec.settlement_currency
        or root["settlement_currency"] != account.settlement_currency
    ):
        corrupt()
    snapshot = dict(
        snapshot_id=snapshot_row.id,
        content_sha256=snapshot_row.content_sha256,
        specification=snapshot_row.specification,
    )
    raw = reconstruct(session, root, revision, snapshot, risk_raw)
    _financial_strings(raw)
    _financial_strings(result_raw)
    _financial_strings(risk_raw)
    request = CfdPositionRequest.model_validate(raw)
    if input_text(request) != calc["canonical_input"]:
        corrupt()
    result = CfdPositionResult.model_validate(result_raw)
    risk = OriginalRiskV1.model_validate(risk_raw)
    entry = request.trade.entry
    conversion = next(
        (
            item
            for item in request.trade.conversions
            if item.conversion_id == request.trade.risk_conversion_id
        ),
        None,
    )
    if (
        (
            root["original_entry_id"],
            root["entry_at"],
            Decimal(root["entry_price"]),
            Decimal(root["original_lots"]),
        )
        != (entry.execution_id, instant(entry.executed_at), entry.price, entry.lots)
        or risk.account_sha256 != root["account_sha256"]
        or risk.snapshot_sha256 != root["snapshot_sha256"]
        or risk.direction != request.trade.direction
        or risk.entry != entry
        or risk.original_stop != request.trade.original_stop
        or risk.rounding != request.rounding
        or risk.reporting_policy != request.trade.reporting_policy
        or risk.recognition_policy != request.recognition_policy
        or risk.risk_conversion_id != request.trade.risk_conversion_id
        or risk.risk_conversion != conversion
    ):
        corrupt()
    _correspondence(request, result, risk)
    return CfdPersonalRead(
        position_id=root["id"],
        account_id=root["account_id"],
        revision_id=revision["id"],
        revision_no=revision["revision_no"],
        created_at=root["created_at"],
        input=request,
        result=result,
        original_risk_basis=risk,
        input_sha256=calc["input_sha256"],
        result_sha256=calc["result_sha256"],
        original_risk_sha256=root["original_risk_sha256"],
        manifest_sha256=calc["manifest_sha256"],
        engine_build_sha256=calc["engine_build_sha256"],
        manifest=manifest,
    )


def verify_record(session, root, revision):
    """Read verification is independent of installed, active or revoked local software."""
    try:
        return _verify(session, root, revision)
    except (ValidationError, ValueError, KeyError, TypeError, ArithmeticError, RecursionError):
        corrupt()
