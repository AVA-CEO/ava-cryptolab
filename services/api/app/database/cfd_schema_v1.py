"""Frozen 0004 schema contract. Future changes need a new version, never edits to v1."""

import sqlalchemy as sa

NAMES = (
    "cfd_positions",
    "cfd_revisions",
    "cfd_event_keys",
    "cfd_conversions",
    "cfd_executions",
    "cfd_adjustments",
    "cfd_broker_evidence",
    "cfd_calculations",
    "cfd_position_heads",
    "cfd_requests",
)


def tables(metadata):
    def col(name, kind=sa.String(36), nullable=False, **kw):
        return sa.Column(name, kind, nullable=nullable, **kw)

    def fk(local, remote, name):
        return sa.ForeignKeyConstraint(local, remote, ondelete="RESTRICT", name=name)

    def check(expr, name):
        return sa.CheckConstraint(expr, name=name)

    def text(name, nullable=False):
        return col(name, sa.Text(), nullable)

    def ident(name, nullable=False):
        return col(name, sa.String(100), nullable)

    def enum(name, values):
        return check(f"{name} IN ({','.join(repr(v) for v in values)})", f"ck_{name}")

    result = {}

    def table(name, *items):
        value = sa.Table(name, metadata, *items)
        result[name] = value
        return value

    p = table(
        "cfd_positions",
        col("id", primary_key=True),
        ident("account_id"),
        ident("broker"),
        col("settlement_currency", sa.String(12)),
        col("snapshot_id"),
        ident("instrument_id"),
        col("platform", sa.String(10)),
        ident("server"),
        ident("venue"),
        col("product", sa.String(32)),
        col("snapshot_sha256", sa.String(64)),
        text("account_contract"),
        col("account_sha256", sa.String(64)),
        col("direction", sa.String(4)),
        ident("original_entry_id"),
        col("entry_at", sa.String(27)),
        text("entry_price"),
        text("original_lots"),
        text("original_stop", True),
        text("original_risk_basis"),
        col("original_risk_sha256", sa.String(64)),
        col("import_batch_id", nullable=True),
        text("source"),
        col("created_at", sa.String(27)),
        col("replaces_position_id", nullable=True),
        sa.UniqueConstraint("id", "account_id", name="uq_cfd_position_account"),
        fk(
            ["account_id", "broker", "settlement_currency"],
            [
                "journal_accounts.id",
                "journal_accounts.broker",
                "journal_accounts.settlement_currency",
            ],
            "fk_cfd_account",
        ),
        fk(
            ["snapshot_id", "instrument_id", "broker", "settlement_currency"],
            [
                "instrument_snapshots.id",
                "instrument_snapshots.instrument_id",
                "instrument_snapshots.broker",
                "instrument_snapshots.settlement_currency",
            ],
            "fk_cfd_snapshot",
        ),
        fk(
            ["import_batch_id", "account_id"],
            ["broker_import_batches.id", "broker_import_batches.account_id"],
            "fk_cfd_import",
        ),
        fk(["replaces_position_id"], ["cfd_positions.id"], "fk_cfd_replacement"),
        enum("direction", ["buy", "sell"]),
        enum("platform", ["manual", "mt5"]),
        check("product = 'cfd' AND server = venue AND length(trim(server)) > 0", "ck_cfd_scope"),
        check("replaces_position_id IS NULL OR replaces_position_id != id", "ck_cfd_self_replace"),
    )
    sa.Index("ix_cfd_account_created", p.c.account_id, p.c.created_at, p.c.id)
    sa.Index("ix_cfd_snapshot", p.c.snapshot_id)
    table(
        "cfd_revisions",
        col("id", primary_key=True),
        col("position_id"),
        ident("account_id"),
        col("revision_no", sa.Integer),
        col("parent_revision_id", nullable=True),
        col("operation", sa.String(10)),
        col("lifecycle", sa.String(10)),
        col("reason", sa.String(500)),
        text("notes", True),
        text("planned_take_profit", True),
        col("as_of", sa.String(27)),
        col("reporting_policy", sa.String(16)),
        col("recognition_policy", sa.String(16)),
        text("rounding_policy"),
        text("changed_event_ids"),
        col("request_schema_version", sa.String(64)),
        col("created_at", sa.String(27)),
        col("sealed_at", sa.String(27), True),
        sa.UniqueConstraint("position_id", "revision_no", name="uq_cfd_revision_no"),
        sa.UniqueConstraint("id", "position_id", name="uq_cfd_revision_position"),
        sa.UniqueConstraint("id", "position_id", "account_id", name="uq_cfd_revision_scope"),
        fk(
            ["position_id", "account_id"],
            ["cfd_positions.id", "cfd_positions.account_id"],
            "fk_cfd_revision_root",
        ),
        fk(
            ["parent_revision_id", "position_id"],
            ["cfd_revisions.id", "cfd_revisions.position_id"],
            "fk_cfd_revision_parent",
        ),
        enum("operation", ["create", "amend", "archive", "restore", "void"]),
        enum("lifecycle", ["active", "archived", "void"]),
        enum("reporting_policy", ["native_only", "explicit_rates"]),
        check("recognition_policy = 'incurred_once' AND revision_no > 0", "ck_cfd_policy"),
        check("length(trim(reason)) > 0", "ck_cfd_reason"),
    )
    table(
        "cfd_event_keys",
        ident("account_id", False),
        col("kind", sa.String(12)),
        ident("event_id"),
        col("position_id"),
        col("first_revision_no", sa.Integer),
        col("created_at", sa.String(27)),
        sa.PrimaryKeyConstraint("account_id", "kind", "event_id"),
        sa.UniqueConstraint(
            "account_id", "kind", "event_id", "position_id", name="uq_cfd_event_scope"
        ),
        fk(
            ["position_id", "account_id"],
            ["cfd_positions.id", "cfd_positions.account_id"],
            "fk_cfd_event_root",
        ),
        enum("kind", ["execution", "adjustment", "conversion", "evidence"]),
        check("first_revision_no > 0 AND length(trim(event_id)) > 0", "ck_cfd_event_id"),
    )

    # All evidence rows are scoped to a single revision and stable logical key.
    def ledger(name, id_name, kind, *extra):
        return table(
            name,
            col("revision_id"),
            ident(id_name),
            col("position_id"),
            ident("account_id"),
            col("event_kind", sa.String(12)),
            sa.PrimaryKeyConstraint("revision_id", id_name),
            fk(
                ["revision_id", "position_id", "account_id"],
                ["cfd_revisions.id", "cfd_revisions.position_id", "cfd_revisions.account_id"],
                f"fk_{name}_revision",
            ),
            fk(
                ["account_id", "event_kind", id_name, "position_id"],
                [
                    "cfd_event_keys.account_id",
                    "cfd_event_keys.kind",
                    "cfd_event_keys.event_id",
                    "cfd_event_keys.position_id",
                ],
                f"fk_{name}_key",
            ),
            check(f"event_kind = '{kind}'", f"ck_{name}_kind"),
            *extra,
        )

    ledger(
        "cfd_conversions",
        "conversion_id",
        "conversion",
        col("from_currency", sa.String(12)),
        col("to_currency", sa.String(12)),
        text("rate"),
        col("observed_at", sa.String(27)),
        col("applies_at", sa.String(27)),
        col("max_age_seconds", sa.Integer),
        text("source"),
        check("from_currency != to_currency AND observed_at <= applies_at", "ck_cfd_fx_direction"),
        check("max_age_seconds BETWEEN 0 AND 31536000", "ck_cfd_fx_age"),
    )
    x = ledger(
        "cfd_executions",
        "execution_id",
        "execution",
        col("role", sa.String(5)),
        col("ordinal", sa.Integer),
        col("executed_at", sa.String(27)),
        text("price"),
        text("lots"),
        ident("profit_conversion_id", True),
        sa.UniqueConstraint("revision_id", "ordinal", name="uq_cfd_execution_ordinal"),
        fk(
            ["revision_id", "profit_conversion_id"],
            ["cfd_conversions.revision_id", "cfd_conversions.conversion_id"],
            "fk_cfd_execution_fx",
        ),
        check(
            (
                "(role = 'entry' AND ordinal = 0 AND profit_conversion_id IS NULL) OR "
                "(role = 'exit' AND ordinal > 0)"
            ),
            "ck_cfd_fill_role",
        ),
    )
    sa.Index(
        "uq_cfd_one_entry",
        x.c.revision_id,
        unique=True,
        sqlite_where=sa.text("role = 'entry'"),
        postgresql_where=sa.text("role = 'entry'"),
    )
    ledger(
        "cfd_adjustments",
        "adjustment_id",
        "adjustment",
        col("kind", sa.String(10)),
        text("amount"),
        col("currency", sa.String(12)),
        col("occurred_at", sa.String(27)),
        ident("execution_id", True),
        ident("conversion_id", True),
        col("description", sa.String(300)),
        text("source"),
        enum("kind", ["commission", "swap", "fee", "other"]),
        check("length(trim(description)) > 0", "ck_cfd_cost_description"),
        fk(
            ["revision_id", "execution_id"],
            ["cfd_executions.revision_id", "cfd_executions.execution_id"],
            "fk_cfd_cost_fill",
        ),
        fk(
            ["revision_id", "conversion_id"],
            ["cfd_conversions.revision_id", "cfd_conversions.conversion_id"],
            "fk_cfd_cost_fx",
        ),
    )
    ledger(
        "cfd_broker_evidence",
        "evidence_id",
        "evidence",
        ident("instrument_id"),
        col("position_reference"),
        text("original_lots", True),
        text("exited_lots", True),
        col("state", sa.String(7)),
        col("as_of", sa.String(27)),
        col("reported_at", sa.String(27)),
        col("basis", sa.String(9)),
        col("recognition_policy", sa.String(16)),
        col("metric", sa.String(16)),
        text("amount"),
        col("currency", sa.String(12)),
        col("comparison_basis", sa.String(16)),
        text("absolute_tolerance"),
        text("source"),
        enum("state", ["open", "partial", "closed"]),
        enum("basis", ["native", "reporting"]),
        enum("recognition_policy", ["incurred_once", "other", "unknown"]),
        enum(
            "metric", ["gross_pnl", "net_pnl", "adjustments", "commission", "swap", "fee", "other"]
        ),
        enum("comparison_basis", ["raw", "display_rounded"]),
        check("reported_at >= as_of", "ck_cfd_report_time"),
    )
    table(
        "cfd_calculations",
        col("revision_id", primary_key=True),
        col("position_id"),
        col("snapshot_sha256", sa.String(64)),
        col("original_risk_sha256", sa.String(64)),
        text("canonical_input"),
        col("input_sha256", sa.String(64)),
        text("canonical_result"),
        col("result_sha256", sa.String(64)),
        col("engine_id", sa.String(64)),
        col("engine_build_sha256", sa.String(64)),
        col("policy_version", sa.String(64)),
        col("canonicalizer_version", sa.String(64)),
        text("manifest"),
        col("manifest_sha256", sa.String(64)),
        col("calculated_at", sa.String(27)),
        fk(
            ["revision_id", "position_id"],
            ["cfd_revisions.id", "cfd_revisions.position_id"],
            "fk_cfd_calc_revision",
        ),
    )
    table(
        "cfd_position_heads",
        col("position_id", primary_key=True),
        col("revision_id"),
        col("revision_no", sa.Integer),
        col("row_version", sa.Integer),
        col("updated_at", sa.String(27)),
        fk(["position_id"], ["cfd_positions.id"], "fk_cfd_head_root"),
        fk(
            ["revision_id", "position_id"],
            ["cfd_revisions.id", "cfd_revisions.position_id"],
            "fk_cfd_head_revision",
        ),
        fk(["revision_id"], ["cfd_calculations.revision_id"], "fk_cfd_head_calculation"),
        check("row_version = revision_no AND revision_no > 0", "ck_cfd_head_version"),
    )
    table(
        "cfd_requests",
        col("id", primary_key=True),
        ident("account_id"),
        ident("idempotency_key"),
        col("operation", sa.String(10)),
        col("resource_id"),
        col("revision_id"),
        col("request_sha256", sa.String(64)),
        col("request_schema_version", sa.String(64)),
        col("response_status", sa.Integer),
        text("response_body"),
        col("created_at", sa.String(27)),
        sa.UniqueConstraint("account_id", "idempotency_key", name="uq_cfd_request_key"),
        fk(
            ["revision_id", "resource_id", "account_id"],
            ["cfd_revisions.id", "cfd_revisions.position_id", "cfd_revisions.account_id"],
            "fk_cfd_request_result",
        ),
        enum("operation", ["create", "amend", "archive", "restore", "void", "replace"]),
        check(
            "response_status IN (200,201) AND length(trim(idempotency_key)) > 0",
            "ck_cfd_receipt",
        ),
    )
    # Portable shape checks; exact financial semantics stay in the approved Python contracts.
    financial = {
        "entry_price",
        "original_lots",
        "original_stop",
        "planned_take_profit",
        "price",
        "lots",
        "rate",
        "amount",
        "original_lots",
        "exited_lots",
        "absolute_tolerance",
    }
    for name, value in result.items():
        for c in value.columns:
            if c.name.endswith("sha256"):
                value.append_constraint(check(f"length({c.name}) = 64", f"ck_{name}_{c.name}"))
            if c.name.endswith("currency"):
                value.append_constraint(
                    check(
                        f"length({c.name}) BETWEEN 2 AND 12 AND {c.name} = upper({c.name})",
                        f"ck_{name}_{c.name}",
                    )
                )
            if c.name in financial:
                value.append_constraint(
                    check(f"length({c.name}) BETWEEN 1 AND 128", f"ck_{name}_{c.name}_text")
                )
            if c.name.endswith("_at") or c.name == "as_of":
                value.append_constraint(
                    check(
                        f"length({c.name}) = 27 AND substr({c.name},27,1) = 'Z'",
                        f"ck_{name}_{c.name}",
                    )
                )
        for c in value.columns:
            if c.name in {"position_id", "revision_id"} and not c.primary_key:
                sa.Index(f"ix_{name}_{c.name}", c)
    return result


def migration_tables():
    """Minimal frozen parent references; never import evolving ORM metadata into 0004."""
    metadata = sa.MetaData()
    for name, fields in {
        "journal_accounts": ("id", "broker", "settlement_currency"),
        "instrument_snapshots": ("id", "instrument_id", "broker", "settlement_currency"),
        "broker_import_batches": ("id", "account_id"),
    }.items():
        sa.Table(name, metadata, *(sa.Column(f, sa.String(100)) for f in fields))
    return tables(metadata)
