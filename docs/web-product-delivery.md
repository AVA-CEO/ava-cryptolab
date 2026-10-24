# Working web delivery

AVA CryptoLab remains a Next.js web application. No Android/native package, Play Store flow, Docker/WSL installation, broker connection or deployment is part of this delivery.

## What works

- Existing local crypto CRUD, partial exits, screenshots, CSV and performance analytics are preserved.
- `/cfd-preview`: BUY/SELL, lots, entry/time, original stop, target, multiple exit prices/quantities/times, signed commissions/swaps/fees and optional explicitly hypothetical JPY-to-USD conversion. Results come from the existing separate Python Decimal engine. Native and reporting availability, original risk, net/gross PnL, remaining quantity and realized R are shown. Inputs/results are not saved in the browser or ledger.
- `/insights`: dedicated Trading IQ using recorded crypto analytics, separate USD/USDT/USDC cohorts, existing evidence thresholds and charts. No synthetic CFD fixture is included in these statistics.
- `/academy`: eight curated beginner lessons with goals, explanations, examples and browser-local completion tracking.
- `/trivia`: sixteen original four-choice questions, grading/explanations from the Next.js server, topic selection and browser-local first-attempt score tracking. Public question responses omit answer keys. This is personal practice progress, not authenticated achievement evidence.
- `/markets`: searchable/sortable fictional market examples, a browser-local watchlist and two educational scatterplots. Every numeric market figure is explicitly fictional. No live price, volume or volatility provider is connected.
- `/lab`: interactive candle-direction exercise and practical market-mechanics explanations. The candle exercise is unscored browser education, not server-certified trivia or a trading signal.

Purple branding, light/dark mode and responsive layouts are retained. Unknown/unavailable data is not replaced with fake recorded profits.

## Start a protected local practice website

Use existing installed dependencies. No install/download is needed for these commands. Start from the repository root. Keep the normal journal and previous practice sessions separate. If any proposed port is occupied, do not stop that process automatically; choose a separately reviewed configuration instead.

**Terminal 1: a NEW disposable crypto journal for this preview website**

```powershell
cd services/api
..\..\.venv\Scripts\python.exe scripts/e2e_server.py
```

This existing runner creates a fresh synthetic testing database and explicitly migrates that new target. It uses port 8001. It does not open/migrate the normal journal or resume previous Accounts data. Records entered here are temporary and disappear when this practice runner stops. Your existing normal journal remains a separate application on its original ports.

**Prepare the private preview-only release once, from the root:**

```powershell
.\.venv\Scripts\python.exe services/api/scripts/cfd_preview_practice.py --prepare
```

This copies reviewed calculator/schema files and required existing dependencies into ignored `.local-cfd-preview/`, records the Git source commit/dirty state, Python/stdlib/native-runtime identity, exact dependency versions, source-file hashes, canonicalizer hash and Decimal settings, and prints a `sha256:...` release digest. It does not calculate or activate anything. It refuses to overwrite an existing release directory. Inspect its manifest; do not publish the private artifact directory or edit a digest to force acceptance. A source-dirty release is test-only; normal startup rejects it. Commit reviewed source before preparing a usable personal preview release.

**Terminal 2: explicitly select the reviewed digest:**

```powershell
.\.venv\Scripts\python.exe services/api/scripts/cfd_preview_practice.py --approve-release sha256:PASTE_THE_EXACT_PRINTED_DIGEST
```

This starts only NEW disposable CFD data on 8003 and grants only preview capability for that exact unsigned local release. It provides clearly labelled synthetic accounts/specifications, not actual broker rules. Any artifact/interpreter/canonicalizer mismatch blocks startup/execution; there is no fallback. A fixed `-I -S -B` Python worker uses frozen imports and a nonexistent bytecode prefix; output/deadline limits and before/after verification apply. This is local execution with your user's permissions, not an OS security sandbox or historical replay guarantee. Do not reuse a synthetic test release as accepted financial evidence.

**Terminal 3: frontend, from the root**

```powershell
$env:API_BASE_URL='http://127.0.0.1:8001'
$env:CFD_API_BASE_URL='http://127.0.0.1:8003'
npm run dev -- --hostname 127.0.0.1 --port 3300
```

Open **http://127.0.0.1:3300**. The environment changes above apply only to this shell/process. Do not overwrite normal journal environment files. If testing alongside another Next development session, use the production-start command below after the build rather than sharing a development lock.

```powershell
npm run build
npm run start --workspace @ava/web -- --hostname 127.0.0.1 --port 3300
```

Use Ctrl+C in these terminals to stop only these owned sessions. Do not terminate all Python/Node processes, reset databases or delete release artifacts as a troubleshooting shortcut.

## Quick manual checks

1. Preview the EURUSD default partial exit: native gross 8 USD, original risk 20 USD, remaining 0.06 lots and 0.40R with no costs.
2. Add 0.06 lots at 1.10300, using a valid time through the cutoff: cumulative gross 26 USD. Enter costs totaling -4 USD once: net 22 USD and 1.10R. No Save action is available.
3. Select USDJPY: JPY outcomes are available while USD is unavailable under native-only policy. Supply a hypothetical 0.005 USD per JPY: the form supplies explicitly labelled same-time teaching observations, never a fetched/current rate. It does not claim historical broker FX evidence.
4. Select gold/silver, review the synthetic contract sizes and change inputs. Invalid stops, times, account scope or over-closing produce validation errors. Change an input after success: the previous result becomes stale.
5. Complete a lesson and reload. Answer a quiz, read its server explanation and reload to see browser-local practice progress. Browser storage may be cleared or edited and is not authoritative account progress.
6. Watch an educational market asset, reload, search/filter it and inspect the fictional scatterplot axes. No figures should be mistaken for live data.
7. Test desktop/mobile, themes and keyboard navigation. The automated suite uses NEW disposable databases, not the normal journal.

## Accepted saving remains unavailable

There is no POST positions endpoint, CFD revision editor, accepted local-evidence reader or normal database migration. The ten-table ledger, constraints and existing synthetic read verifier remain intact.

This delivery deliberately implements a smaller preview-only manifest, `ava-local-preview-build-v1`. It verifies actual frozen files, exact interpreter/runtime fingerprint, dependency payload and Decimal/canonicalizer identity, and requires an exact owner-selected digest. It does **not** implement P1's full `ava-local-python-release-v1` artifact/approval-history format, retained reconstruction archives, per-revision accepted-evidence envelope or complete historical verifier. Approval is process-local and preview-only; no accepted receipt is generated. This is an explicit delivery limitation, not an implementation of the full P1 release specification under a different name.

Accepted saving is blocked until the full accepted-release/evidence contract, original-risk anchors, idempotent transactional creation, accepted-format read verification and round-trip/rollback tests are implemented and qualified on fresh disposable data. A persistent personal CFD dataset also needs its own approved location, backup/recovery policy and acceptance; no permission to migrate the normal journal is inferred. Actual broker reconciliation still needs redacted real statements. PostgreSQL and historical container replay remain UNVERIFIED.

## Vercel: frontend preview only

Project root: `apps/web`; framework: Next.js; build: `npm run build`. Use the monorepo lockfile/workspace installation behavior. No API keys/account connection is needed for the current educational screens. Connecting the private repository and creating a Vercel project/deployment still requires owner approval; no connection or deployment was made here.

On Vercel, the server-only `VERCEL` flag unconditionally disables journal, Accounts and CFD bridges and prevents server dashboard retrieval, even if a caller supplies a loopback Host. Do not configure local API URLs, personal databases, uploads, broker credentials or market keys for this preview. The explicit dashboard sample mode, lessons, stateless server-graded quizzes, candle lab and educational market/watchlist work without a financial backend. This is not a deployed production financial journal.

Never use Vercel's ephemeral filesystem/SQLite for persistent financial records. A later secure financial release requires authentication, per-user authorization, a durable database, secure attachment storage, an appropriately hosted Python service and cloud-qualified configuration/tests. FastAPI's normal app still refuses nonlocal deployment; do not set `APP_ENV=local` on a public server to bypass it. Vercel hosts only the Next.js frontend in this proposal. No claim of cloud persistence or deployed security validation is made.

## Validation

Run the existing checks with installed tools:

```powershell
.\.venv\Scripts\python.exe -m pytest services/api/tests -q
.\.venv\Scripts\python.exe -m ruff check services/api
.\.venv\Scripts\python.exe -m ruff format --check services/api
npm run lint
npm run typecheck
npm run build
npm run format:check
npm run test:e2e
```

The browser suite starts its own fresh APIs on 8001/8003 and frontend on 3100, never reusing existing servers. Stop only your own new preview sessions before running it if those ports are occupied. Synthetic browser-test release approval is explicitly test-only and cannot accept real records.

Measured on 2026-10-24: **703 backend tests passed; 26 desktop/mobile browser tests passed**. Python lint/format, frontend lint, TypeScript, production build and repository formatting passed. A production-server smoke check with `VERCEL=1` returned 403 for journal/Accounts/CFD bridges while the educational catalog and server quiz grading worked. This simulates the hosting guard locally; it is not an actual Vercel deployment test. The backend emitted one existing Starlette/httpx TestClient deprecation warning; browser runs emitted reduced-motion/color-environment notices. No package was installed to suppress warnings.

The first runs found a missing adjustment description in a new synthetic test, a default-route-manifest regression, an overly internal origin comparison and an ambiguous browser alert selector. These were corrected and the passing suites rerun. Initial sandbox filesystem restrictions required permission to run temporary-database tests/format traversal outside the sandbox; no system security feature or validation hook was disabled. The R2A report's original SHA-256 remained unchanged; normal journal/backups/old practice records were not test targets.
