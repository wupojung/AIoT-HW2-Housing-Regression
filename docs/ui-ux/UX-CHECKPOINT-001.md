# UX Checkpoint 001 — 2026-10-26

Status: Owner-confirmed concepts; P6-A documentation only.
Source Issue: https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/34
Primary spec: [REGSCOPE-UX-SPEC.md](REGSCOPE-UX-SPEC.md)

## Confirmed
1. CRISP-DM-first Home, not a dashboard mode per stage.
2. Desktop six stages numbered 1–6, horizontal one row, selected stage content below.
3. Study-case selector global to all six stages; documented cases only.
4. Separate secondary Dashboard for integrated plots and assignment bonuses (two problems, custom dataset).
5. Phase 4 teaches methods, experimental Top K and feature-count vs CV performance through progressive disclosure instead of showing everything.
6. Phase 6 links/downloads reviewed study outputs.
7. Every view gets ASCII Markdown wireframe; text defines interaction, data, empty states and review checks.

## Pending review
Actual research data contract; second case; exact experiment combinations; chart and interval evidence; responsive/accessibility; upload security; content copy and traceability.

## Explicit non-authorization
Draft documentation does not initiate implementation, CI run, worker/OS use, Phase 4 or 5 experiments, Merge, Preview or Production. Preserve #34 P6-A/P6-B/P6-C gates.

## Next
Independent reviewer checks legibility and consistency; PM/Nex reviews the design against research evidence; Owner must separately authorize engineering.


## Nex PARTIAL remediation delta — 2026-10-26

Source: https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35#issuecomment-6412376101

- **BLOCKER 1 addressed in document (pending Nex verification):** Phase 4 three-question selector matrix, method/K reset and failure states, observed-point-only encoded-K CV curve, fold/mean/SD/track and incomparable baseline policy.
- **BLOCKER 2 addressed in document (pending Nex verification):** Dashboard separates read-only Verified Research from experimental Custom Dataset; loading, parsing, validation, safe-URL constraints, Run disabled until authorized, running/cancel/stale invalidation behaviors.
- **BLOCKER 3 addressed in document (pending Nex verification):** minimal Case/Run/Feature-map/Metric/Visual/Download schema and LOADING/EMPTY/ERROR/PLANNED/MOCK/UNAVAILABLE/VERIFIED per-component display with visible watermark and evidence.
- **Supplement 1:** mobile horizontal-scroll proposal, focus/semantic/keyboard/charts alternative table/contrast/touch expectations (reviewed design proposal only).
- **Supplement 2:** OWNER CONFIRMED / DESIGN PROPOSAL / ENGINEERING TBD classification applied to decision matrix, preserving Owner's core design.

The above are *document changes*, not claims of completed empirical experiments, working uploads, functioning user interface or Nex PASS.

## Unresolved (explicit)
- **ENGINEERING TBD:** actual dataset 2, available methods and encoded K, run comparability and provenance inventory, live CSV processing/SSRF and size limits, secure cancellation support, real prediction/confidence interval methodology, breakpoints and implementation semantics.
- **P6-A independent review pending:** Nex must verify that proposed controls, states and schema are sufficiently precise. No acceptance assumed from our own edits.
- **Gate unchanged:** no P6-B, experimental Worker/OS/holdout, Merge or Deploy.

## Phase 2 EDA research narrative amendment — 2026-10-26 (v0.3)

Nex supplementary review: https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35#issuecomment-6413470789

- **Scope:** only Phase 2 Data Understanding teaching panel and evidence/storytelling contract. Original CRISP-DM-first Home, six-step row, independent Dashboard, Phase 4/CV contracts and P6-A PASS architecture preserved.
- **Empirical source:** https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/main/docs/crisp-dm/02-data-understanding.md ; source reports **empirical descriptive profiling + independent QA PASS**, PM Review and Epic Closeout PENDING.
- **Wireframe:** one selected insight/one principal figure, key verified findings, source/denominator and finding → interpretation+caveat → Phase 3/4 candidate hypothesis, with linked downstream evidence only if later verified.
- **Only four published QA-reviewed figure items:** FIG-01 profile; FIG-03 price distribution; FIG-02 missingness semantics; FIG-06 correlation/collinearity. Their PNG/SVG counterparts are public. The remaining 83 figure items (166 files) and raw row data remain private ignored `local/`, not UI/download assets.
- **Evidence labeling:** verified observation ≠ candidate hypothesis ≠ accepted downstream decision. No EDA finding alone licenses deleting outliers, forcing log1p, blindly imputing facility absences, or declaring Phase 4 selected features.
- **Design data contract:** additive EDA finding id/figure id, case/source/version, observation/unit/population/denominator, evidence URL, statement kind, linked phase/decision status, limitation and UI availability. Shared seven UI statuses and accessible alternative table apply.
- **Pending:** availability of reviewed downstream Phase 3/4 decision links, responsive breakpoint and precise visual implementation (ENGINEERING TBD). Not a fresh Owner decision; do not invent a downstream adoption claim.
- **Gate:** docs-only amendment for Nex re-review; P6-B, Runner, raw dataset access, Merge, Preview and Production remain NOT AUTHORIZED.


## Owner design amendment — Phase 6 inference lab / Desktop-first

**OWNER CONFIRMED (2026-10-26):**
- Phase 6 primary interaction = real housing-price prediction by selecting a **previously trained and approved** model, entering housing attributes, and invoking a model inference API. Research downloads are secondary.
- Design priority = **PC Desktop, 1920×1080 Full HD reference**; phone/mobile support deferred. Keyboard access/readable desktop content retained.
- First selection dimension = studied dataset/case. Second = **recorded feature-selection run/method+configuration** (e.g. exact measured K or alpha), not every theoretical method×K permutation.
- Phases 2–5 show precomputed research findings/evaluation only; Phase 6 can perform *new inference*, **not retraining**, contingent on deployment authorization.

**DESIGN PROPOSAL:** versioned public-safe JSON catalog with stable `case_id`, `run_id`, `model_id`, experiment config/track/protocol/status and model input schemas. Dependent selectors; case/model switch invalidates prior results. Multiple CV experiment results can share one manifest but do not imply each has a deployable inference artifact.

**ENGINEERING TBD / evidence dependencies:** exact registered model artifacts, training-time preprocessing and raw input schema, serialization/loading strategy, runtime/API, prediction interval method, inference tests/security, deployment gate. Package B contains 97-encoded-feature final model *metadata*, not a directly loadable model. Do not expose active Predict until these are validated.

**Gate:** design documents only in PR #35; no P6-B engineering, Merge or Deploy approval implied.

## Nex v0.4 delta checkpoint — generic model prediction (2026-10-26)

Reviewed request: https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35#issuecomment-6417360873

**P0-1:** General case-driven Model Prediction Lab; "房價預測實驗室" stays Ames label. Used Car is **PLANNED** candidate, not a verified case.
**P0-2:** Research Run, approved deployable Model and new Prediction separated. Every selector change invalidates old inputs and outputs; no derived method×K models.
**P0-3:** Raw input schema required/optional, provenance/type/unit/range/category/dependency/imputer; structural facility absence vs genuinely unknown value vs omitted required fields distinguished and unsafe defaults forbidden.
**P1-1:** Dashboard custom CSV/URL **Train/Evaluate (future authorized)** distinct from Phase 6 single-sample **Predict with approved existing model**.
**P1-2:** Ames reviewed EDA/Development research ≠ verified deployable API; Used Car remains planned and cannot appear as having experiments.
**P1-3:** Minimal conceptual API request/response plus explicit error codes; no real prediction or fabricated uncertainty interval.
**P1-4:** >13 original candidate predictors (>=14), no formal <40 cap; audit CSV original fields, eligible raw fields, encoded and selected fields separately.

**Authority:** OWNER CONFIRMED remains Desktop 1920×1080, CRISP-DM-first six steps, case switching, separate Dashboard, Phase 4 progressive disclosure, Phase 6 inference concept. Added contract rules are DESIGN PROPOSAL. Used Car research, deployable registry/pipeline/API, custom training limits and actual evaluation all ENGINEERING TBD.

**Review status:** amended for Nex independent re-review, not self-certified PASS. Only the two UI/UX Markdown files changed on PR #35; P6-B, Runner, Holdout, Merge and Deploy remain NOT AUTHORIZED.
