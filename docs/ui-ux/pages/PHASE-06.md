# Phase 6 — Model Prediction Lab

**Current detailed UX; docs-only.** No live API or registered inference approved. Canonical endpoint/schema naming in [contract delta](../REGSCOPE-CONTRACT-REVIEW-DELTA.md), not historical payload examples below.

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