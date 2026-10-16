"""Synthetic, disposable migration rehearsal. No personal database is opened."""

import hashlib
import shutil
import sqlite3
from decimal import Decimal
from pathlib import Path

from alembic import command
from alembic.config import Config
from PIL import Image
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.orm import Session

from app.analytics.performance import performance
from app.analytics.trades import calculate
from app.models import Trade, TradeExit
from app.schemas.trade import TradeInput

API_ROOT = Path(__file__).resolve().parents[2]
LEGACY_TABLES = ("trading_accounts", "trades", "trade_exits")
NEW_TABLES = (
    "journal_accounts",
    "instruments",
    "instrument_snapshots",
    "broker_import_batches",
    "trade_contexts",
)


def migration_engine(path):
    engine = create_engine(f"sqlite:///{Path(path).resolve().as_posix()}")

    @event.listens_for(engine, "connect")
    def transaction_mode(connection, record):
        connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def explicit_begin(connection):
        connection.exec_driver_sql("BEGIN")

    return engine


def migration_config(connection=None, output_buffer=None):
    config = Config(str(API_ROOT / "alembic.ini"), output_buffer=output_buffer)
    config.set_main_option("script_location", str(API_ROOT / "migrations"))
    config.set_main_option("prepend_sys_path", str(API_ROOT))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def migrate(engine, revision="head", *, downgrade=False):
    with engine.begin() as connection:
        action = command.downgrade if downgrade else command.upgrade
        action(migration_config(connection), revision)


def seed_legacy(engine, directory):
    """Only synthetic fixtures; works against the actual 0002 schema."""
    screenshot = "a" * 32 + ".png"
    uploads = directory / "uploads"
    uploads.mkdir()
    Image.new("RGB", (8, 8), "purple").save(uploads / screenshot)
    common = {
        "pair": "BTC/USD",
        "exchange": "Synthetic broker",
        "currency": "USD",
        "market": "spot",
        "direction": "buy",
        "entry_at": "2025-01-01T12:00:00Z",
        "entry_price": "100",
        "quantity": "2",
        "stop_loss": "90",
        "entry_fees": "1",
        "notes": "Synthetic migration rehearsal",
        "strategy": "Practice",
        "exits": [
            {"exit_at": "2025-01-02T12:00:00Z", "price": "110", "quantity": "2", "fees": "1"}
        ],
    }
    cases = [
        common,
        {
            **common,
            "market": "futures",
            "direction": "sell",
            "stop_loss": "110",
            "margin_type": "isolated",
            "funding": "-3",
            "leverage": "10",
            "exits": [
                {"exit_at": "2025-01-02T12:00:00Z", "price": "90", "quantity": "2", "fees": "1"}
            ],
        },
        {
            **common,
            "market": "futures",
            "margin_type": "cross",
            "quantity": "10",
            "entry_fees": "3",
            "funding": "2",
        },
        {
            **common,
            "pair": "ETH/USDT",
            "currency": "USDT",
            "quantity": "1",
            "stop_loss": None,
            "exits": [],
        },
    ]
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO trading_accounts(id,name,currency,opening_balance,created_at) "
                "VALUES ('local-USD','Legacy balance','USD','1000','2025-01-01 00:00:00')"
            )
        )
    with Session(engine) as session, session.begin():
        for index, payload in enumerate(cases):
            data = TradeInput.model_validate(payload)
            trade = Trade(id=f"legacy-{index}", **data.model_dump(exclude={"exits", "version"}))
            trade.exits = [
                TradeExit(id=f"exit-{index}-{i}", **value.model_dump())
                for i, value in enumerate(data.exits)
            ]
            if index == 0:
                trade.screenshot = screenshot
            session.add(trade)


def legacy_state(engine, directory):
    with engine.connect() as connection:
        rows = {
            table: [
                list(row) for row in connection.execute(text(f"SELECT * FROM {table} ORDER BY id"))
            ]
            for table in LEGACY_TABLES
        }
        violations = list(connection.exec_driver_sql("PRAGMA foreign_key_check"))
    with Session(engine) as session:
        trades = list(session.scalars(select(Trade)))
        metrics = {trade.id: calculate(trade) for trade in trades}
        aggregates = {
            "USD": performance(trades, "USD", Decimal("1000")),
            "USDT": performance(trades, "USDT"),
        }
    pictures = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (directory / "uploads").iterdir()
    }
    return {
        "rows": rows,
        "metrics": metrics,
        "analytics": aggregates,
        "screenshots": pictures,
        "foreign_key_violations": violations,
    }


def prepare_legacy(directory):
    directory.mkdir(exist_ok=False)
    path = directory / "rehearsal.db"
    engine = migration_engine(path)
    migrate(engine, "0002")
    seed_legacy(engine, directory)
    before = legacy_state(engine, directory)
    backup = directory / "before-0003.db"
    # SQLite's backup API gives a consistent database copy, including committed WAL data.
    with sqlite3.connect(path) as source, sqlite3.connect(backup) as destination:
        source.backup(destination)
    shutil.copytree(directory / "uploads", directory / "backup-uploads")
    return engine, path, backup, before


def run_rehearsal(directory):
    engine, path, backup, before = prepare_legacy(directory)
    try:
        migrate(engine)
        after = legacy_state(engine, directory)
        if before != after:
            raise AssertionError("Legacy records, calculations or screenshots changed.")
        with engine.begin() as connection:
            counts = {
                name: connection.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar_one()
                for name in NEW_TABLES
            }
            if any(counts.values()):
                raise AssertionError("Migration invented account/instrument associations.")
            command.check(migration_config(connection))
        migrate(engine, "0002", downgrade=True)
        if before != legacy_state(engine, directory):
            raise AssertionError("Safe downgrade changed legacy data.")
        migrate(engine)
        with engine.connect() as connection:
            tables = inspect(connection).get_table_names()
        return {
            "mode": "synthetic-disposable",
            "database": str(path),
            "backup": str(backup),
            "legacy_trade_count": len(before["rows"]["trades"]),
            "legacy_exit_count": len(before["rows"]["trade_exits"]),
            "ids_rows_calculations_screenshots_preserved": before
            == legacy_state(engine, directory),
            "new_tables_initially_empty": counts,
            "migration_metadata_check": "passed",
            "empty_extension_downgrade_and_reupgrade": "passed",
            "table_count": len(tables),
        }
    finally:
        engine.dispose()
