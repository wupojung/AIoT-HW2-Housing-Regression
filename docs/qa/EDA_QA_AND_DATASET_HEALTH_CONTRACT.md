# EDA QA and Dataset Health Check contract

This QA checkpoint tests the Phase 2 profiler with synthetic inputs only. It does not include Kaggle rows, empirical Ames results, preprocessing, or model training.

## Current QA coverage

`tests/tools/eda/test_profile_ames.py` covers the terms gate, required input files, output confinement, symlink rejection, a basic synthetic profile, dictionary crosswalk, SHA-256 presence, and SVG creation.

`tests/tools/eda/test_profile_ames_qa.py` adds known-answer checks for sample standard deviation, linear-interpolated quantiles, population-moment skew, pairwise-complete Pearson correlation, constant columns, target/identifier roles, the 14-predictor count boundary, duplicate rows and IDs, empty/all-missing inputs, and SVG XML structure and dimensions.

These tests do not claim line or branch coverage percentages. The repository does not currently pin a coverage reporter, so the QA avoids adding one solely to publish a percentage.

## Dataset Health Check JSON proposal

The future web view should consume an aggregate, versioned report; it must never need raw rows. A minimum v1 shape is:

```json
{
  "contract_version": "1.0",
  "profile_status": "complete",
  "source": {
    "dataset_id": "ames-housing",
    "source_url": "https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data",
    "source_version": null,
    "access_date": null,
    "input_sha256": null
  },
  "schema": {
    "row_count": 0,
    "column_count": 0,
    "predictor_count": 0,
    "target_column": "SalePrice",
    "identifier_column": "Id",
    "fields": []
  },
  "quality": {
    "missing_cells": 0,
    "duplicate_rows": 0,
    "duplicate_ids": 0,
    "checks": []
  },
  "statistics": [],
  "figures": [],
  "generated": {
    "tool": "tools/eda/profile_ames.py",
    "tool_version": null,
    "generated_at": null
  },
  "limitations": []
}
```

Contract rules:

- `contract_version` is required and consumers must reject unsupported major versions.
- Counts are non-negative integers; unknown measurements are `null`, never guessed as zero.
- `profile_status` is `complete`, `partial`, or `blocked`; `checks` carry `check_id`, `status` (`pass`, `warn`, `blocked`), and a concise public-safe summary.
- Each field summary carries `name`, `role` (`predictor`, `target`, `identifier`), `kind`, `missing_count`, and `missing_rate`; no row-level values or IDs are exposed.
- Statistics are aggregate only and identify the statistic and population; any sample statistic must say so.
- Each figure has a stable `figure_id`, title/caption, source version and SHA-256, population/sample, generator and command, and `statement_kind` (`observation` or `hypothesis`). Public artifact paths must not disclose local paths.
- `generated_at` is ISO 8601 UTC when known; synthetic fixtures and blocked reports must not masquerade as observed dataset results.
- No credentials, local filesystem paths, raw rows, or private source files belong in this contract.

## Future contract test specification

Before a website consumes v1, tests should validate: required keys and supported version; count types and null semantics; field role uniqueness for target and identifier; missing-rate bounds; allowed status enums; stable figure ID uniqueness; figure provenance completeness; no raw-row or local-path keys; and correct rendering of `blocked`/`partial` reports without numeric placeholders. Contract fixtures must be synthetic and contain no real dataset values.

## Historical baseline findings and resolution status

The following points were recorded as initial QA baseline findings during Issue #11 evaluation against the early profiler, and their current resolution status in the integrated pipeline is tracked below:

- **Figure Manifest & Provenance Linkage**: Initially, the baseline profiler emitted no figure manifest, command, or provenance metadata. *Resolution:* Addressed in the integrated Phase 2 EDA pipeline (`tools/eda/full_ames_eda.py`), which generates `figures_manifest.json` and `figures_manifest.csv` with figure IDs, captions, source SHAs, generation commands, and limitations.
- **Duplicate ID Counting**: Initially, only boolean `id.unique` was reported. *Resolution:* Both `profile_ames.py` and `full_ames_eda.py` now explicitly report duplicate ID counts (`duplicate_count` in profile and `train_duplicate_id_count` / `test_duplicate_id_count` in schema checks).
- **Malformed CSV Row Validation**: Initially, `csv.DictReader` tolerated extra or missing cells without error. *Resolution:* Both profiling tools now enforce strict field counts per line (`csv.reader` with header length check) and fail closed with a descriptive `ValueError`.
- **Non-Finite Numeric Value Rejection**: Initially, numeric parsing could accept `NaN` and infinity into float summaries. *Resolution:* Both pipelines validate with `math.isfinite` and serialize JSON with `allow_nan=False`, rejecting non-finite values before output.
- **Figure Labeling and Truthfulness**: Initially, fallback charts lacked axis labeling and provenance. *Resolution:* Integrated SVG and pure-Python rasterized charts render explicit axes, labels, data-derived observations, and masked legends for undefined correlations.
- **Synthetic Test Isolation**: Confirmed; all QA and unit test suites operate strictly on synthetic fixtures and require no local Kaggle data files.

These historical baseline notes document the QA contract evolution from initial Issue #11 findings through the integrated Issue #9 Package B / PR #12 deliverables.
