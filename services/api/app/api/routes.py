from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.analytics.performance import performance
from app.database.session import get_session
from app.models import Trade, TradeExit, TradingAccount
from app.schemas.dashboard import DashboardSummary
from app.services.journal import all_trades

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "ava-cryptolab", "version": "0.1.0"}


@router.get("/ready")
def ready(session: Session = Depends(get_session)):
    try:
        session.execute(text("SELECT 1"))
        session.execute(select(TradingAccount.id).limit(1))
        session.execute(select(Trade.id).limit(1))
        session.execute(select(TradeExit.id).limit(1))
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Database unavailable or migrations not applied.") from exc
    return {"status": "ready", "database": "connected"}


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(session: Session = Depends(get_session)):
    trades = all_trades(session)
    if trades:
        account = session.get(TradingAccount, "local-USD")
        result = performance(trades, "USD", account.opening_balance if account else None)
        return DashboardSummary(
            mode="recorded",
            total_trades=len(trades),
            recorded_equity=result["recorded_balance"],
            realized_pnl=result["net_pnl"],
            win_rate=result["win_rate"],
            profit_factor=result["profit_factor"],
            message="Recorded journal results; use the currency selector.",
        )
    try:
        accounts = session.scalars(select(TradingAccount)).all()
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Database unavailable or migrations not applied.") from exc
    if not accounts:
        return DashboardSummary()
    # Account balances cannot be added across currencies without an explicit FX policy.
    currencies = {account.currency for account in accounts}
    if currencies != {"USD"}:
        return DashboardSummary(message="Only USD account totals are supported in Phase 1.")
    return DashboardSummary(recorded_equity=str(sum(a.opening_balance for a in accounts)))
