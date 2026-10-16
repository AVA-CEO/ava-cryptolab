# Proposed Milestone 2B.4 — account workflows and CFD journal integration

Status: **proposal for owner review; not implemented or authorized by 2B.3C**. Reuse the existing journal and tested CFD calculators. Preserve legacy records, IDs, screenshots, crypto calculations and the purple interface. Do not automatically assign historical trades to new accounts/instruments.

## 2B.4A — accounts and instrument selection

Build local account creation/list/detail workflows using existing `journal_accounts`, instruments and immutable snapshot tables. Each account explicitly names broker/platform/server and reporting/settlement currencies. No keys, passwords or trading permissions are requested. Existing historical trades remain visibly unassigned until an owner-reviewed policy exists.

The backend must load the actual stored account/snapshot by ID and verify compatibility. It must not trust browser-supplied contract sizes, currencies or source hashes as authority. A new broker specification creates a new snapshot; it never rewrites an old one. Account balance/cash-flow history needs its own reviewed model before showing consolidated equity; account labels alone do not create a known balance.

Likely files: account/instrument API routers and schemas, reviewed reuse of `services/multi_asset.py`, frontend account/specification features and disposable API tests. Teach primary/foreign keys, IDs versus trusted data, immutable versions and transaction boundaries. Verify two separate accounts with explicit currencies and reject cross-account/snapshot mismatches.

## 2B.4B — review CFD persistence before writing a migration

The legacy `trades`/`trade_exits` tables encode crypto quantity/funding semantics. Do not force CFD lots, swaps and signed costs into those columns. Propose dedicated CFD position/execution/adjustment persistence linked to the existing account/instrument snapshot identities, with original-risk inputs and future import provenance.

A new additive migration may be necessary. First present exact tables, constraints, preservation policy and SQL/Alembic plan for approval. Rehearse on backed-up disposable legacy databases; verify IDs, counts, calculations, screenshot references, rollback and safe reversal. The normal journal and both current backups stay untouched. Applying any migration to the normal database requires separate explicit approval and a newly validated backup checkpoint.

Likely files after approval: dedicated SQLAlchemy models, Alembic revision, persistence services and migration/reconciliation tests. Teach durable storage versus pure calculation, relationships, transactions, revision control and recovery. No migration is implemented by this proposal.

## 2B.4C — manual forex/CFD forms and server calculation preview

Add a market/product selector that preserves the existing crypto form path. The CFD path selects a real account and dated instrument specification, then collects entry lots/price/time, original stop, exits and sourced signed adjustments. Currency conversion fields must be explicit and explain missing coverage. Financial values remain decimal strings in TypeScript; Python validates and calculates authoritative results.

Preview original/exited/remaining lots, realized gross/net/R, currency labels, recognized costs and unavailable unrealized values. Distinguish entry fees recognized in full from any future analytical allocation view. Keep purple brand styling, green gains/success and red losses, responsive layout and accessible validation. Screenshot reuse needs explicit record ownership/lifecycle tests before enabling attachment to CFD records.

Likely files: separate CFD feature/forms, discriminated TypeScript contracts, backend preview/CRUD endpoints and API bridge. Teach React form state, discriminated unions, Zod versus server validation, Decimal serialization and optimistic concurrency. Do not replace working crypto components or expose a broker API key.

## 2B.4D — integration acceptance and documentation

Test create/read/edit/delete, partial exits through full close, invalid lots/times, missing FX, stale edits, account separation and immutable snapshot binding. Repeat the owner's 8 + 18 = 26 USD example through real application screens using disposable databases. Verify costs total −4 once and net/R agree with the pure engine. Preserve all backend, frontend, build and browser checks and test screenshots only where supported.

Provide exact run commands and a beginner manual checklist, update the learning journal and create meaningful local commits. Request separate permission for pushes and any normal-database migration. Account-level and combined analytics must disclose conversion coverage and require reviewed balance/cash-flow policies; do not silently mix currencies or invent equity. Public multiuser deployment still requires authentication/ownership protections. No deployment is included.

Broker statement import, real-statement reconciliation and read-only synchronization retain their separate evidence/architecture gates. No live broker connection, automated order, amendment, cancellation, transfer or withdrawal is authorized.
