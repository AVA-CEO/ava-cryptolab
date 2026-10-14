from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_session
from app.main import app
from app.models import TradingAccount


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_session] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_health_and_readiness(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"
    assert client.get("/api/v1/ready").json()["database"] == "connected"


def test_empty_dashboard_has_no_fabricated_financials(client):
    body = client.get("/api/v1/dashboard").json()
    assert body["total_trades"] == 0
    for key in ("recorded_equity", "realized_pnl", "win_rate", "profit_factor"):
        assert body[key] is None


def test_equity_comes_from_database(client, db):
    db.add(TradingAccount(name="Test", currency="USD", opening_balance=Decimal("1234.50")))
    db.commit()
    body = client.get("/api/v1/dashboard").json()
    assert Decimal(body["recorded_equity"]) == Decimal("1234.50")
    assert body["realized_pnl"] is None


def test_different_currencies_are_not_silently_aggregated(client, db):
    db.add(TradingAccount(name="Test", currency="EUR", opening_balance=Decimal("100")))
    db.commit()
    assert client.get("/api/v1/dashboard").json()["recorded_equity"] is None


def test_readiness_without_schema_returns_safe_error():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with Session(engine) as session:
        app.dependency_overrides[get_session] = lambda: session
        with TestClient(app) as client:
            response = client.get("/api/v1/ready")
            assert response.status_code == 503
            assert "Database unavailable" in response.json()["detail"]
    app.dependency_overrides.clear()
    engine.dispose()
