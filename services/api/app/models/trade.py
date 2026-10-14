from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.database.types import ExactDecimal


class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    pair: Mapped[str] = mapped_column(String(30))
    exchange: Mapped[str] = mapped_column(String(80))
    currency: Mapped[str] = mapped_column(String(4), default="USD")
    market: Mapped[str] = mapped_column(String(10))
    direction: Mapped[str] = mapped_column(String(10))
    entry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    entry_price: Mapped[Decimal] = mapped_column(ExactDecimal())
    quantity: Mapped[Decimal] = mapped_column(ExactDecimal())
    stop_loss: Mapped[Decimal | None] = mapped_column(ExactDecimal())
    take_profit: Mapped[Decimal | None] = mapped_column(ExactDecimal())
    entry_fees: Mapped[Decimal] = mapped_column(ExactDecimal(), default=0)
    funding: Mapped[Decimal] = mapped_column(ExactDecimal(), default=0)
    leverage: Mapped[Decimal] = mapped_column(ExactDecimal(10, 2), default=1)
    margin_type: Mapped[str | None] = mapped_column(String(10))
    strategy: Mapped[str] = mapped_column(String(100), default="Unspecified")
    notes: Mapped[str] = mapped_column(Text, default="")
    mistakes: Mapped[str] = mapped_column(String(1000), default="")
    emotion_before: Mapped[str] = mapped_column(String(100), default="")
    emotion_after: Mapped[str] = mapped_column(String(100), default="")
    lessons: Mapped[str] = mapped_column(Text, default="")
    screenshot: Mapped[str | None] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(default=1)
    __mapper_args__ = {"version_id_col": version}
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    exits: Mapped[list[TradeExit]] = relationship(
        back_populates="trade", cascade="all, delete-orphan", order_by="TradeExit.exit_at"
    )


class TradeExit(Base):
    __tablename__ = "trade_exits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    trade_id: Mapped[str] = mapped_column(ForeignKey("trades.id", ondelete="CASCADE"), index=True)
    exit_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    price: Mapped[Decimal] = mapped_column(ExactDecimal())
    quantity: Mapped[Decimal] = mapped_column(ExactDecimal())
    fees: Mapped[Decimal] = mapped_column(ExactDecimal(), default=0)
    trade: Mapped[Trade] = relationship(back_populates="exits")
