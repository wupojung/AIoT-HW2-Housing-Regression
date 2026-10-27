# Phase 5 synthetic Evaluation CLI

This is an engineering-gate tool for producing a Phase 5 empty index or a clearly marked synthetic evaluation. It does not read Ames/Kaggle data, OOF/Holdout rows, fitted models, or Phase 4 run artifacts. It never publishes a package. All nonempty output uses `MOCK` metrics, leaves figures unavailable, and keeps INT-F/INT-S unavailable.

## Contract pin

`evaluation-index.schema.json` is copied byte-for-byte from PR #35 commit `8d2bc4405e08e1a1b982204984f681d90975956a`, path `docs/ui-ux/case-package/phase-05/evaluation-index.schema.json` (schema version `1.0.0`, JSON Schema Draft 2020-12; Git blob SHA-1 `c5ce014f9b96fded1df2f756f590c88d1401eac6`, file SHA-256 `a7f725d74e00d0c8e0ee24685722251181f45fec36e5145da0e2205aef89ad1f`). The wire output is `phases/phase-05/evaluations.json`. CV fold-mean and pooled OOF have distinct evaluation IDs and are only linked to each other; fold SD is per metric with `ddof: 1`. Schema validation uses `Draft202012Validator` and `FormatChecker`.

The isolated task environment resolved `jsonschema[format]==4.25.1` from the available package index. Create it under the authorized ignored task directory; do not install globally or modify root dependency files:

```sh
python3 -m venv local/research/phase5/engineering-gate-20261027-01/venv
local/research/phase5/engineering-gate-20261027-01/venv/bin/python -m pip install -r tools/phase5_evaluation/requirements.txt
```

## Invocation

```sh
local/research/phase5/engineering-gate-20261027-01/venv/bin/python tools/phase5_evaluation/cli.py export \
  --manifest /approved/input-root/manifest.json \
  --gate /approved/control/gate.json \
  --output-root /approved/private-staging-root
```

The output root must already exist and resolve exactly to `gate.output_root`. The tool creates only `phases/phase-05/evaluations.json`; it refuses to replace an existing file. A same-directory staged file is flushed and atomically hard-linked into place, so interrupted promotion leaves no partial destination. Filesystem hard-link support is required; unsupported filesystems fail closed.

`python3 tools/phase5_evaluation/cli.py --help` is available without the validator dependency. The `export` and `validate` operations require the isolated environment above. Exit codes are stable: `0` success, `2` argparse usage error, `3` invalid input/authorization/host/path/digest, `4` schema or identity/join failure, `5` output/dependency failure.

## Input manifests

Both control files are UTF-8 JSON. `manifest.json` must be directly inside `gate.input_root`. An authorized empty request contains no source and has this shape:

```json
{
  "manifest_version": 1,
  "mode": "empty",
  "case_id": "synthetic-empty-demo",
  "reason_code": "NO_APPROVED_EVALUATIONS"
}
```

A synthetic request identifies its target and canonical identities, and references a separate synthetic-only source file by relative path and SHA-256:

```json
{
  "manifest_version": 1,
  "mode": "synthetic",
  "case_id": "synthetic-housing-demo",
  "execution_run_id": "synthetic-run-01",
  "configuration_id": "synthetic-config-01",
  "prediction_origin": "synthetic_fold_specific_models",
  "protocol_version": "synthetic-protocol-v1",
  "target": {"column": "SyntheticTarget", "unit": "synthetic_units"},
  "source": {
    "path": "predictions.json",
    "sha256": "<64-character SHA-256 of predictions.json>",
    "kind": "synthetic_prediction_pairs"
  }
}
```

The referenced source must contain `{"fixture_kind":"synthetic","rows":[...]}`. Each row has a string `fold_id` and finite numeric `actual`/`predicted` values. At least two folds with at least two rows per fold are required. The program calculates each fold's metrics first, then the arithmetic fold mean and sample SD; pooled metrics are separately calculated over all rows. `residual = actual - predicted`. IDs and values remain synthetic and are not evidence about Ames.

The gate record is an explicit local authorization envelope. Its `authorized` field must be true, `mode` must be `synthetic_only`, and `allowed_operations` must include `export`. `input_root` must match the manifest directory; `input_allowlist` must contain exactly one matching source path and digest. `output_root` must be an existing directory and exactly match `--output-root`. `host.platform`, `host.host_id`, `host.python_version`, and `host.python_executable` must match the current runtime. The CLI rejects traversal, absolute paths, symlinks in the source path, host mismatch, missing authorization, and any mismatch between manifest digest, gate digest, and source bytes.
A synthetic gate record has this shape (replace the host values with the exact authorized runtime values):

```json
{
  "gate_id": "owner-approved-synthetic-gate",
  "authorized": true,
  "mode": "synthetic_only",
  "allowed_operations": ["export"],
  "input_root": "/private/approved/input-root",
  "input_allowlist": [
    {"path": "predictions.json", "sha256": "<64-character SHA-256>"}
  ],
  "output_root": "/private/approved/staging-root",
  "host": {
    "platform": "macos",
    "host_id": "<host name>",
    "python_version": "3.9",
    "python_executable": "/private/task-env/bin/python"
  }
}
```

For an empty request, `input_allowlist` is an empty array; the gate still authorizes the operation, output root, and runtime.

The CLI does not discover or verify the authenticity of a gate record, inspect Git state, or infer real-data permission. A trusted Owner/Coordinator must provide the gate. Never use a synthetic gate for a real source.

## Validation

```sh
local/research/phase5/engineering-gate-20261027-01/venv/bin/python tools/phase5_evaluation/cli.py validate \
  --index /private/staging-root/phases/phase-05/evaluations.json
```

Validation checks the pinned schema and evaluation ID/link invariants. It does not implement Case Package cross-file joins, asset-byte checks, rights review, release sealing, publication, or research QA. Phase 6 owns those gates. Linux/Windows portability is designed but was not runtime-tested for this handoff.
