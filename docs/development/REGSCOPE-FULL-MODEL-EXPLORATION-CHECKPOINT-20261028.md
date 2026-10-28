# RegScope Full Model Exploration Checkpoint

**Status:** `PARTIAL` — historical Development exploration is packaged and rendered locally; Phase 5 publication review and Phase 6 final-model inference remain unavailable.

## Case and provenance

- Case: `ames-full-model-exploration` — Ames Housing — Full Model Exploration.
- Immutable package revision: `ames-full-model-exploration-20261028-01`.
- Package SHA-256: `af4dbbf26c86ee81cd1af412077d808a7e29b409dce7bdb3437cc4b948fff863` (`package.json`, 35,859 bytes).
- Package bundle: 144 manifest-listed files, 4,667,757 bytes; `PARTIAL`; Phase 1 `UNAVAILABLE`, Phase 2/3/4 `VERIFIED`, Phase 5 `PLANNED` / publication `PENDING`, Phase 6 `UNAVAILABLE`.
- Phase 2/3 documents are reused from the distinct INIT B package, with source package/run identity retained in the execution manifest. Phase 4 is historical Run `development_20261026_01`, code HEAD `f30a9293f12dba221a36d62f35abd7cb45acbab5`, dataset digest `2525b2e9385f9873a45d124dfd7520851234fe0a30501a69b8e5e5536403017c`, fold digest `2d12b0a6294055b8aac95e6055fc9095c436c472666f56fd6f33828cc683dd30`. This is not represented as one execution run across Phases 1–6.
- The official training CSV SHA-256 was verified during the local audit as `1e18addf81e5e4d347cc17ee6075bbe4a42b7fa26b9e5b063e8f692a5f929d41`; no raw rows were added to the release.

## Historical research represented

The source summary covers 32 candidate configurations and 96 fold records: 30 completed configurations and 2 invalid Lasso candidates. All compared completed candidates use the same three-fold Development protocol and selected-features → primary OLS track. Mean-fold CV scores are model-selection evidence, not independent generalization estimates.

| Method | Best completed candidate | Mean-fold RMSE | Mean-fold MAE | Mean-fold R² |
|---|---|---:|---:|---:|
| All-feature OLS baseline | all encoded columns | 40,628.988626 | 22,167.835718 | 0.714185 |
| Pearson → OLS | K=20 | 36,918.472530 | 23,379.760554 | 0.768836 |
| Mutual Information → OLS | K=20 | 37,208.278236 | 23,510.513287 | 0.765345 |
| Lasso → OLS | α=100; α=0.1 and 1 invalid | 35,389.184561 | 19,395.048845 | 0.784159 |
| ElasticNet → OLS | α=100, l1_ratio=0.8 | 38,108.091256 | 21,747.552357 | 0.750248 |
| Ridge RFE → OLS | K=20 | 40,704.144200 | 26,744.644281 | 0.716501 |

The private OOF artifact was SHA/byte checked and independently recomputed in memory. All 90 fold metrics for the 30 completed configurations reconciled. For Lasso α=100, mean-fold metrics are RMSE 35,389.184561 / MAE 19,395.048845 / R² 0.784159; pooled OOF metrics are RMSE 35,936.820129 / MAE 19,394.931769 / R² 0.782514. These are separate aggregation definitions. No row-level OOF or sealed 292-row partition values are included or used.

Historical run-state evidence remains contradictory: early runner metadata records failure/interruption, while later finalization and aggregate files record completed artifacts; private fit accounting is inconsistent with the final summary. The package preserves the limitation; it does not silently rewrite history.

## Core and Web delivery

- Python adapter verifies summary/manifest/data/fold identities and candidate/fold coverage, reconciles historical OOF aggregates, and emits Phase 4/5 aggregate documents.
- Package producer emits an immutable aggregate-only package and validates all six Phase schemas, references, hashes, run/config bindings and private-row/model exclusions.
- Web release index now lists both the existing INIT B Reference Baseline and this separate exploration case. The existing package files and pointer digest are unchanged.
- Phase 4 Model Explorer has Method Comparison, Selected Features (fold-local), and Feature Count vs. CV RMSE views with method/config selectors and fold metrics. Invalid candidates remain identified and excluded from score plots.
- Phase 5 offers mean-fold and pooled OOF metrics for the selected configuration. It shows publication review pending and no residual chart because row-level public predictions are excluded.
- Phase 6 clearly reports that this historical exploration run has no matching final-fit model or prediction service.

## Validation evidence

- Python focused tests: `tests.core.test_model_exploration` — 5 PASS.
- Public bundle validator: PASS — 144 files, 32 configurations, 60 Phase 5 evaluations, no raw OOF or model binary.
- Browser smoke: `local/phase4-model-exploration-20261028/browser-smoke.json`; local Chromium exercised all six phases, Mock/INIT B/Exploration case switching, both Phase 2 figures, Model Explorer views/configuration selectors, selected-feature list, Phase 5 aggregation switching, Phase 6 unavailable state, desktop/mobile layout and Package-to-UI numeric consistency. Result: no console, request-failure or HTTP errors.
- `node --check web/app.js` and `git diff --check`: PASS at the latest local check.
- Production/Preview browser, CI/security scan, PR review, merge and deployment: `NOT RUN`.

## Remaining work and risks

1. The historical run-state/finalization/fit-accounting contradiction remains unresolved; the case is a historical source-reconciled exploration, not a fresh current-Core model run.
2. Phase 5 values are verified Development metrics but remain publication `PENDING`; no public row-level residuals/plots are included.
3. Phase 6 is unavailable because there is no per-configuration final refit model. No model was fit during this task.
4. Phase 2/3 are reused from INIT B and carry a separate source identity; do not label the entire case a single-run pipeline.
5. No PR, push, merge or Production deployment has been performed in this worktree yet.

## Reproduction

From this worktree, validate the committed/public release bundle with the project Python environment and run the static web server. For this local session, the browser smoke used the isolated browser installation under the sibling Core worktree and wrote its machine-readable result only under ignored `local/`.

**Worktree:** dedicated branch worktree; local absolute path is retained only in the ignored handoff.
**Branch:** `feat/regscope-full-model-exploration-20261028`
**Base:** `52dfc23719638f42b9651811d9c10eec0f91501a`
**Current code HEAD:** recorded by Git after local commit; not yet published.
