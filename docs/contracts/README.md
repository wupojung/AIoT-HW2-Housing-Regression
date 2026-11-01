# RegScope — Contracts Registry

**Authoritative contract root:** `docs/contracts/`. API and CLI interfaces must be specified here when approved; a JSON Schema describes JSON shape, not deployment procedure. **Phase schema directory:** [schemas/](schemas/README.md). One canonical location for Phase 1–6 machine-readable contracts. The Phase 5 Evaluation Index schema lives at [schemas/phase-05.schema.json](schemas/phase-05.schema.json).

## Prediction Input Schema v0.1 (separate from Phase 1–6)

[PR #67](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/67) (merged to `main`, merge commit `905c622aad4a9f8581b9c5b904200aa373e96c25`) introduced the [Prediction Input Schema v0.1](../design/data-contracts/schemas/prediction-input-schema-v0.1.schema.json) and its standalone exporter under [Issue #34](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/34). This is a **per-model prediction-input contract**, not an additional Phase-level schema and not part of the Phase 1–6 relocation. Its existing path remains authoritative for that delivered PR #67 artifact until a separately approved migration.

The exporter is standalone: Phase 4 Final Fit does **not** automatically invoke it, published Case Packages do **not** automatically include `prediction-input-schema.json`, and Phase 6 `input_schema_ref` is **not** automatically bound to it. Publication, input form generation, prediction API and online inference remain separate approval, integration and verification gates. Do not infer production availability from Schema or exporter existence.

## Responsibility and precedence

- **Data contract / Schema**: permitted field shapes, types, required properties and validation. These are *not* layout or wireframe specifications.
- **UI/UX**: presentation, interaction, loading/error/empty states, navigation and terminology; [UI/UX directory](../ui-ux/README.md).
- **Research protocol**: data splits, feature engineering, CV/OOF/holdout and scientific interpretation; [CRISP-DM](../crisp-dm/README.md).
- **Published evidence**: immutable Case Packages under `web/data/releases/` with explicit provenance, hashes and statuses.

A JSON Schema being valid does not make its scientific contents VERIFIED or permission-cleared. Preserve package/status/license constraints. The frozen PR #35 design references are historical only, not a merged authoritative UI design.

## Relocation history (Issue #62 follow-up)

`docs/ui-ux/case-package/phase-05/evaluation-index.schema.json` was relocated **byte-for-byte** to `docs/contracts/schemas/phase-05.schema.json`. Existing historical JSON Schema `$id` was deliberately retained to avoid a silent identity or compatibility change. All in-repo runtime/test path consumers must use the canonical new path; old paths in Git history remain for audit.

This migration does not authorize Schema revision, scientific recalculation, new API, model or Production deployment.
