# Proposed 2B.4B — reviewed trade persistence and API integration

Status: **B1 and disposable-only B2 authorized; B3 not authorized**. No migration was included in 2B.4A. See the [B2 implementation and B3 review boundary](phase-2b-4b-b2.md) and [actual validation results](phase-2b-4b-b2-validation.md).

Historical design checkpoint, before the later B1/B2 approval: the owner accepted 2B.4A on [eight user-reported manual passes](phase-2b-4a-acceptance.md) and explicitly authorized **design review only** for 2B.4B. The detailed proposal is now in [CFD persistence design review](phase-2b-4b-design-review.md), covering ten new CFD-only tables, a proposed additive 0004, revision/correction policy, exact Decimal storage, retries, concurrency, reproducibility and disposable rehearsal gates. Existing 0003 account/snapshot tables are reused but cannot store the CFD ledger by themselves. No implementation or migration is authorized by either document.

## What we will build

Store reviewed CFD trades separately from legacy crypto rows. A trade links to an existing account ID and immutable specification snapshot ID, with exact entry/exits, original stop/risk inputs, signed costs, dated conversion evidence and optional broker reconciliation values. Python loads trusted identities by ID and calls the tested partial-CFD engine; browser calculations are never the authority.

Think of this as adding a new filing cabinet for CFD records, with labels pointing to an account and a specific dated rule card. It avoids squeezing lots and swaps into crypto quantity/funding columns.

## Review before any schema changes

First inspect current contracts and propose exact tables and constraints: CFD positions, executions and adjustments, conversion evidence, reconciliation evidence and future import provenance. Review whether immutable versioned calculation inputs/results should be stored as canonical evidence alongside normalized executions. Record units, Decimal precision/serialization, required identities, currency/timestamp coverage, cost-recognition policy and update concurrency. Preserve calculated and broker-reported amounts separately.

Any necessary additive Alembic revision requires explicit approval before implementation. Rehearse on disposable legacy databases with verified backups; compare IDs, counts, screenshots, calculations and relationships, test constraint failures/rollback and safe reversal. The normal database and both preserved backups remain untouched. A later normal-database migration needs its own backup checkpoint and approval.

## Proposed implementation sequence

1. Review a persistence contract and schema decision document. Resolve original-risk immutability, correction history and stable execution/adjustment IDs.
2. After schema approval, implement models and migration rehearsals. Reuse existing accounts/snapshot identities; no automatic historical assignments.
3. Add a separate CFD validation/preview API, then explicit reviewed save/read/update/delete operations. Use transactions and optimistic concurrency to prevent stale edits. Define deletion and evidence-retention policy before enabling destructive operations.
4. Add tests comparing persisted-and-reloaded outputs with the pure engine: EURUSD 8 + 18 = 26 USD, costs −4 once, net 22 and 1.10R; JPY conversion; metals; missing evidence; over-closing; incompatible accounts; immutable snapshots; crypto regressions.

Likely files: new CFD models/schemas/services/router, an approved migration, disposable persistence/API/rehearsal tests and architecture/learning documentation. Keep the existing journal UI unchanged; forms follow in 2B.4C. Local practice isolation continues until normal-database and authentication policies are separately approved.

## How you will verify it

Use a synthetic request to preview, save and reload a CFD position in a disposable database. Confirm the same snapshot ID and exact Decimal results survive reload. Attempt an invalid exit or incompatible account and confirm no partial rows remain. Learn foreign keys, atomic transactions, durable storage, financial evidence and concurrency. No broker connection, automated trading, public deployment or real-statement reconciliation is included.
