# Milestone 2B.4A — local practice account management

Status: **accepted and closed by the owner on 2026-10-17**. All eight practice scenarios passed according to the owner's manual observations. See the [user-reported acceptance report](phase-2b-4a-acceptance.md); these are separate from the previously measured automated tests. 2B.4B remains design review only, with no implementation authorized.

## Working scope

The Accounts area creates and lists manually recorded accounts, selects an account, and reviews its compatible instrument specification history. Accounts record broker, platform, optional server/non-secret reference, reporting currency and settlement currency. No balances or currency conversions are inferred. All accounts in this milestone are in an ephemeral practice workspace; a persistent demo/live account classification is deferred.

Specifications must be supplied with documented values and manual/statement provenance. Sources are recorded, not independently authenticated. The UI accepts an instrument JSON object as a small, tested foundation instead of pretending to know current broker contract sizes. Decimal quantities remain strings in the browser. Python reuses the approved contracts and validates exact values, currencies, source times, CFD requirements and relationships.

Saving changed specification content appends an immutable snapshot. Identical content reuses its snapshot ID. An existing instrument ID cannot be redefined to mean a different broker, symbol, product or venue. The existing database triggers reject snapshot updates and deletions.

## Files and request flow

- `apps/web/src/app/accounts/page.tsx`: Accounts route.
- `apps/web/src/features/accounts/`: responsive interface, account validation and compatibility checks.
- `apps/web/src/app/api/management/[[...path]]/route.ts`: same-origin local bridge; only explicitly supported read/create operations, bounded request bodies, no caching or redirects, local backend address only.
- `services/api/app/api/management.py`: status, account create/list/detail and snapshot register/list/detail endpoints under `/api/v1/management`.
- `services/api/app/schemas/management.py`: validated request contracts; extra fields rejected and validation responses exclude submitted values.
- `services/api/app/services/management.py`: transactional persistence using the existing account/specification services.
- `services/api/app/core/management_access.py`: loopback client/host checks and actual database target guard.
- `services/api/scripts/accounts_practice.py`: disposable, revision-0003 practice runner.

## Safety boundaries and limitations

Management is disabled by default. Enabling the setting alone does not permit normal-database access: the actual SQLAlchemy target must be an absolute SQLite path inside an approved temporary practice folder. The runner cannot accept a caller-supplied database path. Browser tests use their own disposable database. PostgreSQL management is not enabled by this practice boundary.

This is local protection, not production authentication. Local software can still act as the local user. No public or multiuser deployment is supported. No broker passwords or API keys are accepted. Account identities have create/view operations only; editing, deletion, balance history and normal-database enablement require later review.

Instrument specifications form a **shared compatible catalog**, not account-owned private records: accounts with the same broker/server/settlement scope can review the same specifications. Different brokers, recorded servers, settlement currencies or incompatible platforms cannot use them. Account selection does not create an account/instrument assignment. Existing trades and `trade_contexts` are untouched.

The UI displays the first 100 accounts/snapshots with explicit totals. API pagination uses `offset` and `limit` (maximum 100). Full catalog pagination controls are deferred. No new migrations, CFD trade forms, calculator changes, broker synchronization or execution are included.

## Try it safely

From the repository root, terminal 1:

```powershell
.\.venv\Scripts\python.exe services/api/scripts/accounts_practice.py
```

Terminal 2:

```powershell
$env:AVA_PRACTICE="1"
$env:API_BASE_URL="http://127.0.0.1:8002"
npm run dev --workspace @ava/web -- --hostname 127.0.0.1 --port 3200
```

Open <http://127.0.0.1:3200/accounts>. This uses `.next-practice`, separate from the normal app and browser-test builds. Stop both terminals with Ctrl+C. Practice records disappear when the API runner stops; never enter personal records in this workspace.

Create an MT5 practice account with broker `Synthetic broker`, server `Synthetic server`, reporting `GBP` and settlement `USD`. Copy **only** `snapshot.specification` from `services/api/tests/fixtures/cfd-input.synthetic.json` into the specification editor. These are synthetic teaching values, not verified Bybit specifications. Register it, review its full snapshot, then change `contract_size` from `"100000"` to `"200000"` and register again. Both versions must remain visible. Refresh and select the account to confirm persistence during this practice session. Try a mismatched broker and confirm rejection.

The normal journal remains at its usual address. Its Accounts route displays a disabled state unless connected to the isolated runner; do not change its database configuration.

## Validation

Backend regression includes the existing crypto/CFD engines, additive migration rehearsals and immutable snapshot constraints. Browser checks exercise desktop/mobile account creation, version history, refresh persistence, compatibility errors, local bridge protection and the existing journal flows. No reconciliation with real broker statements is claimed.

Measured local validation on 2026-10-16:

- `python -m pytest services/api/tests -q`: **478 passed**, including 439 prior cases and 39 new management cases. One pre-existing Starlette/httpx deprecation warning remains; no test fails from it.
- `python -m ruff check services/api`: passed.
- `python -m ruff format --check services/api`: passed, 79 Python files.
- `npm run lint`, `npm run typecheck`: passed.
- `AVA_E2E=1` / unavailable local API plus `npm run build`: passed using `.next-e2e`.
- `npm run format:check`: passed.
- `npm run test:e2e`: **14 passed in 34.0 seconds** on the final rerun, including explicit specification review selection, account persistence, snapshot history and existing journal regressions on desktop/mobile.
- The manual practice runner started on port 8002; its management status returned `enabled: true`, `mode: local_practice`. The smoke process was stopped after verification.
- Normal database and both preserved backup SHA-256 fingerprints matched the private baseline. Models, migrations, analytics engines, original persistence service and legacy journal feature files have no changes. No normal migration or data write was performed.
- The changed-file path/signature scan found no credentials or private/generated files in the commit candidates. Ignore rules cover databases, environment files, private backups and all three build directories. This scan is a targeted check, not a claim that every possible secret format can be detected.

The owner-authorized `d4ffab4` push was verified on GitHub; Actions run `38885471028` passed `api` and `web`. The owner subsequently authorized pushing **`a00860a`**; that push was verified on `main`, repository visibility remained private, and [Actions run `38973742171`](https://github.com/AVA-CEO/ava-cryptolab/actions/runs/38973742171) passed both jobs. No deployment occurred. These are the recorded results from the push tasks, not a new CI run caused by this closure documentation.

During development, tests caught a snapshot-error wording mismatch, an ambiguous platform label and an ambiguous Next.js alert selector. React lint also identified a loading-effect issue. These were corrected and relevant checks rerun. Routine browser notices about reduced motion and terminal colors are non-failing.
