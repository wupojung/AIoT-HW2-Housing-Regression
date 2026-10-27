# Phase 4 Validation Matrix

**Scope:** static Phase 4 Case Package contracts and examples. Schema checks validate one `modeling.json`; they do not certify research results, cross-file references, package publication, or model readiness.

## Schema samples

| Input | Expected | Evidence / status |
|---|---|---|
| `sample/modeling.unavailable.json` | PASS | empty, honest no-results state |
| `sample/modeling.nonempty.mock.json` | PASS | synthetic nonempty state, MOCK only |
| `../sample/ames-housing/phases/phase-04/modeling.json` | PASS | source-reported staging fixture; schema only, not empirical validation |
| Root `status=VERIFIED` with zero eligible configurations | REJECT | cross-field eligibility check; Bundle Validator **NOT_IMPLEMENTED** |
| Duplicate `configuration_id` / dangling or ineligible default ID | REJECT | Bundle Validator requirement; **NOT_IMPLEMENTED** |
| A detail ref with traversal, external URL, or mismatched configuration directory | REJECT | Safe relative path and identity check; schema pattern plus Bundle Validator; **NOT_IMPLEMENTED** |
| Ref omitted from `package.json.files[]` or hash/size/MIME mismatch | REJECT | Bundle Validator; **NOT_IMPLEMENTED** |
| Two configs with different protocol/track mixed in one comparison chart | REJECT | Bundle Validator/chart policy; **NOT_IMPLEMENTED** |
| Fold task has row IDs or predictions | REJECT | Data safety review; do not add to public Case Package |
| Phase 4 CV record presented as Phase 5 OOF/Holdout | REJECT | Phase boundary / independent review |
| Final Fit private binary or fitted coefficients/scaler included | REJECT | public package safety boundary |

## Package invariants

1. Resolve `package.json.phases.phase4.data_ref`; require its `case_id` to match `case.json` and `package.json`.
2. Validate `modeling.json` against the canonical Draft 2020-12 schema at `docs/design/data-contracts/schemas/phase-04.schema.json`.
3. Enforce unique execution/configuration/chart/task IDs; each configuration references a known execution run and method; default configuration resolves exactly.
   `source_reported_candidate_configuration_id` is informational only; it must never substitute for an eligible `default_configuration_id`.
4. For each non-null configuration detail ref, require a safe case-root-relative path, matching configuration ID, physical file, and matching `package.json.files[]` SHA-256/bytes/MIME.
5. For each chart `points_ref`, require file/ref/hash consistency and matching protocol, track, metric scope, unit, and declared axis semantics.
6. Reconcile task counts/statuses with the source report. Preserve invalid and incomplete tasks. Calculate CV summary values only from explicitly eligible folds and keep CV fold mean distinct from pooled OOF and Holdout.
7. Keep every source-derived but unreviewed value `SOURCE_REPORTED_NOT_VERIFIED` or the enclosing object `PLANNED`; structural parsing or successful execution cannot promote status to `VERIFIED`.
   `final_fit_id` remains null unless independently source-backed; never derive it from `configuration_id`.
8. Reject raw dataset rows, row identifiers, OOF/Holdout predictions, private artifact paths, fitted binaries, coefficients/scaler arrays, and unauthorized external assets.
9. Schema PASS is not publication PASS. A release also requires independent research/data-rights review, complete sealed manifest, and explicit publication approval.

## Current implementation boundary

- Phase 4 modeling root schema: implemented at the canonical shared schema path and versioned `1.1.0`.
- Schema validation applies only to `modeling.json`; schemas/validators for configuration leaf files and chart JSON are **NOT_IMPLEMENTED**.
- Positive empty and synthetic nonempty samples: provided in this folder.
- Cross-file reference, uniqueness, task reconciliation, publication and privacy bundle validator: **NOT_IMPLEMENTED**.
- Targeted local Phase 4 schema validation: **PASS** for the Ames `modeling.json` and both Phase 4 `modeling` samples using the existing shared `validate_schema.py` and the available Draft 2020-12 environment. This does not validate the package index or leaf files. Ordinary CI was not run.
- No modeling or data-generation command is part of this contract.

## One-time read-only audit of the Ames staging snapshot

Audit scope: the Ames package snapshot `sample-r7-phase1-4-p4-consumer-audit` only; no source dataset, model execution, or scientific re-computation. This is a bounded snapshot audit, not a reusable validator and not publication authorization.

| Check | Result | Evidence / boundary |
|---|---|---|
| JSON parsing and package file seal | **PASS** | All 144 package payload files parse as JSON; `files[]` covers all 144 physical non-root files with matching unique paths, SHA-256, byte counts, and MIME. |
| Configuration detail joins | **PASS** | 32 unique configurations; all 128 metadata/fold-task/CV-metric/selected-feature refs exist and match case, execution, configuration, and protocol identity where the leaf carries that field. |
| Chart/config joins | **PASS** | 8 unique chart IDs/refs (including the protocol detail ref), 102 points; all points are `SOURCE_REPORTED_NOT_VERIFIED`, and point configuration/method/params/track/detail refs resolve to the root catalog. Every point targets a `PLANNED` configuration; none targets either `ERROR` configuration. |
| Fold task inventory | **PASS** | 96 unique task IDs and three distinct fold indices per configuration; 91 `COMPLETED`, 5 `INVALID`. The parent execution run remains `ERROR`. |
| Public payload shape scan | **PASS, structural only** | No row IDs, row-level predictions, OOF/Holdout prediction payloads, coefficients/scaler arrays, or absolute private paths were found. This does not clear source licensing, derived-result publication rights, or scientific validity. |
| Task-to-chart reconciliation | **NOT_IMPLEMENTED** | Chart points do not carry included fold task IDs or excluded task IDs/reasons. Existing file-level limitations mention invalid configurations, but a reusable point-to-task reconciliation gate does not exist. Keep charts `PLANNED`; do not recalculate or promote them. |
| Leaf schemas / full Bundle Validator / publication QA | **NOT_IMPLEMENTED** | This audit does not replace Phase 4 leaf schemas, automated cross-file validation, independent research/data-rights review, or release approval. |

`cv-protocol.json.status=SOURCE_REPORTED_VERIFIED_MATCH` identifies a source-manifest/protocol match only. Its `run_status=ERROR`, the package publication state, and every chart's `PLANNED` status remain separate and visible. The current sample is staging-only.
