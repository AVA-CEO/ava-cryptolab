# Architecture

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
