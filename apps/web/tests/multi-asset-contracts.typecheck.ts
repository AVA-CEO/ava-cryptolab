/** Compile-time assertions: checked by npm run typecheck; no broker calls. */
import type {
  CfdInstrument,
  CryptoLinearInstrument,
  Instrument,
  TradfiPerpetualInstrument,
} from "../src/features/journal/multi-asset-contracts";

export function checkProductNarrowing(instrument: Instrument) {
  if (instrument.product === "cfd") {
    const lots: "lots" = instrument.quantity_unit;
    const contractSize: string = instrument.contract_size;
    // @ts-expect-error CFD specifications must not expose crypto funding.
    const invalidFunding = instrument.funding;
    void invalidFunding;
    return [lots, contractSize];
  }
  if (instrument.product === "crypto_linear_futures") {
    const units: "base_units" = instrument.quantity_unit;
    // @ts-expect-error Crypto specifications must not inherit CFD lot sizes.
    const invalidContractSize = instrument.contract_size;
    void invalidContractSize;
    return [units, instrument.calculation_mode];
  }
  if (instrument.product === "tradfi_perpetual") {
    return [instrument.contract_multiplier, instrument.calculation_mode];
  }
  return [instrument.base_currency, instrument.calculation_mode];
}

// @ts-expect-error A CFD cannot use base-asset quantity units.
export const invalidCfdUnit: CfdInstrument["quantity_unit"] = "base_units";
// @ts-expect-error Crypto linear products cannot use a forex calculator.
export const invalidCryptoMode: CryptoLinearInstrument["calculation_mode"] =
  "forex";
// @ts-expect-error A TradFi perpetual is separate from a CFD.
export const invalidPerpetual: TradfiPerpetualInstrument["product"] = "cfd";
