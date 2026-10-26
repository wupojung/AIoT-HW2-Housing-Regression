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
