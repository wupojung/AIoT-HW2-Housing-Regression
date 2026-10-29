# RegScope | NCHU AIoT 2026 — Research Case Explorer

**Production site:** https://regscope-aiot.vercel.app/

RegScope is a static, CRISP-DM-oriented presentation of machine-learning regression research. The currently published release index lists two active cases:

1. **Ames Housing — Full Model Exploration** (`ames-full-model-exploration`, default).
2. **Used Car Price Prediction — Optimized Modeling** (`used-car-price-optimized`).

Both Case Packages are **PARTIAL**. Public presentation of recorded research evidence does **not** mean all phases, diagnostic charts, final fits, publication reviews or prediction services are complete. The used-car model's CV performance did **not** surpass its Dummy baseline. CAR dataset attribution is recorded, but competition-specific Kaggle redistribution Rules remain **PENDING independent review**.

## Current UX and evidence

The site offers Home, Dashboard, a case-wide selector and six CRISP-DM phases. The Dashboard distinguishes reviewed-research display from **browser-local Custom Dataset CSV preview** (not upload/model training). Phase 3 includes source/encoded feature lineage; Phase 4 offers method comparison and model exploration based on actual recorded configurations; Phase 5 distinguishes CV fold-mean from pooled OOF evaluation. Phase 6 presents case-specific readiness and unavailable states. **No online Prediction API or batch prediction service is deployed.**

The selector no longer lists historical Mock, Placeholder or INIT B cases. Historical fixtures can remain in source control. PR #61 added a direct-route restriction to `main`, but it was **not present in `deploy`** at the documentation evidence watermark; do not claim production 404 until independently verified.

**Authoritative UI documents:** [Production UI/UX Baseline](docs/ui-ux/REGSCOPE-PRODUCTION-UX-BASELINE.md) and [Specification Reconciliation & Terminology Audit](docs/ui-ux/REGSCOPE-SPEC-RECONCILIATION.md). The older [PR #35](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35) is closed **without merge**, retained only as historical design context. Source validation is not equivalent to independent production-browser validation.

## CRISP-DM

1. **Business Understanding — 業務理解:** research question, target and approved source context.
2. **Data Understanding — 資料理解:** recorded data summaries and evidence availability.
3. **Data Preparation — 資料準備:** transformation, excluded columns and feature lineage.
4. **Modeling — 模型建立:** recorded configurations, methods and development cross-validation.
5. **Evaluation — 模型評估:** scoped CV / out-of-fold metrics, evidence and limitations.
6. **Deployment — 部署:** readiness and publication boundary; **not** an implemented online inference API.

Research protocols and validation status are governed by their source artifacts and [CRISP-DM documents](docs/crisp-dm/README.md), not by UI labels. Holdout results are not interchangeable with Development CV / OOF.

## Repository map

- `web/` — static site, release index and reviewed public research artifacts.
- `python/src/` — research/experiment Python code; its existence does not make the browser a model runtime.
- `tests/` — applicable automated tests.
- `docs/` — research, security, design and authoritative UI documents.
- `tools/` — project utilities.
- `local/` — private, ignored working data, never deployed.

## Data, workflow and release boundaries

Follow [AGENTS.md](AGENTS.md) and [Security and Data Policy](docs/SECURITY_AND_DATA_POLICY.md). Do not commit raw Kaggle CSVs, private rows, VIN/free text, row-level OOF, fitted model binaries, secrets, local research files or unreviewed outputs. A public data source does not automatically authorize redistribution.

`main` is integration; `deploy` is the approved production release branch. Documentation and development merges do not themselves authorize Production deployment. Required security checks and actual branch protection should be verified against current settings rather than inferred from historical instructions. For environment setup, see [Python Environment](python/README.md) and [Developer Setup](docs/SETUP.md).

Issue #62 documentation watermark (2026-10-29): `main` `40a153d522b49aab4594470f0eb493b6eae26807`, `deploy` `65c7ef0e5f3ccd7aac1c6a90f32fc287a4b50602`. Actual Production browser/HTTP verification remained **UNKNOWN** in that audit.
