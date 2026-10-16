# AVA CryptoLab

**Analyse. Learn. Trade Smarter.**

A cryptocurrency research, trading journal and education platform built incrementally as a full-stack engineering project. It helps explain trading decisions and market mechanics without profit promises or exchange execution.

## Current milestone: Phase 2B.2 — Multi-asset persistence rehearsals

Phase 2 is accepted on the owner's nine reported manual passes. Phase 2B adds account/instrument contracts and five additive persistence tables, with disposable migration and backup-restore rehearsals. **The normal local journal was migrated to `0003` after explicit approval and preservation checks**, with verified private backups retained. Read the [normal migration verification](docs/migration-0003-verification.md) and [safe rehearsal report](docs/phase-2b-2.md). Account-management screens, CFD entry/calculations and broker synchronization remain future milestones.

The working journal currently supports:

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
# Fresh empty development database; the existing normal journal is already at 0003.
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
2. **Journal** — accepted: CRUD, executions, risk calculations, performance charts, CSV and Trading IQ foundations.
   **Phase 2B** — account/instrument contracts and additive persistence rehearsals; account management, CFD calculations, reconciliation and combined analytics follow before Phase 3.
3. **Market intelligence** — provider adapters, caching, screener and watchlists.
4. **Academy** — curated learning paths, lessons and server-validated quiz attempts.
5. **Gamification** — achievements, streaks and minigames.
6. **Production readiness** — authentication, ownership authorization, security, accessibility and deployment.

Read [architecture](docs/architecture.md), [deployment preparation](docs/deployment.md) and [contribution guidelines](CONTRIBUTING.md).

## Connect to GitHub

The project is connected to the owner's private `AVA-CEO/ava-cryptolab` repository. Earlier commits were pushed with explicit authorization; new milestone commits stay local until separately approved. Beginner reference: [GitHub guide](docs/github.md).

```powershell
git status
git log --oneline -5
git remote -v
```

This milestone does not push or deploy anything. Database files, uploads, secrets, environments and build artifacts are ignored.

## Licence

MIT is proposed, pending the project owner’s approval. No project licence is granted yet. A proposal is in [docs/license-proposal.md](docs/license-proposal.md). Third-party packages retain their own licences.
