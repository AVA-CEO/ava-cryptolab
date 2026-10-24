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

## B3 readiness review - a service desk with a locked save button

This milestone is design only. The [readiness plan](phase-2b-4b-b3-readiness.md) explains future API contracts; it does not add endpoints or run migrations. B2's SQLite work is closed. PostgreSQL and historical container replay are still unverified.

An **API endpoint** is a named service desk. Preview asks, "What would these supplied trades calculate to?" Save says, "Check the reviewed facts again and file one complete record." Read says, "Show the page we already filed." A normal read should not recalculate a historical trade with today's rates or software.

A **runtime** is the toolbox in which the recipe executes. Our approved accepted-save policy requires a versioned container toolbox, not just the current Python program. No approved runtime is installed. We can build and test the desk while keeping accepted saves locked. An optional host-Python preview would need separate approval and must say it is unsaved and unapproved for accepted saves. A fake toolbox used in a test proves the desk's behavior, not that the real toolbox works.

A **fingerprint** or hash checks whether data matches the content previously reviewed. B3 must compare the stored rows with the preserved calculation input, not merely check a JSON blob against its own hash. An intact fingerprint is different from rerunning the original recipe, and neither proves a broker supplied the observations. A privileged database owner can alter data and hashes together; future access control still matters.

An **idempotency key** is a receipt number for one account. If a save commits but the reply is lost, retrying the same command and key should return the same receipt. Do not create another trade just because a reply went missing. An **atomic transaction** means all trade pages and that receipt commit together. The design calculates outside the write lock, then checks the account and rule card again inside the transaction before accepting the pages.

### Exercise: two currencies, two R values

On paper, buy a synthetic 0.10-lot USDJPY position at 150.000 with contract size 100000 and stop 149.800. Close 0.04 at 150.200 and 0.06 at 150.300, with no costs. Gross profit is 800 + 1800 = 2600 JPY; original risk is 2000 JPY; native R is 1.30.

Now supply fictional dated USD-per-JPY rates: risk 0.006, first exit 0.0065, second exit 0.0068. Reporting profit is 5.20 + 12.24 = 17.44 USD; original reporting risk is 12 USD; reporting R is about 1.453333. Different dated rates explain the difference. These are teaching numbers, not live quotes or broker specifications. Removing reporting FX under an explicit native-only policy can leave JPY results available while USD results are unavailable; it does not authorize guessing a rate.

No software, database or account needs to change for this exercise. B3A, B3B and B3C each need separate implementation approval. Normal-journal migration, broker access, runtime installation, deployment and a GitHub push remain separate approvals too.

## B3A Option A - checking an envelope without running the calculator

The owner authorized B3A after the readiness lesson above. The [B3A guide](phase-2b-4b-b3a.md) contains the file map, commands and actual validation report. B3B and B3C remain separate decisions.

An **API endpoint** is a named service desk. `GET /api/v1/cfd/status` asks which services are available. `POST /api/v1/cfd/preview` hands over an unsaved draft. FastAPI routes that request to Python. HTTP status codes are short labels: 200 means the status request succeeded, 422 means the supplied fields failed validation, and 503 means the required calculator is unavailable.

**Pydantic validation** is the desk's checklist. It checks that quantities are exact Decimal strings, timestamps name a timezone, exits do not exceed original lots and currency evidence has the right references. For example:

```json
{ "price": "150.000", "lots": "0.10" }
```

The quotes matter. This HTTP boundary rejects numeric `0.1` for lots instead of first turning a binary floating-point number into money. The existing internal calculation contracts and crypto engine are unchanged. Validation can establish that a specification is consistent; it cannot establish that a broker supplied it.

An **ID** is a checked label, not the whole account. SQLAlchemy loads the account and immutable instrument snapshot from the new practice database. Python compares broker, server, venue, product and settlement currency. A caller cannot slip a different rule card into the request. Snapshot hashing checks that the retained rule card has not changed; it is not a broker authenticity certificate.

A **separate practice runner** is a new exercise notebook. It creates a new temporary database, builds its approved 0004 tables and adds clearly synthetic identities. It never selects your normal notebook or resumes the older Accounts session. The guard checks the actual engine URL and the SQLite connection argument before opening a database. Read-only serving sessions add another boundary against accidental writes. The normal app does not gain these routes.

The **preview boundary** is the desk and checklist. An **operational calculator** is the approved toolbox that actually runs the recipe. We built the desk, but that toolbox is unavailable. Therefore a valid preview returns 503 with `calculation_runtime_unavailable`. It does not return invented profit or silently use host Python. Even a returning fake provider in an automated test cannot make the route report success. Test doubles prove control flow, not real financial execution or replay.

**Saving remains unavailable** because B3A neither implements a save endpoint nor has an approved calculation release. A future accepted trade must retain its original risk, exact results, dated conversion evidence and release identity together. The existence of empty ledger tables is not permission to file records. The original stop can be validated now without calculating or freezing original risk.

### Exercise: distinguish three responses

Follow the isolated-runner commands in the B3A guide. First request status with the local header: expect 200 and disabled capabilities. Submit the generated USDJPY example: expect 503, not PnL. In a copy of that JSON, change the lots string to a JSON number: expect 422. Finally omit the local header: expect 403. Explain each result in one sentence: readiness, missing runtime, invalid input, denied access. Stop the runner with Ctrl+C. Never substitute a journal database path, enter real trades or treat these steps as a calculation test.

You have learned API routing, strict transport contracts, trusted reference loading, disposable environments and the distinction between a validated request and an executed financial calculation. PostgreSQL and historical container replay remain unverified.

## B3B-R - opening a filed page without rewriting it

A **GET request** asks the API to retrieve a resource. Think of asking a librarian to show a numbered page. It must not place a trade, save a new version, update an exchange rate or run today's calculator. Our four new GET routes live only in the isolated practice API; the normal journal app is unchanged. The [B3B-R guide](phase-2b-4b-b3b-r.md) contains the exact file map, commands and validation report.

**Read-only** is also enforced at the database connection. SQLite's `query_only=ON` rejects writes. An explicit read transaction gives the verifier one stable photograph of the database while it checks the head, revision and evidence. Otherwise, inspecting one page before an edit and another page afterward could mix two different moments. Closing this read transaction changes no trading records.

A **hash** is a fingerprint of exact written content. Before displaying money, we compare stored documents with their fingerprints and reconstruct the input from the normalized rows: entries, exits, commissions, swaps and dated FX. Checking only the stored JSON against its own hash would not tell us whether its rows agree. A mismatch produces an error and withholds values; the reader does not quietly repair a page. A database owner who rewrites content and every matching fingerprint can defeat hash-only checks, so a fingerprint is not a signature or proof of the mathematics.

These three things are different:

| Evidence                  | Meaning                                                                                                                                                                   |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Accepted calculation      | A future result produced under the approved release/runtime policy, with retained provenance and verification. This is not enabled.                                       |
| Saved historical result   | A result retained from an earlier point in time. Its format, hashes, normalized evidence and provenance still need checking; being saved alone does not make it accepted. |
| Synthetic testing fixture | An invented, clearly labelled example used to test software. Our new read fixtures contain hand-declared results, not broker records or approved runtime output.          |

**Historical retrieval must not recalculate.** Suppose a saved USDJPY page used a supplied 0.005 USD-per-JPY observation at its recorded time. A rate fetched today answers a different question and could change the displayed historical USD profit. The GET returns the preserved result and dated evidence, with replay explicitly `not_run`. It does not claim that checking hashes reran the original recipe.

**Pagination** divides a collection into manageable pages. A signed cursor is a checked bookmark bound to the account, collection, parent and page size. It is not a password. Changing those instructions or restarting the practice app invalidates the bookmark. Account scoping prevents a position from another synthetic account appearing under the requested account; public multiuser authentication is still outside scope.

### Exercise: two historical pages, one original risk

Run the new isolated practice runner and follow the catalog commands in the B3B-R guide. Retrieve current revision 2 and historical revision 1. Find net 2400 JPY on the closed page and 700 JPY on the partial page. Compare `original_risk_sha256`: it should match, with original risk 2000 JPY on both pages. Explain why closing 0.04 lots did not replace the original 0.10-lot risk denominator. Inspect `provenance` and `replay`: why does this successful GET still not prove accepted calculation or historical replay?

Do not edit a database to test corruption yourself; automated tests use newly created adversarial fixtures. A POST must remain unavailable, and the valid preview example must still return 503 `calculation_runtime_unavailable`. Stop the practice runner when done. No normal journal, existing practice records or backup is involved.

You learned GET semantics, database read-only transactions, stable snapshots, normalized evidence reconstruction, fingerprints versus replay, explicit provenance and scoped pagination. Runtime readiness and accepted saving require separate review and authorization.

## R1 - a toolbox needs room on the workbench

The [R1 machine and security review](phase-2b-4b-r1-runtime-review.md) records the actual observations and the proposed installation/recovery gates. Nothing was installed or enabled. The laptop has 16 GiB of physical RAM, but only 2.28–2.73 GiB was available during the snapshots. Owning a large workbench is different from having an empty workbench.

**WSL** means Windows Subsystem for Linux. WSL 2 provides a Linux kernel in a virtualized environment so Linux programs can run alongside Windows programs. It still uses real CPU, RAM and disk. Finding `wsl.exe` is like finding a doorbell: it does not prove the room behind it is ready. We found the command file, but the WSL and Virtual Machine Platform features were disabled; the exact installed WSL product version was not established. We did not launch it to find out.

**Virtualization** lets a computer host a separate operating environment. The processor model supports it, and Windows' existing virtualization-based security is running. That does not prove a Linux VM or calculator works. The conflicting low-level CPU flags were marked UNKNOWN rather than used as a reason to change BIOS settings or turn security off. A read-only preflight checks signs of readiness without trying to make the system ready.

A **container** is a packaged process with its libraries and restrictions. Think of a recipe in a sealed toolbox, placed inside a larger workshop. On this Windows design the Linux workshop is WSL; the calculator container is the toolbox. A 256 MiB calculator limit does not mean the whole WSL/runtime consumes only 256 MiB. VM and container budgets are separate.

**Docker Desktop** is one application that manages that workshop and its containers. Podman is another approach; Microsoft's WSL container tooling is another candidate. They need their own setup and tests. Familiar commands or a lower number of installed applications do not prove lower memory consumption or equivalent security. Our conditional preference is Docker with WSL 2, after resource and approval gates pass.

An **OCI image** is a container package following the Open Container Initiative's standards. Its layers, configuration and manifest identify what will run. A tag such as `latest` is a movable label. A **digest** is a fingerprint of specific bytes. The image manifest digest, image configuration digest, source-code hash and archive-file checksum identify different things; one cannot stand in for all the others.

A **signature** is an approval seal made with a private key and checked with a public key. The proposed AVA policy uses Ed25519 signatures over a precisely defined canonical release manifest. This choice still needs owner sign-off and implementation tests. No real signing key was created. The executor would receive only approved public keys, never the private signing key. A signature from an unknown key is not trustworthy simply because that key arrived with the package.

**Canonical** means there is one defined way to write the signed data. Otherwise two documents could mean the same thing but have different bytes and fingerprints. The release manifest records the image identity, Python/dependency versions, Decimal context, supported contracts and limits. This proposed signed software manifest is different from our existing synthetic test manifests. We cannot turn a fixture into accepted financial evidence by changing a label.

**Historical financial replay** means using the original retained recipe, policy and inputs again, including the original dated FX evidence and risk basis. It does not mean asking today's calculator for today's exchange rate. Reading saved evidence is also different from rerunning the recipe. If the old artifact, verifier or compatible runtime is missing, the honest result is replay unavailable. Keep the saved evidence; do not invent a replacement.

**Rollback** means undoing only changes made by the approved installation, using a record of the original state. Uninstalling a runtime can delete its images or volumes. It must not become permission to delete a different Linux environment, overwrite a journal backup, shut down all WSL distributions or disable Windows security. A stopped runtime is not the same as a fully removed runtime, and an idle icon is not proof that all memory has been released.

### Exercise: decide whether to start, without starting anything

Open the R1 matrix. Find one PASS (the processor's hardware capability), one FAIL (the currently disabled WSL prerequisite) and one UNKNOWN (actual offline calculator execution). On paper, compare 2.73 GiB available RAM with the proposed 3 GiB VM ceiling. Why is there no safe promise that it fits, even though the laptop contains 16 GiB? What else must remain available for Windows, VS Code and Python?

Now imagine two packages both labelled `calculator-v1`, but with different image digests. Explain why the label alone cannot authorize execution. Finally, explain why a valid signature still does not prove that a broker supplied a trade or that historical replay succeeded. No command, key, calculation or database change is needed for this exercise.

You learned machine capability versus operational readiness, WSL/VM resource sharing, containers, image identity, signatures, offline trust, replay and reversible installation planning. R2, signing-key generation, approved previews and accepted saves remain separate approvals. PostgreSQL and historical container replay remain unverified.

## P1 — keep the careful bookkeeping, simplify the kitchen

The owner has chosen **Path B**. The [local policy](path-b-local-calculation-policy.md), [release specification](path-b-python-release-spec.md) and [product-first roadmap](product-first-roadmap.md) document the proposed rules and the next visible feature. This milestone writes documentation; it does not switch on a calculator, save a CFD position or change a database. Earlier container documents remain history, not mistakes to erase.

Think of the calculator as a recipe and the database as a bound accounting book. A container packages a larger kitchen around the recipe. For a personal journal, we can propose using a carefully checked Python kitchen already on the laptop, while retaining the same rules about entries, costs, currencies and corrections. We do not need to throw away the accounting book to change kitchens.

**Version-pinned** means choosing exact software, not whatever happens to be newest. A **release manifest** lists the recipe, interpreter, dependencies, calculation settings and their fingerprints. A **registry** is the owner's list of which release may do which job. Preview permission is not save permission. Even a correct result cannot grant itself permission to enter the journal.

A **build hash** identifies a defined software descriptor. A **release-manifest hash** identifies the full software description. A future **evidence-envelope hash** identifies the software description plus that revision's local execution/approval facts. These are different fingerprints, like an oven's model number, a recipe card's fingerprint and a particular meal's receipt. Path B must never call a Python build hash a container-image digest.

**Canonical** means writing the same data in one precise form before hashing it. For example, a financial zero becomes `"0"`, and timestamps use UTC with recorded precision. Existing instrument snapshots keep their original agreed spelling and fingerprint. A new serializer must not rewrite old snapshots or pretend the existing synthetic test format has become accepted personal evidence.

The local profile is named `local_personal`. It must be deliberately selected and approved. **Fail closed** means a missing or changed release produces an unavailable message rather than quietly using a different calculator. Until P2 is implemented and its actual preview release is approved, the current valid API preview still returns 503 `calculation_runtime_unavailable`.

**Isolation has limits.** A Python virtual environment keeps packages organized; it does not lock the calculator away from Windows. The proposed small worker process makes timeouts and bounded output practical, but it still runs with your user's permissions. Hashes help catch changed files; they do not defeat someone who can rewrite both the files and expected hashes. Signed containers remain an optional future assurance level.

**Financial rules stay careful.** Original risk is the starting measuring stick, not the quantity left after an exit. Costs are counted once through the chosen cutoff. JPY, USD and USDT are separate currencies. A saved result must retain the rate/source/time actually supplied, not quietly use today's rate. Native results can remain available while reporting conversions are unavailable; an unsupported mixed-currency cost still needs an honest explanation.

**Reading is not replaying.** A future GET checks that the saved pages fit together, then shows their preserved values. Replay would run the exact older recipe again and compare results. If the original runtime is missing, we keep the pages and say replay is unavailable. A successful synthetic test, a locally accepted record and a broker-reconciled record are three different claims.

### Exercise: review a preview without running software

On paper, start with the roadmap's synthetic EURUSD example: 0.10 lots, declared contract size 100000, entry 1.10000 and original stop 1.09800. Original risk is 20 USD. Closing 0.04 lots at 1.10200 gives 8 USD gross; 0.06 lots remain. Why is realized gross R 8 / 20 = 0.40R rather than a fraction based on the remaining lots?

Now close the remaining 0.06 lots at 1.10300: cumulative gross is 26 USD. Add signed costs of -2, -1 and -1 USD, each once. Net is 22 USD and realized R is 1.10R. Identify which parts belong in the immutable original-risk record, which belong in executions/costs, and which belong in the software release manifest. Should changing the software version change these already saved facts? Explain why a `saved:false` preview grants no save permission.

You learned explicit execution profiles, versioned releases, separate approval purposes, build versus evidence identity, canonicalization, local trust limitations and product-first delivery. Next is review of P1 and separate P2 implementation/release approval, not automatic host activation. No journal, backup, practice record or migration changed during this documentation milestone.

## Working web delivery — connect the buttons to real behavior

The later owner authorization moved us from P1 documents into implementation. The [delivery guide](web-product-delivery.md) has the actual startup commands. Forex/metals previews now use a frozen copy of the existing Python engine and dependencies. Starting that runner requires the exact reviewed release digest; changed bytes fail verification. The preview-only manifest is intentionally smaller than the full accepted-evidence proposal, and cannot authorize saving.

A **server bridge** is a controlled doorway: the Next.js screen sends decimal strings to its own API, which forwards them only to the explicitly configured local practice service. Python validates the account/specification, runs the verified worker and returns results. Browser code never calculates the journal PnL or handles broker credentials. On Vercel, this financial doorway is closed until secure cloud persistence and authentication exist.

The first browser tests caught a useful integration lesson: a server's internal URL can differ from the browser's public host. Origin checks must validate the public address without accepting foreign origins. Another test caught an examples route being registered on the default unavailable API; it now appears only under explicit local preview configuration. Existing crypto and default-unavailable behavior remain regression-tested.

Trivia answers are checked by the Next.js server. The question catalog omits answer keys, and submitting a claimed score is rejected. Lesson completion, quiz first-attempt scores and watchlist symbols persist in browser storage only. That is convenient practice progress, not authenticated account evidence; it can be cleared or edited. The candle exercise is explicitly unscored browser learning.

### Exercise: use, inspect, refresh

In the NEW practice website, calculate the default EURUSD partial exit: gross 8 USD, original risk 20 USD, 0.06 lots remaining. Change exit lots to 0.11 and observe validation rather than an invented result. Check that no Save button exists. Then complete a lesson, answer a quiz and refresh: learning progress should return, while no financial preview was saved. Explain why persisting a learning checkbox is different from accepting a financial trade.

You learned frontend/server boundaries, typed financial results, explicit release selection, regression testing, browser storage versus trusted records, and the difference between Vercel frontend hosting and durable financial persistence. No normal journal, preserved backup, existing practice data or database migration was changed by this delivery.
