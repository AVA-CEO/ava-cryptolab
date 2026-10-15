# Multi-asset journal: proposed development milestone

Status: design approved; Phase 2B implementation subsequently authorized by the owner.

Phase 2 manual acceptance is complete: the owner reported all nine scenarios passed in the isolated practice journal. See the [acceptance report](phase-2-acceptance.md). The owner subsequently authorized **Phase 2B, before Phase 3**, following the [milestone plan](phase-2b-plan.md). Application work and migration development proceed in those increments; the initial contract milestone makes no database changes. Broker connections, scheduled synchronization, remote pushes and deployment remain separately gated.

## Product and interface

Preserve existing journal functionality, exact Python financial calculations, automated tests, and the premium purple identity. Green denotes gains/success; red denotes losses. Manual entries and broker statement imports come first.

Keep market category separate from product type:

| Market category                         | Product type                                                 |
| --------------------------------------- | ------------------------------------------------------------ |
| Cryptocurrency                          | Spot; linear futures/perpetuals                              |
| Forex                                   | CFD                                                          |
| Metals, including XAUUSD and XAGUSD     | CFD; separately identified TradFi perpetuals where supported |
| Other supported traditional instruments | Contract-specific CFD or perpetual                           |

The form selects account, market category, product and instrument, then shows appropriate fields. Unsupported contract calculation modes must be explicit, not mapped to crypto calculations.

## Accounts and ownership

Support independent accounts with broker/server identity, account currency, settlement assets, balances, trade/execution histories, risk settings and analytics. Broker accounts are distinct even when currencies match. Do not infer legacy account assignments without sufficient evidence and owner review.

Model deposits, withdrawals, transfers, credits and adjustments separately from trading PnL. Link internal transfers to avoid double counting in consolidated reporting. Keep broker balance, equity, available funds and margin distinct, with source and observation time. Account and record access must respect the authenticated owner boundary before any remote multiuser use.

## Contract specifications and calculations

Preserve existing spot inventory and linear quote-settled crypto calculations, including quantity, fees and funding. Add separate CFD calculators dispatched by supported contract calculation mode.

CFD records support lots, contract size, volume increments, tick size/value, pip size/value, profit currency, account reporting currency, settlement asset, executions, initial stop/target, commissions, signed swaps, adjustments, spread observations, leverage, reported margin and broker PnL. Values requiring currency or time context must retain both.

Snapshot instrument specifications per trade with source, effective time and calculation version. Do not silently recalculate history from today's contract settings. Pip and tick sizes are separate; pip value can change with conversion rates. Leverage is not a PnL multiplier. Execution prices already reflect spread, so spread must not be deducted twice. Missing specifications or initial risk produce unavailable metrics rather than guesses.

Preserve calculated and broker-reported gross/net PnL separately. Record reconciliation differences and the explicitly selected accounting basis used by analytics. Never add both versions of the same profit. Handle partial closes, scale-ins, reversals and hedging/netting according to documented allocation rules. Unknown original stops cannot be reconstructed from final stops for realized R.

## Currency policy and consolidated analytics

Provide account-specific and product-specific views, including Crypto Futures and Forex CFDs, plus a combined dashboard. Keep USD, USDx, USDT and other assets distinct; a documented broker conversion rule is not permission to assume general parity.

Conversions require a versioned policy specifying reporting currency, rate direction, source, timestamp, historical cash-flow conversion versus current valuation, rounding and missing-rate behavior. Preserve native amounts and conversion provenance. Missing/stale rates must be disclosed; exclude unconvertible amounts and show coverage rather than silently understating totals.

Recompute consolidated expectancy, profit factor and drawdown from eligible converted observations; do not average account ratios. Combine accounts on a common timeline. Separate cash-flow-adjusted performance from changes caused by deposits, withdrawals and transfers. Label realized closed-trade drawdown separately from broker equity or mark-to-market drawdown.

Trading IQ retains its minimum 20 closed trades overall and 5 observations per compared group. Show account/product cohort, currency policy, evidence coverage and rule version. These thresholds do not establish statistical significance or prediction.

## Unified risk dashboard

Planned views include per-account and consolidated exposure, initial planned risk, remaining open-position stop risk, realized losses, drawdown and concentration by instrument, underlying, asset class, currency and broker/account. Keep initial planned risk fixed for R calculations; current remaining risk is a separate measure. Define gross and net exposure explicitly and avoid assuming positions at different brokers offset operational risk.

Account risk settings should support owner-defined trade, open-risk, daily loss, drawdown and concentration limits, with currency, percentage denominator and reset timezone stated. Unknown balances or equity make percentage-based measures unavailable.

Stop-based risk is an estimate: execution gaps, slippage and currency movement can change losses. Missing stops create unknown risk coverage, not zero risk. Realized losses and fees are actual recorded outcomes; aggregate open stop risk is not portfolio maximum loss. Scenarios and correlation analysis require adequate data and disclosed assumptions.

Display actual broker margin, free margin, margin level and reported liquidation information only when available, with timestamps. Label calculated margin estimates separately. Never treat planned risk, notional, margin and liquidation requirements as equivalent. Cross-margin liquidation cannot be inferred from a single isolated trade.

## Statement import adapter

Confirm the actual export format using a redacted sample from the owner's MT5 terminal. Do not promise universal direct account-history CSV export: MT5 report formats and market-data CSV exports differ.

Use a versioned adapter that maps supported statement/export layouts into normalized accounts, executions and cash flows. Validate sizes, encodings, headers, decimals, currencies, broker timezone/DST and symbols. Preview mapped records and row errors before a transactional save. Deduplicate by broker/server, account and deal identifiers; detect changed previously imported records. Preserve import provenance and selected date-range completeness.

Separate deposits, withdrawals, swaps, commissions, credits and trading PnL. Reconstruct position events without assuming one row is one complete trade. Reject ambiguous or unsupported records explicitly. Do not execute uploaded content; protect CSV exports against spreadsheet formulas. Raw statements, credentials and private fixtures remain ignored and outside Git.

## Future read-only synchronization

Design a common history-provider interface for manual imports, official Bybit account-history access and an optional local MT5 reader. Verify official API permissions, account/product coverage and regional availability before promising support. A crypto API connection must not be assumed to expose MT5 CFD history.

Proposed boundaries:

- Bybit: backend-only secrets in secure credential storage; minimum read permissions; no trading, transfer or withdrawal permissions; supported IP restrictions; redacted logs and revocation/rotation support.
- MT5: optional local Python companion communicating with the installed terminal. Prefer broker-supported investor/read-only access where available. The SDK itself includes trading functions, so use a strict read-function allowlist, no order API or execution route, and verify broker/terminal restrictions separately. Credentials stay local and out of browser code, exports and logs.
- Synchronization: explicit owner opt-in per account; bounded historical backfills; rate limits, retries/backoff and cancellation; per-account cursors with overlap and idempotent deduplication; source timestamps, last successful sync, history completeness and visible errors.
- Corrections: preserve broker identities and history; reconcile updated costs/corrections without duplicating PnL or silently overwriting manual notes. Review uncertain matches and account mappings. Prevent manual/import/sync versions of one execution being counted repeatedly.
- Security: no arbitrary remote command execution, no public listener for the local companion, and authenticated local communication if used. No credentials in the frontend or Git. Connection failure must not erase existing records.

No live execution, order placement/modification/cancellation, automated trading, transfers or withdrawals. Any execution capability requires a separate architecture review and explicit owner authorization. Approval of this design is not approval to establish account connections.

## Migration, verification and sequence

Use additive Alembic migrations with tested legacy mappings. Preserve trade IDs, exits, screenshots and relationships. Test a backup copy before touching personal data; document restoration and verify counts, references and unchanged crypto results. Expand account association carefully rather than assigning all historical records to an invented account.

Proposed sequence after explicit authorization:

1. Contract/account model and migration regression tests.
2. Manual CFD entry and product-specific calculations.
3. Reconciliation against redacted sample broker statements.
4. Previewable, validated statement/CSV adapter.
5. Separate and combined analytics with explicit currency policies and risk coverage.
6. Optional read-only synchronization feasibility review, then separately authorized integration.

Tests must cover long/short forex, JPY pairs, gold/silver, supported calculation modes, variable tick/pip values, partial closes, signed swaps, commissions, spread double counting, historical conversions, rounding, missing data, separate accounts, transfer handling, duplicate/replayed imports, corrections, risk denominators, concentration and unchanged legacy crypto behavior. Reconcile execution/cost totals, net PnL and balance movements to broker statements with explicit tolerances. Synthetic fixtures are labelled and do not substitute for broker reconciliation.

Likely implementation areas: backend instrument/account models, CFD schemas, product calculator modules, import/sync adapters, migrations and tests; frontend journal contracts, conditional forms, filters and analytics/risk panels. Exact file changes will be explained before each authorized milestone.

## Beginner learning goals

Learn how React/TypeScript forms select valid inputs; how FastAPI/Pydantic validates them again; how database relationships keep accounts separate; how migrations preserve old records; how Decimal calculations handle financial units; how adapters translate external records; and how tests and reconciliation verify results.

## Research references

These are design references, not a guarantee of account eligibility or historical API coverage. Recheck current specifications before implementation.

- [Bybit CFD specifications](https://www.bybit.com/en/help-center/article/How-to-Get-Started-with-CFD-Trading)
- [Bybit MT5 CFD account](https://www.bybit.com/en/help-center/article/How-to-Get-Started-with-MT5-CFD-Account)
- [MT5 symbol properties and calculation modes](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants)
- [MT5 history deals](https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py)
- [MT5 profit calculation](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py)
- [MT5 report export release notes](https://www.metatrader5.com/en/releasenotes/terminal/2342)
