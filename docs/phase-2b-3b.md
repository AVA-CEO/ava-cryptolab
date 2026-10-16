# Milestone 2B.3B — single-close forex and CFD engine

Status: **implemented locally with owner authorization**. The engine supports one entry and one exit closing all lots, with no new dependencies, migrations, API routes, forms, broker calls or database writes. The normal journal and verified backups are not calculation/test targets. The premium purple UI is unchanged.

## Architecture and files

| File                                                             | Responsibility                                                                                                       |
| ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `services/api/app/analytics/cfd.py`                              | Pure Decimal validation boundary, supported-mode gate, linear cash accounting, explicit FX and presentation rounding |
| `services/api/app/schemas/cfd_results.py`                        | Frozen request/rounding/result contracts; currency-labelled raw and rounded amounts, unavailable reasons             |
| `services/api/app/analytics/products.py`                         | Explicit opt-in CFD/legacy-crypto dispatch; no automatic fallback                                                    |
| `services/api/scripts/calculate_cfd.py`                          | Read a local JSON request and print readable or JSON results; exit 0 for calculated, 1 for unavailable/invalid       |
| `services/api/tests/fixtures/cfd-calculation.synthetic.json`     | Synthetic, fully closed EURUSD example                                                                               |
| `services/api/tests/fixtures/cfd-jpy-calculation.synthetic.json` | Synthetic JPY native profit and explicit USD reporting example                                                       |
| `services/api/tests/cfd_calculation_examples.py`                 | Synthetic request builders, tests only                                                                               |
| `services/api/tests/test_cfd_calculations.py`                    | Hand-worked answers, independent cash ledgers, product/input/scope rules                                             |
| `services/api/tests/test_cfd_rounding.py`                        | Decimal context isolation, exact cash/FX arithmetic, rounding and original-risk precision                            |
| `services/api/tests/test_product_calculators.py`                 | Pure CFD import boundary and unchanged crypto semantics/dispatch/margin regressions                                  |
| `services/api/tests/test_cfd_calculation_script.py`              | Runnable examples and safe error output                                                                              |

The existing `analytics/trades.py`, journal routes, models, persistence services, old input contracts and migrations are unchanged. The dispatcher is available for later reviewed integration; existing UI/API routes continue using their current implementation. New result models are Python contracts, not database tables.

## Supported formulas and units

The allowlist is explicit: `forex` with category forex; `cfd_linear` with metals, indices, energy, equities or other; `cfd_index` with indices. Those declared linear profit modes use the formulas below. `futures_tick`, incompatible category/mode pairs and TradFi perpetuals have no calculation fallback. Broker symbol text alone does not choose a formula or contract size.

For `s = +1` buy or `−1` sell, exit `X`, entry `E`, lots `L` and supplied units-per-lot `C`:

| Quantity                    | Formula and currency                                                                               |
| --------------------------- | -------------------------------------------------------------------------------------------------- |
| Directional price movement  | `s × (X − E)`; positive is favourable to the trade direction                                       |
| Gross PnL                   | `s × (X − E) × L × C`, in the recorded instrument profit currency                                  |
| Pips                        | Directional movement ÷ supplied pip size; unavailable if no pip size is supplied                   |
| Ticks                       | Directional movement ÷ supplied tick size; this is a movement count, not tick-mode money valuation |
| Original planned price risk | `abs(E − original_stop) × original_lots × C`; unavailable without the original stop                |
| Net PnL                     | Gross plus all supplied incurred signed adjustments, once, on a valid common currency basis        |
| Realized R                  | Unrounded net ÷ unrounded original risk on the group's currency basis                              |

Amounts are not multiplied again by leverage. Actual fill prices already incorporate execution at bid/ask; no guessed spread is subtracted again. No CFD margin or liquidation estimate is produced without a separate broker-rule contract. Planned price risk excludes assumed slippage/future costs and is not a guaranteed loss or broker margin requirement. Existing crypto margin behavior remains unchanged.

## Currency and unavailable-result policies

Native gross is calculated and labelled before any reporting conversion. Recorded adjustments retain their original currency totals. Each explicit conversion is source→target, with target units per source unit, source reference, observed/applies timestamps and chosen allowed age. The 2B.3A validator checks its binding before calculation. No inversion, cross-rate construction, live lookup, default rate or USD/stablecoin equivalence occurs.

- `native_only` keeps known native results. Reporting values are available directly when their currencies match; amounts requiring FX remain unavailable. A foreign fee is not silently dropped from net PnL.
- `explicit_rates` requires correctly linked evidence for each differing-currency exit/cost and entry-time original risk. Each cost is converted at its own supplied application time, then added without rounding. Risk uses its entry-time observation, not the exit's rate.
- Native net is available when every cost is already native, or when the account reports native currency and explicit cost conversions produce that currency. Otherwise native net/R remain unavailable while reporting net may still be available. A JPY gross result with USD fees does not acquire a fabricated JPY net result.
- Native and reporting R can differ when currency rates vary across entry, exit and costs. Both use the original risk denominator for their declared basis. Missing stop means missing risk/R, not zero.

Invalid required inputs return an overall `unavailable` result with safe field-path diagnostics. Unsupported modes/products or open/partial/multiple-exit CFD positions also return unavailable. No partial accounting is performed. If a valid `native_only` request lacks reporting conversion coverage, the overall result can be calculated while affected individual fields carry `null` raw/rounded values and a reason. This preserves known facts without claiming unavailable totals.

Validation proves internal consistency, not that an account ID, specification source or rate was authenticated by a broker. Snapshot checks detect changed content; real binding to stored rows belongs to later authorized service integration. No real broker statement has been reconciled in this milestone.

## Precision and display rules

All monetary inputs and operations use Decimal. Inputs preserve the 2B.3A limits. Output amounts may exceed input-field bounds after multiplication; output schemas therefore allow finite exact Decimal results without incorrectly truncating them to input precision.

A fresh 160-digit context explicitly fixes precision, rounding, exponent limits and arithmetic traps. For bounded 18-decimal-place factors, cash products/conversions require at most four such factors and money addition remains within that precision. Tests compare extreme products and cash ledgers with exact `Fraction` arithmetic. Working ratios and potentially repeating pip divisions use 160-digit HALF_EVEN precision. Caller/global Decimal settings cannot change results or be changed by the engine.

The request must supply per-currency display decimal places, R/movement decimal places (0–18) and HALF_EVEN or HALF_UP. No currency precision is guessed. Display `rounded` values are created with Decimal quantization; raw values remain available as JSON strings. Net is formed from unrounded cash flows, and R uses unrounded net/risk. Outcomes use raw net sign even if a tiny amount displays as zero. Display rounding is not a broker settlement-rounding/reconciliation policy; individually displayed amounts may not sum to the displayed aggregate after conversion.

## Run the synthetic example

No new environment configuration or restart is required. From the repository root:

```powershell
.\.venv\Scripts\python.exe services/api/scripts/calculate_cfd.py services/api/tests/fixtures/cfd-calculation.synthetic.json
.\.venv\Scripts\python.exe services/api/scripts/calculate_cfd.py services/api/tests/fixtures/cfd-jpy-calculation.synthetic.json
```

Add `--json` for complete raw values, original currency cost totals, FX evidence, snapshot reference and rounding policy. The script reads the request only. Inputs and outputs contain no actual journal records.

### Explain every EURUSD output number

| Output                                     | Explanation                                                                              |
| ------------------------------------------ | ---------------------------------------------------------------------------------------- |
| 0.10 lots × 100,000 units/lot              | The supplied snapshot and quantity describe 10,000 units; not a hardcoded broker default |
| Entry 1.10000; exit 1.10100                | Synthetic recorded execution prices, expressed as quote price per unit                   |
| Directional change 0.001000                | Buy exit minus entry; displayed at six movement decimals                                 |
| 10.000000 pips                             | 0.00100 ÷ declared pip size 0.0001                                                       |
| 100.000000 ticks                           | 0.00100 ÷ declared tick size 0.00001                                                     |
| Gross 10.00 USD                            | 0.00100 × 0.10 × 100,000                                                                 |
| Adjustments −4.00 USD                      | Commission −3 plus incurred swap −1, counted once                                        |
| Net 6.00 USD                               | Gross 10 plus adjustments −4                                                             |
| Original planned risk 10.00 USD            | Entry 1.10000 minus original stop 1.09900, multiplied by original units                  |
| Realized 0.600000R                         | Unrounded net 6 ÷ original risk 10; six ratio display decimals                           |
| Account reporting repeats those USD values | Profit and account reporting currencies match; no FX rate is needed                      |
| HALF_EVEN; 160 digits                      | Explicit display tie-breaking policy and fixed internal calculation precision            |

The JPY example uses an explicitly supplied synthetic 0.0065 USD per JPY observation: 1,000 JPY gross becomes 6.50 USD gross. USD costs total −4, giving 2.50 USD net. Original risk is 1,000 JPY, converted at its entry-time observation to 6.50 USD; reporting R is 0.384615 when displayed at six decimals. Native JPY net/R remain unavailable because the USD costs have no JPY valuation policy. None of these prices, sizes or FX rates is presented as current Bybit data.

## Validation record

- Original baseline: **266 tests passed** before implementation.
- Final backend suite: **357 passed**, including **91 new cases**. Tests cover signed long/short EURUSD/GBPUSD, JPY/cross-pair and metals calculations, costs/credits, breakeven, missing/invalid inputs, explicit FX timing, original risk/R, rounding/precision, crypto regression and CLI/import isolation.
- Python lint and formatting passed; 63 Python files are formatted.
- Frontend lint, TypeScript checks and production build passed. Build used `.next-e2e` and an unreachable API address, excluding the normal journal API.
- All **10 desktop/mobile browser tests passed** using their temporary database/API on port 8001 and frontend on port 3100. Color-environment and reduced-motion notices were informational.
- Repository formatting and whitespace checks passed. The documented synthetic loss exercise was independently run and produced −10 USD gross, −14 USD net, 10 USD risk and −1.4R.
- The normal journal and both verified backups retained their start-of-milestone byte fingerprints. Read-only API health and journal-page checks returned HTTP 200. No normal data or backup writes occurred.
- Hand-worked expectations are literal test answers. Independent rational cash ledgers calculate sale proceeds minus original cash cost and verify Decimal output, including extreme conversion products. No expected answer is generated by the calculator under test.

During preparation, formatting/import-order findings and a typo in the temporary fixture-generation command were corrected before final checks. The final backend run exited successfully. The existing Starlette/httpx test-client deprecation warning remains; no dependency change was made as part of this financial milestone.

Tests run only on synthetic inputs and disposable databases. A private read-only fingerprint report records normal-journal and backup preservation; private file paths, actual records and checksums are excluded from source documentation. No further normal migration or historical account/instrument assignment is authorized here.

## What comes next

Review the [2B.3C plan](phase-2b-3c-plan.md) before authorizing partial-closure and broker-comparison implementation. The current engine deliberately rejects partial/multiple exits, including a multi-exit position whose lots eventually total the entry. Tick-mode historical valuation remains outside the linear-engine scope. Existing CFD validation can describe more inputs than this calculator supports.

Official references checked: [MT5 symbol calculation modes](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants) distinguish linear and tick-based profit rules; [Python 3.13 Decimal documentation](https://docs.python.org/3.13/library/decimal.html) documents contexts, quantization and rounding. This implementation does not call MT5 or assert real broker reconciliation.
