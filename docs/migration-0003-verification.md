# Approved normal SQLite migration 0003 — verification

Status: **applied and verified on 2026-10-16 after explicit owner approval**. This records an operational migration, not new CFD feature implementation. No application source or historical trade values were changed. No deployment or Git push was performed in this checkpoint; local documentation commit `cbe1f58` remains unpushed.

## Preconditions and backup safety

- Resolved backend settings to the approved normal development database, `services/api/ava.db`, and upload directory, `services/api/uploads`. Confirmed this was not a temporary `ava-browser-*` practice database.
- Inspected listeners and matching processes. No application API/frontend writer was running; the remaining matching Python processes were VS Code formatter services, which were left alone. The migration also acquired a database write lock.
- Rechecked the original private backup's SHA-256, SQLite integrity, foreign keys, rows, IDs, screenshot manifest and financial/analytics fingerprints. Confirmed the source had not changed since that backup, so a fresh replacement backup was unnecessary.
- Preserved the original verified backup. Created an additional restricted copy outside the project under the owner's Documents backup directory, then independently verified its checksum, integrity and contents. Both copies remain unchanged at revision `0002`.
- Re-ran all **99 backend tests** and the backed-up synthetic migration rehearsal against disposable databases. Also exercised the exact migration/verification runner on synthetic data before applying it to the normal target.

Actual source records, identifiers, checksums, backup locations, runtime PIDs/logs and detailed verification JSON are retained only in the ignored private audit, with a second backup outside the repository. No real trade data or private manifests are included in this document.

## Execution and preservation

Applied the explicit Alembic target `0003`, not a moving `head` target. Revision `0002` was verified immediately before execution under the write lock. The transaction created five tables and their indexes/guards, then compared preserved state before commit. It did not drop, recreate, rebuild or update legacy journal tables.

| Check                                                              | Result                                     |
| ------------------------------------------------------------------ | ------------------------------------------ |
| Installed revision                                                 | `0003`                                     |
| SQLite integrity check                                             | `ok`                                       |
| Foreign-key violations                                             | None                                       |
| Legacy rows/counts and complete record fingerprints                | Preserved                                  |
| Trade IDs and exit parent links                                    | Preserved                                  |
| Legacy table/index definitions                                     | Unchanged                                  |
| Per-trade calculations and currency-separated analytics/Trading IQ | Preserved                                  |
| Screenshot references and upload manifest                          | Preserved                                  |
| `journal_accounts`                                                 | Exists; empty                              |
| `instruments`                                                      | Exists; empty                              |
| `instrument_snapshots`                                             | Exists; empty                              |
| `broker_import_batches`                                            | Exists; empty                              |
| `trade_contexts`                                                   | Exists; empty; no inferred assignments     |
| Snapshot guard triggers                                            | All three expected SQLite guards installed |
| Alembic metadata comparison                                        | No new upgrade operations detected         |

After commit, the database was reopened read-only and independently checked against the baseline. No verification failed; no recovery or downgrade was performed. Its whole-file checksum changes as expected when the schema/version changes, while the historical record fingerprints remain identical.

## Local application restart

Started the development API on `127.0.0.1:8000` and frontend on `127.0.0.1:3000`, bound to loopback. The API uses the explicit normal database and upload paths. Background processes run without visible helper windows; private logs/PIDs are in the audit directory.

GET-only verification passed for API readiness, listing, trade detail, analytics, the journal page and frontend API bridge. API records and calculated metrics matched the verified migration state. The database fingerprint remained unchanged by these reads. No practice trades or other mutation requests were sent to the real journal.

Open **http://127.0.0.1:3000/journal**, choose the existing record's currency, open that record and compare its saved prices, quantity, fees, notes, exits and metrics. Refresh to confirm it remains readable. Use the isolated practice environment for test additions/deletions rather than adding test records to the normal journal.

## Safe table-inspection exercise

A migration changes the database blueprint; an empty new table is expected because ownership and specifications have not been invented. From the repository root, this PowerShell/Python exercise opens the normal database in read-only mode and displays only revision/table names:

```powershell
@'
from pathlib import Path
from contextlib import closing
import sqlite3

database = Path("services/api/ava.db").resolve(strict=True)
with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
    connection.execute("PRAGMA query_only=ON")
    print("Revision:", connection.execute("SELECT version_num FROM alembic_version").fetchone()[0])
    for (name,) in connection.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name"):
        print(name)
'@ | .\.venv\Scripts\python.exe -
```

Expect revision `0003`, the three old journal tables, five new extension tables and `alembic_version`. Do not use an upgrade command just to inspect a revision. The SQLAlchemy schema must describe the tables, while Alembic's version records that the database has actually installed them.

## Recovery boundary and limitations

The verified recovery copies are still pre-migration snapshots, not backups of future trades. Before any later migration, re-evaluate source changes and refresh backup verification as needed. Preserve a failed database and assess its transaction/revision state before considering restoration. Do not overwrite a healthy source or erase populated extension tables as an automatic response to an error.

SQLite runtime migration is verified. PostgreSQL migration SQL was previously checked offline; PostgreSQL runtime remains unverified and requires its own rehearsal before deployment. Account-management UI, CFD entry/calculations, automatic synchronization and execution are not enabled by these empty tables.

Next: review the [2B.3 calculation-engine plan](phase-2b-3-plan.md). No CFD implementation is part of this checkpoint.
