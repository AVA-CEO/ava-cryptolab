# Phase 2B.1 — Account and instrument contracts

This is the first code milestone following explicit owner authorization of Phase 2B. It defines and tests future inputs; it does not add CFD persistence, account CRUD, CFD calculations, broker connections or a new trade form. The current crypto journal API and database models/migrations remain unchanged.

## What a contract means

A contract here is a checked description of data, not a broker order or financial agreement. Python Pydantic models validate it at runtime. TypeScript discriminated unions let the future form select the right fields from the product name. For example, a CFD uses lots and contract size; a crypto linear product uses base-asset quantity. A forex CFD cannot claim a crypto calculation mode.

New files:

- `services/api/app/schemas/account.py`: account identity, broker/platform/server, reporting and settlement currency. Extra fields such as API keys/passwords are rejected. Labels are non-secret references, not credentials.
- `services/api/app/schemas/instrument.py`: immutable versioned specification snapshots for Crypto Spot, Crypto Linear Futures, CFDs and TradFi Perpetuals. Sources and timezone-aware timestamps accompany specifications and optional per-lot pip/tick-value observations.
- `services/api/app/schemas/multi_asset.py`: account/instrument compatibility. Broker and settlement must match; MT5 contracts must be CFDs and refer to the account's server.
- `apps/web/src/features/journal/multi-asset-contracts.ts`: corresponding serialized wire types. Monetary values remain strings to preserve decimal precision.
- Backend contract tests and frontend compile-time assertions: product/unit separation, bad metadata, account mismatches and legacy API rejection of CFDs.

The existing `contracts.ts`, trade inputs, crypto calculator, trade API, database tables and purple interface are retained. No dependencies were added.

## Validation results

- 68 backend tests passed: the existing 33 tests plus 35 new contract cases.
- Ruff lint and formatting checks passed for the new Python files.
- Repository Prettier formatting, frontend ESLint and TypeScript checks passed. TypeScript also checks the negative assertions that deliberately reject wrong product/unit combinations.
- The existing Starlette TestClient deprecation warning remains; no new test warnings were introduced.
- Git diff review confirmed that existing journal forms/contracts, API, calculations, database models and migrations were unchanged. No database migration or broker connection was run.
- Production build and browser tests were not rerun for this schema/type-only milestone; there is no changed rendering or runtime frontend behavior. Existing Phase 2 acceptance and remote CI results remain separate evidence.

The milestone is committed locally. Its remote push requires owner approval; do not treat prior GitHub Actions results as validation of this new commit.

## Current boundaries

Validation recognizes the proposed specification shape, not broker eligibility or calculator availability. Only the existing crypto journal can currently save and calculate trades. CFD definitions have supported vocabulary for future calculators; they do not dispatch into the crypto calculator. TradFi perpetuals are separate and currently describe linear same-currency settlement only. Unsupported product/calculation modes fail validation.

Specification values use positive finite Decimals, volume bounds, explicit pip sizes for forex, and explicit profit/loss tick observations for tick-based modes. Pip size is not derived from tick size. Reporting currency can differ from settlement currency without implying conversion or parity. Currency codes are uppercase application identifiers; `USDX` is distinct from `USD` and `USDT` and is not a claim that USDX is an ISO currency.

Snapshots and nested value/source models are frozen in memory. Durable historical snapshots will be added with persistence in 2B.2. Source text records provenance; it does not independently verify the broker. Future imports must avoid placing secrets in any free-text field. Timestamp normalization preserves UTC; importing broker-local dates will require an explicit timezone policy in the import milestone.

Frontend types are compile-time assistance, not runtime security. Python is authoritative for semantic validation. The handwritten wire types will need updating alongside schema versions; automated schema generation can be considered when the persisted API stabilizes.

## Try the foundation

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest services/api/tests/test_multi_asset_contracts.py -v
.\.venv\Scripts\python.exe -m pytest services/api/tests -q
.\.venv\Scripts\python.exe -m ruff check services/api
npm run typecheck
npm run lint
npm run format:check
```

The contract tests contain labelled synthetic EURUSD, XAUUSD/XAGUSD, crypto and TradFi perpetual examples. They are not verified Bybit contract specifications or live observations. Inspect `specification()` in the test file to see how one product determines its units and required fields. Tests run with isolated in-memory databases and never migrate the personal journal.

For an interactive Python example, open a terminal in `services/api`:

```powershell
..\..\.venv\Scripts\python.exe
```

Then enter:

```python
from app.schemas.account import AccountContract
account = AccountContract(
    account_id="practice-only",
    name="Teaching account",
    broker="Synthetic broker",
    platform="mt5",
    server="Synthetic server",
    reporting_currency="USDX",
    settlement_currency="USDT",
)
print(account.model_dump_json(indent=2))
```

This validates an object in memory; nothing is saved. Try removing `server` or adding `password="example"`: validation rejects those inputs. A difference between reporting and settlement currencies is preserved; no conversion occurs. Exit Python with `exit()`.

The app runs as before with `npm run dev` and the existing local FastAPI command in the README. There are no new environment variables, credentials or installation steps. The journal page intentionally has no CFD controls yet.

## Learning and next milestone

You have a concrete example of domain modeling (naming financial concepts accurately), runtime validation, product-based type narrowing, immutable historical specifications and regression testing. Runtime checks verify submitted data; type checks help developers catch mistakes before running the code.

Next is 2B.2: additive persistence and migration rehearsals. Explain the exact table changes and restoration process before implementation. Do not migrate the normal journal as a shortcut for testing. Separate account management and manual CFD entry follow in 2B.3 and 2B.4.

References checked for this milestone: [Pydantic discriminated unions](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions-with-str-discriminators), [MT5 calculation modes and symbol properties](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants), and the installed Next.js TypeScript reference. Existing dependencies were reused.
