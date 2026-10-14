from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class TradingAccount(Base):
    __tablename__ = "trading_accounts"
    __table_args__ = (CheckConstraint("opening_balance >= 0", name="nonnegative_balance"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
