"""Adversarial fixtures ONLY: corrupt a newly minted DB before serving starts.

Removing triggers here simulates privileged tampering; no application guard or
historical migration is edited. All changes happen inside new fixture provisioning.
"""

import json
import re
from copy import deepcopy
from uuid import uuid4

from sqlalchemy import delete, insert, select, text, update

from app.models import InstrumentSnapshot, JournalAccount
from app.models.cfd import TABLES
from app.services.cfd_read_codec import canonical, digest


def attack(workspace, session, change):
    workspace.check_target(workspace.engine.url)
    assert not workspace.ready and session.get_bind().engine is workspace.engine
    # Deliberately bypass ONLY database triggers in this new adversarial fixture,
    # to exercise application verification even after an administrator alters SQL.
    names = (
        session.execute(text("SELECT name FROM sqlite_master WHERE type='trigger'")).scalars().all()
    )
    for name in names:
        assert re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", name)
        session.connection().exec_driver_sql(f'DROP TRIGGER "{name}"')
    ref = workspace.samples["read_catalog"][0]
    position = TABLES["cfd_positions"]
    revisions = TABLES["cfd_revisions"]
    calculations = TABLES["cfd_calculations"]
    root = session.execute(select(position).filter_by(id=ref["position_id"])).mappings().one()
    revision = (
        session.execute(select(revisions).filter_by(position_id=root["id"], revision_no=2))
        .mappings()
        .one()
    )
    calc = (
        session.execute(select(calculations).filter_by(revision_id=revision["id"])).mappings().one()
    )

    def set_revision(**values):
        session.execute(update(revisions).where(revisions.c.id == revision["id"]).values(**values))

    def set_calc(**values):
        session.execute(
            update(calculations)
            .where(calculations.c.revision_id == revision["id"])
            .values(**values)
        )

    def set_root(**values):
        session.execute(update(position).where(position.c.id == root["id"]).values(**values))

    if change == "snapshot":
        row = session.get(InstrumentSnapshot, root["snapshot_id"])
        spec = dict(row.specification, contract_size="99999")
        session.execute(
            update(InstrumentSnapshot)
            .where(InstrumentSnapshot.id == row.id)
            .values(specification=spec)
        )
    elif change == "account_server":
        session.execute(
            update(JournalAccount)
            .where(JournalAccount.id == root["account_id"])
            .values(server="WRONG-SYNTHETIC-SERVER")
        )
    elif change == "account_hash":
        set_root(account_sha256="0" * 64)
    elif change == "root_entry":
        set_root(entry_price="150.1")
    elif change == "root_stop":
        set_root(original_stop="149.7")
    elif change == "risk_hash":
        set_root(
            original_risk_basis=canonical(
                dict(json.loads(root["original_risk_basis"]), original_stop="149.7")
            )
        )
    elif change == "risk_redefined":
        risk = json.loads(root["original_risk_basis"])
        risk["native"]["raw"] = "3000"
        risk["native"]["rounded"] = "3000"
        new_hash = digest(canonical(risk))
        set_root(original_risk_basis=canonical(risk), original_risk_sha256=new_hash)
        session.execute(
            update(calculations)
            .where(calculations.c.position_id == root["id"])
            .values(original_risk_sha256=new_hash)
        )
        result = json.loads(calc["canonical_result"])
        result["native"]["original_planned_risk"] = deepcopy(risk["native"])
        set_calc(canonical_result=canonical(result), result_sha256=digest(canonical(result)))
    elif change in {"fill", "cost", "fx", "event_key"}:
        name, column, values = {
            "fill": ("cfd_executions", "ordinal", dict(price="150.201")),
            "cost": ("cfd_adjustments", "kind", dict(amount="-101")),
            "fx": ("cfd_conversions", "rate", dict(rate="0.006")),
            "event_key": ("cfd_event_keys", "kind", dict(first_revision_no=3)),
        }[change]
        table = TABLES[name]
        if change == "event_key":
            session.execute(update(table).where(table.c.position_id == root["id"]).values(**values))
        else:
            condition = {
                "fill": table.c[column] == 1,
                "cost": table.c[column] == "commission",
                "fx": table.c[column] == "0.005",
            }[change]
            session.execute(
                update(table)
                .where(table.c.revision_id == revision["id"], condition)
                .values(**values)
            )
    elif change in {
        "input_hash",
        "input_rehashed",
        "duplicate_input_key",
        "result_hash",
        "result_rehashed",
        "numeric_result",
        "manifest_hash",
        "manifest_rehashed",
    }:
        field = "input" if "input" in change else "manifest" if "manifest" in change else "result"
        column = "manifest" if field == "manifest" else "canonical_" + field
        data = json.loads(calc[column])
        if field == "input":
            data["trade"]["entry"]["price"] = "151"
        elif field == "result":
            data["original_lots"] = 0.1 if change == "numeric_result" else "999"
        else:
            data["accepted_release"] = True
        raw = canonical(data)
        if change == "duplicate_input_key":
            raw = '{"schema_version":"cfd-position-v1",' + raw[1:]
        values = {column: raw}
        if change.endswith("rehashed") or change == "numeric_result":
            values[field + "_sha256"] = digest(raw)
            if field == "manifest":
                values["engine_build_sha256"] = digest(raw)
        set_calc(**values)
    elif change.startswith("unsupported_"):
        field = change.removeprefix("unsupported_")
        if field in {"canonicalizer", "policy"}:
            set_calc(**{field + "_version": "future-v999"})
        elif field == "request":
            set_revision(request_schema_version="future-v999")
        else:
            column = {
                "result": "canonical_result",
                "manifest": "manifest",
                "input": "canonical_input",
            }[field]
            data = json.loads(calc[column])
            data["engine" if field == "result" else "schema_version"] = "future-v999"
            raw = canonical(data)
            set_calc(**{column: raw, field + "_sha256": digest(raw)})
    elif change == "unsealed":
        set_revision(sealed_at=None)
    elif change == "invalid_head":
        table = TABLES["cfd_position_heads"]
        session.execute(
            update(table)
            .where(table.c.position_id == root["id"])
            .values(revision_no=1, row_version=1)
        )
    elif change == "unpublished":
        table = TABLES["cfd_position_heads"]
        session.execute(delete(table).where(table.c.position_id == root["id"]))
    elif change == "orphan_revision":
        values = dict(revision, id=str(uuid4()), revision_no=3, parent_revision_id=revision["id"])
        session.execute(insert(revisions), values)
    elif change == "missing_entry":
        costs, fills = TABLES["cfd_adjustments"], TABLES["cfd_executions"]
        session.execute(
            delete(costs).where(costs.c.revision_id == revision["id"], costs.c.kind == "commission")
        )
        session.execute(
            delete(fills).where(fills.c.revision_id == revision["id"], fills.c.role == "entry")
        )
    else:
        raise AssertionError("Unknown synthetic attack")
