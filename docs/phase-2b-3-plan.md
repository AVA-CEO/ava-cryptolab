# Phase 2B.3 proposal — Forex and CFD calculation engines

Status: planning only. The owner moved calculation engines ahead of account-management screens. GitHub validation and final approval/application/verification of the normal database migration come first. No calculator, broker connection, CFD-entry screen or schema change is implemented by this plan.

## Architecture and purpose

Build pure Python calculation functions around the versioned CFD instrument contracts and historical snapshots already defined. Pure means the same explicit inputs produce the same answer, without fetching prices, connecting to a broker or writing a database. Reuse Decimal arithmetic and existing validation conventions. Keep the current crypto calculator and its outputs unchanged.

An explicit product dispatcher will select the appropriate engine; it must never send a CFD into crypto quantity math. Start with supported forex and linear CFD modes, then handle declared index/tick modes only when their required inputs and broker rules are verified. Unsupported modes return an explicit unavailable/error result. TradFi perpetuals stay a separate product category rather than borrowing CFD rules.

Account-management and manual CFD-entry UI work follows in 2B.4, split into account workflow and conditional forms. Engine completion alone does not mean users can save CFD trades. It also does not authorize statement imports or synchronization.

## Proposed formulas and units

Let `s` be +1 for a buy/long and -1 for a sell/short, `L` closed lots, `C` contract units per lot and `delta` exit price minus entry price.

| Result                                                 | Rule and boundary                                                                                                                                                  |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Gross PnL for supported linear forex/CFD modes         | `s × delta × L × C`, in the instrument's profit currency                                                                                                           |
| Tick-based gross PnL                                   | `s × delta / tick_size × L × applicable_tick_value_per_lot`, only with verified historical tick value/currency; distinguish profit/loss tick values where required |
| Signed pip movement                                    | `s × delta / pip_size`, only if an explicit pip size exists                                                                                                        |
| Per-lot pip value for supported linear modes           | `C × pip_size`, initially in profit currency; reporting-currency value requires an explicit conversion observation                                                 |
| Net PnL                                                | Gross plus signed commissions, swaps, fees and other recorded adjustments, after bringing amounts into the declared common currency                                |
| Original planned price risk for supported linear modes | `abs(entry - original_stop) × original_lots × C`; this is a stop-price estimate, not guaranteed loss or margin                                                     |
| Realized R                                             | Recorded net PnL divided by valid original planned risk, expressed on a documented consistent currency basis; unavailable when original risk is missing or zero    |

These rules follow supported contract calculation modes, not a universal CFD formula. MT5 documents distinct calculation modes and tick values. Current-terminal profit estimation is not proof of historical conversions. References: [MT5 symbol/calculation properties](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants), [MT5 profit estimation](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py).

For the new CFD cash-flow inputs, use explicit signed adjustments: positive is a credit and negative a debit. Preserve timestamps and currency for each adjustment. Translate broker columns explicitly during later import work. Do not change the existing crypto convention where positive funding represents paid funding.

Execution prices already include the bid/ask spread. Record spread for analysis or a clearly labelled hypothetical estimate, but do not subtract it again from actual fill-based PnL. Leverage is not an extra PnL multiplier. Broker margin and liquidation values remain separately reported, not inferred from planned risk.

## Synthetic teaching example

Assume a hypothetical EURUSD contract with 100,000 units per lot, 0.1 lots, buy entry 1.10000, exit 1.10100, original stop 1.09900 and pip size 0.0001. These are synthetic inputs, not current Bybit specifications or a market recommendation.

- Gross: `0.00100 × 0.1 × 100000 = 10 USD`.
- Pip movement: `0.00100 / 0.0001 = 10 pips`.
- Commission debit 3 USD and swap debit 1 USD give net 6 USD.
- Initial planned price risk is 10 USD, giving 0.6R for this fully closed example.

Changing leverage alone must not change those profit figures. Changing contract size or lots does change them.

## Currency, costs and partial exits

Profit, reporting and settlement currencies are distinct. Store native amounts. Convert each realized cash flow with an explicit rate, direction, source, timestamp and rounding policy when reporting currency differs. Missing conversions produce unavailable reporting totals, not zero or assumed USD/USDT/USDx parity. Do not revalue historical results using today's rates.

For multiple exits, calculate each closed lot quantity and sum gross results. Track remaining lots and reject over-closing. Retain original stop/risk for R; current remaining-position stop risk is a different measure. Define incurred commission/swap recognition and any allocation explicitly, and do not duplicate costs already included in broker-reported net PnL. No unrealized PnL is invented for open lots.

Preserve broker-reported gross/net PnL separately from calculated figures, with their stated inclusion of costs. Later reconciliation shows differences without replacing the original evidence. No broker reconciliation claim is possible until redacted sample statements and historical specifications are available.

## Likely files

- New `services/api/app/analytics/cfd.py`: pure per-mode gross/net/risk/pip calculations.
- New `services/api/app/schemas/cfd.py`: validated lots, executions, signed money adjustments and explicit conversions, reusing instrument contracts.
- A small product dispatcher module: reject unsupported products instead of silently falling back to crypto.
- New CFD calculation fixtures/tests, plus unchanged crypto regression tests.
- This documentation and `docs/learning-journal.md`.

No new database migration or TypeScript form change is proposed for the initial engine step. Later form/API integration will receive its own file plan and acceptance checks before coding.

## Test and teaching strategy

1. Hand-worked synthetic long/short EURUSD, JPY/cross pairs, XAUUSD/XAGUSD and supported index/tick examples with declared units and currencies.
2. Zero movement, fractional lots, exact lot/tick increments, minimum/maximum volume, large/small decimals and rounding at reporting boundaries.
3. Commission rebates/debits, signed swaps, fees, no spread double counting and no leverage multiplier.
4. Partial exits, remaining lots, over-close rejection, missing/invalid initial stops and zero-risk division prevention.
5. Missing/wrong-direction/stale conversion observations and non-equivalence of currency codes. Reporting output must disclose coverage and assumptions.
6. Invariants: a linear long/short sign reversal flips gross PnL; doubling lots doubles gross PnL for unchanged contract data; costs affect net without altering gross.
7. Keep all existing backend tests, especially crypto calculations, passing. Reconcile against permitted sanitized broker samples when supplied; synthetic expected values are not broker evidence.

Before coding, walk through the example together, identify units on every multiplication and explain each field. After coding, provide exact test commands and an in-memory example; report actual results and unresolved limits. The milestone teaches separation of financial models, Decimal precision, pure functions, product dispatch and testable accounting policies.
