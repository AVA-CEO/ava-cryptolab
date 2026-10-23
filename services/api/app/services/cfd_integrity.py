"""Verify preserved evidence without importing or executing a financial calculator."""

from datetime import datetime, timezone
from decimal import Decimal, localcontext

from pydantic import ValidationError
from sqlalchemy import func, select

from app.models import InstrumentSnapshot, JournalAccount
from app.models.cfd import TABLES
from app.schemas.account import AccountContract
from app.schemas.cfd_api import validate_wire
from app.schemas.cfd_positions import CfdPositionRequest, CfdPositionResult
from app.schemas.cfd_reads import CfdReadResponseV1, OriginalRiskV1
from app.services.cfd_canonical import canonical_input
from app.services.cfd_read_codec import (
    CANONICALIZER,
    MANIFEST,
    MAX_EVIDENCE_BYTES,
    POLICY,
    corrupt,
    document,
    unsupported,
)
from app.services.cfd_read_rows import reconstruct
from app.services.management import account_contract
from app.services.multi_asset import load_snapshot


def instant(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def lineage(session, root):
    """Only the head's sealed ancestry is published, not every staged revision."""
    head = (
        session.execute(select(TABLES["cfd_position_heads"]).filter_by(position_id=root["id"]))
        .mappings()
        .one_or_none()
    )
    if head is None:
        return []
    number, key, chain = head["revision_no"], head["revision_id"], []
    if head["row_version"] != number or not 1 <= number <= 1000:
        corrupt()
    while number:
        row = (
            session.execute(
                select(TABLES["cfd_revisions"]).filter_by(
                    id=key, position_id=root["id"], account_id=root["account_id"]
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None or row["revision_no"] != number or row["sealed_at"] is None:
            corrupt()
        calculations = TABLES["cfd_calculations"]
        calc = (
            session.execute(
                select(
                    calculations.c.snapshot_sha256, calculations.c.original_risk_sha256
                ).filter_by(revision_id=row["id"], position_id=root["id"])
            )
            .mappings()
            .one_or_none()
        )
        if calc is None or (calc["snapshot_sha256"], calc["original_risk_sha256"]) != (
            root["snapshot_sha256"],
            root["original_risk_sha256"],
        ):
            corrupt()
        if any(instant(row[field]) != row[field] for field in ("created_at", "sealed_at", "as_of")):
            corrupt()
        if row["sealed_at"] < row["created_at"]:
            corrupt()
        if number == 1 and (row["parent_revision_id"] is not None or row["operation"] != "create"):
            corrupt()
        if number > 1 and row["operation"] not in {"amend", "archive", "restore", "void"}:
            corrupt()
        if row["lifecycle"] not in {"active", "archived", "void"}:
            corrupt()
        chain.append(row)
        key, number = row["parent_revision_id"], number - 1
    return chain


def _financial_strings(value):
    validate_wire(value)
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"raw", "rounded"} and item is not None and not isinstance(item, str):
                corrupt()
            _financial_strings(item)
    elif isinstance(value, list):
        for item in value:
            _financial_strings(item)


def _correspondence(request, result, risk):
    trade, spec = request.trade, request.trade.snapshot.specification
    fills = tuple(item for item in trade.exits if item.executed_at <= request.as_of)
    costs = tuple(item for item in trade.adjustments if item.occurred_at <= request.as_of)
    if (
        result.position_reference != request.position_reference
        or result.as_of != request.as_of
        or result.snapshot_id != trade.snapshot.snapshot_id
        or result.snapshot_sha256 != trade.snapshot.content_sha256
        or result.symbol != spec.symbol
        or result.native.currency != spec.profit_currency
        or result.reporting.currency != trade.account.reporting_currency
        or result.rounding_policy != request.rounding
        or result.recognition_policy != request.recognition_policy
        or result.reporting_policy != trade.reporting_policy
        or result.original_lots != trade.entry.lots
        or result.recognized_adjustments != costs
        or tuple(item.evidence for item in result.comparisons) != request.broker_evidence
        or result.native.original_planned_risk != risk.native
        or result.reporting.original_planned_risk != risk.reporting
        or result.unrealized_pnl.raw is not None
    ):
        corrupt()
    # Quantity and reference consistency checks only: no PnL, FX or R recalculation.
    with localcontext() as context:
        context.prec = 160
        exited = sum((item.lots for item in fills), Decimal(0))
        remaining = trade.entry.lots - exited
        state = "closed" if remaining == 0 else "partial" if exited else "open"
        if (result.exited_lots, result.remaining_lots, result.state) != (exited, remaining, state):
            corrupt()
        if result.eligible_for_closed_trade_statistics != (state == "closed"):
            corrupt()
        if len(result.exits) != len(fills):
            corrupt()
        remainder = trade.entry.lots
        for fill, saved in zip(fills, result.exits, strict=True):
            remainder -= fill.lots
            if (saved.execution_id, saved.executed_at, saved.lots, saved.remaining_lots_after) != (
                fill.execution_id,
                fill.executed_at,
                fill.lots,
                remainder,
            ) or (saved.native_gross.currency, saved.reporting_gross.currency) != (
                spec.profit_currency,
                trade.account.reporting_currency,
            ):
                corrupt()
    if result.deferred_execution_ids != tuple(
        item.execution_id for item in trade.exits if item.executed_at > request.as_of
    ) or result.deferred_adjustment_ids != tuple(
        item.adjustment_id for item in trade.adjustments if item.occurred_at > request.as_of
    ):
        corrupt()
    used = {item.profit_conversion_id for item in fills} | {item.conversion_id for item in costs}
    used.add(trade.risk_conversion_id)
    if result.conversion_evidence != tuple(
        item for item in trade.conversions if item.conversion_id in used
    ):
        corrupt()
    if [item.kind for item in result.cost_breakdown] != ["commission", "swap", "fee", "other"]:
        corrupt()
    if any(
        (item.native.currency, item.reporting.currency)
        != (spec.profit_currency, trade.account.reporting_currency)
        for item in result.cost_breakdown
    ):
        corrupt()
    if [item.currency for item in result.adjustments_by_currency] != sorted(
        {c.currency for c in costs}
    ):
        corrupt()


def _verify(session, root, revision, current_no):
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
    if (
        calc["canonicalizer_version"] != CANONICALIZER
        or calc["policy_version"] != POLICY
        or calc["engine_id"] != "cfd-position-v1"
        or revision["request_schema_version"] != "cfd-position-v1"
        or saved.get("schema_version") != "cfd-position-v1"
        or result_raw.get("engine") != "cfd-position-v1"
        or risk_raw.get("schema_version") != "cfd-risk-anchor-v1"
        or manifest.get("schema_version") != MANIFEST["schema_version"]
    ):
        unsupported()
    if manifest != MANIFEST or calc["engine_build_sha256"] != calc["manifest_sha256"]:
        corrupt()
    if (calc["snapshot_sha256"], calc["original_risk_sha256"]) != (
        root["snapshot_sha256"],
        root["original_risk_sha256"],
    ):
        corrupt()
    account = AccountContract.model_validate(
        document(root["account_contract"], root["account_sha256"])
    )
    current = session.get(JournalAccount, root["account_id"])
    if current is None or account.account_id != root["account_id"]:
        corrupt()
    actual = account_contract(current)
    identity = (
        "broker",
        "platform",
        "server",
        "reporting_currency",
        "settlement_currency",
        "broker_account_ref",
    )
    if any(getattr(actual, key) != getattr(account, key) for key in identity):
        corrupt()
    spec = load_snapshot(session, root["snapshot_id"])
    snapshot_row = session.get(InstrumentSnapshot, root["snapshot_id"])
    if (
        snapshot_row.content_sha256 != root["snapshot_sha256"]
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
    if canonical_input(request) != calc["canonical_input"]:
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
    return CfdReadResponseV1(
        position_id=root["id"],
        account_id=root["account_id"],
        revision_id=revision["id"],
        revision_no=revision["revision_no"],
        current_revision_no=current_no,
        historical=revision["revision_no"] != current_no,
        lifecycle=revision["lifecycle"],
        created_at=root["created_at"],
        input=request,
        result=result,
        original_risk_basis=risk,
        input_sha256=calc["input_sha256"],
        result_sha256=calc["result_sha256"],
        manifest_sha256=calc["manifest_sha256"],
        original_risk_sha256=root["original_risk_sha256"],
        manifest=manifest,
    )


def verify_record(session, root, revision, current_no):
    try:
        return _verify(session, root, revision, current_no)
    except (ValidationError, ValueError, KeyError, TypeError, ArithmeticError, RecursionError):
        corrupt()
