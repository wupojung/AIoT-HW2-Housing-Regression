# RegScope Phase 4 — Modeling & Experiment Package Contract v1.1

> Defines the static Phase 4 payload inside a Case Package. The authoritative modeling-index JSON Schema is [`docs/design/data-contracts/schemas/phase-04.schema.json`](../../../design/data-contracts/schemas/phase-04.schema.json); this folder does not duplicate it. This contract describes package-level meaning and cross-file checks that JSON Schema cannot perform. A schema pass is not scientific validation, publication approval, model readiness, or permission to train or deploy.

## 1. Files and authority

```text
<case-package-root>/
  package.json                                      # phases.phase4.data_ref
  case.json                                         # canonical target/source labels
  phases/phase-04/
    modeling.json                                   # required index/catalog
    configurations/<configuration_id>/             # optional per-configuration detail
      metadata.json
      fold-tasks.json
      cv-metrics.json
      selected-features.json
    charts/<chart-data-id>.json                      # optional aggregate chart points
```

`package.json` is the package file/hash authority. `modeling.json` is the Phase 4 catalog authority. Config detail files and chart data are reached through the case-root-relative refs in `modeling.json`; their directory names never create a configuration or chart by themselves. Do not infer unavailable refs from a method/parameter Cartesian product.

## 2. Modeling index

`modeling.json` uses schema version `1.1.0` and contains `schema_version,case_id,status,cv,methods[],execution_runs[],configurations[],default_configuration_id,charts[]`.

- `status` describes the Phase 4 page-level evidence state. Use `PLANNED` for a source-reported sample awaiting research review; `UNAVAILABLE` for a real empty state; `MOCK` only for visibly synthetic fixtures; use `VERIFIED` only after separate evidence review and release approval.
- `cv` identifies the training row count, fold count, protocol ID, and its own evidence status. A source report that has not been independently confirmed uses `SOURCE_REPORTED_NOT_VERIFIED`; it must not inherit `VERIFIED` from a successful computation status.
- `methods[]` defines actual controls (`method_id,label,parameters[]`). It is not an experiment list.
- `execution_runs[]` identifies one actual runner invocation (`execution_run_id,status`, optional source-manifest SHA). One run may contain many configurations; a method/parameter tuple is not a run.
- `configurations[]` contains only source-backed configurations: `configuration_id,execution_run_id,method_id,track_id,params,protocol_id,status`. The status is an evidence/display gate, not a task execution status. Use `PLANNED` for source-reported configurations pending review and `ERROR` for invalid/incomplete configurations. Four optional case-root refs may point to that configuration's `metadata.json`, `fold-tasks.json`, `cv-metrics.json`, and `selected-features.json`.
- `default_configuration_id` is a UI selection default and may point only to an eligible configuration. Keep it null while every configuration is `PLANNED`, `ERROR`, or otherwise ineligible. `source_reported_candidate_configuration_id` is a separate optional annotation for the candidate named by a source report; it never preselects a configuration or certifies a winner, release, or deployable model.
- `charts[]` describes displayable aggregates; each entry requires a stable `chart_id`, `chart_type`, case-root-relative `points_ref`, and `status`. `status` controls eligibility independently from the point file's source status. Comparisons must state and match protocol, track, metric source, target unit, and X-axis semantics. Never combine requested K, observed selected K, and regularization parameters on one unlabeled axis. Existence, file-manifest membership, ID joins, and comparability remain Bundle Validator checks.

Adding optional config detail refs is the backward-compatible v1.1 change. Reference existence, same-configuration identity, and membership in `package.json.files[]` are bundle checks, not schema assertions.

## 3. Per-configuration detail files

- `metadata.json`: configuration identity, method/parameters, track/protocol, requested K (when applicable), observed selected K by fold/summary, source artifact evidence, and any Final Fit projection. Source flags such as `source_reported_method_winner`, `source_reported_five_method_winner`, and `source_reported_selection_role` are annotations only; they never set UI eligibility or a default. Requested K, fold-selected K, and full-Development Final Fit K are distinct quantities.
- `fold-tasks.json`: one record per planned outer-fold task with stable task ID, fold index, source execution state, and permitted aggregate counts. Keep `COMPLETED`, `INVALID`, `NOT_COMPUTED`, and `ERROR` visible. Do not convert incomplete tasks into successful results or expose row IDs/train/validation indices.
- `cv-metrics.json`: metrics scoped to the actual fold set and target unit, with per-fold values, aggregation rule, mean and sample SD (`ddof=1`) where available. Mark unknown values null with a reason/status. CV fold mean is not pooled OOF and is not Holdout.
- `selected-features.json`: selected encoded-feature IDs and allowed aggregate feature evidence. Preserve source attribution status; do not invent raw-field lineage or coefficient/rank evidence when absent. No row-level prediction payloads.

`final_fit` is optional. `final_fit_id` stays null unless that identity is explicitly present in independently reviewed source evidence; do not derive it from a `configuration_id` or invent one from method/parameters. Metadata-only projection must say whether it is source-reported/unverified and whether the fitted binary is private/not included. Never package joblib/pickle/model binaries, coefficients, scaler arrays, or enable Phase 6 prediction from a Phase 4 catalog entry.

## 4. Status and Phase 5 boundary

Execution status (`COMPLETED`, `INVALID`, etc.), evidence status (`SOURCE_REPORTED_NOT_VERIFIED`), package review, and publication approval are separate. A completed process does not prove scientific correctness; a populated metrics file does not imply an approved result. Aggregate Phase 4 CV is not Phase 5 OOF evaluation. Phase 4 must not contain Phase 5 evaluation records, prediction points, Holdout values, intervals, or diagnostic figures.

The current Ames Sample is a sealed staging snapshot with `publication.approved=false`; its 32 configs and 96 fold tasks are source-reported Development data. It keeps 91 task results marked completed and 5 invalid. The 30 structurally complete configurations remain `PLANNED`; two incomplete configurations remain `ERROR`. `default_configuration_id` is null; the source-reported candidate ID is kept only in the non-rendering annotation field. A source-marked candidate is not a verified scientific winner. The Final Fit projection is restricted metadata only; its ID remains null because the source does not independently provide one, and the binary stays private. These facts are not a new research result or release approval.

## 5. Sample set

- [`modeling.unavailable.json`](./sample/modeling.unavailable.json): empty Phase 4 state; no generated methods, runs, configurations, or chart points.
- [`modeling.nonempty.mock.json`](./sample/modeling.nonempty.mock.json): one synthetic run/configuration to exercise the nonempty catalog path. It uses synthetic IDs and `MOCK` throughout and is never empirical Ames evidence.
- [`VALIDATION-MATRIX.md`](./VALIDATION-MATRIX.md): deterministic schema and bundle checks, with current implementation status.
- The full source-reported fixture remains in [`sample/ames-housing`](../sample/ames-housing/phases/phase-04/modeling.json); do not substitute it for the explicitly synthetic fixture or promote it to VERIFIED.

## 6. Static delivery only

The frontend reads the pinned Case Package and follows its refs. Phase 4 does not add `POST /api/train`, `POST /api/evaluate`, browser-side model fitting, or runtime access to private research files. Training/runner authorization, independent research review, Phase 5 evaluation, model registry, and Phase 6 inference each remain separate gates.
