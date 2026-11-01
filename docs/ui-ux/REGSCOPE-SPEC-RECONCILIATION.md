# RegScope — Specification Reconciliation & Terminology Audit

> Issue #62 · 2026-10-29 · Docs-only reconciliation. Basis: `main` `40a153d522b49aab4594470f0eb493b6eae26807`; `deploy` `65c7ef0e5f3ccd7aac1c6a90f32fc287a4b50602`. This is a source/release-index audit; **live browser and HTTP behavior remain UNKNOWN**.
>
> Classification applies to specific **claims**, not automatically to entire files: CURRENT / STALE / PROPOSED / UNKNOWN.

## Evidence and discrepancy matrix

| Scope | Existing source | Evidence at watermark | Class | Documentation-only remedy |
| --- | --- | --- | --- | --- |
| Home / Dashboard | `web/README.md` legacy prototype | `web/app.js` `renderHome`, `renderDashboard`, `renderDashboardVerified` | STALE for the old global prototype description; CURRENT for verified code | Describe actual static research/dashboard modes and local CSV limitations |
| Selector | `web/README.md` says MOCK, INIT B and placeholder selectable | `web/data/current-release.json` contains only Ames Full Exploration + CAR | STALE | Replace old public-selector list; retain legacy code as history |
| Phases 1–2 | `docs/crisp-dm/`, Case Packages | Per-case renderers and source-bound statuses | CURRENT / UNKNOWN per artifact | Avoid universal VERIFIED claim |
| Phase 3 | Old generic transformation wording | CAR `renderCarPhase3`: raw, filtered, processed, encoded; raw SHA/lineage checking | STALE where raw/encoded conflated | Define units and source lineage explicitly |
| Phase 4 | PR #35 wireframes and historical feature-K proposal | `renderExplorationPhase4` supports Comparison/Explorer and checked configuration refs | CURRENT code; PR #35 PROPOSED historical | Use observed code labels and conditional eligibility; no invented K |
| Phase 5 | `docs/contracts/schemas/` contracts | `renderExplorationPhase5` binds `cv_fold_mean`/`pooled_oof` and configuration evidence | CURRENT contract as retained; statuses PARTIAL/PENDING | Retain contracts, document distinct metrics and missing diagnostics |
| Phase 6 | PR #35 / legacy UI label `模型預測實驗室` and `web/README.md` | CAR local reload smoke; no online model API; Ames exploration unavailable; Owner approved heading `模型預測與結果` | STALE current UI wording; CURRENT unavailable state; PROPOSED future API | Update normative heading only; record required future UI-copy change without touching code |
| Retired package routing | PR #61 | `main` has allowlist; `deploy` SHA predates #61 | UNKNOWN in Production | Require release + HTTP checks before claiming 404 |
| Package / research license | Release Index, PR #59/#60 | Both packages PARTIAL; CAR competition-specific reuse rights PENDING; CAR CV worse than Dummy | CURRENT | Keep limitations explicit |
| Responsive / localization | `web/styles.css`, `web/index.html` | CSS media queries; `zh-Hant`, mixed language copy | CURRENT in code, UNKNOWN visually | Do not claim tested responsive or bilingual localization |
| Project overview | Root `README.md` | Claims models/results still solely future work | STALE | Update to published aggregate research with incomplete phases |
| Old design material | PR #35 CLOSED/UNMERGED | `docs/ui-ux/REGSCOPE-UX-SPEC.md` and related docs appear in unmerged PR, not current main | PROPOSED/HISTORICAL | Link historically; do not copy wholesale or declare normative |

## Terminology registry — canonical usage

| Avoid / ambiguous wording | Use in documents | Why |
| --- | --- | --- |
| “Ames Housing” for all cases | **RegScope** platform; **Ames Housing — Full Model Exploration** case; **Used Car Price Prediction — Optimized Modeling** case | Platform now contains two research domains |
| “Production verified” from `deploy` SHA alone | **Release-branch source verified**; **Production HTTP/browser UNKNOWN** | Commit and actual deployment need separate proof |
| “Case available” = “all phases finished” | **Case listed; package PARTIAL** | Public navigation is not scientific completion |
| “Mock retired / removed” | **Mock retired from active selector; historical fixtures retained** | Prevent accidental destructive cleanup claims |
| “Phase 3 raw features” for encoded features | **raw source columns**, **retained predictors**, **encoded features** | Different units and denominators |
| “Top-K” for every plotted X-axis | **observed fold-mean encoded feature count** when chart uses it; **requested K** only where recorded | Requested K ≠ observed model width |
| “CV RMSE” without aggregation | **mean-fold CV RMSE**, or **pooled OOF RMSE** | Different calculations/populations |
| “Evaluation = Holdout test” | **Development CV / OOF evaluation**, unless independent Holdout evidence explicitly exists | Prevent leakage/protocol confusion |
| “Verified method” = best prediction | **artifact-scoped VERIFIED**; compare against **Dummy baseline** explicitly | CAR model did not beat Dummy |
| “Optimized” = proven best | **Optimized Modeling** is the case's proper title, **not** performance certification | Preserve official name while stating poor fit |
| “Deployment complete” / “Prediction Lab live” | **Phase 6／模型預測與結果 (Model Prediction & Results)** as approved page heading; **online Prediction API NOT IMPLEMENTED** | Page naming is not evidence of inference service |
| `模型預測實驗室` as canonical Phase 6 heading | **模型預測與結果（Model Prediction & Results）**; CRISP-DM stage remains **Deployment／部署** | Owner-approved naming; currently deployed UI strings still use the old label and require separately authorized UI code changes |
| “CSV upload” | **browser-local CSV preview** for current UI | No server upload or batch prediction |
| “License verified” | **dataset attribution recorded; competition Rules review PENDING** | Different rights and redistribution conditions |
| “Accessible retired cases blocked” | **removed from selector**; **direct-route 404 UNKNOWN** | PR #61 not yet on deploy at watermark |
| “Bilingual site” | **zh-Hant document with mixed Chinese/English UI labels** | No verified language switch |
| “Dashboard analysis run” | **Dashboard Verified Research display** or **Custom Dataset preview** | Custom mode cannot run training |
| “Smoke PASS” | **local model reload smoke passed (scoped)** | Not proof of accuracy, API, security or production |

## Owner naming decision and implementation gap

- **Approved on 2026-10-29:** the Phase 6 **page title** is `模型預測與結果（Model Prediction & Results）`. The CRISP-DM Phase 6 *classification* remains `Deployment／部署`.
- The production-source strings `PHASES[6]` (`模型預測實驗室`) and legacy `renderPhase6()` page heading (`房價預測實驗室`) remain **STALE in UI source**. This docs-only PR does **not** modify them. Any future UI engineering change must coordinate the visible menu, heading, case-specific CAR/Ames page states, accessibility labels and tests, without suggesting API availability.
- Do not modify historical code identifiers or prior research records merely to satisfy a glossary change.

## File disposition and authority

- **NEW CURRENT normative**: `docs/ui-ux/REGSCOPE-PRODUCTION-UX-BASELINE.md` (source-verified behavior only).
- **NEW CURRENT audit**: this file, with explicit UNKNOWN/PROPOSED claims.
- **UPDATE STALE**: root `README.md`; `web/README.md`.
- **RETAIN**: canonical `docs/contracts/schemas/`, `docs/crisp-dm/` research documents, source package artifacts and fixtures. Their scientific/protocol authority is not redefined here.
- **HISTORICAL**: [PR #35](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35) including unmerged `REGSCOPE-UX-SPEC.md`, reconstruction index, contract drafts and mock samples. Historical citation only; no automatic migration.
- **Do not edit under #62**: `web/app.js`, `web/styles.css`, `vercel.json`, Case Packages, models, tests, workflows, CI and deployment configuration.

## Verification backlog and stop conditions

1. Independently confirm Production release SHA and two-case display/navigation with desktop/mobile browser evidence; status UNKNOWN until observed.
2. Confirm direct-route 404 after a separately authorized release of PR #61 to `deploy`; selector retirement alone does not satisfy route blocking.
3. Reconcile per-case Phase 1–6 availability and Phase 5 diagnostic figure states against complete package manifests; do not upgrade statuses by inference.
4. Audit visible UI terminology against this registry. Code/UI copy changes require a **different Owner-authorized engineering Issue/PR**.
5. Verify CAR competition-specific rights before broader redistribution; no raw data publication.
6. Phase 6 Prediction API is a future proposal, not an executable task here.

## Change log

- 2026-10-29: Owner-approved Phase 6 page title `模型預測與結果`; CRISP-DM Deployment name unchanged; live UI copy change recorded separately.
- 2026-10-29: Initial Issue #62 docs-only reconciliation of two-case release, UI behavior, historical design status and terminology. No frontend, scientific metric, package, routing, CI, merge or deployment modifications.
