"""Reusable, train-fitted preprocessing pipeline for Ames Housing regression."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .constants import (
    ALL_PREDICTOR_COLUMNS,
    GENUINE_MISSING_INDICATORS,
    ID_COLUMN,
    NOMINAL_COLUMNS,
    NUMERIC_COLUMNS,
    ORDINAL_COLUMNS,
    ORDINAL_LEVELS,
    STRUCTURAL_ABSENCE_COLUMNS,
    STRUCTURAL_INDICATORS,
    STRUCTURAL_NOMINAL_SENTINELS,
    TARGET_COLUMN,
)


@dataclass
class TransformResult:
    """Encapsulated transformed dataset partition output."""

    ids: list[str]
    y: list[float] | None
    feature_names: list[str]
    features: list[dict[str, float]]
    feature_matrix: list[list[float]]
    unseen_categories: list[dict[str, Any]]
    split_name: str
    n_rows: int
    n_features: int

    def to_dict_records(self, include_id: bool = True, include_target: bool = True) -> list[dict[str, Any]]:
        """Return row records as list of dictionaries."""
        records: list[dict[str, Any]] = []
        for i in range(self.n_rows):
            rec: dict[str, Any] = {}
            if include_id and i < len(self.ids):
                rec[ID_COLUMN] = self.ids[i]
            if include_target and self.y is not None and i < len(self.y):
                rec[TARGET_COLUMN] = self.y[i]
            rec.update(self.features[i])
            records.append(rec)
        return records

    def to_dataframe(self, include_id: bool = True, include_target: bool = True):
        """Export to pandas DataFrame if pandas is installed."""
        try:
            import pandas as pd
            return pd.DataFrame(self.to_dict_records(include_id=include_id, include_target=include_target))
        except ImportError as exc:
            raise RuntimeError("pandas is not installed in the environment.") from exc

    def to_numpy(self):
        """Export feature matrix to numpy ndarray if numpy is installed."""
        try:
            import numpy as np
            return np.array(self.feature_matrix, dtype=np.float64)
        except ImportError as exc:
            raise RuntimeError("numpy is not installed in the environment.") from exc


class AmesDataPreparationPipeline:
    """Reproducible train-fitted preprocessing pipeline.

    Guarantees:
    - Learns parameters strictly from training partition (no leakage).
    - Excludes Id and isolates SalePrice.
    - Handles 15 structural absence fields via category sentinels and indicator flags.
    - Imputes non-structural missingness via training medians and modes.
    - Maps ordinal levels to source-documented hierarchical integer scores.
    - One-hot encodes nominal fields and handles unknown categories gracefully.
    - Preserves all 61 SalePrice IQR outlier candidates in y.
    """

    def __init__(
        self,
        handle_unknown: str = "ignore",
        garage_sentinel_year: float = 0.0,
        add_structural_indicators: bool = True,
    ) -> None:
        self.handle_unknown = handle_unknown
        self.garage_sentinel_year = garage_sentinel_year
        self.add_structural_indicators = add_structural_indicators

        self.is_fitted: bool = False
        self.numeric_impute_values: dict[str, float] = {}
        self.nominal_impute_values: dict[str, str] = {}
        self.ordinal_impute_values: dict[str, int] = {}
        self.nominal_levels: dict[str, list[str]] = {}
        self.feature_names: list[str] = []
        self.feature_manifest: list[dict[str, Any]] = []
        self.fit_summary: dict[str, Any] = {}
        self.unseen_categories_encountered: list[dict[str, Any]] = []

    def _is_missing(self, val: Any) -> bool:
        if val is None:
            return True
        if isinstance(val, str):
            v_str = val.strip()
            return v_str == "" or v_str == "NA"
        if isinstance(val, float) and math.isnan(val):
            return True
        return False

    def fit(self, rows: Sequence[Mapping[str, Any]]) -> AmesDataPreparationPipeline:
        """Fit all preprocessing parameters strictly on training records."""
        if not rows:
            raise ValueError("Cannot fit pipeline on empty dataset.")

        n_samples = len(rows)

        # 1. Learn medians for numeric columns
        self.numeric_impute_values = {}
        for col in NUMERIC_COLUMNS:
            valid_vals: list[float] = []
            for r in rows:
                val = r.get(col)
                if not self._is_missing(val):
                    try:
                        valid_vals.append(float(val))
                    except (ValueError, TypeError):
                        pass
            if valid_vals:
                self.numeric_impute_values[col] = float(statistics.median(valid_vals))
            else:
                self.numeric_impute_values[col] = 0.0

        # Special handling for GarageYrBlt: compute median among properties with garages
        garage_years: list[float] = []
        for r in rows:
            g_type = r.get("GarageType")
            g_yr = r.get("GarageYrBlt")
            if not self._is_missing(g_type) and g_type != "None" and not self._is_missing(g_yr):
                try:
                    garage_years.append(float(g_yr))
                except (ValueError, TypeError):
                    pass
        if garage_years:
            self.numeric_impute_values["GarageYrBlt"] = float(statistics.median(garage_years))

        # 2. Learn modes for nominal columns and collect unique training levels
        self.nominal_impute_values = {}
        self.nominal_levels = {}
        for col in NOMINAL_COLUMNS:
            sentinel = STRUCTURAL_NOMINAL_SENTINELS.get(col)
            counts: dict[str, int] = {}
            for r in rows:
                val = r.get(col)
                if self._is_missing(val):
                    val = sentinel if sentinel is not None else None
                if val is not None:
                    val_str = str(val).strip()
                    counts[val_str] = counts.get(val_str, 0) + 1

            if counts:
                # Mode is the most frequent observed category
                mode_val = max(counts.items(), key=lambda pair: pair[1])[0]
                self.nominal_impute_values[col] = mode_val
                # Sort unique levels alphabetically for stable dummy ordering
                self.nominal_levels[col] = sorted(list(counts.keys()))
            else:
                fallback = sentinel if sentinel is not None else "Missing"
                self.nominal_impute_values[col] = fallback
                self.nominal_levels[col] = [fallback]

        # 3. Learn modes/medians for non-structural ordinal columns
        self.ordinal_impute_values = {}
        for col in ORDINAL_COLUMNS:
            if col in STRUCTURAL_ABSENCE_COLUMNS:
                # Documented structural absence is explicitly score 0
                self.ordinal_impute_values[col] = 0
            else:
                mapping = ORDINAL_LEVELS[col]
                mapped_scores: list[int] = []
                for r in rows:
                    val = r.get(col)
                    if not self._is_missing(val):
                        val_str = str(val).strip()
                        if val_str in mapping:
                            mapped_scores.append(mapping[val_str])
                if mapped_scores:
                    self.ordinal_impute_values[col] = int(round(statistics.median(mapped_scores)))
                else:
                    self.ordinal_impute_values[col] = 1

        # 4. Construct deterministic feature sequence and metadata manifest
        self.feature_names = []
        self.feature_manifest = []

        # (a) Numeric continuous & discrete features
        for col in NUMERIC_COLUMNS:
            self.feature_names.append(col)
            self.feature_manifest.append({
                "feature_name": col,
                "source_column": col,
                "encoding_type": "numeric_continuous_or_discrete",
                "imputation_strategy": f"train_median ({self.numeric_impute_values[col]})",
            })

        # (b) Physical presence indicators
        if self.add_structural_indicators:
            for ind in STRUCTURAL_INDICATORS:
                self.feature_names.append(ind)
                self.feature_manifest.append({
                    "feature_name": ind,
                    "source_column": ind.replace("Has", ""),
                    "encoding_type": "binary_structural_indicator",
                    "imputation_strategy": "deterministic_physical_presence",
                })

        # (b2) Explicit missingness indicators for genuine non-structural missing fields
        for ind in GENUINE_MISSING_INDICATORS:
            self.feature_names.append(ind)
            self.feature_manifest.append({
                "feature_name": ind,
                "source_column": ind.replace("_is_missing", ""),
                "encoding_type": "binary_missingness_indicator",
                "imputation_strategy": "explicit_genuine_missing_flag",
            })

        # (c) Ordinal features (hierarchically mapped)
        for col in ORDINAL_COLUMNS:
            self.feature_names.append(col)
            self.feature_manifest.append({
                "feature_name": col,
                "source_column": col,
                "encoding_type": "ordinal_integer_rank",
                "imputation_strategy": (
                    "structural_absence_zero (0)"
                    if col in STRUCTURAL_ABSENCE_COLUMNS
                    else f"train_median_level ({self.ordinal_impute_values[col]})"
                ),
            })

        # (d) Nominal one-hot encoded dummy features
        for col in NOMINAL_COLUMNS:
            for level in self.nominal_levels[col]:
                feat_name = f"{col}_{level}"
                self.feature_names.append(feat_name)
                self.feature_manifest.append({
                    "feature_name": feat_name,
                    "source_column": col,
                    "encoding_type": "one_hot_dummy",
                    "level": level,
                    "imputation_strategy": (
                        "structural_sentinel_None"
                        if col in STRUCTURAL_NOMINAL_SENTINELS
                        else f"train_mode ({self.nominal_impute_values[col]})"
                    ),
                })

        self.fit_summary = {
            "n_train_samples": n_samples,
            "raw_predictors_count": len(ALL_PREDICTOR_COLUMNS),
            "encoded_features_count": len(self.feature_names),
            "numeric_count": len(NUMERIC_COLUMNS),
            "indicators_count": len(STRUCTURAL_INDICATORS) if self.add_structural_indicators else 0,
            "missing_indicators_count": len(GENUINE_MISSING_INDICATORS),
            "ordinal_count": len(ORDINAL_COLUMNS),
            "nominal_onehot_count": sum(len(lvl) for lvl in self.nominal_levels.values()),
        }

        self.is_fitted = True
        return self

    def transform(
        self,
        rows: Sequence[Mapping[str, Any]],
        split_name: str = "unspecified",
    ) -> TransformResult:
        """Transform any partition (train, val, or test) using strictly fitted parameters."""
        if not self.is_fitted:
            raise RuntimeError("Pipeline must be fitted before calling transform().")

        ids: list[str] = []
        y_vals: list[float] | None = []
        features_list: list[dict[str, float]] = []
        feature_matrix: list[list[float]] = []

        unseen_tracker: dict[str, dict[str, int]] = {}

        has_target_in_batch = any(TARGET_COLUMN in r for r in rows)

        for row in rows:
            # 1. Metadata and target isolation
            row_id = str(row.get(ID_COLUMN, ""))
            ids.append(row_id)

            if has_target_in_batch:
                t_val = row.get(TARGET_COLUMN)
                if not self._is_missing(t_val):
                    try:
                        y_vals.append(float(t_val))
                    except (ValueError, TypeError):
                        y_vals.append(float("nan"))
                else:
                    y_vals.append(float("nan"))

            # 2. Derive physical presence booleans
            g_type = row.get("GarageType")
            has_garage = 1.0 if not self._is_missing(g_type) and str(g_type).strip() not in ("None", "NA") else 0.0

            bsmt_qual = row.get("BsmtQual")
            tot_bsmt_sf = row.get("TotalBsmtSF")
            has_bsmt = 1.0
            if (self._is_missing(bsmt_qual) or str(bsmt_qual).strip() in ("None", "NA")) and (
                self._is_missing(tot_bsmt_sf) or str(tot_bsmt_sf).strip() in ("0", "0.0")
            ):
                has_bsmt = 0.0

            try:
                fp_count = float(row.get("Fireplaces", 0) or 0)
            except (ValueError, TypeError):
                fp_count = 0.0
            has_fireplace = 1.0 if fp_count > 0.0 or not self._is_missing(row.get("FireplaceQu")) else 0.0

            try:
                pool_area = float(row.get("PoolArea", 0) or 0)
            except (ValueError, TypeError):
                pool_area = 0.0
            has_pool = 1.0 if pool_area > 0.0 or not self._is_missing(row.get("PoolQC")) else 0.0

            has_fence = 0.0 if self._is_missing(row.get("Fence")) or str(row.get("Fence")).strip() in ("None", "NA") else 1.0
            has_alley = 0.0 if self._is_missing(row.get("Alley")) or str(row.get("Alley")).strip() in ("None", "NA") else 1.0
            has_misc = 0.0 if self._is_missing(row.get("MiscFeature")) or str(row.get("MiscFeature")).strip() in ("None", "NA") else 1.0

            row_feats: dict[str, float] = {}

            # 3. Numeric continuous & discrete features
            for col in NUMERIC_COLUMNS:
                raw_val = row.get(col)
                if col == "GarageYrBlt":
                    if has_garage == 0.0:
                        row_feats[col] = self.garage_sentinel_year
                    elif self._is_missing(raw_val):
                        row_feats[col] = self.numeric_impute_values[col]
                    else:
                        try:
                            row_feats[col] = float(raw_val)
                        except (ValueError, TypeError):
                            row_feats[col] = self.numeric_impute_values[col]
                else:
                    if self._is_missing(raw_val):
                        row_feats[col] = self.numeric_impute_values[col]
                    else:
                        try:
                            row_feats[col] = float(raw_val)
                        except (ValueError, TypeError):
                            row_feats[col] = self.numeric_impute_values[col]

            # 4. Structural indicators
            if self.add_structural_indicators:
                row_feats["HasGarage"] = has_garage
                row_feats["HasBasement"] = has_bsmt
                row_feats["HasFireplace"] = has_fireplace
                row_feats["HasPool"] = has_pool
                row_feats["HasFence"] = has_fence
                row_feats["HasAlley"] = has_alley
                row_feats["HasMiscFeature"] = has_misc

            # 4b. Explicit missingness indicators for genuine non-structural missing fields
            row_feats["MasVnrType_is_missing"] = 1.0 if self._is_missing(row.get("MasVnrType")) else 0.0
            row_feats["MasVnrArea_is_missing"] = 1.0 if self._is_missing(row.get("MasVnrArea")) else 0.0

            # 5. Ordinal features
            for col in ORDINAL_COLUMNS:
                raw_val = row.get(col)
                mapping = ORDINAL_LEVELS[col]
                if self._is_missing(raw_val):
                    if col in STRUCTURAL_ABSENCE_COLUMNS:
                        row_feats[col] = 0.0
                    else:
                        row_feats[col] = float(self.ordinal_impute_values[col])
                else:
                    val_str = str(raw_val).strip()
                    if val_str in mapping:
                        row_feats[col] = float(mapping[val_str])
                    elif val_str in ("None", "NA") and "None" in mapping:
                        row_feats[col] = float(mapping["None"])
                    else:
                        # Unknown ordinal level: fall back to training median score
                        row_feats[col] = float(self.ordinal_impute_values[col])

            # 6. Nominal features (one-hot with unknown-category support)
            for col in NOMINAL_COLUMNS:
                raw_val = row.get(col)
                sentinel = STRUCTURAL_NOMINAL_SENTINELS.get(col)

                if self._is_missing(raw_val):
                    val_str = sentinel if sentinel is not None else self.nominal_impute_values[col]
                else:
                    val_str = str(raw_val).strip()

                active_levels = self.nominal_levels[col]
                is_known = val_str in active_levels

                if not is_known and self.handle_unknown == "ignore":
                    # Track unseen category occurrence
                    if col not in unseen_tracker:
                        unseen_tracker[col] = {}
                    unseen_tracker[col][val_str] = unseen_tracker[col].get(val_str, 0) + 1

                for level in active_levels:
                    feat_name = f"{col}_{level}"
                    row_feats[feat_name] = 1.0 if (is_known and val_str == level) else 0.0

            # 7. Assemble row vector according to exact self.feature_names sequence
            row_vector: list[float] = [row_feats[fn] for fn in self.feature_names]

            features_list.append(row_feats)
            feature_matrix.append(row_vector)

        # Record unseen categories for logging and manifest reports
        unseen_records: list[dict[str, Any]] = []
        for col, counts in unseen_tracker.items():
            for val, cnt in counts.items():
                rec = {
                    "split_name": split_name,
                    "column": col,
                    "unseen_value": val,
                    "count": cnt,
                }
                unseen_records.append(rec)
                self.unseen_categories_encountered.append(rec)

        final_y = y_vals if has_target_in_batch else None

        return TransformResult(
            ids=ids,
            y=final_y,
            feature_names=self.feature_names,
            features=features_list,
            feature_matrix=feature_matrix,
            unseen_categories=unseen_records,
            split_name=split_name,
            n_rows=len(rows),
            n_features=len(self.feature_names),
        )

    def fit_transform(
        self,
        rows: Sequence[Mapping[str, Any]],
        split_name: str = "train",
    ) -> TransformResult:
        """Fit strictly on the given training rows and return transformed result."""
        return self.fit(rows).transform(rows, split_name=split_name)

    def get_feature_mapping(self) -> dict[str, Any]:
        """Return structured mapping of raw predictors to engineered features."""
        if not self.is_fitted:
            raise RuntimeError("Pipeline must be fitted first.")
        return {
            "summary": self.fit_summary,
            "feature_manifest": self.feature_manifest,
            "numeric_impute_values": self.numeric_impute_values,
            "nominal_impute_values": self.nominal_impute_values,
            "ordinal_impute_values": self.ordinal_impute_values,
            "nominal_levels": self.nominal_levels,
        }
