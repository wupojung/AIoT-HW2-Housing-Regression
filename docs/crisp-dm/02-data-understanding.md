# CRISP-DM Phase 2 — Data Understanding

**Project:** NCHU AIoT 2026 HW2 Housing Regression
**Parent Epic:** [#4 — HW2 Regression Research](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/4)
**Work item:** [#9 — Ames Housing — Data Understanding](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/9)
**Phase status:** REVIEW_PENDING (Empirical descriptive profile completed — PM Review and independent QA pending)
**Data inspection date:** 2026-10-24
**Owner download / access date:** UNKNOWN / UNRECORDED (local package verified via SHA-256 integrity match on 2026-10-24)

---

## 1. Gate summary

| Status | Finding |
|---|---|
| **Verified** | Kaggle official competition Data source page verified. Local dataset package provided under ignored `local/datasets/` with byte-for-byte SHA-256 hash match (`train.csv`, `test.csv`, `data_description.txt`, `sample_submission.csv`). |
| **Verified** | Continuous target `SalePrice` present in `train.csv` (1,460 rows × 81 columns); target absent from `test.csv` (1,459 rows × 80 columns), preserving competition holdout isolation. Explanatory predictor count: exactly 79 (excluding `Id` and `SalePrice`), satisfying course requirement (>= 14). |
| **Verified** | `Id` uniqueness verified in train and test (0 duplicates in train, 0 in test); train/test `Id` overlap is exactly 0. `sample_submission.csv` matches test IDs and ordering. |
| **Verified** | Full field-level data dictionary crosswalk completed against `data_description.txt` (77 exact matches, 2 documented aliases: `BedroomAbvGr` -> `Bedroom`, `KitchenAbvGr` -> `Kitchen`). |
| **Verified** | Full empirical profiling executed via reproducible pipelines `tools/eda/profile_ames.py` and `tools/eda/full_ames_eda.py` with outputs preserved in ignored `local/research/phase2-eda/`. |
| **Verified** | Kaggle account terms and competition rules acceptance: Previously recorded as OPEN; updated to Verified per Owner decision (2026-10-24 checkpoint resolution). Owner explicitly confirmed that the Ames dataset package was formally acquired and applicable Kaggle competition rules were agreed to, satisfying the terms gate. Provenance recorded with byte-for-byte SHA-256 integrity match. |
| **Boundary** | Phase 2 strictly descriptive. No data imputation, cleaning, feature engineering, train/test splitting, model training, or performance evaluation. |

---

## 2. Source and provenance

- **Official source:** Kaggle, [House Prices — Advanced Regression Techniques, Data](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data); [competition overview](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/overview); [rules](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/rules).
- **Access checked / Data inspection:** 2026-10-24. Local files provided in ignored `local/datasets/`.
- **Original download date:** UNKNOWN / UNRECORDED (byte-for-byte SHA-256 hashes match Kaggle distribution package).
- **License / Terms evidence:** Downloaded files are present locally and verified by SHA-256 hashes. Kaggle official competition terms and rules agreement (previously documented as OPEN) are now officially confirmed based on Owner resolution (2026-10-24 checkpoint decision confirming formal data acquisition and competition rules agreement), satisfying data acquisition authorization.
- **Exact File Manifest and SHA-256 Hashes:**
  - `train.csv`: SHA-256 `1e18addf81e5e4d347cc17ee6075bbe4a42b7fa26b9e5b063e8f692a5f929d41` (1,460 rows × 81 columns, 460,676 bytes)
  - `test.csv`: SHA-256 `8fdd3d829d4d986b58f845c9553b225e67dd8383624d90fb6ca1d4bed5798c1e` (1,459 rows × 80 columns, 451,405 bytes)
  - `data_description.txt`: SHA-256 `356a4670aa688afa8ba44b1365b633fbbac2dae535fe4638532630607d64070d` (13,370 bytes)
  - `sample_submission.csv`: SHA-256 `f19e99699b925aa3085c8d2ae43c62f15fbcd35e4a953b98025f8392c3ffa807` (1,459 rows × 2 columns, 31,939 bytes)

---

## 3. Data dictionary crosswalk & semantic categorization

The Kaggle `data_description.txt` defines 79 explanatory feature headings. All 79 feature headings map completely to the dataset schema (77 exact matches, 2 documented aliases: `BedroomAbvGr` -> `Bedroom`, `KitchenAbvGr` -> `Kitchen`).

### 3.1 Field-level classification by semantic measurement type

| Semantic Category | Fields | Description & Modeling Considerations |
|---|---|---|
| **Identifier** | `Id` | Row index; excluded from feature sets and modeling. |
| **Continuous Target** | `SalePrice` | Housing sale price in USD; training target only. |
| **Numeric-Coded Ordinal / Discrete Categorical** | `MSSubClass`, `OverallQual`, `OverallCond` | Coded as integers, but represent nominal dwelling types (`MSSubClass`) or ordinal ratings (`OverallQual`, `OverallCond`). Candidate hypothesis: evaluate whether treating as discrete/ordinal representations outperforms naive linear scales. |
| **Discrete Numeric (Counts & Dates)** | `YearBuilt`, `YearRemodAdd`, `GarageYrBlt`, `MoSold`, `YrSold`, `BsmtFullBath`, `BsmtHalfBath`, `FullBath`, `HalfBath`, `BedroomAbvGr`, `KitchenAbvGr`, `TotRmsAbvGrd`, `Fireplaces`, `GarageCars` | Integer counts of rooms/baths or calendar years. Appropriate for linear or tree-based modeling; calendar years may yield duration features (e.g. house age at sale) in Phase 3. |
| **Continuous Numeric (Areas & Dimensions)** | `LotFrontage`, `LotArea`, `MasVnrArea`, `BsmtFinSF1`, `BsmtFinSF2`, `BsmtUnfSF`, `TotalBsmtSF`, `1stFlrSF`, `2ndFlrSF`, `LowQualFinSF`, `GrLivArea`, `GarageArea`, `WoodDeckSF`, `OpenPorchSF`, `EnclosedPorch`, `3SsnPorch`, `ScreenPorch`, `PoolArea`, `MiscVal` | Physical dimensions in square feet or linear feet. Positive continuous values with heavy zeros (no porch, no pool). |
| **Ordinal Categorical (Ranked Levels)** | `ExterQual`, `ExterCond`, `BsmtQual`, `BsmtCond`, `BsmtExposure`, `BsmtFinType1`, `BsmtFinType2`, `HeatingQC`, `KitchenQual`, `Functional`, `FireplaceQu`, `GarageFinish`, `GarageQual`, `GarageCond`, `PoolQC`, `Fence` | Ordered textual evaluations (e.g., Ex, Gd, TA, Fa, Po). Candidate hypothesis: evaluate whether ordinal integer mapping or one-hot encoding yields lower validation error in Phase 3/4. |
| **Nominal Categorical (Unordered Levels)** | `MSZoning`, `Street`, `Alley`, `LotShape`, `LandContour`, `Utilities`, `LotConfig`, `LandSlope`, `Neighborhood`, `Condition1`, `Condition2`, `BldgType`, `HouseStyle`, `RoofStyle`, `RoofMatl`, `Exterior1st`, `Exterior2nd`, `MasVnrType`, `Foundation`, `Heating`, `CentralAir`, `Electrical`, `GarageType`, `PavedDrive`, `MiscFeature`, `SaleType`, `SaleCondition` | Unordered discrete attributes. Candidate hypothesis: evaluate one-hot vs target encoding under cross-validation in Phase 3/4. |

### 3.2 Structural missingness vs unrecorded missingness

In the Kaggle Ames package, missing cells are encoded as literal `"NA"`. The dictionary explicitly documents that for 15 features, `"NA"` indicates **structural absence** (the physical facility does not exist on the property):

| Field Name | Train Missing (Rate) | Test Missing (Rate) | Nature of Missingness | Dictionary Definition |
|---|---|---|---|---|
| `PoolQC` | 1453 (99.52%) | 1456 (99.79%) | Structural absence | `NA`: No Pool |
| `MiscFeature` | 1406 (96.30%) | 1408 (96.50%) | Structural absence | `NA`: None |
| `Alley` | 1369 (93.77%) | 1352 (92.67%) | Structural absence | `NA`: No alley access |
| `Fence` | 1179 (80.75%) | 1169 (80.12%) | Structural absence | `NA`: No Fence |
| `FireplaceQu` | 690 (47.26%) | 730 (50.03%) | Structural absence | `NA`: No Fireplace |
| `GarageType` | 81 (5.55%) | 76 (5.21%) | Structural absence | `NA`: No Garage |
| `GarageYrBlt` | 81 (5.55%) | 78 (5.35%) | Structural absence | `NA`: No Garage |
| `GarageFinish` | 81 (5.55%) | 78 (5.35%) | Structural absence | `NA`: No Garage |
| `GarageQual` | 81 (5.55%) | 78 (5.35%) | Structural absence | `NA`: No Garage |
| `GarageCond` | 81 (5.55%) | 78 (5.35%) | Structural absence | `NA`: No Garage |
| `BsmtQual` | 37 (2.53%) | 44 (3.02%) | Structural absence | `NA`: No Basement |
| `BsmtCond` | 37 (2.53%) | 45 (3.08%) | Structural absence | `NA`: No Basement |
| `BsmtExposure` | 38 (2.60%) | 44 (3.02%) | Structural absence | `NA`: No Basement |
| `BsmtFinType1` | 37 (2.53%) | 42 (2.88%) | Structural absence | `NA`: No Basement |
| `BsmtFinType2` | 38 (2.60%) | 42 (2.88%) | Structural absence | `NA`: No Basement |
| `LotFrontage` | 259 (17.74%) | 227 (15.56%) | Unrecorded missingness | Linear feet of street connected; requires imputation |
| `MasVnrType` | 8 (0.55%) | 16 (1.10%) | Unrecorded missingness | Masonry veneer type; unrecorded (distinct from `None`) |
| `MasVnrArea` | 8 (0.55%) | 15 (1.03%) | Unrecorded missingness | Masonry veneer area; unrecorded |
| `Electrical` | 1 (0.07%) | 0 (0.00%) | Unrecorded missingness | Electrical system; 1 unrecorded row in train |
| `MSZoning` | 0 (0.00%) | 4 (0.27%) | Unrecorded missingness | Test set unrecorded rows |
| `Utilities` | 0 (0.00%) | 2 (0.14%) | Unrecorded missingness | Test set unrecorded rows |
| `BsmtFullBath` | 0 (0.00%) | 2 (0.14%) | Unrecorded missingness | Test set unrecorded rows |
| `BsmtHalfBath` | 0 (0.00%) | 2 (0.14%) | Unrecorded missingness | Test set unrecorded rows |
| `Functional` | 0 (0.00%) | 2 (0.14%) | Unrecorded missingness | Test set unrecorded rows |
| `BsmtFinSF1` | 0 (0.00%) | 1 (0.07%) | Unrecorded missingness | Test set unrecorded row |
| `BsmtFinSF2` | 0 (0.00%) | 1 (0.07%) | Unrecorded missingness | Test set unrecorded row |
| `BsmtUnfSF` | 0 (0.00%) | 1 (0.07%) | Unrecorded missingness | Test set unrecorded row |
| `TotalBsmtSF` | 0 (0.00%) | 1 (0.07%) | Unrecorded missingness | Test set unrecorded row |
| `Exterior1st` | 0 (0.00%) | 1 (0.07%) | Unrecorded missingness | Test set unrecorded row |
| `Exterior2nd` | 0 (0.00%) | 1 (0.07%) | Unrecorded missingness | Test set unrecorded row |
| `GarageCars` | 0 (0.00%) | 1 (0.07%) | Unrecorded missingness | Test set unrecorded row |
| `GarageArea` | 0 (0.00%) | 1 (0.07%) | Unrecorded missingness | Test set unrecorded row |
| `KitchenQual` | 0 (0.00%) | 1 (0.07%) | Unrecorded missingness | Test set unrecorded row |
| `SaleType` | 0 (0.00%) | 1 (0.07%) | Unrecorded missingness | Test set unrecorded row |

---

## 4. Empirical descriptive profile & statistical findings

### 4.1 Target variable `SalePrice` distribution (N = 1,460)

- **Sample count:** 1,460
- **Mean:** $180,921.20
- **Standard deviation:** $79,442.50
- **Minimum:** $34,900.00
- **25th percentile (Q1):** $129,975.00
- **Median (50%):** $163,000.00
- **75th percentile (Q3):** $214,000.00
- **Maximum:** $755,000.00
- **Sample skewness:** 1.881 (substantial right/positive skew)
- **IQR outlier candidates (1.5 × IQR):** 61 observations exceeding upper fence ($340,037.50). Lower fence is $3,937.50 (no observations fall below).
- **Distribution observation:** `SalePrice` exhibits notable right-skewness where the mean ($180,921) exceeds the median ($163,000) by over $17,000. High-value luxury homes extend the right tail to $755,000.

### 4.2 Top numeric correlations with `SalePrice`

Calculated using pairwise-complete observations (Pearson $r$):

| Rank | Feature | Correlation ($r$) | Pairwise $N$ | Description |
|---|---|---|---|---|
| 1 | `OverallQual` | 0.7910 | 1460 | Rates the overall material and finish of the house (1-10) |
| 2 | `GrLivArea` | 0.7086 | 1460 | Above grade (ground) living area square feet |
| 3 | `GarageCars` | 0.6404 | 1460 | Size of garage in car capacity |
| 4 | `GarageArea` | 0.6234 | 1460 | Size of garage in square feet |
| 5 | `TotalBsmtSF` | 0.6136 | 1460 | Total square feet of basement area |
| 6 | `1stFlrSF` | 0.6059 | 1460 | First Floor square feet |
| 7 | `FullBath` | 0.5607 | 1460 | Full bathrooms above grade |
| 8 | `TotRmsAbvGrd` | 0.5337 | 1460 | Total rooms above grade (excluding bathrooms) |
| 9 | `YearBuilt` | 0.5229 | 1460 | Original construction date |
| 10 | `YearRemodAdd` | 0.5071 | 1460 | Remodel date |
| 11 | `GarageYrBlt` | 0.4864 | 1379 | Year garage was built |
| 12 | `MasVnrArea` | 0.4775 | 1452 | Masonry veneer area in square feet |
| 13 | `Fireplaces` | 0.4669 | 1460 | Number of fireplaces |
| 14 | `BsmtFinSF1` | 0.3865 | 1460 | Type 1 finished basement square feet |
| 15 | `LotFrontage` | 0.3518 | 1201 | Linear feet of street connected to property |

### 4.3 Multicollinearity and co-missingness patterns

- **Multicollinearity:**
  - `GarageCars` and `GarageArea` exhibit very high linear collinearity ($r = 0.882$).
  - `GrLivArea` and `TotRmsAbvGrd` exhibit strong collinearity ($r = 0.825$).
  - `TotalBsmtSF` and `1stFlrSF` exhibit strong collinearity ($r = 0.820$).
- **Co-missingness Clusters:**
  - **Garage cluster:** 81 properties in train (76 in test) simultaneously lack `GarageType`, `GarageYrBlt`, `GarageFinish`, `GarageQual`, and `GarageCond`.
  - **Basement cluster:** 37 properties in train (42–45 in test) simultaneously lack `BsmtQual`, `BsmtCond`, and `BsmtFinType1`.
  - **Masonry veneer cluster:** 8 properties in train (15 in test) simultaneously lack `MasVnrType` and `MasVnrArea`.

---

## 5. Quality risks & research limitations

1. **Target skewness and non-normality:** `SalePrice` skewness of 1.881 indicates that unregularized linear models fitted directly on raw prices will be heavily influenced by high-value outliers and violate homoscedasticity assumptions. Evaluating a logarithmic transformation (`log1p(SalePrice)`) in Phase 3 is an exploratory hypothesis to stabilize variance and optimize for Kaggle's evaluation metric.
2. **Predictor multicollinearity:** Pairs such as `GarageCars`/`GarageArea` ($r = 0.882$) and `TotalBsmtSF`/`1stFlrSF` ($r = 0.820$) introduce severe variance inflation for standard ordinary least squares (OLS) regression. Regularization (Ridge, Lasso, ElasticNet) or selective feature pruning represents a key candidate strategy in Phase 4.
3. **Imputation risk for structural absence:** Imputing missing values with naive global means or medians would mischaracterize properties lacking garages or basements. Structural absence must be explicitly distinguished and encoded as dedicated categorical levels (`"None"`) or zero square footage.
4. **Test-set exclusive missingness:** The test set contains isolated missing entries in features that are complete in the training set (`TotalBsmtSF`, `GarageCars`, `MSZoning`, `Utilities`, etc.). Preprocessing pipelines must be robust against novel missingness in future inference.
5. **Correlation vs causality limit:** Pearson correlation measures linear association only and does not establish causal housing price drivers or optimal feature subsets.

---

## 6. Phase 3 exploratory research questions & candidate hypotheses

The following items represent exploratory candidate hypotheses and open research questions for Phase 3 (Data Preparation) and Phase 4 (Modeling) exploration, not mandatory or binding modeling decisions:

1. **Target transformation hypothesis:** Evaluate whether training linear and tree-based models on `log(SalePrice)` optimizes Kaggle's evaluation metric (RMSLE) while reporting back-transformed RMSE, MAE, and R² for course grading.
2. **Categorical encoding hypothesis:** Test whether ordinal features (`OverallQual`, `ExterQual`, `KitchenQual`) yield better cross-validation performance with ordinal-integer encoding compared to one-hot encoding.
3. **Structured imputation hypothesis:** Test whether separating the 15 structural absence features (encoded as `"None"` / 0) from genuine unrecorded missing features (imputed using training fold medians/modes) prevents artificial distortion.
4. **Collinearity management hypothesis:** Investigate whether retaining collinear pairs (`GarageCars`/`GarageArea`) under regularized models (Ridge/Lasso) or constructing composite features yields superior generalization.
5. **Leakage prevention requirement:** Confirm that all preprocessing transformations (imputers, encoders, scalers) are strictly fit on training cross-validation folds and never across the combined dataset.

---

## 7. Reproducibility & verification record

- **Reproducible entrypoints:**
  - Fast summary profiler: [`tools/eda/profile_ames.py`](../../tools/eda/profile_ames.py)
    ```bash
    python3 tools/eda/profile_ames.py --local-root "${REGSCOPE_LOCAL_ROOT:-local}" --access-date 2026-10-24 --terms-confirmed
    ```
    Supports optional `--local-root` to target an external ignored `local/` data store.
  - Full comprehensive EDA pipeline: [`tools/eda/full_ames_eda.py`](../../tools/eda/full_ames_eda.py)
    ```bash
    python3 tools/eda/full_ames_eda.py --local-root "${REGSCOPE_LOCAL_ROOT:-local}" --access-date 2026-10-24 --terms-confirmed
    ```
    Supports optional `--local-root` to target an external ignored `local/` data store and output directory.
- **Automated test suites executed:**
  - EDA focused suite: `python3 -m unittest discover -s tests/tools/eda -v` (50 tests passed)
  - Security scanning suite: `python3 -m unittest discover -s tests/security -v` (26 tests passed)
  - Tracked repository scan: `python3 tools/security_scan.py --tracked` (passed, no findings)
- **Private research artifacts:**
  - All detailed machine-readable manifests (`field_manifest.json`, `figures_manifest.json`, `profile.json`, `correlation_matrix.csv`, Traditional Chinese research report `report.md`, and 88 visual figure assets) are preserved under ignored `local/research/phase2-eda/`.
  - All generated figures under ignored `local/research/phase2-eda/figures/` (88 figures, excluding identifier `Id` and holding `SalePrice` in target-specific FIG-03) are **provisional unreviewed local drafts** produced for internal exploratory profiling. In headless environments without `matplotlib`, figures are rendered via pure-Python fallback routines (structured vector SVGs with complete axes and labels, alongside pixel PNG fallbacks). These charts serve internal exploratory purposes only and are **not** approved publication-ready public visual assets. Any proposed public web or report figures will require formal styling, aggregation, and dedicated review; raw observation scatter points and unreviewed charts remain strictly confined to private `local/`.

---

## References

1. Kaggle, [House Prices — Advanced Regression Techniques, Data](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data), [overview](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/overview), and [rules](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/rules). Accessed 2026-10-24.
2. De Cock, D. (2011), [Ames, Iowa: Alternative to the Boston Housing Data as an End of Semester Regression Project](https://doi.org/10.1080/10691898.2011.11889627).
3. Repository [Security and Data Policy](../SECURITY_AND_DATA_POLICY.md): raw datasets and working profiles remain strictly confined to ignored `local/`.
