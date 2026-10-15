"""Future account identity. No balances, credentials or account creation yet."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.instrument import ContractModel, CurrencyCode, Identifier


class AccountContract(ContractModel):
    schema_version: Literal["account-v1"] = "account-v1"
    account_id: Identifier
    name: Annotated[str, Field(min_length=1, max_length=100)]
    broker: Identifier
    platform: Literal["manual", "bybit", "mt5"]
    # Non-secret user label/reference; never a password, token or API key.
    broker_account_ref: Identifier | None = None
    server: Identifier | None = None
    reporting_currency: CurrencyCode
    settlement_currency: CurrencyCode

    @model_validator(mode="after")
    def terminal_identity(self):
        if self.platform == "mt5" and self.server is None:
            raise ValueError("MT5 account identity requires a broker server label.")
        return self
