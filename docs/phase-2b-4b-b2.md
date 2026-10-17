# B2 — CFD database foundations

B1's ten-table design is implemented as an additive `0004` rehearsal migration. B2 creates no CFD endpoints or journal forms. The existing crypto journal stays on its approved schema and calculator. See the [validation report](phase-2b-4b-b2-validation.md) for actual results, corrected failures and remaining limits.

## What the tables do

Think of a position as a folder, revisions as numbered pages, and the head as a bookmark pointing to the currently accepted page.

| Table                 | Purpose                                                                       |
| --------------------- | ----------------------------------------------------------------------------- |
| `cfd_positions`       | Original entry, account/snapshot identity and frozen risk basis               |
| `cfd_revisions`       | Numbered revisions, reasons, lifecycle, accounting policy and seal            |
| `cfd_event_keys`      | Account-scoped stable identities for execution and evidence records           |
| `cfd_conversions`     | Exact dated currency-conversion evidence                                      |
| `cfd_executions`      | Entry and ordered partial exits for each revision                             |
| `cfd_adjustments`     | Signed commissions, swaps and other costs                                     |
| `cfd_broker_evidence` | Separately reported broker observations, never substituted for calculated PnL |
| `cfd_calculations`    | Canonical inputs/results, hashes and versioned recipe/manifest identifiers    |
| `cfd_position_heads`  | Current revision and version number for concurrency checks                    |
| `cfd_requests`        | Account-scoped idempotency receipts and original responses                    |

All ten use the approved [B1 design](phase-2b-4b-design-review.md) and [addendum](phase-2b-4b-b1-addendum.md). Existing 0003 accounts, instruments, snapshots and import provenance are reused. Parent identity guards reject server/venue drift only once a CFD root references the parent; old account records are not rewritten. No legacy trade is assigned to an account or instrument.

The schema remains ten tables. No replacement for 0003 or extra migration was introduced. String lengths, named checks and operational trigger definitions are concrete implementations of the reviewed design. Financial meaning is validated in the approved Python contracts, not inferred through SQL arithmetic. B3 must load trusted identities, verify hashes and preserve the original risk/conversion policy before it saves anything.

## Important files

| File                                                  | Responsibility                                                                     |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `services/api/app/database/cfd_schema_v1.py`          | Frozen table/constraint/index definitions shared by the models and 0004            |
| `services/api/app/database/cfd_guards_v1.py`          | Versioned immutability, identity, sealing, head and replacement-collision triggers |
| `services/api/app/database/cfd_target.py`             | Disposable path checks; no connection is opened by the helper                      |
| `services/api/app/models/cfd.py`                      | Ten SQLAlchemy model mappings and test metadata guard installation                 |
| `services/api/migrations/versions/0004_cfd_ledger.py` | Add tables/guards; refuse downgrade when any CFD evidence exists                   |
| `services/api/migrations/env.py`                      | Preconnection target validation and explicit transactional SQLite DDL              |
| `services/api/app/database/rehearsal.py`              | Synthetic legacy migration, integrity and preservation rehearsal                   |
| `services/api/tests/cfd_ledger_helpers.py`            | Synthetic SQL staging/reload driver; not a production save service                 |
| `services/api/tests/test_cfd_ledger.py`               | Migration, evidence, rollback, currency replay and concurrency tests               |
| `services/api/tests/test_cfd_target.py`               | Permitted temporary targets and rejected normal targets without opening them       |

Migration 0004 imports the frozen schema/guard modules rather than evolving application metadata. Future schema changes require a new version; do not silently edit the accepted v1 definitions after this migration is released.

## Safe verification

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest services/api/tests/test_cfd_ledger.py services/api/tests/test_cfd_target.py -q
.\.venv\Scripts\python.exe services/api/scripts/rehearse_multi_asset.py
```

These commands select their own disposable targets. No journal path or broker credentials are needed. The rehearsal creates four synthetic legacy trades, three exits and a tiny screenshot; its old IDs, calculations and relationships must survive upgrade and safe reversal. Separate tests restore the synthetic backup and attack constraints using direct SQL. Application startup does not apply migrations.

The CLI guard blocks normal paths for inspection as well as mutation. Temporary Accounts provisioning is allowed only at the launcher's pinned 0003; it is not permission to migrate an existing practice environment to 0004. PostgreSQL targets remain blocked until real isolated tests are available.

## Financial evidence and runtime limits

Decimal values are serialized as strings, timestamps use UTC microseconds, and currency labels remain explicit. The original risk anchor cannot be replaced by a new revision's calculation hash. Synthetic test envelopes carry a test-only host manifest; they are not signed release artifacts or proof of historical container replay. A broker evidence row marked synthetic is not a real broker statement.

No Docker or other runtime is installed, and existing journal development does not depend on one. Before a container replay service becomes mandatory, a separate review must document exact supported Windows/WSL versions, virtualization requirements, disk/memory/CPU budgets, installation/removal steps, isolation and impact on the journal. Installation still requires explicit approval. Historical runtime unavailability must produce an honest unavailable replay state rather than recalculate with today's engine.

## B3 proposal — review only

1. Review a disposable-only persistence service contract: trusted account/snapshot loading; full Pydantic validation; fixed original risk and conversion policy; explicit schema/engine/canonicalizer versions.
2. Implement preview and transactional create/read first, only after separate authorization. Retain exact native/reporting values and independent broker evidence; verify normalized reload against accepted hashes before returning data.
3. Review amendments/lifecycle separately: immutable history, reason/changed IDs, conditional head update, terminal void and atomic replacement. No hard-delete endpoint.
4. Implement the reviewed retry protocol: scoped normalized command hashes, same-key receipt replay before version checks, payload conflicts, stale version rejection, bounded locks and rollback. Database fixture behavior is not an implemented HTTP contract.
5. Test all API status/header rules, authorization/local access boundaries, tamper rejection, unavailable runtime behavior and fresh disposable legacy regressions. No new public access or normal-journal target.

B3 APIs, CFD frontend forms, normal-journal migration, deployment and broker integration remain unauthorized. No push is included in B2 completion.
