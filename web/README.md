# RegScope — Static Web Research Explorer

`web/` is a static HTML/CSS/JavaScript client. It uses reviewed JSON Case Packages and browser-side presentation/validation logic. It has **no production server-side model inference or Prediction API**. The platform is a research evidence explorer, not an online model-training service.

**Current public release-index cases** (`web/data/current-release.json`):

- **Ames Housing — Full Model Exploration** (`ames-full-model-exploration`, default; package `PARTIAL`).
- **Used Car Price Prediction — Optimized Modeling** (`used-car-price-optimized`; package `PARTIAL`).

Mock, Placeholder and INIT B are **retired from the active selector**, not necessarily removed from historical source, test fixtures or local-only preview branches. Do not use old prototype code as evidence that a mock is publicly selectable.

## Routes and interactions

- Hash routes: `#home`, `#dashboard`, `#phase-1` through `#phase-6`; case picker applies across the six-phase journey.
- **Dashboard:** Verified Research presentation and Custom Dataset preview are separate modes. Custom Dataset reads a local CSV header/sample in the browser; a URL field is format-validated only; remote loading/training/Run is disabled.
- **Phase 3:** transformation stages and source-feature lineage. CAR distinguishes raw fields, excluded/retained fields and post-encoding feature counts. These are not interchangeable denominators.
- **Phase 4:** Method Comparison and Explorer present recorded configurations, fold metrics and feature-count/CV-RMSE curves when package-bound and eligible. Unexecuted configurations are not filled in.
- **Phase 5:** distinguishes `cv_fold_mean` and `pooled_oof`, ties evaluations to the chosen configuration and run, and renders diagnostics only when eligible public evidence exists. Neither calculation is automatically Holdout.
- **Phase 6 — 模型預測與結果 (Model Prediction & Results):** Owner-approved future-facing page heading while the CRISP-DM stage stays **Deployment／部署**. The released source still contains historical `模型預測實驗室` / `房價預測實驗室` UI copy, not updated by this docs-only PR. Current readiness/status panels; CAR local model reload smoke does not certify predictive fitness. Legacy manual / CSV mock UI in the source is not deployed model inference; **no online Prediction API is implemented**. Do not interpret fixed mock outputs as calculated predictions.

The public loader validates package identity, manifest paths, size and SHA-256 before using source-bound artifacts. These checks prove file integrity within their scope, **not** model quality, license clearance or scientific publication approval. CAR's CV modeling result did **not** beat the Dummy baseline. CAR competition-specific redistribution Rules remain `PENDING`.

## Preview locally

From the repository root, with Python installed:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Then open http://127.0.0.1:8000/web/ . This loopback-only static preview does not run the Python model; do not expose a local checkout/server to a network. Some historical code may reference ignored private staging packages for local-only experiments; that does not make them production artifacts.

## Deployment and limitations

The repository root `vercel.json` sets `web/` as the static output directory. `main` is integration; `deploy` is reserved for production releases. At Issue #62's 2026-10-29 baseline, PR #61's direct-route blocking was merged to `main` but not yet released to `deploy`; **production HTTP 404 behavior for retired package URLs remained UNKNOWN**, even though the selector was reduced to two cases.

Traditional Chinese (`zh-Hant`) and English are mixed in the visible UI; this is **not** a verified complete two-language locale system. Responsive CSS breakpoints exist, but no independent browser breakpoint acceptance is claimed by these docs.

For the canonical navigation, status, terminology and research-evidence boundaries, consult [Production UX Baseline](../docs/ui-ux/REGSCOPE-PRODUCTION-UX-BASELINE.md) and [Reconciliation / Terminology Audit](../docs/ui-ux/REGSCOPE-SPEC-RECONCILIATION.md). [Historical PR #35](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35) is CLOSED/UNMERGED and non-normative.

Never place source datasets, raw vehicle records/VIN, private model binaries, row-level OOF, credentials or unreviewed artifacts in `web/`. Follow [Security and Data Policy](../docs/SECURITY_AND_DATA_POLICY.md).
