> **CANONICAL CONTRACT CORRECTION (2026-10-26):** Read [REGSCOPE-CONTRACT-REVIEW-DELTA.md](./REGSCOPE-CONTRACT-REVIEW-DELTA.md) **before implementing any JSON/endpoint**; its identity model, source-to-export feasibility, Phase 5 fields, publication protocol and endpoint names **supersede incompatible v0.1 examples below**. Start at [REGSCOPE-RECONSTRUCTION-INDEX.md](./REGSCOPE-RECONSTRUCTION-INDEX.md). Docs-only, no API/tooling authorization.

# RegScope — Data Products, Visualization Assets & Prediction API Contract v0.1

**Status:** P6-A **DESIGN PROPOSAL / docs-only**, 2026-10-26. Companion to [REGSCOPE-UX-SPEC.md](./REGSCOPE-UX-SPEC.md); PR #35, Issue #34. This file is the authoritative **production/export and integration proposal**, not a claim that any file, model, image or endpoint has been generated/deployed. Phase 5 detailed UI and evaluation gate await Nex/Owner decision. **No runner, ETL, CI, model training, holdout evaluation, deployment, repository secret, raw dataset publishing or merge authorized.**

## 0. Decision summary (important for Codex/other AI)

1. **Offline Python Exporter** produces **immutable, validated, public-safe aggregate JSON + optional static SVG/PNG** from **existing audited artifacts**. Frontend does **not** recompute EDA, preprocessing, feature selection, CV or holdout.
2. Global \`case_id\` selects one study's Phase 1–6; Phase 4 eligible \`run_id\` inventory generates method/parameter dropdowns from **actually computed tuples**. A run can have no evaluated result and no deployed model. \`case_id+run_id\` lookup in a **separate approved Model Registry** yields zero/one/multiple versioned \`model_id\`; never construct a model ID by concatenating strings.
3. **Static pages = data products**, while **Prediction API = live, gated** service. A valid research run, \`model_id\`, and working API are distinct statuses.
4. **Privacy/publication gate:** raw Kaggle rows, local-only manifests, sealed holdout, credentials, model artifacts and train/test indices remain private unless individually authorized. Public JSON should be **aggregate** and evidence-linked. Do not turn an ignored \`local/\` folder into \`public/\`.
5. **Source of truth:** records with evidence, immutable hashes, QA and approval; absent values \`null\` with reason/status, not invented zeros, mock scores or percentages. If sources disagree, fail validation and request audit—not silent reconciliation.
6. **Design target:** desktop **1920×1080**; responsive implementation deferred. Detailed view layout in UI/UX spec; below specifies exactly what backend hands UI, where files sit and figure contracts.

## 1. External documentation researched and design implications

- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12): publish schemas, validate export **before** publication, including types, enums, required fields and versioning.
- [Vega-Lite specification](https://vega.github.io/vega-lite/docs/spec.html) and [Data formats](https://vega.github.io/vega-lite/docs/data.html): declarative JSON charts support inline data and URL-backed data. **Proposal:** use **own simple semantic chart manifest + tidy datasets** first; do not lock frontend to a renderer. Vega-Lite specs are optional generated derivatives, not the only authoritative source.
- [FastAPI response models](https://fastapi.tiangolo.com/advanced/custom-response/): response validation/serialization, OpenAPI generation if FastAPI is later selected. Choosing FastAPI **is not a project architecture decision here**; HTTP contracts below are framework-independent.
- [scikit-learn model persistence](https://scikit-learn.org/stable/model_persistence.html): pickle/joblib may execute arbitrary code on loading; training-serving package version compatibility is critical. Model artifacts stay on trusted backend/object storage, pinned by digest; server loads only explicitly approved artifacts. ONNX/skops may be evaluated separately subject to pipeline compatibility.
- [Matplotlib SVG backend](https://matplotlib.org/stable/api/backend_svg_api.html): Python export can render SVG; also export raster PNG as fallback when verified.
- **Chosen separation:** Phase 2 reviewed EDA = offline image + explanation; Phase 3 stage bars = **native frontend from numeric JSON** (not screenshot); Phase 4 fold bars = **native frontend from fold JSON**; CV curves/comparisons = structured **chart data JSON** with optional publication-approved SVG/PNG; Phase 5 charts **reserved, not asserted completed**.

## 2. Directory layout — proposed, do not assume already exists

~~~text
repo/
  docs/
    ui-ux/
      REGSCOPE-UX-SPEC.md                 # visual wireframes, every control
      REGSCOPE-DATA-API-CONTRACT.md       # THIS DOCUMENT: generating + serving data
  contracts/                             # FUTURE generator-owned versioned schemas
    v1/
      case.schema.json
      analysis.schema.json
      stages.schema.json
      method.schema.json
      run.schema.json
      chart.schema.json
      evaluation.schema.json
      model-registry.schema.json
      input-schema.schema.json
      predict-request.schema.json
      predict-response.schema.json
  public/
    data/
      index.v1.json                      # approved cases + manifest pointers
      cases/
        ames-housing/
          manifest.v1.json               # case root + phase descriptors/status
          phase1/
            context.v1.json
          phase2/
            analyses.v1.json
          phase3/
            preparation.v1.json
            feature-lineage.v1.json      # aggregate/public-safe mapping only if approved
          phase4/
            modeling.v1.json             # method catalog + available verified runs
            runs/
              <run-id>/
                metadata.v1.json
                cv-folds.v1.json
                cv-metrics.v1.json
                selected-features.v1.json  # PUBLIC-SAFE aggregate/name list only if reviewed
            charts/
              comparison.v1.json
              feature-count-vs-cv.v1.json
          phase5/
            evaluations.v1.json          # empty/unavailable until separately approved
          phase6/
            inference-catalog.v1.json    # PUBLIC projection: eligible models + readiness only
    figures/
      ames-housing/
        phase2/
          fig01_dataset_overview.svg
          fig01_dataset_overview.png
          fig02_missingness_overview.svg
          fig02_missingness_overview.png
          fig03_saleprice_distribution.svg
          fig03_saleprice_distribution.png
          fig06_numeric_correlation_heatmap.svg
          fig06_numeric_correlation_heatmap.png
        phase4/
          <approved-chart-id>.svg
          <approved-chart-id>.png
        phase5/
          <approved-chart-id>.svg        # only after Phase 5 approval
  local/                                # PRIVATE / ignored; DO NOT COPY TO public automatically
    research/
      <case-id>/<run-id>/...             # raw datasets, full logs, fold indices, full predictions
    artifacts/
      <model-id>/<version>/...           # fitted pipeline/estimator, hashes, dependency lock
    export-staging/                     # generated private manifest before gates
  tools/                                # FUTURE, not created by this specification
    export_research_contract.py
    validate_research_contract.py
    render_verified_figures.py
~~~

**Paths are a proposal requiring repository review**; if \`public/\` is not the actual frontend's static root, configure the same logical published URLs at build/deploy time. **Never create public artifacts from this text alone**. Treat individual manifest names as stable versioned API resources. Content hashes/digests prevent silently replacing research under the same version; when publishing revised results, generate a new immutable revision and update case index.

## 3. Canonical file families — exact export checklist

| File/family | Producing source & unit | Consuming UI | Required data and audit | Publication |
|---|---|---|---|---|
| \`index.v1.json\` | QA-approved case registry | Global Dataset dropdown | schema version, cases with case_id/title/status/manifest URL | public |
| \`manifest.v1.json\` | case research metadata | all six pages | case_id, title, methodology_id, phase refs+status, target/source/license, release digest | public |
| \`phase1/context.v1.json\` | case brief | Phase 1 text | source/name/url, business problem/objective/value, target/unit, methodology | public |
| \`phase2/analyses.v1.json\` | reviewed EDA report + approved images | Phase 2 dynamic insight buttons | stable id/title, image refs, description, finding, limitations, provenance, scope, status | public if reviewed |
| \`phase3/preparation.v1.json\` | accepted preprocessing quality report/feature dictionary | Phase 3 four bars + 80/20 | raw/filtered/processed/encoded stages, type counts, sum, units, treatment actions, exclusions, split | public aggregate |
| \`phase3/feature-lineage.v1.json\` | fitted encoder/feature mapping inventory | Phase 3 encoded mapping; Phase 4 selected feature names | raw source type → generated encoded feature IDs/count and encoder version | release review |
| \`phase4/modeling.v1.json\` | immutable run inventory and experimental manifest | dynamic Method + parameters, 3 perspectives | CV protocol, methods[]/parameters[], eligible run refs, valid tuple/default | public aggregate |
| \`phase4/runs/<id>/metadata.v1.json\` | one immutable executed config | Phase 4 selected run, Phase 5/6 handoff | run_id/case/method/params/split/protocol/track/seed/status/SHA | public reviewed |
| \`cv-folds.v1.json\` | splitter/protocol audit | 3 horizontal fold bars | fold number, training/validation count, ratio, fit isolation, source | public aggregate |
| \`cv-metrics.v1.json\` | compatible fold scoring artifacts | Phase 4 comparison, CV progress | scoped RMSE by fold/mean/SD, units, selected encoded K, metric direction, QA | public reviewed |
| \`selected-features.v1.json\` | actual model selection/encoder mapping | Phase 4 selected features | stable encoded IDs, raw lineage, coefficients/rank **if actually recorded** | release review |
| \`phase4/charts/*.json\` | approved compatible run summaries | Phase 4 curves/method comparison | chart_id, encoding type, x/y units, tidy data refs/points, run IDs, protocol, status | public reviewed |
| \`phase5/evaluations.v1.json\` | **pending Nex/Owner Phase 5 gate** | Phase 5 | evaluation_id, run/model, population/scope, metrics, diagnostics, evidence | NEVER prepopulate from CV |
| \`phase6/inference-catalog.v1.json\` | approved server model registry **sanitized view** | model selector/readiness | model_id, version, source_run_id, readiness, schema URL, reason if unavailable | public projection |
| \`input-schema.v1.json\` (served per model) | registered fitted raw input/pipeline schema | Phase 6 dynamic form | field ids/type/unit/options/required/dependencies/missingness, pinned model version | public-safe, dynamic |
| **Private** model registry + artifact | trusted build backend/release process | inference server only | artifact/pipeline digest, dependencies, QA/signoff; not URL-exposed as raw pickle | private |

**No Phase 5 empirical artifacts may be fabricated** pending independent design/gate. **No raw rows, CV fold membership indices or per-row sealed Holdout predictions in public JSON.**

## 4. Global JSON conventions (applies to every JSON)

~~~json
{
  "schema_version": "1.0.0",
  "case_id": "ames-housing",
  "status": "UNAVAILABLE",
  "generated_at": null,
  "source": {
    "dataset_version": null,
    "run_id": null,
    "evidence_url": null,
    "artifact_sha256": null,
    "publication_review": "PENDING"
  }
}
~~~

This is a common **envelope template**; each family adds keys and may not need \`run_id\`. Require UTF-8, ISO-8601 UTC \`generated_at\` when generated, stable case/run IDs, string units, source digests. Status vocabulary: \`VERIFIED\`, \`UNAVAILABLE\`, \`PLANNED\`, \`MOCK\`, \`ERROR\` (LOADING/EMPTY are usually runtime UI states, not published research states). All public facts require evidence/source_version and publication status; \`VERIFIED\` applies **per field or subartifact**, not magically to absent children. Distinguish zero, null unknown, not applicable and not published. Use \`available:false\` + \`reason\` where needed. Content validation requires checking counts and cross-file referential integrity, not just JSON parse.

### 4.1 Case index / manifest

~~~json
{
  "schema_version": "1.0.0",
  "cases": [
    {
      "case_id": "ames-housing",
      "title": "Ames Housing",
      "status": "VERIFIED",
      "manifest_ref": "/data/cases/ames-housing/manifest.v1.json"
    }
  ]
}
~~~

Here \`VERIFIED\` means case registry/documented case eligibility, **not every phase complete and not inference ready**. Used Car remains candidate/PLANNED until accepted and published.

~~~json
{
  "schema_version": "1.0.0",
  "case_id": "ames-housing",
  "title": "Ames Housing",
  "methodology_id": "mlr-feature-selection-v1",
  "dataset": {
    "name": "House Prices",
    "source": "Kaggle",
    "url": "https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data",
    "target": {"column": "SalePrice", "unit": "USD"},
    "license_review": "PENDING"
  },
  "phases": {
    "phase1": {"ref": "/data/cases/ames-housing/phase1/context.v1.json", "status": "PLANNED"},
    "phase2": {"ref": "/data/cases/ames-housing/phase2/analyses.v1.json", "status": "PLANNED"},
    "phase3": {"ref": "/data/cases/ames-housing/phase3/preparation.v1.json", "status": "PLANNED"},
    "phase4": {"ref": "/data/cases/ames-housing/phase4/modeling.v1.json", "status": "PLANNED"},
    "phase5": {"ref": "/data/cases/ames-housing/phase5/evaluations.v1.json", "status": "UNAVAILABLE"},
    "phase6": {"ref": "/data/cases/ames-housing/phase6/inference-catalog.v1.json", "status": "UNAVAILABLE"}
  }
}
~~~

**All statuses in this example are design placeholders; do not override actual verified Phase 2 figures.** For ungenerated files, \`ref\` is an **intended location** and must not be served as an actual existing file. Production index should omit nonexistent paths or mark them unavailable with no fetch.

### 4.2 Phase 1 content

~~~json
{
  "schema_version": "1.0.0",
  "case_id": "ames-housing",
  "dataset": {"name":"House Prices","source":"Kaggle","url":"https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data"},
  "business_context": {
    "problem":"如何依據住宅條件估計住宅售價？",
    "objective":"探索住宅特徵與售價的關聯，並建立可解釋的預測基準。",
    "value":"作為住宅價格迴歸與特徵選擇的教學案例。"
  },
  "prediction_target":{"column":"SalePrice","unit":"USD"},
  "methodology_id":"mlr-feature-selection-v1"
}
~~~

### 4.3 Phase 2 analyses and static image references

~~~json
{
  "schema_version": "1.0.0",
  "case_id": "ames-housing",
  "analyses": [
    {
      "id": "missingness",
      "title": "缺失值分析",
      "figure_id": "FIG-02",
      "image": {
        "svg_ref": "/figures/ames-housing/phase2/fig02_missingness_overview.svg",
        "png_ref": "/figures/ames-housing/phase2/fig02_missingness_overview.png",
        "alt": "每個欄位缺失值比例與結構性缺失的彙整",
        "accessible_table_ref": null
      },
      "description": "分析各欄位缺失比例與缺失原因。",
      "finding": "部分 NA 代表設施不存在，不能直接視為資料遺漏。",
      "limitations": "缺失值分析本身不代表已完成插補處理。",
      "next_impact": {
        "phase": 3,
        "statement": "檢視實際採用的缺值策略",
        "status": "CANDIDATE"
      },
      "population": "Kaggle labeled train",
      "denominator_rows": 1460,
      "status": "VERIFIED",
      "source": {
        "evidence_url": "https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/main/docs/crisp-dm/02-data-understanding.md",
        "publication_review": "REQUIRED"
      }
    }
  ]
}
~~~

**Release constraints:** Above is only an object example; source/report reference and existing four Phase 2 published images must be revalidated on the export branch/version. Only approved FIG-01/02/03/06 eligible based on prior design audit; other eight/87 local EDA candidates are not automatically public. No image URL may point to an uncommitted local path. Figure and explanation swap **atomically** for analysis selected by id.

### 4.4 Phase 3 four-stage bars, treatment accordion and split

~~~json
{
  "schema_version": "1.0.0",
  "case_id": "ames-housing",
  "feature_type_order": ["nominal", "ordinal", "discrete", "continuous"],
  "stages": [
    {"id":"raw","unit":"raw_columns","total":79,"total_status":"VERIFIED","distribution_status":"UNAVAILABLE","segments":[],"evidence_ref":null},
    {"id":"filtered","unit":"raw_columns","total":null,"total_status":"UNAVAILABLE","distribution_status":"UNAVAILABLE","segments":[],"excluded_count":null,"excluded_columns_ref":null,"evidence_ref":null},
    {"id":"processed","unit":"pre_encoding_columns","total":null,"total_status":"UNAVAILABLE","distribution_status":"UNAVAILABLE","segments":[],"evidence_ref":null},
    {"id":"encoded","unit":"encoded_features","total":248,"total_status":"VERIFIED","distribution_status":"UNAVAILABLE","segments":[],"feature_lineage_ref":null,"evidence_ref":null}
  ],
  "treatments": [
    {"type_id":"nominal","operations":[],"status":"UNKNOWN","evidence_ref":null},
    {"type_id":"ordinal","operations":[],"status":"UNKNOWN","evidence_ref":null}
  ],
  "split": {
    "source_labeled_rows": 1460,
    "training_set_rows": 1168,
    "holdout_test_rows": 292,
    "random_seed": 42,
    "competition_unlabeled_test_rows": 1459
  }
}
~~~

When VERIFIED, each \`segments[]\` entry is \`{"type_id":"nominal","count":N,"source_type_id":"nominal"}\` and the sum of counts MUST equal stage.total. Percentage **computed from counts by frontend**, denominator stage total; do not independently store rounded percentages. Consistent colors/order by original source type; encoded stage attributes expanded outputs to their **original source type**, not numeric dtype after encoding. Missing-indicator or custom derived fields need explicit lineage and a deliberate classification; if uncertain, distribution stays unavailable. Stage ③ uses accordion operations such as \`{"operation_id":"impute_median","status":"APPLIED","affected_raw_fields":[...],"fit_scope":"training-fold-only","evidence_ref":"..."}\` **only when verified**; never claim an arbitrary method was used. Phase 3 source facts documented to date: original candidates **79** and encoded model inputs **248**; exclusion and per-type shares still require audit. \`97\` selected encoded features belongs to one Phase 4 outcome, not a Phase 3 total.

### 4.5 Phase 3 raw→encoded lineage

~~~json
{
  "schema_version": "1.0.0",
  "case_id": "ames-housing",
  "pipeline_revision": null,
  "status": "UNAVAILABLE",
  "mappings": [
    {
      "raw_field_id": "EXAMPLE_NominalField",
      "source_type_id": "nominal",
      "operation": "one_hot",
      "encoded_feature_ids": ["EXAMPLE_NominalField_A","EXAMPLE_NominalField_B"],
      "generated_count": 2,
      "evidence_ref": null
    }
  ]
}
~~~

The mapping is **MOCK illustrative**, not an Ames factual field/output. Production \`status=VERIFIED\` requires a fully reconciled exhaustive mapping to a specific pipeline version/feature matrix, including generated missingness indicators and provenance. Field IDs/labels may be public only if release review permits.

### 4.6 Phase 4 method registry and immutable valid run inventory

~~~json
{
  "schema_version": "1.0.0",
  "case_id": "ames-housing",
  "cv": {
    "protocol_id": "development-3fold-cv",
    "training_set_label": "Training Set",
    "training_set_rows": 1168,
    "holdout_test_rows": 292,
    "fold_count": 3,
    "metric": {"id":"rmse","display":"CV RMSE","direction":"lower_is_better","unit":"USD"},
    "splitter": null,
    "shuffle": null,
    "cv_seed": null,
    "folds_ref": "/data/cases/ames-housing/phase4/runs/EXAMPLE-RUN/cv-folds.v1.json"
  },
  "methods": [
    {"id":"pearson","label":"Pearson","kind":"feature_selection","parameters":[{"id":"top_k","label":"Top K","type":"integer","control":"select"}]},
    {"id":"mutual_information","label":"Mutual Information","kind":"feature_selection","parameters":[{"id":"top_k","label":"Top K","type":"integer","control":"select"}]},
    {"id":"ridge_rfe","label":"Ridge-RFE","kind":"feature_selection","parameters":[{"id":"top_k","label":"Top K","type":"integer","control":"select"}]},
    {"id":"lasso","label":"Lasso","kind":"feature_selection","parameters":[{"id":"alpha","label":"Alpha","type":"number","control":"select"}]},
    {"id":"elastic_net","label":"Elastic Net","kind":"feature_selection","parameters":[{"id":"alpha","label":"Alpha","type":"number","control":"select"},{"id":"l1_ratio","label":"L1 Ratio","type":"number","control":"select"}]},
    {"id":"ols_baseline","label":"OLS Baseline","kind":"baseline","parameters":[]}
  ],
  "runs": [],
  "default_run_id": null
}
~~~

\`runs: []\` deliberately prevents fake empirical runs. Add \`runs[]\` only after audit, with \`run_id,method_id,params,protocol_id,track,status,metadata_ref,cv_metrics_ref,selected_features_ref,evidence_ref\`. **Derive dropdown allowed values from full eligible \`runs[].params\` tuples**. Do not infer all combinations from independent field options. Method definitions may exist with zero runs and appear disabled/unavailable. Unqualified "CV seed 42" is prohibited unless separately verified (Phase 3 split seed is 42 but CV splitter seed can differ).

### 4.7 Per-run metadata, fold partition and metrics

~~~json
{
  "schema_version": "1.0.0",
  "case_id": "ames-housing",
  "run_id": "EXAMPLE-RUN",
  "method_id": "pearson",
  "params": {"top_k": 5},
  "protocol_id": "development-3fold-cv",
  "track": "selected_to_ols",
  "encoded_selected_count": null,
  "original_selected_count": null,
  "dataset_version": null,
  "feature_mapping_version": null,
  "split_id": null,
  "seed": null,
  "status": "MOCK",
  "artifact_sha256": null,
  "evidence_ref": null
}
~~~

~~~json
{
  "case_id": "ames-housing",
  "run_id": "EXAMPLE-RUN",
  "protocol_id": "development-3fold-cv",
  "fold_count": 3,
  "total_rows": 1168,
  "folds": [
    {"fold":1,"training_rows":null,"validation_rows":null,"validation_segment_index":0},
    {"fold":2,"training_rows":null,"validation_rows":null,"validation_segment_index":1},
    {"fold":3,"training_rows":null,"validation_rows":null,"validation_segment_index":2}
  ],
  "status": "UNAVAILABLE"
}
~~~

For schematic fold bars, layout may show approximately 2/3 training and 1/3 validation; actual row counts and per-fold membership evidence must come from run's splitter. Never include row indices in public. If real protocol uses a different fold type, use truthful segments/counts rather than pretending 3 identical contiguous slices.

~~~json
{
  "case_id":"ames-housing",
  "run_id":"EXAMPLE-RUN",
  "protocol_id":"development-3fold-cv",
  "scope":"development_cv",
  "metric":"rmse",
  "unit":"USD",
  "direction":"lower_is_better",
  "fold_values":[],
  "mean":null,
  "std":null,
  "status":"UNAVAILABLE",
  "evidence_ref":null
}
~~~

No mean or SD should be synthesized from cross-incompatible runs. In verified cases, if \`fold_values\` exists, cross-check \`mean/std\` and declared ddof convention; if only aggregate evidence exists, \`fold_values\` may be unavailable even while mean is verified.

~~~json
{
  "case_id":"ames-housing",
  "run_id":"EXAMPLE-RUN",
  "status":"UNAVAILABLE",
  "features":[
    {
      "encoded_feature_id":"EXAMPLE_feature",
      "raw_source_field_ids":["EXAMPLE_raw"],
      "rank":null,
      "coefficient":null,
      "selected":null
    }
  ],
  "encoded_selected_count":null,
  "evidence_ref":null
}
~~~
Example feature IDs are mock only; never display as evaluated/selected before audit.

### 4.8 Chart manifest + tidy points (frontend plotting)

~~~json
{
  "schema_version":"1.0.0",
  "case_id":"ames-housing",
  "chart_id":"feature-count-vs-cv-rmse",
  "chart_type":"line",
  "status":"UNAVAILABLE",
  "title":"Selected Encoded Features vs CV RMSE",
  "x":{"field":"encoded_selected_count","label":"Selected encoded features","unit":"features","scale":"linear"},
  "y":{"field":"cv_rmse_mean","label":"Mean CV RMSE","unit":"USD","scale":"linear"},
  "series_field":"method_id",
  "points_ref":null,
  "point_fields":["run_id","method_id","encoded_selected_count","cv_rmse_mean","cv_rmse_std","protocol_id","track"],
  "compatible_protocol_id":"development-3fold-cv",
  "evidence_ref":null,
  "assets":{"svg_ref":null,"png_ref":null,"accessible_table_ref":null}
}
~~~

Verified \`points_ref\` is same-case/version JSON of records keyed \`run_id\`; no interpolation for missing K values, no fabricated smooth curve. Comparisons filter same metric/scope/track/protocol. Optional error bars need actual SD, else absent. Tables must show actual numbers and provenance. Render a graph natively from JSON or preapproved SVG/PNG; both must derive from the **same immutable points**.

### 4.9 Phase 5 reserved evaluation payload — interface only, NOT a claim of results

~~~json
{
  "schema_version":"1.0.0",
  "case_id":"ames-housing",
  "status":"UNAVAILABLE",
  "reason":"PHASE5_REVIEW_PENDING",
  "evaluations":[],
  "proposed_evaluation_record_shape":{
    "evaluation_id":"string",
    "run_id":"string",
    "model_id":"string-or-null",
    "scope":"holdout_or_other_explicit_scope",
    "holdout_approved":false,
    "metrics_ref":null,
    "diagnostics_ref":null,
    "evidence_ref":null
  }
}
~~~

Do not compute or publish Phase 5 charts, ranked holdout scores, residual plots or prediction intervals from this outline. Design pending Nex. Phase 4 CV may be read without any Phase 5 approval.

### 4.10 Phase 6 public registry view and model-bound input schema

~~~json
{
  "schema_version":"1.0.0",
  "case_id":"ames-housing",
  "title":"房價預測實驗室",
  "target":{"column":"SalePrice","label":"預測房價","unit":"USD"},
  "models":[],
  "readiness":{
    "status":"UNAVAILABLE",
    "reason_code":"NO_APPROVED_MODEL",
    "message":"此模型尚未準備好"
  }
}
~~~

\`models[]\` populated only by approved, registered published model views. A real eligible model includes \`model_id,model_version,source_run_id,readiness_status,input_schema_ref,target\` but not private object path or arbitrary disk/URL loading.

~~~json
{
  "schema_version":"1.0.0",
  "case_id":"ames-housing",
  "model_id":"EXAMPLE-MODEL",
  "model_version":"EXAMPLE-VERSION",
  "input_schema_version":"EXAMPLE-SCHEMA",
  "status":"MOCK",
  "fields":[
    {
      "raw_field_id":"GrLivArea",
      "source_column":"GrLivArea",
      "label":"地上居住面積",
      "type":"numerical",
      "control":"number",
      "unit":"sqft",
      "required":true,
      "min":1,
      "max":null,
      "missingness_kind":"not_permitted",
      "dependencies":[],
      "preprocessing_ref":null
    },
    {
      "raw_field_id":"Neighborhood",
      "source_column":"Neighborhood",
      "label":"社區",
      "type":"nominal",
      "control":"select",
      "required":true,
      "allowed_values":[],
      "missingness_kind":"not_permitted",
      "dependencies":[],
      "preprocessing_ref":null
    }
  ]
}
~~~

Example fields are NOT a complete Ames input schema; \`allowed_values:[]\` means unknown, not permissive. Final schema must be generated from exact **fitted model pipeline** rather than using Phase 2 dictionary or Phase 4 K as an input count. Structural absent/unknown missing/unentered required are separate states. The basic form is forbidden until omission policies are verified.

## 5. HTTP API contract (only prediction requires live computation)

**Prefer static GET JSON from public asset paths for Phase 1–4**. Dynamic GET endpoints can be thin read-only facades if later needed; do not force a database service just to display frozen research. Endpoint descriptions below are **PROPOSED**, not deployed.

| Method/path | Request | Response / behavior |
|---|---|---|
| \`GET /data/index.v1.json\` | none | case registry for global dropdown, version/cache metadata |
| \`GET /data/cases/{case_id}/manifest.v1.json\` | known case | phase refs, status and source; scoped |
| \`GET /data/cases/{case_id}/phaseN/*.v1.json\` | refs from manifest | offline facts/figures/runs, not inference |
| \`GET /api/cases/{case_id}/models\` | case ID | **approved public projection**; registry readiness may be dynamic |
| \`GET /api/models/{model_id}/input-schema?version={model_version}\` | explicit approved model/version | model-bound schema, eligible fields/allowed categories, API readiness |
| \`GET /api/models/{model_id}\` | model ID | public model identity/source run/status/version metadata, not artifact bytes |
| \`POST /api/predictions\` | model/case/run/schema + raw_inputs | validated model inference, output and trace only if ready |
| \`GET /api/health\` | none | minimal public status only, no internal model paths or private error dumps |
| \`GET /api/runs/{run_id}\` | optional, if not statically hosted | read-only approved immutable metadata; scope by case/auth if needed |

**Prediction request**
~~~json
{
  "case_id":"ames-housing",
  "run_id":"EXAMPLE-RUN",
  "model_id":"EXAMPLE-MODEL",
  "model_version":"EXAMPLE-VERSION",
  "schema_version":"EXAMPLE-SCHEMA",
  "raw_inputs":{
    "GrLivArea":1500,
    "Neighborhood":"NAmes"
  }
}
~~~
**Not executable:** fake model/run IDs and incomplete raw fields. Real server verifies case→run→model relationship, input schema and version, all required raw fields, allowed categories, unit/range, structural absence/unknown, field dependencies and backend model/artifact approval; uses pinned fitted transformations; **no request-time fitting**.

**Prediction success**
~~~json
{
  "status":"success",
  "request_id":"generated-server-id",
  "case_id":"ames-housing",
  "run_id":"verified-source-run",
  "model_id":"registered-model-id",
  "model_version":"registered-version",
  "target":{"column":"SalePrice","unit":"USD","prediction":null},
  "prediction_interval":null,
  "provenance":{"pipeline_version":"pinned-version","artifact_sha256":"approved-digest"}
}
~~~
\`prediction:null\` is **shape placeholder only**: real success must contain a finite number (not null or NaN); if unavailable response is non-success. Interval null unless independently validated and labeled. Never return holdout metrics from a single prediction request.

**Prediction failure**
~~~json
{
  "status":"error",
  "request_id":"generated-server-id",
  "code":"MODEL_UNAVAILABLE",
  "message":"此模型尚未準備好，請選擇其他已核准模型或返回 Phase 4。",
  "field_errors":{}
}
~~~

| HTTP group | Codes | UI action |
|---|---|---|
| 400/422 | \`INCOMPLETE_INPUT\`, \`UNKNOWN_CATEGORY\`, \`INVALID_UNIT\`, \`OUT_OF_RANGE\`, \`INVALID_FIELD_DEPENDENCY\` | Field-specific fixes, do not issue prediction |
| 404 | \`CASE_NOT_FOUND\`, \`RUN_NOT_FOUND\`, \`MODEL_NOT_FOUND\` | Clear stale state, return to selector |
| 409 | \`MODEL_UNAVAILABLE\`, \`SCHEMA_MISMATCH\`, \`MODEL_NOT_APPROVED\` | Not Ready panel and alternate model/Phase 4 |
| 429 | \`RATE_LIMITED\` | Retry guidance after server interval |
| 500/503 | \`API_UNAVAILABLE\`, \`PREDICTION_FAILED\` | Clear stale result and show safe retry; no raw trace |

Security proposal for later review: approved allowlist, signed/verified artifacts, no user-provided pickle/paths, request size and concurrency caps, rate limits, TLS, controlled CORS, no raw request fields in public logs by default, safe error sanitization, health/status, optional auth if exposure requires it. Resolve hosting and model runtime (Vercel serverless vs other) **after** auditing model sizes/cold starts and fitted pipeline dependencies; no host commitment here.

## 6. Figure inventory, sizes and exact page placement

**General:** images generated from the **same immutable, cited numeric/export data** as front-end graphs, not manually corrected screenshots. Prefer vector SVG for static EDA plus PNG fallback; native bar charts from JSON for four Phase 3 stages and Phase 4 fold bars. All figures have \`chart_id/figure_id\`, title, population N, unit, subtitle, source/version/run where relevant, legend, accessible alternative table/alt, review status. Avoid misleading truncated axes, unsupported smoothing, hidden unknowns and inconsistent denominators.

| Page + placement | Visualization | Delivery | Dimensions (recommended, NOT fixed requirement) | Important contracts |
|---|---|---|---|---|
| Phase 1 | **none** | textual JSON | n/a | no generic irrelevant illustration |
| Phase 2 selector → one main figure | FIG-01 dataset overview | SVG + PNG | landscape **16:9**, export SVG viewBox ~1200×675, PNG ~1600×900 | Kaggle train/test population distinguished |
| Phase 2 selector → one main figure | FIG-02 missingness | SVG + PNG | landscape 16:9 or taller when axes need legibility | structural absence ≠ unknown missing |
| Phase 2 selector → one main figure | FIG-03 target SalePrice | SVG + PNG | landscape ~16:9 | N=1460, SalePrice USD, descriptive not residual |
| Phase 2 selector → one main figure | FIG-06 correlations | SVG + PNG | near-square or landscape as needed for cell labels | association not causation/model ranking |
| Phase 3 **four vertical successive sections** | Original type distribution | **native 100% stacked bar** from \`stages[0].segments\` | responsive width, ~32–48px high bar (proposal) | 79 known aggregate; category counts pending |
| Phase 3 section ② | Retained distribution | same native bar structure | same height/order/colors | if no exclusions verified, same counts; otherwise evidence |
| Phase 3 section ③ + accordion underneath | Processed distribution | same native bar | same | accordion per actual type below bar |
| Phase 3 section ④ | Encoded type lineage distribution | same native bar | same | percentages can change; denominator 248 features, not 79 |
| Phase 3 last section | Train–Test Split | native two-part row bar | same horizontal idiom | 80% / 1,168 training rows; 20% / 292 holdout rows |
| Phase 4 **top** | 3-Fold CV diagram | three native segmented horizontal bars | consistent width ~32–48px each | ~66.7/33.3 each rotation; exact counts when known |
| Phase 4 perspective: method comparison | compatible CV RMSE bar/point | tidy JSON native; optional reviewed SVG/PNG | landscape 16:9 | scope/metric/protocol/run comparability |
| Phase 4 perspective: selected features | selected features ranked table/plot | JSON native | vertical scroll as needed | raw↔encoded mapping, K from actual run |
| Phase 4 perspective: feature count vs CV | scatter/line + points | tidy JSON native; optional reviewed SVG/PNG | landscape 16:9 | only actual measured K; no synthetic interpolation |
| Phase 5 | **deferred**: evaluation metrics/actual-vs-predicted/residual | reserved only | **TBD by Nex/Owner** | no invented Holdout result/figure |
| Phase 6 left | raw input form | model-specific schema API | desktop two-column | never ask for 248 encoded field inputs |
| Phase 6 right | prediction result / error | live response API | desktop two-column | no prefilled numeric estimate, no unvalidated interval |

**Chart typography and export acceptance** (recommended initial defaults to permit independent rebuilding; not Owner-approved precise pixel gate):
- SVG uses sensible \`viewBox\`, responsive container \`max-width:100%; height:auto\`, preserves axes and legends. PNG fallback at least **1600×900** for landscape desktop figures; give exact produced width/height in manifest. Square/dense correlation charts may use larger height and must not be forced into 16:9 cropping.
- Keep readable title/axis/caption with legible label density at a 1920×1080 viewport; wrap/rotate category labels intentionally, prefer showing a table over illegible crowded heatmap ticks.
- Theme-consistent accessible color palette, **same colors per feature type across Phase 3**, and training vs validation colors consistent within Phase 4. Include text legend and not color alone; meet documented WCAG contrast target.
- Filenames: lowercase ASCII kebab/snake as already established figures, stable figure ID; \`figXX_...svg\`, PNG same basename. Don't rename previously reviewed figures without preserving links/manifest and review.
- SVG static render is untrusted content: sanitize exported SVG, avoid scripts/external refs/fonts; prefer embedding sanitized image element, not unsanitized inline HTML. Confirm licensing and metadata (no local machine paths or usernames in exported images).
- **Accessible equivalence:** text alt + adjacent finding/limitation and a table of measured values (or linked approved aggregate table). Raster is not authoritative numeric output; underlying JSON/CSV table is.
- Print source, measurement scope/denominator, units and QA state near graphics; keep legends and source on same viewport when possible.
- Every published figure has a manifest with \`figure_id,case_id,phase,source_run_id/null,svg_ref,png_ref,alt,accessible_table_ref,width,height,sha256,source_evidence_ref,publication_review,status\`. Check the image and manifest digest agree; broken URLs fail build.

## 7. Offline exporter specification — handoff to Codex/runner engineer, **NOT authorized to implement yet**

**Input**: approved Phase 1 narratives + Phase 2 EDA reports/reviewed figures + Phase 3 quality/feature mapping + Phase 4 run inventory/metrics/fold protocol + future Phase 5 evaluations + approved registered models. Each comes with original source file/version, hash, publisher approval and QA status. **NEVER derive real empirical values from narrative guesses or fake sample runs.**

**Proposed commands (names and flags are illustrative and do not yet exist):**
~~~bash
python tools/export_research_contract.py --case ames-housing --source local/research/ames-housing \
  --out local/export-staging/ames-housing --mode aggregate-only
python tools/validate_research_contract.py --input local/export-staging/ames-housing \
  --schemas contracts/v1 --strict
python tools/render_verified_figures.py --input local/export-staging/ames-housing \
  --out local/export-staging/figures --approved-only
~~~

**Required sequential pipeline**:
1. **Inventory/read-only** every current evidence source, actual file, manifest, run list and existing public asset. Distinguish figure published/verified vs local-only, and model artifact existing vs CV-only. Generate an evidence coverage table and missing-data report.
2. **Extract aggregate** with Python; generate canonical case_id/run_id/model_id links; no methods/results invented. Timestamp, content digests, dependency metadata and immutable run IDs.
3. **Calculate/check** source row counts, 80/20 split with known seed, raw/encoded feature counts, type-by-type stage sum, exclusion reconciliation, feature lineage coverage, CV fold train+val sums, Fold count vs metric records, valid run parameter tuple and comparable CV protocol/track; no leakage across train/validation folds. Null/UNAVAILABLE for anything not independently verifiable.
4. **Render** only allowed figures and write exact metadata/alt/alternative table and digests. Existing QA-approved Phase 2 images should be reused if consistent rather than unnecessarily regenerated or silently altered. Source plot data remains separate from static images.
5. **Validate JSON Schema and cross-file references**, every ref resolves inside approved publication root, MIME/magic check SVG/PNG, public-safety/license filter, no private absolute paths, no raw house rows or holdout predictions. Fail on incorrect schema, missing assets, partial mapping presented verified, incompatible experiments or mismatched model identity.
6. **Publish via separate reviewed PR/gate** to public static root, copying only allowlisted staging artifacts and immutable hash files; never auto-push from a scientific computation run. Manifest points only to files that actually exist in same release; no broken stubs.
7. **Smoke test** static GETs and UI selector-to-figure bindings; validate run/params → selected chart → Phase 5 placeholder → Phase 6 model readiness, including zero-ready-model UI.
8. **Only in later approved inference phase**: register fitted pipelines privately, verify artifact digests+environment, deploy API with validation/limits/health, verify end-to-end prediction and refusal on invalid model/schema/category; no live Predict until PASS.

**Exporter deliverables and acceptance**:
- \`coverage-report.md/json\`: each proposed artifact = PRESENT VERIFIED / PRIVATE / MISSING / PROPOSED, evidence source and actual repository path; no fictional existing files.
- \`export-report.json\`: counts of cases/runs/figures, source digests, SHA checks, unpublished/unavailable items and reasons, schema validator version, explicit PASS/FAIL.
- \`references-report.json\`: all internal \`*_ref\` paths resolved or flagged and case-scoped.
- **No** publish on partial FAIL; retain local diagnostics, not private data in public log.

## 8. Frontend rendering orchestration (exact user events)

1. Site loads \`index.v1.json\` → global dataset select values. Select case → fetch manifest + current phase resource; old case data immediately cleared.
2. Phase 1: display read-only text.
3. Phase 2: \`analyses[]\` builds buttons → selected \`id\` resolves exactly ONE approved figure and same-analysis prose/accessible data.
4. Phase 3: each stage's \`segments\` generates a full-width 100%-stacked bar (count/total) with stable type colors; types with unknown count render not-a-chart pending state, not equal demo-width. Stage ③ accordion displays verified method handling; ④ dynamically expands type contribution; bottom row split bar.
5. Phase 4: \`methods[]\` defines parameter controls, but dropdown values **ONLY from eligible complete \`runs[]\` tuples**; selected \`run_id\` fetches metadata/folds/CV/results with compatible protocol. Perspective tabs show ONE result at once; fold bars read fixed training metadata. \`View Evaluation\` passes \`case_id,run_id\`; \`Use Model\` passes lookup context.
6. Phase 5: until Nex gate, \`UNAVAILABLE\` or approved evaluation only. No assumptions from Phase 4 CV.
7. Phase 6: \`case_id+run_id\` query eligible model registry; select \`model_id+version\` → fetch exact raw input schema; model change clears values/prediction. Validate inputs → POST prediction only when model/pipeline/API ready. If unavailable, show 「此模型尚未準備好」 and reason; \`Choose another ready model\` or \`Return Phase 4\` preserving run config. No HTML form input for transformed One-Hot columns.
8. Any case/run/model/parameter change cancels or marks stale prior requests; only apply response if correlation context matches current selected identifiers.

## 9. Open work inventory: what is known vs still missing

| Item | Current knowledge | Next prerequisite |
|---|---|---|
| Ames source candidate predictors | **79** | type classifications and exclusion audit |
| Phase 3 final encoded dimensions | **248** | exhaustive raw→encoded mapping, types/indicators |
| Labeled train rows | **1,460** | split evidence cross-check |
| Phase 3 Training/Development rows | **1,168** | exact split identity/version |
| Sealed Holdout rows | **292** | Phase 5 gate, no leakage |
| Kaggle unlabeled competition test | **1,459** | keep separate |
| CV protocol | **3-Fold** within Development/Training | exact splitter/seed and fold-size source |
| Phase 4 methods | Lasso, Pearson, MI, Ridge-RFE, Elastic Net + OLS baseline | actual run inventory and exact params/status |
| Phase 2 published figures | FIG-01, FIG-02, FIG-03, FIG-06 previously independently reviewed | confirm current branch URLs and publication license |
| Per-type Phase 3 proportions | **UNKNOWN** | dictionary/Pipeline export |
| All method×parameter combinations | **not all automatically valid** | immutable audited \`runs[]\` |
| Phase 5 metrics/graphs | **PENDING Nex** | formal Issue and approvals |
| Deployable fitted models | **UNKNOWN/NOT PROVEN** | private artifact audit + registry approval |
| Model-specific raw input list | **UNKNOWN** | fitted pipeline/input schema contract |
| Prediction API | **not deployed by this doc** | future architecture/build/test gate |

## 10. Review gates and acceptance criteria

- **Nex independent technical review:** case/run/model provenance invariants, no false model readiness, safe model loading, train/CV/holdout isolation, dynamic method tuple enumeration, ability to generate static JSON.
- **Scientific/QA review:** EDA figures and stage counts correct, no stale/unsupported metrics, method × K/Alpha compatibility, actual CV protocol, selected original vs encoded features differentiated.
- **Security/publication review:** only approved aggregated data/images public, no untrusted pickle loading, schema/SSRF/raw CSV hazards, no sensitive machine paths/indices, limits and safe errors.
- **Frontend reconstruction review:** exact four Phase 3 bars, Phase 4 three fold bars, one-at-a-time EDA and CV views, Phase 6 dynamic form, understandable unavailable states and navigation.
- **Owner approval gates:** Phase 5 design separate; export tooling implementation separate; public release separate; inference server and deployed model separate; merge/deploy explicitly separate.

**This document authorizes only detailed design specification in the existing Draft PR #35.**
