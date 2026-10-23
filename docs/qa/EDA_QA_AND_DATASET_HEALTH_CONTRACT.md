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

## Findings and known gaps

- The current profiler emits no Figure ID, figure manifest, generator command, population/sample declaration, or provenance linkage for generated SVGs. The Phase 2 document has a figure plan, but it is not connected to generated files.
- It does not explicitly count duplicate IDs; only the boolean `id.unique` is reported.
- `csv.DictReader` tolerates extra fields on a row by placing them under a `None` key; the profiler currently ignores that key. Thus malformed wide rows may be silently accepted. Minimal synthetic reproduction: a header `Id,SalePrice` followed by `1,100,unexpected`.
- Numeric parsing accepts `NaN` and infinity as floats; downstream summary values may then be non-finite and unsuitable for JSON consumers.
- SVG output is parseable and dimensioned, but contains no axis labels/units or machine-readable figure provenance.
- The existing code expects local `train.csv`, `test.csv`, and `data_description.txt`. This QA does not use or require those files.

The findings are for W1P1 / W1P2 review. This QA branch deliberately does not modify `tools/eda/profile_ames.py` or change the analysis behavior.
