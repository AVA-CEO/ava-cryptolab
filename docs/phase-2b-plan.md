# Phase 2B — Multi Asset Trading Expansion plan

Status: **design approved; implementation awaiting explicit owner authorization**. Phase 2 manual acceptance is complete on the owner's report. Phase 2B now takes priority over Phase 3.

The [architecture proposal](multi-asset-expansion.md) is the detailed policy reference. These milestones divide it into reviewable increments. Proposed file names can be refined after code inspection; they are not files created by this documentation milestone.

Before every coding milestone, explain what is being built, why it matters, how it works, the files to change, the concept being taught and a manual test. Afterward, report actual checks, working behavior and remaining limits. Preserve the purple interface, green profits/success, existing journal behavior and Python Decimal calculations. Reuse current forms, execution records, analytics and import protections where appropriate.

## 2B.1 — Account and instrument contracts

- Build: define account identity, market category versus product type, supported calculation modes, specification snapshots, execution units and currencies. Separate Crypto Spot, Crypto Linear Futures, CFDs and TradFi Perpetuals. Define supported contracts before accepting records.
- Why/how: one journal can share common fields while choosing the right calculator from explicit contract metadata; a symbol alone cannot determine its product rules.
- Proposed files: `services/api/app/schemas/account.py`, `schemas/instrument.py`, contract/policy modules, `apps/web/src/features/journal/contracts.ts`, and architecture documentation.
- Learn: domain modeling, Python enums/Pydantic and TypeScript discriminated unions (a type that selects the right fields for each product).
- Verify: review example crypto, EURUSD and XAUUSD payloads; valid combinations pass schema tests and invalid units/product combinations fail. No live connection is needed. Existing crypto API compatibility is required.

## 2B.2 — Safe additive persistence and migration rehearsal

- Build: persist accounts, instruments/specification snapshots and product-specific details, preserving legacy trade IDs, exits, screenshots and relationships. Add explicit account associations without guessing unknown historical ownership.
- Why/how: an Alembic migration is a versioned set of database changes. Rehearse it on an isolated backup, compare before/after records and document recovery before applying it to personal data.
- Proposed files: `services/api/app/models/account.py`, `models/trade.py`, new instrument/CFD models, database exports, `services/api/migrations/versions/`, and migration regression tests.
- Learn: primary/foreign keys, nullable transitional fields, data backfills, transactions and restoration procedures.
- Verify: migrate a disposable legacy fixture and a private backup copy; confirm IDs/counts/references and legacy calculations survive. Check SQLite and PostgreSQL migration compatibility with explicit results; do not claim PostgreSQL verification unless actually run. No destructive rollback against personal data.

## 2B.3 — Independent account management

- Build: create/edit/select accounts with currencies, balances, cash flows, risk settings and separate journal/analytics views. Preserve a clear legacy-record assignment workflow.
- Why/how: an account is a separate ledger. Filtering alone is insufficient: all reads, writes, imports and calculations must enforce the chosen account association. Transfers and deposits are not trading profits.
- Proposed files: account API/service/schema, account balance/cash-flow models as needed, frontend account selector/settings and journal query filters; adapt existing balance controls.
- Learn: database relationships, API scoping, React state and server-side validation. Account separation within a local app does not replace user authorization for future multiuser deployment.
- Verify: create two practice accounts with different currencies and risk limits; a trade, balance update or import in one must not change the other. Test legacy assignment and internal transfer accounting without double counting.

## 2B.4 — CFD calculator and manual journal entry

- Build: independent supported forex/CFD calculation engines, lot/contract/tick/pip validation, partial exits, commissions, signed swaps and native-currency PnL; connect them to conditional manual-entry fields. Keep broker and calculated PnL separate. TradFi perpetuals use verified contract-specific rules and remain a separate product category.
- Why/how: lots describe a number of contracts, not crypto coin quantity. Dispatch by calculation mode; snapshot the specifications used. Unsupported modes or missing conversion inputs return unavailable metrics instead of guessed totals.
- Proposed files: `services/api/app/analytics/cfd.py`, calculator dispatch, CFD schemas/services, `apps/web/src/features/journal/trade-form.tsx`, trade details and calculation tests.
- Learn: Decimal arithmetic, dimensional units, strategy-based calculators and conditional forms. Pip size differs from tick size; leverage affects margin rather than multiplying price-movement profit.
- Verify: labelled long/short EURUSD, JPY pair and gold/silver examples; costs/credits, partial exits, missing specifications and rounding. Confirm spread is not subtracted twice. Initial risk/R must remain unavailable without a valid original stop. Re-run all existing crypto regressions.

## 2B.5 — Broker statement reconciliation

- Build: compare broker-reported and calculated gross/net PnL, execution volumes, commissions, swaps and account balance movements. Explain discrepancies and select a disclosed accounting basis for analytics.
- Why/how: reconciliation checks our records against the broker's statement. Keep both values and trace differences instead of silently forcing a match.
- Proposed files: reconciliation service/schema, fixtures and tests, journal detail reconciliation panel, reconciliation documentation.
- Learn: audit trails, rounding tolerances, signed cash-flow accounting and evidence-based validation.
- Verify: synthetic edge cases plus owner-provided redacted broker samples, including partial closes and statement totals. Private samples remain ignored; commit only permitted sanitized fixtures. Broker reconciliation is not complete until actual sample totals match within documented tolerances.

## 2B.6 — Secure statement/CSV import

- Build: format-specific adapters, column mapping preview, account/specification matching, row errors and transactional saving. Handle deal IDs, netting/hedging, reversals and previously imported corrections. Keep current crypto CSV support working.
- Why/how: translate supported external layouts into the same validated execution records used by manual entry. Confirm actual MT5 account-history export format; market-data CSV is not a trade statement.
- Proposed files: `services/api/app/services/imports/`, existing CSV service/API, import frontend and import/replay tests.
- Learn: adapters, normalization, idempotency (repeating an import has no duplicate effect) and all-or-nothing database transactions.
- Verify: preview then import a supported redacted sample; replay safely, detect corrected records, reject ambiguous rows, preserve notes and distinguish deposits/withdrawals from PnL. Test file limits and CSV formula protection.

## 2B.7 — Combined analytics and unified risk dashboard

- Build: separate Crypto Futures/Forex CFD/account views, explicit currency-conversion policies, consolidated cash-flow-aware analytics, exposure and concentration panels. Reuse existing charts and Trading IQ evidence rules.
- Why/how: monetary values can be combined only after conversion to a declared reporting currency. Store native values plus rate source/time; recompute ratios from eligible observations rather than averaging account ratios.
- Proposed files: FX observation/policy models and service, `analytics/performance.py`, `analytics/trading_iq.py`, new risk analytics, frontend performance/risk panels and tests.
- Learn: time-series alignment, currency valuation, aggregation and uncertainty/coverage reporting.
- Verify: different-currency accounts with explicit fixture rates; missing/stale rates, deposits and transfers; account-relative risk limits, concentration and unknown stops. Distinguish initial planned risk, remaining stop risk, actual losses, notional exposure, estimated margin and broker-reported margin/liquidation information. Do not present closed-trade drawdown as intratrade equity drawdown. A missing stop must never become zero risk. IQ thresholds remain 20 closed trades overall and 5 per comparable group, with disclosed cohorts.

## 2B.8 — Optional read-only synchronization feasibility and approval

- Build first: evaluate official Bybit account-history coverage and MT5 local-terminal history reading. Specify a provider interface, permissions, credentials, historical cursors, replay/correction handling and error states. Do not assume Bybit crypto API keys expose MT5 CFD accounts.
- Why/how: synchronization is another input adapter. It must use the same account, deduplication and reconciliation rules as imports. Manual entries and statement imports remain usable without any broker connection.
- Proposed files after separate authorization: history-provider interfaces, backend-only Bybit adapter and optional `tools/mt5-reader/` local companion with isolated dependencies. No execution module or endpoint.
- Learn: API capabilities, least privilege, credential storage, pagination, rate limits/retries and incremental synchronization.
- Verify: mocked providers, denied permissions, interruptions, overlapping history windows, duplicate/corrected deals and note preservation. Any real-account connection requires explicit approval and read-only credentials/access where supported. The MT5 SDK includes order functions, so a read-function allowlist alone must not be advertised as a broker-enforced permission boundary.
- Gate: report feasibility before implementing optional synchronization. Never enable orders, amendments, cancellations, transfers, withdrawals or automated trading. Execution requires a separate architecture review and explicit owner authorization.

## Delivery gates

Each authorized implementation milestone needs applicable unit/integration checks, documented manual checks, meaningful local commits and honest limitations. Remote pushes require separate approval. Do not rebuild working features or broaden into Phase 3 without agreement. No secrets, private statements, personal trading data or database files may enter commits.

The next immediate decision is explicit authorization to begin 2B.1. This plan and its commit do not grant that authorization.
