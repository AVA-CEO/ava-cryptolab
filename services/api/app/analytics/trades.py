"""Linear, quote-settled journal math. No prices or FX rates are inferred."""

from datetime import timezone
from decimal import Decimal, localcontext

from app.models import Trade


def utc(value):
    # SQLite returns naive timestamps even for timezone=True; stored values are UTC.
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def calculate(trade: Trade) -> dict:
    with localcontext() as context:
        context.prec = 60
        return _calculate(trade)


def _calculate(trade: Trade) -> dict:
    qty = Decimal(trade.quantity)
    closed = sum((Decimal(e.quantity) for e in trade.exits), Decimal(0))
    sign = Decimal(1) if trade.market == "spot" or trade.direction == "buy" else Decimal(-1)
    gross = sum(
        ((e.price - trade.entry_price) * e.quantity * sign for e in trade.exits), Decimal(0)
    )
    exit_fees = sum((e.fees for e in trade.exits), Decimal(0))
    # All incurred entry fees and funding are recognized immediately, including open trades.
    net = gross - trade.entry_fees - exit_fees - trade.funding
    risk = abs(trade.entry_price - trade.stop_loss) * qty if trade.stop_loss else None
    status = "closed" if closed == qty else "partial" if closed else "open"
    last_exit = max((utc(e.exit_at) for e in trade.exits), default=None)
    holding = (last_exit - utc(trade.entry_at)).total_seconds() / 3600 if last_exit else None
    notional = trade.entry_price * qty
    return {
        "status": status,
        "closed_quantity": str(closed),
        "remaining_quantity": str(qty - closed),
        "gross_pnl": str(gross),
        "net_pnl": str(net),
        "planned_risk": str(risk) if risk else None,
        "realized_r": str(net / risk) if risk and closed else None,
        "notional": str(notional),
        "estimated_margin": str(notional / trade.leverage),
        "holding_hours": holding,
        "last_exit_at": last_exit.isoformat() if last_exit else None,
        "outcome": "win" if net > 0 else "loss" if net < 0 else "breakeven",
    }


def serialize(trade: Trade) -> dict:
    fields = [
        "id",
        "pair",
        "exchange",
        "currency",
        "market",
        "direction",
        "entry_price",
        "quantity",
        "stop_loss",
        "take_profit",
        "entry_fees",
        "funding",
        "leverage",
        "margin_type",
        "strategy",
        "notes",
        "mistakes",
        "emotion_before",
        "emotion_after",
        "lessons",
        "version",
    ]
    data = {key: getattr(trade, key) for key in fields}
    for key, value in data.items():
        if isinstance(value, Decimal):
            data[key] = format(value, "f")
    data["entry_at"] = utc(trade.entry_at).isoformat()
    data["has_screenshot"] = bool(trade.screenshot)
    data["exits"] = [
        {
            "exit_at": utc(e.exit_at).isoformat(),
            "price": format(e.price, "f"),
            "quantity": format(e.quantity, "f"),
            "fees": format(e.fees, "f"),
        }
        for e in trade.exits
    ]
    data["metrics"] = calculate(trade)
    return data
