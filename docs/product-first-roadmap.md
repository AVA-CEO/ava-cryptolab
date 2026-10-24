# Product-first roadmap: Path B

Prepared 2026-10-24. **Path B is the owner's chosen direction. P1 documentation only is authorized in this task.** P2 implementation, local release activation, CFD saving, replay, normal-journal migration, broker integration and deployment require their own approvals. No further audit or Path A/Path B decision is needed.

Product goal: **Analyse. Learn. Trade Smarter.** Deliver a premium purple crypto/forex/metals journal, clear analytics, useful Trading IQ and engaging education. Keep green for profits/success and red for losses. Every implementation milestone ends with a visible workflow and owner manual acceptance, separately recorded from automated tests.

## 1. Preserve and reuse

| Completed work                                           | Reuse / boundary                                                                                               |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Phase 1/2 crypto journal, charts, CSV and screenshots    | Keep working; do not replace with mockups or change crypto formulas                                            |
| Trading IQ rules                                         | Extend eligible data later; retain sample thresholds and honest insufficient-evidence messages                 |
| Accounts practice workspace and immutable specifications | Reuse contracts/validation and UI conventions; do not upgrade its existing database/session                    |
| Separate CFD engines                                     | Reuse `calculate_position` for one entry/multiple exits and current rounding/FX/cost rules                     |
| B2 ten-table schema, constraints and guards              | Keep frozen migration 0004 and all approved protections                                                        |
| B3A boundary and B3B-R reads                             | Preserve default unavailable mode and synthetic-only reader; add new behavior only through authorized versions |
| R1/R2A research                                          | Preserve as historical work; Docker/WSL installation is not on Path B's critical path                          |

The original [B1 design](phase-2b-4b-design-review.md), [B1 addendum](phase-2b-4b-b1-addendum.md), [B2 report](phase-2b-4b-b2.md), [B3A](phase-2b-4b-b3a.md) and [B3B-R](phase-2b-4b-b3b-r.md) remain historical scope/approval records. The [Path B policy](path-b-local-calculation-policy.md) and [release specification](path-b-python-release-spec.md) define the proposed amendment, not retroactive execution authorization.

## 2. Delivery milestones

| Stage                                   | Visible outcome                                                                                      | Financial/engineering scope                                                                                                         | Acceptance gate                                                                                     |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **P1 — documentation and sign-off**     | Accurate README, policy/release specification, clear development plan                                | No application changes or execution                                                                                                 | Owner reviews the actual documents; implementation is separately authorized                         |
| **P2 — interactive preview**            | Responsive purple forex/metals form, explicit synthetic examples, native/reporting results and costs | Verified local preview release, no persistence, no current-rate fetches                                                             | Manual arithmetic, validation, mobile/theme/accessibility and no-write tests                        |
| **P3 — safe saving and retrieval**      | Create, reopen and browse CFD positions in a NEW disposable workspace                                | Transactional create/idempotency; versioned local verifier and provenance; create/read only initially                               | Refresh/retry/account isolation, rollback and saved-evidence verification                           |
| **P4 — everyday journal**               | Add partial exits; correct records with reasons; search/filter/export                                | Immutable revisions, optimistic concurrency, supported void/replacement workflows; no destructive history rewrite                   | Partial-to-final accounting, duplicate fees, simultaneous edits, correction/export checks           |
| **P5 — analytics and Trading IQ**       | Dedicated insights workspace, account views, performance charts/scatterplots                         | Separate crypto/CFD cohorts; explicit FX aggregation; retain minimum samples/coverage                                               | Charts reconcile to selected records; no currency blending or unsupported conclusions               |
| **P6 — persistent personal acceptance** | Approved durable personal CFD journal, account/specification workflow, recovery guide                | Explicit new dataset/location approval, backup/restore, independent artifact retention and actual redacted statement reconciliation | Owner approves persistent use only after disposable acceptance; no implied normal-journal migration |

P3 can create an open, partial or closed position with all supplied exit history. P4 adds changes to an already saved position. The existing engine supports both, but their persistence/UI authorizations are distinct. P6 must bring account creation/specification management into the approved durable workflow rather than require hand-editing a database. Existing crypto trades are not automatically assigned to accounts.

P5 starts with separate account and currency panels. Monetary combined totals require a declared target currency, conversion method/timing/source and complete coverage; disclose exclusions and do not silently add USD, USDT, JPY or other currencies. A journal-derived balance is not a broker-reconciled balance; deposits, withdrawals and mark-to-market exposure need separate explicit support. Dimensionless R comparisons still require compatible definitions and disclosed samples.

## 3. Education alongside functionality

- **P2:** concise explanations next to lots, contract size, pip/tick units, leverage and original risk. Add three unscored interactive knowledge checks using clearly synthetic examples. No XP, saved progress or claim of server-validated quiz results yet.
- **P3/P4:** deliver a small beginner lesson path and a server-validated quiz slice as a separately bounded submilestone. Teach money/crypto basics and journal mechanics; keep content curated and independent of AI services. Manual acceptance includes wrong-answer explanations and server rejection of forged answers.
- **P5:** grow the academy toward the original five levels and starter trivia bank; keep quiz progress separate from trading performance. Add streaks/XP only after answer/progress persistence works.
- After the usable journal: deliver a focused live screener/watchlist slice, provider source/timestamp/cache/error handling, then candlesticks and meaningful market scatterplots. Do not wait for runtime research to resume these product modules.

Small lessons can ship beside journal milestones without making them a prerequisite for saving. Advanced minigames, account synchronization and container replay remain later options, not blockers for the first product.

## 4. P2: concrete implementation proposal

### Reuse and intended files

These are proposed future edits/creations, **not files implemented by P1**.

| File/module                                                                | P2 role                                                                                      |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `services/api/app/analytics/cfd_positions.py`                              | Reuse unchanged `calculate_position`; no TypeScript PnL engine                               |
| `services/api/app/schemas/cfd*.py`, `financial.py`, `instrument.py`        | Reuse financial inputs, result/unavailable types and rounding contracts                      |
| `services/api/app/services/cfd_preview.py`                                 | Reuse `bind_preview` trusted account/snapshot/scope validation                               |
| `services/api/app/services/cfd_canonical.py`                               | Reuse/qualify financial normalization; keep snapshot fingerprint algorithm                   |
| `services/api/app/api/cfd.py`, `schemas/cfd_api.py`                        | Add approved local branch and new response/status versions while preserving default Option A |
| Proposed `services/api/app/schemas/cfd_local_release.py`                   | Typed local manifest/registry/provenance contracts                                           |
| Proposed `services/api/app/services/cfd_local_release.py`                  | Offline artifact/registry verification; no arbitrary paths from HTTP                         |
| Proposed `services/api/app/services/cfd_local_runtime.py` and fixed worker | Bounded verified Python invocation; no saving/replay/fallback                                |
| `services/api/app/core/cfd_settings.py`, `app/cfd_practice.py`             | Explicit profile/release/purpose wiring, disabled by default                                 |
| Proposed `services/api/scripts/cfd_preview_practice.py`                    | New explicit fresh-workspace preview runner; reuse registered target guard and provisioning  |
| `services/api/app/services/cfd_samples.py`                                 | Extend NEW synthetic catalog with EURUSD; never edit a running/retained session              |
| Proposed `apps/web/src/app/cfd-preview/page.tsx`, `features/cfd-preview/*` | Form, results, learning checks and local TypeScript response contracts                       |
| Proposed `apps/web/src/app/api/cfd-preview/route.ts`                       | Server-only proxy to the exact authorized local practice API; no fallback URL                |
| Existing button/form/theme/layout utilities                                | Reuse purple design, validation, responsive components and formatting                        |
| Backend/Playwright tests and docs                                          | New disposable cases plus existing crypto regressions; update learning journal               |

Only add the small worker/release boundary needed for exact imports, cancellation and bounded output. Use existing Python/Node dependencies. No Docker, WSL, package installation, broker SDK, new database service or generic plugin architecture. Missing packages/artifacts require reporting, not downloads.

### Execution and transition from 503

1. New runner creates a fresh process-owned temporary 0004 workspace using existing guards. Explicit provisioning occurs before serving, never automatically during normal application startup. It accepts no caller database path, resume/import flag or inherited normal database target.
2. Existing B3B-R synthetic read fixtures MAY remain as a labelled baseline in that NEW database. P2 must not modify them through previews. Do not require an empty ledger to prove no writes: compare the actual full baseline. New accounts/specification examples are seeded only during fresh provisioning.
3. Prepare a local calculator payload from reviewed committed source and existing verified dependencies. Measure the selected interpreter/import closure, qualify golden vectors, generate actual digests and register a preview-only release following the approved specification. If required materials are unavailable, stop; no downloads or unsigned-as-signed claims. Final concrete artifact identity is reviewed before enabling the preview runner.
4. Start only with explicit `local_personal`/preview selection and its registered release. Missing selection, registry approval or valid artifacts keeps the unavailable response. The old B3A runner remains unavailable by default; it must not discover the host engine automatically.
5. Reuse the reference-binding read session, construct validated input, then close that session before worker execution. Invoke the verified release's existing position calculator through the bounded worker. Validate typed output and provenance; do not pass a database connection to the worker.
6. Only the authorized local branch may return `cfd-preview-response-v2`. A valid registered preview can return 200 with calculated/partially unavailable values. Failure does not fall back to another engine. `can_create=false` and `saved=false` always; no POST positions or accepted-read format is added in P2.

Release qualification has a narrow role: prove which existing calculator bytes will run, with correct known outputs. It is not a new container/replay programme. P2 implementation authorization should include preparing/qualifying a preview release; approval of its actual manifest/purpose is still required before activation. Review source and commit implementation only if separately authorized; do not use uncommitted calculator edits as a release.

### Purple preview UI

Run a separate frontend at proposed port **3300**, isolated build output `.next-cfd-preview`, against the fresh CFD API on **8003**. If a port is occupied, stop and ask for an alternative; do not stop an existing process. Keep normal 3000/8000, Accounts practice 3200/8002 and browser regression 3100/8001 untouched. The separate development configuration must not overwrite existing settings.

The server-only bridge validates the exact loopback endpoint and practice header, forwards only the preview contract, disables caching and never falls back to the normal API. This local boundary is not production authentication. Source labels/free text remain escaped; no raw stderr, private paths or financial input logging. Browser values remain decimal strings.

Form inputs:

- Synthetic account and compatible immutable specification selectors, with a collapsible specification/source review. No editable broker rules silently overwrite a snapshot.
- Long/short direction; entry price, lots and timezone-aware time; zero or more exit rows with lots, price, time and stable IDs.
- Original stop, optional planned target and explicit `as_of` cutoff.
- Commission/swap/fee/other adjustment rows: signed amount, currency, occurrence time and source. Explain charge/credit signs; do not double-charge spread.
- Native/reporting policy and explicit FX evidence with direction, observed/applies times, age allowance, source and reference; explicit risk-conversion selection.
- Complete per-currency rounding and ratio precision, shown in an advanced panel with disclosed synthetic presets. Do not hide an assumed conversion rate or broker precision.

Results show state, original/exited/remaining lots, native and reporting gross/net PnL, recognized costs by currency/type, original risk, realized R, raw/rounded values, FX evidence used and unavailable reasons. Show individual exit outcomes and costs recognized through the cutoff. Unrealized PnL stays unavailable under the existing position contract. Estimated broker margin/liquidation and pip/tick movement outputs are not fabricated; explain units using the specification/learning cards. Any later calculated movement output needs a reviewed extension.

Use two clear panels: **Trade inputs** and **Unsaved preview**. Purple is primary; green/red convey positive/negative results; neutral styling denotes unavailable. Include loading, empty/error states, keyboard focus, small-screen stacking and dark/light themes. Changing an input marks the old result stale until recalculated. No Save button implying availability, hidden autosave, localStorage/IndexedDB draft persistence or financial-data analytics events. Optional broker comparison evidence is not required by the initial UI; keep the existing contract default empty rather than imply real reconciliation.

### Exact synthetic arithmetic fixtures

All specifications/prices/rates here are fictional teaching inputs, **not verified Bybit rules or live observations**. Supply valid tick/lot grids, event IDs, timestamps, source references and rounding in the test fixtures.

| Example     | Entry / exits / original stop                                        | Declared contract                                                     | Independent expected result, no costs                                                                    |
| ----------- | -------------------------------------------------------------------- | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| EURUSD long | 1.10000; exit 0.04 lots at 1.10200 and 0.06 at 1.10300; stop 1.09800 | Original 0.10 lots, 100000 underlying units/lot, USD profit/reporting | 8 + 18 = 26 USD gross/net; risk 20 USD; 1.30R; no lots remaining                                         |
| USDJPY long | 150.000; exit all at 150.200; stop 149.800                           | 0.10 lots, 100000 units/lot, JPY profit, USD reporting                | 2000 JPY gross/risk; 1R; with explicit fictional 0.005 USD/JPY at each required event: 10 USD gross/risk |
| XAUUSD long | 2000.00; exit all at 2010.00; stop 1990.00                           | 0.10 lots, 100 ounces/lot, USD profit/reporting                       | 100 USD gross/net; risk 100 USD; 1R                                                                      |
| XAGUSD long | 25.000; exit all at 25.200; stop 24.800                              | 0.02 lots, 5000 ounces/lot, USD profit/reporting                      | 20 USD gross/net; risk 20 USD; 1R                                                                        |

EURUSD cost variant: one entry commission -2 USD, exit fee -1 USD and swap -1 USD recognized once gives net 22 USD and 1.10R after both exits. Partial first exit, no costs, gives gross 8 USD, 0.06 lots remaining and 0.40R using original 20 USD risk. Test shorts/losses/breakeven separately. USDJPY native-only variant must retain JPY results/R while USD reporting is unavailable. A missing required explicit-rate reference is a validation error under existing contracts; do not promise it silently calculates reporting. Unsupported mixed-currency coverage retains honest unavailable values.

### Automated validation

- Independent expected arithmetic above; short/partial/open states; precise Decimal strings, rounding ties, zero/missing risk, unsupported modes, incompatible scope, over-closing and invalid timestamp/FX evidence.
- Default-unavailable runner still returns 503; missing/revoked registry, changed source/dependency/interpreter, wrong selected digest, extra files and malformed worker output all fail closed. Use only isolated test doubles for adversarial orchestration where appropriate; successful preview tests also exercise the actual approved local engine fixture.
- Verify both actual SQLAlchemy target registration and rejected normal/arbitrary paths **before connection**, without opening protected files. Test CSRF/local-origin/header/request/rate limits and proxy target rejection.
- Before/after valid, invalid, repeated, timed-out and failed previews, compare row counts AND canonical row inventories for **all ten CFD tables**, plus accounts/specifications/legacy synthetic rows. Keep baseline fixture counts explicit. Record SQL statements: reject INSERT/UPDATE/DELETE/DDL from serving sessions and retain `query_only=ON`. Worker has no database handle/settings/imports. Check no `cfd_requests` receipt, approval-to-save token or financial-body log was created.
- Test no persistence in browser storage and no creation route. Provisioning itself creates the disposable schema/catalog/fixtures before the baseline; it is not a preview side effect. Release registry/worker temporary files are not financial journal saves; never put financial JSON in durable diagnostics.
- Run backend regressions, Ruff lint/format, frontend lint/types/build, repository formatting and desktop/mobile Playwright tests on NEW disposable targets. Preserve crypto expected outputs. Do not claim PostgreSQL or historical replay was tested.

### Owner manual acceptance checklist

1. Start the newly approved practice runner/frontend. Confirm synthetic/local/unsigned/unsaved badges, selected release, `can_create=false` and the correct isolated ports. No normal/prior practice dataset is loaded.
2. Select each EURUSD/USDJPY/gold/silver example and compare results against the table. Expand specifications and explain why contract size changes the result.
3. Use the first EURUSD partial exit, then both exits, then the four-dollar cost variant. Check remaining lots, fixed risk and no doubled commission.
4. Select USDJPY native-only policy: JPY values remain, USD unavailable. Add complete fictional dated conversions under explicit-rates policy and verify reporting; removing required evidence gives a useful validation message.
5. Try negative/over-closing lots, wrong account/specification, invalid stop and an exit before entry. Confirm safe validation with no invented output.
6. Change an input after calculating: old results become stale. Refresh the page: no financial draft or accepted position was saved. Inspect the disposable no-write test receipt rather than opening/editing a database manually.
7. Verify narrow-screen (390px) and desktop layouts, light/dark themes, keyboard navigation, loading/error messages and signed cost labels. Answer the unscored lots/pips/risk checks and read explanations.
8. In a separate fresh test invocation with no approved release selected, verify the 503 boundary. Do not alter files or the registry mid-session yourself to test tampering; use automated adversarial fixtures.

Record these as owner-reported acceptance results only when actually reported. A screenshot, working demo or successful test is not authorization to start P3 or migrate a personal database.

## 5. Approval to begin P2

Requested authorization: **sign off the P1 local-personal policy/release specification and authorize P2 implementation and qualification of preview-only local release artifacts using existing installed dependencies, NEW disposable 0004 workspaces and an isolated purple preview UI.** Keep saving/replay disabled. Review and explicitly approve the measured release manifest/preview-purpose registry entry before user-facing execution. No software installation/download, normal-journal access/migration, existing practice mutation, broker connection, deployment, commit or push is included unless separately authorized.

P1 delivers these three new documents plus README/learning-journal updates. It changes no application capability. P2 code remains unauthorized until the owner approves the request above.
