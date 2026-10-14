import csv
import io
from decimal import Decimal

import pytest
from PIL import Image

from app.analytics.trading_iq import review
from app.models import Trade
from app.schemas.trade import TradeInput
from app.services.journal import write_trade


def trade_data(**changes):
    data = {
        "pair": "BTC/USD",
        "exchange": "Manual",
        "currency": "USD",
        "market": "spot",
        "direction": "buy",
        "entry_at": "2025-01-01T12:00:00Z",
        "entry_price": "100",
        "quantity": "2",
        "stop_loss": "90",
        "strategy": "Breakout",
        "entry_fees": "1",
        "exits": [
            {"exit_at": "2025-01-02T12:00:00Z", "price": "110", "quantity": "2", "fees": "1"}
        ],
    }
    data.update(changes)
    return data


def create(client, **changes):
    response = client.post("/api/v1/journal", json=trade_data(**changes))
    assert response.status_code == 201, response.text
    return response.json()


def test_create_edit_detail_delete_and_stale_version(client):
    trade = create(client)
    assert Decimal(trade["metrics"]["net_pnl"]) == 18
    assert Decimal(trade["metrics"]["realized_r"]) == Decimal("0.9")
    assert client.get(f"/api/v1/journal/{trade['id']}").json()["strategy"] == "Breakout"
    payload = trade_data(notes="A reflection", version=trade["version"])
    updated = client.put(f"/api/v1/journal/{trade['id']}", json=payload)
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert client.put(f"/api/v1/journal/{trade['id']}", json=payload).status_code == 409
    assert client.delete(f"/api/v1/journal/{trade['id']}?version=1").status_code == 409
    assert client.delete(f"/api/v1/journal/{trade['id']}?version=2").status_code == 204
    assert client.get(f"/api/v1/journal/{trade['id']}").status_code == 404


def test_partial_exits_costs_and_closed_only_statistics(client):
    trade = create(
        client,
        quantity="10",
        entry_fees="3",
        market="futures",
        margin_type="isolated",
        funding="2",
        exits=[{"exit_at": "2025-01-02T12:00:00Z", "price": "110", "quantity": "2", "fees": "1"}],
    )
    metrics = trade["metrics"]
    assert metrics["status"] == "partial"
    assert Decimal(metrics["remaining_quantity"]) == 8
    assert Decimal(metrics["net_pnl"]) == 14
    assert Decimal(metrics["realized_r"]) == Decimal("0.14")
    analytics = client.get("/api/v1/journal/analytics").json()
    assert analytics["closed_trades"] == 0
    assert analytics["expectancy"] is None
    assert Decimal(analytics["net_pnl"]) == 14


def test_short_funding_credit_and_leverage(client):
    a = create(
        client,
        market="futures",
        direction="sell",
        margin_type="cross",
        stop_loss="110",
        funding="-5",
        leverage="10",
        entry_fees="0",
        exits=[{"exit_at": "2025-01-02T12:00:00Z", "price": "90", "quantity": "2"}],
    )
    assert Decimal(a["metrics"]["net_pnl"]) == 25
    assert Decimal(a["metrics"]["estimated_margin"]) == 20
    b = create(
        client,
        market="futures",
        direction="sell",
        margin_type="cross",
        stop_loss="110",
        funding="-5",
        leverage="1",
        entry_fees="0",
        exits=[{"exit_at": "2025-01-02T12:00:00Z", "price": "90", "quantity": "2"}],
    )
    assert a["metrics"]["net_pnl"] == b["metrics"]["net_pnl"]


def test_spot_sell_is_inventory_disposal_not_short(client):
    assert Decimal(create(client, direction="sell")["metrics"]["net_pnl"]) == 18


@pytest.mark.parametrize(
    "changes",
    [
        {"entry_price": "0"},
        {"quantity": "-1"},
        {"quantity": "NaN"},
        {"entry_price": "Infinity"},
        {"stop_loss": "101"},
        {"take_profit": "80"},
        {"leverage": "10"},
        {"funding": "2"},
        {"entry_at": "2025-01-01T12:00:00"},
        {"entry_at": "2100-01-01T12:00:00Z"},
        {"currency": "USDT"},
        {"exits": [{"exit_at": "2024-01-01T12:00:00Z", "price": "110", "quantity": "2"}]},
        {"exits": [{"exit_at": "2025-01-02T12:00:00Z", "price": "110", "quantity": "3"}]},
    ],
)
def test_invalid_trade_rejected(client, changes):
    assert client.post("/api/v1/journal", json=trade_data(**changes)).status_code == 422


def test_missing_risk_and_no_losses_do_not_divide_by_zero(client):
    trade = create(client, stop_loss=None)
    assert trade["metrics"]["realized_r"] is None
    data = client.get("/api/v1/journal/analytics").json()
    assert data["profit_factor"] is None
    assert data["average_r"] is None
    assert data["iq"]["eligible"] is False
    assert data["iq"]["findings"][0]["kind"] == "quality"


def test_expectancy_profit_factor_drawdown_and_currency_separation(client):
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
        exits=[{"exit_at": "2025-01-03T12:00:00Z", "price": "90", "quantity": "1"}],
    )
    create(
        client,
        quantity="1",
        entry_fees="0",
        exits=[{"exit_at": "2025-01-04T12:00:00Z", "price": "100", "quantity": "1"}],
    )
    create(client, pair="ETH/USDT", currency="USDT")
    client.put("/api/v1/journal/account", json={"currency": "USD", "opening_balance": "100"})
    data = client.get("/api/v1/journal/analytics").json()
    assert data["total_trades"] == 3
    assert Decimal(data["profit_factor"]) == 2
    assert Decimal(data["max_drawdown"]) == 10
    assert abs(Decimal(data["expectancy"]) - Decimal(10) / 3) < Decimal("0.0000001")
    assert Decimal(data["recorded_balance"]) == 110
    assert data["wins"] == data["losses"] == data["breakeven"] == 1
    assert data["iq"]["eligible"] is False


def test_filters_sort_and_dates(client):
    create(client, notes="patient entry")
    create(client, pair="ETH/USD", strategy="Pullback", exchange="Other", exits=[])
    assert client.get("/api/v1/journal?search=patient").json()["total"] == 1
    assert client.get("/api/v1/journal?status=open").json()["total"] == 1
    assert client.get("/api/v1/journal?strategy=Pullback&exchange=Other").json()["total"] == 1
    assert client.get("/api/v1/journal?outcome=win").json()["total"] == 1
    assert client.get("/api/v1/journal?start=2025-01-02").json()["total"] == 0
    assert client.get("/api/v1/journal?sort=pnl_desc").json()["items"][0]["pair"] == "BTC/USD"
    assert client.get("/api/v1/journal?start=2025-02-01&end=2025-01-01").status_code == 422


def test_decimal_precision_survives_database(client):
    trade = create(
        client, entry_price="0.0000000001", stop_loss=None, quantity="123.4567890123", exits=[]
    )
    fetched = client.get(f"/api/v1/journal/{trade['id']}").json()
    assert Decimal(fetched["quantity"]) == Decimal("123.4567890123")
    assert Decimal(fetched["entry_price"]) == Decimal("0.0000000001")


def test_csv_roundtrip_dedup_formula_safety_and_atomic_failure(client):
    create(client, notes='=HYPERLINK("https://bad.invalid")')
    content = client.get("/api/v1/journal/export").text
    assert "'=HYPERLINK" in content
    result = client.post("/api/v1/journal/import", files={"file": ("trades.csv", content)})
    assert result.status_code == 200, result.text
    assert result.json()["skipped"] == 1
    rows = list(csv.DictReader(io.StringIO(content)))
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=rows[0].keys())
    writer.writeheader()
    rows[0]["journal_id"] = ""
    rows[0]["pair"] = "ETH/USD"
    writer.writerow(rows[0])
    rows[0]["quantity"] = "-2"
    writer.writerow(rows[0])
    assert (
        client.post(
            "/api/v1/journal/import", files={"file": ("bad.csv", buffer.getvalue())}
        ).status_code
        == 422
    )
    assert client.get("/api/v1/journal").json()["total"] == 1


def test_screenshot_validation_roundtrip_and_cleanup(client, tmp_path, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path))
    trade = create(client)
    url = f"/api/v1/journal/{trade['id']}/screenshot?version=1"
    assert client.post(url, files={"file": ("unsafe.svg", b"<svg></svg>")}).status_code == 422
    image = io.BytesIO()
    Image.new("RGB", (20, 20), "purple").save(image, format="PNG")
    response = client.post(url, files={"file": ("../../name.png", image.getvalue())})
    assert response.status_code == 200, response.text
    assert response.json()["has_screenshot"]
    assert response.json()["version"] == 2
    assert client.get(url.split("?")[0]).headers["content-type"] == "image/png"
    assert len(list(tmp_path.iterdir())) == 1
    client.delete(url.replace("version=1", "version=2"))
    assert not list(tmp_path.iterdir())


def test_untrusted_origin_and_missing_local_header_blocked(client):
    assert (
        client.post(
            "/api/v1/journal", json=trade_data(), headers={"origin": "https://evil.invalid"}
        ).status_code
        == 403
    )
    assert (
        client.post("/api/v1/journal", json=trade_data(), headers={"x-ava-local": ""}).status_code
        == 403
    )


def test_iq_compares_only_sufficient_groups(db):
    for i in range(20):
        payload = trade_data(
            strategy="Breakout" if i < 10 else "Pullback",
            entry_fees="0",
            mistakes="chased entry" if i < 4 else "",
            exits=[
                {
                    "exit_at": "2025-01-02T12:00:00Z",
                    "quantity": "2",
                    "price": "120" if i < 10 else "95",
                }
            ],
        )
        write_trade(db, TradeInput.model_validate(payload))
    db.commit()
    data = review(db.query(Trade).all(), "USD")
    assert data["eligible"]
    assert any("strongest setup: Breakout" in f["title"] for f in data["findings"])
    assert any(f["kind"] == "reflection" for f in data["findings"])
    assert not review(db.query(Trade).all()[:19], "USD")["eligible"]
