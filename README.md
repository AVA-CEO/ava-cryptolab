# AVA CryptoLab

**Analyse. Learn. Trade Smarter.**

A cryptocurrency research, trading journal and education platform built incrementally as a full-stack engineering project. It helps explain trading decisions and market mechanics without profit promises or exchange execution.

## Current milestone: Phase 2 — Advanced Trading Journal

- Persisted trade creation, viewing, editing and confirmed deletion.
- Spot inventory and linear futures, partial exit executions, initial stops/targets, fees, funding, leverage and margin type.
- Setup and mistake tags, notes, before/after emotions, lessons and validated private screenshot attachments.
- Decimal-based PnL and R, expectancy, profit factor and closed-trade drawdown. USD, USDT and USDC remain separate.
- Searching, date/strategy/exchange/status/outcome filtering, sorting, pagination and transactional CSV import/export.
- Interactive closed-performance charts and duration/risk/entry-hour-versus-R scatterplots.
- AVA Trading IQ evidence rules with transparent minimum observation counts.

See the [journal guide](docs/trading-journal.md), [Trading IQ architecture](docs/trading-iq.md) and [Phase 2 report](docs/phase-2.md).

### Foundation retained from Phase 1

- Next.js App Router, TypeScript and Tailwind CSS; shadcn-style reusable button, Lucide icons, Motion and Recharts.
- Responsive command center with collapsible navigation, mobile menu, workspace search, light/dark themes and honest empty states.
- Explicit sample mode: calculated sample metrics, equity curve, daily PnL, journal examples and duration-versus-R scatterplot.
- FastAPI with Pydantic, SQLAlchemy, Alembic and a local SQLite database. PostgreSQL driver included.
- API health/readiness, validated server-side frontend integration, backend tests and Playwright flows.
- GitHub Actions for lint, types, build, backend tests, migration validation and browser tests.

The dashboard starts empty. **No personal trades or live market prices are seeded.** After you save trades, the command center displays recorded journal analytics. Sample mode remains simulated, ephemeral and separate from the database. Market, academy, lab and trivia routes remain roadmap previews.

## Run locally (PowerShell)

Prerequisites: Node.js 22+ (22 LTS recommended), Python 3.12+ (3.13 tested), Git.

From the repository root:

```powershell
npm ci
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r services/api/requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e services/api
```

Terminal 1 — backend:

```powershell
cd services/api
..\..\.venv\Scripts\python.exe -m alembic upgrade head
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — frontend, from the repository root:

```powershell
npm run dev
```

Open **http://localhost:3000**. API documentation: **http://127.0.0.1:8000/docs**.

Defaults work without environment files. See [.env.example](.env.example) and [setup guide](docs/development.md) for custom configuration. If the API is offline, the interface displays a helpful status; sample mode still works.

## Validate

```powershell
npm run lint
npm run format:check
npm run typecheck
npm run build
.\.venv\Scripts\python.exe -m ruff check services/api
.\.venv\Scripts\python.exe -m pytest services/api/tests
cd apps/web
npx playwright install chromium
cd ../..
npm run test:e2e
```

Details and limits: [testing guide](docs/testing.md).

## Architecture and roadmap

```text
apps/web/          Next.js UI, reusable components and feature modules
services/api/     FastAPI, database models, schemas and migrations
packages/shared/  Reserved for generated API contracts when needed
docs/             Architecture, setup, tests and deployment notes
.github/workflows/ Automated validation
```

1. **Foundation** — completed.
2. **Journal** — current milestone: CRUD, executions, risk calculations, performance charts, CSV and Trading IQ foundations.
3. **Market intelligence** — provider adapters, caching, screener and watchlists.
4. **Academy** — curated learning paths, lessons and server-validated quiz attempts.
5. **Gamification** — achievements, streaks and minigames.
6. **Production readiness** — authentication, ownership authorization, security, accessibility and deployment.

Read [architecture](docs/architecture.md), [deployment preparation](docs/deployment.md) and [contribution guidelines](CONTRIBUTING.md).

## Connect to GitHub

Beginner walkthrough: [connect Git to GitHub](docs/github.md). Local commits are already created; no remote is configured or pushed by the agent.

Create an **empty** repository named `ava-cryptolab` in GitHub (no generated README or licence). Then:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/ava-cryptolab.git
git branch -M main
# Only when you explicitly decide to publish the source:
git push -u origin main
```

No remote is configured or pushed by this milestone. Database files, uploads, secrets, environments and build artifacts are ignored.

## Licence

MIT is proposed, pending the project owner’s approval. No project licence is granted yet. A proposal is in [docs/license-proposal.md](docs/license-proposal.md). Third-party packages retain their own licences.
