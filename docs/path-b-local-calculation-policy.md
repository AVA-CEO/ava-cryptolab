# Path B: local personal calculation policy

Policy identifier: `local-personal-policy-v1`. Prepared 2026-10-24.

**Direction chosen: Path B. P1 authorizes documentation only.** This is the precise amendment submitted for architectural sign-off. It does not activate a release, authorize P2 code, permit accepted saves or change any database. Until separately implemented and authorized, existing Option A behavior remains: valid API previews return HTTP 503 `calculation_runtime_unavailable`.

Normative words **MUST**, **MUST NOT** and **MAY** describe requirements for a future implementation, not capabilities already delivered. The [release specification](path-b-python-release-spec.md) is part of this policy. The [product roadmap](product-first-roadmap.md) defines separate implementation gates.

## 1. Amendment scope and precedence

This amendment changes the execution/release requirements in [B1 addendum section 4](phase-2b-4b-b1-addendum.md#4-versioned-release-artifact-and-replay-policy), the corresponding [B1 design](phase-2b-4b-design-review.md), and the runtime assumptions in [B3 readiness](phase-2b-4b-b3-readiness.md) **only for the explicitly selected `local_personal` profile**. Earlier approvals/documents remain historical records. On sign-off, this amendment takes precedence for that profile; it does not retroactively change evidence or authorize implementation.

| Existing rule                                                                                     | Amendment for `local_personal`                                                                                                           | What remains binding                                                            |
| ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Only approved OCI releases may calculate accepted CFD evidence                                    | REPLACED within this profile: an explicitly approved pinned local Python release may execute for an approved purpose                     | No arbitrary code, unapproved release or automatic fallback                     |
| Publisher signature and OCI approval registry are mandatory                                       | REPLACED within this profile: owner-reviewed local registry approval plus artifact/runtime verification; evidence is explicitly unsigned | Hashes are not signatures; local approval is not broker authenticity            |
| `engine_build_sha256` identifies the platform OCI manifest                                        | AMENDED to a version-dispatched identity: local build-descriptor hash for the new local manifest schema only                             | Existing OCI digest meanings and existing evidence bytes do not change          |
| Historical replay runs the recorded OCI image                                                     | AMENDED: local replay requires the original verified Python release/environment; otherwise unavailable                                   | No silent replay using current code or current FX                               |
| Container network/filesystem sandbox is required                                                  | REPLACED within this profile by bounded local execution and an explicit weaker-isolation disclosure                                      | No credentials, network-dependent calculation, arbitrary paths or broker access |
| Immutable risk/specifications, exact inputs, FX, revisions, sealing and transactional publication | RETAINED without relaxation                                                                                                              | All existing B2 database constraints and financial rules                        |
| Default-disabled access and disposable database registration                                      | RETAINED                                                                                                                                 | No normal-journal or existing practice access implied                           |
| GET verifies saved evidence without recalculation                                                 | RETAINED                                                                                                                                 | New accepted formats need a new verifier; synthetic fixtures stay synthetic     |

Signed OCI releases remain a future optional high-assurance profile, not a Path B prerequisite. PostgreSQL and container replay remain UNVERIFIED.

## 2. Explicit selection and authorization

The application MUST default to no calculation profile and no enabled CFD saving. Installing Python, finding a calculator module, receiving a request or detecting a failed container MUST NOT select `local_personal`.

Future P2 starts only through an owner-authorized isolated practice runner. Its explicit options select `calculation_profile=local_personal`, `purpose=preview` and one approved release digest. These are server-side configuration, not client-controlled executable paths. Configuration without a matching private registry approval MUST fail closed. There is no inferred `latest` release.

The registry MUST separately authorize each purpose: `preview`, `accept_save`, or `replay`. Code approval, release registration and runtime capability are distinct. P2 may implement/register only preview capability after its explicit authorization. `accept_save` MUST remain false, with no creation endpoint, throughout P2 even if the release calculates successfully. Replay is not authorized by preview approval.

Permissions are cumulative: implementation authorization + an approved release/purpose + a valid isolated environment + successful verification are all required. A copied matching-named temporary directory, arbitrary database URL or user-supplied manifest MUST NOT satisfy them.

No implementation or release registry is created by P1. Actual patch versions, artifact digests and approval receipts MUST be captured and reviewed during the separately authorized P2 qualification; placeholders in documentation are never approvals.

## 3. Execution and availability contract

Use the existing pure `app.analytics.cfd_positions.calculate_position` and existing validated financial contracts. Do not duplicate formulas in TypeScript. A small fixed-entry Python worker is permitted as the proposed P2 mechanism, subject to implementation approval; it is justified by cancellation/output limits and separation from the API's mutable imports, not by a claim of sandbox security. No broker SDK, new daemon, VM, runtime installation or package download is required by this design.

The worker MUST execute only a verified release and approved interpreter, with structured arguments and bounded JSON over stdin/stdout, never request text in command-line arguments or a shell. It MUST not receive database settings, broker secrets, user profiles, arbitrary import paths or a network data source. Registry resolution determines paths; clients provide only financial data and trusted account/snapshot references. The worker MUST not open a database. Python import isolation is not an OS filesystem/network sandbox.

Proposed initial limits: one active worker, two waiting requests, 4 MiB input, 32 MiB output, 64 KiB sanitized stderr and a 10-second execution deadline after launch. Request queue wait is at most two seconds; launch/verification/execution must fit the 30-second API deadline. If maximum valid inputs cannot fit, fail unavailable and review limits; never silently raise them. Do not claim a Windows process memory cap is enforced without actually implementing/testing one. Requests remain bounded by existing child-count/financial precision limits; no container CPU/RAM promises are inherited.

For a local worker, use isolated/no-site/no-bytecode interpreter startup and only reviewed release imports; details are in the release specification. The process runs with the current user's permissions. It cannot protect against a malicious user, compromised OS or another same-user process rewriting artifacts. Document this limitation; do not describe `venv`, `-I`, hashes or a subprocess as a container-equivalent sandbox.

The API MUST verify artifacts before execution, validate the typed result, recheck the execution closure before releasing a result, and discard results if identities changed. No automatic repair, installation, download, profile switch or host fallback is allowed.

| Condition                                              | Required behavior                                                                                      |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| No profile/release/runtime capability                  | 503 `calculation_runtime_unavailable`; no calculation/save                                             |
| Release not approved for selected purpose or revoked   | 503 `calculation_release_unapproved`; no execution                                                     |
| Artifact/interpreter/dependency mismatch               | 503 `calculation_release_integrity_failure`; no returned financial values                              |
| Deadline/output/process failure                        | 503 `calculation_execution_unavailable`; no partial successful result                                  |
| Worker queue full                                      | 429 `calculation_capacity_exceeded`; bounded retry guidance                                            |
| Invalid request/scope                                  | Existing 400/404/422 semantics; safe errors, no account leakage                                        |
| Supported engine returns a financial unavailable value | Typed unavailable result/reason, not an invented number; missing FX need not erase valid native values |

These proposed new error identifiers need contract tests in P2. They do not exist today. An integrity verification failure is a stop condition for the affected release, not permission to execute another release.

## 4. Accounting rules retained

- Decimal inputs/outputs MUST remain strings across HTTP and storage. Retain the existing 160-digit calculation context and explicit presentation rounding. Browser chart numbers are display-only.
- Only declared supported calculation-mode/category combinations are permitted. Crypto calculations remain separate and unchanged. Do not invent contract sizes, ticks, pips or broker specifications.
- Freeze original account/specification, direction, entry, original lots, stop and original-risk basis when a position is accepted. Later exits MUST NOT replace that denominator with remaining quantity or a moved stop. A changed original fact requires the reviewed correction/replacement workflow, not an overwrite.
- Retain `incurred_once`: costs/credits are recognized once at their occurrence through the explicit `as_of`; costs are not charged again for each partial exit or historical revision. Charge is a negative adjustment; credit is positive. Preserve original currency and occurrence time.
- Retain dated, explicitly directed FX evidence and age limits. No USD/USDT equivalence, invented inverse rate or current-rate substitution. Entry-time risk conversion remains distinct from exit/cost conversions.
- Native R MAY be available without reporting FX when native net and positive original native risk are available. For example, USDJPY profit/risk can remain in JPY while USD reporting is unavailable. Mixed-currency costs can make native net/R unavailable under the existing engine; do not extend its conversion rules silently.
- Leverage MUST NOT multiply execution-price PnL again. Actual entry/exit prices already reflect execution spread; do not subtract it twice. Estimated margin is not broker margin or liquidation evidence. The existing position result does not compute a broker margin/liquidation requirement.
- Preserve raw and rounded amounts separately; calculate ratios from raw amounts. Missing stop/zero denominator means unavailable R. No assumed unrealized PnL without supported valuation inputs.
- Broker-reported amounts remain separate comparison evidence, never replacements for calculated results. Synthetic tests are not broker reconciliation.

## 5. Preview and accepted-save separation

Preview MUST be labelled hypothetical/unsaved, with `execution_kind=local_personal`, local approval scope, unsigned release provenance and `can_create=false`. Real manual inputs do not become broker-authenticated because they calculate. Seeded examples MUST be labelled synthetic. Preview writes no root, revision, event, cost, FX, result, head, evidence or request-receipt ledger rows; telemetry MUST NOT contain financial bodies or create hidden persisted previews.

Future accepted saving needs separate P3 authorization, reviewed canonicalization and local evidence verification. Creation MUST revalidate trusted identities, execute the approved save-purpose release independently of browser totals, then atomically persist normalized rows, immutable original risk, canonical input/result/release manifest, hashes, seal, published head and idempotent receipt. Never hold a write lock during worker execution. Recheck relevant identities and expected state inside the transaction. Any failure rolls back all staged rows.

Later revision operations require their own authorization and optimistic concurrency. Same account/key/payload returns the original receipt; changed payload under the same key is a conflict. GET remains read-only and returns preserved values after verification, never rerunning the calculator.

## 6. Ledger compatibility and evidence coexistence

Reuse all ten approved tables. The local manifest schema supplies the interpretation of build hashes; no rows or old manifests are reclassified. The reviewed `cfd_calculations` columns can hold the proposed engine, policy/canonicalizer identifiers and canonical local manifest. A database hash-shape check does not itself verify financial truth or software approval.

The exact identity mapping and known API/verifier incompatibilities are specified in the [release specification](path-b-python-release-spec.md#7-ledger-mapping-and-reader-dispatch). P2 needs no schema change because it saves no evidence. P3 MUST demonstrate round-trip compatibility on new disposable 0004 databases before any claim that the schema suffices. If a constraint blocks correct evidence, stop and propose an additive migration separately; never edit frozen 0004 or weaken triggers to make tests pass.

The existing synthetic verifier and manifests MUST remain unchanged in meaning. A future dispatcher selects by the recorded schema/version, not the current preferred profile: synthetic fixtures use their existing verifier; local records use the new local verifier; future OCI records use their independently qualified verifier. Unknown formats fail unavailable. Missing hashes, invalid seals or normalized-row mismatches withhold values; no silent repair.

## 7. Historical evidence, replay and upgrades

Retain canonical inputs/results, specification/account/risk anchors, accounting/canonicalizer versions, original release manifest and approval history. A GET may verify these without executing software. Report stored integrity, release trust, broker provenance and replay as separate properties.

Replay MUST use the original release, retained dependencies/interpreter identity and historical financial evidence. It compares the full canonical result hash, excluding execution audit timestamps. It never changes saved results. Missing artifact/runtime yields `historical_runtime_unavailable`; unknown serializer yields `historical_schema_unavailable`; blocked release yields `historical_release_unapproved`; mismatched evidence yields `integrity_failure`; an executed result mismatch yields `replay_mismatch`. No such state authorizes a newer-engine replacement.

Local replay is best-effort within the recorded supported environment, not a guarantee of bit-identical Windows restoration indefinitely. Successful replay applies only to the tested release/input/environment. New releases require old/new synthetic golden comparisons, documented financial differences and separate purpose approvals. Revocation blocks future execution but does not erase evidence or turn old recorded approval into a current approval. Keep referenced artifacts and trust history; no automatic pruning.

## 8. Approval requested after P1

Review this amendment and the release specification, then separately authorize **P2 local-personal nonpersistent practice preview implementation only**, including qualification/registration of a concrete preview-purpose release and the isolated Next.js interface. That approval must not include saving, replay execution, normal-journal migration, broker integration, installations or deployment. Retaining the unavailable boundary until P2 verification passes is mandatory.
