"""Initial local-personal saves only; all ten ledger tables commit atomically."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.cfd_errors import CfdProblem
from app.models.cfd import TABLES
from app.schemas.cfd_personal import CfdPersonalPage
from app.schemas.cfd_positions import CfdPositionResult
from app.schemas.cfd_reads import OriginalRiskV1
from app.services import cfd_cursor
from app.services.cfd_integrity import instant
from app.services.cfd_personal_codec import (
    CANONICALIZER,
    POLICY,
    canonical,
    digest,
    financial_text,
    input_text,
    make_evidence_envelope,
    normalize,
    result_text,
)
from app.services.cfd_personal_integrity import verify_record
from app.services.cfd_preview import bind_preview
from app.services.cfd_records import account_scope, published


def conflict():
    raise CfdProblem(
        409, "submission_conflict", "This request conflicts with an existing submission."
    )


def read_position(session, account_id, position_id):
    root, chain = published(session, account_id, position_id)
    if len(chain) != 1 or chain[0]["revision_no"] != 1:
        raise CfdProblem(409, "unsupported_evidence", "This historical CFD schema is unavailable.")
    return verify_record(session, root, chain[0])


def position_page(session, account_id, limit=50, cursor=None, key=b"personal-test-cursor-key"):
    account_scope(session, account_id)
    if not 1 <= limit <= 100:
        raise CfdProblem(422, "invalid_query", "Page limit must be from 1 to 100.")
    root, head = TABLES["cfd_positions"], TABLES["cfd_position_heads"]
    scope = dict(kind="personal_positions", account_id=account_id, position_id=None, limit=limit)
    query = (
        select(root)
        .join(head, head.c.position_id == root.c.id)
        .where(root.c.account_id == account_id)
    )
    if cursor:
        last = cfd_cursor.decode(key, scope, cursor)
        try:
            if (
                not isinstance(last, list)
                or len(last) != 2
                or instant(last[0]) != last[0]
                or str(UUID(last[1])) != last[1]
            ):
                raise ValueError
        except (ValueError, TypeError, AttributeError):
            raise CfdProblem(
                400, "invalid_cursor", "Invalid cursor; reload the first page."
            ) from None
        query = query.where(
            or_(
                root.c.created_at > last[0], and_(root.c.created_at == last[0], root.c.id > last[1])
            )
        )
    rows = (
        session.execute(query.order_by(root.c.created_at, root.c.id).limit(limit + 1))
        .mappings()
        .all()
    )
    items, response_bytes = [], 0
    for row in rows[:limit]:
        record = read_position(session, account_id, row["id"])
        response_bytes += len(record.model_dump_json().encode("utf-8"))
        if response_bytes > 32 * 1024 * 1024:
            raise CfdProblem(413, "page_too_large", "Request a smaller page of CFD evidence.")
        items.append(record)
    next_cursor = (
        cfd_cursor.encode(key, scope, [rows[limit - 1]["created_at"], rows[limit - 1]["id"]])
        if len(rows) > limit
        else None
    )
    return CfdPersonalPage(account_id=account_id, items=items, next_cursor=next_cursor)


def command_hash(command):
    raw = command.model_dump(mode="python")
    raw["position_reference"], raw["snapshot_id"] = (
        str(command.position_reference),
        str(command.snapshot_id),
    )
    raw = normalize(raw)
    for name, id_name in (("adjustments", "adjustment_id"), ("conversions", "conversion_id")):
        raw["trade"][name].sort(key=lambda row: row[id_name])
    raw["broker_evidence"].sort(key=lambda row: row["evidence_id"])
    raw["rounding"]["currencies"].sort(key=lambda row: row["currency"])
    return digest(canonical(raw))


def receipt(session, account_id, key, expected):
    row = (
        session.execute(
            select(TABLES["cfd_requests"]).filter_by(account_id=account_id, idempotency_key=key)
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    if (
        row["request_sha256"] != expected
        or row["operation"] != "create"
        or row["request_schema_version"] != "cfd-api-command-v1"
    ):
        conflict()
    record = read_position(session, account_id, row["resource_id"])
    if (
        row["revision_id"] != str(record.revision_id)
        or row["response_status"] != 201
        or row["response_body"] != canonical(record.model_dump(mode="json"))
    ):
        raise CfdProblem(
            409, "integrity_failure", "The saved submission receipt failed verification."
        )
    return record


def _inject(stage, requested):
    if stage == requested:
        raise RuntimeError("Injected disposable save failure: " + stage)


def _insert(session, name, **values):
    session.execute(TABLES[name].insert().values(**values))


def _save_rows(session, request, result, runtime, now, *, fail_at=None):
    trade, snapshot, account = request.trade, request.trade.snapshot, request.trade.account
    spec, position_id, revision_id = (
        snapshot.specification,
        request.position_reference,
        str(uuid4()),
    )
    account_json = financial_text(account)
    risk_fx = next(
        (fx for fx in trade.conversions if fx.conversion_id == trade.risk_conversion_id), None
    )
    risk = OriginalRiskV1(
        account_sha256=digest(account_json),
        snapshot_sha256=snapshot.content_sha256,
        direction=trade.direction,
        entry=trade.entry,
        original_stop=trade.original_stop,
        rounding=request.rounding,
        reporting_policy=trade.reporting_policy,
        recognition_policy=request.recognition_policy,
        risk_conversion_id=trade.risk_conversion_id,
        risk_conversion=risk_fx,
        native=result.native.original_planned_risk,
        reporting=result.reporting.original_planned_risk,
    )
    risk_json = financial_text(risk)
    entry = normalize(trade.entry.model_dump(mode="python"))
    _insert(
        session,
        "cfd_positions",
        id=position_id,
        account_id=account.account_id,
        broker=account.broker,
        settlement_currency=account.settlement_currency,
        snapshot_id=snapshot.snapshot_id,
        instrument_id=spec.instrument_id,
        platform=account.platform,
        server=account.server,
        venue=spec.venue,
        product=spec.product,
        snapshot_sha256=snapshot.content_sha256,
        account_contract=account_json,
        account_sha256=digest(account_json),
        direction=trade.direction,
        original_entry_id=entry["execution_id"],
        entry_at=entry["executed_at"],
        entry_price=entry["price"],
        original_lots=entry["lots"],
        original_stop=normalize(trade.original_stop),
        original_risk_basis=risk_json,
        original_risk_sha256=digest(risk_json),
        source=canonical(
            {
                "kind": "local_personal",
                "input_kind": "synthetic_practice",
                "broker_authenticated": False,
            }
        ),
        created_at=now,
    )
    _insert(
        session,
        "cfd_revisions",
        id=revision_id,
        position_id=position_id,
        account_id=account.account_id,
        revision_no=1,
        parent_revision_id=None,
        operation="create",
        lifecycle="active",
        reason="Initial local-personal practice submission",
        notes=None,
        planned_take_profit=normalize(trade.planned_take_profit),
        as_of=instant(request.as_of),
        reporting_policy=trade.reporting_policy,
        recognition_policy=request.recognition_policy,
        rounding_policy=financial_text(request.rounding),
        changed_event_ids="{}",
        request_schema_version=request.schema_version,
        created_at=now,
        sealed_at=None,
    )
    groups = (
        ("execution", (trade.entry, *trade.exits), "execution_id", "cfd_executions"),
        ("conversion", trade.conversions, "conversion_id", "cfd_conversions"),
        ("adjustment", trade.adjustments, "adjustment_id", "cfd_adjustments"),
        ("evidence", request.broker_evidence, "evidence_id", "cfd_broker_evidence"),
    )
    for kind, rows, id_field, table in groups:
        for item in rows:
            _insert(
                session,
                "cfd_event_keys",
                account_id=account.account_id,
                kind=kind,
                event_id=getattr(item, id_field),
                position_id=position_id,
                first_revision_no=1,
                created_at=now,
            )
    # FX precedes executions; executions precede their linked costs.
    for kind, rows, id_field, table in (groups[1], groups[0], groups[2], groups[3]):
        for ordinal, item in enumerate(rows):
            raw = normalize(item.model_dump(mode="python"))
            if "source" in raw:
                raw["source"] = canonical(raw["source"])
            if kind == "execution":
                raw.update(role="entry" if ordinal == 0 else "exit", ordinal=ordinal)
            raw.update(
                revision_id=revision_id,
                position_id=position_id,
                account_id=account.account_id,
                event_kind=kind,
            )
            _insert(session, table, **raw)
    _inject("children", fail_at)
    envelope = canonical(make_evidence_envelope(runtime, now))
    inputs, results = input_text(request), result_text(result)
    _insert(
        session,
        "cfd_calculations",
        revision_id=revision_id,
        position_id=position_id,
        snapshot_sha256=snapshot.content_sha256,
        original_risk_sha256=digest(risk_json),
        canonical_input=inputs,
        input_sha256=digest(inputs),
        canonical_result=results,
        result_sha256=digest(results),
        engine_id=result.engine,
        engine_build_sha256=runtime.build_sha256,
        policy_version=POLICY,
        canonicalizer_version=CANONICALIZER,
        manifest=envelope,
        manifest_sha256=digest(envelope),
        calculated_at=now,
    )
    _inject("calculation", fail_at)
    session.execute(
        TABLES["cfd_revisions"]
        .update()
        .where(TABLES["cfd_revisions"].c.id == revision_id)
        .values(sealed_at=now)
    )
    _inject("sealed", fail_at)
    _insert(
        session,
        "cfd_position_heads",
        position_id=position_id,
        revision_id=revision_id,
        revision_no=1,
        row_version=1,
        updated_at=now,
    )
    _inject("head", fail_at)
    return read_position(session, account.account_id, position_id)


def create_position(workspace, runtime, command, idempotency_key, *, fail_at=None):
    try:
        if str(UUID(idempotency_key)) != idempotency_key:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise CfdProblem(
            400, "invalid_idempotency_key", "Supply a lowercase UUID Idempotency-Key."
        ) from None
    expected = command_hash(command)
    with workspace.read_session() as session:
        previous = receipt(session, command.account_id, idempotency_key, expected)
        if previous is not None:
            return previous
        request = bind_preview(session, command)
    if command.release_digest != runtime.release_digest:
        raise CfdProblem(
            409,
            "release_mismatch",
            "Preview this draft using the selected local release before saving.",
        )
    # calculate verifies the complete release before AND after its bounded worker;
    # the evidence-envelope builder verifies it again immediately before insertion.
    result = runtime.calculate(request, purpose="accept_save")
    if not isinstance(result, CfdPositionResult):
        raise CfdProblem(
            422,
            "calculation_unavailable",
            "Required financial evidence is unavailable; nothing was saved.",
        )
    try:
        with workspace.write_session() as session:
            previous = receipt(session, command.account_id, idempotency_key, expected)
            if previous is not None:
                return previous
            # Identity and snapshot evidence must still match after acquiring the write lock.
            current = bind_preview(session, command)
            if input_text(current) != input_text(request):
                conflict()
            now = instant(datetime.now(timezone.utc))
            record = _save_rows(session, request, result, runtime, now, fail_at=fail_at)
            _insert(
                session,
                "cfd_requests",
                id=str(uuid4()),
                account_id=command.account_id,
                idempotency_key=idempotency_key,
                operation="create",
                resource_id=str(record.position_id),
                revision_id=str(record.revision_id),
                request_sha256=expected,
                request_schema_version=command.schema_version,
                response_status=201,
                response_body=canonical(record.model_dump(mode="json")),
                created_at=now,
            )
            _inject("receipt", fail_at)
            _inject("before_commit", fail_at)
            return record
    except IntegrityError:
        conflict()
    except OperationalError:
        raise CfdProblem(
            503, "database_busy", "No save was accepted. Retry with the same submission key."
        ) from None
