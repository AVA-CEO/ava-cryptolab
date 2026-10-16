"""CFD calculation input contract, separate from the working crypto trade API."""

from decimal import Decimal, localcontext
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.account import AccountContract
from app.schemas.cfd_snapshot import CfdSnapshotInput
from app.schemas.financial import (
    CurrencyConversionInput,
    FinancialContract,
    FinancialSource,
    PositiveFinancialDecimal,
    SignedMoneyDecimal,
    ZonedTime,
    is_increment,
)
from app.schemas.instrument import CurrencyCode, Identifier
from app.schemas.multi_asset import JournalContract


class CfdExecutionInput(FinancialContract):
    """One actual fill; a volume-weighted aggregate is not an individual fill."""

    execution_id: Identifier
    executed_at: ZonedTime
    price: PositiveFinancialDecimal
    lots: PositiveFinancialDecimal
    profit_conversion_id: Identifier | None = None


class CfdAdjustmentInput(FinancialContract):
    """An incurred cash flow: debit negative, credit positive; never a rate."""

    adjustment_id: Identifier
    kind: Literal["commission", "swap", "fee", "other"]
    amount: SignedMoneyDecimal
    currency: CurrencyCode
    occurred_at: ZonedTime
    source: FinancialSource
    description: Annotated[str, Field(min_length=1, max_length=300)]
    execution_id: Identifier | None = None
    conversion_id: Identifier | None = None


class CfdTradeInput(FinancialContract):
    """Validation only: no PnL, account assignment, network or persistence.

    native_only deliberately leaves cross-currency totals unavailable. With
    explicit_rates, each relevant cash flow and original stop-risk input needs
    a directed observation at its own time. No USD/USDT parity is assumed.
    """

    schema_version: Literal["cfd-input-v1"] = "cfd-input-v1"
    account: AccountContract
    snapshot: CfdSnapshotInput
    direction: Literal["buy", "sell"]
    entry: CfdExecutionInput
    exits: Annotated[tuple[CfdExecutionInput, ...], Field(max_length=1000)] = ()
    original_stop: PositiveFinancialDecimal | None = None
    planned_take_profit: PositiveFinancialDecimal | None = None
    adjustments: Annotated[tuple[CfdAdjustmentInput, ...], Field(max_length=1000)] = ()
    reporting_policy: Literal["native_only", "explicit_rates"]
    conversions: Annotated[tuple[CurrencyConversionInput, ...], Field(max_length=2001)] = ()
    risk_conversion_id: Identifier | None = None

    @model_validator(mode="after")
    def coherent_trade(self):
        spec = self.snapshot.specification
        JournalContract(account=self.account, instrument=spec)
        if self.entry.profit_conversion_id is not None:
            raise ValueError(
                "An entry has no realized profit; use risk_conversion_id for stop risk."
            )
        if spec.source.effective_at > self.entry.executed_at:
            raise ValueError("The snapshot must be effective on or before entry.")
        for value in (
            spec.pip_value_per_lot,
            spec.tick_value_profit_per_lot,
            spec.tick_value_loss_per_lot,
        ):
            if value is not None and value.observed_at > self.entry.executed_at:
                raise ValueError("An entry snapshot cannot use future pip/tick value observations.")

        fills = (self.entry, *self.exits)
        fill_by_id = {fill.execution_id: fill for fill in fills}
        if len(fill_by_id) != len(fills):
            raise ValueError("Execution IDs must be unique across entry and exits.")
        for fill in fills:
            if not is_increment(fill.price, spec.tick_size):
                raise ValueError(f"Execution {fill.execution_id}: price must align with tick size.")
            if fill.lots < spec.volume_min or (
                spec.volume_max is not None and fill.lots > spec.volume_max
            ):
                raise ValueError(f"Execution {fill.execution_id}: lots outside declared bounds.")
            if not is_increment(fill.lots, spec.volume_step):
                raise ValueError(f"Execution {fill.execution_id}: lots must align with lot step.")
        times = [fill.executed_at for fill in fills]
        if times != sorted(times):
            raise ValueError("Exits must follow entry and be supplied in chronological order.")
        with localcontext() as context:
            context.prec = 80
            if sum((fill.lots for fill in self.exits), Decimal(0)) > self.entry.lots:
                raise ValueError("Exit lots cannot exceed original entry lots.")

        for label, price in (
            ("original_stop", self.original_stop),
            ("planned_take_profit", self.planned_take_profit),
        ):
            if price is not None:
                if not is_increment(price, spec.tick_size):
                    raise ValueError(f"{label} must align with the tick size.")
                correct_side = (
                    price < self.entry.price
                    if self.direction == "buy"
                    else price > self.entry.price
                )
                if label == "planned_take_profit":
                    correct_side = (
                        price > self.entry.price
                        if self.direction == "buy"
                        else price < self.entry.price
                    )
                if not correct_side:
                    raise ValueError(f"{label} is on the wrong side of entry for {self.direction}.")

        adjustments = {item.adjustment_id: item for item in self.adjustments}
        if len(adjustments) != len(self.adjustments):
            raise ValueError("Adjustment IDs must be unique; do not recognize a cost twice.")
        for item in self.adjustments:
            if item.execution_id is not None and item.execution_id not in fill_by_id:
                raise ValueError("Adjustment references an unknown execution ID.")
            earliest = (
                fill_by_id[item.execution_id].executed_at
                if item.execution_id is not None
                else self.entry.executed_at
            )
            if item.occurred_at < earliest:
                raise ValueError(
                    "An incurred adjustment cannot predate its entry/linked execution."
                )
        self._validate_conversions()
        return self

    def _validate_conversions(self):
        observations = {item.conversion_id: item for item in self.conversions}
        if len(observations) != len(self.conversions):
            raise ValueError("Conversion IDs must be unique.")
        used = set()
        target = self.account.reporting_currency

        def check(reference, currency, at):
            if self.reporting_policy == "native_only":
                if reference is not None:
                    raise ValueError("native_only does not accept conversion references.")
                return
            if currency == target:
                if reference is not None:
                    raise ValueError("Same-currency amounts must not reference a conversion.")
                return
            observation = observations.get(reference)
            if observation is None:
                raise ValueError(f"Explicit conversion from {currency} to {target} is required.")
            if (observation.from_currency, observation.to_currency) != (currency, target):
                raise ValueError("Conversion currency direction does not match the amount/account.")
            if observation.applies_at != at:
                raise ValueError("Conversion applies_at must match the referenced amount's time.")
            used.add(reference)

        valuation_currency = self.snapshot.specification.valuation_currency
        for fill in self.exits:
            check(fill.profit_conversion_id, valuation_currency, fill.executed_at)
        for item in self.adjustments:
            check(item.conversion_id, item.currency, item.occurred_at)
        if self.original_stop is None:
            if self.risk_conversion_id is not None:
                raise ValueError("A risk conversion requires an original planned stop.")
        else:
            check(self.risk_conversion_id, valuation_currency, self.entry.executed_at)
        if set(observations) != used:
            raise ValueError("Unreferenced conversions are not accepted; check policy and IDs.")
