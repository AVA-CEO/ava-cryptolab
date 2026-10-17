"""Versioned SQLite/PostgreSQL 0004 guards; no application startup migration."""

import sqlalchemy as sa

from app.database.cfd_schema_v1 import NAMES


def definitions(metadata, dialect):
    pg = dialect == "postgresql"
    guards = []

    def add(name, table, operation, bad, message, prefix=""):
        guards.append((name, table, operation, bad, message, prefix))

    def json_field(field):
        return (
            f"s.specification ->> '{field}'" if pg else f"json_extract(s.specification,'$.{field}')"
        )

    valid = f"""EXISTS (SELECT 1 FROM journal_accounts a
        JOIN instrument_snapshots s ON s.id = NEW.snapshot_id
        JOIN instruments i ON i.id = s.instrument_id
        WHERE a.id = NEW.account_id AND a.platform = NEW.platform
        AND a.platform IN ('manual','mt5') AND a.server IS NOT NULL
        AND a.server = NEW.server AND NEW.server = NEW.venue AND i.venue = NEW.venue
        AND {json_field("venue")} = NEW.venue AND {json_field("product")} = 'cfd'
        AND i.product = 'cfd' AND NEW.product = 'cfd' AND i.id = NEW.instrument_id
        AND a.broker = NEW.broker AND s.broker = NEW.broker AND i.broker = NEW.broker
        AND {json_field("broker")} = NEW.broker
        AND a.settlement_currency = NEW.settlement_currency
        AND s.settlement_currency = NEW.settlement_currency
        AND i.settlement_currency = NEW.settlement_currency
        AND {json_field("settlement_currency")} = NEW.settlement_currency
        AND s.content_sha256 = NEW.snapshot_sha256)"""
    lock = (
        """IF current_setting('transaction_isolation') <> 'read committed' THEN
        RAISE EXCEPTION 'CFD writes require READ COMMITTED'; END IF;
        PERFORM 1 FROM journal_accounts WHERE id = NEW.account_id FOR SHARE;
        PERFORM 1 FROM instruments WHERE id = NEW.instrument_id FOR SHARE;"""
        if pg
        else ""
    )
    add(
        "root_scope",
        "cfd_positions",
        "INSERT",
        f"NOT ({valid})",
        "CFD account/server/venue/product mismatch",
        lock,
    )
    add(
        "calculation_anchors",
        "cfd_calculations",
        "INSERT",
        "NOT EXISTS (SELECT 1 FROM cfd_positions p WHERE p.id = NEW.position_id "
        "AND p.snapshot_sha256 = NEW.snapshot_sha256 "
        "AND p.original_risk_sha256 = NEW.original_risk_sha256)",
        "CFD calculation must retain original snapshot and risk anchors",
    )
    for table, fields, join in (
        (
            "journal_accounts",
            (
                "broker",
                "platform",
                "server",
                "reporting_currency",
                "settlement_currency",
                "broker_account_ref",
            ),
            "account_id",
        ),
        (
            "instruments",
            ("broker", "venue", "symbol", "product", "market_category", "settlement_currency"),
            "instrument_id",
        ),
    ):
        changed = " OR ".join(
            f"NEW.{f} IS DISTINCT FROM OLD.{f}" if pg else f"NEW.{f} IS NOT OLD.{f}" for f in fields
        )
        bad = f"({changed}) AND EXISTS (SELECT 1 FROM cfd_positions WHERE {join} = OLD.id)"
        prefix = (
            ""
            if not pg
            else f"""IF ({changed}) AND current_setting('transaction_isolation') <> 'read committed'
            THEN RAISE EXCEPTION 'CFD identity writes require READ COMMITTED'; END IF;"""
        )
        add(
            f"{table}_identity",
            table,
            "UPDATE",
            bad,
            "Referenced CFD identity is immutable",
            prefix,
        )

    for table in NAMES:
        if table not in {"cfd_revisions", "cfd_position_heads"}:
            add(f"{table}_update", table, "UPDATE", "TRUE", "CFD evidence is append-only")
        add(f"{table}_delete", table, "DELETE", "TRUE", "CFD evidence is append-only")
        value = metadata.tables[table]
        groups = [list(value.primary_key.columns)] + [
            list(c.columns) for c in value.constraints if isinstance(c, sa.UniqueConstraint)
        ]
        collisions = " OR ".join(
            "EXISTS (SELECT 1 FROM "
            + table
            + " old WHERE "
            + " AND ".join(f"old.{c.name} = NEW.{c.name}" for c in group)
            + ")"
            for group in groups
        )
        add(
            f"{table}_replace",
            table,
            "INSERT",
            collisions,
            "CFD conflicting insert/replace forbidden",
        )
        if table not in {
            "cfd_positions",
            "cfd_revisions",
            "cfd_event_keys",
            "cfd_position_heads",
            "cfd_requests",
        }:
            add(
                f"{table}_window",
                table,
                "INSERT",
                (
                    "NOT EXISTS (SELECT 1 FROM cfd_revisions r WHERE r.id = NEW.revision_id "
                    "AND r.sealed_at IS NULL)"
                ),
                "CFD revision is sealed or absent",
            )
    # A revision may only transition once from construction to sealed, unchanged otherwise.
    fields = [c.name for c in metadata.tables["cfd_revisions"].columns if c.name != "sealed_at"]
    changed = " OR ".join(
        f"NEW.{f} IS DISTINCT FROM OLD.{f}" if pg else f"NEW.{f} IS NOT OLD.{f}" for f in fields
    )
    calc = (
        "EXISTS (SELECT 1 FROM cfd_calculations c WHERE c.revision_id = OLD.id "
        "AND c.position_id = OLD.position_id)"
    )
    entry = """EXISTS (SELECT 1 FROM cfd_executions x JOIN cfd_positions p ON p.id = OLD.position_id
        WHERE x.revision_id = OLD.id AND x.role = 'entry' AND x.execution_id = p.original_entry_id
        AND x.executed_at = p.entry_at AND x.price = p.entry_price AND x.lots = p.original_lots)"""
    add(
        "revision_seal",
        "cfd_revisions",
        "UPDATE",
        (
            f"OLD.sealed_at IS NOT NULL OR NEW.sealed_at IS NULL OR ({changed}) "
            f"OR NOT ({calc}) OR NOT ({entry})"
        ),
        "Invalid CFD seal transition or original entry",
    )
    first = (
        "NEW.revision_no = 1 AND NEW.parent_revision_id IS NULL "
        "AND NEW.operation = 'create' AND NEW.lifecycle = 'active'"
    )
    parent = """EXISTS (SELECT 1 FROM cfd_position_heads h JOIN cfd_revisions r
        ON r.id = h.revision_id
        WHERE h.position_id = NEW.position_id AND h.revision_id = NEW.parent_revision_id
        AND NEW.revision_no = h.revision_no + 1 AND r.lifecycle != 'void')"""
    add(
        "revision_order",
        "cfd_revisions",
        "INSERT",
        f"NEW.sealed_at IS NOT NULL OR NOT (({first}) OR ({parent}))",
        "Invalid CFD revision chain",
    )
    sealed = """EXISTS (SELECT 1 FROM cfd_revisions r JOIN cfd_calculations c
        ON c.revision_id = r.id
        WHERE r.id = NEW.revision_id AND r.position_id = NEW.position_id
        AND r.revision_no = NEW.revision_no AND r.sealed_at IS NOT NULL)"""
    add(
        "head_first",
        "cfd_position_heads",
        "INSERT",
        f"NEW.revision_no != 1 OR NOT ({sealed})",
        "Invalid first CFD head",
    )
    parent_head = """EXISTS (SELECT 1 FROM cfd_revisions r WHERE r.id = NEW.revision_id
        AND r.parent_revision_id = OLD.revision_id)"""
    add(
        "head_advance",
        "cfd_position_heads",
        "UPDATE",
        (
            f"NEW.position_id != OLD.position_id OR NEW.row_version != OLD.row_version + 1 "
            f"OR NOT ({sealed}) OR NOT ({parent_head})"
        ),
        "Invalid CFD head advance",
    )
    add(
        "receipt_sealed",
        "cfd_requests",
        "INSERT",
        (
            "NOT EXISTS (SELECT 1 FROM cfd_revisions r WHERE r.id = NEW.revision_id "
            "AND r.sealed_at IS NOT NULL)"
        ),
        "CFD receipt requires sealed evidence",
    )
    return guards


def install(connection, metadata):
    pg = connection.dialect.name == "postgresql"
    for name, table, operation, bad, message, prefix in definitions(
        metadata, connection.dialect.name
    ):
        trigger = "ava_cfd_" + name + "_v1"
        if pg:
            result = "OLD" if operation == "DELETE" else "NEW"
            connection.exec_driver_sql(f"""CREATE FUNCTION {trigger}() RETURNS trigger
                LANGUAGE plpgsql VOLATILE AS $$
                BEGIN {prefix} IF {bad} THEN RAISE EXCEPTION '{message}'; END IF;
                RETURN {result}; END; $$""")
            connection.exec_driver_sql(
                f"CREATE TRIGGER {trigger} BEFORE {operation} ON {table} "
                f"FOR EACH ROW EXECUTE FUNCTION {trigger}()"
            )
        else:
            connection.exec_driver_sql(
                f"CREATE TRIGGER {trigger} BEFORE {operation} ON {table} "
                f"BEGIN SELECT CASE WHEN {bad} THEN RAISE(ABORT,'{message}') END; END"
            )
    if pg:
        connection.exec_driver_sql("""CREATE FUNCTION ava_cfd_no_truncate_v1() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'CFD truncate forbidden'; END; $$""")
        for table in NAMES:
            connection.exec_driver_sql(
                f"CREATE TRIGGER ava_cfd_truncate_{table}_v1 BEFORE TRUNCATE ON {table} "
                "FOR EACH STATEMENT EXECUTE FUNCTION ava_cfd_no_truncate_v1()"
            )


def remove(connection, metadata):
    pg = connection.dialect.name == "postgresql"
    for name, table, *_ in reversed(definitions(metadata, connection.dialect.name)):
        trigger = "ava_cfd_" + name + "_v1"
        connection.exec_driver_sql(
            f"DROP TRIGGER IF EXISTS {trigger}" + (f" ON {table}" if pg else "")
        )
        if pg:
            connection.exec_driver_sql(f"DROP FUNCTION IF EXISTS {trigger}()")
    if pg:
        for table in NAMES:
            connection.exec_driver_sql(
                f"DROP TRIGGER IF EXISTS ava_cfd_truncate_{table}_v1 ON {table}"
            )
        connection.exec_driver_sql("DROP FUNCTION IF EXISTS ava_cfd_no_truncate_v1()")
