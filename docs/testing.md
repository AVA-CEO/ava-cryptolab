# Testing

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
