"""Synthetic SQL fixture builder only. NOT an application persistence service or API."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from app.analytics.cfd_positions import calculate_position
from app.models.cfd import TABLES
from app.schemas.cfd_positions import CfdPositionRequest
from app.services.multi_asset import load_snapshot, store_account, store_snapshot

AT = "2025-01-06T00:00:00.000000Z"


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def instant(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def prepare_scope(engine, raw=None):
    raw = raw or json.loads(
        (Path(__file__).parent / "fixtures/cfd-position-costs.synthetic.json").read_text()
    )
    # These collections are keyed evidence sets, not execution sequences.
    # Freeze their order before hashing; SQL row order is never an input contract.
    for name, key in [("conversions", "conversion_id"), ("adjustments", "adjustment_id")]:
        raw["trade"][name].sort(key=lambda item: item[key])
    raw.setdefault("broker_evidence", []).sort(key=lambda item: item["evidence_id"])
    with Session(engine) as session, session.begin():
        store_account(session, raw["trade"]["account"])
        row = store_snapshot(session, raw["trade"]["snapshot"]["specification"])
        raw["trade"]["snapshot"] = {
            "snapshot_id": row.id,
            "content_sha256": row.content_sha256,
            "specification": load_snapshot(session, row.id).model_dump(mode="json"),
        }
    return CfdPositionRequest.model_validate(raw)


def put(connection, table, values):
    connection.execute(insert(TABLES[table]), values)


def request_digest(request, number=1, operation=None):
    return digest(
        canon(
            {
                "request": request.model_dump(mode="json"),
                "operation": operation or ("create" if number == 1 else "amend"),
                "resource": request.position_reference,
                "expected_version": number - 1,
            }
        )
    )


def stage(
    connection,
    request,
    number=1,
    parent=None,
    *,
    publish=True,
    receipt=True,
    lifecycle="active",
    operation=None,
    fail_at=None,
    replaces=None,
):
    """Construct real rows to exercise DDL, without implementing B3 save behavior."""
    wire = request.model_dump(mode="json")
    trade = wire["trade"]
    root = request.position_reference
    revision = str(uuid5(NAMESPACE_URL, f"{root}:revision:{number}"))
    account = trade["account"]
    spec = trade["snapshot"]["specification"]
    result = calculate_position(request).model_dump(mode="json")
    assert result["status"] == "calculated"
    risk = canon(
        {
            "entry": trade["entry"],
            "stop": trade["original_stop"],
            "native": result["native"]["original_planned_risk"],
            "rounding": wire["rounding"],
            "reporting_policy": trade["reporting_policy"],
            "risk_conversion_id": trade["risk_conversion_id"],
            "risk_conversion": next(
                (
                    r
                    for r in trade["conversions"]
                    if r["conversion_id"] == trade["risk_conversion_id"]
                ),
                None,
            ),
        }
    )
    if number == 1:
        put(
            connection,
            "cfd_positions",
            dict(
                id=root,
                account_id=account["account_id"],
                broker=account["broker"],
                settlement_currency=account["settlement_currency"],
                snapshot_id=trade["snapshot"]["snapshot_id"],
                instrument_id=spec["instrument_id"],
                platform=account["platform"],
                server=account["server"],
                venue=spec["venue"],
                product=spec["product"],
                snapshot_sha256=trade["snapshot"]["content_sha256"],
                account_contract=canon(account),
                account_sha256=digest(canon(account)),
                direction=trade["direction"],
                original_entry_id=trade["entry"]["execution_id"],
                entry_at=instant(trade["entry"]["executed_at"]),
                entry_price=trade["entry"]["price"],
                original_lots=trade["entry"]["lots"],
                original_stop=trade["original_stop"],
                original_risk_basis=risk,
                original_risk_sha256=digest(risk),
                source=canon({"kind": "manual", "reference": "SYNTHETIC B2 fixture"}),
                created_at=AT,
                replaces_position_id=replaces,
            ),
        )
    put(
        connection,
        "cfd_revisions",
        dict(
            id=revision,
            position_id=root,
            account_id=account["account_id"],
            revision_no=number,
            parent_revision_id=parent,
            operation=operation or ("create" if number == 1 else "amend"),
            lifecycle=lifecycle,
            reason="Synthetic B2 rehearsal",
            notes=None,
            planned_take_profit=trade["planned_take_profit"],
            as_of=instant(wire["as_of"]),
            reporting_policy=trade["reporting_policy"],
            recognition_policy=wire["recognition_policy"],
            rounding_policy=canon(wire["rounding"]),
            changed_event_ids="[]",
            request_schema_version=wire["schema_version"],
            created_at=AT,
            sealed_at=None,
        ),
    )
    groups = [
        ("execution", [trade["entry"], *trade["exits"]], "execution_id"),
        ("adjustment", trade["adjustments"], "adjustment_id"),
        ("conversion", trade["conversions"], "conversion_id"),
        ("evidence", wire["broker_evidence"], "evidence_id"),
    ]
    for kind, items, key in groups:
        for item in items:
            identity = dict(account_id=account["account_id"], kind=kind, event_id=item[key])
            present = connection.execute(
                select(TABLES["cfd_event_keys"]).filter_by(**identity)
            ).first()
            if not present:
                put(
                    connection,
                    "cfd_event_keys",
                    dict(identity, position_id=root, first_revision_no=number, created_at=AT),
                )
    base = dict(revision_id=revision, position_id=root, account_id=account["account_id"])
    for item in trade["conversions"]:
        data = dict(item)
        data.update(
            observed_at=instant(data["observed_at"]),
            applies_at=instant(data["applies_at"]),
            source=canon(data["source"]),
        )
        put(connection, "cfd_conversions", dict(base, event_kind="conversion", **data))
    for ordinal, item in enumerate([trade["entry"], *trade["exits"]]):
        data = dict(item, executed_at=instant(item["executed_at"]))
        put(
            connection,
            "cfd_executions",
            dict(
                base,
                event_kind="execution",
                role="entry" if ordinal == 0 else "exit",
                ordinal=ordinal,
                **data,
            ),
        )
    for item in trade["adjustments"]:
        data = dict(item, occurred_at=instant(item["occurred_at"]), source=canon(item["source"]))
        put(connection, "cfd_adjustments", dict(base, event_kind="adjustment", **data))
    for item in wire["broker_evidence"]:
        data = dict(
            item,
            as_of=instant(item["as_of"]),
            reported_at=instant(item["reported_at"]),
            source=canon(item["source"]),
        )
        put(
            connection,
            "cfd_broker_evidence",
            dict(
                base, event_kind="evidence", **{k: v for k, v in data.items() if k != "account_id"}
            ),
        )
    if fail_at == "children":
        raise RuntimeError("Injected synthetic save failure")
    manifest = canon(
        {"test_only": True, "runtime": "existing-host-calculator", "not_a_release_artifact": True}
    )
    put(
        connection,
        "cfd_calculations",
        dict(
            revision_id=revision,
            position_id=root,
            snapshot_sha256=trade["snapshot"]["content_sha256"],
            original_risk_sha256=digest(risk),
            canonical_input=canon(wire),
            input_sha256=digest(canon(wire)),
            canonical_result=canon(result),
            result_sha256=digest(canon(result)),
            engine_id="cfd-position-v1",
            engine_build_sha256=digest(manifest),
            policy_version="incurred-once-v1",
            canonicalizer_version="synthetic-test-only",
            manifest=manifest,
            manifest_sha256=digest(manifest),
            calculated_at=AT,
        ),
    )
    connection.execute(
        update(TABLES["cfd_revisions"])
        .where(TABLES["cfd_revisions"].c.id == revision)
        .values(sealed_at=AT)
    )
    if fail_at == "sealed":
        raise RuntimeError("Injected synthetic save failure")
    if publish:
        head = dict(revision_id=revision, revision_no=number, row_version=number, updated_at=AT)
        if number == 1:
            put(connection, "cfd_position_heads", dict(position_id=root, **head))
        else:
            h = TABLES["cfd_position_heads"]
            assert (
                connection.execute(
                    update(h)
                    .where(h.c.position_id == root, h.c.row_version == number - 1)
                    .values(**head)
                ).rowcount
                == 1
            )
    if fail_at == "head":
        raise RuntimeError("Injected synthetic save failure")
    if receipt:
        put(
            connection,
            "cfd_requests",
            dict(
                id=str(uuid5(NAMESPACE_URL, f"{root}:receipt:{number}")),
                account_id=account["account_id"],
                idempotency_key=f"key-{number}",
                operation=operation or ("create" if number == 1 else "amend"),
                resource_id=root,
                revision_id=revision,
                request_sha256=request_digest(request, number, operation),
                request_schema_version=wire["schema_version"],
                response_status=201,
                response_body=canon({"revision_id": revision}),
                created_at=AT,
            ),
        )
    if fail_at == "receipt":
        raise RuntimeError("Injected synthetic save failure")
    return revision


def reload_request(connection, revision):
    """Rebuild inputs from normalized rows, not from the saved input envelope."""

    def rows(name):
        return [
            dict(r)
            for r in connection.execute(
                select(TABLES[name])
                .filter_by(revision_id=revision)
                .order_by(*TABLES[name].primary_key.columns)
            ).mappings()
        ]

    rev = (
        connection.execute(select(TABLES["cfd_revisions"]).filter_by(id=revision)).mappings().one()
    )
    root = (
        connection.execute(select(TABLES["cfd_positions"]).filter_by(id=rev["position_id"]))
        .mappings()
        .one()
    )
    snapshot = (
        connection.execute(select(TABLES["cfd_calculations"]).filter_by(revision_id=revision))
        .mappings()
        .one()
    )
    # Snapshot comes from immutable instrument storage, not the calculation's embedded copy.
    from app.models import InstrumentSnapshot

    s = (
        connection.execute(
            select(InstrumentSnapshot.__table__).where(InstrumentSnapshot.id == root["snapshot_id"])
        )
        .mappings()
        .one()
    )

    def strip(row, keys, json_keys=()):
        return {k: json.loads(row[k]) if k in json_keys else row[k] for k in keys}

    fills = sorted(rows("cfd_executions"), key=lambda r: r["ordinal"])
    trade = dict(
        account=json.loads(root["account_contract"]),
        snapshot=dict(
            snapshot_id=s["id"],
            content_sha256=s["content_sha256"],
            specification=s["specification"],
        ),
        direction=root["direction"],
        entry=strip(
            fills[0], ["execution_id", "executed_at", "price", "lots", "profit_conversion_id"]
        ),
        exits=[
            strip(r, ["execution_id", "executed_at", "price", "lots", "profit_conversion_id"])
            for r in fills[1:]
        ],
        original_stop=root["original_stop"],
        risk_conversion_id=json.loads(root["original_risk_basis"])["risk_conversion_id"],
        planned_take_profit=rev["planned_take_profit"],
        adjustments=[
            strip(
                r,
                [
                    "adjustment_id",
                    "kind",
                    "amount",
                    "currency",
                    "occurred_at",
                    "source",
                    "description",
                    "execution_id",
                    "conversion_id",
                ],
                ["source"],
            )
            for r in rows("cfd_adjustments")
        ],
        conversions=[
            strip(
                r,
                [
                    "conversion_id",
                    "from_currency",
                    "to_currency",
                    "rate",
                    "observed_at",
                    "applies_at",
                    "max_age_seconds",
                    "source",
                ],
                ["source"],
            )
            for r in rows("cfd_conversions")
        ],
        reporting_policy=rev["reporting_policy"],
    )
    evidence = [
        strip(
            r,
            [
                "evidence_id",
                "position_reference",
                "account_id",
                "instrument_id",
                "original_lots",
                "exited_lots",
                "state",
                "as_of",
                "reported_at",
                "basis",
                "recognition_policy",
                "metric",
                "amount",
                "currency",
                "comparison_basis",
                "absolute_tolerance",
                "source",
            ],
            ["source"],
        )
        for r in rows("cfd_broker_evidence")
    ]
    request = CfdPositionRequest(
        trade=trade,
        position_reference=root["id"],
        rounding=json.loads(rev["rounding_policy"]),
        as_of=rev["as_of"],
        recognition_policy=rev["recognition_policy"],
        broker_evidence=evidence,
    )
    assert digest(canon(request.model_dump(mode="json"))) == snapshot["input_sha256"]
    return request
