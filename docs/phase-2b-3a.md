# Milestone 2B.3A — validated forex and CFD inputs

Status: **implemented locally on 2026-10-16 with owner authorization**. This milestone builds Python financial input contracts, not a CFD calculator or journal form. No dependencies, application routes, database models, migrations, crypto calculations or historical journal assignments were changed.

## What works

- CFD categories: forex, metals, indices, energy, equities and other. Explicit product/calculation metadata is required; crypto and TradFi perpetuals cannot masquerade as CFDs.
- Exact Decimal prices, lots, contract sizes, tick/pip sizes and dated tick/pip value observations. Financial fields accept decimal strings, Python Decimal or integers; reject floats, booleans, nonfinite values, excess precision and invalid signs. Limits are 38 significant digits, 18 decimal places and absolute money/positive-quantity bounds of `1e18`. Values are never rounded into validity.
- Separate account reporting/settlement currencies, instrument profit currency and observation currencies. Broker, settlement and MT5 server compatibility reuse the existing account contracts.
- One entry fill and up to 1,000 chronological exit fills with unique IDs, positive prices/lots, explicit timestamps, declared lot limits/steps, tick alignment and exact over-close prevention. Inputs can be open, partially closed or fully closed; no remaining-lot/PnL result is calculated here.
- Optional **original** stop and planned target on the appropriate side of entry. Missing original risk stays missing; a later breakeven/trailing stop is not an original stop. Order-modification history is outside this input version.
- Up to 1,000 incurred commission, swap, fee or other adjustments. Amounts are signed: negative debit, positive credit; explicit zero is allowed. Currency, time, description and source are required. Execution references must exist; adjustment IDs cannot repeat within an input. A rate schedule is not an incurred charge.
- Directed conversion observations with positive rate, source, observation/application times and an explicitly chosen maximum age. Wrong direction, missing references, stale observations, duplicates and unused observations are rejected. Application time must match the particular exit, adjustment or original stop-risk input.
- Frozen nested specification inputs with an explicit snapshot ID and SHA-256 integrity check compatible with existing `instrument-v1` persistence. No existing snapshot is changed or newly stored.
- A standalone UTF-8 JSON validation command that reads a file, prints safe validation messages and returns exit code 0/1. Its imports do not initialize the application, database, HTTP client or broker SDK.

## Files and how they connect

| File                                                   | Purpose                                                                                                             |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| `services/api/app/schemas/financial.py`                | Reusable exact amounts, timezone rules, immutable model settings and explicit FX evidence                           |
| `services/api/app/schemas/cfd_snapshot.py`             | Strict CFD view of existing specs, tick/pip consistency, currency labels and snapshot digest                        |
| `services/api/app/schemas/cfd.py`                      | Execution/cost/trade contracts and rules linking account, snapshot, fills and conversions                           |
| `services/api/scripts/validate_cfd_input.py`           | Read-only learning/developer command; no API endpoint or persistence                                                |
| `services/api/tests/fixtures/cfd-input.synthetic.json` | Runnable, explicitly synthetic EURUSD teaching input                                                                |
| `services/api/tests/cfd_examples.py`                   | Synthetic JPY/FX builders and fixture fingerprint helper, tests only                                                |
| `services/api/tests/test_cfd_*.py`                     | Precision, missing/invalid inputs, currency/chronology/reference rules, persistence compatibility and command tests |

The older `schemas/instrument.py`, `schemas/account.py`, `schemas/trade.py`, `analytics/trades.py`, persistence services and migrations remain unchanged. Stricter CFD checks apply at this new boundary, not retroactively to legacy input or snapshot records. Existing stored specifications can be explicitly serialized into the new contract for validation; no data migration is needed.

## Beginner examples

The key type is:

```python
lots: PositiveFinancialDecimal
```

It checks exact, finite, positive values. A separate relationship rule checks lots against the instrument and other fills. In the synthetic fixture, entry lots `"0.10"` cover exits of `"0.04"` and `"0.06"`. Changing entry lots to `"0.03"` is rejected because the exits exceed the entry. This is input arithmetic for validation, not profit calculation.

An explicitly supplied example conversion looks like:

```json
{
  "conversion_id": "synthetic-jpy-usd",
  "from_currency": "JPY",
  "to_currency": "USD",
  "rate": "0.0065",
  "observed_at": "2025-01-04T00:00:00Z",
  "applies_at": "2025-01-04T00:00:00Z",
  "max_age_seconds": 0,
  "source": { "kind": "manual", "reference": "Synthetic teaching rate" }
}
```

This means USD per one JPY. It is not live or historical market evidence. Validation checks its structure and binding without multiplying money. Actual observations must come from an explicit permitted source.

Choose one reporting policy:

- `native_only`: retain the separate native currencies; supply no conversion observations/references. It does not promise a combined net result or consolidated account total.
- `explicit_rates`: supply the correctly directed rate for each exit/cost that differs from account reporting currency, plus an entry-time rate for original stop risk where needed. Same-currency amounts require no rate. USD, USDT and USDX are distinct codes.

Linear-mode valuation is labelled with the instrument profit currency. Tick-mode valuation is labelled with the supplied tick observation currency; this can differ from the underlying profit currency. The input contract supports tick metadata, but no tick-mode historical calculator is enabled.

## Deliberate boundaries

- Individual fill prices use a zero-origin tick grid, and lots use a zero-origin step grid. Minimum lots must align with that step. Each fill must meet the supplied deal-volume bounds. Unsupported broker grids, unusual residual-close rules, off-grid broker aggregates and negative-priced instruments require explicit design review; inputs are rejected rather than silently rounded. Scale-ins, reversals and netting reconstruction are future import work.
- Forex requires an explicit pip size. Non-forex pip metadata is optional and never inferred from symbol/display digits. Pip sizes, when supplied, must be whole tick multiples. Tick-profit/loss observations must be supplied together, share currency/time and retain separate positive values. Optional pip/tick observations are not presumed constant historical conversion rates.
- Specification effective time cannot follow entry. Capture may be later for historical imports; optional value observations cannot postdate capture or entry. A time check establishes ordering, not that a specification remained applicable throughout a trade. A later calculator must reject historical valuations it cannot substantiate.
- A checksum proves content consistency, not authenticity or ID ownership. Future authenticated services must load/check the actual account and stored snapshot instead of trusting client-provided identities or sources. Existing database immutability guards remain in force.
- Spread is already reflected in actual fill prices. There is no extra spread-debit field or leverage multiplier in this input contract. A separately incurred broker charge can be a sourced fee adjustment; do not invent charges or double-count spread. Crypto funding conventions are unchanged.
- No CFD API/form, PnL/net/risk/R output, new database rows, broker-statement import/reconciliation, live market data, synchronization or execution was added. The purple UI is unchanged. All committed examples are synthetic; private statements and journal data remain excluded.

## Validation results

Actual local results for this milestone:

| Check                             | Result                                                  |
| --------------------------------- | ------------------------------------------------------- |
| Original backend baseline         | 99 passed                                               |
| Complete backend suite            | 266 passed: original 99 plus 167 new cases              |
| Python lint                       | Passed                                                  |
| Python formatting                 | Passed across 54 files                                  |
| Standalone synthetic validation   | Passed; exit 0                                          |
| Frontend ESLint                   | Passed                                                  |
| TypeScript checks                 | Passed                                                  |
| Production build                  | Passed in `.next-e2e`, with normal journal API excluded |
| Desktop/mobile browser regression | 10 passed against disposable database/server            |
| Repository formatting             | Passed                                                  |
| Normal database and both backups  | Byte fingerprints unchanged since milestone baseline    |

The first full backend run encountered an import/discovery conflict caused by a new test-package marker. Removing that marker and following existing flat imports fixed it; the complete rerun passed. The existing Starlette/httpx test-client deprecation warning remains; it is not a test failure. Python lint initially found line lengths/import ordering, corrected before the final passing checks.

The existing migration/persistence regressions execute only against disposable databases. This milestone applies no migration to the normal journal. Normal database and both backup byte fingerprints were compared privately and remained unchanged; private paths, trades and checksums are not part of this report. Screenshots and account/instrument associations received no writes. Browser tests used their separate temporary database on port 8001 and frontend on port 3100. Their color-environment and reduced-motion notices were informational.

## Run and test it yourself

No new environment variable, dependency installation or application restart is needed for these Python-only contracts. From the repository root:

```powershell
.\.venv\Scripts\python.exe services/api/scripts/validate_cfd_input.py services/api/tests/fixtures/cfd-input.synthetic.json
.\.venv\Scripts\python.exe -m pytest services/api/tests -q
.\.venv\Scripts\python.exe -m ruff check services/api
.\.venv\Scripts\python.exe -m ruff format --check services/api
```

See [the learning exercise](learning-journal.md#2b3a--checking-the-ingredients-before-calculating) for a safe invalid-input example. The normal journal remains at **http://127.0.0.1:3000/journal** for the owner's historical-record inspection; the CFD validator does not save anything there.

## Proposed 2B.3B for review

**Awaiting explicit implementation authorization.** Build a pure Decimal calculator for validated `forex`, `cfd_linear` and `cfd_index` modes, starting with one fully closed single-exit position. A pure function takes inputs and returns results without database/network side effects.

Proposed files:

- `services/api/app/analytics/cfd.py`: linear gross PnL, movement, cost/net reporting and original price-risk/R functions.
- `services/api/app/schemas/cfd_results.py`: exact result amounts with currency labels, missing-data reasons and rounding/valuation policy.
- `services/api/app/analytics/products.py`: explicit product/mode dispatch that rejects unsupported products; the legacy crypto path continues using its current calculator unchanged.
- `services/api/tests/test_cfd_calculations.py` and synthetic expected-value fixtures; this report/plan and learning journal.

For direction sign `s` (+1 buy, -1 sell), entry `E`, exit `X`, lots `L`, contract size `C`:

- Gross: `s × (X − E) × L × C`, in instrument profit currency.
- Signed pips: `s × (X − E) / pip_size`, only when specified; tick count uses the separately declared tick size.
- Original planned price risk: `abs(E − original_stop) × original_lots × C`. This is an estimate based on the stop price, not actual broker margin, guaranteed loss or liquidation distance.
- Convert cash flows only with the explicitly linked observations under the chosen reporting policy. Add signed costs once for net PnL; never add a leverage multiplier or subtract spread again.
- R: eligible net divided by original planned risk on the documented common currency basis. Missing stop, conversion coverage or valid denominator yields an explicit unavailable result, never fabricated zero.

Hand-worked synthetic tests will cover long/short EURUSD, USDJPY/EURJPY, supplied XAUUSD/XAGUSD contracts, exact fractional lots, zero price movement, signed costs, explicit FX timing/direction, unavailable cases and scaling/sign invariants. Precision will be sufficient for intermediate products, with explicit reporting-rounding policy rather than rounding every operation. Existing crypto/API/browser checks continue. Unsupported tick-mode historical valuations, partial-closure cost recognition and broker reconciliation stay outside this first calculator step; 2B.3C handles their separately reviewed scope. No broker statement can be described as reconciled until authorized suitable evidence is supplied.

## References checked

The implementation uses the installed Pydantic 2.14.1 API and official [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/), [Decimal types](https://docs.pydantic.dev/latest/api/standard_library_types/#decimals) and [model immutability](https://docs.pydantic.dev/latest/concepts/models/#faux-immutability). Broker property names and the distinction between tick size, tick-profit/loss values, contract size and deal volume metadata were checked against [MT5 symbol properties](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants). These references do not verify any current Bybit contract specification or the synthetic rates/examples.
