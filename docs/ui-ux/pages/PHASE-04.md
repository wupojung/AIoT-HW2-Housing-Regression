# Phase 4 — Modeling

**Current detailed UX; docs-only.** The active consumer contract is Case Package Phase 4 Modeling schema `1.1.0`: `execution_run_id` identifies one producer invocation and `configuration_id` identifies one selectable parameterized configuration. These IDs are distinct. The [data-contracts path table](../../design/data-contracts/README.md#phase-4-authoritative-paths) names the single producer schema, semantic contract, frontend layout, sample, and validation matrix. Earlier Phase 4 payload shapes in this document are superseded by that contract.

## Phase 4 — Modeling / 模型建立：詳細 ASCII Wireframe + JSON Consumer Contract v1.1

**Owner-approved design direction (2026-10-26), DOCS ONLY.** This detailed section controls Phase 4 over the earlier abbreviated Phase 4 diagram, while preserving earlier scientific/evidence/governance safeguards. No implementation, model rerun, holdout use, merge or deployment is authorized.

### A. Purpose, terminology and placement

Phase 4 teaches **(1) how the Training Set was cross-validated, (2) which feature-selection methods and configurations were ACTUALLY run, and (3) what documented feature choices and CV outcomes resulted**. It must not imply that a visitor changing a dropdown trains a model.

- **Training Set:** 1,168 labeled Ames rows (80% of the source 1,460; called Development Set in prior research artifacts). Phase 4's UI-facing label is **Training Set**, preserving the \`development\` name in research provenance where needed.
- **Holdout Test Set:** 292 rows (20%), sealed and **not used in Phase 4 selection, CV, or tuning**; final approved evaluation belongs in Phase 5.
- **Kaggle competition test:** 1,459 separate *unlabeled* rows, not part of the 80:20 split or Phase 4 CV.
- **3-Fold CV:** three similarly sized parts of the 1,168-row Training Set. At each iteration, roughly **66.7% Training Folds** and **33.3% Validation Fold**, with the validation third rotating. Because 1,168/3 is not an integer, do not promise exact equal counts; actual fold counts from splitter artifacts should be preferred. The CV fold count is **recorded experiment metadata**, not a live-editable parameter.
- **Top K / selected encoded feature count** (method-specific selection parameter) is different from **CV folds (K-Fold)**. Do not introduce "Top P" without a documented actual method parameter. Alpha and Top K are **not schema-level either/or**: a method can declare 0, 1, 2 or more parameters.

### B. ASCII wireframe — PC Desktop 1920 × 1080 reference; vertical scrolling

The Ames fixture currently has no eligible configuration. This wireframe therefore shows the public empty state; the listed row/fold counts are source-reported only and must not be presented as verified.

~~~text
+----------------------------------------------------------------------------------------------------------------+
| RegScope                                     Home / CRISP-DM                      [Dashboard]                  |
| Research dataset: [ Ames Housing v ]                                                                           |
| [01 Business] [02 Data] [03 Preparation] [04 Modeling ★] [05 Evaluation] [06 Deployment]                      |
+----------------------------------------------------------------------------------------------------------------+
| PHASE 04 / MODELING                                                                                             |
| 模型建立與特徵選擇：如何驗證訓練資料、選出特徵，並比較模型？                                                       |
| STATUS: PLANNED / SOURCE_REPORTED_NOT_VERIFIED — staging preview only; not approved for public results            |
|                                                                                                                |
| ① CROSS-VALIDATION PROTOCOL                                            [3-Fold CV] (READ-ONLY)                 |
| +------------------------------------------------------------------------------------------------------------+ |
| | Training Set: 1,168 labeled rows             Primary comparison: CV RMSE ↓       Seed: [from protocol]      | |
| |                                                                                                            | |
| | Fold 1  [ Validation ~33.3% ][ Training ~33.3% ][ Training ~33.3% ]                                        | |
| | Fold 2  [ Training ~33.3% ][ Validation ~33.3% ][ Training ~33.3% ]                                        | |
| | Fold 3  [ Training ~33.3% ][ Training ~33.3% ][ Validation ~33.3% ]                                        | |
| | Legend: [Training folds blue] [Validation fold teal]                                                        | |
| | Per-run actual training/validation counts and protocol details: [Expand CV methodology v]                   | |
| | Holdout 292 rows NOT used; competition test 1,459 rows also separate.                                        | |
| +------------------------------------------------------------------------------------------------------------+ |
|                                                                                                                |
| ② FEATURE SELECTION & MODEL EXPLORER                                                                              |
| +------------------------------------------------------------------------------------------------------------+ |
| | Research perspective: [Method Comparison] [Selected Features] [Feature Count vs CV RMSE]                    | |
| |                                                                                                            | |
| | Feature Selection Method: [No eligible configuration — disabled]                                           | |
| | Method parameters — derive only from existing configurations[].params; current sample has no eligible one:   | |
| | [Parameters unavailable]                                                                                   | |
| |                                                                                                            | |
| | Configuration: [none]  Execution: [development_20261026_01 / ERROR]  Protocol: [source-reported]           | |
| +------------------------------------------------------------------------------------------------------------+ |
| | ONE PRIMARY RESULT PANEL — changes with research perspective                                               | |
| | No verified, approved configuration. Public results are unavailable; do not draw charts or rank candidates. | |
| | Reviewer preview, if enabled, must watermark PLANNED / SOURCE_REPORTED_NOT_VERIFIED and remain non-public.  | |
| +------------------------------------------------------------------------------------------------------------+ |
|                                                                                                                |
| ③ EXPERIMENT CONFIGURATION (read-only)                                                                            |
| +------------------------------------------------------------------------------------------------------------+ |
| | Method ID   | Configuration | Selected encoded count / method-defined (unavailable here)   | |
| | CV protocol | Fold count | Scoring | Data version | Execution / Configuration IDs | Params | Track / provenance | |
| | [Expand experiment details v]                                                                                | |
| +------------------------------------------------------------------------------------------------------------+ |
| [< Previous Phase: Data Preparation]                                                [Next Phase: Evaluation >]   |
+----------------------------------------------------------------------------------------------------------------+
~~~

**Presentation details**
1. The CV diagram uses the **same quantitative 100%-horizontal-bar language** as Phase 3, but its unit is **ROWS within training folds**, NOT feature columns. Three bars represent one 3-fold CV protocol, not three independent train/test splits or three selections of a different dataset. Segment widths are equal-ish by actual fold-size data; in schematic view use approximate 33.3%, with explanatory note. Show 66.7% aggregate training versus 33.3% validation per run below the bars. Colors and labels visible without relying on color alone.
2. Phase 4 has **one selected result perspective** at a time; do not render all comparison figures simultaneously. Dynamic controls appear in the same form below that perspective's selector; changing parameters swaps the selected evidenced configuration, its result and detail refs together. Each result panel has explicit configuration/execution/protocol/metric identity and an availability state.
3. Do not assert that every parameter value in a numeric range is supported. **Dropdown choices reflect recorded, eligible configurations**, not a synthetic Cartesian product. A method with \`alpha\` + \`l1_ratio\` may have only one valid pair. If no configuration matches, show UNAVAILABLE and disable outcome rather than invent a score.
4. CV comparison must show a compatible method/config/protocol/track population. Lasso/Elastic Net are not inherently fixed-Top-K selectors; selected encoded counts can be method-defined, while Pearson/Mutual Information/Ridge-RFE may use explicit \`top_k\`/requested selection counts when verified. A method's hyperparameter label is taken from its own schema.
5. A visible method list MAY show Lasso, Pearson, Mutual Information, Ridge-RFE, Elastic Net, OLS Baseline for Ames when backed by actual run records. **OLS is a baseline without selection-specific params**, and should not silently be counted as a sixth feature-selection algorithm.
6. Actual CV primary scoring metric is CV RMSE for current research design. Define lower-is-better and label units when verified; do not put Holdout RMSE or unreviewed test scores on Phase 4 charts. Display fold SD only if it exists.
7. Source/citation, error and accessibility behavior follows the document-wide LOADING / EMPTY / ERROR / PLANNED / MOCK / UNAVAILABLE / VERIFIED state contract. A panel is not VERIFIED merely because a parameter definition exists.

### C. Every interactive control and behavior

| Control | Position | Action | Reset/guard |
|---|---|---|---|
| Global Research Dataset | shared header | Change \`case_id\`, replace *all* Phase 4 method definitions, execution runs, configurations, protocol, outcomes and metadata | Reset method, params, selected configuration and result perspective to supported defaults; never leak Ames values to another case |
| Phase navigation 01–06 | shared header | Navigate within current case | Preserve \`case_id\`; Phase 4 always uses recorded current-case protocol |
| 3-Fold summary | top card, read-only | Displays \`cv.fold_count\`, Training Set rows, and the linked protocol status; show scoring only from a compatible chart's declared metric metadata | NOT a selectable number of folds; missing metric/protocol -> UNKNOWN or UNAVAILABLE |
| Expand CV methodology | below three fold bars | Accordion click toggles protocol, actual fold sizes if recorded, splitter type, shuffle, seed, fitting isolation, evidence | Collapsed initially; metadata missing -> explicit UNKNOWN |
| Perspective tabs | top of Explorer | Switch exactly one result panel: method comparison / selected features / feature count vs CV | Keep method + valid selected configuration when panel supports it; otherwise show unavailability, never stale chart |
| Method dropdown | Explorer | Select method among registered case methods | Recompute available parameter controls and eligible configurations; reset all incompatible parameter values and prior result |
| Each parameter dropdown | Explorer; dynamically repeated per method | Select one **allowed value** for that parameter | Options filtered to values of real available compatible run tuples; later param changes cannot create non-existent combo |
| 0-parameter method | Explorer | Show concise “No feature-selection parameters”; select a compatible eligible configuration | Don't render inert/blank dropdowns |
| Selected configuration/evidence link | result header | Open traceable public configuration record if approved | Missing source: disabled with reason; do not expose local paths |
| Expand experiment details | configuration card | Toggle \`configuration_id\`, parent \`execution_run_id\`, documented params, target, selected counts, CV protocol, track, evidence and limitations | Missing values explicit UNKNOWN; no hardcoded metadata |
| Previous Phase | footer | Go Phase 3 | Same case |
| Next Phase | footer | Go Phase 5 | Same case; Phase 5 independent holdout gate |

**Selection algorithm (UI-only, no fitting):** on method change, filter \`configurations[]\` by \`method_id\` and compatible \`protocol_id\` / \`track_id\`, then populate controls from complete recorded \`params\` tuples. On parameter change, keep only exact existing configuration tuples; update dependent controls to an evidenced tuple or show no compatible configuration. **Never** synthesize a Cartesian combination or silently preserve an invalid tuple. \`default_configuration_id\` may point only to an eligible configuration; it is null in the current Ames staging package. A dataset change invalidates caches/charts/results from the previous case. If a method has no eligible configuration, show its status and reason without an enabled result selector.

### D. Producer v1.1 consumption, perspectives, and eligibility

The single normative field shape is the canonical [Phase 4 root schema](../../design/data-contracts/schemas/phase-04.schema.json), interpreted by the [Phase 4 data contract](../case-package/phase-04/PHASE-04-DATA-CONTRACT-v1.md) and demonstrated by the [Ames staging sample](../case-package/sample/ames-housing/phases/phase-04/modeling.json). Earlier draft payload shapes are superseded; do not add legacy run identifiers. `execution_runs[]` records producer invocations; `configurations[]` records selectable method/parameter configurations. `default_configuration_id` is the only package-level configuration default.

| Perspective | Selector / compatible filter | X / columns | Y | Ordering | Missing or ineligible evidence |
|---|---|---|---|---|---|
| Method comparison | Filter by method, exact recorded `params`, `protocol_id`, metric source, target unit, and one compatible `track_id`; each point resolves to a `configuration_id`. | `configuration_id` (categorical); render method + full params as its label. Fixed-K charts are a distinct chart type with `requested_k` as X. Keep `selected_to_ols`, `all_features_ols`, and `diagnostic_only` tracks in separate panels. | `rmse` / mean CV RMSE in declared target units; lower is better only where the chart declares it. | No metric ranking for staging/unverified data. Eligible results sort by RMSE ascending, then stable configuration ID. | No compatible eligible config: show the empty-state text below; do not draw a connecting line across absent points. |
| Selected features | One selected `configuration_id`; load only its `selected_features_ref` | Table columns: encoded feature ID, selected folds / total folds, selection fraction, source-mapping status. Show raw-source mapping only when present and attributed. | Not a metric chart. | Selection count descending, then encoded feature ID. | If the detail is absent or unavailable, show its reason; do not substitute another configuration's features. |
| Feature count vs CV | Exact configurations in the same protocol/metric/target/track; separate fixed-requested-K and observed-selected-count chart types | Fixed chart: `requested_k`; observed chart: observed selected encoded count. Never combine requested K, observed count, and regularization values on one axis. | CV fold-mean RMSE in target units. | X ascending, then stable `configuration_id`; no interpolation or fabricated points. | Plot only existing points with eligible evidence; missing points remain gaps and have explicit reasons. |

**One eligibility rule:** a public verified result is selectable only when the package publication gate is approved, the page-level Phase 4 evidence is `VERIFIED`, the configuration and required metric/detail evidence are independently `VERIFIED`, and any chart used is itself `VERIFIED` and compatible. The source candidate annotation and source-reported winner flags never count toward eligibility. Preserve producer execution state separately: `execution_runs[].status=ERROR` remains visible even if an individual configuration is later reviewed. For the current Ames staging sample (`publication.approved=false`, modeling `PLANNED`, 30 configurations `PLANNED`, 2 `ERROR`, no eligible default), the public verified view shows a “No verified, approved configuration” state and no result chart. A non-public reviewer preview may show source-reported points only with a visible `PLANNED / SOURCE_REPORTED_NOT_VERIFIED` watermark, no winner/rank/default, and no inference handoff.

**Loading rule:** fetch `modeling.json` first. Do not eagerly fetch all chart point files or the 5.67 MB selected-features-by-configuration aggregate. For the Selected Features perspective, load only the chosen configuration's `selected_features_ref`; never bulk-load the global feature aggregate into the first screen. Load other chart points only when their perspective is opened. Keep long feature tables paginated or virtualized (maximum 50 rows per rendered page); switching configurations cancels/discards the prior detail request. The current source-reported feature payload is an aggregate projection, but rights and research approval remain unverified, so it is staging-only and not public UI evidence.

**Provenance and error rule:** preserve all 96 task records (91 `COMPLETED`, 5 `INVALID`) and both `ERROR` configurations. A chart point may be shown as a verified aggregate only when its source fold set and any excluded task IDs/reasons are linked and independently reconciled with `fold-tasks.json` and `cv-metrics.json`. The current chart points do not identify included/excluded task IDs; they remain `PLANNED` and must not be recomputed, silently filtered, or ranked as a verified winner. `cv-protocol.json`'s `SOURCE_REPORTED_VERIFIED_MATCH` means source-manifest/protocol identity matched only; keep its `run_status=ERROR` visible and do not interpret the match status as research or publication verification.

### E. Phase 4 documentation acceptance checklist
- [ ] 3-fold bar graph conveys approximately 2/3 training and 1/3 validation **within** the Training Set, with each third serving validation once; exact fold-size caveat visible.
- [ ] Phase 3's 80/20 and Phase 4's 3-fold are distinct; Holdout Test Set never participates in CV; Kaggle competition test distinct.
- [ ] All method/parameter controls are generated from `methods[]` and exact `configurations[].params`; no unrestricted Cartesian combination.
- [ ] No unrestricted Cartesian combination of Alpha/L1 Ratio/Top K unless an exact eligible configuration exists.
- [ ] `execution_run_id` and `configuration_id` are separately named and never conflated.
- [ ] One of three result perspectives displays at a time; filters, axes, ordering and empty states follow the table above.
- [ ] Selected encoded features are not equated with raw feature count, and \`top_k\` is not treated as CV folds.
- [ ] Evidence/verification/UNKNOWN/UNAVAILABLE statuses apply to configurations, metrics and controls; no MOCK results presented as empirical.
- [ ] Charts and feature details load on demand; no bulk feature payload loads on the initial page.
- [ ] PR remains DOCS ONLY, subject to existing Owner and independent review gates.


---

### 2. Phase 4 wireframe extension — clarify training set and two handoff links

~~~text
+------------------------------------------------------------------------------------------------------+
| CASE: [Ames Housing v]           PHASE 04 — MODELING                    [Phase 05]  [Phase 06]       |
|                                                                                                      |
| 01. 3-FOLD CROSS-VALIDATION  | Training Set = 1,168 rows | CV Folds = 3 (read only)                    |
| Fold 1   [ VALIDATION ~33.3% ][ TRAINING ~33.3% ][ TRAINING ~33.3% ]                                  |
| Fold 2   [ TRAINING ~33.3% ][ VALIDATION ~33.3% ][ TRAINING ~33.3% ]                                  |
| Fold 3   [ TRAINING ~33.3% ][ TRAINING ~33.3% ][ VALIDATION ~33.3% ]                                  |
| Legend: training / validation; ~66.7% train + ~33.3% validate in each fold; exact rows from evidence   |
| [Expand CV protocol and fold details v]   HOLDOUT 292 rows not used here                             |
|                                                                                                      |
| 02. EXPLORE A RECORDED RESEARCH CONFIGURATION                                                        |
| Perspective: [Method comparison] [Selected features] [Feature count vs CV]                           |
| Method: [No eligible configuration — disabled]                                                       |
| Dynamic parameter controls: [Unavailable until an eligible configuration exists]                      |
| Configuration: [none]  Execution: [development_20261026_01 / ERROR]                                  |
| [No verified, approved configuration; show UNAVAILABLE reason, no result chart]                       |
|                                                                                                      |
| 03. SELECTED CONFIGURATION SUMMARY                                                                   |
| Case / Configuration / Execution / Method / params / selected count: UNAVAILABLE / CV / provenance   |
| [View Evaluation in Phase 5 >]               [Use this Model in Phase 6 >]                            |
| If no linked evaluation: explain NOT EVALUATED. If no registered/deployable model: show reason.      |
+------------------------------------------------------------------------------------------------------+
~~~

**Control behaviors, additive to original Phase 4 contract:**
- \`View Evaluation in Phase 5\`: never calls API or computes metrics; navigates with exact case/run context; unsupported Phase 5 shows pending/unavailable scoped to that run, **not** Ames scores from another run.
- \`Use this Model in Phase 6\`: navigates with case/run context and looks up approved registry entry; if zero eligible models, show Phase 6 availability panel, **not** a broken editable prediction form; if multiple approved versions, show a model selector with permitted exact IDs; if one, preselect it.
- \`Return to Modeling\` on Phase 6 restores prior selected configuration and dynamically derived controls, including the complete valid parameter tuple. This restores view state, **does not restart training**.
- K in CV folds is different from Top K for features; label \`CV Folds: 3\` read-only, \`Top K\` method-specific. Options, when available, are derived from exact configuration tuples.
- Do **not** make the Phase 5 handoff imply Phase 5 governance is already authorized or its Issue exists; it is an interface contract and placeholder.

