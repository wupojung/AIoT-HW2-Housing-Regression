# RegScope canonical Phase 1–6 JSON Schema registry

This directory is the **single repository location** for the six phase-level JSON Schema references used by RegScope validation. See [data contract ownership](../README.md) and [UI/UX responsibility](../../ui-ux/README.md).

| Phase | Canonical file | Scope |
| --- | --- | --- |
| 1 | `phase-01.schema.json` | Business Understanding |
| 2 | `phase-02.schema.json` | Data Understanding |
| 3 | `phase-03.schema.json` | Data Preparation |
| 4 | `phase-04.schema.json` | Modeling |
| 5 | `phase-05.schema.json` | Evaluation Index |
| 6 | `phase-06.schema.json` | Deployment |

## Provenance / compatibility

The Phase 1, 2, 3, 4 and 6 schema references were originally frozen from historical [PR #35](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35), pinned head `08413d08f5cabbbf519b8ceee4ed68b7187d2669`, for the synthetic Core E2E. PR #35 was later **CLOSED / UNMERGED**; this snapshot's provenance is not a claim that the PR was merged or that every contract field represents verified released scientific data.

Phase 5 was originally tracked at `docs/ui-ux/case-package/phase-05/evaluation-index.schema.json`; it is now located at `docs/contracts/schemas/phase-05.schema.json` **with unchanged JSON bytes**, including its historic `$id`. The `$id` is a schema identifier URI, **not a supported current file-path reference**. Consumers must read the file from the new path; do not revise its `$id`, schema version, constraints or semantics without separately reviewed contract-version changes.

All schema changes require an explicit contract review and regression tests. Do not conflate schema-valid JSON with a verified result, approved license, model quality, or an independently validated production site.
