# Path B: pinned Python release specification

Specification: `local-python-release-spec-v1`. Prepared 2026-10-24. **P1 design, not an installed or registered release.** Normative requirements apply after the [policy amendment](path-b-local-calculation-policy.md) is signed off and its implementation is separately authorized. No downloads, artifact creation or calculation execution are performed by this document.

## 1. Release unit and exact identities

A local release consists of a private, immutable-by-policy calculator payload, a canonical release manifest, a private approval-registry entry and retained reconstruction materials. It uses an explicitly approved installed CPython interpreter. A copied `.venv` is not a portable release artifact; do not rely on moving it to reproduce an environment.

The payload is a ZIP archive containing only allowlisted calculator/schema/canonicalizer/worker code, required dependency files and their inventory. It MUST NOT contain the entire repository, journal data, tests with private artifacts, environment files, credentials, signing keys or `.vscode/`. Include only the verified import closure needed by the pure CFD engine, not `app.main`, database configuration or a fixture importer. A deterministic packer uses sorted relative paths, fixed file metadata and explicit permissions. Zip extraction rejects absolute/drive paths, traversal, duplicate names, links/reparse points, excessive expanded size and files absent from the inventory. No archive is produced in P1.

Identity rules are distinct:

| Name                         | Exact meaning                                                                                                     |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `release_id`                 | Human label, e.g. `cfd-local-personal/1.0.0`; never sufficient to select bytes                                    |
| `payload.archive_sha256`     | SHA-256 of retained ZIP bytes; manifest is outside this archive                                                   |
| `build_sha256`               | SHA-256 of canonical UTF-8 JSON bytes of the complete `build` object defined below                                |
| `release_manifest_sha256`    | SHA-256 of canonical UTF-8 JSON bytes of the complete software release manifest; it contains no self-digest field |
| `release_digest`             | `sha256:` plus `release_manifest_sha256`, resolving exactly one registry entry for `local_personal`               |
| Ledger `engine_build_sha256` | The 64 lowercase hex `build_sha256`, **not an OCI digest** for this schema                                        |
| Ledger `manifest_sha256`     | Hash of the per-revision evidence envelope defined in section 7, not the software release hash                    |

`build` includes the payload hash, interpreter identity, dependency inventory, contracts, policies and verification fixtures. Changing any build field creates a new build hash. A changed release label/audit time also creates a new manifest hash, even if build bytes are unchanged. Duplicate aliases do not imply interchangeable approval. Every digest is 64 lowercase hex characters; full digest references add `sha256:`. A source Git SHA is provenance, not the build digest. No hash input includes the field that would contain its own hash. Qualification reports identify the tested payload/runtime/policies, not the final build/manifest hashes that depend on the report. Keep reports outside the payload; otherwise including the report hash could create a circular identity.

## 2. Manifest structure

Strict root object; unknown/missing fields, duplicate keys, JSON floating numbers, invalid timestamps and unsupported versions are rejected. Required fields:

| Field              | Type and required value/meaning                                                           |
| ------------------ | ----------------------------------------------------------------------------------------- |
| `schema_version`   | Literal `ava-local-python-release-v1`                                                     |
| `release_id`       | ASCII label, 1–100 characters, reviewed rather than interpreted as a path                 |
| `profile`          | Literal `local_personal`                                                                  |
| `execution_kind`   | Literal `host_pinned_python`                                                              |
| `approval_scope`   | Literal `local_personal`; approval purposes are in the registry, not self-authorized here |
| `signature_status` | Literal `unsigned`; no fake signature/key fields                                          |
| `created_at`       | UTC `YYYY-MM-DDTHH:mm:ss.ffffffZ`; software-release metadata, not financial cutoff        |
| `build`            | Strict descriptor below                                                                   |

Required `build` fields:

| Field                   | Required contents                                                                                                                                                                                                                                      |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `descriptor_version`    | `ava-local-python-build-v1`                                                                                                                                                                                                                            |
| `source`                | `{repository_id:"ava-cryptolab", commit:<full Git SHA>, calculator_tree_sha256:<digest>, dirty:false}`; release source must match committed reviewed files, not arbitrary working-tree edits                                                           |
| `platform`              | `{os:"windows", architecture:"amd64", qualification_os_build:<sanitized build string>, compatibility_policy:"exact-recorded-environment-v1"}`                                                                                                          |
| `python`                | `{implementation:"CPython", version:<exact patch>, cache_tag:<actual tag>, executable_sha256:<digest>, runtime_inventory_sha256:<digest>, abi_tag:<actual ABI>}`                                                                                       |
| `payload`               | `{format:"zip", archive_sha256:<digest>, archive_bytes:<positive integer>, expanded_bytes:<positive integer>, files_inventory_sha256:<digest>, worker_entry:"worker/preview.py"}`                                                                      |
| `dependencies`          | Sorted array of `{name, version, origin_kind, distribution_metadata_sha256, installed_files_sha256, retained_artifact_sha256}`; exact versions, one per normalized name                                                                                |
| `contracts`             | `{engine_id:"cfd-position-v1", input:"cfd-position-v1", result:"cfd-position-result-v1", risk:"cfd-risk-anchor-v1", snapshot:"instrument-specification-v1"}`; snapshot token names the existing v1 hash algorithm, not a rewritten snapshot JSON field |
| `canonicalizer_version` | `local-personal-json-v1`                                                                                                                                                                                                                               |
| `policy_version`        | `local-personal-incurred-once-v1`                                                                                                                                                                                                                      |
| `decimal`               | Exact context in section 4                                                                                                                                                                                                                             |
| `limits`                | `{input_bytes:4194304, output_bytes:33554432, stderr_bytes:65536, execution_seconds:10, queue_wait_seconds:2, active_workers:1, queued_requests:2, api_seconds:30}`                                                                                    |
| `supported_modes`       | `{"forex":["forex"],"cfd_linear":["metals","indices","energy","equities","other"],"cfd_index":["indices"]}`; capability does not assert actual broker support; P2 UI is narrower                                                                       |
| `qualification`         | `{golden_set_sha256:<digest>, expected_results_sha256:<digest>, report_sha256:<digest>}` referencing retained synthetic evidence                                                                                                                       |

All digest placeholders above are type descriptions, **not executable example values or approvals**. A concrete manifest must contain actual verified values; an incomplete template cannot enter the registry. No production signing keys are needed for this unsigned profile.

Initial artifact-validation bounds: manifest at most 1 MiB, each inventory at most 4 MiB, payload ZIP at most 128 MiB, expanded payload at most 256 MiB and at most 20000 files. Reject oversized manifests/archives before unbounded parsing/extraction and enforce both declared and measured expanded sizes. These are local-profile qualification limits, not installation estimates. A necessary increase requires review rather than disabling checks. Qualification must measure temporary copies/free space before preparation; the old WSL storage budget is not a requirement for Path B, and no cleanup is authorized.

Interpreter identity MUST cover the executable, runtime DLLs, standard-library code/data actually exposed to the worker, ZIP libraries and native extensions such as Decimal's extension, using a sorted relative-file inventory. The runtime inventory stores each relative path, byte length and file SHA-256. Record the CPython distribution/version and bootstrap configuration. Do not include usernames, absolute paths, serial numbers or personal settings in the portable manifest. A local registry resolves the approved installation root privately. Qualification checks the recorded Windows build, interpreter and ABI; mismatches block until separately qualified, not automatically accepted as compatible.

Dependency inventories MUST cover each required distribution's actual importable files and metadata, not merely `pip freeze`. `origin_kind` is `retained_wheel` or `retained_installed_tree`; its retained artifact hash identifies a wheel or separately archived installed tree. Missing wheel archives do not justify a download in P2. Existing reviewed installed files may be retained, with matching file inventories. Rebuilding a native dependency on another OS/ABI is not the same release. Changes to any importable byte require a new release identity and qualification.

Current interpreter/package metadata can inform release preparation, but P1 does not pin or approve the current environment. Do not paste a historical version into a manifest without measuring the actual selected runtime. P2 should first use existing dependencies; a missing required artifact is a blocker, not permission to install software.

## 3. Canonicalization and versioning

`local-personal-json-v1` uses Python JSON serialization with sorted object keys, separators `(',', ':')`, ASCII escaping enabled, no NaN/Infinity and UTF-8 encoding without BOM/newline. Allowed JSON values are objects, arrays, strings, booleans, null and bounded metadata integers. All financial quantities are finite decimal strings; binary JSON floats are forbidden. This is an explicit AVA format, **not a claim of RFC 8785 compatibility**.

Financial normalization uses the existing `cfd_canonical.input_document` semantics as the starting contract: finite fixed-point Decimal strings, remove redundant fractional zeros, normalize signed zero to `"0"`; UTC microsecond timestamps; sort adjustments/conversions by logical ID, broker evidence by evidence ID and rounding definitions by currency. Preserve execution order/ordinals, including equal-time fills. Preserve the immutable snapshot's existing v1 JSON spelling/hash rather than applying new financial normalization inside it. Include all validated defaults and explicit nulls. P2 must qualify this version with independent test vectors; reusing a helper does not itself qualify a serializer.

Result canonicalization normalizes validated typed model output under the same rules, preserving raw versus presentation amounts and unavailable reasons. Array order is contractual; do not sort execution results or silently collapse duplicate events. Calculator results do not incorporate execution wall-clock duration/time, request IDs or approval flags; these belong to the response/audit envelope and must not affect result hashes. Explicit financial `as_of` stays in the result.

Manifest/inventory canonicalization uses the same byte serializer but no financial-model coercion. Inventories sort by portable relative path; reject collisions, duplicate keys and names differing only by Windows case normalization. Hash snapshot documents by their existing algorithm. Exact byte/hash vectors for inputs, results, manifests, build descriptors, snapshot exceptions and negative zero are mandatory before a release is registered.

Version meanings are independent: engine ID is the calculation contract family; release/build digest identifies implementation bytes; policy version names accounting semantics; canonicalizer version names exact bytes; request/result/risk schemas describe data. Any change to one is recorded explicitly. Never reuse an old version label for different semantics or rewrite old evidence to a new serializer.

## 4. Decimal and financial units

The exact calculation context remains `prec=160`, `rounding=ROUND_HALF_EVEN`, `Emin=-999999`, `Emax=999999`, `capitals=1`, `clamp=0`. Traps enabled: `InvalidOperation`, `DivisionByZero`, `Overflow`; other Decimal signals are not trapped. Reset flags for each calculation and never inherit ambient thread precision/flags. The manifest's `decimal` object MUST contain those named fields and the sorted enabled-trap list.

Presentation policy remains supplied/validated per request: each currency has exactly one precision of 0–18 places; rounding is `ROUND_HALF_EVEN` or `ROUND_HALF_UP`; `ratio_places` and `movement_places` are explicit 0–18 integers. No automatic two-decimal assumption for every currency. Persist the complete policy in future accepted input. All arithmetic uses raw amounts; quantization is for display. The release must cover every native/reporting/cost currency needed by the engine.

Preserve existing bounded financial input rules (up to 38 digits/18 fractional places and the field-specific bounds), timezone validation and wire decimal-string limits. Reject nonfinite values, floats and boolean financial values. Unit labels distinguish lots, underlying contract units, price, native/reporting money, pips, ticks and R. Do not reinterpret tick value as pip value. The P2 position engine returns no pips/ticks summary; do not fabricate one in TypeScript. Such an output extension requires its own reviewed schema/tests.

Accounting is `incurred_once` with original-risk anchors, execution timestamps and explicit dated FX. Formula behavior remains the existing engine; the new policy label adds provenance without changing its arithmetic. Native/reporting availability is independent. Broker comparisons retain their explicit tolerance/basis and do not replace calculations. No broker specification, price or rate is inferred.

## 5. Approved local registry and execution checks

Registry schema: `ava-local-release-registry-v1`. This is a private owner-controlled JSON file outside Git, financial databases and release payloads. P2 may place it only within the new process-owned practice workspace; personal persistent placement requires later approval. It stores `registry_version`, monotonically increasing `generation`, `entries` and append-only `decisions`. No secret is required; filesystem access is the local trust boundary, not cryptographic publisher authentication.

Each entry has `profile`, `release_digest`, `build_sha256`, `release_manifest_sha256`, `manifest_location`, `payload_location`, `runtime_root`, `state`, `purposes`, `approval_reference`, `approved_at`. Locations are server-private resolved paths, never API fields. `state` is `active`, `retired` or `revoked`; `purposes` explicitly lists any of `preview`, `accept_save`, `replay`. A decision records sequence, release digest, old/new state/purposes, UTC timestamp and owner approval reference. References must be sanitized, not credentials/account names. Retain prior decisions; no silent overwrite of history. P2 entries can authorize **preview only**. A client cannot create/update registry entries.

Before execution:

1. Validate explicit profile/purpose, private registry schema, selected digest and required approval. No default release, network registry, arbitrary image/module path or fixture promotion.
2. Verify manifest canonical bytes and hash; recompute `build_sha256`; match every declared version/contract/policy and permitted limits. Unknowns fail closed.
3. Verify payload archive and extracted inventories, interpreter/standard-library/dependency identities and platform qualification. Reject links, extra executable/importable files and changed bytes. Resolve actual targets before opening the worker; none may be a protected journal/backup/practice path.
4. Start one fixed worker through the approved interpreter using `-I -S -B` and a structured argument list. The reviewed bootstrap explicitly sets only verified code/dependency/standard-library paths; `-S` prevents site/`.pth` startup hooks and `-B` prevents bytecode writes. Do not rely on activation scripts, inherited `PYTHONPATH`, mutable application imports or moving a virtual environment. Verify native-library resolution during qualification; Python flags alone do not control all DLL search behavior.
5. Supply minimal controlled environment and bounded stdin; no database URL, proxy/broker credentials or user's full environment. The pure worker imports no HTTP/DB clients, does no network lookup and receives no database handle. This is an application rule, not an OS network denial guarantee.
6. Enforce streaming output/stderr/deadline/queue limits and cleanup of only the owned worker. Reject extra stdout, unknown fields, invalid numeric units, mismatched request/snapshot/release identity or unavailable schemas. The API owns provenance; do not trust approval claims emitted by a worker.
7. Reverify execution-closure hashes and approval generation before publishing a result. If bytes/approval changed, withhold it. This reduces accidental races; it cannot defeat a malicious same-user process capable of replacing and restoring files between checks.

The proposed subprocess adds no service, new dependency or installation. Its purpose is a killable calculation boundary and a verified import closure. It does not enforce container-equivalent memory, filesystem or network isolation. If the worker cannot safely meet limits or resolve verified dependencies on the existing interpreter, stop; do not silently switch to an in-process or unpinned calculator.

## 6. Response provenance and unavailable states

P2 MUST introduce explicit versioned status/preview responses because today's `CfdPreviewResponseV1` permits only `approved_container` and today's status literals declare execution unavailable. Do not broaden old literals and imply historical responses meant something else. Proposed response schema: `cfd-preview-response-v2` with:

| Field                                      | Local preview value                                                                                  |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| `saved`, `can_create`                      | `false`, `false`                                                                                     |
| `position_reference`, `result`             | Original draft reference; validated existing position-result/unavailable union                       |
| `execution_kind`, `profile`                | `local_personal`, `local_personal`                                                                   |
| `approval_scope`, `approved_release`       | `local_personal`, `true` only after verified preview-purpose approval; not signed-container approval |
| `release_digest`, `engine_build_sha256`    | Manifest digest reference; local build-descriptor hash                                               |
| `signature_status`, `accepted_calculation` | `unsigned`, `false`                                                                                  |
| `input_provenance`                         | `synthetic_example` or `user_supplied_unverified`; not broker authentication                         |
| `broker_authenticated`                     | `false`                                                                                              |
| `historical_replay`                        | `not_run`                                                                                            |

Status schema `cfd-status-v2` reports the selected profile, execution capability, preview availability and explicit blocked reasons; `can_create=false`. The existing v1 behavior remains for the unselected/unavailable B3A app. Reuse `CfdPreviewCommandV1` financial fields initially: on the explicitly local server, optional `release_digest` must match its selected local manifest digest; on an OCI server its meaning remains the OCI profile's documented reference. No request-supplied profile/path/manifest is accepted. Version/profile context must be unambiguous in documentation and responses.

Worker success is not accepted evidence. No ledger receipt, preview-to-save token or broker-authentic claim is created. A later saved record must add distinct locally accepted provenance under P3's reviewed response schema. Runtime errors use the [policy error table](path-b-local-calculation-policy.md#3-execution-and-availability-contract); valid partial financial availability retains reasons/nulls rather than zero substitutes.

The server derives `input_provenance`: only an exact normalized match to its registered, labelled synthetic example may receive `synthetic_example`; edited/unrecognized requests default to `user_supplied_unverified`. The existing command needs no client-controlled authenticity flag. A synthetic account/specification remains visibly synthetic even when its manually changed trade inputs receive the latter label. Neither value permits broker-authentic or accepted-save claims.

## 7. Ledger mapping and reader dispatch

The reviewed ten-table schema stores plain hashes/version strings and canonical TEXT, not an OCI-only SQL type. Proposed future local mapping:

| Ledger field                              | Local meaning                                                                                                        |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `engine_id`                               | Existing `cfd-position-v1`                                                                                           |
| `engine_build_sha256`                     | Local `build_sha256` from section 1                                                                                  |
| `policy_version`                          | `local-personal-incurred-once-v1`                                                                                    |
| `canonicalizer_version`                   | `local-personal-json-v1`                                                                                             |
| `manifest`, `manifest_sha256`             | Complete canonical `ava-local-calculation-evidence-v1` envelope and its hash; embeds the unchanged software manifest |
| `canonical_input`, `input_sha256`         | Reconstructed normalized request and canonical hash                                                                  |
| `canonical_result`, `result_sha256`       | Preserved typed result and canonical hash                                                                            |
| `snapshot_sha256`, `original_risk_sha256` | Existing unchanged anchor algorithms                                                                                 |
| `calculated_at`                           | Actual UTC execution audit time, excluded from the result hash                                                       |

No new table or migration is proposed for P2. For P3, this is a **compatibility hypothesis supported by source inspection**, not an executed local-save rehearsal. Enforce existing hash lengths, version-field lengths, row/parent relationships, triggers, timestamps and evidence size limits. There is no `source` column on `cfd_revisions`; do not invent one or overload the root's immutable source with later revision approvals.

Instead, define the per-revision stored envelope as a strict object with exactly `schema_version:"ava-local-calculation-evidence-v1"`, `software_release:<complete unchanged release manifest>`, `release_manifest_sha256:<software hash>` and `execution:<object below>`. The envelope's entire canonical bytes produce the ledger's `manifest_sha256`. The software hash and local `build_sha256` are independently recomputed from its embedded release. This avoids a circular hash and preserves the same software identity across executions.

`execution` has exactly `profile:"local_personal"`, `execution_kind:"host_pinned_python"`, `purpose:"accept_save"`, `release_digest`, `build_sha256`, `signature_status:"unsigned"`, `registry_generation:<positive integer>`, `approval_reference:<sanitized string>`, `approved_at:<UTC timestamp>`, `executed_at:<UTC timestamp matching calculated_at>`, `input_provenance:"user_supplied_unverified"`, `broker_authenticated:false`. A test dataset may instead use `input_provenance:"synthetic_example"`; it must never be presented as personal accepted production evidence. These are historical local approval observations, not cryptographic attestations. No preview envelope may claim `purpose:"accept_save"`. Execution metadata stays out of the financial result hash.

P3 MUST prove the typed envelope fits existing manifest TEXT limits, sealing/hash checks and round-trip reconstruction. It does not need a nonexistent per-revision provenance column. If compatibility tests reveal a constraint that cannot safely represent it, request a separately reviewed additive migration; **never edit 0004**.

Known incompatibilities to fix only in later authorized code:

- `cfd_api.py` deliberately returns 503 even when a provider returns; P2 needs a new authorized success branch plus versioned response/status contracts.
- `cfd_runtime.py` contains only the unavailable provider; it must remain the default and must not acquire a fallback.
- `cfd_integrity.py` currently accepts only the exact synthetic manifest and checks fixture-specific build/hash correspondence. It cannot verify local accepted records today.
- `cfd_read_codec.py` is explicitly synthetic-only. Create a separate versioned local codec/verifier and a strict dispatcher; never relabel that codec or relax fixture checks.
- Current read provenance models are synthetic-only and need a separately reviewed locally accepted response variant in P3. P2 must not claim those GET routes already support real local records.

Future B3B-R-derived reads dispatch by recorded manifest/canonicalizer/policy schema. The local verifier checks account/snapshot relationships, seals, original risk, normalized child reconstruction, exact canonical input/result/manifest hashes, release build-descriptor correspondence and acceptance-provenance consistency. It checks stored release identity without needing to execute or reinstall that release. Report historical approval separately from current trust/revocation. Unknown schema withholds values as `historical_schema_unavailable`; corruption as `integrity_failure`; no silent repair/recalculation.

Synthetic fixtures keep `accepted_release=false`, their exact old manifest, original hashes and synthetic verifier. Future OCI evidence keeps its original OCI digest/signature interpretation. No existing record is promoted, reassigned or rewritten.

## 8. Retention, replay and tamper limits

Retain every referenced manifest, payload archive, inventories, interpreter distribution/reconstruction material where legally retainable, dependency artifacts, qualification vectors, canonicalizer/verifier source and registry decisions. Maintain two verified private copies, one independent of the working drive, before accepting personal persistent records. Locations/capacity and restoration require later approval; the R2A report is retained unchanged and does not authorize cleanup. P2's temporary release registration is explicitly disposable and cannot promise long-term historical availability.

Replay requires separate authorization, matching historical artifacts/runtime and the recorded financial input, including dated FX/stop/risk/rounding. Reconstruct from normalized rows, verify input hash, execute the matching release and compare the entire canonical result hash. Keep runtime audit metadata outside the comparison. Do not rebuild missing dependencies from the internet or substitute current engine bytes. On mismatch retain diagnostics and original evidence; never overwrite the historical result.

Distinguish `not_run`, `historical_runtime_unavailable`, `historical_schema_unavailable`, `historical_release_unapproved`, `integrity_failure`, `replay_mismatch` and a genuinely tested `verified_match`. No replay capability is implemented or verified in P1/P2. A valid GET means stored evidence verified, not computation reproduced. Exact future restoration is not guaranteed by a ZIP, lockfile or version number.

Hashes detect mismatches against recorded expectations; registry approval establishes local owner intent. Neither proves a broker supplied the data, prevents replacement of both bytes and expectations by a privileged attacker, nor proves financial correctness. Golden tests, independent expected arithmetic, actual redacted statement reconciliation and honest unavailable states remain necessary. OS updates/security fixes may invalidate an old environment qualification; preserve evidence rather than disabling host security to reproduce it.
