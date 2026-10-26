# RegScope Phase 5 — Data Structure & Static Delivery Contract v1.2

> **Canonical Phase 5 frontend contract** (Draft / Owner-selected UX, subject to scientific/QA review). Located inside [Case Package v1](../CASE-PACKAGE-SPEC-v1.md). Based on [Issue #37 §15](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/37), whose §15.4 is a **conceptual example only**. This document deliberately **does not** authorize data reads, training, computation, publication, merge or deployment. Phase 5's owner-selected design uses **three figure tabs sharing one viewport**, residual first. The older JSON example in #37 does not supersede the contract here.

## v1.1 Review resolution — Phase 5 is a STATIC DATA CONTRACT (controlling)

**P5-UI-01 ACCEPT — private source mapping:** P5-A's ONLY required files are `evidence-inventory.json`, `gap-permission-matrix.json`, `checkpoint.json`. Mapping lives in `evidence-inventory.json.source_key_mappings[]`; minimum keys: `source_artifact_id,source_sha256,source_key_path_or_csv_column,canonical_destination_field,normalization_rule,read_permission,verification_status,reason_code`. An optional *derived* `source-key-mapping.json` requires `parent_inventory_sha256` and is NEVER a second authority. Earlier §6 and parent Case Package text calling it required are **SUPERSEDED**.

**P5-UI-02 ACCEPT — distinct measurement identities, approach A:** CV fold-mean KPIs and pooled OOF charts are **two evaluations**, each with a distinct nonnull `evaluation_id` and one `metric_source`. Join only via explicitly reviewed `linked_evaluation_ids[]`, sharing `case_id/execution_run_id/configuration_id/evaluation_population/prediction_origin/protocol/evidence mapping`. The page displays the selected KPI evaluation and an individually labeled linked OOF diagnostic evaluation, **never falsely identifies both as one evaluation_id**. Without approved link, diagnostic panel UNAVAILABLE. Holdout aggregate can never link to OOF as its row-level chart. A diagnostic figure's `evaluation_id` equals its *owning* pooled-OOF evaluation, not the CV fold-mean KPI's ID.

**P5-UI-03 ACCEPT — stronger JSON Schema and validator:** Metrics VERIFIED requires finite numeric value and non-empty evidence_ref; MAE/RMSE >=0, R² signed. UNAVAILABLE metric = null with reason_code. IDs require safe slug; duplicate IDs/default reference/cross-file consistency are validator rules. Figures require typed axes, reference lines, histogram bins and per-asset SHA; VERIFIED image requires approved publication, nonnull asset_ref, sha256 and alt. INT-F and INT-S are separate typed evaluation fields; INT-S PASS requires an actual method/type/level/asset and reviewer URL. `fold_summary.sample_sd` is an object `{mae,rmse,r2}`, `ddof:1` (not one unlabeled number).

**P5-UI-04 ACCEPT — staging vs published:** A no-results staging Sample may have `release_id:null`, `generated_at:null`, `publication_review:PENDING`. A **published** package requires real release_id/time, independent review APPROVED, files[] SHA/bytes/MIME, exact references in the same release, publication approval and successful validator, **even if evaluations:[]**. `status:VERIFIED` requires non-empty reviewed evaluations; no MOCK/PLANNED results can be promoted as evidence. Root default evaluation must reference a published eligible evaluation or be null. All refs relative to case-root and must be allowlisted, no traversal or external links as asset paths.

**P5-UI-05 ACCEPT — one status authority:** `ui.figure_tabs[]` and `ui.population_options[]` contain **presentation metadata only**, never research statuses. `ui.interval_figure_id` is a fixed slot label only. The selected evaluation's `metrics/figures/interval`, reviewed publication state, and actual asset validation control what is displayed. With no evaluation, use root `status/reason_code`; selecting a new population clears all previous data. This eliminates state disagreement across UI vs evaluation data.

**Static delivery decision:** Phase5 needs only approved static JSON/figures via HTTP GET or bundled assets, **not a new evaluation API**. No `POST /api/evaluate`, no inference, no request-time CV/metrics/sklearn. Phase6 prediction API remains distinct.

### Exact authoritative source examples

- [Sample (empty/no-results)](./sample/evaluations.json): syntactically valid staging JSON, NOT a public released empirical package.
- [JSON Schema Draft 2020-12](./evaluation-index.schema.json): machine-checkable structural validation. Cross-file keys, hashes, rights and physical asset validation are still required in later validator implementation.
- **Nonempty evaluation requirement:** For an actual eligible record supply `linked_evaluation_ids:[]` (or verified links), `fold_summary.sample_sd:{mae,rmse,r2}` with ddof=1, `figures[].histogram` null except valid histogram, and all documented source/provenance status. Never create null-identified evaluation items.


## 1. What frontend needs and where to put it

```text
<case-package-root>/
  package.json                                   # root pointer phases.phase5.data_ref
  case.json                                      # target label and unit
  phases/
    phase-04/modeling.json                      # verified execution_run/configuration catalog
    phase-05/
      evaluations.json                          # REQUIRED entrypoint even when EMPTY
      evaluations/
        <evaluation_id>.json                    # OPTIONAL reviewed full evaluation, if split
      figures/
        fig-p5-01.svg                            # OPTIONAL and ONLY if approved/public-safe
        fig-p5-01.png
        fig-p5-02.svg
        fig-p5-02.png
        fig-p5-03.svg
        fig-p5-03.png
        fig-p5-04.svg                            # interval figure ONLY after INT-S PASS
      tables/
        <evaluation_id>-fig-p5-02.json           # OPTIONAL PUBLIC-SAFE aggregate alternative
  assets/
    figure-manifest.json                         # all published figure refs, hashes, rights
```

**Naming & path:** Relative paths are always relative to the **Case root**, not the phase directory, with forward slashes only. No `..`, absolute disk/HTTP URL, symlink escape or cross-release reference. `evaluation_id` must use a safe slug, be unique per case+release and come from source mapping/approved exporter; do not invent from alpha values. Entries absent from the root `package.json.files[]` and verified SHA-256 are not releasable. Add those paths to immutable release manifest at seal time. Private P5 files stay at separately authorized `local/research/phase5/<gate_id>/artifacts/`, **never inside public package**.

## 2. Network operations (not a new dynamic evaluation service)

| Action | Canonical route | UI use | Service |
|---|---|---|---|
| Determine active approved snapshot | `GET /data/current-release.json` | pin one `release_id` per view/session | public static read |
| Choose Case | `GET /data/releases/{release_id}/index.v1.json` | registered eligible case IDs | public static read |
| Load root manifest | `GET /data/releases/{release_id}/cases/{case_id}/package.json` | resolve exact Phase 5 data_ref | public static read |
| Resolve configuration | GET the same pinned Case Package's `phases/phase-04/modeling.json` | validate `execution_run_id+configuration_id`, restore method/params | public static read |
| Load Phase 5 | GET root `phases.phase5.data_ref` = `phases/phase-05/evaluations.json` | list approved evaluations, metrics/figures, state | public static read |
| Expand evaluation | GET `detail_ref` if not inline | same evaluation scope, fold summary/interpretation | public static read |
| Switch diagnostic figure | GET selected `figures[].asset_ref` and optional `accessible_table_ref` | ONE matching figure + associated alt/findings | public static asset read |
| View evidence | open reviewed `evidence.review_url` or approved source URL | traceability | link only |

**No `POST /api/evaluate`, no browser calculation, no access to private OOF/holdout rows.** `POST /api/predictions` belongs to Phase 6 and must never be used to produce Phase 5 graphs or scores. Vercel need only serve approved static files for P5. HTTP 404/timeouts/hash/version mismatch => item-scoped unavailable/error with stale data cleared, not a fallback to mismatched release.

## 3. Mandatory identity and population invariants

`case_id → execution_run_id → configuration_id`; each `evaluation_id` refers to **one** exact `configuration_id + evaluation_population + metric_source + prediction_origin + evidence version`. `final_fit_id`/registered `model_id` optional and null when not verified; cannot construct from configuration. No `run_id` alias unless independently audited and versioned.

- `evaluation_population`: `development_oof` / `holdout` / `training_in_sample`. The UI may show "Holdout 聚合" only if an approved holdout evaluation exists; **never expose row-level Holdout scatter automatically**.
- `metric_source`: `cv_fold_mean` / `pooled_oof` / `holdout_aggregate` / `training_in_sample`. One evaluation = one metric_source. A fold mean CV score is not the same value as pooled OOF performance even if both refer to Development OOF.
- `prediction_origin`: semantic string from verified source (`fold_specific_selected_to_ols` when truly evidenced, `final_fit_holdout_aggregate` for historic approved Holdout aggregates). No automatic `final_fit` claim from OOF.
- All metrics and figures are scoped to the same case, execution, configuration, protocol and pinned release. Each figure belongs to its **own** evaluation_id; approved linked OOF figures may be presented next to CV-fold-mean KPI only by explicit linked_evaluation_ids[], clearly labeled with a separate source and evaluation ID. No cross-population or Holdout-to-OOF linking. A legitimate research evaluation may have `model_id: null` if no registered inference model exists.
- Null numeric = **unknown/not eligible**, never 0. Reject NaN/Infinity/string numbers. Status `VERIFIED` research requires separate `publication_review=APPROVED`, `asset_status=AVAILABLE` and integrity checks before a published figure can render.

## 4. `evaluations.json` — REQUIRED root fields

The machine-readable concrete example is [`sample/evaluations.json`](./sample/evaluations.json) and the published-staging sample is [`../sample/ames-housing/phases/phase-05/evaluations.json`](../sample/ames-housing/phases/phase-05/evaluations.json).

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema_version` | string | yes | Phase5 record contract version `1.0.0` (distinct from Package's version) |
| `case_id` | slug | yes | matches case root |
| `release_id` | string or null | yes | null in unsealed staging; real approved immutable release at publish |
| `generated_at` | ISO-8601 UTC string or null | yes | null only if never generated from empirical source |
| `status` | `VERIFIED/UNAVAILABLE/PLANNED/MOCK/ERROR` | yes | document-level state, not model readiness |
| `reason_code` | string or null | yes | why empty/unavailable; null if valid |
| `publication_review` | `PENDING/APPROVED/REJECTED` | yes | actual permission to publish |
| `default_evaluation_id` | string or null | yes | must reference a valid eligible `evaluations[]` entry or null |
| `evaluations` | array | yes | only fully identified reviewed records; if none, **`[]`** |
| `ui` | object | yes | fixed figures order/residual-first, available population labels, supports same renderer in all cases |

**Status rule:** An empty list is perfectly valid as a renderable UI fixture; `status=UNAVAILABLE` or `PLANNED`, `reason_code` provided and `default_evaluation_id=null`. In publication mode, APPROVED release cannot contain `MOCK` artifacts passed off as empirical data.

### 4.1 Each `evaluations[]` record — required fields and semantics

| Field | Type | Requirements |
|---|---|---|
| `evaluation_id` | nonempty slug | unique and source-backed; never null in array |
| `execution_run_id`, `configuration_id` | nonempty slug | must resolve Phase4 catalog and refer to matching case/execution/protocol |
| `final_fit_id`, `model_id`, `model_version` | string or null | only real audited link; NULL permitted |
| `evaluation_population` | enum from §3 | evaluation row population |
| `prediction_origin` | string | origin of predicted values; OOF fold-specific vs full-development final-fit |
| `metric_source` | enum §3 | only ONE per evaluation |
| `n` | integer ≥1 | true evaluated sample count; if unknown record not eligible (use empty list) |
| `target` | `{column,unit}` | `SalePrice`, `USD` for Ames, derived from Case not guessed |
| `metrics` | `{mae,rmse,r2}` | each independent `{value:number\|null,status,reason_code,evidence_ref}` |
| `fold_summary` | object or null | `fold_count,aggregation,sample_sd,fold_values_ref`; distinguish fold mean vs pooled |
| `figures` | array | exact FIG-P5-01/02/03 entries from §4.2; each may individually be UNAVAILABLE |
| `interval` | object | distinct `int_f` method feasibility and `int_s` actual submitted CI/PI |
| `evidence` | object | `source_artifact_sha256,source_ref,protocol_version,review_url` (public-safe only) |
| `asset_status` | `AVAILABLE/UNAVAILABLE/PENDING_REVIEW` | separate from evaluated metric research status |
| `review_status` | `APPROVED/AWAITING_REVIEW/REJECTED` | independent reviewer decision |
| `limitations` | string[] | plain-language, verified source caveats; no generated ungrounded conclusions |

**Metric formatting:** MAE/RMSE finite non-negative numeric measured in target units; R² finite may be negative, is not percentage. A visible metric requires its **own** `status=VERIFIED`, evidence, release review and `n`. UI never recomputes values from figures. `fold_summary.sample_sd` pertains to fold distribution and is unavailable (null) if only pooled OOF exists.

### 4.2 Each figure in `figures[]`

| Field | Purpose |
|---|---|
| `figure_id` | Stable: `FIG-P5-01` actual-vs-predicted; `FIG-P5-02` residual-vs-predicted; `FIG-P5-03` residual-distribution |
| `evaluation_id,configuration_id,evaluation_population,prediction_origin` | must equal its own owning evaluation; prevents mixing models, Holdout and OOF |
| `n` | same evaluated population sample; if nonidentical, must be separately justified and not silently treated as same record |
| `status`, `publication_review` | figure's own evidence / rights; only VERIFIED+APPROVED may link image |
| `asset_ref`, `sha256`, `accessible_table_ref` | all nullable if unavailable; approved refs case-root relative and hashed in package manifest |
| `axes` | `{x:{field,label,unit},y:{field,label,unit},reference_line}` |
| `residual_sign` | FIG-P5-02/03 = `actual_minus_predicted`, else null |
| `alt`, `finding`, `limitations`, `source_digest` | accessible description, sourced interpretation and provenance |

**Semantics:** FIG-P5-01 X=actual target, Y=predicted, reference `y_equals_x`. FIG-P5-02 X=predicted, Y=actual−predicted, reference `y_equals_0`; **positive residual means underprediction**. FIG-P5-03 histogram bins and zero line, not an automatic normality test. All 3 may be unavailable separately. No private OOF/holdout CSV, per-row coordinates or uncontrolled URL in public JSON. A PNG alone is not proof of publication approval.

### 4.3 Interval object, FIG-P5-04

`interval.int_f = {status,reason_code,method,assumptions_ref}` evaluates the statistical feasibility of CI/PI; `interval.int_s = {status,reason_code,interval_type,method,nominal_level,population,asset_ref,coverage_evidence,review_url}` denotes the **actual** interval diagram and explanation meeting assignment requirements. Null means unknown/unavailable. **INT-F PASS never implies INT-S PASS**. Do not present `RMSE×1.96` as coverage-guaranteed PI; post-selection OLS method, calibration and Holdout isolation need separate scientific gate.

## 5. Frontend deterministic rendering and failure-state contract

1. Read pinned case, validate Phase 4 selected `execution_run_id+configuration_id`; if deep link fails, do not silently select another run.
2. Fetch Phase5 `evaluations.json`. Eligible selector options require full source/ID integrity and release; with empty list show informative unavailable page, three blank metric cards, residual placeholder and interval pending.
3. Select exactly one evaluation at a time, filtered by chosen population; changing config or population clears previous metrics, image, alt/table, interval, evidence and aborts/ignores stale fetch responses.
4. Render **three metric cards** MAE/RMSE/R², fixed order; absent means `—` plus reason, not 0.
5. Render **one figure viewport** with three accessible tabs, initial FIG-P5-02 (Residual), next FIG-P5-01, next FIG-P5-03. Switching tabs atomically updates image, axes, findings, alt/table and evidence. Disabled/unavailable figure still reveals explanatory same-size placeholder.
6. Interval card is always shown; INT-F and INT-S distinct visible status; when INT-S unavailable say **HW2 formal CI/PI deliverable incomplete**.
7. Show limitations and evidence after charts, and links to Phase4 (preserve case+execution+configuration) and Phase6 (registry lookup, not automatic model readiness).
8. Show `LOADING` placeholder on static resource fetch, `ERROR` on 404/bad JSON/hash, `UNAVAILABLE` on missing approved data, `MOCK` only fixture environment; no metric or chart from earlier case/config/release survives switch.
9. Accessibility: keyboard-reachable tabs with active-state semantic, text alt, table/summary, explicit axis units/population/n, no color-only inference; image aspect `contain` and typography matches shared shell.

**Source of UI geometry**: [`pages/PHASE-05.md`](../../pages/PHASE-05.md) is the authoritative layout. This document controls **data field meanings**, not a separate competing wireframe.

## 6. Producer (Phase5 offline) → exporter mapping

| Private source from Issue #37 | Public product | Restrictions |
|---|---|---|
| `evidence-inventory.json`, `gap-permission-matrix.json` | safe `evidence` refs / unavailable reasons | metadata-only gate, never expose private paths/row keys |
| `evaluation-metrics.json` | per-evaluation `metrics`, `fold_summary` | distinguish CV fold means from pooled OOF, all source SHA and n verified |
| `figure-manifest.json` plus reviewed SVG/PNG | `figures[]`, optional asset refs | authorized public-safe conversion; no Holdout row access without separate approval |
| `evaluation-report.md` | `limitations`, narrative findings | reviewed and sourced, not LLM-invented |
| `qa-report.json` / `checkpoint.json` | publication_review/review_status provenance | producer cannot certify independent QA PASS |

No real source key path has been confirmed for the ignored local artifacts; **must remain UNKNOWN pending authorized metadata audit**. Mac/Windows or historical reported metrics are not promoted to VERIFIED by being typed into JSON.

## 7. Sample, validation and acceptance

- **Normative no-results sample**: [sample/evaluations.json](./sample/evaluations.json). **Nonempty synthetic linked-evaluation fixture**: [sample/evaluations.nonempty.mock.json](./sample/evaluations.nonempty.mock.json); never use as empirical Ames evidence.nvelope): [`sample/evaluations.json`](./sample/evaluations.json), backed by [Case Package sample](../sample/ames-housing/phases/phase-05/evaluations.json). This sample is deliberately `UNAVAILABLE`, `evaluations:[]`, all three figure slots missing and both interval gates outstanding. Does not claim actual results.
- **Schema source**: [`evaluation-index.schema.json`](./evaluation-index.schema.json), JSON Schema 2020-12. Validator must check base schema **and** cross-file referential and SHA/license/source assertions. JSON Schema alone cannot prove publication permission.
- Any future **success** example must be marked `MOCK` with synthetic non-Ames identifiers, never `VERIFIED`, and NEVER published. No sample with null `evaluation_id` inside `evaluations[]`.
- QA matrix: parse UTF-8; schema; unresolved IDs; duplicate ID; cross-population; wrong version; mixed metric source; missing n; R² display; figure residual sign/axes; FIG-P5-02 priority; stale async result; no interval figure; no secrets/local data; source permission; immutable release hash.
- This contract defines **static read-only Phase5 API** only; private offline export and runtime validator remain future authorized implementation. Phase5 #37 reviewer/Owner must approve research evidence before website displays genuine values.

## F01–F12 Review freeze rules — canonical v1.2 (2026-10-27)

**P5-UI follow-up #6421939874:** ACCEPT F01–F12, with code-level release validation **DEFER / NOT_IMPLEMENTED** until authorization. This section is normative; resolve any old §3/§4 wording using the explicitly corrected replacements in their paragraphs; do not reintroduce a second source-mapping authority.

**Producer:** P5-A minimum only `evidence-inventory.json`, `gap-permission-matrix.json`, `checkpoint.json`. The **only** authoritative mapping is `evidence-inventory.json.source_key_mappings[]`; each row has `source_artifact_id,source_sha256,source_key_path_or_csv_column,canonical_destination_field,normalization_rule,read_permission,verification_status,reason_code`. Any optional derived map must contain `parent_inventory_sha256`, and never become a required source or competing truth.

**Linked evaluation A — exact UI lookup:** First resolve KPI evaluation by `case_id+execution_run_id+configuration_id+evaluation_population+metric_source=cv_fold_mean`. Follow **only** `linked_evaluation_ids[]`; each reference must resolve within the same case and pinned release. The linked evaluation must be `metric_source=pooled_oof`, `evaluation_population=development_oof`, same execution/config, protocol/version and approved evidence; it owns **its own** FIG-P5-01/02/03. Check reciprocal compatibility and explicit permission; do not require the KPI evaluation_id to equal the linked graph evaluation_id. If link missing, invalid, or not approved, graph is UNAVAILABLE. Holdout aggregate cannot borrow OOF graphs, directly or transitively. When a pooled OOF evaluation is selected, its own figures may display; never transfer figures between populations.

**Schema versus release validator:** JSON Schema 2020-12 checks nested types and local conditional values (and `date-time` only when FormatChecker/format assertion enabled). A **separate bundle validator** must check ID uniqueness, default IDs, link membership/type/protocol, target mapping, eligible figure scope, publication permission, file SHA/size/MIME, relative path traversal, same-release refs and license. See [VALIDATION-MATRIX.md](./VALIDATION-MATRIX.md). Bundle validator runtime: **NOT_IMPLEMENTED**, and therefore real release PASS cannot be claimed.

**Figure tokens and units:** FIG-P5-01 axes `x.field=actual`, `y.field=predicted`, `reference_line=y_equals_x`; FIG-P5-02 `x.field=predicted`, `y.field=actual_minus_predicted`, `reference_line=y_equals_0`; FIG-P5-03 `x.field=actual_minus_predicted`, `y.field=count`, `reference_line=x_equals_0`, `histogram.bin_count>=1`, `histogram.n=n` and verified bin edges. All target-valued axes have `unit=target.unit`, count is dimensionless `count`. Histogram and plot asset only after approved paired predictions and publication QA.

**Metrics/scope:** VERIFIED MAE/RMSE require finite number >=0 and nonempty evidence_ref. VERIFIED R² is finite, dimensionless and may be negative. UNAVAILABLE must be null with a reason. For `cv_fold_mean`, `metrics.*.value` is source-backed mean across explicitly scored folds and `fold_summary.sample_sd.{mae,rmse,r2}` separately stores per-metric sample SD with `ddof=1`; not a pooled OOF value. Pooled OOF must have its own evaluation ID and metrics; no implicit averaging or synthetic folds.

**Intervals:** `int_f.status=PASS` does **not** complete `int_s`; INT-S PASS requires reviewed method/type/level/population/figure asset/coverage evidence. Unavailable INT-S keeps the homework interval requirement outstanding. Historical Holdout 292 aggregate has no row-level plotting permission.

**Target join:** public P5 `target.column = case.json.target.raw_field_id`, `target.unit = case.json.target.unit`; source `case.json.target.value_type=number` is checked. The frontend never infers SalePrice/USD from case name, nor displays R² as a percentage.

**Render authority:** `ui.*` holds only ordering/labels/figure slot IDs, not availability status. An evaluation is eligible only if its own review/source evidence passes and its parent release is approved. Metric display requires own VERIFIED value/evidence; figure display additionally requires its own VERIFIED, APPROVED publication, asset_status AVAILABLE, case-root asset_ref + correct SHA + public allowlist. An EMPTY/PLANNED/MOCK/PENDING/REJECTED context never displays empirical data. A published EMPTY (evaluations:[]) is legitimate with `status=UNAVAILABLE` and reason, but must be sealed and approved at **package publication layer**.

**Lifecycle:** staging may have release_id/generated_at=null, PENDING, files=[]. Publication mode must require real pinned release_id, valid UTC timestamp, independent APPROVED review, sealed all-files manifest, digest and link integrity, no unauthorized private data and atomic release pointer switch. Schema validation alone is insufficient and does not authorize publication.

## Validation status and F01–F12 trace

See [VALIDATION-MATRIX.md](./VALIDATION-MATRIX.md) for deterministic positive/negative assertions, exact schema-versus-bundle-validator responsibilities, prescribed cross-platform command and **NOT_RUN / NOT_IMPLEMENTED** statuses. The synthetic MOCK fixture contains two linked evaluations with distinct metric sources, plus three correctly typed unavailable figure records. 

**Change log:** v1.0 static Phase5 contract; v1.1 P5 Producer review corrections; **v1.2 (2026-10-27)** F01/F02 stale wording corrected in place, source join/axis tokens/field authority standardized, synthetic linked fixture and separate validation matrix published. The existing filename retains `v1` to denote major compatibility rather than a new incompatible API version.
