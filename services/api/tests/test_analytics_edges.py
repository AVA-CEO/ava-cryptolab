from decimal import Decimal

from test_journal import create, trade_data

from app.analytics.trading_iq import review
from app.models import Trade
from app.schemas.trade import TradeInput
from app.services.journal import write_trade


def test_simultaneous_closures_do_not_invent_drawdown_sequence(client):
    create(
        client,
        quantity="1",
        entry_fees="0",
        exits=[{"exit_at": "2025-01-02T12:00:00Z", "price": "120", "quantity": "1"}],
    )
    create(
        client,
        quantity="1",
        entry_fees="0",
        exits=[{"exit_at": "2025-01-02T12:00:00Z", "price": "90", "quantity": "1"}],
    )
    data = client.get("/api/v1/journal/analytics").json()
    assert Decimal(data["max_drawdown"]) == 0
    assert len(data["curve"]) == 2
    assert data["curve"][-1]["pnl"] == 10


def test_tied_setups_and_duplicate_tags_are_not_ranked_as_evidence(db):
    for i in range(20):
        values = trade_data(
            strategy="A" if i < 10 else "B", mistakes="chased, chased" if i == 0 else ""
        )
        write_trade(db, TradeInput.model_validate(values))
    db.commit()
    result = review(db.query(Trade).all(), "USD")
    assert not any(f["kind"] in ("setup", "reflection") for f in result["findings"])


def test_dashboard_uses_recorded_trade_results(client):
    create(client)
    data = client.get("/api/v1/dashboard").json()
    assert data["mode"] == "recorded"
    assert Decimal(data["realized_pnl"]) == 18
    assert data["recorded_equity"] is None
