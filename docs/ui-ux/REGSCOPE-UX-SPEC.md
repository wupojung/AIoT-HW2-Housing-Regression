# RegScope — UI/UX Design Specification v0.1

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

### Phase 2 — Data Understanding / 資料理解
~~~text
+------------------------------------------------------------------+
| PHASE 2: What does the raw data contain?                         |
| [Rows] [Features] [Numerical / categorical] [Missingness]        |
| Feature: [documented column v]                                   |
| [ONE EDA visualization: distribution / missing / relationship]  |
| [Data dictionary and full EDA evidence v]                        |
| [< Previous]                                         [Next >]     |
+------------------------------------------------------------------+
~~~
Interaction: inspect one column/one exploratory research question at a time. Distinguish raw and encoded counts.

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

### Phase 6 — Deployment / 成果部署
~~~text
+------------------------------------------------------------------+
| PHASE 6: What can be inspected, downloaded, reproduced?          |
| [Reviewed downloadable aggregate/chart/report artifacts]        |
| [GitHub] [Reproduction instructions / source versions]           |
| [NotebookLM >=100-word summary] [GPT-assisted record / PDF]      |
| [Licensing, citations, public-safety and availability notices]   |
| [< Previous]                                         [Next >]     |
+------------------------------------------------------------------+
~~~
Interaction: download only reviewed public-safe material; otherwise show unavailable and link original source.

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
