# RegScope Phase 2 — Exploratory Analysis Index Contract v1

> Defines the static analysis/figure selector at `phases/phase-02/analyses.json`. The authoritative schema is [`phase-02.schema.json`](../../../design/data-contracts/schemas/phase-02.schema.json). This contract does not authorize EDA runs or figure publication.

## Payload and meaning

The root has `schema_version,case_id,status,default_analysis_id,analyses[]`. Each item has `id,figure_id,title,status,image_ref,table_ref,description,finding,limitations,provenance_ref`. IDs are stable within the Case Package. If `analyses[]` is empty, `default_analysis_id` is null. Otherwise the default must resolve to an item; changing the selection replaces the complete figure/finding/provenance context and clears stale content.

When source-safe, reviewed figures do not exist, keep figure and table refs null and use `UNAVAILABLE` for the analysis. A selector entry is not proof that a figure was generated. `MOCK` requires synthetic data and visible watermarking. `VERIFIED` requires source/rights review, asset integrity, accessible description/table, and package publication approval. No browser-created statistical charts from this index.

Allowed assets are case-root-relative and must resolve through both `assets/figure-manifest.json` and `package.json.files[]`. Do not embed dataset rows in table refs. Findings and limitations must be attributable; missing evidence remains null/UNAVAILABLE.

## Samples and validation

- [`analyses.unavailable.json`](./sample/analyses.unavailable.json): no analysis selector entries.
- [`analyses.nonempty.mock.json`](./sample/analyses.nonempty.mock.json): one synthetic selector with no image asset.
- [`VALIDATION-MATRIX.md`](./VALIDATION-MATRIX.md): refs, default selection, status, rights, and privacy checks.
- Use the shared Draft 2020-12 Phase 2 schema and [`validate_schema.py`](../../../design/tools/validate_schema.py).
