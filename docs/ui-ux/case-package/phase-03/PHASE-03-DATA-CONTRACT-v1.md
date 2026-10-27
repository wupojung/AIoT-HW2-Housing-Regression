# RegScope Phase 3 — Data Preparation & Feature Lineage Contract v1

> Defines the static preparation summary at `phases/phase-03/preparation.json`. The authoritative schema is [`phase-03.schema.json`](../../../design/data-contracts/schemas/phase-03.schema.json). This is an aggregate summary, not a data transformation runtime or row-level lineage export.

## Payload and meaning

The root has `schema_version,case_id,status,feature_types[],stages[],treatments[],split,lineage_ref`. Feature types use only `nominal`, `ordinal`, `discrete`, and `continuous`. The four stages must appear in order: `raw`, `filtered`, `processed`, `encoded`. Each stage's `unit` explicitly distinguishes raw columns, pre-encoding columns, and encoded features; totals with different units must not be compared as if they had one denominator.

Each stage has a nullable `total` plus `total_status`, and `segments[]` plus `distribution_status`. When counts are reported, segment `type_id` values must resolve to `feature_types`; counts are nonnegative and sum to `total`. If the distribution is unknown, leave segments empty and mark it unavailable. Never draw equal-sized or invented percentage segments. Source-reported totals use `SOURCE_REPORTED_NOT_VERIFIED`; do not promote historical handoff values to `VERIFIED`.

`treatments[]` records only source-supported cleaning/encoding operations. It may be empty. `split` is row counts (`source_labeled_rows,training_rows,holdout_rows,seed,status`), not a feature count; values may be null. `lineage_ref` is optional and may point to an approved public `feature-lineage.json`; it must not expose row IDs, fold membership, or private preprocessing artifacts. Unknown fit population or pipeline version stays null.

## Ames staging data

The current Ames sample retains the reported 79 raw candidate columns, 248 encoded features, and 1460/1168/292 source/train/holdout counts with seed 42 as `SOURCE_REPORTED_NOT_VERIFIED`. Filtered/pre-encoding counts, feature-type shares, treatments, fit population, pipeline version, and lineage are unavailable and remain blank. The package phase status is `PLANNED`, not VERIFIED. These numbers do not authorize access to Holdout rows.

## Samples and validation

- [`preparation.unavailable.json`](./sample/preparation.unavailable.json): no preparation evidence.
- [`preparation.nonempty.mock.json`](./sample/preparation.nonempty.mock.json): synthetic counts and distributions to exercise the chart layout.
- [`VALIDATION-MATRIX.md`](./VALIDATION-MATRIX.md): ordering, units, count sums, source status, and lineage boundaries.
- Use the shared Draft 2020-12 Phase 3 schema and [`validate_schema.py`](../../../design/tools/validate_schema.py).
