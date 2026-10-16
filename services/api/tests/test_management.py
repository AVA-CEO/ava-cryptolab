"""Synthetic account API tests against disposable on-disk SQLite databases."""

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.management_access import practice_database
from app.database.session import Base, get_session
from app.main import app
from app.models import InstrumentRecord, InstrumentSnapshot, JournalAccount

ROOT = "/api/v1/management"


@pytest.fixture
def management():
    with TemporaryDirectory(prefix="ava-accounts-") as directory:
        engine = create_engine(
            f"sqlite:///{Path(directory) / 'practice.db'}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            app.dependency_overrides[get_session] = lambda: session
            app.dependency_overrides[get_settings] = lambda: Settings(
                account_management_enabled=True
            )
            with TestClient(
                app,
                base_url="http://127.0.0.1",
                client=("127.0.0.1", 50000),
                headers={"X-AVA-Local": "journal-v1"},
            ) as client:
                yield client, session
            app.dependency_overrides.clear()
        engine.dispose()


@pytest.fixture
def identity():
    return dict(
        name="Synthetic practice",
        broker="Synthetic broker",
        platform="mt5",
        server="Synthetic server",
        reporting_currency="USD",
        settlement_currency="USD",
        broker_account_ref=None,
    )


@pytest.fixture
def specification():
    return json.loads((Path(__file__).parent / "fixtures/cfd-input.synthetic.json").read_text())[
        "snapshot"
    ]["specification"]


def add(client, identity):
    response = client.post(f"{ROOT}/accounts", json=identity)
    assert response.status_code == 201, response.text
    return response.json()["account_id"]


def register(client, account, spec):
    return client.post(f"{ROOT}/accounts/{account}/snapshots", json={"specification": spec})


def test_create_view_duplicate_and_no_historical_assignments(management, identity):
    client, session = management
    assert client.get(f"{ROOT}/status").json()["enabled"] is True
    account = add(client, identity)
    assert client.get(f"{ROOT}/accounts/{account}").json()["name"] == identity["name"]
    assert client.get(f"{ROOT}/accounts").json()["total"] == 1
    assert client.post(f"{ROOT}/accounts", json=identity).status_code == 409
    assert session.scalar(select(func.count()).select_from(JournalAccount)) == 1
    assert session.execute(text("select count(*) from trade_contexts")).scalar() == 0
    assert session.execute(text("PRAGMA foreign_key_check")).all() == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("server", None),
        ("reporting_currency", "usd"),
        ("platform", "unknown"),
        ("name", " "),
        ("broker", ""),
    ],
)
def test_invalid_identity(management, identity, field, value):
    identity[field] = value
    assert management[0].post(f"{ROOT}/accounts", json=identity).status_code == 422


def test_currency_independence_and_reference_conflict(management, identity):
    client, _ = management
    identity.update(reporting_currency="GBP", broker_account_ref="synthetic-ref")
    account = add(client, identity)
    assert client.get(f"{ROOT}/accounts/{account}").json()["settlement_currency"] == "USD"
    identity["name"] = "Different label same broker reference"
    assert client.post(f"{ROOT}/accounts", json=identity).status_code == 409


def test_snapshot_history_idempotency_and_immutability(management, identity, specification):
    client, session = management
    account = add(client, identity)
    first = register(client, account, specification)
    assert first.status_code == 201, first.text
    first_id = first.json()["snapshot_id"]
    assert register(client, account, specification).json()["snapshot_id"] == first_id
    specification["contract_size"] = "200000"
    assert register(client, account, specification).status_code == 201
    rows = client.get(f"{ROOT}/accounts/{account}/snapshots").json()
    assert rows["total"] == 2
    assert (
        client.get(f"{ROOT}/accounts/{account}/snapshots/{first_id}").json()["specification"][
            "contract_size"
        ]
        == "100000"
    )
    assert session.scalar(select(func.count()).select_from(InstrumentRecord)) == 1
    assert session.scalar(select(func.count()).select_from(InstrumentSnapshot)) == 2
    assert client.delete(f"{ROOT}/accounts/{account}/snapshots/{first_id}").status_code == 405
    with pytest.raises(IntegrityError, match="append-only"):
        session.execute(text("update instrument_snapshots set content_sha256='changed'"))
    session.rollback()


@pytest.mark.parametrize(
    "field,value",
    [("broker", "Other broker"), ("venue", "Other server"), ("settlement_currency", "USDT")],
)
def test_incompatible_catalog_hidden(management, identity, specification, field, value):
    client, _ = management
    account = add(client, identity)
    snapshot = register(client, account, specification).json()["snapshot_id"]
    other = copy.deepcopy(identity)
    other[{"venue": "server"}.get(field, field)] = value
    other["name"] = "Other scope"
    other_id = add(client, other)
    assert client.get(f"{ROOT}/accounts/{other_id}/snapshots").json()["items"] == []
    assert client.get(f"{ROOT}/accounts/{other_id}/snapshots/{snapshot}").status_code == 404
    assert register(client, other_id, specification).status_code == 422


def test_compatible_accounts_share_catalog(management, identity, specification):
    client, _ = management
    account = add(client, identity)
    register(client, account, specification)
    identity["name"] = "Second compatible practice account"
    other = add(client, identity)
    assert client.get(f"{ROOT}/accounts/{other}/snapshots").json()["total"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("contract_size", 100000.0),
        ("contract_size", True),
        ("contract_size", "0"),
        ("pip_size", None),
        ("volume_min", "0.015"),
        ("calculation_mode", "linear_quote"),
    ],
)
def test_invalid_specifications(management, identity, specification, field, value):
    client, session = management
    account = add(client, identity)
    specification[field] = value
    assert register(client, account, specification).status_code == 422
    assert session.scalar(select(func.count()).select_from(InstrumentRecord)) == 0


def test_identity_conflict_rolls_back(management, identity, specification):
    client, session = management
    account = add(client, identity)
    register(client, account, specification)
    specification["symbol"] = "GBPUSD"
    assert register(client, account, specification).status_code in (409, 422)
    assert session.scalar(select(func.count()).select_from(InstrumentSnapshot)) == 1


@pytest.mark.parametrize(
    "source_change",
    [{"kind": "broker_api"}, {"effective_at": "2025-01-01"}, {"captured_at": 1735776000}],
)
def test_source_evidence(management, identity, specification, source_change):
    client, _ = management
    account = add(client, identity)
    specification["source"].update(source_change)
    assert register(client, account, specification).status_code == 422


def test_no_secret_echo(management, identity):
    identity["api_key"] = "synthetic-secret-must-not-echo"
    response = management[0].post(f"{ROOT}/accounts", json=identity)
    assert response.status_code == 422
    assert identity["api_key"] not in response.text


@pytest.mark.parametrize(
    "headers",
    [{"host": "example.com"}, {"origin": "https://example.com"}, {"X-AVA-Local": "wrong"}],
)
def test_local_security(management, headers):
    assert management[0].get(f"{ROOT}/status", headers=headers).status_code == 403


def test_disabled_guard(management, identity):
    client, _ = management
    app.dependency_overrides[get_settings] = lambda: Settings(account_management_enabled=False)
    assert client.get(f"{ROOT}/status").json()["enabled"] is False
    assert client.post(f"{ROOT}/accounts", json=identity).status_code == 403


@pytest.mark.parametrize(
    "url", ["sqlite:///ava.db", "sqlite://", "sqlite:///C:/not-practice/ava.db"]
)
def test_actual_target_guard(url):
    engine = create_engine(url)
    with Session(engine) as session:
        assert practice_database(session, Settings(account_management_enabled=True)) is False
    engine.dispose()


def test_missing_and_pagination(management, identity):
    client, _ = management
    add(client, identity)
    assert client.get(f"{ROOT}/accounts/unknown").status_code == 404
    assert client.get(f"{ROOT}/accounts?limit=101").status_code == 422
    assert client.get(f"{ROOT}/accounts?offset=1").json()["items"] == []
    assert client.patch(f"{ROOT}/accounts/unknown", json={}).status_code == 405


@pytest.mark.parametrize("platform", ["manual", "bybit"])
def test_crypto_platform_compatibility(management, identity, specification, platform):
    client, _ = management
    identity.update(platform=platform, server=None)
    account = add(client, identity)
    response = register(client, account, specification)
    assert response.status_code == (201 if platform == "manual" else 422)


@pytest.mark.parametrize("field", ["source", "contract_size", "pip_size", "profit_currency"])
def test_missing_specifications(management, identity, specification, field):
    client, _ = management
    account = add(client, identity)
    del specification[field]
    assert register(client, account, specification).status_code == 422


def test_decimal_precision_preserved(management, identity, specification):
    client, _ = management
    account = add(client, identity)
    specification["contract_size"] = "100000.123456789123456789"
    response = register(client, account, specification)
    assert response.status_code == 201, response.text
    assert response.json()["specification"]["contract_size"] == specification["contract_size"]


def test_non_loopback_client_rejected(management):
    with TestClient(
        app,
        base_url="http://127.0.0.1",
        client=("192.0.2.10", 50000),
        headers={"X-AVA-Local": "journal-v1"},
    ) as client:
        assert client.get(f"{ROOT}/status").status_code == 403
