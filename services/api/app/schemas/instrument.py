"""Versioned specification contracts, not persistence or broker integration.

Only existing crypto products have a working calculator today. CFD and TradFi
perpetual definitions describe future inputs; validation does not enable trading.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9]{1,11}$")]
Identifier = Annotated[str, Field(min_length=1, max_length=100)]
PositiveDecimal = Annotated[
    Decimal, Field(gt=0, le=Decimal("1e18"), max_digits=38, decimal_places=18, allow_inf_nan=False)
]
TraditionalMarket = Literal["forex", "metals", "indices", "energy", "equities", "other"]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)


def aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Include a timezone; broker local time must be resolved explicitly.")
    return value.astimezone(timezone.utc)


class SpecificationSource(ContractModel):
    kind: Literal["manual", "statement", "broker_api", "terminal"]
    reference: Annotated[str, Field(min_length=1, max_length=200)]
    effective_at: datetime
    captured_at: datetime

    _timestamps = field_validator("effective_at", "captured_at")(aware_utc)

    @model_validator(mode="after")
    def known_specification(self):
        if self.effective_at > self.captured_at:
            raise ValueError("A specification cannot take effect after its capture time.")
        return self


class MoneyValue(ContractModel):
    """A positive per-lot value observation; not a permanent FX conversion rule."""

    amount: PositiveDecimal
    currency: CurrencyCode
    observed_at: datetime

    _timestamp = field_validator("observed_at")(aware_utc)


class InstrumentBase(ContractModel):
    schema_version: Literal["instrument-v1"] = "instrument-v1"
    instrument_id: Identifier
    symbol: Annotated[str, Field(min_length=1, max_length=60)]
    broker: Identifier
    venue: Identifier
    profit_currency: CurrencyCode
    settlement_currency: CurrencyCode
    tick_size: PositiveDecimal
    volume_min: PositiveDecimal
    volume_step: PositiveDecimal
    volume_max: PositiveDecimal | None = None
    source: SpecificationSource

    @model_validator(mode="after")
    def volume_bounds(self):
        if self.volume_max is not None and self.volume_max < self.volume_min:
            raise ValueError("Maximum volume cannot be below minimum volume.")
        return self


class CryptoSpotInstrument(InstrumentBase):
    product: Literal["crypto_spot"]
    market_category: Literal["crypto"]
    calculation_mode: Literal["spot_inventory"]
    quantity_unit: Literal["base_units"]
    base_currency: CurrencyCode
    quote_currency: CurrencyCode

    @model_validator(mode="after")
    def quote_settled(self):
        if not self.quote_currency == self.profit_currency == self.settlement_currency:
            raise ValueError("Current crypto contracts require quote-settled profit.")
        return self


class CryptoLinearInstrument(CryptoSpotInstrument):
    product: Literal["crypto_linear_futures"]
    calculation_mode: Literal["linear_quote"]


class CfdInstrument(InstrumentBase):
    product: Literal["cfd"]
    market_category: TraditionalMarket
    calculation_mode: Literal["forex", "cfd_linear", "cfd_index", "futures_tick"]
    quantity_unit: Literal["lots"]
    contract_size: PositiveDecimal
    # Broker/contract-specific: do not derive pips from decimal digits or ticks.
    pip_size: PositiveDecimal | None = None
    pip_value_per_lot: MoneyValue | None = None
    tick_value_profit_per_lot: MoneyValue | None = None
    tick_value_loss_per_lot: MoneyValue | None = None

    @model_validator(mode="after")
    def calculation_inputs(self):
        if self.market_category == "forex" and self.calculation_mode != "forex":
            raise ValueError("Forex CFDs must declare the forex calculation mode.")
        if self.calculation_mode == "forex" and self.market_category != "forex":
            raise ValueError("The forex calculation mode requires the forex market category.")
        if self.market_category == "forex" and self.pip_size is None:
            raise ValueError("Forex contracts require an explicit pip size.")
        if self.pip_value_per_lot is not None and self.pip_size is None:
            raise ValueError("A pip value requires an explicit pip size.")
        if self.calculation_mode == "futures_tick" and (
            self.tick_value_profit_per_lot is None or self.tick_value_loss_per_lot is None
        ):
            raise ValueError("Tick-based contracts require both profit and loss tick values.")
        return self


class TradfiPerpetualInstrument(InstrumentBase):
    product: Literal["tradfi_perpetual"]
    market_category: TraditionalMarket
    calculation_mode: Literal["linear_contract"]
    quantity_unit: Literal["contracts", "base_units"]
    contract_multiplier: PositiveDecimal

    @model_validator(mode="after")
    def settlement(self):
        if self.profit_currency != self.settlement_currency:
            raise ValueError(
                "This contract version only describes linear same-currency settlement."
            )
        return self


Instrument = Annotated[
    CryptoSpotInstrument | CryptoLinearInstrument | CfdInstrument | TradfiPerpetualInstrument,
    Field(discriminator="product"),
]
instrument_adapter = TypeAdapter(Instrument)
