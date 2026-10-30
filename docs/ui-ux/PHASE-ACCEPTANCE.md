# RegScope Phase 1–6 — UI acceptance inventory

**Basis:** current `deploy` two-case release and `web/app.js` documented as source-backed; live browser verification is still UNKNOWN. **This document does not authorize broader UI redesign or web runtime changes; the sole exception is the Owner-approved, narrow `web/app.js::footerNav()` Phase 1–6 `Schema ↗` href correction included in PR #66.** That source change does not establish browser/HTTP verification; targeted six-link smoke remains NOT RUN pending authorized merge and verification. UI must not invent values for a missing package item. The canonical contract is [Data Contracts](../contracts/CASE-PACKAGE-CONTRACT.md).

| ID | Page | Acceptance test against current published case | Evidence / failure state |
| --- | --- | --- | --- |
| UX-01 | Home | Navigates to Dashboard and CRISP-DM without dropping case identity | Browser navigation record; UNKNOWN until run |
| UX-02 | Case selector | Only Ames Full Exploration and Used Car appear in the public selector | Compare `web/data/current-release.json` |
| UX-03 | Case change | All selected phase/method/config/CSV state resets or rebinds to the new case; no stale cross-case metric | Browser interaction test |
| UX-04 | Dashboard | Verified Research vs Custom Dataset modes clearly distinguished | Local preview only; do not claim upload/training |
| UX-05 | Phase 1 | Research question/source/status follow case document | Ames Phase 1 UNAVAILABLE; CAR VERIFIED; correct empty state |
| UX-06 | Phase 2 | Missingness, target distribution and any other available analyses use package-bound refs | No substitution with mock images |
| UX-07 | Phase 3 | Counts distinguish raw source fields, retained fields and encoded features | Do not label encoded width as original columns |
| UX-08 | Phase 4 | Method comparison + Explorer show only eligible recorded configurations | No invented feature-K points |
| UX-09 | Phase 4 | CV RMSE labels, aggregation, encoded K and protocol/run are coherent | Compare only compatible experiment protocols |
| UX-10 | Phase 5 | Each evaluation retains configuration/run identity, population, `cv_fold_mean` or `pooled_oof` | Missing diagnostics visibly unavailable, not Holdout |
| UX-11 | Phase 6 | CRISP-DM stage remains Deployment／部署; approved page-heading target is 模型預測與結果 | Existing live UI old labels are a separate engineering task |
| UX-12 | Phase 6 | No API is advertised as live; smoke and fixed mock are clearly identified | Ames unavailable; CAR local reload smoke != online prediction |
| UX-13 | All | Empty, loading, hash/path error, mismatched digest, missing figure shown accurately | Fail closed; do not silently show another case's data |
| UX-14 | All | Keyboard focus, skip link, labels and accessible status text; reduced-motion preference | Browser a11y tests outstanding |
| UX-15 | All | Desktop/tablet/mobile layout and overflow tested | CSS breakpoints alone are not browser PASS |
| UX-16 | All | Mixed Chinese/English terminology follows canonical glossary | No claim of full i18n |

## Test status discipline

**SOURCE-VERIFIED** = backed by code/manifest. **BROWSER-VERIFIED** = observed in captured browser session. **PENDING REVIEW** = requires human or specialist judgment. **UNKNOWN** = not run. Do not conflate these with JSON's `VERIFIED`, `PARTIAL`, `UNAVAILABLE`, `PLANNED` or publication `PENDING`.

Expected screenshot evidence: case selector, six phase routes for both cases, Phase 4 method/config toggles, Phase 5 missing evaluation/diagnostics, Phase 6 unavailable, Custom Dataset local CSV, small viewport, keyboard-only traversal. Record browser version, viewport, case ID, release ID, asset digest and tested URL; no unsupported visual PASS.

## Cross-cutting UX contract

Every case-dependent widget must source data from the selected case, carry an eligible research status, and explain unavailable evidence. A case switch invalidates the previous case's asynchronous state. If digest or configuration identity is invalid, stop and show a reason rather than substitute mock content. No change to the released site is part of this documentation.

## Executable test matrix (source watermark)

Source branch: `deploy` at `65c7ef0e5f3ccd7aac1c6a90f32fc287a4b50602`; release-index ID `research-cases-20261029-01`. Actual Production/browser test evidence: **NOT RUN**. `main` and proposed PR #66 documentation are not a substitute for a browser observation.

| ID | Surface / reproducible procedure | Ames expected | CAR expected | Evidence |
| --- | --- | --- | --- | --- |
| UX-01 | Browser: visit `#home`, navigate Dashboard then Phase 1 | Hash routes work | Same | NOT RUN |
| UX-02 | Static: read `web/data/current-release.json`; Browser: selector | Exactly two listed cases | Exactly two listed cases | SOURCE: `current-release.json`; browser NOT RUN |
| UX-03 | Browser: choose config in Phase 4, switch case and return | Clear stale CAR state | Clear stale Ames state | NOT RUN |
| UX-04 | Browser: Dashboard switch Verified/Custom; local CSV header preview | Browser-only preview | Browser-only preview | NOT RUN |
| UX-05 | Static: `package.json.phases.phase1.status`; Browser empty panel | UNAVAILABLE | VERIFIED | SOURCE: published package manifests; browser NOT RUN |
| UX-06 | Static manifest + browser Phase 2 | VERIFIED phase (package) | VERIFIED phase (package) | SOURCE: published manifests; browser NOT RUN |
| UX-07 | Browser: Phase 3 feature-lineage tables | raw vs encoded separated | raw/filtered/encoded separated | NOT RUN |
| UX-08 | Browser: Phase 4 method/config selector | Only recorded results | Only recorded results | NOT RUN |
| UX-09 | Browser: inspect plotted K, CV RMSE and comparison scope | No fabricated points | No fabricated points, Dummy caveat | NOT RUN |
| UX-10 | Static: `phases.phase5.status`; browser diagnostics | PLANNED; no unsupported HOLDOUT label | PLANNED; no unsupported HOLDOUT label | SOURCE: manifests; browser NOT RUN |
| UX-11 | Static: UI source labels vs approved spec; browser Phase 6 | Current old label, target future new name | Current old label, target future new name | SOURCE: `web/app.js`; browser NOT RUN |
| UX-12 | Static: `phases.phase6.status`; browser action buttons | UNAVAILABLE/no online API | UNAVAILABLE/no API; local smoke is not online | SOURCE: manifests; browser NOT RUN |
| UX-13 | Browser: induce missing file/digest mismatch in isolated fixture (never production) | Distinguish UNAVAILABLE vs ERROR | Same | NOT RUN |
| UX-14 | Browser: keyboard-only focus, labels, skip link, reduced motion | Meets observed a11y checks only | Same | NOT RUN |
| UX-15 | Browser: widths 1920, 1024, 768, 375; inspect overflow | Visual report needed | Same | NOT RUN |
| UX-16 | Browser: compare visible Phase 1–6 labels to glossary | Mixed English/zh-Hant; no locale switch | Same | NOT RUN |

**Evidence capture contract:** for each browser row record case_id, release_id, URL/hash route, viewport/browser version, UTC timestamp, visible status and screenshot/console/network evidence. A failing fetch, integrity mismatch, or wrong case binding is **ERROR**, while a package-declared unprovided phase is **UNAVAILABLE/PLANNED**, not a fabricated substitute.

**Case switch sequence:** select Ames → Phase 4 method/config → switch CAR → inspect dependent widgets for CAR-only results → switch back → ensure previous asynchronous response cannot overwrite active case. This remains browser NOT RUN.

**Label governance:** `Deployment／部署` is the CRISP-DM stage. `模型預測與結果` is the Owner-approved **future UI page heading**. Existing shipped wording (`模型預測實驗室` / `房價預測實驗室`) is historically accurate source description, not a completed UI text change.
