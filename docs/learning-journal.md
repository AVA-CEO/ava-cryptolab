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

## 2B.3A — checking the ingredients before calculating

A schema is a form with rules. Pydantic is the Python tool checking that form. A field rule checks one box, such as positive lots; a model rule checks several boxes together, such as exit lots not exceeding entry lots. A valid form means the inputs meet our rules, not that a broker has verified them. The [milestone report](phase-2b-3a.md) explains each file and the rules.

Think of cooking: buying the right ingredients and measuring them correctly comes before turning on the oven. We have built the measuring stage. CFD PnL calculation is the next separately reviewed step. Your existing crypto calculator continues working.

### Decimal and units

Python `Decimal("0.10")` keeps that base-ten amount exact. Ordinary binary floating point can introduce tiny representation differences. Converting a float afterward cannot recover precision already lost, so the new financial fields reject floats and booleans. JSON amounts are strings; a later TypeScript form must preserve those strings when sending them to Python. This milestone changes no TypeScript forms.

Lots and contract size are different measuring cups. Lots measure how many contracts; contract size says how much one lot represents. A pip and a tick are also separate declarations. We do not assume a gold contract has the same size as a forex contract or that a JPY pip is the same as a EURUSD pip.

### Currency conversions need a label and a date

An amount without its currency is like a distance without metres or miles. A conversion rate says how many target currency units one source unit buys. The reverse direction is a different input. Each rate has a source, observation time, application time and explicitly chosen allowed age. No automatic inversion or dollar/stablecoin equivalence occurs.

`native_only` means keep currencies separate without converted totals. `explicit_rates` requires suitable evidence for each foreign-currency exit/cost and original stop-risk input. A missing rate is not replaced with 1. For tick-mode metadata, the supplied tick observation's currency remains visible; it is not relabelled as another currency.

### Immutability and fingerprints

A frozen input is a photograph, rather than an editable whiteboard. Nested models are frozen and execution/cost lists become tuples, which cannot be appended to in place. A SHA-256 digest is a content fingerprint: altering the contract size while retaining the old fingerprint causes rejection. It is not a broker signature and does not prove the supplied snapshot ID exists. Existing database guards still protect stored snapshots; this milestone does not write them.

### Tests can teach us about the test setup

The first full run stopped during test discovery because a new package marker conflicted with an existing flat test import. We removed the new marker and used the established convention, without changing the original tests. The final backend run passed 266 cases. A test that cannot be collected has not passed; fixing the setup and rerunning is part of verification.

### Practical exercise — a safe validation error

From the repository root, run the synthetic example:

```powershell
.\.venv\Scripts\python.exe services/api/scripts/validate_cfd_input.py services/api/tests/fixtures/cfd-input.synthetic.json
```

Expect `Valid CFD inputs (explicit_rates). No PnL calculated or records saved.` Then create a private practice copy:

```powershell
New-Item -ItemType Directory -Force private/exercises | Out-Null
Copy-Item services/api/tests/fixtures/cfd-input.synthetic.json private/exercises/cfd-input.json
```

In VS Code, open `private/exercises/cfd-input.json` and change only the entry's `lots` from `"0.10"` to `"0.03"`. Keep the exit lots unchanged, then run:

```powershell
.\.venv\Scripts\python.exe services/api/scripts/validate_cfd_input.py private/exercises/cfd-input.json
```

Expect `Exit lots cannot exceed original entry lots.` The process exits with code 1: a deliberate validation failure, not a broken database. Restore entry lots to `"0.10"` and run again for success (exit code 0). You learned how one form field can invalidate a relationship with other fields. The command does not open the journal database or calculate a profit, and `private/` is ignored by Git.

## 2B.3B — following the money and keeping the units

We now have a separate calculator for explicitly supported linear forex/CFD contracts, one entry and one fully closing exit. Think of a receipt: first count what was bought, then compare sale proceeds to purchase cost, then add the recorded fees or credits. A different contract may need a different recipe; a tick-based instrument is not sent into the linear recipe automatically.

### Lots are packages; contract size is the package label

In the synthetic EURUSD example, one lot represents 100,000 units because the supplied snapshot says so. At 0.10 lots, the position represents 10,000 units. Moving from 1.10000 to 1.10100 gives a difference of 0.00100 USD per unit. Therefore the buy earns 10 USD gross. The original stop at 1.09900 is also 0.00100 away, so original planned price risk is 10 USD. This is a stop-price estimate, not a guarantee or broker margin requirement.

Commission of −3 USD and swap of −1 USD are debits. Gross 10 plus costs −4 gives net 6 USD. Divide net 6 by original risk 10 to get 0.6R. R is a ratio: like saying a journey used six tenths of a tank, it compares two quantities on the same basis. It is not a currency or a promise of future performance. A missing original stop produces an unavailable risk/R result rather than zero risk.

### Decimal and rounding do different jobs

Decimal keeps the base-ten inputs exact. The calculator uses a fresh 160-digit working context, independent of the caller's Decimal settings. That is enough for exact cash products and sums within our input bounds. A repeating division such as 2.5 ÷ 6.5 still needs finite precision. Display rounding then uses a separately supplied rule; it never replaces the raw amount used for R or net accounting.

The policy must name decimal places for every relevant currency. We do not assume all currencies have two decimals. HALF_EVEN rounds a tie toward an even final digit: 2.345 to two decimals becomes 2.34. HALF_UP gives 2.35. Two separately rounded fees need not add to the correctly rounded total, so we sum unrounded fees first. Exact raw values and the chosen policy remain visible in JSON output.

### JPY profit is still JPY before conversion

The synthetic USDJPY move from 150.000 to 150.100 produces 1,000 JPY gross using the declared lots and contract. A supplied JPY→USD rate of 0.0065 converts it to 6.50 USD; USD costs of −4 then leave 2.50 USD. The native JPY gross remains visible. Native net is unavailable here because those USD costs have no approved JPY valuation policy. We do not silently reverse the rate.

Entry-time risk conversion and exit-time profit conversion are separate observations. If those rates differ, native R and reporting-currency R can differ. That is why we show their currencies and preserve each observation's source and timestamp. USD, USDT and USDX are separate labels, not interchangeable money.

### Pure functions and independent tests

A pure function is like a pocket calculator: it uses the supplied numbers and returns an answer without opening a database or calling a broker. The engine does not save a trade. Its tests compare hand-worked answers and independent rational-number cash ledgers. A rational number is an exact fraction, so it gives us a second arithmetic method rather than trusting the same Decimal implementation to generate expected answers.

Leverage is not multiplied into these profits. Actual fill prices already reflect bid/ask execution; subtracting a guessed spread again would count it twice. No CFD margin estimate is produced because broker margin rules need their own inputs and review. Existing crypto leverage/margin behavior remains unchanged and is regression-tested.

### Practical exercise — turn a synthetic win into a loss

From the repository root:

```powershell
.\.venv\Scripts\python.exe services/api/scripts/calculate_cfd.py services/api/tests/fixtures/cfd-calculation.synthetic.json
New-Item -ItemType Directory -Force private/exercises | Out-Null
Copy-Item services/api/tests/fixtures/cfd-calculation.synthetic.json private/exercises/cfd-calculation.json
```

Open the private copy in VS Code. Under `trade.exits`, change the single exit's `price` from `"1.10100"` to `"1.09900"`. Leave the entry, original stop and costs unchanged. Then run:

```powershell
.\.venv\Scripts\python.exe services/api/scripts/calculate_cfd.py private/exercises/cfd-calculation.json
```

Expect −10 USD gross, −14 USD net, 10 USD original planned risk and −1.4R. Costs can make a stop-price loss larger than the original price-risk estimate. Restore the exit price for the original 6 USD net and 0.6R. Add `--json` to inspect the raw amounts and policy. You have learned units, signed cash flows, original-risk denominators and the difference between calculation and display rounding. This exercise does not touch your normal journal or backups.

## 2B.3C — closing a position in pieces

Imagine a box containing ten identical items. You sell four today and six tomorrow. You began with ten, sold four and have six remaining after the first sale. Counting tomorrow's sale today would give the wrong answer, so our calculator asks for an explicit `as_of` time: a financial snapshot at a chosen moment.

| Trading term       | Simple meaning                                                                     |
| ------------------ | ---------------------------------------------------------------------------------- |
| Original lots      | Quantity opened at entry; it stays the starting reference                          |
| Exited lots        | Quantity actually closed by the chosen cutoff                                      |
| Remaining lots     | Original minus exited quantity                                                     |
| Gross realized PnL | Price profit/loss from those completed exits, before recorded costs                |
| Realized net PnL   | Gross realized PnL plus included incurred costs/credits                            |
| Unrealized PnL     | Valuation of the still-open portion at a separate supplied price; unavailable here |

### Follow the owner's example

The synthetic EURUSD buy opens 0.10 lots at 1.10000 with a supplied 100,000-unit contract. Closing 0.04 lots at 1.10200 realizes 8 USD and leaves 0.06 lots. Closing those 0.06 at 1.10300 adds 18 USD, bringing gross to 26 USD. The original stop is 1.09800, so original planned risk is 20 USD throughout.

At the first exit, no-cost realized R is 8/20 = 0.40. At full closure it is 26/20 = 1.30. We do not replace the denominator with the quantity remaining. With 4 USD of costs the final net is 22 USD, or 1.10R. Planned price risk remains an estimate, not broker margin or guaranteed maximum loss.

### One receipt, one recognition

Each recorded cost has a unique ID, occurrence time, signed amount, currency and source. Think of stamping a receipt once. The entry commission is recognized in full when incurred; it is not stamped again for every exit. Exit fees link to actual execution IDs. Swaps/other costs follow their own timestamps. Component views explain the same costs; they are not extra charges to add again.

Our policy is called `incurred_once`. It can show an open position with negative realized net from an actual entry commission even before the first exit. That is recorded cash cost, not an estimate of unrealized loss. Partial/open outcomes are not classified as completed-trade wins/losses. Duplicate IDs reject the request; detecting accidentally duplicated economic charges with different IDs needs future import provenance, not a guess.

### Dates, currencies and evidence

Every included exit uses its own supplied conversion observation. Two JPY profits on different days can use different JPY→USD rates. Original risk uses its entry-time rate. We retain native amounts and mark missing converted totals unavailable.

Reconciliation means comparing two independently preserved records. Our foundation keeps calculated and reported amounts side by side, checks position/account/instrument, lot coverage, time, currency and accounting basis, then shows a difference with an explicit tolerance. Numerical agreement in a synthetic exercise does not prove a real broker statement was reconciled. No real statement has been tested.

### Practical exercise — move the financial clock

From the repository root:

```powershell
.\.venv\Scripts\python.exe services/api/scripts/calculate_cfd_position.py services/api/tests/fixtures/cfd-position.synthetic.json
New-Item -ItemType Directory -Force private/exercises | Out-Null
Copy-Item services/api/tests/fixtures/cfd-position.synthetic.json private/exercises/cfd-position.json
```

In the private copy, change the top-level `as_of` from `"2025-01-05T00:00:00Z"` to `"2025-01-04T00:00:00Z"`, then run:

```powershell
.\.venv\Scripts\python.exe services/api/scripts/calculate_cfd_position.py private/exercises/cfd-position.json
```

Expect state partial, 0.04 exited lots, 0.06 remaining, gross/net 8 USD, original risk 20 USD and 0.40R. The later exit remains in the input ledger but is deferred from this financial snapshot. Restore the original cutoff for 26 USD and 1.30R. Then run the cost example:

```powershell
.\.venv\Scripts\python.exe services/api/scripts/calculate_cfd_position.py services/api/tests/fixtures/cfd-position-costs.synthetic.json
```

Expect four recognized cost records totalling −4 USD, net 22 USD and 1.10R. Add `--json` to inspect the IDs and separate synthetic comparison evidence. The commands read files and return calculations; they do not save journal trades. You learned event-ledger accounting, time cutoffs, immutable original risk, explicit cost recognition and evidence comparison.

## Milestone 2B.4A — accounts, APIs and dated rule cards

An **API endpoint** is a named service desk, such as `POST /api/v1/management/accounts`. POST asks the desk to create something; GET asks it to read something. The React screen sends JSON through a local Next.js bridge to FastAPI. The bridge checks the destination and browser origin; it never asks for broker passwords.

**Pydantic** is the inspector at the desk. It rejects missing currencies, unsupported platforms and incompatible specifications before they reach storage. **Zod** gives quicker feedback in TypeScript, but Python still makes the final decision. Decimal strings such as `"0.01"` preserve exact financial quantities while travelling in JSON.

**SQLAlchemy** translates Python account objects into database rows. An account ID is its unique folder number; the broker label is not its ID. Instrument and snapshot IDs identify the instrument and a dated version of its rules. A snapshot is like a signed-off recipe card: a changed recipe gets a new card rather than quietly rewriting yesterday's card.

The specification catalog is shared between compatible accounts at the same broker/server/settlement scope. That does not mean their trades or balances are merged. Reporting GBP and settlement USD are different labels; no exchange rate is invented. Current practice accounts have no calculated balances and cannot receive historical trades automatically.

A **transaction** groups a database action into one package. If account identity or instrument rules conflict, rollback cancels the package. The snapshot's content hash is a fingerprint used to reuse identical content and detect changes; it is not proof that a broker verified the values.

The practice runner creates a temporary filing cabinet, and the normal journal's cabinet remains closed to management operations. Loopback means this computer; it is a useful local boundary, not a replacement for future user authentication.

### Exercise: one account, two rule cards

Follow [the practice commands](phase-2b-4a.md#try-it-safely). Create the synthetic MT5 account and paste the fixture's `snapshot.specification` object. Save it, then change its contract size and save again. Review both IDs and content hashes: the account ID remains the same, while the changed specification receives a different snapshot ID. Save identical content again and confirm there are still two versions. Try changing the broker and confirm rejection. Stop the practice API when finished; its records are discarded.

You have practiced React form state, TypeScript boundary validation, HTTP requests, Python validation, SQLAlchemy persistence, immutable version history and isolated testing. None of these steps places an order.

## Milestone 2B.4A acceptance and 2B.4B design review — safe saves

On **2026-10-17** you reported passing all eight manual Accounts scenarios and accepted 2B.4A. Those are your observations, not eight new automated tests. Automated tests repeatedly check programmed rules; manual acceptance checks whether the real experience works for you. Neither kind should be relabelled as the other.

The next design adds a CFD filing cabinet beside the existing crypto cabinet. A **database relationship** is a checked label: a position points to its account and the exact instrument rule card. A foreign key stops it pointing to a nonexistent record. Python must also check meaning—for example, an MT5 CFD account cannot use a crypto futures specification merely because that specification has a valid ID.

An **API endpoint** is a service desk with an address. A future preview desk would calculate without saving; a save desk would validate and store a complete, numbered revision. TypeScript helps prepare the request; FastAPI receives it; Pydantic checks its shape and financial units; Python Decimal calculates; SQLAlchemy stores it. The proposed [flow diagram and schema](phase-2b-4b-design-review.md) show this journey. None of those new CFD endpoints exists yet.

An **atomic transaction** is an all-or-nothing envelope. If saving an exit succeeds but saving its commission fails, rollback discards the entire attempt. You should never see half a trade saved. A rollback can cancel staged work before commit; it is not permission to erase a previously committed historical trade.

**Idempotency** means retrying one request has one effect. Imagine clicking a lift button twice: it should not create a second lift. A numbered save key acts like a receipt. If the network loses the reply, retrying the same key and same data returns the already saved result. Reusing the key with different data is an error. Giving the same trade completely new IDs can still look like a new request, so IDs and future broker-import rules matter too.

**Optimistic concurrency** prevents one old browser tab overwriting another tab's newer work. Both tabs open page 3. Tab A saves page 4. Tab B still presents page 3, so the server asks it to reload rather than erasing page 4. The proposed HTTP `If-Match` header carries that expected version; a database comparison makes the check atomic.

An **immutable revision** is a retained page of history. A correction adds page 4 and moves the bookmark; page 3 remains available. Original entry, specification and risk basis stay fixed within the position. A genuinely mistaken original basis would require an explicit void-and-replacement workflow. Archive hides a record from current views; it is not permanent deletion.

Decimal strings preserve exact written quantities. A calculation manifest records which recipe and rounding rules were used. Saving the same inputs, dated rates, recipe version and result lets us check it again later. A hash is a fingerprint that detects changed content; it does not prove a broker supplied the numbers.

### Paper exercise — two tabs and a lost reply

No database or new code is needed. Draw a position at version 3 with net PnL 8 USD. Pretend two tabs both opened it. Tab A submits key `practice-A`, expected version 3, and saves version 4 with net PnL 26 USD. Its reply is lost. What should happen when A retries the same key/data? **Return the original version-4 receipt, without another revision.** Now tab B submits a different edit expecting version 3. What should happen? **Reject the stale edit and ask B to reload.** If A instead reuses `practice-A` with different data, reject that key conflict. Keep pages 3 and 4 on your paper: this is the history we want the future database to preserve.

This was a design exercise only. You learned relationships, API boundaries, atomic transactions, idempotency, optimistic concurrency and revision history. B1 and disposable-only B2 were subsequently authorized; B3 and normal-database migration remain unauthorized.

## B2 corrective rehearsal — missing instructions are not permission to guess

An Alembic inspection command is like asking a librarian to compare the catalogue with the shelves. It does not ask to travel to a new revision. Our guard wrongly expected every command to name a destination. The correction handles that missing instruction while still checking that the database is disposable.

A regression test repeats the situation that previously failed, so future edits cannot quietly bring the problem back. The corrected rehearsal reached the metadata check successfully. A later currency test then failed for a separate reason: it introduced a EUR commission without supplying EUR rounding instructions. The existing calculator refused to guess. Passing one check does not mean every check passed; the [B2 report](phase-2b-4b-b2-validation.md) records the distinction.

An atomic transaction is a sealed envelope: either every page is filed or none is. Synthetic tests deliberately fail after different save stages to check rollback. Immutable revisions are numbered pages that cannot be erased or rewritten; a current-revision pointer is the bookmark. Concurrency tests must prove that two writers cannot silently replace each other's bookmark updates.

### Exercise: inspect a synthetic currency policy

Open `services/api/tests/fixtures/cfd-position-costs.synthetic.json` in VS Code. Find `rounding.currencies`: it declares USD with two decimal places. On paper, change one commission's currency to EUR. List the additional instructions required: an explicit EUR precision rule and dated EUR-to-USD conversion evidence. Why is a conversion rate alone insufficient? It tells the software how to translate currencies, but not how to round and display each currency. Do not edit your journal or run migrations for this exercise.

## B2 completion ? reproducible pages and safe retries

The authorized B2 work adds ten CFD database tables and a migration rehearsed only on disposable databases. The final backend run passed 557 tests, and desktop/mobile browser regression testing passed 14 tests. PostgreSQL and historical container replay remain unverified. No CFD API, frontend trade form or normal-journal migration was added.

An **SQLAlchemy model** describes a filing drawer in Python. A **migration** is the instruction sheet that builds the drawers in a database. A **primary key** is a unique label on a page; a **foreign key** checks that a referenced folder exists and belongs to the expected account. Compatibility checks additionally ensure that the broker, server, venue and product agree. Matching broker names alone is insufficient.

A **trigger** is a database rule that runs even if someone writes SQL directly. Our triggers reject changes to accepted history and the wrong account/server combination. They cannot prove that a broker supplied a price or that a calculation is correct. Python validates financial meaning; Decimal keeps financial strings out of binary floating-point arithmetic. A database administrator can still alter schema rules, so future authentication and least-privilege access matter too.

A **transaction** keeps the trade pages, bookmark and receipt together. Tests deliberately interrupt saves after children, sealing, bookmark updates and receipts; rollback leaves the old state intact. A compound void-and-replacement operation needs the same envelope for both folders. A verified synthetic backup is a separate saved copy; restoring it into another temporary database proves that the copy is usable without overwriting anything valuable.

**Idempotency** uses a receipt key scoped to an account. Repeating the same command can retrieve its receipt; using that key for different content is a conflict. **Optimistic concurrency** checks the version the editor started with. SQLite's `BEGIN IMMEDIATE` gives one writer the turn, and the second writer must recheck the saved version after waiting. This does not demonstrate PostgreSQL's different locking behavior; PostgreSQL needs its own real tests.

We found that three correct FX records could return from SQL in a different order. Hashing a list with a different order creates a different fingerprint. The synthetic builder now sorts keyed evidence consistently before hashing and reloading. Entry and exit order is retained separately with execution ordinals. B3 must adopt and version its production normalization rules; a test fixture is not an API.

We also learned that ?after one table was created? is different from ?after all tables were created.? Trigger setup now waits for the complete schema and does not reinstall guards when `create_all` finds everything already present. The normal application never calls migrations at startup.

### Exercise: a disposable safety drill

From the repository root, run:

```powershell
.\.venv\Scripts\python.exe -m pytest services/api/tests/test_cfd_target.py -q
.\.venv\Scripts\python.exe services/api/scripts/rehearse_multi_asset.py
```

The first command proves that normal path strings are rejected before engine creation; it does not open your journal. The second invents four teaching trades and three exits in its own temporary database, backs them up, migrates, compares them and rehearses reversal. Look for `0004 (head)`, `No new upgrade operations detected`, preservation `true` and zero counts for new tables. A zero count proves no historical account or instrument assignment was invented. Do not replace the temporary path with your journal path.

B3 implementation and normal-database migration still require separate approval. No Docker installation is needed for this exercise.
