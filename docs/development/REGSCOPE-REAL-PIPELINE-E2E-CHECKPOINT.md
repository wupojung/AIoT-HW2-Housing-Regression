# RegScope Real Pipeline E2E Checkpoint

**State:** local Development engineering run completed; package is `PARTIAL` and not publication approved.
**Run:** `initb-development-e2e-20261028-02` · **Configuration:** `ames-lasso100-primary-ols-3fold-v1`
**Data:** authorized Ames `train.csv`; no source data or row-level predictions are included in this checkpoint.

## Pipeline result

- INIT B preserved as a separate Reference Baseline configuration; INIT A was not changed.
- Phase 1 remains `UNAVAILABLE` because approved business/source-rights evidence is incomplete.
- Phase 2 ran on the original, unfilled Development CSV. It reports 1,460 records and 6,965 missing cells; `MasVnrType` has 8 missing entries and the literal `None` category remains distinct from missing values. Two package-bound aggregate SVGs were generated.
- Phase 3 used the fixed 80/20, seed-42 split and train-only fitting. The development training partition has 1,168 records and the encoded design has 248 features. No validation records were opened or used for tuning.
- Phase 4 ran the fixed three-fold Lasso (`alpha=100`) selection followed by primary OLS. Candidate search was disabled. Development OOF covers the 1,168 training records across folds of 390/389/389; its artifact is bound to this run, configuration, source digest and fold metadata.
- Phase 5 recalculated fold-mean and pooled OOF metrics from this run’s saved predictions and created three draft PNG figures. The evaluation document remains `PLANNED` pending independent research review/publication approval; the calculations themselves are present and schema-valid.
- Phase 6 fitted the fixed Development model, persisted it locally, reloaded it, and passed a local inference smoke. The model is private, remote inference/deployment is disabled, and the smoke prediction is not a research result.

## Verification

- Private Case Package validator: `PASS` (six phase documents, 24 manifest-listed files, 1,168 OOF records); package status remains `PARTIAL` because Phase 1 and publication approval are unresolved.
- Browser smoke on loopback: `PASS`. Case selector loaded the Reference Baseline. Phase 2 showed package aggregates and both SVGs loaded; Phase 3 showed 248 features; Phase 4 showed this run’s CV values; Phase 5 showed pooled OOF values and all three PNGs; Phase 6 showed model reload/local inference PASS. No browser console errors or failed requests were observed.
- Focused tests: `PASS`, 22 tests across Reference Baseline, Phase 5, Phase 1/2, INIT, and synthetic package E2E. JavaScript syntax and `git diff --check`: `PASS`.
- W5P2’s independent review of the newly produced OOF/package artifacts is still pending. An earlier review snapshot predates this run’s package and was blocked for missing inputs; it is not evidence against this run.

## Limits and next review

This is a bounded Development reproduction, not independent generalization testing. No hyperparameter search, validation-row evaluation, Holdout use, deployment, public release, or Push was performed. Phase 5’s OOF review must confirm its independently recomputed values and provenance before the evaluation is treated as research-approved. Phase 2 historical classification/correlation/PNG reconciliation items remain subject to the previously recorded reconciliation checkpoint.

The local package, source-linked files, OOF predictions, model, and detailed integrity evidence stay under ignored `local/`. The Web consumer reads the package only from loopback; no private package files were copied into `web/`.
