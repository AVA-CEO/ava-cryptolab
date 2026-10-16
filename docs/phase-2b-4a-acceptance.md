# Milestone 2B.4A — user-reported manual acceptance

Acceptance recorded: **2026-10-17, Africa/Lagos**. Milestone status: **accepted and closed by the owner**.

The owner reports completing all eight scenarios in the isolated Accounts practice workspace at `http://127.0.0.1:3200/accounts`. The values were synthetic teaching examples, not verified Bybit specifications. These are **user-reported manual observations**, not tests executed or independently witnessed by Codex.

| #   | Scenario                                                            | Expected behavior                                                                                                                          | Owner-reported outcome |
| --- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------- |
| 1   | CFD practice account creation                                       | Create an MT5 CFD practice account with explicit broker/server/currencies and display its identity.                                        | PASS                   |
| 2   | Cryptocurrency futures practice account creation                    | Create a separate crypto account with explicit USDT currencies and a compatible platform.                                                  | PASS                   |
| 3   | USDJPY specification registration                                   | Save the supplied synthetic forex specification with explicit lots, tick/pip sizes, contract size and native profit currency.              | PASS                   |
| 4   | XAUUSD specification registration                                   | Save the supplied synthetic metals/linear-CFD specification without inventing missing pip values.                                          | PASS                   |
| 5   | Specification review, refresh persistence and account compatibility | Review stored identities/specifications, retain them across refresh within the practice session, and show only compatible catalog records. | PASS                   |
| 6   | Immutable USDJPY version history and duplicate prevention           | Keep both recorded versions unchanged; repeat submission of identical specification content does not create another version.               | PASS                   |
| 7   | Invalid specification rejection                                     | Reject incompatible or invalid inputs with useful feedback while retaining existing valid history.                                         | PASS                   |
| 8   | Desktop/mobile, themes and keyboard navigation                      | Remain usable on desktop and a 390px viewport, in light/dark themes and with keyboard controls.                                            | PASS                   |

**Result: 8 of 8 manual acceptance scenarios passed, as reported by the owner.** This does not add eight cases to the automated suite. The previously measured automated baseline remains **478 backend passes and 14 desktop/mobile browser passes**; no new automated run is claimed by this acceptance report.

The owner formally accepts and closes 2B.4A. Commit `a00860a` was previously pushed with authorization; its [GitHub Actions run](https://github.com/AVA-CEO/ava-cryptolab/actions/runs/38973742171) passed both `api` and `web`. Repository privacy was verified during that push task, not newly inferred from these manual results.

Acceptance covers the local practice Accounts scope only. It does not authorize normal-journal management, historical assignment, CFD trade persistence, migration `0004`, broker access or deployment. **2B.4B remains design review only and implementation is not authorized.**

See the [2B.4A scope and technical validation](phase-2b-4a.md) and [2B.4B design review](phase-2b-4b-design-review.md).

Closure-documentation verification: formatting and Git whitespace checks passed; all 56 relative link targets in the nine reviewed documents exist. Read-only fingerprints of the normal database and both verified backups matched the private baseline. No tracked application/model/calculator/schema/migration files changed, and no migration 0004 file was created. No application regression suite was rerun for this documentation-only closure. The pre-existing untracked `.vscode` folder was left untouched and excluded from the documentation commit.
