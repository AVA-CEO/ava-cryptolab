# Phase 2 — Advanced Trading Journal

Status: **closed following owner-reported manual acceptance**. All nine planned manual scenarios were reported passed by the owner in the isolated practice journal. These are human observations, not automated tests performed by Codex. See the [acceptance report](phase-2-acceptance.md).

Phase 1 was finalized with the owner-confirmed repository-local author identity. The journal backend was committed as `feat(api): add journal ledger analytics and Trading IQ evidence rules`. The frontend milestone completes the journal experience while retaining the purple identity and using green for profits, successful actions and closed trade status.

## Working features

- Local persisted trade creation, viewing, editing and confirmed deletion.
- Spot inventory and linear quote-settled futures, one entry and multiple partial exits.
- Entry/exit prices and UTC timestamps, quantity, initial stop, target, costs, funding, leverage and margin type.
- Setup/mistake tags, notes, emotions, lessons and private screenshot upload/view/replacement/removal.
- Decimal PnL and R calculations, expectancy, profit factor, closed-trade drawdown and average outcomes.
- Currency-separated analytics, configurable opening balances, filtering/search/sorting and pagination.
- Transactional CSV import/export with size/row limits, duplicate skipping and formula protection.
- Interactive cumulative closed PnL/balance, daily/monthly/setup charts and duration/risk/entry-hour versus R scatterplots.
- Command center integration with saved records, retaining explicit separate sample mode.
- AVA Trading IQ evidence gates, missing-risk warnings and eligible historical setup/coin/period/mistake/risk reviews.

## Validation

- 33 backend tests passed, including analytics edge cases and API flows.
- 10 desktop/mobile Chromium browser flows passed using disposable databases.
- ESLint, TypeScript and production build passed during implementation.
- Ruff and formatting checks passed during implementation.
- Local migration upgrade and Alembic metadata check passed.
- Runtime npm audit: zero vulnerabilities. The known development-only braces advisory remains documented.
- Visual review covered recorded-trade journal screenshots at desktop and mobile sizes. Those images use disposable synthetic test inputs; they are not market observations or personal trading results.

The implementation commits are published to the private GitHub repository. The latest GitHub Actions run, [Quality checks #1](https://github.com/AVA-CEO/ava-cryptolab/actions/runs/38755310672), completed successfully for both web and API on commit `6a4cee687d6c8745082fcbf5af1aba34ab3ffaf6`; its status was rechecked during closure. The new closure documentation has not been pushed or run remotely. PostgreSQL deployment/runtime and public multi-user authorization remain unverified. Starlette emits the existing TestClient deprecation warning.

## Limits

This is a functional **local single-user journal**, not a public multi-user launch. There is no authentication yet. Public access remains gated. Real market feeds, academy lessons, trivia and gamification remain planned modules. No exchange orders are executed. The command center sample fixtures remain explicitly simulated and never written to the database.

Inverse contracts, automatic scale-ins, deposits/withdrawals, actual exchange collateral and intratrade/mark-to-market drawdown are not modeled. Read the [journal policy](trading-journal.md) before interpreting financial results. Screenshots are private local files, and CSV exports must remain out of Git. MIT licensing remains pending approval.

## Run and try it

From the repository root, terminal 1:

```powershell
cd services/api
..\..\.venv\Scripts\python.exe -m alembic upgrade head
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2, repository root:

```powershell
npm run dev
```

If your frontend is already running on port 3000, keep it and refresh the page instead of starting a second instance. Open **http://localhost:3000/journal**. Choose your settlement currency, record a trade, add an exit, inspect it, and try the filters. Only use actual personal records in your local journal; tests belong in disposable databases.

Defaults work without environment files. `API_BASE_URL` is server-only; `DATABASE_URL`, `APP_ENV=local` and `UPLOAD_DIR` are backend settings. See the README for dependency installation on a fresh checkout.

Run checks from the root:

```powershell
npm run lint
npm run typecheck
npm run build
npm run format:check
.\.venv\Scripts\python.exe -m ruff check services/api
.\.venv\Scripts\python.exe -m pytest services/api/tests
npm run test:e2e
```

Browser tests reserve ports 3100 and 8001; their `.next-e2e` folder and databases are separate from the normal development preview. Do not run them over an active practice session. The owner completed manual acceptance at `http://127.0.0.1:3100/journal` using the isolated practice API on port 8001. See [GitHub connection instructions](github.md). The three implementation commits were pushed with explicit authorization; no application deployment or repository visibility change occurred. New commits require separate push authorization.

Next priority: [Phase 2B — Multi Asset Trading Expansion](phase-2b-plan.md), ahead of Phase 3. Its design direction is approved; coding, migrations and broker connections still require explicit authorization. Existing functionality and the purple visual identity remain requirements.
