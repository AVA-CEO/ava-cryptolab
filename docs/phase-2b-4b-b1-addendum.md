# 2B.4B B1 addendum — final schema proposal for review

**Conditional direction accepted; B1 sign-off pending. Implementation NOT authorized.** This addendum takes precedence over the earlier [design review](phase-2b-4b-design-review.md) on the seven questions below. Rules/tests are proposed, not implemented or newly tested. No database, practice data or backup is accessed.

## 1. Compatibility at both boundaries

Add immutable `platform VARCHAR(10)`, `server VARCHAR(100)`, `venue VARCHAR(100)` and `product VARCHAR(32)` columns to the proposed `cfd_positions` root. All four are NOT NULL. Keep its existing proposed composite account/snapshot FKs. The root copies identities loaded by the server, never trusts browser assertions.

| Identity           | Application boundary                                                                                                                                   | Database boundary proposed for 0004                                                                                                                                                                               |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Account/instrument | Load actual account, snapshot and instrument; validate snapshot hash and frozen contract.                                                              | Existing 0003 composite keys supply scoped FKs from the new root. Missing parents are rejected.                                                                                                                   |
| Broker/currency    | Account, snapshot and instrument brokers/settlement currencies must all match. Reporting currency stays separately frozen; profit currency may differ. | Composite FKs protect broker/settlement; root insert guard also verifies the copied identities and snapshot JSON against its instrument.                                                                          |
| Server/venue       | Require an explicit account server, even for manual CFD persistence, and exact equality with snapshot/instrument venue. No fallback from broker name.  | NOT NULL/nonblank checks plus `server = venue`; insert guard joins account/snapshot/instrument and requires `account.server = root.server = instrument.venue = snapshot.specification.venue`.                     |
| Platform/product   | Account platform must be `manual` or `mt5`; snapshot product must be `cfd`. Use the existing engine's mode/category allowlist.                         | CHECK platform in `manual/mt5`, CHECK product `cfd`; insert guard checks those values against account and instrument/snapshot, not merely root labels. Decimal/mode validation still belongs to versioned Python. |

**Design tightening:** manual accounts with unknown server remain valid accounts, but are ineligible for CFD persistence until a reviewed identity has an explicit server/venue. No identity is filled automatically. “Bybit” alone proves no product compatibility.

An insert check alone is insufficient: someone could change a referenced parent afterward. Proposed new guards on `journal_accounts` block changes to broker, platform, server, reporting/settlement currencies and broker reference while any CFD root references it. Guards on referenced `instruments` block broker, venue, symbol, product, category and settlement changes. An account display-name change can remain a future metadata operation; historical calculation uses its frozen contract. Existing snapshot guards remain unchanged. SQL NULL/unknown comparisons must fail closed, not accidentally pass an equality test.

Parent-check races must also be covered: PostgreSQL root insertion locks account then instrument rows `FOR SHARE`, and guarded identity updates validate after locking under READ COMMITTED with fresh trigger queries. Guarded writes at unsupported isolation levels are rejected until separately proven safe. SQLite serializes writers. B2 must prove concurrent root-insert versus parent-update cannot commit a mismatched pair; a sequential trigger test alone is insufficient.

**Migration scope change:** 0004 would also add these CFD-reference guards to two existing tables, without changing their columns/business rows or 0003/v1 guards. New trigger removal belongs in the B2 downgrade review.

**Required mismatch test:** create synthetic account `A`, broker `B`, platform MT5, server `S1`, settlement USD; create a valid CFD snapshot for broker `B`, venue `S2`, settlement USD. App validation must reject it. Direct SQL inserting a root must also fail, even if the caller lies with `root.server = root.venue = S1`. Assert no root/revision/head/receipt remains. Repeat with all copied fields set to S2 to prove the account join is checked. Then create a valid S1 relationship and attempt to change the referenced account server or instrument venue to S2: both must fail, on each database backend.

## 2. Native realized R versus reporting R

Net realized R is **net realized PnL / positive original planned risk in the same currency**. A reporting FX gap does not automatically invalidate native R. A missing original stop, unavailable native net amount, unsupported mode or invalid denominator does. Partial R remains cumulative net divided by original whole-position risk; it is not a completed-trade outcome.

Synthetic USDJPY example: buy 0.10 lots, contract 100000, entry 150, exit 151, original stop 149.50. Gross = 10000 JPY; original risk = 5000 JPY. These are teaching inputs, not broker specifications.

| Costs and policy                                                   | Native JPY result                                                                                                 | USD reporting result                                                                                        |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| No costs; USD account, `native_only`, no JPY/USD rate              | Net 10000 JPY; **2.00R available**.                                                                               | Net and R unavailable; no rate is invented.                                                                 |
| Commission −100 JPY; same setup                                    | Net 9900 JPY; **1.98R available**.                                                                                | Still unavailable.                                                                                          |
| Commission −1 USD; USD account, `native_only`                      | Gross/risk JPY remain known; native net/R unavailable because the cost cannot be added to JPY.                    | Cross-currency gross/net/R unavailable.                                                                     |
| Commission −1 USD; USD account, complete `explicit_rates` evidence | Native net/R **still unavailable** in the current engine: reporting rates do not convert USD costs back into JPY. | Net/R can be calculated with exit-time profit FX and entry-time risk FX. Those rates need not be identical. |

When reporting currency **is JPY**, complete explicit USD→JPY cost evidence can also make native net/R available, because native and reporting basis coincide. Do not silently invert a reporting rate. The current engine does not provide arbitrary cost→native conversion for different native/reporting currencies; that would require a separate accounting-contract review. Missing required `explicit_rates` evidence rejects the request; it does not silently switch to `native_only` or manufacture partial totals. This section describes existing source behavior, not a new calculation feature.

## 3. Storage growth and operational consequences

**Planning estimate, not a database benchmark.** Assume five full revisions per position: create, partial exit, final exit, cost correction and notes correction. Typical complete ledger: one entry, two exits, four costs, two FX observations and one reported value. Budget 6 KiB fixed root/head/event identity data plus **52 KiB per revision**: about 8 KiB normalized rows/metadata, 8 KiB input, 12 KiB result and 24 KiB successful response receipt. Add 35% for indexes/page overhead. Exclude attachments, release artifacts, WAL, backup copies and compression savings.

| Positions | Five revisions: logical data | Five revisions: planning budget | Fifteen revisions: planning budget |
| --------- | ---------------------------- | ------------------------------- | ---------------------------------- |
| 100       | 26 MiB                       | 35 MiB                          | 104 MiB                            |
| 1,000     | 260 MiB                      | 351 MiB                         | 1.01 GiB                           |
| 10,000    | 2.54 GiB                     | 3.42 GiB                        | 10.12 GiB                          |

Formula: `positions × (6 + revisions × 52) KiB`; budget multiplies by 1.35. Real documents, fragmentation and index widths can differ substantially. Near-maximum ledgers/documents can far exceed these averages. In B2, measure actual synthetic 100/1000/10000-position datasets, serialized evidence/receipt sizes and database/index bytes on both engines before treating these as capacity figures.

Index IDs/FKs, position/revision number and request keys, not whole JSON or every financial value. Index `(account_id, created_at, id)` supports keyset pagination: fetch 50 summaries, then one revision on demand. Paginate history too.

Revisions/receipts duplicate evidence deliberately; archive does not reclaim space. No automatic pruning is proposed. Three uncompressed backups of the 3.42 GiB baseline need another 10.3 GiB, plus WAL/headroom. Use consistent, database-aware backups, separately archive release artifacts and rehearse restoration. A possible backup schedule—7 daily / 4 weekly / 12 monthly generations—must be budgeted and approved; it does not authorize pruning existing backups/evidence. No maintenance or benchmark runs now.

## 4. Versioned release artifact and replay policy

Propose an **offline OCI container image**—a sealed toolbox containing the calculator and its runtime—plus source/dependency wheels and golden synthetic fixtures. Label `cfd-position-v1/r1` is illustrative; the SHA-256 image digest identifies the exact release. Its signed manifest records source/module hashes, Python patch, OS/CPU, dependencies, contracts/canonicalizer/policy versions and Decimal context/rounding. Verify the signature against a pinned maintainer public key; a hash alone does not establish approval.

Keep referenced releases in a private archive with verified backup/restore; never prune one while retained evidence depends on it. Git contains source/manifests, not private trading inputs or runtime archives.

Accepted saves/replay use the allowlisted release runtime: no network, read-only runtime, temporary input/output, no credentials and bounded resources. No arbitrary image URL or uploaded code is executable. **B1 trade-off:** a local container runtime becomes a CFD dependency. Nothing is installed now; crypto stays unchanged. If unacceptable, specify a replacement runtime bundle before B1; a lockfile alone is insufficient.

For an engine upgrade, release a new digest, run old/new synthetic golden comparisons, review every financial difference and keep the old artifact. Newly accepted calculations identify the new release; historical revision replay still selects its original digest. Rebuild input from stored rows/anchors, compare its canonical hash, run that release and compare the complete canonical result hash; audit wall-clock metadata stays outside that result hash. A mismatch is an integrity/reproducibility failure and never overwrites history. If the old runtime is missing or unsupported, display preserved result/provenance with **`runtime_unavailable`**, not “replayed successfully”; restore the approved artifact before verified replay. Stored-hash integrity and computational replay are different checks.

## 5. Ten-table necessity and smaller option

**Ten is not an absolute minimum.** The full lifecycle benefits from the separation: merging heads into mutable roots complicates guards; the registry separates stable event identities from revision copies.

| Full ten-table proposal                                                            | Smaller historical create/read-only alternative                                                                                                                                              |
| ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Positions, revisions, executions, adjustments, conversions, calculations, requests | Retain these **seven** tables, with exactly one immutable revision per position. Keep idempotency and calculation evidence.                                                                  |
| `cfd_position_heads`                                                               | Defer; derive the sole accepted revision. No mutable pointer, concurrent edit API or lifecycle transitions.                                                                                  |
| `cfd_event_keys`                                                                   | Defer; use UNIQUE `(account_id, execution_id)` / `(account_id, adjustment_id)` on sole-revision rows. Conversion IDs remain revision-local. No global registry promise for later amendments. |
| `cfd_broker_evidence`                                                              | Defer broker-value submission/comparison persistence explicitly; no real-statement reconciliation claim.                                                                                     |

The seven-table option stores completed historical positions with all exits supplied together, without ongoing updates, amendments, archive/void/replacement or broker-evidence submission. Later revisions require a reviewed migration to populate heads/registry and replace sole-revision uniqueness. **Recommend ten tables for B1**, unless the owner explicitly selects the smaller scope.

Smaller-schema changes: UNIQUE `cfd_revisions(position_id)`, no registry FKs/columns, reads require the sealed revision/calculation, and nonempty broker evidence is rejected. Its test subset excludes unavailable lifecycle/edit features.

## 6. Exact transaction and concurrency acceptance matrix

Run each schedule with independent real connections on **both** disposable SQLite and PostgreSQL, controlled barriers rather than sleeps. SQLite's second `BEGIN IMMEDIATE` waits for the first writer; PostgreSQL tests overlapping reads/writes. No shared in-memory test session can prove these races. Let baseline current head be version `n`, with exact row-count/hash inventory captured before each schedule.

| Schedule                                                                    | Required response and committed-state assertions                                                                                                                                                                                               |
| --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Same account/key/normalized create payload, sequential and concurrent       | One root, revision 1, one head and one receipt. Both callers receive the same saved IDs/body/status; replay identified in a response header. No repeated cost/key rows.                                                                        |
| Same account/key, different payload/operation/resource                      | One command may win; the other is 409. No mixed graph or second receipt. Same key in a different account is independently scoped, not cross-account replay.                                                                                    |
| Different keys, two edits with If-Match `n`                                 | Exactly one new revision/head `n+1` and one successful receipt. Loser is 412; its staged children and registry keys roll back. A revision-number unique race must be classified by receipt/head re-read, not a generic success or blind retry. |
| Missing If-Match / forced SQLite lock timeout                               | 428 with no writes / bounded 503 with no accepted receipt. Retry the same key after the winner releases the lock; never bypass version checks.                                                                                                 |
| Commit succeeds but reply is lost                                           | Same-key retry returns the original receipt, even if a different command has advanced the head to `n+2`. It must not create `n+3`. If commit outcome is uncertain, query the receipt on a fresh connection before deciding whether to retry.   |
| Failure after child insert, after sealing, after head CAS, or before commit | Roll back **all** new roots/revisions/children/event keys/receipts and restore the prior pointer; compare exact pre-attempt inventory. Corrected same-key retry may succeed because no failed receipt was committed.                           |
| Successful compound replacement and retry                                   | In one transaction: predecessor becomes void at `n+1`, replacement has new ID/active revision 1, and one receipt records both revisions. Retry returns those same IDs without another replacement.                                             |
| Compound failure / two concurrent replacements or archive-versus-replace    | Failure at any staged point leaves old head `n`, no replacement and no receipt. Racing operations yield one success and one 412, never two active replacements or a voided predecessor without its successful replacement.                     |

Every mutation checks a committed matching receipt before stale-version rejection. A matching key/different command is always 409. After a unique/CAS race, rollback first, then re-read receipt/head. Request hashes include schema-normalized exact values, account, operation, resource/draft ID and expected version. Idempotency receipts are retained; new keys/new IDs can still disguise an economic duplicate. B2 tests SQL/transaction primitives and constraints; B3 separately implements and tests the API status/header behavior described here.

## 7. Dialect-specific guards and independent validation

| Invariant                                                           | SQLite implementation proposed                                                                                                                                      | PostgreSQL implementation proposed                                                              |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Scoped PK/FK/unique/enum constraints                                | Normal constraints; verify `foreign_keys=ON` on every connection.                                                                                                   | Normal constraints and non-owner application role.                                              |
| Root compatibility and referenced-parent drift                      | BEFORE INSERT root and BEFORE UPDATE account/instrument triggers using joins and `json_extract`; reject NULL/mismatch.                                              | Separate PL/pgSQL trigger functions using joins and JSON field extraction; null-safe rejection. |
| Append-only roots/events/evidence/receipts; head cannot be replaced | UPDATE/DELETE denial plus BEFORE INSERT collision guards covering PK and unique-key replacements. Test `INSERT OR REPLACE` with recursive triggers both off and on. | UPDATE/DELETE denial, reject conflicting UPSERT updates, and statement-level TRUNCATE denial.   |
| Revision seal, child insertion window and head advance              | Narrow seal transition trigger; child insert checks unsealed parent; head guards require calculation/parent/version and block replacement bypass.                   | Equivalent row-trigger functions; explicit TRUNCATE guards also protect histories and heads.    |

Cross-row Decimal totals, canonical hashes and financial availability remain Python invariants, not claims about generic SQL CHECKs. SQLite REPLACE has special delete-trigger behavior, so UPDATE/DELETE guards alone are insufficient. [SQLite conflict rules](https://www.sqlite.org/lang_conflict.html). PostgreSQL supports different row/statement trigger events, including TRUNCATE. [PostgreSQL trigger reference](https://www.postgresql.org/docs/current/sql-createtrigger.html).

B2 must run real 0003→0004 upgrades and raw-SQL attacks on each disposable engine, including parent mutation, server-only mismatch, replace/upsert, late child insert, seal/head bypass, truncate where supported, rollback injection, empty-only downgrade and restore. Assert equivalent accepted/rejected cases and record engine/driver versions and pragmas/roles. SQL compilation or SQLite success is not PostgreSQL validation. Parent-update guards add new trigger objects only; migration 0003/v1 snapshot guards and all existing data remain untouched. Schema-owner DDL or direct file control can bypass application protections; these guards are not a replacement for access control.

## B1 final proposal and approval boundary

Submit the **ten-table schema in design-review §4**, amended by §1 scope columns/parent guards. Retain its PK/FK/unique constraints, immutable revisions/risk, Decimal TEXT/UTC, signed incurred-once costs, explicit FX/unavailable values, separate broker evidence and retry receipts. Adopt the versioned release/replay policy; no hard purge or silent upgrades. Seven tables remains an explicit alternative, not assumed acceptance.

- **B1:** final schema, accounting, operational artifact dependency and full-versus-smaller scope sign-off. Conditional architectural acceptance is not B1 completion.
- **B2:** separate authorization to implement proposed 0004/models and rehearse on disposable databases **only**, after B1.
- **B3:** separate authorization for CFD persistence APIs **after** successful migration rehearsals.

None of these approvals authorizes normal-journal migration, altering old trades/backups/practice data, deployment, broker integration or a documentation push. No such action is taken by this addendum.
