# Phase 6 CAR Local Inference

This is a local-only integration for one verified CAR Run 03 Final Fit. It is
not a public API, a pricing recommendation, or evidence that the model has
acceptable predictive quality. The existing CAR research reports negative
Development R² and performance below its Dummy baseline.

## Scope and artifact handling

- Case: `used-car-price-optimized`
- Run / configuration: `used-car-e2e-20261028-03` /
  `car-mutual-information-8b59f9573a65`
- Runtime contract: 15 raw inputs, in the fitted transformer order.
- The local API pins the verified model and schema SHA-256 values in the
  adapter. It reads the model from the private Run 03 root and verifies the
  Run manifest before deserializing the artifact.
- JSON Schema validation resolves
  `docs/contracts/schemas/prediction-input-schema-v0.1.schema.json` first. As
  of PR #66's current diff, that PR relocates Phase 1–6 schemas only and
  explicitly leaves this separate Prediction Input Schema at its existing
  `docs/design/data-contracts/schemas/` path. A fail-closed fallback supports
  that current layout without copying the schema. Remove the fallback only
  after a separately reviewed migration moves this schema and updates all
  consumers to the canonical path.
- Keep the model, generated input schema, input values, and predictions in
  ignored local storage. Do not add them to Git, a public package, or a hosted
  release. The API returns schema metadata only to the loopback UI origin.
- No training, Holdout reads, OOF reads, CSV upload, batch prediction, or
  remote serving is performed.

## Start the local API

Use the project Python 3.12 environment and provide the trusted archived Run
03 root and locally generated `prediction-input-schema.json` path:

```sh
PYTHONPATH=python/src .venv/bin/python tools/modeling/serve_local_car_prediction.py \
  --run-root <trusted-archived-run-03-root> \
  --schema <ignored-local-prediction-input-schema.json> \
  --port 8767
```

The server binds to `127.0.0.1` only and allows browser requests only from
`http://127.0.0.1:8766`. It exits if the model digest, schema digest, Run,
configuration, source identity, or raw feature order fails verification.
Stop it with `Ctrl-C` in the serving terminal.

## Use the local UI

With the existing static preview serving this worktree's `web/` directory on
port 8766, open:

```text
http://127.0.0.1:8766/?car-phase6-prototype=1&car-local-inference=1#phase-6
```

The second query flag is accepted only on that exact loopback origin. The UI
loads the schema from the local API, displays blank contract-driven fields,
and sends one complete record to `/api/predict`. The optional synthetic input
button creates test values in the browser; these are not real vehicle records.
The ordinary prototype and all hosted UI routes keep prediction unavailable.

The schema reports no supported JSON `null` marker for the Run 03 imputers, so
the API rejects `null`. Unknown categories follow the fitted encoder's
`handle_unknown` metadata; this is not a public API allowlist. Numeric bounds
and a target unit are not established by this integration and are not
invented.
