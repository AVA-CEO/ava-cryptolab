# AVA CryptoLab learning journal

This journal grows at each milestone. Each entry explains what changed, the concept behind it and a safe way to explore it. It contains no personal trades, account balances, private backup manifests or credentials.

## Phase 2 acceptance — checking behavior yourself

You reported nine manual journal scenarios passed in an isolated practice environment. A manual acceptance test is you using the application and checking what happens. An automated test is code checking behavior repeatedly. They complement each other; one must not be presented as the other.

Think of a bicycle: a mechanic can test its parts, but a rider still checks how it feels to ride. The [acceptance report](phase-2-acceptance.md) records your observations separately from automated checks.

## 2B.1 — contracts and financial units

A data contract is a form with rules. A crypto trade measured in coin quantity and a CFD measured in lots need different fields. Pydantic validates submitted values in Python; TypeScript helps catch developer mistakes before the application runs. Neither a symbol nor a label proves the correct broker contract rules.

A specification snapshot is a dated photograph of the rules used for a trade. A later broker update should create a new photograph, not repaint the old one. See the [contract milestone](phase-2b-1.md).

## 2B.2 — tables, relationships and safe migrations

### Tables and relationships

A database table resembles a spreadsheet: columns describe fields, and rows describe records. Our `trades` table stores trades; `trade_exits` stores partial exits. One trade can have several exits, just as one shopping receipt can contain several items.

A schema is the blueprint describing these tables, their fields and the rules between them. SQLAlchemy models describe that blueprint in Python. The database must also have the matching physical tables; changing a Python model alone does not update the database.

### Primary keys and foreign keys

A primary key is a permanent ID, like a library book's inventory number. Names and prices may change, but the ID identifies the same record.

A foreign key is a checked reference to another record. `trade_exits.trade_id` points to `trades.id`. Like a checkout slip that must name a real library book, an exit cannot reference a nonexistent parent when foreign-key enforcement is active.

Composite foreign keys check several facts together. Our new context links check broker and settlement currency alongside account/snapshot IDs. This helps prevent connecting records that individually exist but do not belong together.

### Migrations

A migration is a numbered renovation plan for the database. Alembic records which renovation has been installed in `alembic_version`. Revision `0003` adds multi-asset tables; it does not guess which account owns an old trade.

Think of adding an extension to a house. We can build and rehearse the plan without demolishing the existing rooms. The optional `trade_contexts` table lets old trades remain unassigned until their account and instrument are explicitly reviewed.

See the [2B.2 report](phase-2b-2.md) for the actual tables and safeguards. Its 99 backend passes include the original tests plus migration/persistence cases. SQLite runtime checks passed; PostgreSQL SQL generation is checked, but PostgreSQL runtime migration is not yet verified.

### Backups and restoration

A backup is a preserved copy. Restoration means recovering a usable database from that copy. A spare house key is only useful if it actually opens the door; likewise, a backup should be restored and checked, not merely assumed good because the file exists.

SQLite's backup API makes a consistent database copy. Screenshots live in separate files, so they need a separate copy and manifest too. A checksum is a file fingerprint that helps detect byte changes; it does not by itself prove the database has the right records. We also compare IDs, exits, screenshot references, calculations and analytics.

At the backup checkpoint, the approved normal-journal backup was restored into an isolated location and checked without applying a migration. Its report stays under the ignored `private/backups/` directory. The normal database stayed at its old revision until the later explicit migration approval described below. Windows folder permissions protect the backup from other ordinary accounts; they are not encryption.

### Transactions and rollback

A transaction groups changes so they succeed together or are cancelled together. Think of a bank transfer: removing money from one account without adding it to the other is an incomplete operation.

Rollback cancels an uncommitted transaction. Backup restoration recovers an earlier saved copy and can replace already committed changes. They solve different problems. Our SQLite migration runner explicitly begins a transaction so table-changing statements are included, and tests deliberately interrupt migrations to check rollback.

A downgrade is another migration running in reverse; it is not automatically harmless. Revision `0003` refuses to remove its tables if they contain data. This prevents a convenient command from silently discarding new account or specification history.

### SQLite and PostgreSQL

SQLite is like a notebook stored as a file: convenient for local development and portable backups. PostgreSQL is like a shared records office with a dedicated server: useful when many users and services need coordinated access.

Both can enforce relationships, but SQLite foreign keys must be enabled on each connection. SQLite's Python driver also needs care around transactions for schema changes. PostgreSQL has native transactional schema changes. Our existing money storage uses exact decimal text in SQLite and NUMERIC in PostgreSQL; snapshot JSON keeps decimal amounts as strings in both. We still need actual PostgreSQL runtime tests before claiming production compatibility is verified.

### One safe practical exercise

From the repository root, run:

```powershell
.\.venv\Scripts\python.exe services/api/scripts/rehearse_multi_asset.py
```

Find these results in its output:

1. Four **synthetic** trades and three exits are preserved.
2. All five new tables start with zero rows: no historical facts were invented.
3. The migration metadata check and empty-table downgrade/re-upgrade pass.

Explain to yourself why an empty new table can be a correct result. The runner creates, backs up and removes only temporary teaching data. It does not migrate or open your normal journal for its target. Do not substitute the normal journal path or run an ordinary upgrade as part of this exercise.

## GitHub and backup verification checkpoint

A Git push uploads committed source history, not ignored databases. Commits `9cacad7` and `70d5203` were pushed with explicit approval, and both remote Actions jobs passed. The repository stayed private. Private backups, statements, reports and credentials remain ignored; never use `git add -f` to include them.

The backup verifier was first tested on synthetic data. Its initial comparison passed but Windows cleanup found an open SQLite connection. Explicitly closing that connection fixed the preflight. Lesson: Python's SQLite transaction context manager does not close the connection automatically; resource cleanup is separate from committing or rolling back.

## Approved normal migration — adding rooms without moving the furniture

After final owner approval, the normal SQLite database moved from `0002` to `0003`. Think of adding labelled empty filing cabinets beside existing records. We checked that the old records, IDs, relationships, calculations and screenshot references stayed the same. Empty account/instrument tables are deliberate: the application must not guess missing ownership or contract rules.

Before changing anything, we rechecked the original backup, made and verified another copy outside the project, confirmed there were no application writers, then acquired a database write lock. A transaction covered the schema change and preservation checks. We reopened the committed database read-only afterward to verify the result independently.

The local API and frontend were then started again. GET-only requests read journal records and analytics successfully without writing test trades into the real journal. An automated regression test suite still belongs on disposable databases. The complete [migration verification and read-only table exercise](migration-0003-verification.md) shows how to inspect revision `0003` and the new tables without running another migration.

Lesson: a whole database file's fingerprint should change when its schema changes. The preservation question is whether the old record/table/calculation fingerprints stayed the same—not whether the entire modified file is byte-for-byte identical.

## Next: 2B.3 calculation engines

The owner's updated priority puts forex/CFD calculations before account-management screens. The [2B.3 design](phase-2b-3-plan.md) explains formulas, units, files and tests. A calculation engine can be a pure Python function: given explicit inputs, return an answer without network access or database writes. The normal migration gate is resolved; this checkpoint presents the plan and implements no calculator.

Documentation references: [Python SQLite backup and connection handling](https://docs.python.org/3/library/sqlite3.html), [SQLite backup API](https://sqlite.org/backup.html). The practical exercise is a synthetic rehearsal, not broker-statement reconciliation.
