from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Amount = Annotated[Decimal, Field(max_digits=28, decimal_places=10, allow_inf_nan=False)]
Positive = Annotated[Amount, Field(gt=0, le=Decimal("1000000000000"))]
Cost = Annotated[Amount, Field(ge=0, le=Decimal("1000000000000"))]


class ExitInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exit_at: datetime
    price: Positive
    quantity: Positive
    fees: Cost = Decimal(0)

    @field_validator("exit_at")
    @classmethod
    def aware_date(cls, value):
        if value.tzinfo is None:
            raise ValueError("Include a timezone in exit timestamps.")
        if value > datetime.now(timezone.utc):
            raise ValueError("An actual exit cannot be in the future.")
        return value.astimezone(timezone.utc)


class TradeInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    pair: str = Field(min_length=3, max_length=30, pattern=r"^[A-Z0-9]+/(USD|USDT|USDC)$")
    exchange: str = Field(min_length=1, max_length=80)
    currency: Literal["USD", "USDT", "USDC"] = "USD"
    market: Literal["spot", "futures"]
    direction: Literal["buy", "sell"]
    entry_at: datetime
    entry_price: Positive
    quantity: Positive
    stop_loss: Positive | None = None
    take_profit: Positive | None = None
    entry_fees: Cost = Decimal(0)
    # Positive = paid; negative = received. Applied in full to trade net PnL.
    funding: Amount = Decimal(0)
    leverage: Annotated[Decimal, Field(ge=1, le=125, decimal_places=2)] = Decimal(1)
    margin_type: Literal["isolated", "cross"] | None = None
    strategy: str = Field(default="Unspecified", max_length=100)
    notes: str = Field(default="", max_length=10000)
    mistakes: str = Field(default="", max_length=1000)
    emotion_before: str = Field(default="", max_length=100)
    emotion_after: str = Field(default="", max_length=100)
    lessons: str = Field(default="", max_length=10000)
    exits: list[ExitInput] = Field(default_factory=list, max_length=100)
    version: int | None = Field(default=None, ge=1)

    @field_validator("entry_at")
    @classmethod
    def aware_entry(cls, value):
        if value.tzinfo is None:
            raise ValueError("Include a timezone in entry timestamps.")
        if value > datetime.now(timezone.utc):
            raise ValueError("An actual entry cannot be in the future.")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def coherent_trade(self):
        if self.pair.split("/")[-1] != self.currency:
            raise ValueError("Quote and settlement currencies must match; FX is not assumed.")
        if self.market == "spot" and (
            self.leverage != 1 or self.margin_type is not None or self.funding != 0
        ):
            raise ValueError("Spot trades use 1x leverage, no margin type and no funding.")
        if self.market == "futures" and self.margin_type is None:
            raise ValueError("Choose isolated or cross margin for futures.")
        # Spot sell represents disposal of inventory whose recorded cost basis is entry_price.
        long = self.market == "spot" or self.direction == "buy"
        if self.stop_loss is not None:
            if (long and self.stop_loss >= self.entry_price) or (
                not long and self.stop_loss <= self.entry_price
            ):
                raise ValueError("Initial stop must be on the loss side of entry.")
        if self.take_profit is not None:
            if (long and self.take_profit <= self.entry_price) or (
                not long and self.take_profit >= self.entry_price
            ):
                raise ValueError("Planned target must be on the profit side of entry.")
        if sum(e.quantity for e in self.exits) > self.quantity:
            raise ValueError("Total exited quantity cannot exceed the original position.")
        if any(e.exit_at < self.entry_at for e in self.exits):
            raise ValueError("Exits cannot precede entry.")
        self.exits.sort(key=lambda e: e.exit_at)
        self.strategy = self.strategy or "Unspecified"
        return self
