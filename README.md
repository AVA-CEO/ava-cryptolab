# AVA CryptoLab

**Analyse. Learn. Trade Smarter.**

A cryptocurrency research, trading journal and education platform built incrementally as a full-stack engineering project. It helps explain trading decisions and market mechanics without profit promises or exchange execution.

## Current direction: Path B — product-first personal journal

**The web application now includes a disposable CFD journal.** Follow the [P3 guide](docs/p3-cfd-journal.md) to calculate, save, refresh and reopen forex/metals positions in a newly created practice session. The complete Path B local release and evidence verifier qualify this explicitly selected save path. Existing practice services and the normal journal remain separate. Academy, trivia, the educational watchlist, candle lab and Trading IQ remain usable. No Docker/WSL installation, normal-journal migration or deployment is included.

The retained [local policy](docs/path-b-local-calculation-policy.md), [Python release specification](docs/path-b-python-release-spec.md) and [product-first roadmap](docs/product-first-roadmap.md) record the P1 proposal and accepted-evidence design. The earlier [web delivery](docs/web-product-delivery.md) used the narrower preview-only format; P3 adds the distinct `ava-local-python-release-v1` and per-calculation evidence envelope. Synthetic B3B-R fixtures retain their original provenance and verifier. Local acceptance is not broker authentication or historical replay.

Completed capabilities now include initial CFD saving in the newly isolated P3 session. Durable personal CFD saving remains unavailable:

| Area                                                          | Actual status                                                                                                           |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Crypto journal, performance charts and Trading IQ foundations | Working local features; Phase 2 accepted on nine owner-reported manual passes                                           |
| Accounts and immutable specifications                         | 2B.4A accepted on eight owner-reported practice scenarios; not everyday CFD account integration                         |
| CFD contracts and calculation engines                         | Separate Decimal engine, multiple exits, verified local-personal preview/create/read in the new disposable P3 session   |
| B2 ledger and migration 0004                                  | Ten-table schema and SQLite disposable validation completed; normal journal remains at owner-approved 0003              |
| B3A and B3B-R                                                 | Default unavailable boundary and synthetic GETs retained; P3 uses a separate local evidence verifier and guarded writer |
| R1/R2A                                                        | Read-only assessment/planning; no runtime installed; R2A report remains local/uncommitted                               |
| Markets, lab, academy and trivia                              | Educational screener/watchlist, candle exercise, eight lessons and sixteen server-checked questions; no live feed       |

Read the [B2 guide](docs/phase-2b-4b-b2.md), [validation report](docs/phase-2b-4b-b2-validation.md), [B3A guide](docs/phase-2b-4b-b3a.md) and [B3B-R guide](docs/phase-2b-4b-b3b-r.md). Earlier documents retain historical approval language; later explicit owner authorizations and milestone reports define what was actually completed. PostgreSQL compatibility and historical container replay remain **UNVERIFIED**. Signed containers remain a future optional profile; no existing approval or synthetic evidence is silently reclassified.

**2B.4A is accepted and closed (2026-10-17): 8/8 user-reported manual acceptance scenarios passed.** These are the owner's observations, separate from automated results. Read the [acceptance report](docs/phase-2b-4a-acceptance.md).

The new [Accounts workspace guide](docs/phase-2b-4a.md) explains isolated account creation, explicit currencies and immutable specification review. Start its temporary API and separate frontend to test at `http://127.0.0.1:3200/accounts`. Management stays disabled for the normal journal. No new migration or historical account assignment is included. See the [four-step integration roadmap](docs/phase-2b-4-plan.md) and [proposed persistence milestone](docs/phase-2b-4b-plan.md).

Phase 2 is accepted on the owner's nine reported manual passes. Phase 2B adds account/instrument contracts and five additive persistence tables, with disposable migration and backup-restore rehearsals. **The normal local journal was migrated to `0003` after explicit approval and preservation checks**, with verified private backups retained. Read the [normal migration verification](docs/migration-0003-verification.md) and [safe rehearsal report](docs/phase-2b-2.md). Account management now works in disposable practice mode; Durable personal CFD integration and broker synchronization remain future milestones; P3 adds a separate disposable journal.

The separate [CFD input contracts](docs/phase-2b-3a.md), [single-close calculator](docs/phase-2b-3b.md) and [position accounting engine](docs/phase-2b-3c.md) support validated Decimal accounting. The position engine handles open, partial and closed positions, multiple exits, incurred-once costs, fixed original risk and separate broker-comparison evidence. P3 packages that engine through an explicitly approved local release rather than using the standalone tools as a save bypass.

The single-close tool remains unchanged and deliberately rejects partial positions; use the position tool for those. Supported modes are explicitly defined forex, linear CFD and index CFD contracts; tick-based modes remain unavailable. Durable personal CFD persistence, saved-trade revisions, real broker reconciliation and broker connections remain unavailable. Existing crypto calculations and the purple interface are retained.

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

The dashboard starts empty. **No personal trades or live market prices are seeded.** After you save trades, the command center displays recorded journal analytics. Sample mode remains simulated, ephemeral and separate from the database. Academy, trivia, the candle lab and educational market watchlist are usable; live market data remains unavailable.

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
# Existing owner-approved journal at 0003 only: do not apply migration 0004 here.
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — frontend, from the repository root:

```powershell
npm run dev
```

Open **http://localhost:3000**. API documentation: **http://127.0.0.1:8000/docs**.

The backend commands above assume the existing journal schema. For fresh disposable testing, use the [rehearsal commands](docs/phase-2b-4b-b2.md); the B2 guard intentionally rejects normal-database migration commands. Defaults work without environment files. See [.env.example](.env.example) and [setup guide](docs/development.md) for custom configuration. If the API is offline, the interface displays a helpful status; sample mode still works.

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

Foundation and the original crypto journal are completed. The revised delivery order is:

1. **P1 — policy documentation and sign-off:** local-personal amendment, release specification and this roadmap; no capability activation.
2. **P2 — interactive forex/metals preview:** delivered purple UI, verified Python engine, explicit synthetic examples and no saving on the preview-only service.
3. **P3 — safe saving and retrieval:** implemented atomic initial creation, idempotency and versioned verification on new disposable datasets; see the [P3 guide](docs/p3-cfd-journal.md).
4. **P4 — everyday journal workflow:** editing through revisions, partial exits, corrections, filtering and export.
5. **P5 — multi-asset analytics and Trading IQ:** account/currency-aware performance and a dedicated insights workspace.
6. **P6 — persistent personal acceptance:** separately approved dataset/location, backups/restoration and broker-statement reconciliation; no implied normal-journal migration.

Teach lots, pips, leverage and risk during P2. Deliver small curated lesson/quiz slices alongside subsequent journal milestones, then expand the academy/trivia and live market screener/watchlists. Preserve the original five-level education, market-lab and gamification vision without making all modules prerequisites for a usable journal. Authentication and ownership authorization remain prerequisites for any later public/multiuser deployment; local access guards do not replace them. Details and manual acceptance gates are in the [product-first roadmap](docs/product-first-roadmap.md).

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
