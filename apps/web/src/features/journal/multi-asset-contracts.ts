/** Draft wire contracts. Not accepted by the current crypto-only trade API.
 * Monetary/quantity values stay decimal strings; Python validates at runtime.
 */
export type AssetCurrency = string;
export type DecimalString = string;
export type TraditionalMarket =
  "forex" | "metals" | "indices" | "energy" | "equities" | "other";

export type AccountContract = {
  readonly schema_version: "account-v1";
  readonly account_id: string;
  readonly name: string;
  readonly broker: string;
  readonly platform: "manual" | "bybit" | "mt5";
  readonly broker_account_ref: string | null;
  readonly server: string | null;
  readonly reporting_currency: AssetCurrency;
  readonly settlement_currency: AssetCurrency;
};

export type SpecificationSource = {
  readonly kind: "manual" | "statement" | "broker_api" | "terminal";
  readonly reference: string;
  readonly effective_at: string;
  readonly captured_at: string;
};

export type MoneyValue = {
  readonly amount: DecimalString;
  readonly currency: AssetCurrency;
  readonly observed_at: string;
};

type InstrumentBase = {
  readonly schema_version: "instrument-v1";
  readonly instrument_id: string;
  readonly symbol: string;
  readonly broker: string;
  readonly venue: string;
  readonly profit_currency: AssetCurrency;
  readonly settlement_currency: AssetCurrency;
  readonly tick_size: DecimalString;
  readonly volume_min: DecimalString;
  readonly volume_step: DecimalString;
  readonly volume_max: DecimalString | null;
  readonly source: SpecificationSource;
};

type CryptoFields = InstrumentBase & {
  readonly market_category: "crypto";
  readonly quantity_unit: "base_units";
  readonly base_currency: AssetCurrency;
  readonly quote_currency: AssetCurrency;
};

export type CryptoSpotInstrument = CryptoFields & {
  readonly product: "crypto_spot";
  readonly calculation_mode: "spot_inventory";
};

export type CryptoLinearInstrument = CryptoFields & {
  readonly product: "crypto_linear_futures";
  readonly calculation_mode: "linear_quote";
};

export type CfdInstrument = InstrumentBase & {
  readonly product: "cfd";
  readonly market_category: TraditionalMarket;
  readonly calculation_mode:
    "forex" | "cfd_linear" | "cfd_index" | "futures_tick";
  readonly quantity_unit: "lots";
  readonly contract_size: DecimalString;
  readonly pip_size: DecimalString | null;
  readonly pip_value_per_lot: MoneyValue | null;
  readonly tick_value_profit_per_lot: MoneyValue | null;
  readonly tick_value_loss_per_lot: MoneyValue | null;
};

export type TradfiPerpetualInstrument = InstrumentBase & {
  readonly product: "tradfi_perpetual";
  readonly market_category: TraditionalMarket;
  readonly calculation_mode: "linear_contract";
  readonly quantity_unit: "contracts" | "base_units";
  readonly contract_multiplier: DecimalString;
};

export type Instrument =
  | CryptoSpotInstrument
  | CryptoLinearInstrument
  | CfdInstrument
  | TradfiPerpetualInstrument;

export type JournalContract = {
  readonly schema_version: "journal-contract-v1";
  readonly account: AccountContract;
  readonly instrument: Instrument;
};
