# RegScope Phase 1–6 — UI acceptance inventory

**Basis:** current `deploy` two-case release and `web/app.js` documented as source-backed; live browser verification is still UNKNOWN. **No redesign or web changes are authorized here.** UI must not invent values for a missing package item. The canonical contract is [Data Contracts](../design/data-contracts/CASE-PACKAGE-CONTRACT.md).

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
