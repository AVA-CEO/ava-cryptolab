# Proposed Milestone 2B.3C — partial closures and reconciliation foundations

Status: **implemented following explicit owner authorization**. Read the [accounting policy and implementation report](phase-2b-3c.md). The original pre-implementation proposal below is retained for design history; the implementation adds no broker-file parser or database changes. The next [2B.4 integration plan](phase-2b-4-plan.md) awaits review.

## Why this is a separate step

Selling a position in pieces is like selling a box of items in several receipts. Each receipt has its own time, price and costs, while the original quantity and risk remain the starting reference. Simply adding more exits to the single-close calculator would leave important accounting choices unstated.

## Step 1 — position state and execution accounting

- Extend the pure calculation boundary with a reviewed position-result version supporting open, partial and closed status. Keep existing single-close requests compatible.
- Calculate realized gross separately for each actual exit using its lots, price, snapshot and native profit currency, then sum exact results. Show original, closed and remaining lots; reject over-closes, duplicate IDs and invalid chronology.
- Keep the original specification/risk reference fixed. Do not silently apply new broker specifications to old fills. Contract changes during a position need an explicit policy before support.
- Do not invent mark-to-market or unrealized PnL without separate price observations. No live prices, execution or automatic broker connection.
- Preserve the unchanged crypto engine and current UI/API paths.

Proposed files: `app/analytics/cfd_positions.py`, reviewed additions to `schemas/cfd_results.py` and new position tests. Reuse the validated `CfdTradeInput` execution records rather than rebuilding them.

## Step 2 — cost recognition and currency coverage

- Choose an explicit timezone-aware `as_of` cutoff for reproducible accounting. Recognize only supplied incurred adjustments up to that cutoff, once. No invented future swaps/commission schedules.
- Proposed primary policy: recognize actual recorded entry-level fees when incurred, without prorating away their real cash effect. Execution-linked exit costs remain tied to their actual exits. Any later per-exit fee-allocation view must be labelled as analysis and must reconcile back to the same position total.
- Convert each exit and cost only using its own permitted directed/time-aligned observation. Report missing coverage; never silently omit a foreign-currency fee or assume a peg.
- Keep full original planned risk as the R denominator. A partial result must clearly say realized net/original risk and show closure coverage. Do not treat it as a completed-trade win/loss cohort observation.
- Separate currency totals and explain native versus reporting differences. No guessed rates, tick values, broker margin or liquidation requirements.

Teaching focus: execution ledgers, state transitions, cash recognition, explicit cutoffs, aggregation and missing-data coverage.

## Step 3 — broker comparison without replacing evidence

- Define read-only comparison inputs for broker-reported gross/net, commission and swap amounts with currency, statement/source reference and reporting time/basis.
- Preserve broker-reported and independently calculated results as separate values. Show differences and coverage rather than changing original evidence to force a match.
- Require a reviewed rounding/tolerance policy and comparable scopes. Display rounding from 2B.3B is not automatically a broker settlement policy.
- Start with clearly labelled synthetic comparisons. Real reconciliation requires authorized redacted statements and historical contract/rate evidence. Do not claim any broker match until those cases actually pass.
- Statement parsing, import writes, account-management UI and synchronization stay in their separately reviewed milestones.

Proposed files: `schemas/cfd_reconciliation.py`, `analytics/cfd_reconciliation.py`, synthetic fixtures and later permitted sanitized evidence tests. No schema migration is proposed; review necessity separately if durable new fields are later requested.

## Tests and manual exercise

Test open→partial→closed states, irregular fractional exits, simultaneous exit timestamps, cost credits/debits, entry and exit fee recognition, duplicate IDs, over-close rejection, mixed currencies/rates, missing stops, missing conversion coverage and explicit cutoffs. Compare exit totals against independent hand-worked cash ledgers. Preserve all crypto and single-close regressions, frontend checks, isolated build and disposable browser tests.

The implemented teaching exercise closes a synthetic 0.10-lot EURUSD position in 0.04 and 0.06 lots, inspects remaining lots at each cutoff and explains the unchanged original risk. See the report and learning journal for exact commands.

## Approval boundary

Explain the chosen accounting policy and affected files before coding. Obtain owner approval for this milestone and separately for any remote push. Do not change the normal journal, verified backups, historical associations, UI forms or migrations under this proposal. No live broker connections, synchronization, orders, transfers or deployment.
