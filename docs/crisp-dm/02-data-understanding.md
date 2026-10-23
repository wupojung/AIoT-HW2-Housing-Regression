# CRISP-DM Phase 2 — Data Understanding

**Project:** NCHU AIoT 2026 HW2 Housing Regression
**Parent Epic:** [#4 — HW2 Regression Research](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/4)
**Work item:** [#9 — Ames Housing — Data Understanding](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/9)
**Phase status:** BLOCKED — source and dictionary reviewed; empirical profiling awaits authorized Owner-provided files.
**Checkpoint date:** 2026-10-24

## 1. Gate summary

| Status | Finding |
|---|---|
| Verified | Kaggle's official competition Data page is the requested source. The public page identifies the competition and dataset description; Kaggle account access and competition rules govern downloads. |
| Verified | No files were present in `local/datasets/` during this checkpoint. W1P2 independently confirmed the empty directory. |
| Verified | The project target is `SalePrice`; `Id` is an identifier and is excluded from ordinary predictor counts. The source competition description characterizes the data as 79 explanatory variables. |
| Assumed | The intended package is the competition download containing `train.csv`, `test.csv`, and `data_description.txt`; Owner must confirm exact names/version and provide these files locally. |
| Open | Owner's access date, exact file hashes/version, current rules acceptance, and the applicability of the page's MIT license metadata to each distributed file. |
| Blocked | Actual shape, predictor count in the delivered CSV, dtypes, missingness, duplicates, ID properties, target distribution, cardinalities, correlations, and anomaly candidates. No values are inferred from secondary copies or the original Ames study. |

## 2. Source and provenance

- **Official source:** Kaggle, [House Prices — Advanced Regression Techniques, Data](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data); [competition overview](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/overview); [rules](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/rules).
- **Access checked:** 2026-10-24 via public page metadata. The Data and Rules page content requiring account/competition access was not independently inspectable in this review.
- **License/terms:** Kaggle's public competition page search metadata displayed `MIT`; this is not treated as proof that all files may be redistributed. Owner/account holder must log in, accept applicable current rules, and confirm the terms that apply to the downloaded files. Do not bypass access controls.
- **Local files and SHA-256:** None available; hashes are therefore **not measured**. Do not publish private local paths. Once provided, the script records hashes for each CSV and the dictionary in ignored `local/research/phase2-eda/profile.json`.
- **Required Owner action:** Obtain through the official competition page after satisfying its login and terms gate, then place `train.csv`, `test.csv`, and `data_description.txt` in ignored `local/datasets/`. Preserve the original files unchanged.

## 3. Data dictionary crosswalk

The competition overview describes **79 explanatory variables** in addition to `Id` and the `SalePrice` training target. This is source-level context, not a count verified against the absent local CSV. The count must be recomputed from the actual `train.csv`; no cap is applied. `Id` is not a normal house attribute and must be reported separately. `SalePrice` is the continuous target in training data and is absent from the Kaggle test predictors.

The Kaggle `data_description.txt` is the field-level dictionary of record for the exact download. The following crosswalk gives candidate measurement types using representative fields described by that source; it is not a substitute for checking all delivered columns and category encodings.

| Dictionary concept / examples | Candidate type | Phase 2 verification |
|---|---|---|
| `Id` | Identifier | Verify presence, missingness, uniqueness, duplicates, and train/test overlap; exclude from predictor tally. |
| `SalePrice` | Numeric continuous target | Verify only in training file; profile non-null count, range, quantiles, skew and histogram. |
| `MSSubClass`, `OverallQual`, `OverallCond`, `MoSold` | Numeric-coded ordinal/discrete candidates | Confirm semantics and allowed values from the dictionary; do not assume integer dtype means continuous. |
| `LotFrontage`, `LotArea`, `YearBuilt`, `GrLivArea`, `GarageArea` | Numeric continuous/discrete candidates | Check dictionary meaning, type, range, missingness, and unusual values. |
| `MSZoning`, `Street`, `Neighborhood`, `HouseStyle`, `SaleType` | Nominal categorical candidates | Check observed levels/cardinality and compare levels with dictionary descriptions. |
| `ExterQual`, `BsmtQual`, `HeatingQC`, `KitchenQual`, `Functional` | Ordered categorical candidates | Confirm ordered levels in dictionary; do not impose ordering from string labels alone. |
| `Alley`, `PoolQC`, `Fence`, `MiscFeature`, basement/garage feature fields | Categorical fields with possible structural absence semantics | Inspect dictionary definitions and observed missingness together; distinguish “not present” from unknown/unrecorded only when the source supports it. |

**Field-level status:** complete mapping and actual predictor count remain blocked until the Owner supplies the exact dictionary and CSVs. The script reports the observed columns without trimming them; any type/ordinal mapping refinements should be recorded against the local dictionary after review.

## 4. Empirical EDA status

**BLOCKED — no authorized CSV is present.** No empirical statistics, plot, missingness pattern, anomaly, or data-quality conclusion is claimed here. De Cock's original Ames study and other competition mirrors are not substitutes for this competition download and were not used to fabricate a profile.

After the Owner provides files, run from the repository root:

```bash
python3 tools/eda/profile_ames.py --access-date YYYY-MM-DD --terms-confirmed
```

The Owner must replace the date with the actual access/download date and confirm the login/rules gate. Input defaults to `local/datasets/`; the JSON profile and target histogram default to ignored `local/research/phase2-eda/`. Review them for public safety before moving any aggregate result into this document.

The script records file hashes, shapes, predictor counts, dtypes, missingness and co-missingness patterns, duplicate rows, identifier uniqueness and train/test overlap, categorical cardinality, numeric summaries, IQR anomaly candidate counts, target summaries, numeric target correlations, and train/test schema checks. It parses dictionary field headings and reports a name-level crosswalk against the training schema; it does not publish definitions or infer measurement types. `Id` remains in integrity checks but is excluded from numeric distributions, IQR flags, and target correlations. Input must be `local/datasets/`, and all output paths are resolved and constrained to ignored `local/`; symlinked local roots and output escapes are rejected. It does not alter data, impute, select features, split data for modeling, or fit models. Treat distribution extremes and IQR flags as descriptive candidates for human review, not errors or causal evidence.

## 5. Phase 3 handoff

Decisions to make only after dictionary and profile review:

1. Determine whether missing values represent structural absence, unknown values, or data quality issues, and document a field-specific preparation decision before transformation.
2. Confirm the usable original predictor count and resolve the course requirement's meaning of “at least 14” (candidate inputs versus final selected variables) with PM/teacher.
3. Decide how to encode nominal and ordinal fields from documented semantics; do not treat numeric-looking category codes as continuous without justification.
4. Inspect duplicated records, ID anomalies/overlap, implausible ranges, and target distribution with domain context; preserve source data and log any later handling decision.
5. Prevent leakage: `Id` is not a regular predictor; `SalePrice` is target-only; all learned preparation and feature selection must be fitted only within training folds in Phase 3/4.
6. Resolve whether evaluation should additionally report Kaggle RMSLE alongside the course's RMSE, MAE, and R².

No cleaning, feature selection, model fitting, modeling split, or performance score belongs to this Phase 2 checkpoint.

## 6. Reproducibility and verification record

- Reproducible entrypoint: [`tools/eda/profile_ames.py`](../../tools/eda/profile_ames.py)
- Synthetic-only tests: [`tests/tools/eda/test_profile_ames.py`](../../tests/tools/eda/test_profile_ames.py)
- Runtime dependencies: Python standard library only.
- W1P2 independent review by agy (`w1:p2`): completed against the working tree on 2026-10-24. Scope covered the profiler, its synthetic tests, and this document; real Kaggle CSVs were not inspected and no files were changed. The reviewer checked dictionary heading matching, local path confinement, `Id` exclusion, pairwise-complete correlations, and the descriptive-only boundary; reported no actionable defects. Full collaboration checkpoint is recorded in Issue #9.
- Dataset tests use generated synthetic rows only. They do not embed Kaggle rows.
- Empirical EDA and file hashes: blocked pending Owner-supplied files.

## References

1. Kaggle, [House Prices — Advanced Regression Techniques, Data](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data), [overview](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/overview), and [rules](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/rules). Accessed 2026-10-24; exact download version and terms remain for Owner confirmation.
2. De Cock, D. (2011), [Ames, Iowa: Alternative to the Boston Housing Data as an End of Semester Regression Project](https://doi.org/10.1080/10691898.2011.11889627). The original research dataset differs from the Kaggle competition files and is not used as a substitute.
3. Repository [Security and Data Policy](../SECURITY_AND_DATA_POLICY.md): raw datasets and working profiles remain in ignored `local/`.
