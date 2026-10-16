# Architecture

## Phase 2B.3B independent calculation engine

The [single-close CFD calculator](phase-2b-3b.md) accepts a validated trade plus explicit per-currency rounding policy. `analytics/cfd.py` performs pure Decimal accounting for an allowlist of linear calculation modes; `schemas/cfd_results.py` separates raw money, rounded display values and unavailable reasons. Native profit remains visible before explicit cash-flow-time reporting conversions. A fresh 160-digit Decimal context keeps cash operations exact over the bounded input domain; ratios use that finite precision. No rate is fetched or inferred.

`analytics/products.py` is an opt-in dispatcher. CFD requests use only the CFD engine. Matching legacy crypto `Trade` objects use the unchanged legacy calculator and response structure through a lazy import; existing journal routes are not rerouted. Unsupported products/modes and open/partial/multiple-exit CFD positions return unavailable. The standalone script imports no ORM, database session, application entry point or broker SDK. Result models are not new database tables.

## Phase 2B.3A financial input boundary

The [CFD validation milestone](phase-2b-3a.md) adds pure Pydantic contracts under `app/schemas/`. Exact financial types, timezone-aware evidence, frozen specification inputs and typed execution/cost/conversion references are separate from the existing crypto `TradeInput` and calculator. These modules import no database session, application entry point, HTTP client or broker SDK. The standalone validation script reads JSON only. No API route, database schema or historical account association changes in this milestone.

The new snapshot wrapper validates the existing `instrument-v1` canonical digest and retains an explicit snapshot ID. The ID must later be bound to its actual stored row by an authorized API/service; a supplied checksum alone cannot authenticate broker facts. Input validation is a separate boundary from persistence and financial calculation.

## Phase 2B persistence extension

See the [2B.2 design and rehearsal report](phase-2b-2.md) for the five additive tables, immutable specification snapshots, optional reviewed trade associations and transaction safeguards. The normal SQLite database is now at `0003` after explicit approval and [verification](migration-0003-verification.md); existing records/calculations were preserved and new tables remain empty. Current journal handlers also retain tested compatibility with `0002`. Multi-account screens, CFD calculations/imports and broker connections are not implemented in this persistence milestone.

## Phase 2 extension

The journal now has its own route, feature components, client forms, API bridge and backend router. Trades own exit executions via a cascading relationship. Version columns reject stale edits. Pure Decimal services calculate risk and outcomes; a separate evidence engine produces Trading IQ findings. See [the journal specification](trading-journal.md) for calculation policies and [Trading IQ](trading-iq.md) for evidence thresholds.

The Next.js bridge keeps browser requests on the frontend origin and permits local hostnames only. Backend mutation guards reject untrusted browser origins and limit request volume. These safeguards are not authentication; the public deployment gate remains. CSV import validates the batch before writing; screenshot processing checks raster content and strips metadata.

The sections below record the Phase 1 baseline and its evolution plan; the journal work described as planned there is now implemented as the Phase 2 extension above.

## Boundaries

The Next.js application shell provides navigation and branding. Dashboard features live under `src/features/dashboard`; chart code is loaded only when used. Server components fetch the FastAPI summary, validate it with Zod and pass a typed result to the client UI. No browser API key or cross-origin backend access is required.

The FastAPI service separates routing, schemas, settings, database sessions and models. A request-scoped SQLAlchemy session is closed after every request. Decimal database columns preserve account balances; JSON represents monetary amounts as strings. Alembic owns schema changes: application startup never silently creates tables.

## Phase 1 API

| Endpoint                | Purpose                                                     |
| ----------------------- | ----------------------------------------------------------- |
| `GET /api/v1/health`    | Process health, independent of database                     |
| `GET /api/v1/ready`     | Connectivity and initial schema readiness                   |
| `GET /api/v1/dashboard` | Empty summary, or recorded opening equity from USD accounts |

There is no account creation API yet. No trade model exists, so PnL, win rate and profit factor remain null. Recorded equity is the sum of stored opening balances only at this milestone. Multi-currency totals remain unavailable without an FX policy. Readiness and summary failures return safe 503 errors without database internals.

## Data honesty

Sample fixtures are frontend-only, deterministic, labelled and never persisted. Sample metrics are derived from those fixtures rather than separately hardcoded. Each fixture defines planned risk and an R outcome; dollar PnL is their product. These educational examples assume no separate fee/funding fields and a hypothetical USD 10,000 starting balance. They are not production journal calculations. Date buttons filter the available 30 sample observations; 90D explicitly reports the limited coverage. Custom dates and additional charts belong to Phase 2.

The market preview lists asset identities only; it has no prices, observations or saved watchlist. Learning cards and onboarding steps are previews and do not claim saved learning progress, XP or a streak.

## Planned database evolution

Phase 2 will add user/account ownership, strategies, trades and executions. An execution ledger will support partial exits. Decimal arithmetic will distinguish notional, margin, initial risk and actual realized loss; cash movements must be modelled before an equity curve can represent deposits and withdrawals correctly. SQLite is for local use; production will use PostgreSQL and authentication. Avoid SQLite-specific SQL in application logic.

Phase 3 adds provider contracts, HTTPX integration, bounded retries with backoff, upstream rate controls, cache TTLs, source timestamps and explicit unavailable states. Phase 4 adds curated lessons, question records and server-validated attempts; answer keys must never be returned with unanswered questions. Phase 5 adds progress and achievement events.

## Security boundary

This milestone is a local single-user foundation. Start Uvicorn on loopback only. `APP_ENV` must be `local`; other values fail startup until authentication is implemented. This guard is not authentication and must not be bypassed for a public API deployment. No private trading endpoints, uploads or execution permissions are implemented. Production requires authorization tests for user ownership and secure upload validation before those surfaces are enabled.

## Compatibility references

Implementation checked against official [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [Tailwind Next.js setup](https://tailwindcss.com/docs/installation/framework-guides/nextjs), [Motion React installation](https://motion.dev/docs/react-installation), [Recharts API](https://recharts.github.io/en-US/api/) and [FastAPI SQL database guidance](https://fastapi.tiangolo.com/tutorial/sql-databases/). Dependencies are pinned in `package-lock.json` and `services/api/requirements.lock`; review updates deliberately.
