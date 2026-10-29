# RegScope — Contracts Registry

**Authoritative contract root:** `docs/contracts/`. API and CLI interfaces must be specified here when approved; a JSON Schema describes JSON shape, not deployment procedure. **Phase schema directory:** [schemas/](schemas/README.md). One canonical location for Phase 1–6 machine-readable contracts. The Phase 5 Evaluation Index schema lives at [schemas/phase-05.schema.json](schemas/phase-05.schema.json).

## Responsibility and precedence

- **Data contract / Schema**: permitted field shapes, types, required properties and validation. These are *not* layout or wireframe specifications.
- **UI/UX**: presentation, interaction, loading/error/empty states, navigation and terminology; [UI/UX directory](../ui-ux/README.md).
- **Research protocol**: data splits, feature engineering, CV/OOF/holdout and scientific interpretation; [CRISP-DM](../crisp-dm/README.md).
- **Published evidence**: immutable Case Packages under `web/data/releases/` with explicit provenance, hashes and statuses.

A JSON Schema being valid does not make its scientific contents VERIFIED or permission-cleared. Preserve package/status/license constraints. The frozen PR #35 design references are historical only, not a merged authoritative UI design.

## Relocation history (Issue #62 follow-up)

`docs/ui-ux/case-package/phase-05/evaluation-index.schema.json` was relocated **byte-for-byte** to `docs/contracts/schemas/phase-05.schema.json`. Existing historical JSON Schema `$id` was deliberately retained to avoid a silent identity or compatibility change. All in-repo runtime/test path consumers must use the canonical new path; old paths in Git history remain for audit.

This migration does not authorize Schema revision, scientific recalculation, new API, model or Production deployment.
