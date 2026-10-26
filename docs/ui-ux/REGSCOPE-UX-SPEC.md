> **CANONICAL ENTRYPOINT (2026-10-26):** Start at [REGSCOPE-RECONSTRUCTION-INDEX.md](./REGSCOPE-RECONSTRUCTION-INDEX.md). Earlier sketches and phase 4 per-parameter “run_id” examples are **HISTORICAL / SUPERSEDED** where they conflict with [REGSCOPE-CONTRACT-REVIEW-DELTA.md](./REGSCOPE-CONTRACT-REVIEW-DELTA.md). Phase 5 final UI and Dashboard full UI are NOT reconstruction-approved. This remains docs-only.

# RegScope — UI/UX Design Specification v0.3

Status: Owner-confirmed concept, **P6-A docs-only / no engineering authorization**.
Date: 2026-10-26. Tracking: https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/34

## Design rationale
RegScope is a CRISP-DM-first research teaching site: explain how the work was done and why decisions were made. A separate Dashboard is a secondary integrated analysis workspace, not an alternate dashboard mode for each CRISP-DM phase. Avoid overwhelming learners with all charts at once.

## Confirmed interaction contract
- Home initially opens Phase 1. Six clear steps 1–6 sit in **one horizontal desktop row**, left to right. Never wrap them into two desktop rows. For narrow screens, horizontal scrolling is a candidate, not yet final.
- Clicking a numbered step updates one large lower content panel. Previous/Next permits sequential reading.
- A global **research-case** selector above the six steps switches the *entire recorded study*; only cases with documented evidence appear. Never imply that an arbitrary uploaded CSV has a complete research history.
- Right upper navigation goes to separate **Dashboard**, whose dense overview may contain two preset problems and a custom CSV/direct-URL dataset loader for the instructor's bonus requirements.
- Each phase: guiding question, method/decisions, one primary display, takeaway, expandable detailed evidence. Show source and status.
- Phase 4: research conclusion first; choose one of (method comparison, selected features, feature count vs CV performance). Allow method/Top K only for truly computed combinations; collapse complete experiment matrix. Do not show all graphs in one view.
- Phase 6: provide links/downloads to reviewed, licensed, public-safe outcomes and reproduction documentation.

## Research controls
- Distinguish preprocessing column cleanup in Phase 3 from model-based feature selection in Phase 4.
- Feature-selection result for Top 3 cannot be faked by slicing Top 5; some methods (e.g. Lasso) cannot guarantee exactly K selected features.
- Training/CV, model selection and final sealed holdout must remain separate. Do not claim model superiority, real RMSE, or holdout result without evidence and Owner gate.
- Correctly label confidence vs prediction intervals; don't fabricate uncertainty bands.
- Label verified / mock / planned / unavailable visibly, including charts and downloads.
- Uploaded datasets need schema, target/feature validation, preprocessing policy, size/security limits and failure states; raw CSV loading alone is not successful analysis.

## ASCII wireframe — HOME

~~~text
+--------------------------------------------------------------------------------+
| RegScope                                                   Home  [Dashboard]   |
+--------------------------------------------------------------------------------+
| CRISP-DM Research Journey                                                      |
| How did we move from raw data to a regression model?                           |
| Research case: [ Ames Housing v ]                                               |
|                                                                                |
| +-----------+-----------+-----------+-----------+-----------+-----------+      |
| |     1     |     2     |     3     |     4     |     5     |     6     |      |
| | Business  | Data      | Data      | Modeling  | Evaluation| Deployment|      |
| | Understand| Understand| Preparation|          |           |           |      |
| +-----------+-----------+-----------+-----------+-----------+-----------+      |
|                                                                                |
| +--------------------------------------------------------------------------+   |
| | PHASE N: Guiding question                                                |   |
| | Method and decisions; provenance / verified-or-unavailable status         |   |
| | [ONE primary figure, interaction, or explanation]                        |   |
| | [Expand methodology and evidence v]                                      |   |
| | [< Previous]                                             [Next >]         |   |
| +--------------------------------------------------------------------------+   |
| GitHub | NotebookLM summary | GPT PDF | attribution                         |
+--------------------------------------------------------------------------------+
~~~

## ASCII wireframe — DASHBOARD (separate route)

~~~text
+--------------------------------------------------------------------------------+
| RegScope                                     [< Back to CRISP-DM Home]          |
+--------------------------------------------------------------------------------+
| Dashboard — integrated regression analysis                                    |
| Problem [Preset 1 / Preset 2 v]  OR Dataset [CSV upload / direct URL input]    |
| Target [select]  Features [select]  [Validate] [Run if supported]              |
| [Load status, errors and supported/unsupported notices]                        |
| +----------------------+----------------------+---------------------------+    |
| | Dataset overview     | Feature selection    | Metrics                   |    |
| +----------------------+----------------------+---------------------------+    |
| | Prediction visual / verified CI or PI when justified; else unavailable  |    |
| +--------------------------------------------------------------------------+    |
| | Reproducibility, provenance, limits, run status                           |    |
| +--------------------------------------------------------------------------+    |
+--------------------------------------------------------------------------------+
~~~

## All six phase wireframes

### Phase 1 — Business Understanding / 業務理解
~~~text
+------------------------------------------------------------------+
| PHASE 1: Why is this prediction problem worthwhile?              |
| [Research problem] [Prediction target] [Success criteria]        |
| [Why this dataset?] [Scope and limitations]                      |
| [Evidence / sources v]                                           |
| [< Previous]                                         [Next >]     |
+------------------------------------------------------------------+
~~~
Content: research motivation, dataset source, target SalePrice (Ames case), objectives, explicit limitations.
Interaction: choose documented research case globally, read problem and supporting sources.

### Phase 2 — Data Understanding / 資料理解 (EDA-driven redesign v0.3)

**OWNER CONFIRMED:** CRISP-DM Home stays the primary six-step teaching journey, with one Phase content panel and progressive disclosure. **DESIGN PROPOSAL:** replace the old generic EDA panel with verified finding → interpretation/limitation → downstream hypothesis navigation.

~~~text
+--------------------------------------------------------------------------------+
| PHASE 2 / DATA UNDERSTANDING       [VERIFIED EDA / QA PASS] [Ames Housing]      |
| What did we discover BEFORE cleaning or modeling?                              |
| Population: Kaggle train 1,460 / test 1,459 | Source: Phase 2 report [view]     |
|                                                                                |
| KEY FINDINGS (verified observations; see individual denominators below)        |
| 79 candidate raw features | SalePrice right-skew | NA semantics differ         |
| Correlations / predictor collinearity are signals, NOT model rankings          |
|                                                                                |
| Insight: [Dataset Profile] [SalePrice] [Missingness] [Correlation]             |
| +--------------------------------------------------------------------------+   |
| | ONE PUBLIC QA-REVIEWED FIGURE: FIG-01 / 03 / 02 / 06                     |   |
| | [Figure title + observed population/denominator + accessible table]       |   |
| | [Evidence URL] [SVG/PNG alternative] [status and source/version]         |   |
| +--------------------------------------------------------------------------+   |
| +-------------------+-----------------------+------------------------------+  |
| | VERIFIED FINDING  | INTERPRETATION +      | NEXT HYPOTHESIS             |  |
| | quantified facts  | methodological caveat | [CANDIDATE / UNCONFIRMED]  |  |
| +-------------------+-----------------------+------------------------------+  |
| [Inspect Phase 3 hypothesis] [Inspect Phase 4 comparison]                       |
| [Expand method, figures, QA/report and provenance v]                            |
| [< Previous]                                                     [Next >]      |
+--------------------------------------------------------------------------------+
~~~

**Four insight choices / exactly one principal figure at a time:**

| Insight / selection | Reviewed public figure | Primary verified observation (scope, denominator, units) | Interpretation and limit | Candidate next action (NOT adopted by this card) |
|---|---|---|---|---|
| Dataset Profile (default, DESIGN PROPOSAL) | [FIG-01](https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/main/docs/crisp-dm/assets/phase2/fig01_dataset_overview.png) | Kaggle train **1,460 rows × 81 columns** (includes Id/SalePrice); competition test **1,459 × 80** (has no SalePrice); **79 original candidate features** excluding Id/target. Id duplicates **0** in either file and overlap **0**; dictionary crosswalk **79/79** (77 exact + 2 aliases). | Descriptive schema and integrity checks only, not CV/holdout scores. Kaggle test ≠ **292 sealed internal holdout** ≠ **1,168 Development**. | Phase 3: design permitted split and train-fold-safe pipeline; see evidence before claiming adoption. |
| SalePrice Distribution | [FIG-03](https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/main/docs/crisp-dm/assets/phase2/fig03_saleprice_distribution.png) | **Train N=1,460** target in USD: mean **180,921.20**, median **163,000**, population-moment skewness **1.881**, 1.5×IQR upper fence **340,037.50 USD**, **61 upper-fence outlier candidates**, maximum **755,000 USD**. | Right-skewed *marginal target distribution* does **not** prove residual non-normality/heteroscedasticity, mandate log transformation, or justify dropping 61 rows. | Phase 3: investigate log1p target transform and inverse-transform reporting; decision **CANDIDATE HYPOTHESIS** until supported by downstream evidence. |
| Missingness Semantics | [FIG-02](https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/main/docs/crisp-dm/assets/phase2/fig02_missingness_overview.png) | Original literal \`NA\` cells: **train 6,965** and **test 7,000**; **15 structurally absent facility fields** by dictionary. Train examples: PoolQC **99.52%**, Alley **93.77%**, Fence **80.75%**, FireplaceQu **47.26%**, garage-related **5.55%**, basement-related around **2.53%**. LotFrontage **17.74% of train (259/1,460)** represents unrecorded measurement, not facility absence. | 'No pool/garage/basement' ≠ 'measurement unknown'; blanket global mean fill could erase meaningful absence; categories/field context matter. Test-only missingness also exists. | Phase 3: compare explicit absence category/zero against fold-trained imputers for genuine unknowns, and maintain leakage isolation. **Not an adopted policy merely from EDA.** |
| Correlation & Collinearity | [FIG-06](https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/main/docs/crisp-dm/assets/phase2/fig06_numeric_correlation_heatmap.png) | Train pairwise-complete Pearson with SalePrice: OverallQual **0.7910**, GrLivArea **0.7086**, GarageCars **0.6404**, GarageArea **0.6234**, TotalBsmtSF **0.6136** (each pairwise **N=1,460** for these five). Predictor pairs: GarageCars/GarageArea **0.882**, GrLivArea/TotRmsAbvGrd **0.825**, TotalBsmtSF/1stFlrSF **0.820**. Garage and basement groups show co-missingness. | Pearson r is association, **not causation, adjusted coefficient, importance ranking or Phase 4 winner**. Collinearity calls for testing, not automatic deletion. | Phase 4: compare feature selection/regularization or paired-feature sensitivity in **compatible, verified** CV; remain **CANDIDATE HYPOTHESIS** until research supports a result. |

**Evidence and state semantics — DESIGN PROPOSAL:**
- Only published and reviewed FIG-01, FIG-02, FIG-03, FIG-06 (PNG/SVG) may be used for this design. 87 local figure items exist in full EDA (174 PNG/SVG files); 83 nonpublic figure items, local datasets and row-level artifacts in ignored \`local/\` are **not** public downloads or UI assets. Don't synthesize new charts from private data.
- Single selectable insight updates the **figure, measured facts, interpretation, limitation and next-action links atomically**. Case switch invalidates prior findings; unsupported case/figure yields UNAVAILABLE with reason and report reference, not fallback Ames values.
- **VERIFIED OBSERVATION** means a cited Phase 2 descriptive statistic; **CANDIDATE HYPOTHESIS** means a downstream option not automatically adopted; **ACCEPTED DOWNSTREAM DECISION** appears only if an independently approved Phase 3/4 evidence link exists, identifying decision ID, phase, status and exact source. No adopted decision is claimed by this design.
- FIG-01 etc. are public aggregate images; figures must offer alt description and **keyboard-accessible, screen-reader-readable alternate table** with population and units. Charts never expose raw rows. Small screens stack finding/interpretation/next-action cards vertically, keep one chart and a scrollable/accessible insight selector; precise breakpoint ENGINEERING TBD.
- All states follow shared LOADING / EMPTY / ERROR / PLANNED / MOCK / UNAVAILABLE / VERIFIED contract. LOADING clears prior chart and facts; MOCK bears persistent visible/in-figure \`MOCK / 示意\` watermark and cannot be mistaken for the verified figures; missing or non-public figures become UNAVAILABLE with no fabricated chart. Source link and denominator remain adjacent to displayed facts. Navigation link into Phase 3/4 identifies *hypothesis to inspect*, never asserts it was accepted.

**Minimal EDA finding payload (DESIGN PROPOSAL; read-only, aggregate, additive to shared case/run contract):**

| Key | Meaning / validation |
|---|---|
| \`finding_id\` | stable unique ID per verified finding or hypothesis |
| \`figure_id\` | FIG-01 / FIG-02 / FIG-03 / FIG-06, or null if unavailable |
| \`case_id\`, \`source_url\`, \`source_version\` | Ames study + exact public Phase 2 source, no local paths |
| \`observation_name\`, \`value\`, \`unit\`, \`population\`, \`denominator\` | number/string/null as meaningful; population = Kaggle train/test explicitly, never implied Development/Holdout |
| \`evidence_url\` | approved public report/figure provenance |
| \`statement_kind\` | \`verified_observation\` / \`candidate_hypothesis\` / \`accepted_downstream_decision\`; latter needs downstream decision evidence |
| \`linked_phase\`, \`decision_status\`, \`decision_evidence_url\` | Phase 3/4, \`candidate\` / \`accepted\` / \`rejected\` / \`unavailable\`; absent evidence cannot be accepted |
| \`limitation\`, \`ui_status\` | explicit caveat and shared UI status |

The data may map onto the pre-existing aggregate [EDA QA/Dataset Health contract](https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/main/docs/qa/EDA_QA_AND_DATASET_HEALTH_CONTRACT.md); this is **not** a request to alter EDA Runner, generate new figures or publish private manifests. The 2026-10-24 [official Phase 2 report](https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/main/docs/crisp-dm/02-data-understanding.md) records empirical profiling/independent QA **PASS**, while PM Review/Epic Closeout is **PENDING** in that document. Do not render this as 'all Phase 2 governance gates closed'.

### Phase 3 — Data Preparation / 資料準備
~~~text
+------------------------------------------------------------------+
| PHASE 3: How were raw data transformed responsibly?              |
| [Raw data] -> [Cleaning, encoding, splitting] -> [Model-ready]    |
| Treatment/decision: [documented step v]                          |
| [Before / After with actual numbers or unavailable]              |
| [Reason for decision, leakage controls and audit v]              |
| [< Previous]                                         [Next >]     |
+------------------------------------------------------------------+
~~~
Interaction: choose a documented preparation decision, see actual before/after and rationale.

### Phase 4 — Modeling / 模型建立
~~~text
+------------------------------------------------------------------+
| PHASE 4: How did we select candidate features and models?        |
| [Takeaway: supported result or unavailable]                      |
| Question: [Methods] [Selected features] [K vs CV performance]    |
|                                                                  |
| [ONE main result/chart for current question only]                |
| Method [available method v]   Features [supported Top K v]        |
| [Selected features or CV-RMSE vs K curve; verified runs only]     |
| [Expand full experiment matrix and traceable settings v]         |
| [< Previous]                                         [Next >]     |
+------------------------------------------------------------------+
~~~
Method selector: only methods supported by the actual research. K selector: only truly run combinations. Metrics label CV protocol/folds/track; no invented curve points.

### Phase 5 — Evaluation / 模型評估
~~~text
+------------------------------------------------------------------+
| PHASE 5: How well does the approved model generalize?            |
| [Approved model] [MAE] [RMSE] [R2] [Adjusted R2 if valid]         |
| [Actual vs predicted + justified CI or prediction interval]     |
| [Residual diagnostics and method limitations v]                  |
| [Holdout not available until approved evaluation gate]           |
| [< Previous]                                         [Next >]     |
+------------------------------------------------------------------+
~~~
Interaction: optional switch between approved evaluated candidates. No premature holdout, fake uncertainty or leakage.

### Phase 6 — Deployment / 模型部署與房價預測實驗室 (Owner-approved direction)

**OWNER CONFIRMED (2026-10-26):** Phase 6 primary purpose is an actual *inference experience*: select a documented dataset/model, enter housing attributes and ask a Prediction API for a price estimate. Download/reproducibility links remain secondary. This supersedes the earlier downloads-only emphasis but does **not** authorize creation or public release of an API. Design for a **PC 1920 × 1080 Full HD reference viewport**; mobile/RWD implementation is **DEFERRED**, not a current acceptance gate. Maintain keyboard operation/readability on desktop.

~~~text
+--------------------------------------------------------------------------------------------------+
| RegScope                                                          Home  [Dashboard]              |
+--------------------------------------------------------------------------------------------------+
| CRISP-DM  1 -- 2 -- 3 -- 4 -- 5 -- [6 Deployment selected]                                      |
|                                                                                                  |
| PHASE 6 / 房價預測實驗室  | Prediction API [NOT DEPLOYED until verified]                         |
| Select study dataset: [ Ames Housing v ]   Selection: [ eligible run / method+config v ]         |
| Model version: [ currently unavailable / approved model_id ]  [Model metadata / evidence]       |
| NOTE: CV experiments are not automatically deployable models.                                   |
|                                                                                                  |
| +--------------------------------------------+ +----------------------------------------------+  |
| | 房屋條件輸入                               | | 預測結果                                     |  |
| | GrLivArea (sq ft)   [            ]          | | [UNAVAILABLE until approved API/model]      |  |
| | OverallQual (1-10) [            ]          | | Predicted SalePrice: -- USD                 |  |
| | GarageCars          [            ]          | | Prediction interval: unavailable           |  |
| | YearBuilt           [            ]          | | Model version / input schema / timestamp   |  |
| | [More required raw input fields / defaults] | | Evidence / limitations / non-appraisal     |  |
| | [Validate inputs] [Predict (disabled TBD)]  | | [error/loading/invalid input details]      |  |
| +--------------------------------------------+ +----------------------------------------------+  |
| [Reproducibility, source/license, reviewed model card, GitHub, approved safe downloads v]       |
| [< Previous]                                                                                   |
+--------------------------------------------------------------------------------------------------+
~~~

**DESIGN PROPOSAL:** The named raw-input fields above are *illustrative only*. The 97 selected **encoded** features cannot be equated to 97 human input widgets or safely reconstructed from only these four example fields. Schema determines required raw columns, defaults, allowable category values, missing indicators, encoders, scaling, feature names and order. **Never fabricate absent inputs or arbitrary defaults.**

#### Variable hierarchy and read-only research dataset selection

| Layer | Frontend role | Backing identity / constraint |
|---|---|---|
| Study case / dataset | First dropdown: case with available studies | stable \`case_id\`; changing case clears downstream experiment/model/prediction/results |
| Feature-selection experimental run | Second dependent dropdown, human label = method + config + applicable K/alpha + track/protocol | unique \`run_id\` in reviewed experiment manifest; **only measured** options, no Cartesian product generated on client |
| Evaluated model | read-only result for selected run or an additional selector only when multiple *explicitly approved and comparable* model artifacts exist | \`model_id\`, \`model_version\`, \`artifact_digest\`, \`eval_status\`, approved scope; a run may lack deployed model |
| Raw housing input | dynamically generated from **the chosen model's input schema**, not the selected encoded feature count | fields of numeric/ordinal/nominal types, units, bounds, required/optional, allowed values, imputation policy, validation |
| Prediction result | output from a single approved inference service/model | input validation, price unit, requested model, model version, status, provenance and interval only if separately validated |

**Important conceptual split:** Selection in Phases 2–5 primarily switches precomputed study **views**; no retraining. Phase 2's insight tabs aren't model-selection controls. Phase 4 can compare recorded Methods/K; Phase 5 displays *approved evaluation evidence* without turning Development CV into Holdout. Phase 6 performs **new inference on a user-supplied sample** only when a complete deployable pipeline exists; inference is not model training or candidate selection.

**Package B boundary:** The Development three-fold Lasso alpha=100 selected→OLS record and final Development fit metadata (97 encoded features; 1,168 Development rows) do not alone establish a portable trained inference model, complete preprocessing/input schema or authorized/verified Holdout performance. The handoff contains no loadable Joblib model. Thus the present UI stays **PLANNED / UNAVAILABLE** and cannot make a real prediction until explicitly approved artifacts and service are present. Never label all CV candidates as deployable; visible selector may show a candidate as **“研究結果可查，推論不可用”**.

#### Frontend catalog contract (DESIGN PROPOSAL)

Do **not** construct arbitrary method × K combinations. Use a single **versioned manifest JSON** as a catalog of *explicitly recorded* combinations, referring to artifact URLs and per-case evidence. This may be split into smaller JSON files without changing meaning. Identifiers are stable; labels are for display and may change.

~~~json
{
  "schema_version": "proposal-v1",
  "cases": [
    {"case_id": "ames-housing", "label": "Ames Housing", "status": "research_available"}
  ],
  "experiments": [
    {
      "run_id": "EXAMPLE-NOT-REAL",
      "case_id": "ames-housing",
      "method_id": "lasso",
      "method_label": "Lasso",
      "config": {"alpha": 100},
      "requested_encoded_k": null,
      "actual_encoded_k": null,
      "cv_protocol_id": "UNSPECIFIED",
      "track": "selected_to_ols",
      "evidence_status": "PLANNED",
      "deployable_model_id": null
    }
  ],
  "models": [],
  "note": "Illustrative schema only; the run ID and null values are NOT empirical records."
}
~~~

A real manifest must use **actual experiment IDs, measured K, source SHAs, protocol IDs and validation states** from reviewed evidence; the example above is intentionally nonempirical. Do not expose private file paths or embed 97-feature raw metadata without review. Dropdowns should be *dependent*: choose case → load recorded runs → display only eligible models or show unavailable. When switching case/run/model, invalidate old data, form, validation, forecast and any in-flight response. Errors and provenance must be visible.

**Prediction API concept only:** \`GET /api/models\` returns the eligible published model catalog and public input schemas; \`POST /api/predict\` receives a **registered model ID and validated raw input**. The server *selects only an allowlisted model*, performs the exact training-time preprocessing and feature-order mapping, infers with loaded coefficients/artifact, and returns predicted price + model version + scope. Never accept arbitrary file paths, unrestricted URLs or deserialization names as model choices. Small model size alone does not guarantee deployability; preprocessing pipeline, compatibility/security, runtime and model QA matter. Interval is optional only when specifically validated; never turn CV RMSE into a prediction interval.

**Phase 6 UI state:** if no approved artifact/API → PLANNED / UNAVAILABLE with explanation, disabled Predict and browsable research evidence. With an approved artifact: LOADING model/catalog, EMPTY if case has no model, ERROR on incompatible schema/inference, VERIFIED only for approved artifact provenance (not a guarantee of future forecast accuracy); predictions are explicitly labeled **model estimates**, not verified actual sales prices or appraisal.

#### Desktop specification amendment

**OWNER CONFIRMED:** PC-first layout with **1920×1080 Full HD reference**. Do not set fixed 1920px body width or assume browser viewport height equals 1080px; allow vertical scrolling. Preserve desktop usability in smaller browser windows without promising phone support. Mobile and specific responsive breakpoints remain **DEFERRED/ENGINEERING TBD**; prior small-screen horizontal-step scrolling is a nonbinding future proposal, not present P6-A/P6-B requirement.

## Future review acceptance checks (not engineering authorization)
- [ ] Every page/view has an ASCII wireframe and corresponding behavior/data rules.
- [ ] Six numbered desktop steps stay in one horizontal row and selection updates one content area.
- [ ] Dataset selection changes the study context across all phases; arbitrary user CSV stays in Dashboard.
- [ ] Phase 4 progressive disclosure and experiment-supported method/K behavior are clear.
- [ ] Phase 5 handles correct prediction interval or confidence interval and evidence status.
- [ ] Download links require provenance, review, licensing and public-safety check.
- [ ] Responsive, accessibility, loading/empty/error and data-contract details are reviewed before development.

## Unresolved details / not decisions
Second case identity, exact available methods/Top-K experiments, chart payloads, confidence/prediction interval method, supported upload formats/limits, breakpoint behavior, precise source artifacts, and final copy. Do not guess or claim these are implemented.

## Gate
Issue #34 currently authorizes planning only. This documentation does NOT authorize backend/frontend changes, Preview, production, OS/worker experiments, sealed holdout access, Merge or Deploy.


## P6-A Nex PARTIAL review remediation (design contract v0.2)

Review source: [Nex comment 6412376101](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35#issuecomment-6412376101).
Authority tags: **OWNER CONFIRMED** = previously approved concept; **DESIGN PROPOSAL** = testable UI recommendation, pending independent review; **ENGINEERING TBD** = capability or value requiring new authorization and evidence. No statement here certifies availability of a run.

### Authority and route matrix

| Item | Classification | Scope |
|---|---|---|
| CRISP-DM-first Home; numbered single-row desktop steps; one selected content panel | OWNER CONFIRMED | Must preserve |
| Global selector for documented research cases; separate secondary Dashboard | OWNER CONFIRMED | Must preserve |
| Phase 4 progressive disclosure, feature methods and evidence-backed Top K / performance curve | OWNER CONFIRMED | Must preserve |
| Phase 6 reviewed public-safe links/downloads | OWNER CONFIRMED | Must preserve |
| Conditional control reset rules, status labels, fallback displays, keyboard/scroll proposal | DESIGN PROPOSAL | Nex acceptance review |
| Second research case identity and completion, supported method/K values, derived chart points | ENGINEERING TBD | Verify against evidence; don't invent |
| Arbitrary CSV execution, secure URL fetching, limits, backend, interval construction | ENGINEERING TBD | Only design the guardrails; no implementation |

### BLOCKER 1 — Phase 4 interaction state machine

**DESIGN PROPOSAL** — One active question at a time. Use precomputed reviewed experiment artifacts only.

| Research question | Visible controls | Option source | Change rule | Main display |
|---|---|---|---|---|
| Methods (initial candidate) | method comparison selector if several comparable methods; protocol/track read-only | manifest of evaluated methods within same case + protocol + track | Changing question keeps case, clears incompatible method/K, selects first explicitly available comparable view; never silently picks a winner | method descriptions/comparable experiment table, one graph or table |
| Selected Features | method; K only where method supports **measured exact K**; protocol/track read-only | valid case+run+method+track+CV protocol entries with selected-feature artifact | Method changes reset K if unsupported; otherwise retain K only if exact measured tuple exists. Changing case resets question/method/K and unloads old output | selected raw/encoded feature mapping and recorded list for exact tuple |
| K vs CV | method; metric selector among stored CV metrics; encoded K as x-axis; protocol/track read-only | distinct observed K and CV folds in **one comparable protocol** | K may highlight existing point but does not create a point; method/protocol/case changes clear highlight/series until matching data exists | sparse observed-point chart; explicit missing K gaps and optional error bars |

The three questions are **tabs/choices**, not three simultaneous large plots. A display header must show selected case, protocol version, fold count, track and whether evidence is verified. Default question is a **DESIGN PROPOSAL**, not Owner-declared.

| Situation | UX response | Allowed action |
|---|---|---|
| Method supports no exact K (e.g., Lasso natural nonzero subset) | hide/disable K with “K 不適用（方法不保證固定 K）”; show actual nonzero count with raw vs encoded units | view native method diagnostics if verified; never synthesize Top K |
| Requested method+K not run | option disabled or absent, explain “尚無此組合實測” | no metrics/selected list |
| Run failed | ERROR with failure type, run ID and evidence link; cannot rank it | return to valid combination |
| Requested metric lacks point / fold missing | point omitted, table row “UNAVAILABLE — missing result”; line **breaks across gaps** | show only observed points, do not interpolate or join across missing K |
| Case/protocol changed | invalidate previous charts and tuple-based selections; show LOADING then EMPTY/VERIFIED as applicable | prevent stale metrics |
| Different protocol, folds, track or target transform | “不可直接比較” and separate chart/table facet | no merged ranking, no common winner |

**Curve contract — DESIGN PROPOSAL:** X = **number of encoded model-input columns selected (encoded K)** for the selected→OLS track, **not original raw feature count**. Display “encoded K” in axis, tooltip and table; raw-source feature count is a separate field/tooltip derived from mapping, never treated as equivalent. Y = one stored out-of-fold/CV metric (default CV RMSE, **lower is better**, in target units, transform/back-transform labeled). Optionally R² (**higher is better**) only if same compatible CV protocol produces it. Every plotted sample must identify method, experimental run ID, fold count, seed, protocol ID/version, track, mean and SD if valid; when SD unavailable show “SD unavailable”, not a fabricated band. Display fold-level count and uncertainty meaning; no generic CI shading. Only measured K points; noncontiguous K must not imply measured intermediate values. Evidence/provenance linked near chart and each table row.

**Track separation:** primary **selected feature set → OLS** comparison series; any method's **native estimator diagnostic** series is a distinct view/track (e.g., native Lasso coefficients), never overlaid as interchangeable OLS outcomes. Baseline OLS uses a separate explicitly labeled reference line/table entry only **if same case/target preprocessing/split/folds/metric/protocol**; historic five-fold baseline vs later three-fold research must be separated with a “non-comparable protocol” explanation. Never infer best-performing method from incompatible runs. No final holdout values without Phase 5 approval.

### BLOCKER 2 — Dashboard: source modes, state and security proposal

**OWNER CONFIRMED:** Dashboard is separate from CRISP-DM Home. **DESIGN PROPOSAL:** mutually exclusive source modes; fixed study evidence is read-only and cannot be modified by uploaded data.

~~~text
+-----------------------------------------------------------------------+
| DASHBOARD                                                              |
| Mode: [ Verified Research ] [ Custom Dataset (experimental) ]         |
|                                                                       |
| VERIFIED RESEARCH                                                     |
| Case [ documented case v ] | Run [reviewed run v] | [View evidence]    |
| [Dataset/feature/metric panels + provenance + fixed verified status]  |
|                                                                       |
| CUSTOM DATASET (experimental; capability TBD)                         |
| Source: ( ) Local CSV  ( ) Direct CSV URL [not Kaggle webpage]        |
| [Choose file / paste URL]   [Load]  [LOADING / ERROR / EMPTY]          |
| [Rows/columns/type preview] Target [v] Features [multi-select]        |
| [Validation report]  [Validate]  [Run — disabled until supported]     |
| [RUNNING / Cancel if supported / UNSUPPORTED]                          |
| [Session-only output; never “Verified Research”]                     |
+-----------------------------------------------------------------------+
~~~

| Event/state | Required UI behavior (DESIGN PROPOSAL) |
|---|---|
| Enter verified research | load only reviewed manifests; original case/run metadata read-only; never reuse custom-run results |
| Enter custom source | clear verified metric/result cards, show experimental disclaimer, source picker and requirements |
| Local CSV selected | validate file extension **and contents**, parseability, UTF-8/encoding handling policy, size/row/column budget (specific limits ENGINEERING TBD), headers/duplicate columns, blank or malformed rows and nonfinite values; show actionable errors |
| Direct URL submitted | accept only reviewed allowed HTTP(S) scheme plus URL security rules; reject private/loopback/metadata hosts, credentials, redirects to disallowed locations and untrusted content; do not promise browser CORS or network fetch works. Exact allowlist, redirects and proxy design ENGINEERING TBD |
| Preview loaded | show source provenance and preview only, not fitted model. Target must be numeric/convertible continuous; Features exclude target, have nonempty supported columns, and require an explicit missing/categorical encoding strategy; check leakage risk, sufficient rows versus encoded columns and invalid/missing target |
| Validate | separate **loaded** from **validated**. On invalid schema or unsupported preprocessing: ERROR/UNSUPPORTED with per-field reasons and repair instructions. No Run |
| Run | enabled **only if later engineered, authorized, secure and supported**; show RUNNING/progress if available, cancel request only if backend supports it, and explicit cancellation/failure result. Until then, button disabled with ENGINEERING TBD |
| Switch problem/case/file/URL/target/features/mode | immediately invalidate prior validation token, derived previews, cached model, selected-feature graph and metrics (no stale verified output); cancel in-flight task when supported, else mark stale and ignore late result |
| Network/CORS/memory/unsupported size | ERROR or UNAVAILABLE (not success); safe, non-sensitive reason, retry after correction only |
| Custom result shown | label “exploratory/unverified”, scope and exact current input/session; never record it as a completed CRISP-DM case or public certified run |

**ENGINEERING TBD:** whether custom data *can* run regression at all; accepted file types beyond CSV; upload byte/row/feature thresholds; server upload/retention, SSRF mitigation and cancellation backend. UX documents required safety checks without authorizing implementation.

### BLOCKER 3 — Minimal shared data contract (design only)

**DESIGN PROPOSAL** — manifest + per-run/visual/asset references. No real data values are asserted. Keys below are illustrative field names, not a Runner modification request.

| Entity | Minimum fields | Rule |
|---|---|---|
| Case | case_id, source_url, version, license, target, status, evidence_url | case identity and rights; source URL not arbitrary download URL |
| Run | run_id, digest/SHA, case_id, config_id, config_version, seed, split_id, protocol_id, fold_count, track, method_id, status, evidence_url | immutable lookup for experiment; distinguish selected_to_ols / native_diagnostic / holdout |
| Feature map | run_id, encoded_feature_id, raw_source_feature_id(s), encoded_selected_k, raw_distinct_count, feature_mapping_version | counts cannot be interchanged; trace back to original columns |
| Metric | run_id, metric_name, value, units, direction (min/max), fold_values if available, mean, sd if available, availability, evaluation_scope | unavailable fields are null/labelled, not zero; fold count and comparability explicit |
| Visual | visual_id, case_id, run_id(s), artifact_digest, chart_type, axis_definitions, interval_type + provenance if any, status, evidence_url | chart shows only points in its compatible experimental scope |
| Download | asset_id, sha, source_url, license, publication_review, sensitivity_review, mime/type, status, evidence_url | links enabled only for reviewed public-safe files |

Illustrative **state** is independent of method/result availability. Every component including step content, card, metric, chart, table and download must use the same state semantics:

| State | UX display / behavior | Evidence / watermark |
|---|---|---|
| LOADING | neutral skeleton/indicator; no old run visible; disable incompatible actions | run/source context shown, never fake numbers |
| EMPTY | no relevant records or zero rows; explain how to select a populated case | “No evidence/data” |
| ERROR | safe reason, remediation, retry if meaningful; no stale content | error type and run ID where safe, evidence link if any |
| PLANNED | specified concept not implemented or not yet studied; control disabled | “PLANNED — not empirical” |
| MOCK | sample illustration only; never ranked/merged with research | persistent obvious **MOCK / 示意資料** watermark on every affected graph/table/metric/export; accessible text, not color alone |
| UNAVAILABLE | source exists but required result, approval, compatible protocol or license is absent | “UNAVAILABLE” plus reason and nearest trustworthy source |
| VERIFIED | reviewed evidence exactly matches selected case/run/protocol and approved publication scope | visible VERIFIED label + source URL, run ID/digest and method; verified does not itself imply holdout approval |

**Component rules:** every phase panel has status and citation near its content; chart axes/legend/caption show units and provenance; table rows that are incomplete use cell-level UNAVAILABLE; metric cards state evaluation scope; downloads render disabled with reason unless status VERIFIED **and** publication_review/sensitivity_review/license allow sharing. A MOCK visualization must carry in-plot watermark and adjacent text; downloads of MOCK are either disabled or visibly marked non-empirical. Source links are safe/public links only.

**Cross-case comparison:** no shared leaderboard without compatible target, preprocessing, split, metric, CV protocol and track. Dashboard verified read-only runs can be compared only when this contract permits; custom runs cannot be promoted to VERIFIED via UI actions.

### Non-blocking mobile/accessibility proposal and review gate

**DESIGN PROPOSAL:** one row of six steps at desktop, and **horizontal scroll with visible overflow cue** for narrow screens (not six steps wrapped into two rows); breakpoint in px is **ENGINEERING TBD** after responsive inspection. Use native tablist/tab/tabpanel semantics *or* accessible equivalent navigation links, with numbered readable names, aria-selected/current, keyboard Left/Right to switch steps, Home/End and visible focus; clicking Previous/Next retains a meaningful focus position. Contrast meets WCAG AA target (4.5:1 normal text, 3:1 meaningful UI), no meaning by color alone. Every chart has a textual takeaway and **accessible alternative data table**; all error/watermark labels are screen-reader-readable. Touch target proposal >= 44×44 CSS px and no horizontal overflow of the whole page. Exact breakpoints, role choice and mobile behavior require independent QA before engineering.

### Review checklist for Nex

- [ ] Three Phase 4 research questions have state/selector/reset rules and unsupported cases.
- [ ] Curve explicitly uses encoded K and CV mean/SD or documented absence, with fold/protocol/track and non-comparability.
- [ ] Dashboard has isolated research vs custom source modes and validation/run/cancel/stale-result states.
- [ ] Minimal manifest/run/metrics/visual/download contract supports all seven statuses with visible source/Mock watermark.
- [ ] Mobile and accessibility rules are labeled as proposals; Owner/engineering boundaries clear.


## Nex P6-A v0.4 amendment — Generalized dataset / prediction contract

Source: [Nex PARTIAL comment](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35#issuecomment-6417360873). This **adds** to, and where more specific supersedes, earlier illustrative Ames/Phase 6 wording; the six-phase navigation, Phase 2/4 research design, reviewed evidence and Desktop 1920×1080 decision remain intact.

### P0-1 — Case-driven Model Prediction Lab (DESIGN PROPOSAL)

**OWNER CONFIRMED:** Phase 6 provides inference with an approved existing model, while the earlier "房價預測實驗室" layout is retained as the **Ames display preset**. **DESIGN PROPOSAL:** use a general heading "模型預測實驗室 / Model Prediction Lab" in the reusable container. Case metadata supplies display_title ("房價預測實驗室" for Ames), target_label (SalePrice), target_unit (USD), schema, explanatory description and eligibility badges. No hardcoded SalePrice, USD, house sizes or 97-feature assumptions for other cases.

~~~text
+------------------------------------------------------------------------------------------------+
| RegScope  HOME / CRISP-DM [1][2][3][4][5][6 Deployment]     PC Full HD 1920x1080 reference    |
| MODEL PREDICTION LAB                         Case title: [from case metadata]                  |
| Dataset / study: [Ames Housing v]            Target: [SalePrice] Unit: [USD]                    |
| Research run: [measured method+config v]   RESEARCH STATUS: [verified / unavailable]          |
| Deployable model: [approved model_id v / none] INFERENCE STATUS: [unavailable]                 |
|                                                                                                |
| +--------------------------------------------+ +---------------------------------------------+ |
| | Raw input form (from model input_schema)     | | Prediction output (case target/unit)       | |
| | Field 1 [value / unit / required marker]     | | [--] [target unit]                          | |
| | Field 2 [category / absent / unknown]        | | Run / model version / provenance           | |
| | [conditional fields / explanations]          | | Prediction interval only if approved       | |
| | [Validate] [Predict disabled if not ready]   | | [ERROR / LOADING / UNAVAILABLE]            | |
| +--------------------------------------------+ +---------------------------------------------+ |
| [Research CV evidence separate from deployable status] [Reviewed references / downloads]       |
+------------------------------------------------------------------------------------------------+
~~~

**ENGINEERING TBD:** second case candidate *Used Car* requires its own Dataset Audit, feature dictionary, research runs, evaluation and approved deployable artifact. Used Car must show PLANNED/UNAVAILABLE, not invented metrics, figures or active inference. Home case selector should include it only when documented case content exists; a *design preview* may list it disabled with explicit "Candidate — not researched". No cross-case RMSE leaderboard.

### P0-2 — Three-layer availability and selection

| Layer | Identity / authoritative source | Availability and UI behavior |
|---|---|---|
| Research experiment | case_id + run_id + actual method/config/encoded K and CV protocol/track | Shows VERIFIED or other evidence status *independently*; no guarantee of fitted inference artifact |
| Registered trained model | model_id + model_version + artifact SHA/digest + fitted preprocessing/pipeline revision + approved raw schema | Only published, approved, allowlisted models can be considered deployable; status can be UNAVAILABLE even for VERIFIED run |
| Prediction request/result | request_id + chosen registered model + validated raw fields + model version/provenance | Run only if artifact, fitted pipeline, input schema, API compatibility and API QA are approved; response is estimate, not evaluation/holdout metric |

Changes to case, run **or** model invalidate old form values, validation token, predicted outputs and in-flight results; stale API responses must be ignored. Model selector cannot invent a method × K → model mapping. Research-only runs remain selectable for reading evidence with disabled Predict and explanatory reason. If several approved model versions map to one run, user may choose among **only those explicitly registered**; never infer model ID from method/K.

### P0-3 — Raw-input and missingness semantics

**DESIGN PROPOSAL** — Minimum per-field contract, reviewed alongside the immutable fitted preprocessing:
- \`raw_field_id\`, \`source_column\`, \`source_version\`, \`label\`, \`data_type\` (numeric, ordinal, nominal, boolean), \`unit\`, \`required\`, \`allowed_values\`, \`min/max\`, \`dependencies\`, \`missingness_kind\` and \`preprocessing_ref\`.
- Three *different* states: (A) **structural absence** explicitly confirmed by user and supported by training schema (e.g., no garage → supported absence category); (B) **unknown measured value** when facility exists but measurement unrecorded, admitted **only** if fitted pipeline has a documented fold-trained imputer; (C) **omitted required UI field**, always INVALID and block Predict. These must never map to the same silent default.
- Unknown category, unsupported unit, out-of-range value, conflicting fields (e.g., no garage plus positive garage area), unsupported missingness or schema version mismatch => explicit field-level ERROR. Optional fields may omit only if contract documents what fitted preprocessing does; otherwise validation fails. Encoded feature columns are **not** UI form fields; raw-to-encoded transform and order must match the fit pipeline, with no invented dwelling/car defaults.

| Input example | Semantics | Action |
|---|---|---|
| \`garage_present=false\` and \`GarageCars=0\` where supported | structural absence | Encode as trained absence representation; not missing numeric measurement |
| \`garage_present=true\`, garage size unknown, imputer supported | genuine unrecorded | Apply trained inference imputer; disclose uncertainty/handling |
| \`OverallQual\` absent and marked required | required field omitted | REJECT, explain missing field |
| \`GarageCars=2\` and garage explicitly absent | contradictory dependent fields | REJECT until corrected |

All examples are **interface semantics**, not claims that these exact fields/defaults are available in an approved inference schema.

### P1-1 — Train vs Predict split (DESIGN PROPOSAL)

~~~text
DASHBOARD / CUSTOM DATASET (future authorized training)
[CSV / URL] -> [Parse + preview] -> [Choose numeric target + raw X] -> [Validate]
    -> [Train/Evaluate (DISABLED until separately authorized)]
    -> [New run summary with its own CV/test evidence; NOT Ames VERIFIED]
PHASE 6 / DEPLOYED INFERENCE
[Registered approved model] -> [Schema-driven single raw record]
    -> [Validate] -> [Predict (only approved API)] -> [Estimated target + version]
~~~

User CSV with X and labeled Y requires **new fitting** of preprocessing and regression, separately gated for compute, security, size limits, CV and data leakage; it does not automatically invoke an existing Ames model or become a reviewed research case. Phase 6 single-record prediction does **not** retrain, rank feature selection or evaluate Holdout. Optional batch inference is a future proposal, not implied by the teacher's Custom Dataset bonus.

### P1-2 — Minimal multi-case state (illustration, not research data)

| Case | Research evidence | Evaluated deployable model | Inference UI | Eligibility |
|---|---|---|---|---|
| Ames Housing | Phase 2 EDA reviewed; Development experiments available with their own review status | **Not proven by metadata alone**; only approved model registry may say yes | disabled UNAVAILABLE until API + fitted pipeline + schema + QA approved | known teaching case |
| Used Car | PLANNED / not yet audited or run | NONE | disabled PLANNED | second-case candidate only |

Keep Phase 2–5 exhibits bound to selected case-specific cited run IDs. Unavailable case phase shows a truthful empty state. Cross-case metric rankings are prohibited unless a scientifically valid common protocol/target comparison exists.

### P1-3 — Minimal API exchange (DESIGN PROPOSAL only)

~~~json
{
  "model_id": "registered-model-id",
  "schema_version": "reviewed-input-schema-version",
  "raw_inputs": {
    "raw_field_from_schema": "user-supplied-value"
  }
}
~~~

Success response conceptual envelope (numbers omitted deliberately):

~~~json
{
  "status": "success",
  "request_id": "opaque-request-id",
  "model_id": "registered-model-id",
  "model_version": "approved-version",
  "target": {"name": "target-from-case", "unit": "case-unit", "prediction": null},
  "prediction_interval": null,
  "provenance": {"artifact_sha256": "registered-digest", "pipeline_version": "approved-pipeline-version"}
}
~~~

Errors use a documented machine-readable \`code\` and readable \`message\`, with optional safe \`field_errors\` and correlation/request ID; no stack, model path, sensitive rows or internal traces. Minimum codes: \`INCOMPLETE_INPUT\`, \`UNKNOWN_CATEGORY\`, \`INVALID_UNIT\`, \`MODEL_UNAVAILABLE\`, \`SCHEMA_MISMATCH\` (also \`INVALID_FIELD_DEPENDENCY\` / \`OUT_OF_RANGE\` where needed). Only approved allowlist IDs, no URL/path/serialization payload selection. \`prediction_interval\` stays null/UNAVAILABLE unless independently validated and properly labeled (type/level/units/method). This example contains no real fitted model ID or empirical prediction.

### P1-4 — Instructor rubric: original feature count audit

**OWNER-independent assignment clarification:** Kaggle source dataset must have **more than 13 original candidate predictors (>=14)**; **no formal <40 upper bound**. One-hot encoded feature counts cannot satisfy this criterion by themselves. For each case's Phase 2 dataset profile and Phase 4 feature map, show:

| Stage / number | Meaning | Rule |
|---|---|---|
| Source CSV total columns | includes ID and target if present | label train/test and version separately |
| Original candidates | original raw predictors after excluding target and identifier | rubric uses this number |
| Eligible original predictors | also remove leakage and inadmissible columns with reason | document exclusions and schema version |
| Encoded model inputs | transformed model matrix dimension, post encoding | never call this original feature count |
| Selected original / selected encoded | derived documented mapping for exact method/run | cannot equate raw and encoded K |

**Verified Ames source example:** Kaggle train 1,460×81, test 1,459×80; 79 original candidates after excluding \`Id\` and \`SalePrice\`. Encoded count, effective after-leakage original count and selected counts must be read from their correct versioned run/feature map, not inferred or mixed with a different Development/Holdout population.

### Authority and acceptance

**OWNER CONFIRMED:** CRISP-DM-first Desktop Home, 1920×1080 Full HD reference, six numbered horizontal phases, global documented-case selection, independent Dashboard, Phase 4 progressive verified results, Phase 6 model inference when authorized. **DESIGN PROPOSAL:** case metadata-driven labels, model registry/contract, missingness validation, custom Train vs Predict separation and minimal API envelope. **ENGINEERING TBD:** Used Car audit/run, deployable model registry/artifacts, fitted preprocessing, security/compute budget, active endpoints, interval estimation and model QA.

- [ ] Case-driven Phase 6 labels/target/unit with Ames only as example, Used Car disabled candidate.
- [ ] Run research status distinct from model deployment status and prediction availability; selectors invalidate stale values.
- [ ] Required/optional raw schema and all three missingness meanings enforced in design.
- [ ] Custom CSV Train and approved-model Predict are separate flows with separate gates.
- [ ] No unsupported API/interval/model result invented.
- [ ] Assignment original feature threshold and count provenance explicit.

**Gate unchanged:** this is documentation only. No P6-B engineering, Runner, Holdout, Merge, Preview or production deploy.


---

## P6-A Owner discussion supplement — Phase 1–3 detailed reconstruction contract (2026-10-26)

**Status: OWNER-DISCUSSED UX SPECIFICATION / DOCS ONLY.** This section records the latest Phase 1–3 decisions and is the **more specific controlling visual/interaction reference** where older generic Phase 1–3 ASCII sketches above differ. It does not supersede verified Phase 2 evidence, governance gates, the case/model registry safety requirements, or the unfinished Phase 4–6 designs. **No implementation, dataset processing, research rerun, publication, merge or deployment is authorized by this document.**

**How to reconstruct it:** This is a specification, not a screenshot. Draw controls and content in the relative order shown; labels in square brackets are actual controls only where the control catalog explicitly says so. A chart is a **single 100%-stacked horizontal bar** with dynamic segments, consistent category colors and labels, plus explicit numeric counts; four successive bars MUST read as a continuous feature-processing story. Desktop target **1920×1080**, vertically scrollable page. Exact component pixel measurements, type scales, colors and responsive breakpoints are **not Owner-approved**: do not mistake invented values for acceptance requirements. Use responsive widths within a centered desktop content panel; allow scrolling down rather than squeezing four stages into one screen.

### A. Shared shell and navigation — every Phase

~~~text
+--------------------------------------------------------------------------------------------------+
| RegScope                                                 Home / CRISP-DM    [Dashboard]          |
| Study dataset: [Ames Housing                                                 v]                 |
+--------------------------------------------------------------------------------------------------+
| [01 Business Understanding] [02 Data Understanding] [03 Data Preparation*]                     |
| [04 Modeling]             [05 Evaluation]       [06 Deployment]                                |
| NOTE: these six items occupy ONE horizontal desktop row; above is label wrapping in ASCII only.  |
+--------------------------------------------------------------------------------------------------+
| PHASE NN / [ENGLISH TITLE]                                                                        |
| [CASE-SPECIFIC SCROLLING CONTENT]                                                                 |
|                                                                                                  |
| [< Previous Phase]                                                         [Next Phase >]        |
+--------------------------------------------------------------------------------------------------+
~~~

**Global control contract**
1. **Research dataset selector**: one global control, not six phase-local selectors. Its displayed label comes from the current case \`title\`, with stable \`case_id\` used internally. Options are **documented cases only**; planned candidates may be disabled with a visible PLANNED explanation, never presented as completed runs. Selecting an eligible case replaces every phase's content, evidence, image paths, metrics, target/unit and available controls. Keep current phase number if supported; on unsupported phase show UNAVAILABLE/PLANNED rather than retaining the previous case's content. Clear previous case-specific selected EDA analysis and open details, and use the new case's default published item. Do not combine case data.
2. **Phase tabs 01–06**: each navigates to exactly one phase in the current case. The selected tab has active appearance and an accessible current-state label; other tabs stay individually keyboard-focusable if navigation is allowed. Click never changes case. On unsupported content show honest empty/unavailable explanation; tabs need not imply empirical completion. **Six in one horizontal desktop row**, regardless of the ASCII line-wrap used to explain them.
3. **Home**: opens the six-step research journey at Phase 1. **Dashboard**: separate secondary route, *not* an alternative dashboard panel under each phase. Keep prior dashboard-specific security and custom-data gate descriptions above; this supplement does not authorize the Dashboard Run action.
4. **Previous / Next**: navigate exactly one phase backward/forward within the same case. Hide or disable Previous at Phase 1, Next at Phase 6; never loop around. Keyboard Enter/Space activation, visible focus, meaningful labels. Case/phase navigation invalidates stale selected content and asynchronous results.
5. **State handling**: LOADING clears stale content; EMPTY, ERROR, PLANNED, MOCK, UNAVAILABLE, VERIFIED have meanings already defined above. Never turn UI examples or unreviewed local figures into verified case data. External source links must be safe, published URLs; no local machine paths.

### B. Phase 1 — Business Understanding / 純文字研究案例介紹

**Goal:** explain why this case exists, what is being predicted, source, problem, objective, research value and shared methodology. NO dataset figures, EDA galleries, photos, prediction form, chart or benchmark metrics.

~~~text
+--------------------------------------------------------------------------------------------------+
| PHASE 01 / BUSINESS UNDERSTANDING                                                                 |
| 業務理解：本研究要解決什麼問題？                                                                  |
|                                                                                                  |
| +----------------------------------------------------------------------------------------------+ |
| | DATASET / CASE                                                                               | |
| | Ames Housing                                                                                 | |
| | Source: Kaggle                   Dataset: House Prices                                       | |
| | Source URL: [Open official dataset source ↗]                                                | |
| +----------------------------------------------------------------------------------------------+ |
| | BUSINESS CONTEXT                                                                             | |
| | Problem:   如何依據住宅條件估計住宅售價？                                                    | |
| | Objective: 探索住宅特徵與售價的關聯，並建立可解釋的預測基準。                                | |
| | Value:     作為住宅價格迴歸與特徵選擇的教學案例。                                             | |
| +----------------------------------------------------------------------------------------------+ |
| | PREDICTION TARGET                                                                            | |
| | Column: SalePrice                 Unit: USD                                                  | |
| +----------------------------------------------------------------------------------------------+ |
| | RESEARCH METHOD / SHARED METHODOLOGY                                                         | |
| | Multiple Linear Regression → Feature Selection → Evaluation                                | |
| | Methodology: mlr-feature-selection-v1                                                        | |
| +----------------------------------------------------------------------------------------------+ |
|                                                      [Next Phase: Data Understanding >]          |
+--------------------------------------------------------------------------------------------------+
~~~

**Per-element behavior:** Dataset/Case, Business Context and Target are read-only text from selected case metadata. Source link opens the exact permitted official source; it is not a data download or automatic import. Shared methodology is resolved through root \`methodology_id\`: if same methodology applies to different cases, don't copy boilerplate into every case's \`business_context\`. \`problem/objective/value\` MUST be genuinely specific to the selected case, not a universal "run MLR" description. If a case lacks an approved field, show \`UNAVAILABLE\` for that item; do not write Ames-specific text into another case. Next navigates Phase 2.

**Minimum phase 1 data structure** (illustrative contract; content shown is existing Ames case description):
~~~json
{
  "case_id": "ames-housing",
  "title": "Ames Housing",
  "methodology_id": "mlr-feature-selection-v1",
  "phase1": {
    "dataset": {
      "name": "House Prices",
      "source": "Kaggle",
      "url": "https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data"
    },
    "business_context": {
      "problem": "如何依據住宅條件估計住宅售價？",
      "objective": "探索住宅特徵與售價的關聯，並建立可解釋的預測基準。",
      "value": "作為住宅價格迴歸與特徵選擇的教學案例。"
    },
    "prediction_target": {"column": "SalePrice", "unit": "USD"}
  }
}
~~~

### C. Phase 2 — Data Understanding / 靜態 EDA 選取器

**Goal:** explain *already-produced* dataset-specific descriptive research. Phase 2 is NOT an on-demand EDA engine, frontend statistical calculator or interactive Kaggle reanalysis. One selected **published, reviewed** image and its associated prose are shown at a time. Number of analysis buttons is dynamic, from approved case manifest. The four **currently public/reviewed** Ames figures are FIG-01 (overview), FIG-02 (missingness), FIG-03 (target distribution), FIG-06 (numeric correlations); other local figure candidates DO NOT become published buttons just because they exist on disk.

~~~text
+--------------------------------------------------------------------------------------------------+
| PHASE 02 / DATA UNDERSTANDING                                                                    |
| 資料理解：我們從已完成的 EDA 看到了什麼？                                                        |
|                                                                                                  |
| AVAILABLE EDA ANALYSES — dynamic navigation, only approved and published items                   |
| [Dataset Overview*] [Missingness] [SalePrice Distribution] [Numeric Correlations]               |
| [more approved titles wrap onto next row ONLY if the case manifest contains them]               |
|                                                                                                  |
| +----------------------------------------------------------------------------------------------+ |
| | SELECTED: Dataset Overview               [VERIFIED]                                        | |
| |                                                                                              | |
| |                    +---------------------------------------------------+                     | |
| |                    |                                                   |                     | |
| |                    |               FIGURE: SVG / PNG                  |                     | |
| |                    |         one analysis, one principal image        |                     | |
| |                    |                                                   |                     | |
| |                    +---------------------------------------------------+                     | |
| | Alt text / accessible data table for the selected figure                                   | |
| | [Open figure/source]                                                                         | |
| +----------------------------------------------------------------------------------------------+ |
| | DESCRIPTION — what was measured, which population and denominator?                          | |
| | KEY FINDING — what was actually observed, with evidence?                                   | |
| | LIMITATIONS — what cannot be concluded from this descriptive graphic?                       | |
| | DOWNSTREAM IMPLICATION / HYPOTHESIS (if evidence available; NOT automatic adopted policy)    | |
| +----------------------------------------------------------------------------------------------+ |
| [< Previous Phase: Business Understanding]                          [Next Phase: Data Preparation >]|
+--------------------------------------------------------------------------------------------------+
~~~

**Every dynamic EDA selector button**
- **Label:** analysis \`title\` from JSON, not hard-coded first four/eight. Order follows approved manifest array.
- **Click:** set only this button active and **atomically** swap image, alt/accessible data, title, Description, Finding, Limitations, population, source URL, and optional downstream implication; never leave stale captions from previous selection.
- **Default:** first approved/published manifest item for this case; if list empty, show EMPTY/UNAVAILABLE and no inert fake buttons.
- **Hover/focus/keyboard:** visible active and focus indicators; Enter/Space selects. Long lists wrap within selector area on desktop; avoid truncating distinct labels; zero-item empty state.
- **Image:** prebuilt static public SVG/PNG generated offline by Python, with \`object-fit: contain\` behavior (preserve aspect ratio, never crop axes/legend); image failure shows UNAVAILABLE and source, not a dummy empirical figure. Alternative data/description needed for accessibility. No raw private rows on website.
- **Explanatory text:** description, finding and limitations derive from same analysis object. \`next_impact\` is OPTIONAL and must state **candidate/hypothesis** unless an explicitly accepted downstream decision and source exists; absence hides the section, not invented content.
- **Dataset change:** clear previous selection, select first eligible new-case analysis, render unavailable if none. Do not display Ames images in a Used Car case.
- **Evidence:** static images and notes may be served by separately validated public assets. Exact image asset paths and publish permissions must be validated rather than guessed. The deeper Phase 2 empirical details and original FIG evidence table above remain authoritative.

**Minimal manifest item** (all fields sourced from evidence, not code-generated claims):
~~~json
{
  "phase2": {
    "analyses": [
      {
        "id": "missingness",
        "title": "缺失值分析",
        "image": "figures/fig02_missingness_overview.svg",
        "description": "分析各欄位缺失比例與缺失原因。",
        "finding": "部分 NA 代表設施不存在，不能直接視為資料遺漏。",
        "limitations": "缺失值分析本身不代表已完成插補處理。"
      }
    ]
  }
}
~~~
The image path in this snippet is a **schema/path example, not a verified deployable URL**. Optional implementation fields: \`status\`, \`source_url\`, \`source_version\`, \`population\`, \`denominator\`, \`alt_text\`, \`accessible_table_ref\`, \`next_impact\`; do not create an incompatible second protocol when mapping to the earlier Phase 2 finding contract.

### D. Phase 3 — Data Preparation / 四張連續、同規格的特徵變化圖

**Owner's critical visual intent:** teach a **continuous feature-transformation journey**, not four unrelated widgets. **ALL FOUR stages have the SAME stacked horizontal quantitative visualization** with category ordering and colors held stable. Descriptions go BELOW the bar. Stage ③ additionally has an expandable methods accordion. Stage ④ must show that categories can change width/absolute count following One-Hot/other encoding; it MUST NOT mechanically reuse Stage ①'s percentages. Train–Test Split is an independent fifth **closing** bar below the four feature stages.

**Vocabulary hierarchy:** Categorical → Nominal (unordered), Ordinal (ordered). Numerical → Discrete (countable), Continuous (measured). These are **common examples, not a forced exhaustive schema**: each case can have 1, 2, 3, 4 or additional supported types, such as Other/Datetime/Text where actually present. Display only actual classified types. **Preferred visible order** for comparability: Nominal, Ordinal, Discrete, Continuous, then other explicitly documented types. This intentionally puts Categorical before Numerical so that Nominal → One-Hot contribution can be traced. Type classification must use the **dataset dictionary + approved preprocessing policy**, NOT automatically infer "any integer = discrete" or silently assign ambiguous numeric codes. An Ordinal source column may be processed differently by a particular pipeline; display *actual* transformation rather than pretending the category dictates it.

**Percent/count rules and critical denominator discipline**
- Each stage's bar is **100% stacked** over that stage's **own total columns/features**. Within a stage, segment width = that category's count / that stage total. Show count \`n\` and percent \`n/total × 100%\` together via segment label (if readable) and fixed legend immediately beneath. No denominator mixing or sum-by-rounded-percent bugs.
- Persistent same color assignment by **type id** in all four bars, and persistent order. Accessibility: labels text/legend, not color-only. If a 1–3% segment is too narrow for text, put the exact count/percent in the legend; do not hide the segment or pretend it is zero. Empty categories are omitted in the stage but legend can explicitly report zero when needed for stage comparison.
- **Counts matter at least as much as percentages**: show the stage's total prominently at upper right, plus per-type raw counts, and a change note relative to preceding stage. Percentages are relative and MUST NOT imply absolute growth by themselves. In stage ④, reclassification after encoding must be traceable to source type, even though actual encoded matrix entries are numeric: plot segments by **ORIGINAL source-feature type / transformation lineage**, otherwise all encoded columns would trivially appear Numerical and defeat the purpose.
- Stages ①–③ count **source/retained feature columns at their respective stage**, unless independently documented feature creation happens at stage ③; then show its actual unit and a recorded mapping. Stage ④ counts **encoded model-input dimensions**; labeling changes to \`encoded features\`, and the source→encoded mapping explains expanded counts. Never label all four as the same measurement without this unit change.
- If no original predictor is excluded, Stage ② repeats **exactly** Stage ①'s category counts and percent, explicitly "0 excluded"; do not fake a minor reduction. If Stage ③ only imputes/fills without adding/removing fields, it repeats Stage ②'s counts/percent with a note that values changed, **not** feature dimension.
- Unknown count is **UNKNOWN/待核對**, never 0. Don't calculate percent from missing counts. A segment distribution is not independently VERIFIED until per-type values and classification are audited. **Do not use sample 35/20/15/30% in a published Ames chart**: those were UI mock numbers, not empirical results.

**Actual Ames evidence available for design:** 79 source candidate predictors (not counting \`Id\` or \`SalePrice\`), **248 model-matrix encoded columns from Phase 3**, original Kaggle labeled train 1,460 rows. Number of original excluded columns and per-type counts are **UNKNOWN pending actual pipeline/dictionary audit**. **97 selected encoded columns** belongs to a specific Phase 4 selection fit and must NOT replace 248 in Phase 3. Phase 3 and Phase 4 selection metrics must not be conflated.

~~~text
+------------------------------------------------------------------------------------------------------------------+
| PHASE 03 / DATA PREPARATION                                                                                      |
| 資料準備：79 個原始候選欄位，如何變成模型使用的 248 個編碼後特徵？                                                |
| Note: numbers 79 and 248 are Ames documented totals; per-type values below are placeholders awaiting evidence.   |
|                                                                                                                  |
| ① ORIGINAL FEATURE DISTRIBUTION                         TOTAL: 79 raw candidate columns                          |
| +--------------------------------------------------------------------------------------------------------------+ |
| | +------------------- 100% stacked category bar ---------------------------------------------+                | |
| | | [Nominal share ?] [Ordinal share ?] [Discrete share ?] [Continuous share ?] [Other?]       |                | |
| | +-------------------------------------------------------------------------------------------+                | |
| | LEGEND  Nominal: ? cols / ?%   Ordinal: ? cols / ?%   Discrete: ? cols / ?%  Continuous: ? cols / ?%           | |
| | Original candidate predictors exclude target and identifier. Classification: PENDING AUDIT.                   | |
| +--------------------------------------------------------------------------------------------------------------+ |
|                                                  ↓                                                               |
| ② FILTERED FEATURE DISTRIBUTION                         TOTAL: UNKNOWN retained raw columns                      |
| +--------------------------------------------------------------------------------------------------------------+ |
| | +------------------- SAME 100% stacked category bar ----------------------------------------+                | |
| | | [Nominal share ?] [Ordinal share ?] [Discrete share ?] [Continuous share ?] [Other?]       |                | |
| | +-------------------------------------------------------------------------------------------+                | |
| | LEGEND  each retained type: ? cols / ?%       EXCLUDED: UNKNOWN  RETAINED: UNKNOWN                           | |
| | [Show excluded columns and reasons v]                                                                         | |
| | If zero exclusions, repeat Stage ① exactly and print EXCLUDED 0.                                              | |
| +--------------------------------------------------------------------------------------------------------------+ |
|                                                  ↓                                                               |
| ③ PROCESSED FEATURE DISTRIBUTION                        TOTAL: UNKNOWN columns after value processing           |
| +--------------------------------------------------------------------------------------------------------------+ |
| | +------------------- SAME 100% stacked category bar ----------------------------------------+                | |
| | | [Nominal share ?] [Ordinal share ?] [Discrete share ?] [Continuous share ?] [Other?]       |                | |
| | +-------------------------------------------------------------------------------------------+                | |
| | LEGEND  each processed type: ? cols / ?%    Show count delta and non-dimensional value treatments             | |
| | HOW THE DATA WERE PROCESSED (expandable accordion immediately below the bar)                                  | |
| | [Nominal  | processing methods | click to expand v]                                                           | |
| | [Ordinal  | processing methods | click to expand v]                                                           | |
| | [Discrete | processing methods | click to expand v]                                                           | |
| | [Continuous | processing methods | click to expand v]                                                         | |
| | [Other, only if present | click to expand v]                                                                  | |
| +--------------------------------------------------------------------------------------------------------------+ |
|                                                  ↓                                                               |
| ④ FINAL ENCODED FEATURE DISTRIBUTION                    TOTAL: 248 ENCODED FEATURES                              |
| +--------------------------------------------------------------------------------------------------------------+ |
| | +------------------- SAME 100% stacked category bar ----------------------------------------+                | |
| | | [Nominal EXPANDED WIDTH ?] [Ordinal ?] [Discrete ?] [Continuous ?] [Other?]                |                | |
| | +-------------------------------------------------------------------------------------------+                | |
| | LEGEND  each ORIGINAL TYPE's contributed encoded cols: ? / ?%      Σ = 248                                    | |
| | One-Hot Encoding: raw source columns → several encoded columns (actual mapping pending audit).                | |
| | [Expand raw-to-encoded feature mapping v]                                                                      | |
| +--------------------------------------------------------------------------------------------------------------+ |
|                                                                                                                  |
| DATASET PARTITION / TRAIN–TEST SPLIT (different unit: ROWS, not feature columns)                                 |
| +--------------------------------------------------------------------------------------------------------------+ |
| | [-------------------- 80% Development Set (Training) ---------------------][20% Holdout Test Set]              | |
| |     Development: 1,168 labeled rows                                      Holdout: 292 labeled rows            | |
| | Labeled Kaggle train: 1,460 rows; Random Seed: 42. Kaggle Competition Test: 1,459 unlabeled rows SEPARATE.    | |
| | 3-Fold Cross-Validation: explained in Phase 4, on Development ONLY; Holdout not part of CV.                   | |
| +--------------------------------------------------------------------------------------------------------------+ |
| [< Previous Phase: Data Understanding]                                                [Next Phase: Modeling >]   |
+------------------------------------------------------------------------------------------------------------------+
~~~

**A note on ASCII bar characters:** question-mark segment widths in the diagram are *unknown* rather than an actual 20/30% chart. Implementation must compute widths from approved JSON data, including unknown/loading/empty states. In contrast, the 80:20 ROW split has known verified counts and may be drawn proportionally. When a case has only one type, that type fills 100%; with two, three or four types the count and widths follow the manifest. The four chart sections should be stacked **vertically on a scrollable page**, with visible sequence connectors, not four separate phase navigation pages or a carousel.

#### Phase 3 interactive control catalog (each actual button and its result)
| Control | Location and label | Trigger | State transition and content | Guard/disabled handling |
|---|---|---|---|---|
| Global dataset picker | Shared header, \`Study dataset: [title v]\` | select case | changes all stages' dataset, resets open disclosures, data and labels | planned case disabled or truthful incomplete case |
| Phase 01–06 tabs | Shared row | click tab | navigates selected phase; persists case | no invented result for unsupported phase |
| Exclusions disclosure | Under Stage ② \`Show excluded columns and reasons v\` | click | toggles visible list of \`raw_column_name\`, \`type\`, \`exclusion_reason\`, \`stage\`, \`evidence_ref\`; no navigation | UNKNOWN count => message "Exclusion audit pending", not fabricated zero; zero verified => "No raw columns excluded" |
| Nominal accordion | Stage ③ \`Nominal v\` | click | toggles only Nominal's actual treatment list, affected fields, missingness policy, transformation status, evidence | no confirmed method => UNKNOWN, not default One-Hot |
| Ordinal accordion | Stage ③ \`Ordinal v\` | click | toggles only Ordinal's documented ordering, imputation, encoding/identity pass-through, exact fields and evidence | unsupported subtype omitted; never invent category order |
| Discrete accordion | Stage ③ \`Discrete v\` | click | toggles numeric discrete missingness, scaling/retention/transform actually applied and evidence | not every integer raw column is discrete |
| Continuous accordion | Stage ③ \`Continuous v\` | click | toggles numeric continuous imputation/transformation actually applied and evidence | do not claim scaling/log transformation without observed pipeline |
| Other accordion | Stage ③ \`[type] v\` | click | only for a present and documented case type, shows recorded treatment and evidence | absent type should not generate a dead control |
| Raw→Encoded mapping disclosure | Stage ④ \`Expand raw-to-encoded feature mapping v\` | click | toggles searchable/scrollable list of input raw field, source type, encoder/operation, generated encoded feature IDs/count, source revision | unavailable mapping => UNAVAILABLE reason, NOT invented per-type numbers |
| Previous Phase | Footer \`< Previous Phase\` | click | Phase 2, same case | Phase 1 only disabled/hidden globally |
| Next Phase | Footer \`Next Phase >\` | click | Phase 4, same case | Phase 6 only disabled/hidden globally |

**Accordion mechanics:** all Stage ③ type panels **default collapsed** and may be open simultaneously; clicking its header toggles only that panel, without modifying bars or collapsing other panels. Disclosure headers are keyboard accessible with focus/expanded state; no added accordions for non-existent types. Each body is explanatory prose, not a second unrelated chart. Show **APPLIED / NOT_APPLIED / NOT_APPLICABLE / UNKNOWN** for each *actual documented operation* where needed. Do not use a bulky separate generic "research integrity" panel (Owner explicitly rejected it).

**Pipeline placement and scientific accuracy:**
1. Stage ① identifies raw candidate **predictor columns**, excludes \`Id\` and \`SalePrice\` from that 79; original CSV's 81 columns include those two. Its percentage denominator = classified candidate predictor count.
2. Stage ② records explicit column exclusion policies and approved reasons. **Feature selection by model/CV is NOT Stage ②**; that is Phase 4. Report both excluded and retained counts; distinguish 0 vs pending audit.
3. Stage ③ explains structural absence, genuine missing imputation, extra missingness indicators, categorical/numeric transformations, and each applicable \`APPLIED\` state. Clarify that **imputation changes values, not automatically number of columns**; missing-indicator creation *can* increase dimension, and the step where new columns are created must be assigned to a unique transformation stage in the manifest.
4. Stage ④ is the **actual encoded model input matrix**, type lineage by source type. One-Hot may expand Nominal source columns into many indicators; other methods can preserve or add columns, too. The encoded contributions by source type **must sum to exactly 248 for this Ames run**; when mapping is incomplete, the aggregate verified 248 may display but category shares must be UNKNOWN, not a fake stacked bar.
5. Source type/encoder is **not one-to-one by definition**: One-Hot is commonly applied to Nominal, Ordinal Encoding to Ordinal, but only the **actual fitted pipeline** decides; never label all Ordinal values One-Hot or all Nominal values as one numeric output without evidence.
6. The Kaggle 1,459-row competition test is separate from the internally split 1,460 labeled rows; do not call it Holdout. The 292 **Holdout Test Set** is sealed relative to selection/tuning. Phase 4 conducts **3-Fold Cross-Validation inside the 1,168-row Development Set**; Phase 5 holds final independently approved Holdout evaluation.
7. Train-fitted preprocessing and CV fold safety must be explained accurately. A Phase 3 transformed feature dimension is not proof that encoders/imputers were fitted on the entire labeled dataset or before CV; distinguish reported artifacts from CV-fold fit procedure using versioned evidence. No leakage claims without checking their actual provenance.

**Recommended per-case Phase 3 JSON manifest** (schema design, not generated research; UNKNOWN fields represented as null/status, sample type entries omitted until audited):
~~~json
{
  "phase3": {
    "distribution_units": {
      "raw": "raw_columns",
      "filtered": "raw_columns",
      "processed": "pre_encoding_columns",
      "encoded": "encoded_features"
    },
    "stages": [
      {
        "id": "raw",
        "title": "原始特徵型態分布",
        "total": 79,
        "status": "VERIFIED",
        "types": [],
        "evidence_ref": "SOURCE_AUDIT_REFERENCE"
      },
      {
        "id": "filtered",
        "title": "篩選後特徵型態分布",
        "total": null,
        "status": "UNAVAILABLE",
        "types": [],
        "excluded_columns": [],
        "excluded_count": null,
        "evidence_ref": null
      },
      {
        "id": "processed",
        "title": "資料處理後的特徵分布",
        "total": null,
        "status": "UNAVAILABLE",
        "types": [],
        "evidence_ref": null
      },
      {
        "id": "encoded",
        "title": "最終編碼特徵分布",
        "total": 248,
        "status": "VERIFIED",
        "types": [],
        "feature_mapping_ref": null,
        "evidence_ref": "PHASE3_QUALITY_REPORT_REFERENCE"
      }
    ],
    "processing_details": [],
    "split": {
      "source_labeled_rows": 1460,
      "development_rows": 1168,
      "holdout_rows": 292,
      "development_ratio": 0.8,
      "holdout_ratio": 0.2,
      "random_seed": 42,
      "competition_test_rows": 1459
    }
  }
}
~~~
**Contract invariants for future generation:** \`types[]\` is a dynamic array of \`{type_id, label, count, proportion, evidence_ref}\` (plus stable \`color_key\` or centrally mapped color). If \`status=VERIFIED\` for **distribution completeness**, counts are nonnegative integers and sum to \`total\`, and proportions derive from counts (do not trust independently supplied rounded text); the Stage ④ lineage contributions sum to encoded total; raw + excluded/retained reconciliation must hold for verified filtering. An aggregate known total **may coexist with unavailable subtype distribution** (don't use the stage-level VERIFIED flag to imply all its child bars are verified). Therefore the application should model **separate \`total_status\` and \`distribution_status\`** in the final production contract, or supply equivalent per-field provenance. In the illustrative JSON above, an empty \`types\` list with a verified total means **distribution unavailable**, not "zero types". No actual per-type counts are recorded in this document. Stage ③ \`processing_details[]\` entries require type/operation ID, status, fields, handling rules, stage, evidence and optional change in dimension; a categorical label is **not** sufficient evidence of a performed transform. The backend ETL/preprocessing audit will populate this later, after authorization.

### E. Acceptance checks for Phase 1–3 reconstruction
- [ ] On 1920×1080 desktop, all six CRISP-DM tabs appear in a **single** horizontal row; main panel vertically scrolls without forcing four Phase 3 bars onto one viewport.
- [ ] Global dataset picker drives all six phases; no per-phase dataset picker and no stale previous-case figure/copy.
- [ ] Phase 1 renders dataset provenance, case-specific Problem/Objective/Value, target/unit and shared methodology, without charts or images.
- [ ] Phase 2 analysis selector count equals the **approved/published** manifest length; each selection atomically swaps one image and its verified explanatory/evidence data; inaccessible/unapproved assets never appear as research.
- [ ] Phase 3 stages ①–④ each visibly have **the same** stacked horizontal type-distribution chart structure, legend, count, percent, known/unknown status, explanation BELOW bar and a directional connector.
- [ ] Stage ② preserves unchanged distribution **if** exclusion count verified 0; pending exclusion count is not displayed as zero.
- [ ] Stage ③ includes working independently collapsible treatment accordions; expand state doesn't alter the four bars; no fictional operations.
- [ ] Stage ④ encoded type segment widths may differ from Stages ①–③, especially due to **One-Hot expansion**; numeric encoded total 248 is distinctly not Phase 4 selected count 97.
- [ ] When distribution numbers are missing, UI displays **pending/unavailable** rather than any sample percentage, while retaining known audited total.
- [ ] Train–Test Split is the final separate 80/20 **row** bar, labels exact English names and row counts, never confuses Kaggle competition test or Phase 4 3-fold CV.
- [ ] Every control's inactive/loading/empty/unavailable state is accessible and truthful; all paths and percentages are validated and case-scoped.
- [ ] No engineering work or changes to substantive research/QA evidence are implied by this docs-only supplement.


---

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

## Owner decision supplement — Phase 4 ↔ Phase 5 ↔ Phase 6 linked navigation and inference UX (2026-10-26)

**Authority:** Owner discussion confirmed **CASE → RUN → (EVALUATION | REGISTERED MODEL) → PREDICTION** as the user-facing learning journey. This supplement **extends**, not replaces, the detailed Phase 4 ASCII Wireframe/JSON contract above and the prior generalized Phase 6 contract. **Phase 5 detailed design is NOT approved**: its Issue and independent Nex assessment are pending. All diagrams are reconstruction specs, NOT evidence that an API/model actually exists. PR remains docs-only Draft.

### 1. Canonical identity model and source of dropdown options

| Identity | Function | Relationship and hard rule |
|---|---|---|
| \`case_id\` | Selects dataset, Phase 1–6 recorded case, target, source dictionary and allowed research | One case may have many runs; switch clears old-case selections |
| \`run_id\` | Selects one immutable **actual** method + parameter tuple + training/CV protocol + selected-feature outcome | Phase 4 method/parameter selectors are **derived from eligible runs** for the case, not arbitrary combinations |
| \`evaluation_id\` / \`evaluation_ref\` | Links separately reviewed Phase 5 evaluation of a specific run/model to scope/protocol/evidence | Optional, never implied by a CV score. Holdout evaluation may be absent |
| \`model_id\` + \`model_version\` | Identifies a **registered fitted inference artifact**, preprocessing pipeline and raw-input schema | \`case_id+run_id\` **does not automatically construct** a model ID; lookup may yield zero, one or multiple approved versions |
| \`schema_version\` | Pins raw input field contract to model/pipeline revision | Selection of another model requires fresh validation and clears old prediction |

**Required relations and gating:** \`run.case_id == case.case_id\`; \`model.case_id == case.case_id\`; \`model.source_run_id == selected_run_id\` when entering via a run; \`model.input_schema_version\` matches fitted pipeline and request; only model registry entries meeting publication/security/QA/API readiness may enable Predict. A research-only run may still expose CV in Phase 4 and any *separately approved* evaluation in Phase 5. A \`run_id\` is not by itself proof of a trained model; a valid \`model_id\` is not proof of deployed API availability.

**Phase 4 navigation continuity:** choosing method and parameter tuple selects a real \`run_id\` and loads corresponding CV result, source, feature mapping and parameters. "View Evaluation" navigates to Phase 5 with same \`case_id+run_id\` *only as a lookup context*, without presuming evaluated holdout exists. "Use This Model" navigates to Phase 6 with that context; if no approved registry match, render informative disabled state. Returning from Phase 6 to Phase 4 restores the actual selected method/parameter tuple for the same run. Direct Phase 6 entry without a selected run offers **only eligible registered models for that case**. Do not globally hide research-only runs from Phase 4 just because they cannot predict.

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

### 3. Phase 6 — Model Prediction Lab / full ASCII reconstruction wireframe

**Desktop reference 1920×1080, responsive/mobile deferred.** A Case determines the research dictionary and *eligible models*. A particular **registered model/version determines the actual raw-input form**, so two runs in one case can legitimately require different fields. Input is **raw predictor values**, NOT one-hot dummy columns nor Phase 4's selected encoded count. The API loads approved *already-fitted* preprocessing+estimator, never retrains as part of prediction.

~~~text
+----------------------------------------------------------------------------------------------------------------+
| RegScope     Case: [Ames Housing v]               PHASE 06 / MODEL PREDICTION LAB             [Dashboard]        |
| [01 Business] [02 Data] [03 Preparation] [04 Modeling] [05 Evaluation] [06 Deployment ★]                       |
|                                                                                                                |
| MODEL PREDICTION LAB                                  Target: SalePrice    Unit: USD                           |
| Study: Ames Housing  | Run context: [method / complete params / run_id]  [Return to Phase 4]                   |
|                                                                                                                |
| REGISTERED MODEL                                                                                               |
| [Approved model / version v]  [Research status]  [Model readiness]  [Prediction API status]                    |
| Provenance: case_id, source_run_id, model_id/version, input_schema_version, pipeline revision, review           |
|                                                                                                                |
| +-------------------------------------------------------+ +--------------------------------------------------+ |
| | RAW INPUT FORM (generated from model's schema)        | | PREDICTION RESULT                                | |
| | [Basic / Advanced, ONLY if omitted fields safe]       | | State: [NOT READY / READY / LOADING / ERROR]    | |
| |                                                       | |                                                  | |
| | Numerical:                                             | | Estimated SalePrice                              | |
| | Label / unit           [ numeric input            ]   | | [--] USD                                         | |
| | Nominal:                                               | | Only display numeric value after API success     | |
| | Label                  [approved category       v]    | | Model version, run ID, request ID, source         | |
| | Ordinal:                                               | | Prediction interval: unavailable unless approved | |
| | Label                  [ordered options         v]    | |                                                  | |
| | Missingness: structural absence / unknown / required | | User-visible error/help if prediction fails      | |
| | [field-level validation messages and dependencies]    | +--------------------------------------------------+ |
| | [Validate Inputs]      [Predict — only when READY]    |                                                    |
| +-------------------------------------------------------+----------------------------------------------------+ |
|                                                                                                                |
| IF NO READY MODEL MATCHES SELECTED RUN:                                                                        |
| +------------------------------------------------------------------------------------------------------------+ |
| | [Information icon] 此模型尚未準備好                                                                          | |
| | Reason from actual status (not guessed): not trained / artifact absent / not approved / API unavailable.    | |
| | [Choose another AVAILABLE model v]      [Return to Phase 4 — Modeling]                                       | |
| | Optional [View this run's results in Phase 5] only as evidence/navigation; may be UNAVAILABLE.              | |
| +------------------------------------------------------------------------------------------------------------+ |
|                                                                                                                |
| Model limitations, provenance, approved source/download links (secondary), privacy/error notice                |
+----------------------------------------------------------------------------------------------------------------+
~~~

**Layout behavior**:
1. Shared global Case picker: changes Phase 1–6 case and clears previous selected run/model, form values, validation, prediction, model status and in-flight result. Rebuild eligible run and model inventory.
2. Run context: read-only when arriving from Phase 4; show selected \`method\`, each documented \`param\`, and \`run_id\`. It is NOT a free-form model parameter editor in Phase 6. On direct entry, let user pick an approved registered model; reflect its source run.
3. Model selector: choices are **eligible, registered models for the current case**, optionally filtered by selected \`run_id\`. No arbitrary ID input and no guessed method×Top-K/model mapping. Approved model versions may appear as distinct options. If no valid match, show Not Ready card, not fabricated inference.
4. Raw input panel (left desktop column): render from versioned \`input_schema.fields[]\`. Use numeric input for numerical data with units/limits; select/radio for nominal/ordinal with exact allowed trained categories and documented order; conditional controls only where explicit schema dependencies exist. Required indicators and field-level errors. Input values do not survive model/schema switches unless explicitly validated compatible; safer initial behavior = clear all.
5. Basic/Advanced mode is **optional/planned**, not automatically safe. Basic may hide a required raw field only if that particular approved model's schema includes a documented safe/default/missing strategy; otherwise only show complete required form. Never silently invent absent garage, price or area.
6. Output panel (right desktop column): neutral placeholder \`--\` initially, status, target/unit from Case and model contract. On success render predicted target, model version/trace and interpretive limitations. No accuracy/CV/Holdout metrics masquerading as individual prediction; prediction interval only with distinct approved evidence and method. Failure never leaves stale prior predicted number visible.
7. Readiness card: always says **「此模型尚未準備好」** as neutral header for unready inference; supporting reason from actual state, e.g. 「尚未找到完成且核准的模型檔案」、「模型研究已完成，但尚未提供預測 API」、「預測服務暫時無法使用」. **Never say 「模型訓練失敗」 merely because it is undeployed**. Encourage choosing another *eligible* model/parameters or returning to Phase 4. If no alternate approved model, show disabled selection with explanation. Redirect preserves same case and run.
8. Footer evidence/download links stay secondary and publication gated; no live API promise follows from an existing research CV record.

### 4. Phase 6 control-level behavior and failure states

| UI control / event | Exact effect | Validation, reset and availability |
|---|---|---|
| Global Case dropdown | Replace scoped case; query registered models and schemas for new case | Clear run/model/form/validation/results; no stale previous-case input |
| Registered Model dropdown | Resolve concrete model_id + version (approved registry only) and source_run_id | Rebuild exact schema; clear prior prediction; unsupported models absent/disabled with reason |
| \`Choose another AVAILABLE model\` | Shows only other deployable model entries or directs back to Phase 4's run exploration | Disabled with reason when none; no suggestion to select a parameter combination with no actual run |
| \`Return to Phase 4 — Modeling\` | Reopen same case/run, restore method and parameter controls from run | No recompute/retraining; if run no longer eligible, show UNAVAILABLE |
| \`View run evaluation\` | Navigate to Phase 5 same case/run | Only approved evaluation displays; pending Phase 5 design gate |
| Raw number input | Accept schema unit/range/precision; validation on change/submit | No user-facing encoded feature field; non-finite/out-of-range error |
| Nominal/ordinal select | List exact schema allowed values; preserve internal value vs display label | Unknown value error; ordinal option order is schema-defined |
| Structural absence / unknown / required | Separate states with explicit supported mapping | Required omitted blocks; unknown only with fitted imputer; contradictory dependencies block |
| Basic/Advanced | Switch visibility only where model-specific safe defaults are documented | Otherwise absent/disabled, never hides mandatory input |
| \`Validate Inputs\` | Local or server-backed schema validation for selected pinned model/schema | Show individual errors; readiness doesn't equate to successful prediction |
| \`Predict\` | POST sanitized raw payload to approved API; show LOADING then success or actionable ERROR | Enabled only if deployed model+pipeline/schema/API QA eligible AND all inputs valid; block duplicates, ignore stale responses |
| Result output | Show prediction in target unit and model/request trace | Reset on input/model/case change; no values before success; no manufactured uncertainty |
| Public evidence/downloads | Open published/reviewed assets | Missing approval/license/sensitivity review disables link |

**Status taxonomy (reason-coded, not all "not trained"):** \`NO_TRAINED_ARTIFACT\`, \`ARTIFACT_NOT_REGISTERED\`, \`MODEL_NOT_APPROVED\`, \`SCHEMA_UNAVAILABLE\`, \`PIPELINE_UNAVAILABLE\`, \`API_NOT_DEPLOYED\`, \`API_UNHEALTHY\`, \`READY\`. These are **proposed UI reason codes** distinct from the global LOADING/ERROR/PLANNED/UNAVAILABLE states. Source of truth is backend model registry / service health, not client speculation. For example, a run with verified CV but no fitted artifact means research available yet inference unavailable.

### 5. JSON contracts and example payloads (DESIGN PROPOSAL ONLY)

Root case manifest is \`case_id,title,methodology_id,phase1...phase6\`; Phase 4's \`methods[]\` and \`runs[]\` remain canonical. **Do not duplicate or independently invent runs in Phase 6.** Phase 5 details remain pending and may later add evaluation references, without requiring new IDs for the same runs.

**Phase 4 run reference extension** (additive to detailed contract above; all example identifiers non-empirical):
~~~json
{
  "run_id": "example-run-001",
  "case_id": "ames-housing",
  "method_id": "pearson",
  "params": {"top_k": 5},
  "cv_protocol_id": "development-3fold-cv",
  "cv_result_ref": null,
  "evaluation_ref": null,
  "status": "MOCK"
}
~~~

**Phase 6 case-specific prediction presentation and model registry references**:
~~~json
{
  "phase6": {
    "title": "房價預測實驗室",
    "target": {"column": "SalePrice", "label": "預測房價", "unit": "USD"},
    "model_registry_ref": "approved-model-registry-manifest",
    "direct_entry_policy": "eligible_registered_models_only",
    "prediction_api": {
      "schema_endpoint_template": "GET /api/cases/{case_id}/prediction-schema",
      "predict_endpoint": "POST /api/predictions",
      "model_metadata_endpoint_template": "GET /api/models/{model_id}"
    },
    "ui_states": {
      "no_model_title": "此模型尚未準備好",
      "no_model_next": "選擇其他可用模型，或返回 Phase 4 查看實驗"
    }
  }
}
~~~
**These endpoint strings are proposed API route shapes, NOT deployed endpoint claims**. A schema GET needs enough information to pin model/version; if using the case schema endpoint, response must include eligible model-specific schema references rather than falsely treating case's shared dictionary as a universal input schema.

**Registry record** (one model source run, potentially multiple registered versions per run):
~~~json
{
  "model_id": "example-registered-model",
  "model_version": "example-v1",
  "case_id": "ames-housing",
  "source_run_id": "example-run-001",
  "artifact_digest": null,
  "fitted_pipeline_ref": null,
  "input_schema_version": null,
  "input_schema_ref": null,
  "status": "UNAVAILABLE",
  "readiness_reason": "ARTIFACT_NOT_REGISTERED",
  "publication_review": null,
  "api_qa": null,
  "evidence_ref": null
}
~~~
**The \`example-...\` items are placeholders, not actual deployed models, and MUST NOT be exposed as selectable approved options.** Approved eligibility requires evidence of model artifact, fitted pipeline, input schema, matching hashes/versions, permitted publication, API compatibility and QA.

**Versioned input field definition** (EXAMPLE only; never presume 2–3 raw fields are enough for Ames model):
~~~json
{
  "schema_version": "example-v1",
  "model_id": "example-registered-model",
  "fields": [
    {
      "id": "GrLivArea",
      "source_column": "GrLivArea",
      "label": "地上居住面積",
      "data_type": "numerical",
      "control": "number",
      "unit": "sqft",
      "required": true,
      "min": 1,
      "max": null,
      "missingness_kind": "not_permitted",
      "preprocessing_ref": null
    },
    {
      "id": "Neighborhood",
      "source_column": "Neighborhood",
      "label": "社區",
      "data_type": "nominal",
      "control": "select",
      "required": true,
      "allowed_values_ref": null,
      "missingness_kind": "not_permitted",
      "preprocessing_ref": null
    }
  ]
}
~~~
Model-specific versions must define **all** required raw inputs and valid categories/dependencies based on the *fitted* preprocessing. This list is incomplete by design and cannot justify an active Predict button.

**Prediction request** (a request identifies the concrete registered model AND case; run provides research trace, not instructions to fit or tune):
~~~json
{
  "case_id": "ames-housing",
  "run_id": "example-run-001",
  "model_id": "example-registered-model",
  "model_version": "example-v1",
  "schema_version": "example-v1",
  "raw_inputs": {
    "GrLivArea": 1500,
    "Neighborhood": "NAmes"
  }
}
~~~
Before inference server checks \`case_id\`, \`run_id\` relationship, registered model/version and schema, validates every required raw field, enforces trained category handling and dependencies, applies registered fitted transformation, returns estimate. **No on-request training, feature selection, CV or default guess**. In production the model may demand many more fields; example input is explicitly incomplete and not an executable valid Ames request.

**Success response envelope**:
~~~json
{
  "status": "success",
  "request_id": "opaque-request-id",
  "case_id": "ames-housing",
  "run_id": "example-run-001",
  "model_id": "example-registered-model",
  "model_version": "example-v1",
  "target": {"column": "SalePrice", "unit": "USD", "prediction": null},
  "prediction_interval": null,
  "provenance": {"artifact_digest": null, "pipeline_version": null}
}
~~~
Here \`prediction=null\` means **illustrative schema with no calculation performed** and MUST NOT be shown as a successful numeric prediction. Real success requires a finite validated value and actual trace; \`prediction_interval\` remains null unless separately approved. API error envelope must supply safe \`code/message\`, optional \`field_errors\` and request_id; examples: \`MODEL_UNAVAILABLE\`, \`SCHEMA_MISMATCH\`, \`INCOMPLETE_INPUT\`, \`UNKNOWN_CATEGORY\`, \`INVALID_FIELD_DEPENDENCY\`, \`API_UNAVAILABLE\`. Fail closed if artifact / pipeline / schema or API QA absent.

### 6. Phase 4 ↔ Phase 6 handoff acceptance checks
- [ ] Selecting any method/params in Phase 4 resolves to an eligible **actual run_id** and does not invent experiment data or Cartesian combinations.
- [ ] Phase 5 handoff carries case/run for lookup without implying Phase 5 research or Issue completed.
- [ ] Phase 6 selects a **registered model_id/version** by registry lookup, never constructs it from case/run strings.
- [ ] Phase 6 form is generated from selected model's approved raw-input schema; never asks for 248 encoded columns or assumes Top K equals raw input count.
- [ ] Model not ready: reason-specific neutral notice, choose alternate ready model or return to Phase 4; no false training-failed claim.
- [ ] Switching case/run/model invalidates stale form, validation, prediction and in-flight API replies.
- [ ] Back to Phase 4 restores actual run's method/params, no training operation triggered.
- [ ] API request pins model/version and schema; backend verifies relationship, model registration, safe inputs, pipeline and deployment QA; zero real API calls until authorized.
- [ ] Basic/Advanced simplification only for a model with explicitly documented safe omissions, not a generalized default.
- [ ] Docs-only design gate and Phase 5 pending independent discussion stay explicit.

### 7. Open engineering/evidence dependencies — not Owner decisions needed now

1. Inventory **which real Phase 4 run_ids** have preserved, loadable fitted models and complete immutable preprocessing. Existing CV results alone cannot certify deployability.
2. Audit model-specific raw-field inputs, allowed category values, missingness semantics, derived feature mapping, whether any safe Basic form exists.
3. Select permitted deployment architecture, registered artifact storage, API authentication/rate limits and availability reporting; security review, endpoint QA and model/publication approval.
4. Phase 5 Evaluation design/Issue to be prepared separately with Nex input; not invented in this supplement.

**Governance:** No P6-B build, runner modification, actual prediction API, training, merge, release or deploy; all require further explicit authorization and review.


## Integration reference — Offline data and Prediction API contract

The independently versioned data-production and backend-interface design is in [REGSCOPE-DATA-API-CONTRACT.md](./REGSCOPE-DATA-API-CONTRACT.md). **Use that document for file inventories, JSON structures, static SVG/PNG/chart placement/asset specifications, exporter/validator responsibilities, model registry and Prediction API request/response formats**; use THIS UX document for visible page layout, every control and interaction. The companion document is a proposal, not evidence of existing generated assets or an authorized endpoint. Phase 5 detailed design remains pending Nex/Owner.
