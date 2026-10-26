# P3: calculate, save and reopen a practice CFD trade

The owner authorized initial CFD creation and verified retrieval **only in a newly created disposable practice database**. This implementation reuses the Decimal position engine, existing ten-table ledger and immutable instrument snapshots. It does not migrate the normal journal or resume an existing practice database.

## What works

- `/cfd-journal`: responsive purple form, verified preview, explicit save, account-scoped table and an expandable trade-detail view.
- EURUSD, USDJPY, XAUUSD and XAGUSD synthetic teaching specifications; BUY/SELL, original lots, entry, stop, target, multiple initial exits, signed costs and supplied dated JPY conversion evidence.
- Open, partially closed and fully closed initial positions. Saved positions cannot yet be edited, amended or deleted.
- GET reloads verify preserved results without executing a calculator. Refreshing the browser retains records while the runner remains active.
- No live prices, broker connection, margin/liquidation claim or broker-authentic statement is implied.

**Disposable means temporary:** stopping the runner removes its new database on normal exit. This is not yet a durable personal journal. An unexpected failure retains the new diagnostic database; the runner never automatically resumes it. Use synthetic examples only.

## Release and accounting safeguards

The new `ava-local-python-release-v1` manifest implements the fuller Path B accepted-evidence format, distinct from the older preview-only manifest. The private release directory retains a deterministic calculator/dependency ZIP, expanded file inventories, distribution metadata, interpreter/standard-library identities, exact platform identity and independently checked golden arithmetic. A canonical manifest identifies its complete build. Preparation requires committed application source outside explicitly labelled automated test qualification.

The operator explicitly selects the manifest digest. A private registry grants `preview` and `accept_save` to that exact new release for this disposable P3 scope. It grants no replay permission. Missing, altered, retired or unapproved releases fail closed. The bounded worker uses the retained payload with isolated Python startup flags, minimal environment and no database handle. Verify artifacts and registry before and after execution and again before writing calculation evidence. No automatic container/host fallback exists.

`engine_build_sha256` is the hash of the local manifest's canonical **build descriptor**, not an OCI image. Each calculation stores a separate full evidence envelope with the software manifest and local execution/approval facts. Its hash is `manifest_sha256`. Stored synthetic B3B-R fixtures keep their earlier verifier and provenance.

Local execution remains unsigned and runs with the user's Windows permissions. It is not an OS sandbox, publisher authentication or proof against a same-user attacker who can rewrite all expected evidence. Retained installed dependency trees are not portable wheels. Exact environment changes require a newly qualified release. PostgreSQL, container replay and full historical local replay remain unverified.

## One save, one transaction

1. Validate the stable UUID submission key and look for an existing matching account-scoped receipt. A committed retry returns the verified earlier record without recalculation, even if the runtime has since become unavailable.
2. Bind the account and snapshot from the new database; verify broker, server/venue, product and currency relationships.
3. Require the draft's selected release digest and calculate through the qualified worker. An unavailable calculation cannot be saved as successful evidence.
4. Acquire SQLite's immediate write transaction; recheck the receipt and trusted inputs after acquiring the lock.
5. Insert the immutable position/original-risk anchor, initial revision, event keys, FX, executions, costs, broker comparisons and full calculation evidence.
6. Seal the revision, publish its head, reconstruct and verify the saved input/result, then insert the exact response receipt. Commit together. Any failure rolls everything back.

The original entry, lots, stop and risk conversion remain fixed. `incurred_once` recognizes each eligible cost once; realized R uses cumulative net realized PnL divided by original planned risk, not remaining-position risk. Unavailable risk/reporting amounts remain explicitly unavailable. No current FX rates are fetched. Broker-reported values remain comparisons, never substitutes for calculated PnL.

GET verifies the published seal, account identity, snapshot fingerprint, normalized child rows, original-risk anchor, canonical hashes, schemas and local evidence-envelope/build identity. It withholds suspect values with an explicit integrity error. This is stored-evidence verification, **not computational replay**. There is no silent repair.

## Run the new session

Use existing installed dependencies. From the repository root, after the reviewed implementation is committed:

```powershell
cd services/api
..\..\.venv\Scripts\python.exe scripts/cfd_journal_practice.py --prepare
```

Review `.local-cfd-personal/manifest.json` locally. The directory is ignored by Git and must not be uploaded. Copy the exact printed `sha256:...` digest:

```powershell
..\..\.venv\Scripts\python.exe scripts/cfd_journal_practice.py --approve-release sha256:YOUR_PRINTED_DIGEST
```

The new CFD API binds only `127.0.0.1:8004`. Preparation refuses to overwrite an existing release directory. To restart this practice runner, reuse its reviewed digest rather than preparing over it. Each runner start creates a new database; it does not reopen old sessions.

For a fully separate website with a fresh empty crypto/Accounts testing backend, another root terminal:

```powershell
cd services/api
..\..\.venv\Scripts\python.exe scripts/e2e_server.py --port 8011
```

Another terminal, from the repository root:

```powershell
$env:AVA_CFD_P3='1'
$env:API_BASE_URL='http://127.0.0.1:8011'
$env:CFD_API_BASE_URL='http://127.0.0.1:8004'
$env:CFD_JOURNAL_API_BASE_URL='http://127.0.0.1:8004'
npm run build
npm run start --workspace @ava/web -- --hostname 127.0.0.1 --port 3302
```

Open **http://127.0.0.1:3302/cfd-journal**. The separate `.next-p3` build avoids overwriting the existing site's output. Existing journal/practice servers are not stopped or reused. On Vercel the financial proxy remains disabled; authenticated durable storage and explicit cloud approval are still required. No deployment is included.

## Manual acceptance

1. Select EURUSD, keep the labelled synthetic specification, and calculate. Expect gross/net 8 USD, original risk 20 USD, realized 0.40R and 0.06 lots remaining.
2. Save once. Open the new row, inspect original entry/stop, executions, costs, specification and evidence hashes.
3. Refresh the page and reopen the saved row in the table. The same position ID and amounts should return.
4. Start a new trade. Include the second exit of 0.06 lots at 1.10300. With signed costs totalling -4 USD, expect gross 26 USD, net 22 USD and 1.10R. Save and reopen.
5. Try USDJPY with an explicit hypothetical conversion, then gold/silver. Native and account reporting currencies must stay separate.
6. Change inputs after preview: saving must require a new calculation. Over-closing must be rejected.
7. Check mobile layout, keyboard focus and light/dark themes. Confirm existing crypto, academy, trivia, markets and IQ navigation still works.

Automated lost-response and concurrency tests supplement these steps. Manual acceptance remains **pending owner observation**; automated browser checks are not a claim that the owner performed them.

## Validation commands

```powershell
$env:DATABASE_URL='sqlite://'
.\.venv\Scripts\python.exe -m pytest services/api/tests -q
.\.venv\Scripts\python.exe -m ruff check services/api
.\.venv\Scripts\python.exe -m ruff format --check services/api
npm run lint
$env:AVA_CFD_P3='1'
npm run typecheck
npm run build
npm run test:e2e
npm run format:check
git diff --check
```

All browser workers create fresh temporary databases on separate ports. No command targets the normal SQLite journal or preserved backups. The final completion report records the actual validation results.

## Recorded validation: 2026-10-26

| Check                                                            | Actual result                                                                 |
| ---------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Complete backend suite                                           | **805 passed**, no failures/errors/skips; 382.42 seconds                      |
| Desktop/mobile browser regressions                               | **32 passed**; includes calculate/save/refresh/reopen and lost-response retry |
| Python Ruff lint/format                                          | Passed                                                                        |
| Frontend lint, TypeScript and production build                   | Passed                                                                        |
| Repository formatting and whitespace                             | Passed                                                                        |
| Normal journal, preserved backups and existing practice sessions | Excluded from test targets; no migrations or record changes                   |
| PostgreSQL and historical replay                                 | **UNVERIFIED**, not claimed as tested                                         |

Initial test assertions were corrected to match existing behavior: canonical Decimal strings omit redundant zeros, busy concurrent worker requests may return 429 before an idempotent retry, invalid direct-service inputs may raise Pydantic validation errors, and unsupported historical schemas return 503 `historical_schema_unavailable`. The lost-response browser assertion was narrowed to the application's alert rather than Next.js's accessibility announcer. These fixes did not relax financial or access checks. Review also pinned both host canonicalizers to the retained release before activation.

The backend emitted one upstream Starlette/httpx deprecation warning; no dependencies were changed to suppress it. Owner manual acceptance is still pending and is separate from these automated results. Detailed local test artifacts remain private under ignored paths.

## Exact implementation manifest

- `.gitignore`
- `.prettierignore`
- `README.md`
- `apps/web/eslint.config.mjs`
- `apps/web/next.config.ts`
- `apps/web/playwright.config.ts`
- `apps/web/playwright.p3.config.ts`
- `apps/web/tsconfig.json`
- `apps/web/src/app/api/cfd-preview/route.ts`
- `apps/web/src/app/api/cfd-journal/route.ts`
- `apps/web/src/app/cfd-journal/page.tsx`
- `apps/web/src/features/cfd-preview/workspace.tsx`
- `apps/web/src/features/cfd-journal/contracts.ts`
- `apps/web/src/features/cfd-journal/workspace.tsx`
- `apps/web/src/features/cfd-journal/journal.css`
- `apps/web/src/lib/navigation.ts`
- `apps/web/tests/cfd-journal.spec.ts`
- `docs/learning-journal.md`
- `docs/p3-cfd-journal.md`
- `services/api/app/core/cfd_access.py`
- `services/api/app/core/cfd_settings.py`
- `services/api/app/database/cfd_session.py`
- `services/api/app/database/cfd_personal_session.py`
- `services/api/app/cfd_personal.py`
- `services/api/app/schemas/cfd_personal.py`
- `services/api/app/schemas/cfd_personal_release.py`
- `services/api/app/services/cfd_personal_codec.py`
- `services/api/app/services/cfd_personal_integrity.py`
- `services/api/app/services/cfd_personal_positions.py`
- `services/api/app/services/cfd_personal_release.py`
- `services/api/app/services/cfd_personal_worker.py`
- `services/api/scripts/cfd_journal_practice.py`
- `services/api/scripts/e2e_personal_server.py`
- `services/api/scripts/e2e_cfd_server.py`
- `services/api/scripts/e2e_server.py`
- `services/api/tests/test_cfd_personal_api.py`
- `services/api/tests/test_cfd_personal_persistence.py`
- `services/api/tests/test_cfd_personal_target.py`
- `services/api/tests/test_personal_release.py`
