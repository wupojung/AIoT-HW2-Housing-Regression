# Issue #30 Step 5 Engineering Closeout

## Change inventory

The reviewed code delta is against `origin/main` at `f30a9293f12dba221a36d62f35abd7cb45acbab5`.

| File | Change and reason | Evidence / limitation |
|---|---|---|
| `python/src/housing_regression/modeling/p4b_runner.py` | Preserves the canonical null packet for numeric CSV `NA`; adds explicit opt-in Darwin `spawn` execution for exactly one production worker, validates its PID/PPID/start identity, and records worker outcome; receives the Queue result before joining to prevent large OOF payload deadlock; fixes a local import name collision during finalization. The existing Windows Job Object branch and default fail-closed behavior remain. | NA regression tests pass; one-worker Development and full resume completed in the local run; 96 checkpoints and finalization artifacts validate. Windows Job Object runtime was not re-tested on Windows. macOS `libproc` behavior was exercised by the authorized runs but has no isolated platform test yet. |
| `python/src/housing_regression/modeling/p4b_v2.py` | Applies the explicit one-task smoke allowlist before candidate admission, allowing the production runner to perform a bounded smoke task without changing candidate calculations. | Existing v2 contract tests; smoke execution evidence is local. |
| `tests/modeling/test_p4b_runner.py` | Adds canonical encoding compatibility checks for valid numeric values, numeric `NA`, existing missing forms, and rejected malformed values. | Focused tests run as part of the verification below. |
| `python/src/housing_regression/modeling/p4b_final_model.py` | Adds a serializable fitted Phase 3 preprocessing plus selected-feature Primary OLS prediction wrapper. It rejects target-bearing prediction rows and validates the selected feature/coefficient contract. | Development-only artifact round-trip passed; synthetic wrapper tests are included in this change. |
| `tests/modeling/test_p4b_final_model.py` | Exercises prediction feature order, fitted transform use, target exclusion, and coefficient validation using synthetic rows. | Focused tests run as part of the verification below. |
| `docs/reports/issue-30-step5-engineering-closeout.md` | Records public-safe aggregate findings, local evidence index, compatibility limits, and the minimal CLI assessment. | Contains no row-level data, predictions, credentials, local absolute paths, or model artifact. |

The run scripts, execution logs, 96 task checkpoints, OOF/private details, trained joblib artifact, Holdout predictions, and detailed Holdout manifest remain in ignored `local/` storage and are excluded from this change.

## Research result verification

The local manifests and result files agree on the following aggregate evidence:

| Item | Verified result |
|---|---:|
| Development / Holdout partition | 1,168 / 292 rows |
| Development task checkpoints | 96 |
| Task outcomes | 91 `COMPLETED`, 5 `INVALID`, 0 `FAILED` |
| Selected candidate | Lasso alpha 100, evaluated with Primary OLS |
| Final encoded features | 97 |
| Selected candidate Development 3-fold CV | RMSE 35,389.18; MAE 19,395.05; R² 0.784159 |
| One-time Holdout evaluation | RMSE 29,218.12; MAE 18,139.17; R² 0.888834 |

The Holdout metrics record reports 292 predictions, zero missing actual values and zero non-finite actual/prediction values. Its provenance marks `holdout_used_for_fit_or_selection` false. These are held-out evaluation results, not additional model selection evidence. The CV and Holdout figures are aggregate summaries; private row-level evidence is not published.

## Evidence index

The detailed local evidence remains under the ignored run directory `local/research/phase4-p4b/development_20261026_01/`:

- Development: `p4b_public_summary.json`, `p4b_private_details.json`, `p4b_manifest.json`, `p4b_oof_predictions.csv`, task checkpoint files, `run.log`, and resume/finalization logs.
- Final model: `final-model/p4b_final_model_metadata.json`, fitted model artifact, and training log.
- Holdout: `holdout-validation/holdout_metrics.json`, `holdout-validation/holdout_manifest.json`, predictions, and validation log.

These paths are evidence pointers for the authorized local checkout; only the aggregate values above are included in the review branch.

## Minimal CLI feasibility

### Current entry points

- `P4BRunner.run()` is a Python API for the fixed three-fold Development experiment, including checkpoint/resume behavior. It is not currently a stable end-user CLI.
- Phase 3 preprocessing is available as a Python API and is used by the runner and final model fit flow.
- Final model fitting and the one-time Holdout evaluation were invoked by run-specific local scripts. Those scripts are evidence and remain ignored; they are not reusable repository CLI commands.
- No project console-script registration or unified `argparse` entry point is present in the current Python source tree.

### Minimal proposal

Add one thin module entry point, for example `python -m housing_regression.p4b_cli`, that only validates arguments and calls existing APIs. Keep protocol values frozen in the existing code. Provide explicit subcommands for `preflight`, `development --run-id ... [--resume]`, `fit-final --run-id ...`, and `evaluate-holdout --run-id ...`. The Holdout subcommand should load an existing immutable model artifact, reject an existing evaluation output by default, call `predict` only, and write results to its separate private output directory.

Smallest likely code footprint: one CLI module, a narrow output/log helper only if current artifact utilities cannot cover it, and focused CLI contract tests. No model or preprocessing rewrite is needed. Expected effort is about 1–2 engineering days including tests and documentation, assuming current APIs remain stable.

### Operational safeguards

- Require a run ID, data path, and private output path as arguments or a validated config file; never edit Python source to change paths or run IDs.
- On resume, require exact agreement of run ID, Development data fingerprint, protocol/config hash, and checkpoint identity. Preserve valid checkpoints and append structured run events plus a durable failure record on error.
- Keep Holdout loading in a distinct explicit subcommand. Do not expose fit, feature selection, or tuning flags in that command. Refuse to overwrite an existing Holdout result unless a separately authorized new evaluation identity is used.
- Keep raw inputs, row predictions, model artifacts, detailed diagnostics, checkpoints, and logs under ignored private storage. Publish only a reviewed aggregate summary.

Main risks are argument-to-protocol drift, accidentally reusing Holdout for selection, and checkpoint/output collisions. Contract tests should cover those gates before adopting the CLI.

## Validation and compatibility status

Validation performed with the repository `.venv`:

- PASS: 4 focused NA/canonical fingerprint tests.
- PASS: 15 P4B v2 contract tests.
- PASS: 3 synthetic final-model wrapper tests.
- PASS: `compileall` for changed Python files; `git diff --check`.
- PASS: `tools/security_scan.py --all`.
- FAIL / platform-limited: `tests.modeling.test_p4b_runner` ran 20 tests: 13 errors and 1 failure. Windows Job Object checks cannot run on macOS; several older synthetic tests call protected production entry points, and the durable-failure test stops before writing its expected file. The actual authorized runs did produce durable run/failure records, but that does not replace a focused unit test for this path.
- FAIL / path-environment-limited: `tests.modeling.test_p4b_artifacts` ran 10 tests: 3 errors and 2 failures. The existing containment tests report `REPARSE_COMPONENT` for temporary/repository paths on this macOS filesystem, so positive path-containment and sanitized failure-write checks are not established by this test run.
- NOT RUN: full repository test suite and Windows runtime tests.

The authorized macOS Development and Holdout runs provide end-to-end runtime evidence on this host. Windows Job Object execution and cross-platform CI behavior remain unverified here. No full CI workflow is triggered automatically for a PR targeting `main`; the repository security workflow is configured for `deploy` pull requests or explicit manual dispatch.
