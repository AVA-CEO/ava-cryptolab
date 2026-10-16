# Testing

## Phase 2B.4A practice account checks

The owner formally accepted 2B.4A on **2026-10-17**, reporting **8/8 manual scenarios passed** in the isolated Accounts workspace. See the [manual acceptance report](phase-2b-4a-acceptance.md). These results are not additional automated cases and were not independently performed by Codex. The [2B.4B test matrix](phase-2b-4b-design-review.md#12-test-plan-and-approval-checkpoints) is a future plan, not an executed test suite.

The [milestone report](phase-2b-4a.md) covers 39 new synthetic backend cases plus all 439 prior regressions: **478 backend tests pass**. Tests cover account identities, duplicates, currency independence, compatible shared catalogs, incompatible scope rejection, immutable versions, exact precision, missing evidence, safe error responses and disabled/non-loopback/database-target guards. Databases are disposable; no normal journal or backup is a test target.

Run `npm run test:e2e` for the desktop/mobile account flows and existing journal regressions. The browser API runner enables management only for its temporary database. Production builds and browser checks use `.next-e2e` sequentially; the separate manual practice commands in the milestone guide use `.next-practice`. No additional database migration or dependency is required.

## Phase 2B.3C position checks

The [position report](phase-2b-3c.md) records **439 backend passes**: previous 357 plus 82 new cases. Synthetic tests cover the owner's 8 + 18 USD example, four incurred costs, open/partial/closed cutoffs, shorts/losses, JPY rates, metals, invalid ledgers, comparison evidence, exact rounding and maximum ledger cardinality. Existing single-close and crypto regressions remain intact; normal journal data and backups are never test targets.

```powershell
.\.venv\Scripts\python.exe services/api/scripts/calculate_cfd_position.py services/api/tests/fixtures/cfd-position.synthetic.json
.\.venv\Scripts\python.exe services/api/scripts/calculate_cfd_position.py services/api/tests/fixtures/cfd-position-costs.synthetic.json --json
.\.venv\Scripts\python.exe -m pytest services/api/tests -q
```

Expect 26 USD / 1.30R without costs and 22 USD / 1.10R with the supplied costs. Numeric synthetic comparison agreement is not real-statement reconciliation. All commands use the existing environment; there are no new dependencies or migrations.

## Phase 2B.3B calculation checks

The [calculator report](phase-2b-3b.md) records **357 backend passes**, including the previous 266 and 91 new cases. Synthetic hand-worked expectations cover EURUSD/GBPUSD longs and shorts, JPY-profit/USD-reporting cases, supplied gold/silver contract sizes, signed costs, original risk and R, unavailable inputs, precision and rounding. Independent `Fraction` cash ledgers verify exact results, including extreme input/FX products. These are synthetic calculation checks, not real broker reconciliation.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe services/api/scripts/calculate_cfd.py services/api/tests/fixtures/cfd-calculation.synthetic.json
.\.venv\Scripts\python.exe services/api/scripts/calculate_cfd.py services/api/tests/fixtures/cfd-jpy-calculation.synthetic.json --json
.\.venv\Scripts\python.exe -m pytest services/api/tests -q
```

The calculator command reads a request file only. It never opens the journal database, applies migrations or calls a broker. No new environment variables or dependencies are required. Keep the existing lint/format/build/browser checks below; normal data and backups are not test targets. Production build and browser checks use the isolated `.next-e2e` directory sequentially.

## Phase 2B.3A CFD validation

The [milestone report](phase-2b-3a.md) records the actual results. The backend suite now has **266 passing cases**: the existing 99 plus 167 new validation/precision/compatibility cases. New CFD tests use synthetic fixtures and disposable SQLite sessions; they do not test a CFD profit calculator or reconcile broker statements. Test modules retain the project's existing flat import convention.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest services/api/tests -q
.\.venv\Scripts\python.exe -m ruff check services/api
.\.venv\Scripts\python.exe -m ruff format --check services/api
.\.venv\Scripts\python.exe services/api/scripts/validate_cfd_input.py services/api/tests/fixtures/cfd-input.synthetic.json
```

To lint/check/build while a normal frontend is running, use a separate PowerShell terminal and the existing isolated output directory. Keep browser tests sequential with this build because both use `.next-e2e`:

```powershell
$env:AVA_E2E = "1"
$env:API_BASE_URL = "http://127.0.0.1:59999"
npm run lint
npm run typecheck
npm run build
npm run format:check
```

The unreachable API address prevents accidental real-journal access during build. Browser-test configuration supplies its own disposable API URL. No dependency changes are required for this milestone.

## Phase 2B migration rehearsals

Use `.\.venv\Scripts\python.exe services/api/scripts/rehearse_multi_asset.py` from the root. It creates and backs up a synthetic legacy database and screenshot, migrates only that disposable database, compares old records/calculations, checks Alembic metadata and rehearses safe reversal. The temporary files are removed on exit. Full tests also verify backup restoration, injected-failure rollback, immutable snapshot guards and relationship constraints. See [2B.2](phase-2b-2.md) for exact scope and PostgreSQL limits. The separately approved [normal journal migration](migration-0003-verification.md) is complete; it is not an automated test target.

## Phase 2 coverage

Backend coverage now includes trade CRUD, stale versions, linear long/short and spot inventory PnL, funding credits, partial exits, closed-only aggregate metrics, validation failures, currency separation, decimal persistence, CSV atomic validation and duplicate protection, screenshot validation/cleanup, local mutation guards and Trading IQ sample thresholds.

Playwright starts a disposable API/database on port 8001 and a frontend on port 3100 configured to reach that API. Tests run serially against this shared disposable environment. They cover create/view/edit/search/delete flows and form feedback on desktop/mobile as well as the existing workspace flows. Free ports 3100 and 8001 before tests. The frontend uses the ignored `.next-e2e` build folder. This setup never connects to the personal development database. CI installs backend dependencies for the browser job too.

Use the README validation commands. The original Phase 1 notes follow for context.

Backend tests use an isolated in-memory SQLite database and dependency overrides. They cover health, schema readiness, empty financials, stored balances and unsupported currency aggregation. They never use local trading records.

Playwright covers empty onboarding, entering/exiting labelled sample mode, date selection, chart selection, theme persistence, module navigation and page overflow at desktop and mobile dimensions. The web server is started automatically. An API is not required for these UI flows; offline status is an intentional supported state. Live API connectivity is checked separately.

Run the commands in the README. Install Chromium with `npx playwright install chromium` in `apps/web` once. CI uses `--with-deps` on Linux.

Frontend linting uses ESLint directly (not the removed `next lint` command). TypeScript checks run separately from production builds. Ruff checks Python imports and lint rules. `alembic check` detects differences between model metadata and the upgraded schema.

Financial analytics and external-provider tests are added with Phases 2 and 3. Do not claim those features are verified by the Phase 1 fixture charts. Production deployment, PostgreSQL concurrency and multi-user security are outside current verification.

Visual QA should check 390px, tablet and desktop widths, both themes, keyboard focus, mobile navigation, chart tooltips, sample labels and reduced-motion preferences. CI complements manual review; it does not prove perfect accessibility or visual quality.
