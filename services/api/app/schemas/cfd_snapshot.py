"""Stricter CFD input view of the existing instrument-v1 snapshot format.

No existing persisted specifications are rewritten or re-versioned. These
rules apply only when preparing new CFD calculation inputs.
"""

import hashlib
import json
from typing import Annotated

from pydantic import Field, model_validator

from app.schemas.financial import (
    FinancialContract,
    PositiveFinancialDecimal,
    ZonedTime,
    is_increment,
)
from app.schemas.instrument import CfdInstrument, Identifier, MoneyValue, SpecificationSource


class CfdSpecificationSource(SpecificationSource):
    model_config = FinancialContract.model_config
    effective_at: ZonedTime
    captured_at: ZonedTime


class CfdMoneyObservation(MoneyValue):
    model_config = FinancialContract.model_config
    amount: PositiveFinancialDecimal
    observed_at: ZonedTime


class CfdSpecificationInput(CfdInstrument):
    model_config = FinancialContract.model_config
    source: CfdSpecificationSource
    tick_size: PositiveFinancialDecimal
    volume_min: PositiveFinancialDecimal
    volume_step: PositiveFinancialDecimal
    volume_max: PositiveFinancialDecimal | None = None
    contract_size: PositiveFinancialDecimal
    pip_size: PositiveFinancialDecimal | None = None
    pip_value_per_lot: CfdMoneyObservation | None = None
    tick_value_profit_per_lot: CfdMoneyObservation | None = None
    tick_value_loss_per_lot: CfdMoneyObservation | None = None

    @model_validator(mode="after")
    def consistent_units(self):
        # This first input version supports a zero-origin volume/price grid.
        # Reject ambiguous broker rules rather than rounding or inventing them.
        if not is_increment(self.volume_min, self.volume_step):
            raise ValueError("Minimum lots must align with the declared lot step in this version.")
        if self.pip_size is not None and not is_increment(self.pip_size, self.tick_size):
            raise ValueError("Pip size must be a whole multiple of the declared tick size.")
        profit, loss = self.tick_value_profit_per_lot, self.tick_value_loss_per_lot
        if (profit is None) != (loss is None):
            raise ValueError("Supply both profit/loss tick observations, or neither.")
        if profit is not None and (
            profit.currency != loss.currency or profit.observed_at != loss.observed_at
        ):
            raise ValueError(
                "Profit/loss tick observations must share currency and observation time."
            )
        for value in (self.pip_value_per_lot, profit, loss):
            if value is not None and value.observed_at > self.source.captured_at:
                raise ValueError("Value observations cannot postdate specification capture.")
        return self

    @property
    def valuation_currency(self):
        """Label the supplied valuation unit without calculating a profit.

        Tick-mode values can already be denominated in an account currency.
        Never relabel those observations as the underlying profit currency.
        """
        if self.calculation_mode == "futures_tick":
            return self.tick_value_profit_per_lot.currency
        return self.profit_currency


class CfdSnapshotInput(FinancialContract):
    """Frozen values plus integrity digest, compatible with existing storage.

    A digest detects changed content; it is not a broker signature or proof that
    the supplied ID exists. Database binding belongs to a later API milestone.
    """

    snapshot_id: Identifier
    content_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    specification: CfdSpecificationInput

    @model_validator(mode="after")
    def intact_content(self):
        # Same canonical representation as services.multi_asset.content_digest.
        canonical = json.dumps(
            self.specification.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        expected = hashlib.sha256(canonical.encode()).hexdigest()
        if self.content_sha256 != expected:
            raise ValueError("Snapshot content does not match its SHA-256 fingerprint.")
        return self
