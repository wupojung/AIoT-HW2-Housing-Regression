# Phase 5 Evaluation CLI

This CLI supports authorized empty or synthetic exports and evaluation from the normalized, private OOF handoff. It does not read P4-B manifests, summaries, or source CSVs. For the separate Phase 4 adapter, see [tools/research_export/README.md](../research_export/README.md).

## Isolated environment

Install dependencies only in the authorized tool-local environment; do not install globally or modify root dependency files:

```sh
python3 -m venv local/research/phase5/engineering-gate-20261027-01/venv
local/research/phase5/engineering-gate-20261027-01/venv/bin/python -m pip install -r tools/phase5_evaluation/requirements.txt
```

## Empty and synthetic export

The `export` command accepts an empty manifest or a synthetic manifest whose allowlisted source contains only marked synthetic prediction pairs. The gate must authorize `synthetic_only`, bind the manifest's input root, source digest and output root, and identify the current runtime host. Empty exports have no source file. Synthetic results are marked `MOCK`, not empirical evidence.

```sh
local/research/phase5/engineering-gate-20261027-01/venv/bin/python tools/phase5_evaluation/cli.py export \
  --manifest /private/synthetic-input/manifest.json \
  --gate /private/synthetic-input/gate.json \
  --output-root /private/phase5-staging
```

`validate --index <path>` validates a Phase 5 index against the pinned Draft 2020-12 schema and its internal evaluation links.

## Normalized handoff evaluation

The Phase 4 adapter may write a versioned `handoff.json` and normalized `oof.csv` under a separate private root. The handoff has exact columns `row_id,configuration_id,fold_index,task_id,actual,predicted`; it binds source manifest/summary/OOF digests, case/run/protocol/target identity, selected canonical configuration IDs, expected folds, and row counts. Keep this directory outside the Case Package.

`evaluate-handoff` consumes that handoff root and a Phase 4 Case Package root containing `package.json`, `phases/phase-04/modeling.json`, and the empty `phases/phase-05/evaluations.json` slot. Its gate must authorize `phase5_handoff_evaluation`, bind exactly `handoff.json` and `oof.csv` by SHA-256, match the handoff and package case/run/protocol identities, and name the exact input and output roots. The CLI validates package file hashes, the pinned Phase 4 schema, configuration/task/fold joins and counts before computing Development OOF metrics. It writes a PLANNED, pending-review evaluation and assets; it does not approve publication or permit Holdout evaluation.

Phase 5 retains `FIG-P5-01/02/03` as stable per-Evaluation tokens. In the package-level figure manifest, each asset is uniquely joined by `(phase, source_evaluation_id, figure_id)` and its source configuration, PNG path and SHA-256 must match that owning Evaluation. Distinct evaluations therefore keep distinct physical PNG paths even when they use the same figure token.

```sh
local/research/phase5/engineering-gate-20261027-01/venv/bin/python tools/phase5_evaluation/cli.py evaluate-handoff \
  --handoff-root /private/phase5-gate/inputs \
  --package-root /private/phase5-gate/case-package \
  --gate /private/phase5-gate/evaluation-gate.json
```
