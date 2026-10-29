# Prediction Input Schema v0.1

Canonical packaged filename: **`prediction-input-schema.json`**, located at the model's Case Package root and referenced through the existing Phase 6 `input_schema_ref`. This v0.1 deliverable is a standalone exporter: it writes to the caller-supplied `--output` path and does not automatically invoke Phase 4 Final Fit, modify a Case Package, or bind `input_schema_ref`. Those integrations are later work; this schema does not replace the Phase 6 model-readiness contract.

## Purpose and v0.1 scope

The artifact describes raw input keys accepted by a specific fitted preprocessing/model bundle. The count and field order come from that bundle. Raw fields, encoded features, and selected encoded features are separate properties. v0.1's exporter adapter supports the CAR Final Fit bundle shape (`transformer`, `scaler`, `mask`, `estimator`, `features`, and run identity); the document format itself does not contain a CAR field-count assumption.

The output records model SHA, case/model identity, run/config/source evidence, required key presence, nullable values only where a fitted imputer's literal `None` sentinel proves support, blank behavior, encoder category values, category grouping and raw-to-encoded lineage. A fitted imputer using `NaN` does not by itself prove that a JSON `null` will be normalized correctly, so `nullable` stays unknown in that case. Units and numeric bounds remain `null` unless explicit evidence is available. `control_type` is a UI suggestion derived from the fitted data type/cardinality, not a model constraint.

Encoder options are **training vocabulary**, not an approved API allowlist. Unknown-category handling is recorded from the fitted encoder. Before publishing a generated artifact, review category values for scraped text or other source-sensitive content. The exporter never writes model weights, source rows, OOF, Holdout or estimator parameters into the schema. It does not run `predict`.

## Export from a trusted bundle

Obtain the model digest from a trusted Run Manifest or other independent record. Do not accept model uploads or deserialize an artifact whose expected digest is not independently verified. The tool opens a regular file, copies and hashes the same bytes into a private temporary spool, and passes only that verified stream to `joblib.load`, avoiding a path-replacement race between hashing and deserialization.

```sh
PYTHONPATH=python/src python tools/modeling/export_prediction_input_schema.py \
  --model-path /trusted/private/final-model.joblib \
  --expected-sha256 <trusted-64-character-sha256> \
  --run-manifest /trusted/private/run-manifest.json \
  --case-id <case-id> \
  --model-id <verified-model-id> \
  --output /private/output/prediction-input-schema.json
```

The output must not already exist. For a real model, write first to an ignored, private path; inspect and validate the result before any package inclusion. Missing or unsupported fitted metadata fails with a concise error instead of guessing. A run manifest is cross-checked against model SHA, Run ID and source SHA. Without a manifest, export status is `PARTIAL`.

## Consumer and validation rules

- Require every key marked `required`; this is distinct from a nullable value.
- Treat `nullable` and `blank_policy` independently. Do not turn an omitted key, JSON `null`, and `""` into the same value.
- Enforce request validation on the server as well as in the UI.
- Do not interpret training categories as service-approved options. The service needs a separately reviewed policy for unknown/infrequent categories.
- Compare model digest, Run/Configuration identity and schema reference before inference. Fail closed when evidence is missing or stale.
- The canonical input values and field identities remain raw source/English values in v0.1. Localization is out of scope.

The structural contract is `docs/design/data-contracts/schemas/prediction-input-schema-v0.1.schema.json`; `contracts.validate_document` validates generated output. The `input_feature_count == len(input_features)` invariant is checked by exporter tests because standard JSON Schema cannot express this equality portably.

## CAR Final Fit metadata cross-check

A digest-verified, local-only metadata export for `used-car-price-optimized` found **15 runtime raw inputs**, **70 transformed features**, **10 selected encoded features**, sourced from **8 distinct raw fields**. The exporter did not call `predict`, inspect CSV/OOF/Holdout rows, or include the model artifact or generated CAR category values in this repository. Encoder vocabulary is recorded as training metadata only; API allowlisting and publication review remain unresolved. This confirms the model-input shape, not serving authorization or predictive quality.

## Synthetic example

`docs/design/data-contracts/examples/prediction-input-schema.example.json` is a MOCK fixture with five synthetic raw input keys. It contains no CAR categories or real model digest.
