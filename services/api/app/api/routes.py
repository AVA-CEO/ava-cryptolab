from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models import TradingAccount
from app.schemas.dashboard import DashboardSummary

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "ava-cryptolab", "version": "0.1.0"}


@router.get("/ready")
def ready(session: Session = Depends(get_session)):
    try:
        session.execute(text("SELECT 1"))
        session.execute(select(TradingAccount.id).limit(1))
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Database unavailable or migrations not applied.") from exc
    return {"status": "ready", "database": "connected"}


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(session: Session = Depends(get_session)):
    # No trade model until Phase 2. Never substitute sample profits for stored records.
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
