# Full Model Exploration — Phase 4 Data Gap Audit

**Baseline:** `origin/main` `52dfc23719638f42b9651811d9c10eec0f91501a`
**Worktree:** `feat/regscope-full-model-exploration-20261028`
**Audit date:** 2026-10-28
**Status:** `PARTIAL` — usable historical Development-CV aggregates exist; historical run-state artifacts conflict.

## Evidence and source identity

The historical Development directory is `local/research/phase4-p4b/development_20261026_01`, Run ID `development_20261026_01`. Its manifest identifies code HEAD `f30a9293f12dba221a36d62f35abd7cb45acbab5`, Phase 3 contract v2.0, 1,168 Development rows, data digest `2525b2e9385f9873a45d124dfd7520851234fe0a30501a69b8e5e5536403017c`, and 3-fold digest `2d12b0a6294055b8aac95e6055fc9095c436c472666f56fd6f33828cc683dd30`. The published aggregate summary SHA-256 is `293333f133de0f31cf36d5c3db373e9fb60ae81abf1dbb6f9f13db84b5e84afc`; the manifest records the same digest. The summary contains 32 candidate records and 96 fold records.

The current INIT B package is `web/data/releases/ames-initb-development-20261028-02/cases/ames-reference-init-a/`, Run ID `initb-development-e2e-20261028-02`, code HEAD `ba80db58defb980d70664b1f661489f0ef7231d6`, and Config SHA-256 `a67b42afed991d7a69f5de7fdc56657ed9fce9495316bafe89deb2deee6be05f`. It has the same Development data and fold digests, but a distinct run, code HEAD, and configuration. Its Phase 4 is only fixed Lasso alpha=100 → primary OLS. Do not merge these identities into a fictitious single run.

## Historical candidate results

All values below are **historical mean-fold Development CV results** on the common 1,168-row, three-fold population, seed 42, primary selected-features → OLS track. They are model-selection scores, not independent generalization estimates. Only completed configurations are listed as usable; invalid candidates remain recorded as gaps.

| Method | Candidate coverage | Best completed candidate in that historical run | Mean-fold RMSE | Mean-fold MAE | Mean-fold R² |
|---|---:|---|---:|---:|---:|
| All-feature OLS baseline | 1/1 | all encoded columns | 40,628.988626 | 22,167.835718 | 0.714185 |
| Pearson → OLS | 5/5 | K=20 | 36,918.472530 | 23,379.760554 | 0.768836 |
| Mutual Information → OLS | 5/5 | K=20 | 37,208.278236 | 23,510.513287 | 0.765345 |
| Lasso selection → OLS | 2/4 | α=100; α=0.1 and 1 invalid | 35,389.184561 | 19,395.048845 | 0.784159 |
| ElasticNet selection → OLS | 12/12 | α=100, l1_ratio=0.8 | 38,108.091256 | 21,747.552357 | 0.750248 |
| Ridge RFE → OLS | 5/5 | K=20 | 40,704.144200 | 26,744.644281 | 0.716501 |

Protocol-compatible candidates share the same Development folds and primary OLS evaluation track. Lasso/ElasticNet native estimator metrics are diagnostic-only and must not be mixed into the primary comparison. The historical five-fold P4-A OLS result is not comparable to this three-fold population.

The fold-level aggregate summary includes selected encoded names and feature-lineage records for its 91 completed folds. The lineage entries in those records are marked `RESOLVED`; nevertheless, public feature displays must retain the encoded-feature unit and show fold-local selections, not claim a single final all-Development feature set for configurations that have no final-fit model.

## Gaps and contradictions

- The historical `run-metadata.json` and failure record report a failed execution/runner interruption. A later finalization record reports 96 task artifacts and 32 aggregates successfully assembled; the private aggregate record says `SUCCESS`. However, that private record's estimator/preprocessor fit accounting is zero. The Phase 4 closeout and comparison report likewise describe completed folds. Preserve this transition and report it; do not silently rewrite the first status or treat the initial failure as proof that all cached results are absent.
- The later aggregate is checksum-bound by the manifest and carries the matching data/fold digests. This supports use as **historical source-reported Development evidence**, but does not make it output of the current Python Core. Current INIT B's Lasso100 metrics are close but belong to another code/config/run identity and must remain a separate case.
- Two Lasso candidates are invalid. OLS and all five selection methods have aggregate results; however, the historical records do not provide a final all-Development fitted model for every selected configuration. No per-configuration Phase 5 or Phase 6 result is established by these aggregates.
- Phase 5 OOF, residuals, and Phase 6 artifacts from INIT B are bound to a different run/configuration. They cannot be attached to the historical comparison configurations. For the new exploration case, Phase 5/6 must remain explicitly unavailable/planned unless their own correctly bound evidence is present.
- The protocol's current document labels v2.0 a candidate; the current Owner instruction authorizes reuse of actual historical results. That does not retroactively make the old run a current-Core execution.
- W5P2's bounded report is `local/phase4-model-exploration-20261028/W5P2-P4-DATA-GAP-AUDIT.md` and concludes `PARTIAL` for the same run-state contradiction. Its audit did not inspect row-level predictions or the sealed partition.

## Model Explorer implementation implications

1. Method Comparison can use completed historical primary aggregates only, labelled as historical three-fold Development-CV selection scores.
2. Feature-count/CV-RMSE points can use the observed historical candidate configurations; no interpolation or synthetic points.
3. Selected Features can show the selected encoded names by configuration and fold, explicitly marked fold-local. Do not imply a final refit for methods/configs without a final-model artifact.
4. Display both invalid Lasso candidates as unavailable/error entries with their source status; omit them from metric plots.
5. Keep the INIT B Reference Baseline case unchanged. The exploration case may reuse its Phase 2/3 evidence only while retaining separate phase/run identifiers and matching data/fold digests.
6. Phase 5 can use aggregate Development OOF results only after each configuration is reconciled to its matching historical OOF source. Phase 6 remains `UNAVAILABLE`; the historical candidate run has no matching final-fit model artifacts. Existing INIT B model evidence is not transferable by similarity of metrics.

No model fitting, Holdout use, schema change, or edit to historical artifacts was performed for this audit.

## Implementation and independent OOF reconciliation update

W5P2 completed the bounded read-only audit at `local/phase4-model-exploration-20261028/W5P2-P4-DATA-GAP-AUDIT.md` with result `PARTIAL`. It confirmed the reusable historical Development candidate comparison while retaining the contradictory run-state/closeout evidence. Its scope did not open prediction rows or the sealed partition.

Separately, the primary agent verified the private historical Development OOF artifact by manifest SHA/byte identity and recomputed aggregate metrics per configuration/fold in memory. The verification reconciled all 90 fold results for the 30 completed configurations against the historical fold metrics; the two invalid Lasso configurations remain excluded. The OOF source remains local/private and no identifiers or row values were copied into the public package or this report. No Holdout rows were used.

For historical Lasso α=100 (`hist-lasso-23fac5e0453b`), mean-fold CV is RMSE 35,389.184561, MAE 19,395.048845, R² 0.784159; pooled OOF is RMSE 35,936.820129, MAE 19,394.931769, R² 0.782514, each on the 1,168-row Development population. These are different aggregations, not a discrepancy to resolve by changing the method.

An aggregate-only exploration Case Package now binds 32 configurations and 60 Phase 5 evaluations (mean-fold and pooled OOF for each completed configuration). Phase 5 metric values retain `VERIFIED` evidence while the index/publication review stays `PLANNED`/`PENDING`; row-level prediction assets and residual figures are not public. Phase 6 remains `UNAVAILABLE` because this historical run does not contain a corresponding final model. Phase 2/3 are reused from the distinct INIT B package with explicit source package/run provenance; this is not represented as a single-run Phase 1–6 computation.

The browser Model Explorer uses the manifest-bound method comparison and feature-count/RMSE points, and loads selected-feature and fold-metric files by hash. Its three views are available; invalid configurations remain visible with their recorded status and are excluded from score charts. The initial immutable release package `ames-full-model-exploration-20261028-01` is retained. After exact-HEAD QA found that Phase 5 evidence bindings were not enforced fail-closed, release `ames-full-model-exploration-20261028-02` was generated with the same research values and stricter Phase 5 builder/package validation; current package SHA-256 is `1c0d1aa109305cdbe15b7e6d76bc3f479832ed230be985a5589c40f16309902e`. Browser evidence is retained in ignored `local/phase4-model-exploration-20261028/browser-smoke.json`.
