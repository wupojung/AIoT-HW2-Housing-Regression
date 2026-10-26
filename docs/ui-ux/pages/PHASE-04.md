# Phase 4 — Modeling

**Current detailed UX; docs-only. IMPORTANT ID CORRECTION:** historical UI-facing `run_id` means **configuration_id**; original research run maps to **execution_run_id**. See [canonical contract delta](../REGSCOPE-CONTRACT-REVIEW-DELTA.md). Text below preserves detailed interactions; corrected identities take precedence.

## Phase 4 — Modeling / 模型建立：詳細 ASCII Wireframe + JSON Contract v1.0

**Owner-approved design direction (2026-10-26), DOCS ONLY.** This detailed section controls Phase 4 over the earlier abbreviated Phase 4 diagram, while preserving earlier scientific/evidence/governance safeguards. No implementation, model rerun, holdout use, merge or deployment is authorized.

### A. Purpose, terminology and placement

Phase 4 teaches **(1) how the Training Set was cross-validated, (2) which feature-selection methods and configurations were ACTUALLY run, and (3) what documented feature choices and CV outcomes resulted**. It must not imply that a visitor changing a dropdown trains a model.

- **Training Set:** 1,168 labeled Ames rows (80% of the source 1,460; called Development Set in prior research artifacts). Phase 4's UI-facing label is **Training Set**, preserving the \`development\` name in research provenance where needed.
- **Holdout Test Set:** 292 rows (20%), sealed and **not used in Phase 4 selection, CV, or tuning**; final approved evaluation belongs in Phase 5.
- **Kaggle competition test:** 1,459 separate *unlabeled* rows, not part of the 80:20 split or Phase 4 CV.
- **3-Fold CV:** three similarly sized parts of the 1,168-row Training Set. At each iteration, roughly **66.7% Training Folds** and **33.3% Validation Fold**, with the validation third rotating. Because 1,168/3 is not an integer, do not promise exact equal counts; actual fold counts from splitter artifacts should be preferred. The CV fold count is **recorded experiment metadata**, not a live-editable parameter.
- **Top K / selected encoded feature count** (method-specific selection parameter) is different from **CV folds (K-Fold)**. Do not introduce "Top P" without a documented actual method parameter. Alpha and Top K are **not schema-level either/or**: a method can declare 0, 1, 2 or more parameters.

### B. ASCII wireframe — PC Desktop 1920 × 1080 reference; vertical scrolling

~~~text
+----------------------------------------------------------------------------------------------------------------+
| RegScope                                     Home / CRISP-DM                      [Dashboard]                  |
| Research dataset: [ Ames Housing v ]                                                                           |
| [01 Business] [02 Data] [03 Preparation] [04 Modeling ★] [05 Evaluation] [06 Deployment]                      |
+----------------------------------------------------------------------------------------------------------------+
| PHASE 04 / MODELING                                                                                             |
| 模型建立與特徵選擇：如何驗證訓練資料、選出特徵，並比較模型？                                                       |
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
| | Research perspective: [Method Comparison*] [Selected Features] [Feature Count vs CV RMSE]                    | |
| |                                                                                                            | |
| | Feature Selection Method: [ Pearson v ]                                                                     | |
| | Method parameters — GENERATED from method.parameters[]; 0 to N controls, wrap into rows as required:        | |
| | [ Top K: 5 v ]                (Pearson example only)                                                          | |
| |                                                                                                            | |
| | Selecting Elastic Net instead could show [Alpha: 100 v] [L1 Ratio: 0.8 v] (example supported run only).    | |
| | Selecting OLS baseline shows [No feature-selection parameters]                                              | |
| | Valid completed run: [run_id / protocol / availability / source]                                            | |
| +------------------------------------------------------------------------------------------------------------+ |
| | ONE PRIMARY RESULT PANEL — changes with research perspective                                               | |
| | A) Method Comparison: compared method/compatible run → CV RMSE plot/table (only actual metrics).           | |
| | B) Selected Features: documented encoded feature IDs, original source mapping, count and method outcome.    | |
| | C) Feature Count vs CV RMSE: x = selected encoded count, y = measured CV RMSE, actual points only.          | |
| | [Source / run identity] [Metric scope] [Limitations] [UNAVAILABLE reason where necessary]                    | |
| +------------------------------------------------------------------------------------------------------------+ |
|                                                                                                                |
| ③ EXPERIMENT CONFIGURATION (read-only)                                                                            |
| +------------------------------------------------------------------------------------------------------------+ |
| | Method ID   | Actual selected configuration | Selected encoded count / method-defined                       | |
| | CV protocol | Fold count | Scoring | Train data/version | Run ID | Hyperparameters | Track / provenance       | |
| | [Expand experiment details v]                                                                                | |
| +------------------------------------------------------------------------------------------------------------+ |
| [< Previous Phase: Data Preparation]                                                [Next Phase: Evaluation >]   |
+----------------------------------------------------------------------------------------------------------------+
~~~

**Presentation details**
1. The CV diagram uses the **same quantitative 100%-horizontal-bar language** as Phase 3, but its unit is **ROWS within training folds**, NOT feature columns. Three bars represent one 3-fold CV protocol, not three independent train/test splits or three selections of a different dataset. Segment widths are equal-ish by actual fold-size data; in schematic view use approximate 33.3%, with explanatory note. Show 66.7% aggregate training versus 33.3% validation per run below the bars. Colors and labels visible without relying on color alone.
2. Phase 4 has **one selected result perspective** at a time; do not render all comparison figures simultaneously. Dynamic controls appear in the same form below that perspective's selector; changing parameters swaps the selected evidenced run, its results and config together. Each result panel has explicit run/protocol/metric identity and an availability state.
3. Do not assert that every parameter value in a numeric range is supported. **Dropdown choices reflect recorded, completed, eligible runs**, not a synthetic Cartesian product. A method with \`alpha\` + \`l1_ratio\` may have only one valid pair. If no run matches, show UNAVAILABLE and disable outcome rather than invent a score.
4. CV comparison must show a compatible method/config/protocol/track population. Lasso/Elastic Net are not inherently fixed-Top-K selectors; selected encoded counts can be method-defined, while Pearson/Mutual Information/Ridge-RFE may use explicit \`top_k\`/requested selection counts when verified. A method's hyperparameter label is taken from its own schema.
5. A visible method list MAY show Lasso, Pearson, Mutual Information, Ridge-RFE, Elastic Net, OLS Baseline for Ames when backed by actual run records. **OLS is a baseline without selection-specific params**, and should not silently be counted as a sixth feature-selection algorithm.
6. Actual CV primary scoring metric is CV RMSE for current research design. Define lower-is-better and label units when verified; do not put Holdout RMSE or unreviewed test scores on Phase 4 charts. Display fold SD only if it exists.
7. Source/citation, error and accessibility behavior follows the document-wide LOADING / EMPTY / ERROR / PLANNED / MOCK / UNAVAILABLE / VERIFIED state contract. A panel is not VERIFIED merely because a parameter definition exists.

### C. Every interactive control and behavior

| Control | Position | Action | Reset/guard |
|---|---|---|---|
| Global Research Dataset | shared header | Change \`case_id\`, replace *all* Phase 4 method definitions, runs, protocol, outcome and metadata | Reset method, params, selected run and result perspective to supported defaults; never leak Ames values to another case |
| Phase navigation 01–06 | shared header | Navigate within current case | Preserve \`case_id\`; Phase 4 always uses recorded current-case protocol |
| 3-Fold summary | top card, read-only | Displays \`cv.folds\`, Training Set rows and scoring | NOT a selectable number of folds; unsupported protocol -> UNAVAILABLE |
| Expand CV methodology | below three fold bars | Accordion click toggles protocol, actual fold sizes if recorded, splitter type, shuffle, seed, fitting isolation, evidence | Collapsed initially; metadata missing -> explicit UNKNOWN |
| Perspective tabs | top of Explorer | Switch exactly one result panel: method comparison / selected features / feature count vs CV | Keep method + valid selected run when panel supports it; otherwise show unavailability, never stale chart |
| Method dropdown | Explorer | Select method among registered case methods | Recompute available parameter controls and eligible runs; reset all incompatible parameter values and prior result |
| Each parameter dropdown | Explorer; dynamically repeated per method | Select one **allowed value** for that parameter | Options filtered to values of real available compatible run tuples; later param changes cannot create non-existent combo |
| 0-parameter method | Explorer | Show concise “No feature-selection parameters”; select compatible default run | Don't render inert/blank dropdowns |
| Selected run/evidence link | result header | Open traceable public run record if approved | Missing source: disabled with reason; do not expose local paths |
| Expand experiment details | configuration card | Toggle full documented params, target, selected counts, CV protocol, track, run evidence and limitations | Missing values explicit UNKNOWN; no hardcoded metadata |
| Previous Phase | footer | Go Phase 3 | Same case |
| Next Phase | footer | Go Phase 5 | Same case; Phase 5 independent holdout gate |

**Selection algorithm (UI-only, no fitting):** on method change, choose first eligible recorded run (or show UNAVAILABLE); read its complete param tuple, then populate the controls. On parameter change, filter \`runs[]\` by \`method_id\`, full recorded param tuple and relevant compatible CV protocol; update all other controls to a valid evidenced tuple or show no compatible run. **Never** silently preserve invalid old param combinations. Optional \`default_run_id\` must point to an eligible run. A dataset change invalidates caches/charts/results from previous case. If method definition exists without published run, it may be labeled PLANNED/UNAVAILABLE and disabled.

### D. Fixed JSON shape, extensible methods and immutable runs

This is the **proposed structural contract**, not a verified raw experimental artifact. Method names and parameters are examples of mappings; source-backed options MUST come from run inventory and research QA. No invented scores are provided.

~~~json
{
  "phase4": {
    "cv": {
      "protocol_id": "development-3fold-cv",
      "folds": 3,
      "training_set_rows": 1168,
      "holdout_test_rows": 292,
      "metric": "rmse",
      "splitter": null,
      "shuffle": null,
      "random_seed": null,
      "fold_sizes_ref": null,
      "evidence_ref": null
    },
    "default_perspective": "method_comparison",
    "perspectives": [
      "method_comparison",
      "selected_features",
      "feature_count_vs_cv"
    ],
    "methods": [
      {
        "id": "pearson",
        "label": "Pearson",
        "kind": "feature_selection",
        "parameters": [
          {
            "id": "top_k",
            "label": "Top K",
            "type": "integer",
            "control": "select",
            "options": [2, 3, 5, 10, 20]
          }
        ]
      },
      {
        "id": "lasso",
        "label": "Lasso",
        "kind": "feature_selection",
        "parameters": [
          {
            "id": "alpha",
            "label": "Alpha",
            "type": "number",
            "control": "select",
            "options": [100]
          }
        ]
      },
      {
        "id": "elastic_net",
        "label": "Elastic Net",
        "kind": "feature_selection",
        "parameters": [
          {
            "id": "alpha",
            "label": "Alpha",
            "type": "number",
            "control": "select",
            "options": [100]
          },
          {
            "id": "l1_ratio",
            "label": "L1 Ratio",
            "type": "number",
            "control": "select",
            "options": [0.8]
          }
        ]
      },
      {
        "id": "ols_baseline",
        "label": "OLS Baseline",
        "kind": "baseline",
        "parameters": []
      }
    ],
    "runs": [
      {
        "run_id": "example-pearson-k5",
        "method_id": "pearson",
        "params": {"top_k": 5},
        "cv_protocol_id": "development-3fold-cv",
        "status": "MOCK",
        "metrics_ref": null,
        "selected_features_ref": null,
        "evidence_ref": null
      }
    ],
    "default_run_id": null
  }
}
~~~

**NON-EMPIRICAL WARNING:** the \`example-pearson-k5\` run and its \`MOCK\` status exist **solely to show the schema shape**. It MUST NOT be loaded as an actual published run. The \`options\` values above are illustrative mappings based on the research-method discussion; DO NOT claim that every possible tuple is present, admissible or verified. In implementation, \`runs\` must be built from real immutable manifests. A safe production empty state is \`runs: []\`, no default run and disabled results.

**Scalable schema rules**
- \`methods[]\` is an arbitrary-length array; adding a new method requires a new \`id\`, \`label\`, \`kind\` and \`parameters[]\` entries, not front-end branching by hardcoded method names. \`parameters[]\` may have any number of items; render ordered controls from metadata. Param identifiers are method-scoped.
- \`options[]\` describes UI-value candidates but **is NOT independent proof that every combination was run**. \`runs[]\` is the only source of legitimate parameter **tuples**. The final UI may derive each parameter's visible options from eligible runs rather than trusting the illustrative \`options[]\` catalog.
- \`run_id\` is stable and globally unique in a case; link to immutable run/protocol/metric artifacts. A valid measurable result needs appropriate QA/publication approval and provenance. Additive per-run fields include \`track\`, \`scoring\`, \`encoded_selected_count\`, \`pipeline_version\`, \`artifact_digest\`, \`feature_mapping_version\` where evidence supports them. Do not infer selected feature count = requested \`top_k\` without verifying actual output.
- In multi-case usage, embed this \`phase4\` under a root \`case_id\`, \`title\`, \`methodology_id\` manifest already defined in the Phase 1–3 reconstruction supplement. The root global Dataset picker always switches the whole case; no independent case selection inside Phase 4.
- Known \`cv.folds=3\` and \`training_set_rows=1168\` are Ames scoped; any new case supplies its own. \`random_seed=null\` in \`cv\` means splitter seed not yet independently established by this design, even though the Phase 3 80/20 split seed is 42: **do not silently assume they are the same**.
- Method selection is independent from evaluation approval and model deployability. This Phase 4 contract does not certify Holdout or Phase 6 inference eligibility.

### E. Phase 4 documentation acceptance checklist
- [ ] 3-fold bar graph conveys approximately 2/3 training and 1/3 validation **within** the Training Set, with each third serving validation once; exact fold-size caveat visible.
- [ ] Phase 3's 80/20 and Phase 4's 3-fold are distinct; Holdout Test Set never participates in CV; Kaggle competition test distinct.
- [ ] All method/parameter controls are generated from case JSON; zero, one, two or many parameters are supported without changing the UI.
- [ ] No unrestricted Cartesian combination of Alpha/L1 Ratio/Top K unless exact matching eligible completed run exists.
- [ ] One of three result perspectives displays at a time; selection swaps method, run, source and result atomically.
- [ ] Selected encoded features are not equated with raw feature count, and \`top_k\` is not treated as CV folds.
- [ ] Evidence/verification/UNKNOWN/UNAVAILABLE statuses apply to all run results and controls; no MOCK results presented as empirical.
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
| 02. EXPLORE AN ACTUAL RESEARCH RUN                                                                   |
| Perspective: [Method comparison] [Selected features] [Feature count vs CV]                           |
| Method: [Pearson v]                                                                                  |
| Dynamic parameter controls: [Top K: 5 v] OR [Alpha v][L1 Ratio v] OR no controls as method requires   |
| Resolved valid run: [run_id] [status]  [link to public evidence]                                      |
| [ONE verified/available CV chart or feature table; otherwise explain UNAVAILABLE]                    |
|                                                                                                      |
| 03. SELECTED RUN SUMMARY                                                                             |
| Case / Run / Method / actual params / selected encoded count / CV protocol / track / provenance       |
| [View Evaluation in Phase 5 >]               [Use this Model in Phase 6 >]                            |
| If no linked evaluation: explain NOT EVALUATED. If no registered/deployable model: show reason.      |
+------------------------------------------------------------------------------------------------------+
~~~

**Control behaviors, additive to original Phase 4 contract:**
- \`View Evaluation in Phase 5\`: never calls API or computes metrics; navigates with exact case/run context; unsupported Phase 5 shows pending/unavailable scoped to that run, **not** Ames scores from another run.
- \`Use this Model in Phase 6\`: navigates with case/run context and looks up approved registry entry; if zero eligible models, show Phase 6 availability panel, **not** a broken editable prediction form; if multiple approved versions, show a model selector with permitted exact IDs; if one, preselect it.
- \`Return to Modeling\` on Phase 6 restores prior selected run and dynamically derived controls, including the complete valid parameter tuple. This restores view state, **does not restart training**.
- K in CV folds is different from Top K for features; label \`CV Folds: 3\` read-only, \`Top K\` method-specific. Options are derived by \`run_id\` inventory.
- Do **not** make the Phase 5 handoff imply Phase 5 governance is already authorized or its Issue exists; it is an interface contract and placeholder.

