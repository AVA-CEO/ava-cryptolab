# Milestone 2B.3C — position accounting policy

Status: **implemented locally and validated with owner authorization**. The accounting policy below was recorded before implementation. Work remains pure Python with synthetic/disposable tests: no normal-journal or backup writes, migrations, frontend integration or broker connections.

## Accounting policy: incurred once

1. The request explicitly supplies an inclusive timezone-aware `as_of` cutoff at or after entry. Only exits executed and costs incurred by that cutoff affect the result. The full supplied ledger must still pass validation, including future entries and their required FX references. A historical cutoff reconstructs financial state; it does not assert when evidence first became available.
2. Original lots are fixed. Exited lots are the sum of included exits. Remaining lots are original minus exited lots. The whole supplied ledger rejects over-closing, duplicate execution/cost IDs and exits before entry, even when an invalid record is beyond the cutoff. Simultaneous exits retain their supplied order.
3. Each included exit earns `direction × (exit − entry) × exited_lots × recorded_contract_size` in the snapshot profit currency. Sum these unrounded amounts. The allowlist remains forex, linear CFD and index CFD with their explicit compatible categories. No tick-mode fallback.
4. Recognize each supplied incurred adjustment once by its unique ID. Entry commissions are recognized in full when incurred, even while the position is open or partial. Do not allocate them again to each exit. Exit-linked commissions require a valid execution reference and their own occurrence time. Swaps and other signed amounts follow the same rule. Positive is a credit, negative a debit.
5. Realized net is the included realized price profit plus all included incurred adjustments. This includes actual entry costs on still-open lots; it is not a prorated closed-lot net figure. No automatic fee allocation or future swap estimate is provided.
6. Original planned risk is always `abs(entry − original_stop) × original_lots × contract_size`. Realized R is cumulative incurred net divided by that unchanged original risk on the same currency basis. It can include entry-fee loss before an exit. Partial/open positions are ineligible for completed-trade statistics; their outcome label remains unavailable. A missing stop gives unavailable risk/R.
7. Native price profit stays visible. Convert each exit/cost at its explicitly linked source/time/direction, and original risk at entry time. No inverse rate, peg, default rate or mixed-currency total is invented. `native_only` retains known native values and marks conversion-dependent totals unavailable.
8. No unrealized PnL is calculated without a separate valuation-price contract. Missing unrealized value is not zero. Planned risk is not broker margin or liquidation risk.
9. Preserve broker-reported evidence separately. Compare only matching position/account/instrument, state, cutoff, currency and declared accounting basis. Require explicit raw/display comparison choice and absolute currency tolerance. Differences never overwrite calculated or reported values. Numeric agreement on synthetic examples is not real broker reconciliation.
10. Reuse existing Decimal display policy and 160-digit context. Sum unrounded cash flows before display rounding. Repeating ratios have finite working precision. All existing single-close and crypto behavior must remain unchanged.

The complete supplied ledger also requires explicit rounding places for every declared currency. A partial cutoff does not excuse malformed future rows. Only included exits/costs and entry-risk conversion evidence contribute to or appear in the calculated result. Distinct IDs that accidentally describe the same economic charge cannot be detected reliably without provenance; future import adapters must address that separately rather than guessing duplicates.

## Owner's synthetic acceptance example

Buy EURUSD at 1.10000, 0.10 lots, declared 100,000 units/lot, original stop 1.09800, USD profit. Close 0.04 at 1.10200: 8 USD gross, 0.06 lots left. Close 0.06 at 1.10300: another 18 USD, cumulative 26 USD, zero lots left. Original risk remains 20 USD; no-cost final R is 1.30. Four USD of incurred costs give 22 USD net and 1.10R. All prices, rates and contract examples are synthetic, not current Bybit specifications.

## Implementation and important files

Implemented after the policy above was recorded. No old calculator or input contract was modified.

| File                                                       | Purpose                                                                                             |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `services/api/app/schemas/cfd_positions.py`                | Frozen as-of request, position/exit/cost results and position-specific unavailable result           |
| `services/api/app/analytics/cfd_positions.py`              | Validates the whole ledger, filters by cutoff, computes per-exit and cumulative realized accounting |
| `services/api/app/schemas/cfd_reconciliation.py`           | Broker-reported values with scope, quantity coverage, timestamp, source and comparison policy       |
| `services/api/app/analytics/cfd_reconciliation.py`         | Like-for-like comparison without substituting broker amounts                                        |
| `services/api/scripts/calculate_cfd_position.py`           | Read-only local JSON calculation command                                                            |
| `services/api/tests/cfd_position_examples.py`              | Synthetic builders only                                                                             |
| `services/api/tests/test_cfd_positions.py`                 | Owner example, states, fees, losses, shorts, JPY, metals and parity                                 |
| `services/api/tests/test_cfd_position_edges.py`            | Maximum ledger size, tiny lots, unsupported modes and FX/risk parity                                |
| `services/api/tests/test_cfd_reconciliation.py`            | Separate reported/calculated values, scope/tolerance and missing-data checks                        |
| `services/api/tests/test_cfd_position_script.py`           | Local examples, errors and dependency isolation                                                     |
| `services/api/tests/fixtures/cfd-position*.synthetic.json` | Runnable no-cost and cost/comparison examples, explicitly synthetic                                 |

The new engine reuses the supported-mode allowlist and `ResultBuilder` from the single-close engine for consistent rounding/net/R results. It computes each exit independently rather than repeatedly calling a whole-position calculator with the same fees. Cost breakdowns are explanatory views; they are not added again to the position total. The existing product dispatcher and journal routes remain unchanged; call `calculate_position` explicitly for this milestone.

## Trace the example through time

| Cutoff (UTC) | State   | Closed / remaining lots | Gross USD | Incurred costs USD   | Net USD | R on original 20 USD |
| ------------ | ------- | ----------------------- | --------- | -------------------- | ------- | -------------------- |
| Jan 3, 00:00 | Open    | 0 / 0.10                | 0         | −1 entry commission  | −1      | −0.05                |
| Jan 4, 00:00 | Partial | 0.04 / 0.06             | 8         | −1.50 total          | 6.50    | 0.325                |
| Jan 4, 12:00 | Partial | 0.04 / 0.06             | 8         | −3.50 including swap | 4.50    | 0.225                |
| Jan 5, 00:00 | Closed  | 0.10 / 0                | 26        | −4 total             | 22      | 1.10                 |

The cost fixture contains entry commission −1, first-exit commission −0.50, final-exit commission −0.50 and swap −2. Its per-exit gross values are always 8 and 18; position net recognizes the costs once. There is no fabricated per-exit net allocation. Without these costs, first partial R is 8/20 = 0.40 and final R is 26/20 = 1.30.

Open/partial result groups deliberately return an unavailable outcome label. The closure-eligibility flag is a closure gate, not proof of complete fees or FX coverage; later statistics must also select a compatible currency basis and check metric availability. No performance dashboard or Trading IQ cohort logic is changed here.

## Currency and reconciliation evidence

Each included exit has its own native and reporting gross. Dated supplied rates are applied per cash flow, never to a single blended average exit. Original risk keeps its entry-time conversion. Native net/R may be unavailable when costs span currencies even if reporting totals are available. No inverse or USD/stablecoin equivalence is inferred. Unrealized PnL remains explicitly unavailable for every position state because no valuation-price contract is supplied.

Broker evidence retains its original amount, currency and source. A numeric comparison requires matching position/account/instrument, original/exited lots, state, cutoff and `incurred_once` accounting basis. Unknown quantity coverage or incompatible metadata produces an unavailable comparison while preserving valid position calculations. Structurally invalid evidence rejects the request rather than silently dropping it.

The caller chooses `raw` or `display_rounded` comparison and a nonnegative absolute tolerance in the same currency. Difference means selected calculated value minus reported value. Tolerance is inclusive. Status is `within_tolerance`, `difference` or `unavailable`; none is labelled broker-verified. Display rounding is not automatically a broker settlement-rounding policy. A source label does not authenticate a broker statement. All committed comparison evidence is synthetic; no real broker statement has been reconciled.

## Local commands and exercise

From the repository root, with the existing environment:

```powershell
.\.venv\Scripts\python.exe services/api/scripts/calculate_cfd_position.py services/api/tests/fixtures/cfd-position.synthetic.json
.\.venv\Scripts\python.exe services/api/scripts/calculate_cfd_position.py services/api/tests/fixtures/cfd-position-costs.synthetic.json
```

Expect no-cost net 26 USD and 1.30R, then cost-inclusive net 22 USD and 1.10R. Add `--json` to inspect exit rows, recognized/deferred IDs, original risk, included conversion evidence and separate comparison values. No new dependencies, environment variables or application restart are needed. The command does not load SQLAlchemy, application/database settings, an HTTP client or MT5.

See the [learning journal](learning-journal.md) for the safe cutoff exercise. Use private copies for experiments; never edit historical snapshots to make calculations fit.

## Validation record

- Existing backend baseline: **357 passed** before implementation.
- Complete backend suite: **439 passed**, including **82 new cases**. This covers the owner's no-cost/cost examples, losses, shorts, JPY with per-exit FX, supplied gold/silver contracts, invalid ledgers, reconciliation scope/tolerance, single-close parity, 1,000 exits/1,000 costs, tiny lot balances and precision/context isolation.
- Python lint and formatting passed across 73 Python files.
- Frontend lint, TypeScript and isolated production build passed. Build used `.next-e2e` and an unreachable API address; it did not use the normal journal API.
- Both standalone example commands passed with the expected values.
- All **10 desktop/mobile browser tests passed**, using the disposable API/database on port 8001 and frontend on port 3100. Color/reduced-motion notices were informational.
- Repository formatting and whitespace checks passed. The practical cutoff exercise was run and verified: 0.06 lots remain, 8 USD net, 20 USD original risk and 0.40R.
- Normal-journal and both verified-backup byte fingerprints remained unchanged. Read-only health/journal-page requests returned HTTP 200. The private preservation report is excluded from Git.

Approved commit `b323fe3` was pushed after working-tree, history, sensitive-path and credential-signature checks. GitHub confirmed that commit is present, the repository remains private and both Actions jobs passed. This new milestone is committed locally only; pushing it needs separate permission. No deployment was performed.

The first position run passed 35 cases and failed one single-close parity assertion: amounts/availability agreed but unavailable-message text differed. Matching the existing descriptions corrected it without changing the existing engine or calculated values. Subsequent complete tests passed. Initial long-line/import-format findings were corrected before passing lint. The existing Starlette/httpx test-client deprecation warning remains.

Synthetic expected values are hand-worked; an independent exact `Fraction` cash ledger also checks aggregate proceeds minus closed cost basis. This is calculation verification, not broker reconciliation. Existing migration tests run only on disposable databases; no normal-journal migration is performed. Detailed preservation reports and backup fingerprints remain private and ignored by Git.

## Next review

The [2B.4 application-integration proposal](phase-2b-4-plan.md) separates account/specification workflows, reviewed persistence, conditional forms and acceptance testing. Implementation and any new migration require review/authorization. No normal database update, historical association, frontend integration, synchronization, live order or deployment is included here.

References checked: [MT5 calculation-mode definitions](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants), [Python Decimal contexts and rounding](https://docs.python.org/3.13/library/decimal.html). Incurrence and comparison policies above are explicit AVA journal design choices, not claims about a particular broker's statement convention.
