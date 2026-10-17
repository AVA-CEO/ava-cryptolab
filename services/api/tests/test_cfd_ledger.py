"""B2 schema and transaction tests. All targets are newly created pytest databases."""

import json
import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from alembic import command
from cfd_calculation_examples import set_spec
from cfd_ledger_helpers import (
    canon,
    digest,
    prepare_scope,
    reload_request,
    request_digest,
    stage,
)
from cfd_position_examples import jpy_position, position_example
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.analytics.cfd_positions import calculate_position
from app.database.cfd_schema_v1 import NAMES
from app.database.cfd_target import require_disposable_cfd
from app.database.rehearsal import (
    legacy_state,
    migrate,
    migration_config,
    migration_engine,
    prepare_legacy,
)
from app.models.cfd import TABLES
from app.schemas.cfd_positions import CfdPositionRequest


@pytest.fixture
def ledger(tmp_path):
    engine = migration_engine(tmp_path / "ledger.db")
    migrate(engine, "0004")
    request = prepare_scope(engine)
    yield engine, request
    engine.dispose()


def inventory(connection):
    return {
        name: [dict(r) for r in connection.execute(select(TABLES[name])).mappings()]
        for name in NAMES
    }


def test_upgrade_restore_downgrade_and_legacy_preservation(tmp_path):
    directory = tmp_path / "legacy"
    engine, path, _, before = prepare_legacy(directory)
    try:
        migrate(engine, "0003")
        backup = directory / "before-0004.db"
        with sqlite3.connect(path) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        backup_hash = digest(backup.read_bytes().hex())
        migrate(engine, "0004")
        assert legacy_state(engine, directory) == before
        with engine.begin() as c:
            assert all(not values for values in inventory(c).values())
            assert c.exec_driver_sql("PRAGMA integrity_check").scalar() == "ok"
            assert c.exec_driver_sql("PRAGMA foreign_key_check").all() == []
            command.current(migration_config(c))
            command.heads(migration_config(c))
            command.check(migration_config(c))
        migrate(engine, "0003", downgrade=True)
        assert not set(NAMES) & set(inspect(engine).get_table_names())
        assert legacy_state(engine, directory) == before
        migrate(engine, "0004")
        restored = tmp_path / "restored"
        restored.mkdir()
        with sqlite3.connect(backup) as source, sqlite3.connect(restored / "restored.db") as target:
            source.backup(target)
        shutil.copytree(directory / "backup-uploads", restored / "uploads")
        restored_engine = migration_engine(restored / "restored.db")
        try:
            assert legacy_state(restored_engine, restored) == before
            with restored_engine.connect() as c:
                assert (
                    c.exec_driver_sql("select version_num from alembic_version").scalar() == "0003"
                )
        finally:
            restored_engine.dispose()
        assert digest(backup.read_bytes().hex()) == backup_hash
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "point",
    [
        "CREATE TABLE cfd_positions",
        "CREATE TABLE cfd_requests",
        "CREATE TRIGGER ava_cfd_root_scope_v1",
    ],
)
def test_injected_migration_failure_is_atomic(tmp_path, point):
    engine, _, _, before = prepare_legacy(tmp_path / "case")
    migrate(engine, "0003")

    def fail(c, cursor, statement, params, context, many):
        if statement.lstrip().startswith(point):
            raise RuntimeError("Expected injected DDL failure")

    event.listen(engine, "after_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="Expected injected"):
            migrate(engine, "0004")
    finally:
        event.remove(engine, "after_cursor_execute", fail)
    try:
        assert not set(NAMES) & set(inspect(engine).get_table_names())
        assert legacy_state(engine, tmp_path / "case") == before
        with engine.connect() as c:
            assert c.exec_driver_sql("select version_num from alembic_version").scalar() == "0003"
            assert not c.exec_driver_sql(
                "select name from sqlite_master where type='trigger' and name like 'ava_cfd_%'"
            ).all()
        migrate(engine, "0004")
    finally:
        engine.dispose()


def test_real_rows_rebuild_exact_calculation_and_preserve_versions(ledger):
    engine, request = ledger
    with engine.begin() as c:
        first = stage(c, request)
    with engine.begin() as c:
        restored = reload_request(c, first)
        result = calculate_position(restored)
        assert result.native.net_pnl.raw == Decimal("22")
        assert result.native.realized_r.raw == Decimal("1.10")
        assert (
            digest(canon(result.model_dump(mode="json")))
            == c.execute(select(TABLES["cfd_calculations"].c.result_sha256)).scalar()
        )
        stage(c, request, 2, first)
        assert c.execute(select(TABLES["cfd_position_heads"].c.row_version)).scalar() == 2
        assert calculate_position(reload_request(c, first)).native.net_pnl.raw == Decimal("22")


@pytest.mark.parametrize("table", NAMES)
@pytest.mark.parametrize("operation", ["delete", "update"])
def test_published_rows_cannot_be_mutated(ledger, table, operation):
    engine, request = ledger
    with engine.begin() as c:
        stage(c, request)
    if table == "cfd_conversions":
        return  # Covered with populated FX rows below; empty tables cannot fire row triggers.
    with pytest.raises(IntegrityError):
        with engine.begin() as c:
            if operation == "delete":
                c.exec_driver_sql(f"DELETE FROM {table}")
            else:
                field = next(iter(TABLES[table].columns)).name
                c.exec_driver_sql(f"UPDATE {table} SET {field}={field}")


@pytest.mark.parametrize("recursive", [0, 1])
@pytest.mark.parametrize(
    "table", ["cfd_positions", "cfd_revisions", "cfd_position_heads", "cfd_requests"]
)
def test_replace_cannot_erase_evidence(ledger, recursive, table):
    engine, request = ledger
    with engine.begin() as c:
        stage(c, request)
    with pytest.raises(IntegrityError):
        with engine.begin() as c:
            c.exec_driver_sql(f"PRAGMA recursive_triggers={recursive}")
            c.exec_driver_sql(f"INSERT OR REPLACE INTO {table} SELECT * FROM {table}")


@pytest.mark.parametrize(
    "field,value",
    [
        ("server", "Wrong"),
        ("platform", "bybit"),
        ("reporting_currency", "GBP"),
        ("broker_account_ref", "changed"),
    ],
)
def test_referenced_account_identity_is_frozen(ledger, field, value):
    engine, request = ledger
    with engine.begin() as c:
        stage(c, request)
    with pytest.raises(IntegrityError, match="identity"):
        with engine.begin() as c:
            c.execute(text(f"UPDATE journal_accounts SET {field}=:value"), {"value": value})


def test_server_mismatch_when_broker_and_currency_match(ledger):
    engine, request = ledger
    # Valid original account and snapshot, then change ONLY account server before any root exists.
    with engine.begin() as c:
        c.exec_driver_sql("UPDATE journal_accounts SET server='Different server'")
    with pytest.raises(IntegrityError, match="mismatch"):
        with engine.begin() as c:
            stage(c, request)
    with engine.connect() as c:
        assert all(not rows for rows in inventory(c).values())


def test_instrument_venue_cannot_drift_after_root(ledger):
    engine, request = ledger
    with engine.begin() as c:
        stage(c, request)
    with pytest.raises(IntegrityError, match="identity"):
        with engine.begin() as c:
            c.exec_driver_sql("UPDATE instruments SET venue='Different server'")


@pytest.mark.parametrize("point", ["children", "sealed", "head", "receipt"])
def test_whole_transaction_rolls_back_after_injected_failure(ledger, point):
    engine, request = ledger
    with pytest.raises(RuntimeError, match="Injected"):
        with engine.begin() as c:
            stage(c, request, fail_at=point)
    with engine.connect() as c:
        assert all(not rows for rows in inventory(c).values())
    with engine.begin() as c:
        stage(c, request)


def test_nonempty_downgrade_refused_without_data_loss(ledger):
    engine, request = ledger
    with engine.begin() as c:
        stage(c, request)
        before = inventory(c)
    with pytest.raises(RuntimeError, match="Downgrade refused"):
        migrate(engine, "0003", downgrade=True)
    with engine.connect() as c:
        assert inventory(c) == before
        assert c.exec_driver_sql("select version_num from alembic_version").scalar() == "0004"


def test_currency_conversion_rows_and_exact_decimal_roundtrip(ledger):
    engine, original = ledger
    data = original.model_dump(mode="json")
    adjustment = data["trade"]["adjustments"][0]
    adjustment.update(currency="EUR", conversion_id="synthetic-fx")
    data["rounding"]["currencies"].append(dict(currency="EUR", decimal_places=2))
    data["trade"]["conversions"] = [
        dict(
            conversion_id="synthetic-fx",
            from_currency="EUR",
            to_currency="USD",
            rate="2.000000000000000001",
            observed_at=adjustment["occurred_at"],
            applies_at=adjustment["occurred_at"],
            max_age_seconds=0,
            source=dict(kind="manual", reference="Synthetic rate only"),
        )
    ]
    request = CfdPositionRequest.model_validate(data)
    with engine.begin() as c:
        revision = stage(c, request)
        restored = reload_request(c, revision)
        assert restored.trade.conversions[0].rate == Decimal("2.000000000000000001")
        assert calculate_position(restored) == calculate_position(request)
    for operation in ["UPDATE cfd_conversions SET rate='3'", "DELETE FROM cfd_conversions"]:
        with pytest.raises(IntegrityError):
            with engine.begin() as c:
                c.exec_driver_sql(operation)


def test_late_child_and_foreign_scope_rejected(ledger):
    engine, request = ledger
    with engine.begin() as c:
        stage(c, request)
    with pytest.raises(IntegrityError, match="sealed"):
        with engine.begin() as c:
            c.exec_driver_sql(
                "INSERT INTO cfd_executions SELECT revision_id,'new-id',position_id,account_id, "
                "event_kind,role,99,executed_at,price,lots,profit_conversion_id "
                "FROM cfd_executions WHERE role='entry'"
            )


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///ava.db",
        "sqlite://",
        "sqlite:///C:/private/backup.db",
        "postgresql+psycopg://unused/unused",
    ],
)
def test_guard_rejects_without_connecting(url):
    with pytest.raises(RuntimeError, match="CFD migration"):
        require_disposable_cfd(make_url(url))


def test_two_real_connections_cannot_overwrite_same_version(ledger):
    engine, request = ledger
    with engine.begin() as c:
        first = stage(c, request)
    concurrent = create_engine(engine.url, connect_args={"timeout": 5, "check_same_thread": False})

    @event.listens_for(concurrent, "connect")
    def mode(dbapi, record):
        dbapi.isolation_level = None

    @event.listens_for(concurrent, "begin")
    def begin(c):
        c.exec_driver_sql("BEGIN IMMEDIATE")

    barrier = Barrier(2)

    def save(_):
        barrier.wait(timeout=5)
        with concurrent.begin() as c:
            head = c.execute(select(TABLES["cfd_position_heads"].c.row_version)).scalar()
            if head != 1:
                return "stale"
            stage(c, request, 2, first)
            return "saved"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(save, range(2))) == ["saved", "stale"]
        with engine.connect() as c:
            assert c.execute(select(TABLES["cfd_position_heads"].c.row_version)).scalar() == 2
            assert len(inventory(c)["cfd_revisions"]) == 2
    finally:
        concurrent.dispose()


@pytest.mark.parametrize("conflict", [False, True])
def test_concurrent_same_key_has_one_effect(ledger, conflict):
    engine, request = ledger
    data = request.model_dump(mode="json")
    if conflict:
        data["trade"]["planned_take_profit"] = "1.10400"
    other = CfdPositionRequest.model_validate(data)
    concurrent = create_engine(engine.url, connect_args={"timeout": 5, "check_same_thread": False})

    @event.listens_for(concurrent, "connect")
    def mode(dbapi, record):
        dbapi.isolation_level = None

    @event.listens_for(concurrent, "begin")
    def begin(c):
        c.exec_driver_sql("BEGIN IMMEDIATE")

    barrier = Barrier(2)

    def save(payload):
        barrier.wait(timeout=5)
        with concurrent.begin() as c:
            receipt = c.execute(select(TABLES["cfd_requests"])).mappings().first()
            if receipt:
                return (
                    "replayed"
                    if receipt["request_sha256"] == request_digest(payload)
                    else "conflict"
                ), receipt["revision_id"]
            return "saved", stage(c, payload)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(save, [request, other]))
        assert sorted(r[0] for r in outcomes) == ["conflict" if conflict else "replayed", "saved"]
        assert outcomes[0][1] == outcomes[1][1]
        with engine.connect() as c:
            rows = inventory(c)
            assert len(rows["cfd_positions"]) == len(rows["cfd_revisions"]) == 1
            assert len(rows["cfd_requests"]) == 1
            assert c.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    finally:
        concurrent.dispose()


def test_lost_reply_receipt_survives_later_edit_and_conflicting_reuse(ledger):
    engine, request = ledger
    with engine.begin() as c:
        first = stage(c, request)
    with engine.begin() as c:
        stage(c, request, 2, first)
    with engine.begin() as c:
        before = inventory(c)
        receipt = c.execute(select(TABLES["cfd_requests"]).filter_by(idempotency_key="key-1"))
        receipt = receipt.mappings().one()
        assert receipt["request_sha256"] == request_digest(request)
        assert json.loads(receipt["response_body"])["revision_id"] == first
        assert inventory(c) == before  # A receipt lookup has no write effect.
    for field, value in [("request_sha256", "f" * 64), ("operation", "void")]:
        with pytest.raises(IntegrityError, match="conflicting"):
            with engine.begin() as c:
                duplicate = dict(receipt, id="different-receipt", **{field: value})
                c.execute(TABLES["cfd_requests"].insert(), duplicate)


def test_same_key_is_scoped_to_account(ledger):
    engine, request = ledger
    data = request.model_dump(mode="json")
    data["trade"]["account"]["account_id"] = "other-synthetic-account"
    data["position_reference"] = "other-synthetic-position"
    data["broker_evidence"] = []
    other = prepare_scope(engine, data)
    with engine.begin() as c:
        stage(c, request)
        stage(c, other)
        assert len(inventory(c)["cfd_requests"]) == 2


@pytest.mark.parametrize("fail", [False, True])
def test_compound_void_and_replacement_is_atomic(ledger, fail):
    engine, request = ledger
    with engine.begin() as c:
        first = stage(c, request)
        before = inventory(c)
    data = request.model_dump(mode="json")
    data["position_reference"] = "synthetic-replacement"
    data["trade"]["entry"]["execution_id"] = "replacement-entry"
    data["trade"]["exits"] = []
    data["trade"]["adjustments"] = []
    data["broker_evidence"] = []
    replacement = CfdPositionRequest.model_validate(data)

    def save():
        with engine.begin() as c:
            void = stage(c, request, 2, first, lifecycle="void", operation="void", receipt=False)
            new = stage(c, replacement, receipt=False, replaces=request.position_reference)
            if fail:
                raise RuntimeError("Injected compound failure")
            original_receipt = before["cfd_requests"][0]
            c.execute(
                TABLES["cfd_requests"].insert(),
                dict(
                    original_receipt,
                    id="compound-receipt",
                    idempotency_key="replace-key",
                    operation="replace",
                    revision_id=void,
                    request_sha256=digest(canon({"void": void, "replacement": new})),
                    response_body=canon({"void": void, "replacement": new}),
                ),
            )

    if fail:
        with pytest.raises(RuntimeError, match="compound"):
            save()
    else:
        save()
    with engine.connect() as c:
        if fail:
            assert inventory(c) == before
        else:
            rows = inventory(c)
            assert len(rows["cfd_positions"]) == 2
            assert len(rows["cfd_revisions"]) == 3
            assert len(rows["cfd_requests"]) == 2
            assert sorted(r["row_version"] for r in rows["cfd_position_heads"]) == [1, 2]


def test_jpy_risk_conversion_and_partial_revisions_roundtrip(tmp_path):
    engine = migration_engine(tmp_path / "jpy.db")
    try:
        migrate(engine, "0004")
        request = prepare_scope(engine, jpy_position())
        with engine.begin() as c:
            first = stage(c, request)
            restored = reload_request(c, first)
            assert restored.trade.risk_conversion_id == "risk-fx"
            assert calculate_position(restored) == calculate_position(request)
            assert calculate_position(restored).native.gross_pnl.raw == Decimal("2600")
            assert calculate_position(restored).reporting.original_planned_risk.raw == Decimal("12")
    finally:
        engine.dispose()


def test_original_risk_cannot_drift_in_new_revision(ledger):
    engine, request = ledger
    with engine.begin() as c:
        first = stage(c, request)
        before = inventory(c)
    data = request.model_dump(mode="json")
    data["trade"]["original_stop"] = "1.09700"
    with pytest.raises(IntegrityError, match="anchors"):
        with engine.begin() as c:
            stage(c, CfdPositionRequest.model_validate(data), 2, first)
    with engine.connect() as c:
        assert inventory(c) == before


def test_create_all_does_not_reinstall_existing_guards(db):
    from app.database.session import Base

    Base.metadata.create_all(db.get_bind())
    assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_account_scoped_foreign_key_rejects_orphan_event(ledger):
    engine, request = ledger
    with engine.begin() as c:
        stage(c, request)
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        with engine.begin() as c:
            c.execute(
                TABLES["cfd_event_keys"].insert(),
                dict(
                    account_id="missing-account",
                    kind="execution",
                    event_id="orphan-event",
                    position_id=request.position_reference,
                    first_revision_no=1,
                    created_at="2025-01-06T00:00:00.000000Z",
                ),
            )


def test_partial_history_reload_keeps_original_risk(ledger):
    engine, request = ledger
    previous = None
    revisions = []
    for number, (cutoff, state, remaining, net) in enumerate(
        [
            ("2025-01-03T00:00:00Z", "open", "0.10", "-1"),
            ("2025-01-04T00:00:00Z", "partial", "0.06", "6.5"),
            ("2025-01-05T00:00:00Z", "closed", "0", "22"),
        ],
        start=1,
    ):
        data = request.model_dump(mode="json")
        data["as_of"] = cutoff
        data["broker_evidence"] = []
        with engine.begin() as c:
            previous = stage(c, CfdPositionRequest.model_validate(data), number, previous)
            revisions.append((previous, state, remaining, net))
    with engine.connect() as c:
        for revision, state, remaining, net in revisions:
            result = calculate_position(reload_request(c, revision))
            assert result.state == state
            assert result.remaining_lots == Decimal(remaining)
            assert result.native.net_pnl.raw == Decimal(net)
            assert result.native.original_planned_risk.raw == Decimal("20")


@pytest.mark.parametrize(
    "symbol,contract,entry,first,last,stop,tick,gross,risk",
    [
        ("XAUUSD", "100", "2000", "2002", "2003", "1998", "0.01", "26", "20"),
        ("XAGUSD", "5000", "25", "25.02", "25.03", "24.98", "0.001", "13", "10"),
    ],
)
def test_synthetic_metals_specification_and_calculation_reload(
    tmp_path, symbol, contract, entry, first, last, stop, tick, gross, risk
):
    engine = migration_engine(tmp_path / "metals.db")
    try:
        migrate(engine, "0004")
        data = position_example()
        set_spec(
            data,
            symbol=symbol,
            instrument_id=f"synthetic-{symbol}",
            contract_size=contract,
            market_category="metals",
            calculation_mode="cfd_linear",
            pip_size=None,
            tick_size=tick,
        )
        data["trade"]["entry"]["price"] = entry
        data["trade"]["exits"][0]["price"] = first
        data["trade"]["exits"][1]["price"] = last
        data["trade"].update(original_stop=stop, planned_take_profit=None)
        request = prepare_scope(engine, data)
        with engine.begin() as c:
            revision = stage(c, request)
            result = calculate_position(reload_request(c, revision))
            assert result == calculate_position(request)
            assert result.native.gross_pnl.raw == Decimal(gross)
            assert result.native.original_planned_risk.raw == Decimal(risk)
            assert result.native.realized_r.raw == Decimal("1.3")
    finally:
        engine.dispose()
