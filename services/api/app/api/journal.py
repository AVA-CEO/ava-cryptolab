from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.analytics.performance import performance
from app.analytics.trades import serialize
from app.analytics.trading_iq import review
from app.database.session import get_session
from app.models import TradingAccount
from app.schemas.trade import TradeInput
from app.services.csv_journal import export_csv, import_csv
from app.services.journal import all_trades, filter_trades, find_trade, write_trade
from app.services.screenshots import MAX_BYTES, remove_image, save_image, storage_path

router = APIRouter(prefix="/journal", tags=["Trading journal"])
Currency = Literal["USD", "USDT", "USDC"]


def cohort(
    session: Session = Depends(get_session),
    search: str = Query("", max_length=100),
    strategy: str = Query("", max_length=100),
    exchange: str = Query("", max_length=80),
    status: Literal["all", "open", "partial", "closed"] = "all",
    outcome: Literal["all", "win", "loss", "breakeven"] = "all",
    currency: Currency = "USD",
    start: date | None = None,
    end: date | None = None,
    sort: Literal["entry_desc", "entry_asc", "pnl_desc", "pnl_asc", "pair"] = "entry_desc",
):
    trades = filter_trades(
        all_trades(session),
        search=search,
        strategy=strategy,
        exchange=exchange,
        status=status,
        outcome=outcome,
        currency=currency,
        start=start,
        end=end,
        sort=sort,
    )
    return trades, currency


@router.get("")
def listing(
    selected=Depends(cohort), offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200)
):
    trades, _ = selected
    return {"total": len(trades), "items": [serialize(t) for t in trades[offset : offset + limit]]}


@router.get("/analytics")
def analytics(selected=Depends(cohort), session: Session = Depends(get_session)):
    trades, currency = selected
    account = session.get(TradingAccount, f"local-{currency}")
    data = performance(trades, currency, account.opening_balance if account else None)
    data["iq"] = review(trades, currency)
    return data


class BalanceInput(BaseModel):
    currency: Currency
    opening_balance: Annotated[
        Decimal, Field(ge=0, le=999_999_999_999, decimal_places=8, allow_inf_nan=False)
    ]


@router.get("/account")
def get_account(currency: Currency = "USD", session: Session = Depends(get_session)):
    account = session.get(TradingAccount, f"local-{currency}")
    return {
        "currency": currency,
        "opening_balance": str(account.opening_balance) if account else None,
    }


@router.put("/account")
def set_account(data: BalanceInput, session: Session = Depends(get_session)):
    account = session.get(TradingAccount, f"local-{data.currency}")
    if not account:
        account = TradingAccount(
            id=f"local-{data.currency}",
            name="Personal journal",
            currency=data.currency,
            opening_balance=data.opening_balance,
        )
        session.add(account)
    else:
        account.opening_balance = data.opening_balance
    session.commit()
    return {"currency": data.currency, "opening_balance": str(account.opening_balance)}


@router.get("/export")
def export(selected=Depends(cohort), template: bool = False):
    return Response(
        export_csv([] if template else selected[0]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="ava-journal.csv"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/import")
async def upload_csv(file: UploadFile, session: Session = Depends(get_session)):
    payload = await file.read(2_000_001)
    return import_csv(session, payload)


@router.post("", status_code=201)
def create(data: TradeInput, session: Session = Depends(get_session)):
    trade = write_trade(session, data)
    session.commit()
    return serialize(trade)


@router.get("/{trade_id}")
def detail(trade_id: str, session: Session = Depends(get_session)):
    return serialize(find_trade(session, trade_id))


@router.put("/{trade_id}")
def update(trade_id: str, data: TradeInput, session: Session = Depends(get_session)):
    trade = write_trade(session, data, find_trade(session, trade_id))
    session.commit()
    return serialize(trade)


@router.delete("/{trade_id}", status_code=204)
def delete(trade_id: str, version: int = Query(ge=1), session: Session = Depends(get_session)):
    trade = find_trade(session, trade_id)
    if trade.version != version:
        raise HTTPException(409, "Trade changed. Reload before deleting.")
    name = trade.screenshot
    session.delete(trade)
    session.commit()
    remove_image(name)
    return Response(status_code=204)


@router.post("/{trade_id}/screenshot")
async def upload_screenshot(
    trade_id: str,
    file: UploadFile,
    version: int = Query(ge=1),
    session: Session = Depends(get_session),
):
    trade = find_trade(session, trade_id)
    if trade.version != version:
        raise HTTPException(409, "Trade changed. Reload before attaching an image.")
    payload = await file.read(MAX_BYTES + 1)
    name = save_image(payload)
    old = trade.screenshot
    trade.screenshot = name
    try:
        session.commit()
    except Exception:
        remove_image(name)
        raise
    remove_image(old)
    return serialize(trade)


@router.delete("/{trade_id}/screenshot")
def delete_screenshot(
    trade_id: str, version: int = Query(ge=1), session: Session = Depends(get_session)
):
    trade = find_trade(session, trade_id)
    if trade.version != version:
        raise HTTPException(409, "Trade changed. Reload before removing its image.")
    old = trade.screenshot
    trade.screenshot = None
    session.commit()
    remove_image(old)
    return serialize(trade)


@router.get("/{trade_id}/screenshot")
def screenshot(trade_id: str, session: Session = Depends(get_session)):
    trade = find_trade(session, trade_id)
    if not trade.screenshot or not storage_path(trade.screenshot).is_file():
        raise HTTPException(404, "Screenshot not found.")
    return FileResponse(
        storage_path(trade.screenshot),
        media_type="image/png",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )
