"""Explicit persistence only; never infers legacy account ownership or commits."""

import hashlib
import json

from sqlalchemy import select

from app.models import InstrumentRecord, InstrumentSnapshot, JournalAccount, Trade, TradeContext
from app.schemas.account import AccountContract
from app.schemas.instrument import instrument_adapter
from app.schemas.multi_asset import JournalContract

IDENTITY_FIELDS = ("broker", "venue", "symbol", "product", "market_category", "settlement_currency")


def content_digest(payload):
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def store_account(session, payload):
    contract = AccountContract.model_validate(payload)
    if session.get(JournalAccount, contract.account_id):
        raise ValueError("Account already exists; implicit identity replacement is not allowed.")
    values = contract.model_dump(exclude={"schema_version", "account_id"})
    record = JournalAccount(id=contract.account_id, **values)
    session.add(record)
    session.flush()
    return record


def store_snapshot(session, payload):
    spec = instrument_adapter.validate_python(payload)
    values = spec.model_dump(mode="json")
    digest = content_digest(values)
    instrument = session.get(InstrumentRecord, spec.instrument_id)
    identity = {field: getattr(spec, field) for field in IDENTITY_FIELDS}
    if instrument:
        if any(getattr(instrument, key) != value for key, value in identity.items()):
            raise ValueError("Instrument identity differs; use a distinct instrument ID.")
    else:
        instrument = InstrumentRecord(id=spec.instrument_id, **identity)
        session.add(instrument)
        session.flush()
    existing = session.scalar(
        select(InstrumentSnapshot).where(
            InstrumentSnapshot.instrument_id == spec.instrument_id,
            InstrumentSnapshot.content_sha256 == digest,
        )
    )
    if existing:
        load_snapshot(session, existing.id)
        return existing
    snapshot = InstrumentSnapshot(
        instrument_id=spec.instrument_id,
        broker=spec.broker,
        settlement_currency=spec.settlement_currency,
        specification=values,
        content_sha256=digest,
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def load_snapshot(session, snapshot_id):
    row = session.get(InstrumentSnapshot, snapshot_id)
    if row is None:
        raise ValueError("Snapshot not found.")
    if content_digest(row.specification) != row.content_sha256:
        raise ValueError("Snapshot integrity check failed.")
    spec = instrument_adapter.validate_python(row.specification)
    instrument = session.get(InstrumentRecord, row.instrument_id)
    if spec.instrument_id != row.instrument_id or instrument is None:
        raise ValueError("Snapshot instrument mismatch.")
    if any(getattr(instrument, key) != getattr(spec, key) for key in IDENTITY_FIELDS):
        raise ValueError("Snapshot identity differs from the instrument record.")
    if row.broker != spec.broker or row.settlement_currency != spec.settlement_currency:
        raise ValueError("Snapshot scope mismatch.")
    return spec


def attach_legacy_trade(session, *, trade_id, account_id, snapshot_id, import_batch_id=None):
    """Owner-reviewed assignment; only existing supported crypto semantics for now."""
    trade = session.get(Trade, trade_id)
    account = session.get(JournalAccount, account_id)
    if trade is None or account is None:
        raise ValueError("Trade and account must already exist.")
    if session.get(TradeContext, trade_id):
        raise ValueError("Trade already has an explicit context; reassignment needs review.")
    spec = load_snapshot(session, snapshot_id)
    account_data = {
        field: getattr(account, field)
        for field in AccountContract.model_fields
        if field not in {"schema_version", "account_id"}
    }
    JournalContract(account={"account_id": account.id, **account_data}, instrument=spec)
    expected_product = "crypto_spot" if trade.market == "spot" else "crypto_linear_futures"
    if (
        spec.product != expected_product
        or trade.pair != spec.symbol
        or trade.currency != spec.settlement_currency
        or trade.exchange != spec.broker
    ):
        raise ValueError("Legacy trade facts do not match the supplied instrument/account.")
    context = TradeContext(
        trade_id=trade.id,
        account_id=account.id,
        instrument_id=spec.instrument_id,
        snapshot_id=snapshot_id,
        broker=spec.broker,
        settlement_currency=spec.settlement_currency,
        import_batch_id=import_batch_id,
    )
    session.add(context)
    session.flush()
    return context
