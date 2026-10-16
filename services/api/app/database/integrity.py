"""Versioned guard DDL. Keep v1 stable: migration 0003 depends on it."""

from sqlalchemy import DDL, event

SQLITE_SNAPSHOT_GUARDS_V1 = tuple(
    f"""CREATE TRIGGER snapshots_no_{operation.lower()} BEFORE {operation}
    ON instrument_snapshots BEGIN
    SELECT RAISE(ABORT, 'Instrument snapshots are append-only'); END"""
    for operation in ("UPDATE", "DELETE")
) + (
    """CREATE TRIGGER snapshots_no_replace BEFORE INSERT ON instrument_snapshots
WHEN EXISTS (SELECT 1 FROM instrument_snapshots WHERE id = NEW.id
OR (instrument_id = NEW.instrument_id AND content_sha256 = NEW.content_sha256))
BEGIN SELECT RAISE(ABORT, 'Instrument snapshots are append-only'); END""",
)
POSTGRES_SNAPSHOT_FUNCTION_V1 = """
CREATE FUNCTION ava_snapshot_immutable_v1() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Instrument snapshots are append-only'; END; $$
"""
POSTGRES_SNAPSHOT_TRIGGER_V1 = """
CREATE TRIGGER snapshots_immutable BEFORE UPDATE OR DELETE ON instrument_snapshots
FOR EACH ROW EXECUTE FUNCTION ava_snapshot_immutable_v1()
"""
POSTGRES_SNAPSHOT_TRUNCATE_V1 = """
CREATE TRIGGER snapshots_no_truncate BEFORE TRUNCATE ON instrument_snapshots
FOR EACH STATEMENT EXECUTE FUNCTION ava_snapshot_immutable_v1()
"""


def snapshot_guards_v1(table):
    for statement in SQLITE_SNAPSHOT_GUARDS_V1:
        event.listen(table, "after_create", DDL(statement).execute_if(dialect="sqlite"))
    for statement in (
        POSTGRES_SNAPSHOT_FUNCTION_V1,
        POSTGRES_SNAPSHOT_TRIGGER_V1,
        POSTGRES_SNAPSHOT_TRUNCATE_V1,
    ):
        event.listen(table, "after_create", DDL(statement).execute_if(dialect="postgresql"))
    event.listen(
        table,
        "after_drop",
        DDL("DROP FUNCTION IF EXISTS ava_snapshot_immutable_v1()").execute_if(dialect="postgresql"),
    )


def install_snapshot_guards_v1(connection):
    statements = (
        SQLITE_SNAPSHOT_GUARDS_V1
        if connection.dialect.name == "sqlite"
        else (
            POSTGRES_SNAPSHOT_FUNCTION_V1,
            POSTGRES_SNAPSHOT_TRIGGER_V1,
            POSTGRES_SNAPSHOT_TRUNCATE_V1,
        )
    )
    for statement in statements:
        connection.execute(DDL(statement))
