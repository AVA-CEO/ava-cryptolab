from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.analytics.trades import calculate, utc
from app.models import Trade, TradeExit
from app.schemas.trade import TradeInput


def find_trade(session, trade_id):
    trade = session.scalar(
        select(Trade).options(selectinload(Trade.exits)).where(Trade.id == trade_id)
    )
    if not trade:
        raise HTTPException(404, "Trade not found.")
    return trade


def all_trades(session):
    return session.scalars(select(Trade).options(selectinload(Trade.exits))).all()


def write_trade(session, data: TradeInput, trade=None):
    if trade and data.version != trade.version:
        raise HTTPException(409, "This trade changed. Reload it before saving your edits.")
    fields = data.model_dump(exclude={"exits", "version"})
    if trade is None:
        trade = Trade(**fields)
        session.add(trade)
    else:
        for name, value in fields.items():
            setattr(trade, name, value)
        trade.version += 1
    trade.exits = [TradeExit(**e.model_dump()) for e in data.exits]
    session.flush()
    return trade


def filter_trades(
    trades,
    *,
    search="",
    strategy="",
    exchange="",
    status="all",
    outcome="all",
    currency="USD",
    start: date | None = None,
    end: date | None = None,
    sort="entry_desc",
):
    if start and end and start > end:
        raise HTTPException(422, "Start date must not be after end date.")
    selected = []
    for t in trades:
        if currency != "all" and t.currency != currency:
            continue
        if search.casefold() not in f"{t.pair} {t.strategy} {t.notes} {t.mistakes}".casefold():
            continue
        if strategy and t.strategy.casefold() != strategy.casefold():
            continue
        if exchange and t.exchange.casefold() != exchange.casefold():
            continue
        # Date selection is entry date UTC. Analytics use this same trade cohort.
        if start and utc(t.entry_at).date() < start or end and utc(t.entry_at).date() > end:
            continue
        metrics = calculate(t)
        if status != "all" and metrics["status"] != status:
            continue
        if outcome != "all" and (metrics["status"] != "closed" or metrics["outcome"] != outcome):
            continue
        selected.append(t)
    if sort in ("pnl_desc", "pnl_asc"):
        from decimal import Decimal

        if currency == "all" and len({t.currency for t in selected}) > 1:
            raise HTTPException(422, "Select one currency before sorting by monetary PnL.")
        selected.sort(
            key=lambda t: (Decimal(calculate(t)["net_pnl"]), t.id), reverse=sort == "pnl_desc"
        )
    elif sort == "pair":
        selected.sort(key=lambda t: (t.pair, utc(t.entry_at), t.id))
    else:
        selected.sort(key=lambda t: (utc(t.entry_at), t.id), reverse=sort != "entry_asc")
    return selected
