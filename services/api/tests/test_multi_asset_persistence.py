"""Persistence invariants using disposable databases and synthetic specifications."""

from copy import deepcopy

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import IntegrityError

from app.database.rehearsal import migrate, prepare_legacy
from app.models import (
    BrokerImportBatch,
    InstrumentRecord,
    InstrumentSnapshot,
    JournalAccount,
    TradeContext,
)
from app.services.multi_asset import (
    attach_legacy_trade,
    load_snapshot,
    store_account,
    store_snapshot,
)


def instrument_payload(product="crypto_spot", **changes):
    data = {
        "instrument_id": "synthetic-btc",
        "symbol": "BTC/USD",
        "broker": "Synthetic broker",
        "venue": "Synthetic server",
        "product": product,
        "market_category": "crypto",
        "calculation_mode": "spot_inventory",
        "quantity_unit": "base_units",
        "base_currency": "BTC",
        "quote_currency": "USD",
        "profit_currency": "USD",
        "settlement_currency": "USD",
        "tick_size": "0.01",
        "volume_min": "0.001",
        "volume_step": "0.001",
        "source": {
            "kind": "manual",
            "reference": "Synthetic fixture",
            "effective_at": "2025-01-01T00:00:00Z",
            "captured_at": "2025-01-02T00:00:00Z",
        },
    }
    if product == "crypto_linear_futures":
        data["calculation_mode"] = "linear_quote"
    if product == "cfd":
        for name in ("base_currency", "quote_currency"):
            data.pop(name)
        data.update(
            instrument_id="synthetic-eur",
            symbol="EURUSD",
            market_category="forex",
            calculation_mode="forex",
            quantity_unit="lots",
            contract_size="100000",
            pip_size="0.0001",
            tick_size="0.00001",
        )
    data.update(changes)
    return data


def account_payload(**changes):
    return {
        "account_id": "account-a",
        "name": "Synthetic account",
        "broker": "Synthetic broker",
        "platform": "manual",
        "reporting_currency": "USD",
        "settlement_currency": "USD",
        **changes,
    }


@pytest.fixture
def migrated(tmp_path):
    from sqlalchemy.orm import Session

    engine, _, _, _ = prepare_legacy(tmp_path / "case")
    migrate(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.mark.parametrize("product", ["crypto_spot", "crypto_linear_futures", "cfd"])
def test_snapshot_decimal_json_roundtrip_and_idempotent_insert(migrated, product):
    with migrated.begin():
        snapshot = store_snapshot(migrated, instrument_payload(product))
        snapshot_id = snapshot.id
        assert store_snapshot(migrated, instrument_payload(product)).id == snapshot_id
    migrated.expire_all()
    spec = load_snapshot(migrated, snapshot_id)
    assert spec.product == product
    if product == "cfd":
        assert str(spec.contract_size) == "100000"
        assert spec.quantity_unit == "lots"
    assert migrated.scalar(select(InstrumentSnapshot)).content_sha256


def test_new_specification_appends_instead_of_replacing_history(migrated):
    with migrated.begin():
        first = store_snapshot(migrated, instrument_payload())
        changed = instrument_payload(tick_size="0.02")
        changed["source"]["effective_at"] = "2025-01-02T00:00:00Z"
        second = store_snapshot(migrated, changed)
        assert first.id != second.id
    assert str(load_snapshot(migrated, first.id).tick_size) == "0.01"
    assert str(load_snapshot(migrated, second.id).tick_size) == "0.02"


@pytest.mark.parametrize("symbol", ["XAUUSD", "XAGUSD"])
def test_metal_specification_roundtrip_is_distinct_from_forex(migrated, symbol):
    with migrated.begin():
        row = store_snapshot(
            migrated,
            instrument_payload(
                "cfd",
                instrument_id=f"synthetic-{symbol}",
                symbol=symbol,
                market_category="metals",
                calculation_mode="cfd_linear",
                pip_size=None,
            ),
        )
        snapshot_id = row.id
    spec = load_snapshot(migrated, snapshot_id)
    assert spec.symbol == symbol
    assert spec.market_category == "metals"
    assert spec.pip_size is None


@pytest.mark.parametrize("operation", ["update", "delete", "replace"])
def test_database_rejects_snapshot_mutation_even_without_orm(migrated, operation):
    with migrated.begin():
        row = store_snapshot(migrated, instrument_payload())
        snapshot_id = row.id
    with pytest.raises(IntegrityError, match="append-only"):
        with migrated.begin():
            if operation == "update":
                migrated.execute(update(InstrumentSnapshot).values(content_sha256="b" * 64))
            elif operation == "delete":
                migrated.execute(delete(InstrumentSnapshot))
            else:
                migrated.execute(
                    text(
                        "INSERT OR REPLACE INTO instrument_snapshots "
                        "SELECT * FROM instrument_snapshots WHERE id=:id"
                    ),
                    {"id": snapshot_id},
                )
    assert str(load_snapshot(migrated, snapshot_id).tick_size) == "0.01"


def test_explicit_context_preserves_trade_and_rejects_reassignment(migrated):
    with migrated.begin():
        store_account(migrated, account_payload())
        snapshot = store_snapshot(migrated, instrument_payload())
        context = attach_legacy_trade(
            migrated, trade_id="legacy-0", account_id="account-a", snapshot_id=snapshot.id
        )
        assert context.trade_id == "legacy-0"
    with pytest.raises(ValueError, match="reassignment"):
        attach_legacy_trade(
            migrated, trade_id="legacy-0", account_id="account-a", snapshot_id=snapshot.id
        )


def test_accounts_do_not_assume_currency_parity_or_replace_identity(migrated):
    with migrated.begin():
        account = store_account(
            migrated, account_payload(reporting_currency="USDX", settlement_currency="USDT")
        )
        assert account.reporting_currency != account.settlement_currency
        store_account(migrated, account_payload(account_id="account-b", reporting_currency="EUR"))
    with pytest.raises(ValueError, match="already exists"):
        store_account(migrated, account_payload())


def test_known_broker_account_reference_is_unique_without_a_server(migrated):
    with migrated.begin():
        store_account(migrated, account_payload(broker_account_ref="synthetic-reference"))
    with pytest.raises(IntegrityError):
        with migrated.begin():
            store_account(
                migrated,
                account_payload(account_id="account-b", broker_account_ref="synthetic-reference"),
            )


@pytest.mark.parametrize(
    "changes",
    [
        {"account_id": "missing"},
        {"instrument_id": "missing"},
        {"snapshot_id": "missing"},
        {"broker": "Other broker"},
        {"settlement_currency": "USDT"},
        {"trade_id": "missing"},
    ],
)
def test_database_rejects_invalid_context_relationships(migrated, changes):
    with migrated.begin():
        store_account(migrated, account_payload())
        snapshot = store_snapshot(migrated, instrument_payload())
        snapshot_id = snapshot.id
    data = {
        "trade_id": "legacy-0",
        "account_id": "account-a",
        "instrument_id": "synthetic-btc",
        "snapshot_id": snapshot_id,
        "broker": "Synthetic broker",
        "settlement_currency": "USD",
    }
    with pytest.raises(IntegrityError):
        with migrated.begin():
            migrated.add(TradeContext(**{**data, **changes}))
            migrated.flush()


def test_provenance_cannot_point_at_another_accounts_import(migrated):
    with migrated.begin():
        store_account(migrated, account_payload())
        store_account(migrated, account_payload(account_id="account-b"))
        snapshot = store_snapshot(migrated, instrument_payload())
        batch = BrokerImportBatch(
            account_id="account-b",
            adapter_version="test-v1",
            source_kind="statement",
            source_sha256="a" * 64,
        )
        migrated.add(batch)
        migrated.flush()
        batch_id, snapshot_id = batch.id, snapshot.id
    with pytest.raises(IntegrityError):
        with migrated.begin():
            attach_legacy_trade(
                migrated,
                trade_id="legacy-0",
                account_id="account-a",
                snapshot_id=snapshot_id,
                import_batch_id=batch_id,
            )


def test_account_deletion_is_restricted_and_trade_deletion_keeps_snapshot(migrated):
    with migrated.begin():
        store_account(migrated, account_payload())
        snapshot = store_snapshot(migrated, instrument_payload())
        attach_legacy_trade(
            migrated, trade_id="legacy-0", account_id="account-a", snapshot_id=snapshot.id
        )
        snapshot_id = snapshot.id
    with pytest.raises(IntegrityError):
        with migrated.begin():
            migrated.execute(delete(JournalAccount))
    with migrated.begin():
        migrated.execute(text("DELETE FROM trades WHERE id='legacy-0'"))
    assert migrated.get(TradeContext, "legacy-0") is None
    assert migrated.get(InstrumentSnapshot, snapshot_id) is not None
    assert (
        migrated.execute(
            text("SELECT COUNT(*) FROM trade_exits WHERE trade_id='legacy-0'")
        ).scalar()
        == 0
    )


def test_invalid_assignment_rolls_back_new_account_and_snapshot(migrated):
    with pytest.raises(ValueError, match="do not match"):
        with migrated.begin():
            store_account(migrated, account_payload())
            snapshot = store_snapshot(migrated, instrument_payload("cfd"))
            attach_legacy_trade(
                migrated, trade_id="legacy-0", account_id="account-a", snapshot_id=snapshot.id
            )
    assert migrated.scalar(select(JournalAccount)) is None
    assert migrated.scalar(select(InstrumentSnapshot)) is None
    assert migrated.scalar(select(InstrumentRecord)) is None


def test_instrument_identity_cannot_be_silently_redefined(migrated):
    with migrated.begin():
        store_snapshot(migrated, instrument_payload())
    with pytest.raises(ValueError, match="identity differs"):
        store_snapshot(migrated, instrument_payload(symbol="ETH/USD"))


def test_corrupted_snapshot_content_is_rejected_on_load(migrated):
    with migrated.begin():
        row = store_snapshot(migrated, instrument_payload())
        snapshot_id = row.id
    # In-memory corruption cannot bypass integrity verification; stored row stays immutable.
    row.specification = deepcopy(row.specification)
    row.specification["tick_size"] = "99"
    with migrated.no_autoflush, pytest.raises(ValueError, match="integrity"):
        load_snapshot(migrated, snapshot_id)
    migrated.rollback()
    assert str(load_snapshot(migrated, snapshot_id).tick_size) == "0.01"
