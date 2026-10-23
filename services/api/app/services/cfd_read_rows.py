"""Reconstruct from scoped normalized rows, independently of stored input JSON."""

from sqlalchemy import select

from app.models.cfd import TABLES
from app.services.cfd_read_codec import corrupt, document

FILL_FIELDS = ("execution_id", "executed_at", "price", "lots", "profit_conversion_id")
FX_FIELDS = (
    "conversion_id",
    "from_currency",
    "to_currency",
    "rate",
    "observed_at",
    "applies_at",
    "max_age_seconds",
    "source",
)
COST_FIELDS = (
    "adjustment_id",
    "kind",
    "amount",
    "currency",
    "occurred_at",
    "source",
    "description",
    "execution_id",
    "conversion_id",
)
BROKER_FIELDS = (
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
)


def strip(row, fields):
    return {key: document(row[key]) if key == "source" else row[key] for key in fields}


def children(session, name, root, revision, limit, kind):
    table, keys = TABLES[name], TABLES["cfd_event_keys"]
    # Query all rows of this revision so a malformed cross-scope row cannot disappear.
    rows = (
        session.execute(
            select(table)
            .where(table.c.revision_id == revision["id"])
            .order_by(*table.primary_key.columns)
            .limit(limit + 1)
        )
        .mappings()
        .all()
    )
    if len(rows) > limit:
        corrupt()
    for row in rows:
        event_id = row[kind + "_id"]
        if (row["account_id"], row["position_id"], row["event_kind"]) != (
            root["account_id"],
            root["id"],
            kind,
        ):
            corrupt()
        key = (
            session.execute(
                select(keys).filter_by(
                    account_id=root["account_id"],
                    kind=kind,
                    event_id=event_id,
                    position_id=root["id"],
                )
            )
            .mappings()
            .one_or_none()
        )
        if key is None or not 1 <= key["first_revision_no"] <= revision["revision_no"]:
            corrupt()
    return rows


def reconstruct(session, root, revision, snapshot, risk):
    fills = sorted(
        children(session, "cfd_executions", root, revision, 1001, "execution"),
        key=lambda row: row["ordinal"],
    )
    if not fills or [row["ordinal"] for row in fills] != list(range(len(fills))):
        corrupt()
    if fills[0]["role"] != "entry" or any(row["role"] != "exit" for row in fills[1:]):
        corrupt()
    fx = children(session, "cfd_conversions", root, revision, 2001, "conversion")
    costs = children(session, "cfd_adjustments", root, revision, 1000, "adjustment")
    evidence = children(session, "cfd_broker_evidence", root, revision, 100, "evidence")
    return {
        "schema_version": revision["request_schema_version"],
        "position_reference": root["id"],
        "trade": {
            "schema_version": "cfd-input-v1",
            "account": document(root["account_contract"], root["account_sha256"]),
            "snapshot": snapshot,
            "direction": root["direction"],
            "entry": strip(fills[0], FILL_FIELDS),
            "exits": [strip(row, FILL_FIELDS) for row in fills[1:]],
            "original_stop": root["original_stop"],
            "planned_take_profit": revision["planned_take_profit"],
            "reporting_policy": revision["reporting_policy"],
            "risk_conversion_id": risk["risk_conversion_id"],
            "conversions": [strip(row, FX_FIELDS) for row in fx],
            "adjustments": [strip(row, COST_FIELDS) for row in costs],
        },
        "rounding": document(revision["rounding_policy"]),
        "recognition_policy": revision["recognition_policy"],
        "as_of": revision["as_of"],
        "broker_evidence": [strip(row, BROKER_FIELDS) for row in evidence],
    }
