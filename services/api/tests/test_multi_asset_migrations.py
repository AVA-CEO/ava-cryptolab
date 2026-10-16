"""Run real Alembic revisions; never point at the personal journal."""

import io
import shutil

import pytest
from alembic import command
from sqlalchemy import create_engine, event, inspect, text

from app.database.rehearsal import (
    NEW_TABLES,
    legacy_state,
    migrate,
    migration_config,
    migration_engine,
    prepare_legacy,
    run_rehearsal,
)


def test_rehearsal_preserves_ids_rows_relationships_calculations_and_screenshots(tmp_path):
    result = run_rehearsal(tmp_path / "case")
    assert result["legacy_trade_count"] == 4
    assert result["legacy_exit_count"] == 3
    assert result["ids_rows_calculations_screenshots_preserved"]
    assert not any(result["new_tables_initially_empty"].values())
    assert result["migration_metadata_check"] == "passed"


def test_backup_can_restore_original_legacy_schema_data_and_uploads(tmp_path):
    engine, _, backup, before = prepare_legacy(tmp_path / "case")
    try:
        migrate(engine)
        restored = tmp_path / "restored"
        restored.mkdir()
        shutil.copy2(backup, restored / "restored.db")
        shutil.copytree(backup.parent / "backup-uploads", restored / "uploads")
        restored_engine = migration_engine(restored / "restored.db")
        try:
            assert legacy_state(restored_engine, restored) == before
            with restored_engine.connect() as connection:
                assert (
                    connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
                    == "0002"
                )
                assert not set(NEW_TABLES) & set(inspect(connection).get_table_names())
        finally:
            restored_engine.dispose()
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "failure_point",
    [
        "CREATE TABLE instrument_snapshots",
        "CREATE TRIGGER snapshots_no_replace",
    ],
)
def test_failed_migration_rolls_back_schema_and_version_then_can_retry(tmp_path, failure_point):
    directory = tmp_path / "case"
    engine, _, _, before = prepare_legacy(directory)

    def fail_after_ddl(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith(failure_point):
            raise RuntimeError("Injected migration failure after DDL")

    event.listen(engine, "after_cursor_execute", fail_after_ddl)
    try:
        with pytest.raises(RuntimeError, match="Injected"):
            migrate(engine)
    finally:
        event.remove(engine, "after_cursor_execute", fail_after_ddl)
    try:
        with engine.connect() as connection:
            assert not set(NEW_TABLES) & set(inspect(connection).get_table_names())
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
                == "0002"
            )
        assert legacy_state(engine, directory) == before
        migrate(engine)
    finally:
        engine.dispose()


def test_downgrade_refuses_to_destroy_new_data_and_is_atomic(tmp_path):
    directory = tmp_path / "case"
    engine, _, _, before = prepare_legacy(directory)
    try:
        migrate(engine)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO journal_accounts"
                    "(id,name,broker,platform,reporting_currency,settlement_currency) "
                    "VALUES ('new','Practice','Synthetic broker','manual','USD','USD')"
                )
            )
        with pytest.raises(RuntimeError, match="Downgrade refused"):
            migrate(engine, "0002", downgrade=True)
        with engine.connect() as connection:
            assert set(NEW_TABLES) <= set(inspect(connection).get_table_names())
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
                == "0003"
            )
            assert connection.execute(text("SELECT COUNT(*) FROM journal_accounts")).scalar() == 1
        assert legacy_state(engine, directory) == before
    finally:
        engine.dispose()


def test_postgresql_upgrade_sql_renders_without_connecting_to_any_database():
    output = io.StringIO()
    config = migration_config(output_buffer=output)
    config.attributes["database_url"] = "postgresql+psycopg://unused/unused"
    command.upgrade(config, "0002:0003", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE journal_accounts" in sql
    assert "CREATE TABLE trade_contexts" in sql
    assert "BEFORE TRUNCATE" in sql
    assert "ON DELETE RESTRICT" in sql
    assert "CREATE FUNCTION ava_snapshot_immutable_v1" in sql


def test_supplied_legacy_sqlite_connection_also_rolls_back_ddl(tmp_path):
    from sqlalchemy.exc import SQLAlchemyError

    engine = create_engine(f"sqlite:///{(tmp_path / 'external.db').as_posix()}")
    try:
        with pytest.raises(SQLAlchemyError):
            with engine.begin() as connection:
                config = migration_config(connection)
                command.upgrade(config, "0002")
                connection.execute(text("INSERT INTO nonexistent_table VALUES (1)"))
        with engine.connect() as connection:
            assert not inspect(connection).get_table_names()
    finally:
        engine.dispose()


def test_current_api_works_while_personal_database_waits_at_0002(tmp_path):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

    from app.database.session import get_session
    from app.main import app

    engine, _, _, _ = prepare_legacy(tmp_path / "case")
    try:
        with Session(engine) as session:
            app.dependency_overrides[get_session] = lambda: session
            try:
                with TestClient(app, headers={"X-AVA-Local": "journal-v1"}) as client:
                    assert client.get("/api/v1/ready").status_code == 200
                    body = client.get("/api/v1/journal/legacy-0").json()
                    assert body["metrics"]["net_pnl"] == "18"
                    assert client.delete("/api/v1/journal/legacy-3?version=1").status_code == 204
            finally:
                app.dependency_overrides.clear()
    finally:
        engine.dispose()
