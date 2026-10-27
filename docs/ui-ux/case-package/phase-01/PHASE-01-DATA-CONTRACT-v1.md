# RegScope Phase 1 — Problem Definition Content Contract v1

> Defines the static text payload for Phase 1. The authoritative modeling schema is [`phase-01.schema.json`](../../../design/data-contracts/schemas/phase-01.schema.json). This contract does not authorize research claims or publication.

## Payload and meaning

The package entry is `phases/phase-01/content.json` with `schema_version,case_id,status,sections[]`. Each section has a stable `section_id`, visible `title`, and plain-text `body`. Section order is display order. The case name, target label, and target unit come only from the shared `case.json`; do not repeat or contradict them in section prose.

Use `UNAVAILABLE` with `sections:[]` when no reviewed text exists. `MOCK` text must be visibly identified as synthetic/UI-only and must not be shown as a research finding. `PLANNED` may identify a section that is expected but not written. `VERIFIED` requires sourced/reviewed prose and package-level publication approval; schema validity alone is insufficient.

Keep research question, objective, and limitations distinct. Do not invent methods, results, metrics, or citations to fill empty cards. No raw participant/personal records, secrets, unreviewed source paths, or model outputs belong in this file.

## Samples and validation

- [`content.unavailable.json`](./sample/content.unavailable.json): honest empty state.
- [`content.nonempty.mock.json`](./sample/content.nonempty.mock.json): synthetic prose for layout testing only.
- [`VALIDATION-MATRIX.md`](./VALIDATION-MATRIX.md): schema and package-level checks.
- Validate with the shared Draft 2020-12 schema and [`validate_schema.py`](../../../design/tools/validate_schema.py); do not duplicate a per-phase validator.
