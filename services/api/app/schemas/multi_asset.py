"""Draft validation boundary; deliberately separate from the existing trade API."""

from typing import Literal

from pydantic import model_validator

from app.schemas.account import AccountContract
from app.schemas.instrument import ContractModel, Instrument


class JournalContract(ContractModel):
    schema_version: Literal["journal-contract-v1"] = "journal-contract-v1"
    account: AccountContract
    instrument: Instrument

    @model_validator(mode="after")
    def compatible_account(self):
        if self.account.broker != self.instrument.broker:
            raise ValueError("Account and instrument must belong to the same broker.")
        if self.account.settlement_currency != self.instrument.settlement_currency:
            raise ValueError("Account and instrument settlement currencies must match explicitly.")
        if self.account.platform == "mt5" and self.instrument.product != "cfd":
            raise ValueError("This milestone describes MT5 CFD accounts only.")
        if self.account.platform == "mt5" and self.account.server != self.instrument.venue:
            raise ValueError("MT5 instrument specifications must match the account server.")
        return self
