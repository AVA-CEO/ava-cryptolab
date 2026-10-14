# Trading Journal — Phase 2

The journal is a local, persisted feature. Use **Record trade** to save actual position facts and reflections. Purple remains the brand color; green communicates profits, successful actions and closed status. No exchange execution or market price inference is implemented.

## Record model

A trade has one entry (or manually calculated average entry) and up to 100 exit executions. Quantity is in base-asset units. Exits may close part of the position; total exited quantity cannot exceed original quantity. Open/partial/closed status is derived from quantities, never an arbitrary flag. Initial stops must be on the loss side of entry. Keep the original stop rather than replacing it with a later trailing stop.

Supported instruments are spot inventory and linear quote-settled futures in USD, USDT or USDC. Each currency is analyzed separately: **there is no assumed peg or FX conversion**. Inverse contracts, option payoffs, contract multipliers and automatic scale-in cost-basis reconstruction are not supported. Spot selling is disposal of owned inventory: entry is its acquisition cost and exit is the sale, not a synthetic short.

SQLAlchemy uses Decimal values. PostgreSQL uses NUMERIC; SQLite uses decimal text to avoid floating-point storage loss. Money in JSON uses decimal strings; charts use floating-point values for display only. Calculations use a 60-digit decimal context. All user timestamps must include a timezone; UI timestamps explicitly use UTC. SQLite-returned naive dates are interpreted as the stored UTC value.

## Calculation policy

- Long / spot gross PnL = sum of `(exit price − entry price) × exited quantity`.
- Short futures gross PnL = sum of `(entry price − exit price) × exited quantity`.
- Net PnL = gross PnL − entry fees − exit fees − funding. Funding paid is positive; funding received is negative.
- All recorded entry fees and total recorded funding are recognized immediately, including open positions. Unrealized price movement is unavailable and never guessed.
- Initial planned risk = `abs(entry − initial stop) × original quantity`. It excludes estimated future fees. No initial stop means null planned risk and null R.
- Realized R = net PnL ÷ original planned risk, including partial realized outcomes. Closed-trade averages exclude partial trades.
- Notional = entry price × original quantity. Estimated entry margin = notional ÷ leverage. Leverage does not multiply PnL again. This estimate is not exchange collateral, liquidation risk or cross-margin account exposure.
- Win rate = closed net-positive trades ÷ all fully closed trades, including breakeven records in the denominator.
- Expectancy = mean net PnL of fully closed trades. Average R includes only closed records with known original risk; coverage is shown.
- Profit factor = sum of net-positive closed outcomes ÷ absolute sum of net-negative closed outcomes. No losses means undefined (null), never fake infinity.
- Closed-trade drawdown = the largest decrease from a peak of cumulative closed net PnL, including the initial zero baseline. Simultaneous closures are grouped to avoid inventing an event order. Percentage drawdown requires a positive user-supplied opening balance. This is not intratrade or mark-to-market drawdown.

Curves, daily and monthly bars assign each complete trade’s net result to its final exit. They are summaries of closed trades, not a cash-movement ledger. Partial exits contribute to total recorded net PnL but not to these closed-trade charts. No deposits or withdrawals are modeled. Recorded balance = opening balance + recorded net PnL; without a supplied starting balance it is unavailable.

Filters select a cohort by UTC **entry date**, currency, status, outcome, setup, exchange and search text. Statistics and charts use the same cohort. A filtered balance is the opening balance plus that cohort’s PnL, not the complete account balance. Sorting by PnL always occurs within one currency.

Reference for linear contract PnL: [Bybit’s published calculation guidance](https://www.bybit.com/en/help-center/article/Profit-Loss-calculations-USDT-Contract). These calculations journal user-provided executions; they do not replicate every exchange’s accounting system.

## CSV

Download the empty template from the journal. One row represents one trade. The `exits` column contains a JSON array such as:

```json
[{"exit_at":"2025-01-02T12:00:00Z","price":"110","quantity":"2","fees":"1"}]
```

This is a format example, not a market observation. Other fields match the form. Export follows current filters. Imports accept UTF-8, at most 2 MB and 1,000 rows; every row is validated before the transaction commits. Existing IDs and equivalent record fingerprints are skipped, not overwritten. Exported text fields beginning with spreadsheet formula markers are prefixed with an apostrophe. Screenshot bytes are not exported. Database IDs are for duplicate detection, not record reassignment.

## Screenshots and local security

PNG/JPEG/WebP uploads are limited to 5 MB and 16 million decoded pixels. Pillow verifies and re-encodes pixel data into PNG, stripping source names and metadata. Files use generated names under the ignored backend uploads directory. The service validates storage paths; images are served with no-store/nosniff headers and are deleted with their trade. Replacing/removing an image increments record versions.

Optimistic row versions reject stale edits/deletes with a reload message. Mutation requests require the local journal header; browser origins are checked and an in-process rate limit allows 120 mutations per client per minute. The Next.js API bridge enforces local hostnames and same-origin browser edits. These are local protections, **not user authentication**. Public deployment remains blocked pending authentication, user ownership and production infrastructure. Uploaded images need isolated processing, quotas and authenticated private storage before public use.

## Beginner walkthrough

1. Start the backend and frontend using README commands. Run `alembic upgrade head` after this milestone.
2. Visit `/journal`, choose your settlement currency, then **Record trade**.
3. Add entry facts and initial risk. Leave exits empty for an open position.
4. Add each real exit, then save. Click **View** to inspect calculations or **Edit trade** to add later exits.
5. Use setup/mistake tags consistently. They are raw material for Trading IQ.
6. Optionally enter the opening balance before the recorded history starts. No starting amount is supplied for you.
7. Filter results and inspect charts. Export private records locally; do not commit them to Git.

Tests use disposable in-memory or temporary databases. Browser tests start their own API on port 8001 and do not use `services/api/ava.db`.
