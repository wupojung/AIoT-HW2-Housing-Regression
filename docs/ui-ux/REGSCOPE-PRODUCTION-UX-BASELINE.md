# RegScope — Production UI/UX Baseline

> Status: CURRENT where explicitly evidenced; otherwise UNKNOWN or PROPOSED. Issue #62, 2026-10-29. Documentation baseline, **not** permission for implementation.
>
> Evidence watermarks: `main` `40a153d522b49aab4594470f0eb493b6eae26807`; `deploy` `65c7ef0e5f3ccd7aac1c6a90f32fc287a4b50602`. Production browser/HTTP verification was **not completed** as part of this baseline; described functionality is source-code/release-index verified, not independently proven live in a browser. Revalidate before claiming production-observed.

## Sources and authority

- [Issue #62](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/62) defines the documentation-only scope.
- [Deployed-branch application](https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/65c7ef0e5f3ccd7aac1c6a90f32fc287a4b50602/web/app.js), [HTML shell](https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/65c7ef0e5f3ccd7aac1c6a90f32fc287a4b50602/web/index.html), [CSS](https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/65c7ef0e5f3ccd7aac1c6a90f32fc287a4b50602/web/styles.css) and [Release Index](https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/65c7ef0e5f3ccd7aac1c6a90f32fc287a4b50602/web/data/current-release.json) describe the released source tree.
- [Historical PR #35](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35) is CLOSED/UNMERGED, historical reference only. Never promote its mocks, wireframes or unpublished schemas into current requirements.
- Phase-specific Case Package evidence governs research status; interface rendering does not validate scientific fitness.

## Shell, navigation and case switching

- Static HTML/CSS/JS shell, hash routes `#home`, `#dashboard`, `#phase-1` through `#phase-6`. Header includes Home, CRISP-DM and GitHub; the phase navigator and case picker appear on phase views, not the Home/Dashboard shell.
- The shared case selection spans phases rather than creating six independent cases. Case changes clear phase-specific selection and transient CSV preview state.
- `current-release.json` lists exactly two **public navigation** cases: `ames-full-model-exploration` (Ames Housing — Full Model Exploration, default) and `used-car-price-optimized` (Used Car Price Prediction — Optimized Modeling). Both package statuses are **PARTIAL**. Historical mock/placeholder/INIT B are excluded from the active public selector; historical source/fixtures are not thereby deleted.
- Home communicates a research journey. Dashboard has `Verified Research` and `Custom Dataset` modes; the latter is browser-local CSV header/sample preview and validation UI, **not** model fitting, upload, or a live URL import. Dashboard is not an alternative truth source for model quality.

## CRISP-DM phase rendering

| Phase | Current source-backed presentation | Evidence boundary |
| --- | --- | --- |
| 1 — Business Understanding / 業務理解 | Case identity, research purpose, source and target | Citation/license state is case-specific; not blanket VERIFIED |
| 2 — Data Understanding / 資料理解 | Package-backed data summaries and analyses where available | Missing figures or findings remain unavailable; no mock substitution |
| 3 — Data Preparation / 資料準備 | Transformation stages and feature-type breakdown; CAR provides raw-column classification, exclusion reasons, filtered/processed/encoded lineage | Original columns ≠ retained source predictors ≠ encoded model features. CAR raw distribution depends on counts and source-SHA validation |
| 4 — Modeling / 模型建立 | Method Comparison and Explorer, method/config selectors, verified configuration metrics, selected features and feature-count vs CV RMSE | Comparisons use compatible recorded protocol/run; unknown, invalid or unexecuted points are never fabricated. X may represent mean encoded feature count across folds, not necessarily requested Top-K |
| 5 — Evaluation / 模型評估 | Per-configuration evaluation with `cv_fold_mean` and `pooled_oof`, diagnostics when package-bound | Fold-mean metrics and pooled-OOF metrics are distinct; neither is Holdout. Mismatched run, sample population, evidence digest or unavailable figure must not silently fall back to another result |
| 6 — Deployment / 部署階段 | Case-specific readiness/unavailability and local model reload smoke evidence where present; legacy/manual/CSV UI exists in code | **No deployed Prediction API**. Local reload smoke is not predictive fitness; a fixed mock estimate is not prediction. Ames historical exploration has no matched deployable final-fit for public inference |

The application loads package manifests and referenced artifacts with identity, permitted path, byte-length and SHA-256 checks. These are **artifact integrity checks**, not approval of data rights, model validity or statistical results. CAR CV performance did not beat the Dummy baseline; do not present it as successfully optimized prediction accuracy.

## State vocabulary and honest UX

- **CURRENT** = a source or documentation statement matches verified released code; not automatically a live-browser PASS.
- **STALE** = contradicted by a newer released source or decision.
- **PROPOSED** = future requirement without deployed evidence.
- **UNKNOWN** = not yet established by adequate evidence.
- **PARTIAL** = incomplete case/package; not synonymous with FAILED or VERIFIED.
- **PENDING** = awaiting approval/review (e.g., CAR Kaggle competition-specific rights or publication gate).
- **UNAVAILABLE** = no eligible public artifact/function for that view.
- **VERIFIED** = an explicitly scoped artifact or check passed; does not transfer to the whole case or model.
- **MOCK** = synthetic presentation only, never a research finding.
- **Smoke test** = restricted operability check; not scientific validation or live service proof.

Loading and failure panels are rendered for package errors; the loader refuses mismatched references instead of inventing values. User-facing copy must distinguish loading, verification failure, and legitimately unavailable research content.

## Responsive, language and accessibility

- `web/styles.css` contains media queries around 1000, 760, 700 and 680 px and respects `prefers-reduced-motion`. Browser visual/layout checks at desktop, tablet and mobile widths are **UNKNOWN**, not accepted as tested.
- HTML uses `lang="zh-Hant"`, a skip link, labelled case/phase navigation and status announcements. Actual copy is mixed Traditional Chinese / English. There is **no verified full bilingual locale switch**.
- Keep canonical English research terms with consistent Traditional Chinese UI labels: `Business Understanding／業務理解`, `Data Understanding／資料理解`, `Data Preparation／資料準備`, `Modeling／模型建立`, `Evaluation／模型評估`, `Deployment／部署`. `模型預測實驗室` is a Phase 6 UI label, **not** an indication that online inference exists.

## Future-only Prediction API UX (PROPOSED, NOT AUTHORIZED)

A future API must separately establish registered model identity and approved revision, validated required feature schema and units, single/batch CSV result lineage, input-size/format constraints, explicit errors, confidence/fitness disclosure, privacy and licensing review, abuse protection, and a deployment/rollback gate. Do not promise an endpoint, an ETA, a working Run button, production model binary or batch predictions. No code, API or model changes are authorized by Issue #62.

## Release and rights limitations

- PR #59 merged CAR into `main`; PR #60 published two-case release into `deploy`.
- PR #61 route allowlist was merged to `main` but **not to `deploy` at the evidence watermark**. Retired paths' production HTTP 404 behavior remains **UNKNOWN**; do not confuse selector exclusion with access-blocking.
- CAR Kaggle competition Rules redistribution rights remain **PENDING independent review** despite dataset attribution/license references. No private CSVs, vehicle rows, VIN, raw OOF or model binaries should be published through documentation.

See [reconciliation and terminology audit](REGSCOPE-SPEC-RECONCILIATION.md) for identified conflicts, source classifications and outstanding verification.
