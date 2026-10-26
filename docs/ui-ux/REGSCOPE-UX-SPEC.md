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
