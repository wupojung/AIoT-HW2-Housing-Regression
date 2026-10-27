# RegScope UI Recovery Checkpoint — 2026-10-28

## Status

Local UI integration is implemented and browser-tested against the public INIT B Case Package. Independent QA of this code revision, GitHub checks, merge, and deployment are still pending. Production remains on its prior working release.

## Root cause and evidence

The previous Real-package route used a separate generic renderer. It did not reuse the established Mock renderer's analysis selector, staged transformation view, model summary cards, or evaluation figure selector. The Mock renderer remains unchanged and explicitly MOCK. This source-based diagnosis is W5P1's finding; W5P2's matrix review was bounded to public aggregate package evidence and did not inspect the renderer source.

The Phase 2 package has four analyses, two SVG figures, 81 field decisions, 81 missingness aggregates, 33 numeric summaries, and 26 nominal distinct-count summaries. Phase 3's 79 included predictor type totals (nominal 26, ordinal 20, discrete 14, continuous 19) match its raw-stage segments. Missingness totals 6,965 cells, including 8 for `MasVnrType`. Phase 3 does not provide public lineage from original types to the 248 encoded dimensions. Phase 4 contains one executed fixed configuration and three fold metrics. Phase 5 contains verified Development OOF metrics and three PNGs, while publication review remains PENDING. Phase 6 is locally smoke-tested only; remote inference is disabled.

See [REGSCOPE-MOCK-REAL-UI-GAP-20261028.md](REGSCOPE-MOCK-REAL-UI-GAP-20261028.md) for the phase-by-phase matrix and W5P2 evidence boundaries. The original UI screenshots were not available in the bounded repository search, so this is a component/data restoration, not pixel-parity validation.

## Changes

- Phase 1: displays traceable case, source label, and target context while keeping missing business evidence UNAVAILABLE.
- Phase 2: restores a four-option analysis selector, aggregate summary cards, missingness bars, accessible expandable tables, package SVGs, and limitation details. Long field lists stay collapsed by default.
- Phase 3: restores four transformation stages, uses verified raw-stage type counts, displays the actual 1,168/292 seed-42 split, and shows real treatments. The 248 encoded total is shown without an invented original-type breakdown.
- Phase 4: presents the fixed Lasso α=100 → OLS run, mean-fold metric cards and a three-fold view. Run/config/parameter details are expandable. No unexecuted model comparison is shown.
- Phase 5: adds mean-fold / pooled-OOF selection and one chart at a time. Development OOF scope and publication PENDING remain visible; chart status is not promoted.
- Phase 6: presents local model reload/inference evidence and states that the public site has no prediction API.
- Mock case renderer, values, and controls are unchanged.

No producer, schema, model, preprocessing, OOF, configuration, or package research values were changed.

## Data and recovery evidence

- Public Case Package: `ames-reference-init-a`, release `ames-initb-development-20261028-02`.
- Package SHA-256: `623c6cc968a65df02b3c6c676758b2fdca25031049cf5013980612cac8ac513f`.
- Run: `initb-development-e2e-20261028-02`.
- Configuration: `ames-lasso100-primary-ols-3fold-v1`.
- P0 archive: `local/worktree-archive/overnight-ui-recovery-20261028/` in the Core worktree. Its 156-file SHA manifest verified 156/156; its bundle contains 54 refs and passed `git bundle verify`. Source research data were copied into the archive; originals were not modified.
- Browser JSON and screenshots are ignored local evidence in `local/w5-browser-test/` in this UI worktree. The run uses the public package only and contains no private row data.

## Local test evidence

- Chromium, desktop and mobile: **PASS**. Case selector; all six phases; keyboard operation of the Phase 2 selector; Phase 2 aggregate summary/figures and selectors; Phase 3 stage totals/type segments/split; Phase 4 JSON-to-screen metric comparison and folds; Phase 5 JSON-to-screen OOF metric comparison, selector, and PNG; Phase 6 local-only state; Mock case preservation; no console errors, failed requests, or HTTP errors; no mobile horizontal overflow.
- Machine-readable result: `local/w5-browser-test/ui-recovery-smoke.json`.
- Screenshots: `local/w5-browser-test/phase2-real.png`, `phase3-real.png`, `phase4-real.png`, `phase5-real.png`.
- `node --check web/app.js`: PASS.
- `tests/test_web_foundation.py`: 5 passed using the existing Core-worktree Python 3.12 environment.
- `git diff --check`: PASS at the time of this checkpoint.
- Production browser test, GitHub required checks, and independent QA of this UI revision: NOT RUN / PENDING.

## Current worktree and release state

- Worktree: `AIoT-HW2-Housing-Regression-ui-recovery` (absolute local path omitted from public notes).
- Branch: `feat/regscope-ui-recovery-20261028`
- Base: `9f4444530a1c8a3d3c40ba8c51bf9e40e8e7ab1d`
- UI changes are committed locally and awaiting independent review. No Push, Merge, or Deploy occurred from this worktree.
- Existing production baseline remains available at `https://regscope-aiot.vercel.app/`.

## Remaining gates

1. Finish focused browser/accessibility checks and reconcile the W5P2 matrix wording corrections.
2. Commit and request W5P2 read-only review of the exact resulting SHA.
3. Run the required security/deploy checks for the final revision; publish through a reviewed PR only if all required gates pass.
4. After any approved deployment, re-run the same browser smoke against Production and record the exact deployed SHA and URL.

## Rollback

Keep the currently deployed production baseline `514477f4ce109ea3a113843de71297999fe8bf64`. If a later release fails browser validation, leave or restore the `deploy` branch to that verified baseline through the repository's normal reviewed deployment process. The P0 Git bundle and verified archive are retained locally; no worktree or research evidence was removed.
