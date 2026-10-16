"""Additive persistence: legacy rows are never automatically assigned."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.integrity import snapshot_guards_v1
from app.database.session import Base


class JournalAccount(Base):
    __tablename__ = "journal_accounts"
    __table_args__ = (
        UniqueConstraint("id", "broker", "settlement_currency", name="uq_account_scope"),
        UniqueConstraint(
            "broker", "platform", "server", "broker_account_ref", name="uq_broker_account"
        ),
        Index(
            "uq_account_without_server",
            "broker",
            "platform",
            "broker_account_ref",
            unique=True,
            sqlite_where=text("server IS NULL"),
            postgresql_where=text("server IS NULL"),
        ),
        CheckConstraint("platform IN ('manual','bybit','mt5')", name="ck_account_platform"),
        CheckConstraint("platform != 'mt5' OR server IS NOT NULL", name="ck_mt5_server"),
        CheckConstraint(
            "length(trim(name)) > 0 AND length(trim(broker)) > 0", name="ck_account_labels"
        ),
        CheckConstraint(
            "length(reporting_currency) BETWEEN 2 AND 12 "
            "AND reporting_currency = upper(reporting_currency) "
            "AND length(settlement_currency) BETWEEN 2 AND 12 "
            "AND settlement_currency = upper(settlement_currency)",
            name="ck_account_currencies",
        ),
    )
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    broker: Mapped[str] = mapped_column(String(100))
    platform: Mapped[str] = mapped_column(String(10))
    server: Mapped[str | None] = mapped_column(String(100))
    broker_account_ref: Mapped[str | None] = mapped_column(String(100))
    reporting_currency: Mapped[str] = mapped_column(String(12))
    settlement_currency: Mapped[str] = mapped_column(String(12))


class InstrumentRecord(Base):
    __tablename__ = "instruments"
    __table_args__ = (
        UniqueConstraint("id", "broker", "settlement_currency", name="uq_instrument_scope"),
        UniqueConstraint("broker", "venue", "symbol", "product", name="uq_instrument_identity"),
        CheckConstraint(
            "(market_category = 'crypto' "
            "AND product IN ('crypto_spot','crypto_linear_futures')) OR "
            "(market_category IN ('forex','metals','indices','energy','equities','other') "
            "AND product IN ('cfd','tradfi_perpetual'))",
            name="ck_instrument_product_market",
        ),
    )
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    broker: Mapped[str] = mapped_column(String(100))
    venue: Mapped[str] = mapped_column(String(100))
    symbol: Mapped[str] = mapped_column(String(60))
    product: Mapped[str] = mapped_column(String(32))
    market_category: Mapped[str] = mapped_column(String(12))
    settlement_currency: Mapped[str] = mapped_column(String(12))


class InstrumentSnapshot(Base):
    __tablename__ = "instrument_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["instrument_id", "broker", "settlement_currency"],
            ["instruments.id", "instruments.broker", "instruments.settlement_currency"],
            ondelete="RESTRICT",
            name="fk_snapshot_instrument",
        ),
        UniqueConstraint(
            "id", "instrument_id", "broker", "settlement_currency", name="uq_snapshot_scope"
        ),
        UniqueConstraint("instrument_id", "content_sha256", name="uq_snapshot_content"),
        CheckConstraint("length(content_sha256) = 64", name="ck_snapshot_hash"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    instrument_id: Mapped[str] = mapped_column(String(100))
    broker: Mapped[str] = mapped_column(String(100))
    settlement_currency: Mapped[str] = mapped_column(String(12))
    specification: Mapped[dict] = mapped_column(JSON)
    content_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


snapshot_guards_v1(InstrumentSnapshot.__table__)


class BrokerImportBatch(Base):
    __tablename__ = "broker_import_batches"
    __table_args__ = (
        UniqueConstraint("id", "account_id", name="uq_import_account"),
        UniqueConstraint("account_id", "adapter_version", "source_sha256", name="uq_import_source"),
        CheckConstraint("length(source_sha256) = 64", name="ck_import_hash"),
        CheckConstraint(
            "source_kind IN ('statement','broker_api','terminal','manual')", name="ck_import_kind"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    account_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("journal_accounts.id", ondelete="RESTRICT")
    )
    adapter_version: Mapped[str] = mapped_column(String(100))
    source_kind: Mapped[str] = mapped_column(String(20))
    source_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class TradeContext(Base):
    __tablename__ = "trade_contexts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "broker", "settlement_currency"],
            [
                "journal_accounts.id",
                "journal_accounts.broker",
                "journal_accounts.settlement_currency",
            ],
            ondelete="RESTRICT",
            name="fk_context_account",
        ),
        ForeignKeyConstraint(
            ["snapshot_id", "instrument_id", "broker", "settlement_currency"],
            [
                "instrument_snapshots.id",
                "instrument_snapshots.instrument_id",
                "instrument_snapshots.broker",
                "instrument_snapshots.settlement_currency",
            ],
            ondelete="RESTRICT",
            name="fk_context_snapshot",
        ),
        ForeignKeyConstraint(
            ["import_batch_id", "account_id"],
            ["broker_import_batches.id", "broker_import_batches.account_id"],
            ondelete="RESTRICT",
            name="fk_context_import",
        ),
    )
    trade_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("trades.id", ondelete="CASCADE"), primary_key=True
    )
    account_id: Mapped[str] = mapped_column(String(100), index=True)
    instrument_id: Mapped[str] = mapped_column(String(100))
    snapshot_id: Mapped[str] = mapped_column(String(36))
    broker: Mapped[str] = mapped_column(String(100))
    settlement_currency: Mapped[str] = mapped_column(String(12))
    import_batch_id: Mapped[str | None] = mapped_column(String(36))
