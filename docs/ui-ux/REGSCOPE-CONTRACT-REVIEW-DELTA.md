# RegScope — PM Contract Review Delta v0.2

**2026-10-26 | Docs-only | Canonical corrections to [DATA/API CONTRACT](./REGSCOPE-DATA-API-CONTRACT.md).** Source: [PM P0 review](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35#issuecomment-6420057913). **The newer definitions on this page SUPERSEDE conflicting v0.1 inline examples**; this is not evidence of completed local asset audit, API deployment or Phase 5 execution.

## P0 resolution decisions

| P0 | Decision | Correction | Remains pending |
|---|---|---|---|
| 1 identity | ACCEPT | `execution_run_id` ≠ `configuration_id` ≠ `task_id` ≠ `final_fit_id` ≠ `evaluation_id` ≠ `model_id` | exact manifest source IDs / SHA-backed alias mappings |
| 2 encoded K | ACCEPT | requested, fold-observed and final-fit K separated | audited fold-to-config references |
| 3 reported 248 | ACCEPT | feature dimensions scoped to fit population/pipeline SHA | independent encoder audit |
| 4 deploy readiness | ACCEPT | five audited gates, Mac/Windows joblib reported exists locally | model load/schema/registry/API QA |
| 5 exports | ACCEPT | below file-to-export feasibility matrix | authorized private key-path inspection |
| 6 Phase 5 | ACCEPT | Issue #37 population/metrics/figures/interval contract | Phase 5 UX + review/authorization |
| 7 publication | ACCEPT | immutable staging→validation→atomic release pointer | implementation/release gate |
| 8 API naming | ACCEPT | below canonical endpoints and fields | versioned schemas + real-source fixture |

## 1. Canonical identity and joins

Research source `run_id` maps to **`execution_run_id`**, one engine execution. PM handoff reports one Development execution including **32 configurations × 3 folds = 96 tasks**, 91 COMPLETED and 5 INVALID (unverified here). **Never mint 32 different execution IDs from configurations.**

| Identity | Foreign keys | Meaning |
|---|---|---|
| `case_id` | — | dataset and study |
| `execution_run_id` | case_id | original run/campaign ID e.g. reported `development_20261026_01` |
| `configuration_id` | case_id, execution_run_id | exact method + track + params + CV protocol; **Phase 4 selected key** |
| `task_id` | configuration_id, execution_run_id, fold_index | fold task/checkpoint and state |
| `final_fit_id` | configuration_id, case_id | separately fitted model trained on full allowed Training Set |
| `evaluation_id` | configuration_id, population, optionally final_fit_id | Phase 5 evaluation |
| `model_id` + `model_version` | final_fit_id, configuration_id, case_id | explicitly registered inference artifact |

Phase 4 controls filter **actual eligible configurations**. Phase 4→5 passes `case_id,execution_run_id,configuration_id`; Phase 4→6 resolves model registry from the same keys; **zero/one/multiple models** may exist, not auto-derived. An upstream config identifier may be exposed through versioned `source_key_mapping`: `source_manifest_sha256`, `source_configuration_key`, `canonical_configuration_id`, `mapping_version`; require deterministic collision-free mapping and reconciliation. No fabricated source key. FKs must resolve and all per-fold protocol/track details match exact execution.

### Redacted identity walk-through — NOT an executable true fixture

~~~json
{
  "schema_version": "1.1.0",
  "case_id": "ames-housing",
  "execution_run_id": "development_20261026_01",
  "configuration_id": null,
  "source_configuration_key": null,
  "method_id": "lasso",
  "track_id": "selected_to_ols",
  "params": {"alpha": 100},
  "task_ids": [],
  "requested_k": null,
  "selected_k_by_fold": [104, 103, 102],
  "selected_k_summary": {"min": 102, "max": 104, "mean": 103, "sample_sd": null},
  "final_fit_selected_k": 97,
  "status": "SOURCE_REPORTED_NOT_VERIFIED"
}
~~~

The handoff gives 104/103/102 fold encoded counts and a **distinct 97-column full-development final fit**, but IDs/tasks/fit mappings are not independently confirmed. Null means blocked from VERIFIED/eligible selection.

## 2. Fold-varying K and Phase 3 feature scope

For fixed-K methods, chart x = **`requested_k`** only when genuinely requested. For Lasso/Elastic Net, use `alpha` (and Elastic Net `l1_ratio` series/facet) with *observed fold selected count range* labeled; never use 97 final-fit count or 103 fold mean as requested K. Alternative observed-K scatter must label x semantics **`observed_fold_mean_selected_k`** and show fold variability; never combine it with requested K on same curve. CV y = compatible CV fold-mean RMSE; sample SD only if verified.

**Phase 3 reported 248 encoded columns are NOT universal for Ames.** Publish only with `fit_population`, `split_id`, `pipeline_version`, `transformer_fit_id`, `source_artifact_sha256`, `feature_mapping_sha256`, `lineage_ref`, `encoded_dimension`, independent `total_status` and `distribution_status`. Pending audit UI displays known reported 248 with fit-scope caveat and no invented type bars. Derived multi-source outputs need `source_raw_field_ids[]` and explicit non-double-counting `attribution_policy`.

## 3. Five readiness gates: local trained ≠ deployable

PM reports Mac/Windows local Final Fit `joblib` artifacts with different SHA, not in published handoff. **Don't claim untrained because artifact absent from Package B.** Model registry gate statuses: `PASS | FAIL | UNKNOWN | NOT_STARTED | REQUIRES_AUDIT` for each of:
`artifact_exists`, `load_verified`, `raw_input_schema_validated`, `registered`, `api_deployed_and_qa_pass`. **Predict enabled only if all five PASS plus release permission**; local joblib never in public root or arbitrary user URL.

## 4. Required source-to-export inventory (not an inspection of ignored local data)

Availability statuses: **SOURCE PRESENT (public verified)** / **SOURCE PRESENT (local reported)** / **DERIVABLE WITH APPROVAL** / **REQUIRES NEW EXTRACTION** / **UNAVAILABLE**. Actual private JSON key paths are **UNKNOWN**; exporter must record exact paths only after separate authorized metadata audit. Proposed functions below do not yet exist.

| Source and source key path | Current source/rights state | Target product | Generator responsibility | Feasibility |
|---|---|---|---|---|
| `p4b_public_summary.json` / UNKNOWN | local reported, not actually public-approved | Phase4 config summary, comparison chart JSON | `extract_configuration_summary()` | DERIVABLE WITH APPROVAL |
| `p4b_private_details.json` / UNKNOWN | local reported/private | Phase4 configuration/task detail | `extract_config_details()` | DERIVABLE WITH APPROVAL |
| `p4b_oof_predictions.csv` / UNKNOWN | local reported, private per-row | Phase5 FIG-P5-01/02/03 only if approved | `inspect_oof_schema()`; `render_authorized_oof_figures()` | REQUIRES NEW EXTRACTION + owner data read/publish gate |
| 96 fold checkpoints / task key UNKNOWN | local reported, 91 completed, 5 invalid | CV fold-size/metric and K-by-fold metadata | `extract_fold_task_audit()` | DERIVABLE WITH APPROVAL |
| Mac/Windows Final Fit metadata and joblib / SHA UNKNOWN | reported local private; distinct hashes | private registry readiness summary | `audit_final_fit_metadata()` | REQUIRES NEW EXTRACTION; load gate separately |
| Phase2 FIG-01 public overview | public reviewed; current URL/hash needs recheck | Phase2 image+manifest | `reference_reviewed_asset()` | SOURCE PRESENT (public verified historically) |
| Phase2 FIG-02 missingness | same | Phase2 image+manifest | same | SOURCE PRESENT (public verified historically) |
| Phase2 FIG-03 SalePrice distribution | same | Phase2 image+manifest | same | SOURCE PRESENT (public verified historically) |
| Phase2 FIG-06 correlations | same | Phase2 image+manifest | same | SOURCE PRESENT (public verified historically) |
| Phase3 type lineage/missing indicators / keys UNKNOWN | no full approved map | Phase3 stage segments / lineage | `extract_preprocess_lineage()` | REQUIRES NEW EXTRACTION |
| Existing 292-row Holdout aggregate metric references / keys UNKNOWN | historically reported; restricted | Phase5 approved aggregate only | `index_approved_holdout_aggregates()` | DERIVABLE WITH APPROVAL; NO Holdout row access |

**No frontend parses private summaries**. Next engineer first produces a metadata-only source inventory and exact source `key_path → output field` mapping; until then the literal value is `UNKNOWN`, NOT a guess. A file called `public_summary` is not publication approval.

## 5. Issue #37 Phase 5 compatible schema (no execution authorization)

[Issue #37](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/37) specifies MAE, RMSE, R²; FIG-P5-01 Actual vs Predicted, FIG-P5-02 Residual vs Predicted (**actual minus predicted**), FIG-P5-03 Residual Distribution, FIG-P5-04 interval-method/evidence slot. Distinguish `development_oof`, `holdout`, `training_in_sample`; metric source `cv_fold_mean`, `pooled_oof`, `holdout_aggregate`; `n`, unit, fold values, fold-mean/sample SD **separate from** pooled metric. No OOF scored winner is independent Holdout. No row-level Holdout access/chart without independent Owner gate. An unavailable interval memo **does not fulfill** the final assignment interval requirement.

~~~json
{
  "schema_version": "1.1.0",
  "case_id": "ames-housing",
  "evaluations": [],
  "evaluation_record_schema_example": {
    "evaluation_id": null,
    "execution_run_id": null,
    "configuration_id": null,
    "final_fit_id": null,
    "model_id": null,
    "evaluation_population": "development_oof",
    "n": null,
    "metric_source": "cv_fold_mean",
    "metrics": {"mae": null, "rmse": null, "r2": null, "fold_mean": null, "sample_sd": null, "pooled_oof": null},
    "figures": [
      {"figure_id":"FIG-P5-01","asset_ref":null,"status":"UNAVAILABLE"},
      {"figure_id":"FIG-P5-02","asset_ref":null,"status":"UNAVAILABLE"},
      {"figure_id":"FIG-P5-03","asset_ref":null,"status":"UNAVAILABLE"}
    ],
    "interval": {"figure_id":"FIG-P5-04","method":null,"interval_type":null,"level":null,"status":"UNAVAILABLE"},
    "source_digest": null,
    "publication_review": "PENDING"
  }
}
~~~

Example null IDs are schema documentation **not evaluation data**. Phase 5 UI remains design-pending, do not infer a fully implemented page from this data contract.

## 6. Immutable package staging and atomic publication

Five package types: `case_study`, `research_execution`, `configuration_metrics`, `evaluation`, `private_inference_model` (private only). Every immutable package manifest needs `package_id, package_kind, release_id, schema_version, case_id, source_digests, files[relative_path,sha256,mime,size_bytes], dependencies, publication_review, approver, evidence_refs,status`.

1. Upload/import enters **private staging only**. No UI publication, VERIFIED promotion or executable registry side-effect.
2. JSON Schema Draft 2020-12 validation, FK checks, source SHA, figure SHA/MIME, public-safety/privacy/license gate, allowlist and explicit approval.
3. Build complete **immutable versioned release** (e.g. `/data/releases/<release_id>/...`) and validate every URL/ref/asset.
4. Atomically switch the `current-release` pointer **only after** whole release PASS. UI pins one release ID for every fetch; immutable assets can cache long; mutable pointer uses revalidation/short TTL.
5. Preserve previous release pointer for rollback; any missing asset/404 or SHA mismatch means do not promote release, and published UI displays UNAVAILABLE instead of stale charts.
6. Register models in trusted private registry after distinct artifact/load/schema/API gates; NEVER directly from public package uploads.

## 7. One canonical set of endpoints and field names

**Canonical, PROPOSED, not live**: `GET /data/releases/{release_id}/index.v1.json`; static case/phase/config files through refs in same release; `GET /api/cases/{case_id}/models`; `GET /api/models/{model_id}/input-schema?model_version={model_version}`; `GET /api/models/{model_id}`; `POST /api/predictions`; `GET /api/health`.

**Superseded**: `GET /api/cases/{case_id}/prediction-schema` (case isn't model-bound); `POST /api/predict`; `GET /api/models` generic; any per-configuration fabricated `run_id`.

**Canonical fields**: `raw_field_id` rather than generic `id` for form fields; `data_type` rather than `type`; `artifact_sha256` rather than `artifact_digest`; `schema_version` + `model_version` pinned at prediction request and model-bound schema. Display status `VERIFIED/MOCK/PLANNED/UNAVAILABLE/ERROR` is separate from the five readiness gate statuses. Error envelope `request_id,code,message,field_errors`. Real success `prediction` must be finite; `null` means non-success/example only. Server checks exact case→execution→configuration→final-fit→registered model mapping, approved preprocessing/schema and version; no request-time fitting.

## 8. Fixture & acceptance strategy

Two fixture categories:
- **UI-only synthetic fixtures**: explicitly `MOCK` or `UNAVAILABLE`; Phase2 selector placeholders with reviewed evidence pointers, Phase3 no subtype shares, Phase4 zero eligible configurations, Phase5 zero approved evaluations, Phase6 zero ready models, Dashboard custom Run disabled. See [reconstruction index](./REGSCOPE-RECONSTRUCTION-INDEX.md). Not empirical.
- **Actual-source walk-through**: one Mac Development `execution_run_id` + one **real** configuration_id + three **real** task_ids + existing final-fit metadata, redacted with actual source SHA/key-path mapping. **BLOCKED pending separately authorized local metadata-only inventory**. Never substitute synthetic keys or label VERIFIED.

Independent QA: verify 32 configs do not create 32 executions; 96 tasks != 96 completed; fold selected K variable; 248 dimension fit scoped; local joblib presence != deploy; Phase5 OOF vs Holdout; endpoints consistent; all public release references resolve. This is a **design-remediation document, not P6-B permission**.