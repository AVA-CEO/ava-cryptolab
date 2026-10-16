"""Local practice account/spec APIs. No credential or trade mutation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.management_access import local_management_access, practice_database
from app.database.session import get_session
from app.models import InstrumentSnapshot, JournalAccount
from app.schemas.account import AccountContract
from app.schemas.management import AccountCreate, SnapshotReview, SpecificationSubmission
from app.services import management


class SafeManagementRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request):
            try:
                return await original(request)
            except RequestValidationError as error:
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": "Check the account or specification fields.",
                        "errors": [
                            {"path": ".".join(map(str, item["loc"])), "message": item["msg"]}
                            for item in error.errors()[:20]
                        ],
                    },
                )

        return handler


router = APIRouter(
    prefix="/management",
    tags=["Local practice accounts"],
    route_class=SafeManagementRoute,
    dependencies=[Depends(local_management_access)],
)


def practice_session(
    session: Session = Depends(get_session), settings: Settings = Depends(get_settings)
):
    if not practice_database(session, settings):
        raise HTTPException(403, "Accounts management requires the isolated practice runner.")
    return session


def find_account(session, account_id):
    row = session.get(JournalAccount, account_id)
    if row is None:
        raise HTTPException(404, "Practice account not found.")
    return management.account_contract(row)


@router.get("/status")
def status(session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    enabled = practice_database(session, settings)
    return {"enabled": enabled, "mode": "local_practice" if enabled else "disabled"}


@router.get("/accounts")
def accounts(
    session: Session = Depends(practice_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    rows = session.scalars(
        select(JournalAccount)
        .order_by(JournalAccount.name, JournalAccount.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "total": session.scalar(select(func.count()).select_from(JournalAccount)),
        "items": [management.account_contract(row) for row in rows],
    }


@router.post("/accounts", response_model=AccountContract, status_code=201)
def create(data: AccountCreate, session: Session = Depends(practice_session)):
    try:
        row = management.create_account(session, data)
        session.commit()
        return management.account_contract(row)
    except (ValueError, IntegrityError):
        session.rollback()
        raise HTTPException(
            409, "Account identity already registered; review the existing account."
        ) from None


@router.get("/accounts/{account_id}", response_model=AccountContract)
def detail(account_id: str, session: Session = Depends(practice_session)):
    return find_account(session, account_id)


@router.get("/accounts/{account_id}/snapshots")
def snapshots(
    account_id: str,
    session: Session = Depends(practice_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    account = find_account(session, account_id)
    query = management.catalog_query(account)
    rows = session.scalars(query.offset(offset).limit(limit)).all()
    return {
        "total": session.scalar(select(func.count()).select_from(query.subquery())),
        "items": [management.review_snapshot(session, row, account) for row in rows],
    }


@router.post("/accounts/{account_id}/snapshots", response_model=SnapshotReview, status_code=201)
def register(
    account_id: str, data: SpecificationSubmission, session: Session = Depends(practice_session)
):
    account = find_account(session, account_id)
    try:
        row = management.register_specification(session, account, data)
        session.commit()
        return management.review_snapshot(session, row, account)
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Instrument identity conflicts with existing history.") from None
    except ValueError as error:
        session.rollback()
        raise HTTPException(422, str(error)) from None


@router.get("/accounts/{account_id}/snapshots/{snapshot_id}", response_model=SnapshotReview)
def snapshot(account_id: str, snapshot_id: str, session: Session = Depends(practice_session)):
    account = find_account(session, account_id)
    row = session.get(InstrumentSnapshot, snapshot_id)
    if row is None:
        raise HTTPException(404, "Compatible snapshot not found.")
    try:
        return management.review_snapshot(session, row, account)
    except ValueError:
        raise HTTPException(404, "Compatible snapshot not found.") from None
