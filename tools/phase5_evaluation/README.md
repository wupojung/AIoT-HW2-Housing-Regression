# Phase 5 Evaluation CLI

This gate-bound tool exports an empty index, a clearly marked synthetic evaluation, or an explicitly authorized Phase 4 Development OOF evaluation. It does not read Holdout/competition-test rows or fitted models, retrain Phase 4, or publish a package. INT-F and INT-S remain unavailable pending their separate evidence and review.

## Contract and isolated environment

`evaluation-index.schema.json` is copied byte-for-byte from PR #35 commit `8d2bc4405e08e1a1b982204984f681d90975956a`, path `docs/ui-ux/case-package/phase-05/evaluation-index.schema.json` (schema version `1.0.0`, JSON Schema Draft 2020-12; Git blob SHA-1 `c5ce014f9b96fded1df2f756f590c88d1401eac6`, file SHA-256 `a7f725d74e00d0c8e0ee24685722251181f45fec36e5145da0e2205aef89ad1f`). The wire output is `phases/phase-05/evaluations.json`. CV fold-mean and pooled OOF have distinct linked IDs; fold SD uses `ddof: 1`.

Install dependencies only in an authorized isolated environment. Do not install globally or modify root dependency files:

```sh
python3 -m venv local/research/phase5/engineering-gate-20261027-01/venv
local/research/phase5/engineering-gate-20261027-01/venv/bin/python -m pip install -r tools/phase5_evaluation/requirements.txt
```

The output root must already exist and resolve exactly to `gate.output_root`. The exporter refuses to replace the index or figure assets. Index files and PNG assets are staged then atomically hard-linked into place; filesystems without hard-link support fail closed. `--help` works without dependencies; `export` and `validate` require the isolated environment. Exit codes: `0` success, `2` usage error, `3` invalid input/authorization/host/path/digest, `4` schema or identity/join failure, `5` output/dependency failure.

## Synthetic mode

The synthetic manifest and gate contract remains available for unit fixtures. A synthetic manifest has `manifest_version: 1`, `mode: synthetic`, `case_id`, run/configuration identity, prediction origin, protocol version, target, and a relative `source` path/SHA-256 with kind `synthetic_prediction_pairs`. The source JSON is `{"fixture_kind":"synthetic","rows":[...]}`; each row has `fold_id`, finite `actual`, and finite `predicted` values.

The gate must set `authorized: true`, `mode: synthetic_only`, `allowed_operations: [export]`, `gate_id`, `input_root`, `input_allowlist`, `output_root`, and exact runtime `host` values (`platform`, `host_id`, `python_version`, `python_executable`). The input root must equal the manifest directory and the allowlist must contain the source exactly once with its digest. The tool rejects path traversal, symlinks, host mismatch and digest mismatch. Synthetic results are marked `MOCK` and are not empirical evidence.

## Phase 4 Development OOF adapter

For the single Owner-authorized Issue #37 Development run, `--manifest` is the original `p4b_manifest.json`. This adapter accepts only these handoff-pinned digests:

- Manifest: `3d1b60ae9cb43a34eff9646b56950531217dc791fcafe4d1ba3cdfeb151f942e`
- Public summary: `293333f133de0f31cf36d5c3db373e9fb60ae81abf1dbb6f9f13db84b5e84afc`
- OOF CSV: `02a8b0cd958713125db52d963b228d3d3a47e2e001569816cd54bad9c12d1988`

The trusted Coordinator gate uses `mode: phase4_oof`, `authorized: true`, `allowed_operations: [export]`, `gate_id`, `case_id`, `run_id`, `protocol_version`, `manifest_sha256`, `input_root`, `input_allowlist`, `output_root`, exact runtime `host` values, `target: {column, unit}`, and a nonempty `configurations` array. The input root is the approved Development artifact directory. The allowlist contains exactly `p4b_public_summary.json` and `p4b_oof_predictions.csv` with their pinned digests. The CLI opens only these two manifest-listed files; it does not inspect other inventory entries.

Each selected configuration has `configuration_id`, `method`, `track`, and the exact `candidate` object from the summary. Its canonical ID is `cfg-` plus the full 64-character Phase 4 `config_hash`. `track` is `primary` for selected-to-OLS groups or `baseline` for the all-features OLS baseline. Every selected config must be completed, primary-valid, and have complete valid-fold coverage in the summary; winner eligibility is not required. It must cover every expected fold, contain exactly the declared Development row count, and have finite predictions. Native secondary, incomplete/invalid, and unselected groups are not exported.

The CSV header must exactly be `Id,fold,task_id,method,track,actual,predicted`. Every exported row's task/fold/method/track joins to one public-summary task. Output has distinct fold-mean and pooled OOF evaluations with reciprocal IDs; pooled metrics are calculated across the OOF rows, and fold sample SD uses `ddof: 1`. Prediction origins are `fold_specific_selected_to_ols` and `fold_specific_all_features_ols`. Only pooled OOF evaluations receive FIG-P5-02/01/03 PNG diagnostics. Residuals are `actual - predicted`. The FIG-P5-03 `histogram.bin_edges_ref` points to a case-root JSON aggregate containing the exact bin edges/counts and `n`; it contains no row-level records. PNG and histogram assets are written under the case-root `assets/` directory. The index contains metrics and evidence references, not raw rows or predictions; image assets are diagnostics with publication review pending. The top-level index has a UTC `generated_at`, remains `PLANNED` with `release_id: null` until publication review, even though individual OOF metrics are marked `VERIFIED`. Asset generation stages the full set before promotion and rolls back promoted files if any promotion fails. No final fit or Holdout result is inferred.

Never open `holdout-validation/`, competition test, unmanifested diagnostic CSVs, or private Phase 4 details. The CLI does not establish gate authenticity, inspect Git state, or infer permission; only the trusted Owner/Coordinator provides the gate.

Example (the Coordinator supplies the trusted gate and private output directory):

```sh
local/research/phase5/engineering-gate-20261027-01/venv/bin/python tools/phase5_evaluation/cli.py export \
  --manifest /approved/development-root/p4b_manifest.json \
  --gate /private/owner-gate.json \
  --output-root /private/phase5-staging
```

Validate the resulting index with:

```sh
local/research/phase5/engineering-gate-20261027-01/venv/bin/python tools/phase5_evaluation/cli.py validate \
  --index /private/phase5-staging/phases/phase-05/evaluations.json
```
