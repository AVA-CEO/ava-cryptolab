# B2 validation report

Date: 2026-10-17. Local disposable-only validation. No normal-journal migration, B3 API, deployment or push is included.

## Corrections and root causes

1. **Alembic:** `EnvironmentContext.get_revision_argument()` reads `destination_rev`, which inspection commands such as `check` do not supply. The guard now catches only that missing key and treats the destination as absent. It still validates the target before creating an engine, and validates supplied connections before running migrations. Every online command is restricted to disposable targets. The existing temporary Accounts launcher retains its explicitly pinned `0003` bootstrap; inspection/head/0004 do not receive that exception. Ordinary journal paths are always rejected. `heads` itself lists the migration graph without requiring a database.
2. **EUR test fixture:** an EUR commission lacked an explicit EUR rounding policy. The fixture now supplies two decimal places. The calculator was not weakened or changed.
3. **Replay test fixture:** unordered SQL conversion rows changed an array-sensitive input fingerprint. A synthetic diagnostic showed `risk-fx, exit-fx-0, exit-fx-1` reloading as `exit-fx-0, exit-fx-1, risk-fx`. The test builder now normalizes keyed evidence collections before hashing and uses explicit primary-key ordering when loading them. Execution ordering remains its recorded ordinal. Optional broker evidence defaults to an empty list, matching the approved schema. B3 must implement and version its own production canonicalization policy.
4. **Disposable metadata setup:** installing guards after the receipts table was created was too early for the complete schema. Installation now runs after metadata creation, checks that all ten tables exist, and only runs when CFD tables were actually created. The repeat-creation regression verifies that existing guards are not reinstalled.
5. **Lint:** long SQL strings were split without changing their meaning. ESLint now excludes generated `.next-practice` output, matching the existing `.next` and `.next-e2e` exclusions. Prettier also excludes the untracked local `.vscode` folder; the folder was not changed or staged. No source rule or hook was disabled.

Each failed test path was stopped and explained before its correction and retry. Earlier failures remain described here; they are not passing results. The Windows sandbox denial of pytest's Temp directory was resolved through the tool approval flow, not by weakening database guards.

## Final results

Final backend run: **557 passed** in 25.02 seconds. Final desktop/mobile browser run: **14 passed** in 34.1 seconds. No final test failures remain in the executed categories. Earlier failures and their corrections are retained above. No PostgreSQL or container replay success is claimed.

| Category                                                         | Result  | Evidence                                                                                                                                                     |
| ---------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Backend regression suite, including existing crypto calculations | PASS    | 557 passed; includes 79 B2 ledger/guard cases                                                                                                                |
| Alembic upgrade/current/heads/check                              | PASS    | Supplied connection and CLI-style disposable configuration; metadata has no pending changes                                                                  |
| SQLite integrity/foreign keys                                    | PASS    | Integrity `ok`, foreign-key check empty; foreign keys enabled on connections                                                                                 |
| Synthetic legacy preservation                                    | PASS    | Four trades, three exits; old IDs, row values, calculations and screenshot fingerprints preserved                                                            |
| Consistent backup and isolated restoration                       | PASS    | SQLite backup API; restored synthetic state equality and unchanged backup fingerprint                                                                        |
| Failure injection/atomic rollback                                | PASS    | Three DDL injection points, four ledger-save stages and compound replacement failure                                                                         |
| Empty-ledger downgrade/reupgrade                                 | PASS    | 0004 -> 0003 -> 0004; standalone runner also rehearses return to 0002                                                                                        |
| Nonempty downgrade rejection                                     | PASS    | Evidence and revision remain unchanged                                                                                                                       |
| Immutable revisions, trigger/constraint enforcement              | PASS    | Updates/deletes, SQLite REPLACE with recursive triggers on/off, parent identity drift, scope mismatch, sealed insertion, scoped FK and original-risk anchors |
| Idempotency and SQLite concurrency                               | PASS    | Independent connections, same-key replay/conflict, account-scoped keys, lost-reply receipt after another edit, two edits with one accepted version advance   |
| Compound void/replacement primitives                             | PASS    | Both histories commit together or the whole transaction rolls back                                                                                           |
| Exact financial reload                                           | PASS    | Synthetic USD net 22 and 1.10R; EUR 18-place FX; JPY native profit and original entry-time risk conversion                                                   |
| Protected target rejection                                       | PASS    | Guard tests use path strings/fake connections and fail if an engine is created for normal targets                                                            |
| Python lint and formatting                                       | PASS    | Ruff lint clean; 87 Python files already formatted                                                                                                           |
| Frontend lint                                                    | PASS    | Source checks retained; generated practice build excluded                                                                                                    |
| TypeScript                                                       | PASS    | `next typegen` and `tsc --noEmit`                                                                                                                            |
| Production build                                                 | PASS    | Optimized build using `.next-e2e`, API pointed at unused port 59999                                                                                          |
| Browser regressions                                              | PASS    | 14 desktop/mobile tests; new disposable API/database, existing journal and Accounts flows                                                                    |
| Repository formatting/diff review                                | PASS    | Prettier check passes; staged diff and sensitive-file review recorded before commit                                                                          |
| PostgreSQL execution                                             | SKIPPED | No safe isolated instance established; no compatibility claim                                                                                                |
| Historical container replay                                      | SKIPPED | No runtime installed or made mandatory; test manifest explicitly identifies host/synthetic execution                                                         |
| Real broker statement reconciliation                             | SKIPPED | No real statements supplied; all evidence synthetic                                                                                                          |

The backend emits one existing Starlette/httpx deprecation warning. Browser output includes terminal colour-environment warnings and intentional reduced-motion notices. None is a test failure.

## Hook investigation

Read-only Codex diagnostics identify `legacy_notify` after-agent failures with Windows error 206: ?The filename or extension is too long.? Three inspected records explicitly say `continuing`; none contains the exact `hook exited with code 1` banner. The configured notification executable is `codex-computer-use.exe`; its two configured argument lengths are 137 and 10 characters. Configured static arguments alone do not establish which runtime command segment exceeded a Windows limit. No credentials or complete hook arguments are reproduced.

This is evidence of a notification-command launch length failure. It does not establish that it caused the separate exit-code-1 banner, which remains unattributed. Git has no configured `core.hooksPath` and only inactive sample hooks were found locally. No notification, validation or security hook was disabled, removed, invoked with fabricated events or bypassed. This investigation reads Codex's diagnostic log database in read-only mode; that is separate from the trading journal databases.

## Safety and limitations

No command in this corrective work opened the normal journal, either preserved backup or existing practice records. Migration rehearsals used fresh Temp directories or newly created pytest databases; schema-only backend fixtures also used disposable in-memory databases. No historical account assignment or crypto calculation code changed. `.vscode/` remains untouched and must not be staged.

The ten-table schema is retained. Decimal values remain text with explicit units, hashes and UTC microsecond timestamps; Python contracts enforce financial semantics. SQL checks do not prove arithmetic, canonical hash correctness or broker authenticity. Database owners can bypass triggers with DDL, so production authorization and least-privilege roles remain future requirements.

SQLite results do not validate PostgreSQL PL/pgSQL branches. The target guard rejects PostgreSQL; a separately reviewed disposable PostgreSQL harness and real execution are required before enabling that dialect. Receipt hashes and replay logic in test helpers demonstrate database primitives, not B3 HTTP status/header behavior or a production persistence service. Release artifact packaging and offline historical runtime replay are not operational; their manifest columns are storage foundations only. No container installation is required for the current journal or tests.

## Repeat locally without accessing your journal

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest services/api/tests -q
.\.venv\Scripts\python.exe services/api/scripts/rehearse_multi_asset.py
.\.venv\Scripts\python.exe -m ruff check services/api
.\.venv\Scripts\python.exe -m ruff format --check services/api
```

The rehearsal command creates its own synthetic database and backup and removes them on successful exit. Do not substitute your journal's path. Do not run `alembic upgrade head` against the normal journal. Browser tests use `npm run test:e2e`; they start their own temporary API on 8001 and frontend on 3100, refuse occupied servers and use `.next-e2e`. Do not run a build concurrently with those browser tests.

## Complete file manifest

Created:

- `services/api/app/database/cfd_schema_v1.py`
- `services/api/app/database/cfd_guards_v1.py`
- `services/api/app/database/cfd_target.py`
- `services/api/app/models/cfd.py`
- `services/api/migrations/versions/0004_cfd_ledger.py`
- `services/api/tests/cfd_ledger_helpers.py`
- `services/api/tests/test_cfd_ledger.py`
- `services/api/tests/test_cfd_target.py`
- `docs/phase-2b-4b-b2.md`
- `docs/phase-2b-4b-b2-validation.md`

Modified:

- `services/api/app/database/rehearsal.py`
- `services/api/app/models/__init__.py`
- `services/api/migrations/env.py`
- `apps/web/eslint.config.mjs`
- `.github/workflows/ci.yml`
- `.prettierignore`
- `README.md`
- `docs/development.md`
- `docs/testing.md`
- `docs/phase-2b-4b-plan.md`
- `docs/learning-journal.md`

The unchanged application calculators, legacy migrations, journal UI, account management APIs and practice runner are not part of this diff. Database/backup/upload files and `.vscode/` are not staged. CI was updated locally; remote Actions results cannot be claimed before an authorized push.

Earlier disposable failures remain documented by this report and the development-session stack traces: `pytest-20` destination handling, `pytest-21` EUR precision, `pytest-23` conversion ordering and `pytest-24` optional broker-evidence handling. The full-suite trigger-creation failure used an in-memory fixture. These are synthetic diagnostic artifacts, not normal journals or preserved owner backups. No retained failure database was deliberately deleted by this corrective work; normal pytest/Windows temporary-file retention still applies.
