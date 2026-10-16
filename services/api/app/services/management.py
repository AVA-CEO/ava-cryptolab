"""Account creation and shared broker-specification catalog; no trade assignment."""

from datetime import timezone
from uuid import uuid4

from sqlalchemy import select

from app.models import InstrumentRecord, InstrumentSnapshot, JournalAccount
from app.schemas.account import AccountContract
from app.schemas.management import SnapshotReview
from app.schemas.multi_asset import JournalContract
from app.services.multi_asset import load_snapshot, store_account, store_snapshot


def account_contract(row):
    fields = {
        name: getattr(row, name)
        for name in AccountContract.model_fields
        if name not in {"schema_version", "account_id"}
    }
    return AccountContract(account_id=row.id, **fields)


def create_account(session, payload):
    values = payload.model_dump()
    # NULL broker references cannot provide database-level duplicate detection.
    query = select(JournalAccount).where(
        *[getattr(JournalAccount, key) == value for key, value in values.items()]
    )
    if session.scalar(query):
        raise ValueError("This account identity is already registered.")
    return store_account(session, {"account_id": str(uuid4()), **values})


def compatible(account, spec):
    JournalContract(account=account, instrument=spec)
    if account.platform == "bybit" and spec.product not in {
        "crypto_spot",
        "crypto_linear_futures",
        "tradfi_perpetual",
    }:
        raise ValueError("Bybit crypto records cannot use CFD contracts; select an MT5 account.")
    if account.server is not None and account.server != spec.venue:
        raise ValueError("Specification venue must match the recorded account server.")


def catalog_query(account):
    query = (
        select(InstrumentSnapshot)
        .join(InstrumentRecord, InstrumentRecord.id == InstrumentSnapshot.instrument_id)
        .where(
            InstrumentRecord.broker == account.broker,
            InstrumentRecord.settlement_currency == account.settlement_currency,
        )
    )
    if account.server is not None:
        query = query.where(InstrumentRecord.venue == account.server)
    if account.platform == "mt5":
        query = query.where(InstrumentRecord.product == "cfd")
    elif account.platform == "bybit":
        query = query.where(
            InstrumentRecord.product.in_(
                ["crypto_spot", "crypto_linear_futures", "tradfi_perpetual"]
            )
        )
    return query.order_by(InstrumentSnapshot.created_at.desc(), InstrumentSnapshot.id)


def review_snapshot(session, row, account):
    spec = load_snapshot(session, row.id)
    compatible(account, spec)
    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return SnapshotReview(
        snapshot_id=row.id,
        content_sha256=row.content_sha256,
        created_at=created,
        specification=spec,
    )


def register_specification(session, account, submission):
    compatible(account, submission.specification)
    return store_snapshot(session, submission.specification.model_dump())
