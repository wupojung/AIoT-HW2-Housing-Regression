"""Independent INIT B reference-baseline configuration and Ames preprocessing.

This module implements the frozen Phase 3 semantics in a new Core path. The
legacy pipeline remains a read-only comparison oracle during migration.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import statistics
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping, Sequence

import numpy as np
import yaml

from housing_regression.data_prep.constants import (
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
from housing_regression.init_config import _UniqueKeySafeLoader


REFERENCE_BASELINE_ID = "ames-reference-baseline-v1"
REFERENCE_RUN_ID = "initb-reference-20261028-01"
REFERENCE_TRAIN_ROWS = 1168
REFERENCE_VALIDATION_ROWS = 292
REFERENCE_RAW_PREDICTORS = 79
REFERENCE_FEATURES = 248
REFERENCE_SPLIT_SEED = 42
REFERENCE_OUTER_FOLDS = 3
REFERENCE_LASSO_ALPHA = 100.0
REFERENCE_TRAIN_SHA256 = "1e18addf81e5e4d347cc17ee6075bbe4a42b7fa26b9e5b063e8f692a5f929d41"


class ReferenceBaselineError(ValueError):
    """INIT B configuration or Phase 3 data did not satisfy the frozen baseline."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_config_sha(values: Mapping[str, Any]) -> str:
    canonical = dict(values)
    canonical.pop("provenance", None)
    payload = yaml.safe_dump(canonical, sort_keys=False, allow_unicode=False).encode("utf-8")
    return _sha256(payload)


def create_reference_config(
    train_csv: str | os.PathLike[str],
    config_dir: str | os.PathLike[str],
    historical_evidence: Mapping[str, str],
) -> Path:
    """Write a separate INIT B config from verified historical evidence.

    `historical_evidence` must identify the one source Run and its immutable
    aggregate/final-model evidence. The config is written once and never edits
    INIT A.
    """
    required_evidence = {
        "run_id", "manifest_sha256", "public_summary_sha256", "final_model_metadata_sha256",
    }
    if set(historical_evidence) != required_evidence or historical_evidence.get("run_id") != "development_20261026_01":
        raise ReferenceBaselineError("INIT B requires the exact historical Run ID and evidence SHA set")
    if any(
        not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value)
        for key, value in historical_evidence.items() if key != "run_id"
    ):
        raise ReferenceBaselineError("historical evidence digests must be lowercase SHA-256 values")

    source = Path(train_csv)
    if source.is_symlink() or not source.is_file():
        raise ReferenceBaselineError("INIT B requires a regular, non-symlink train.csv")
    source = source.resolve(strict=True)
    source_sha = _sha256(source.read_bytes())
    if source.name.lower() != "train.csv" or source_sha != REFERENCE_TRAIN_SHA256:
        raise ReferenceBaselineError("train.csv does not match the owner-verified Ames source fingerprint")

    output_dir = Path(config_dir)
    if output_dir.is_symlink() or not output_dir.is_dir():
        raise ReferenceBaselineError("INIT B config directory must exist and not be a symlink")
    config_path = output_dir / "reference-config.yaml"
    if config_path.exists() or config_path.is_symlink():
        raise ReferenceBaselineError("refusing to overwrite an existing INIT B configuration")
    try:
        source_relative = Path(os.path.relpath(source, output_dir.resolve())).as_posix()
    except ValueError as exc:
        raise ReferenceBaselineError("INIT B source and config must share a filesystem volume") from exc
    if Path(source_relative).is_absolute() or PureWindowsPath(source_relative).is_absolute() or PureWindowsPath(source_relative).drive:
        raise ReferenceBaselineError("INIT B source path must be relative")

    values: dict[str, Any] = {
        "schema_version": "1.0.0",
        "baseline_id": REFERENCE_BASELINE_ID,
        "case_id": "ames-housing-reference-baseline",
        "data": {"path": source_relative, "target": TARGET_COLUMN, "sha256": source_sha,
                 "raw_rows": 1460, "raw_columns": 81, "raw_predictors": REFERENCE_RAW_PREDICTORS},
        "phase2": {"operation": "raw_descriptive_eda", "imputation": "none", "split": "none"},
        "phase3": {
            "split": {"method": "python_random_index_permutation", "validation_fraction": 0.2,
                      "seed": REFERENCE_SPLIT_SEED, "training_rows": REFERENCE_TRAIN_ROWS,
                      "validation_rows": REFERENCE_VALIDATION_ROWS},
            "missing_tokens": ["", "NA"],
            "literal_none_is_category": True,
            "numeric_imputation": "training_median",
            "nominal_imputation": "training_mode",
            "ordinal_imputation": "median_of_training_mapped_scores",
            "structural_absence": "field_specific_none_or_zero_plus_presence_indicators",
            "genuine_missing_indicators": ["MasVnrType", "MasVnrArea"],
            "encoding": "ordinal_plus_training_level_one_hot",
            "outlier_policy": "retain_all_candidates",
            "expected_features": REFERENCE_FEATURES,
            "fit_population": "training_partition_only",
        },
        "phase4": {
            "historical_run_id": historical_evidence["run_id"],
            "protocol_version": "v2.0",
            "cv": {"kind": "KFold", "folds": REFERENCE_OUTER_FOLDS, "shuffle": True,
                   "seed": REFERENCE_SPLIT_SEED, "fold_fit_population": "fold_training_rows_only"},
            "configuration": {"method": "lasso", "alpha": REFERENCE_LASSO_ALPHA,
                              "max_iter": 10000, "tol": 0.0001, "selection": "cyclic",
                              "track": "selected_features_to_primary_ols",
                              "ols_solver": "numpy.linalg.lstsq_svd_minimum_norm"},
            "selection_search": "disabled_for_reference_reproduction",
        },
        "phase5": {"new_scientific_evaluation": "not_authorized_in_this_reference_run",
                   "historical_evaluation": "aggregate_comparison_only"},
        "phase6": {"deployment": "not_authorized", "inference_scope": "local_development_artifact_only"},
        "historical_evidence": {
            "manifest_sha256": historical_evidence["manifest_sha256"],
            "public_summary_sha256": historical_evidence["public_summary_sha256"],
            "final_model_metadata_sha256": historical_evidence["final_model_metadata_sha256"],
        },
        "provenance": {"init_config_sha256": ""},
    }
    values["provenance"]["init_config_sha256"] = _canonical_config_sha(values)
    payload = yaml.safe_dump(values, sort_keys=False, allow_unicode=False).encode("utf-8")
    try:
        with config_path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise ReferenceBaselineError("refusing to overwrite INIT B config") from exc
    except OSError as exc:
        raise ReferenceBaselineError("could not write INIT B config") from exc
    return config_path


@dataclass(frozen=True)
class ReferenceConfig:
    path: Path
    values: dict[str, Any]
    config_sha256: str
    source_csv: Path


def load_reference_config(config_path: str | os.PathLike[str]) -> ReferenceConfig:
    """Read INIT B without rewriting it and verify the exact source file digest."""
    path = Path(config_path)
    try:
        with path.open("r", encoding="utf-8") as stream:
            values = yaml.load(stream, Loader=_UniqueKeySafeLoader)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ReferenceBaselineError("INIT B YAML is missing or invalid") from exc
    if not isinstance(values, dict) or values.get("schema_version") != "1.0.0":
        raise ReferenceBaselineError("INIT B has an unsupported root or schema version")
    if values.get("baseline_id") != REFERENCE_BASELINE_ID or values.get("case_id") != "ames-housing-reference-baseline":
        raise ReferenceBaselineError("INIT B identity does not match the reference baseline")
    data = values.get("data")
    if not isinstance(data, dict) or data.get("target") != TARGET_COLUMN or data.get("raw_predictors") != REFERENCE_RAW_PREDICTORS:
        raise ReferenceBaselineError("INIT B target or raw predictor contract is invalid")
    stored_init_sha = values.get("provenance", {}).get("init_config_sha256")
    if not isinstance(stored_init_sha, str) or stored_init_sha != _canonical_config_sha(values):
        raise ReferenceBaselineError("INIT B fingerprint does not match its current values")
    source_rel = data.get("path")
    if (
        not isinstance(source_rel, str) or not source_rel or "\\" in source_rel
        or Path(source_rel).is_absolute() or PureWindowsPath(source_rel).is_absolute()
        or PureWindowsPath(source_rel).drive
    ):
        raise ReferenceBaselineError("INIT B source path must be relative and portable")
    source = (path.resolve(strict=True).parent / source_rel).resolve(strict=True)
    if source.is_symlink() or not source.is_file():
        raise ReferenceBaselineError("INIT B source must be a regular non-symlink file")
    actual_sha = _sha256(source.read_bytes())
    if actual_sha != data.get("sha256") or actual_sha != REFERENCE_TRAIN_SHA256:
        raise ReferenceBaselineError("INIT B source SHA-256 mismatch")
    return ReferenceConfig(path.resolve(), values, _canonical_config_sha(values), source)


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in ("", "NA")) or (
        isinstance(value, float) and math.isnan(value)
    )


def read_reference_csv(csv_path: str | os.PathLike[str]) -> tuple[list[str], list[dict[str, str]]]:
    """Read only the configured labeled CSV while preserving literal category `None`."""
    path = Path(csv_path)
    if path.name.lower() != "train.csv" or path.is_symlink() or not path.is_file():
        raise ReferenceBaselineError("Phase 3 accepts only a regular train.csv input")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if not reader.fieldnames:
                raise ReferenceBaselineError("train.csv has no header")
            headers = list(reader.fieldnames)
            rows = list(reader)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise ReferenceBaselineError("train.csv cannot be parsed") from exc
    if len(headers) != 81 or len(set(headers)) != len(headers) or len(rows) != 1460:
        raise ReferenceBaselineError("train.csv shape differs from the fixed Ames labeled source")
    if TARGET_COLUMN not in headers or ID_COLUMN not in headers:
        raise ReferenceBaselineError("train.csv must contain Id and SalePrice")
    if any(None in row for row in rows):
        raise ReferenceBaselineError("train.csv contains a row with the wrong number of columns")
    return headers, rows


@dataclass
class ReferenceBatch:
    ids: list[str]
    y: list[float] | None
    feature_names: list[str]
    matrix: np.ndarray

    @property
    def n_rows(self) -> int:
        return int(self.matrix.shape[0])

    @property
    def n_features(self) -> int:
        return int(self.matrix.shape[1])

    def to_numpy(self) -> np.ndarray:
        return self.matrix


class ReferencePhase3Pipeline:
    """Train-only Ames transform implemented independently for INIT B."""

    def __init__(self) -> None:
        self.fitted = False
        self.numeric_medians: dict[str, float] = {}
        self.nominal_modes: dict[str, str] = {}
        self.nominal_levels: dict[str, list[str]] = {}
        self.ordinal_medians: dict[str, int] = {}
        self.feature_names: list[str] = []

    def fit(self, rows: Sequence[Mapping[str, Any]]) -> "ReferencePhase3Pipeline":
        if not rows:
            raise ReferenceBaselineError("cannot fit Phase 3 on an empty training partition")
        for column in NUMERIC_COLUMNS:
            values: list[float] = []
            for row in rows:
                value = row.get(column)
                if _missing(value):
                    continue
                try:
                    number = float(value)
                except (TypeError, ValueError) as exc:
                    raise ReferenceBaselineError(f"non-numeric value in numeric field {column}") from exc
                if not math.isfinite(number):
                    raise ReferenceBaselineError(f"non-finite value in numeric field {column}")
                values.append(number)
            self.numeric_medians[column] = float(statistics.median(values)) if values else 0.0

        garage_years = []
        for row in rows:
            garage_type = row.get("GarageType")
            garage_year = row.get("GarageYrBlt")
            if not _missing(garage_type) and str(garage_type).strip() != "None" and not _missing(garage_year):
                garage_years.append(float(garage_year))
        if garage_years:
            self.numeric_medians["GarageYrBlt"] = float(statistics.median(garage_years))

        for column in NOMINAL_COLUMNS:
            sentinel = STRUCTURAL_NOMINAL_SENTINELS.get(column)
            counts: dict[str, int] = {}
            for row in rows:
                value = row.get(column)
                if _missing(value):
                    value = sentinel
                if value is not None:
                    label = str(value).strip()
                    counts[label] = counts.get(label, 0) + 1
            if not counts:
                raise ReferenceBaselineError(f"nominal field {column} has no training categories")
            self.nominal_modes[column] = min(counts, key=lambda key: (-counts[key], key))
            self.nominal_levels[column] = sorted(counts)

        for column in ORDINAL_COLUMNS:
            if column in STRUCTURAL_ABSENCE_COLUMNS:
                self.ordinal_medians[column] = 0
                continue
            mapping = ORDINAL_LEVELS[column]
            scores = [mapping[str(row[column]).strip()] for row in rows
                      if not _missing(row.get(column)) and str(row[column]).strip() in mapping]
            self.ordinal_medians[column] = int(round(statistics.median(scores))) if scores else 1

        self.feature_names = list(NUMERIC_COLUMNS) + list(STRUCTURAL_INDICATORS) + list(GENUINE_MISSING_INDICATORS)
        self.feature_names.extend(ORDINAL_COLUMNS)
        for column in NOMINAL_COLUMNS:
            self.feature_names.extend(f"{column}_{level}" for level in self.nominal_levels[column])
        self.fitted = True
        return self

    def _indicator_values(self, row: Mapping[str, Any]) -> dict[str, float]:
        def as_number(value: Any) -> float:
            try:
                return float(value) if not _missing(value) else 0.0
            except (TypeError, ValueError):
                return 0.0
        garage = not _missing(row.get("GarageType")) and str(row.get("GarageType")).strip() != "None"
        basement = not (
            (_missing(row.get("BsmtQual")) or str(row.get("BsmtQual")).strip() == "None")
            and (as_number(row.get("TotalBsmtSF")) == 0.0)
        )
        fireplace = as_number(row.get("Fireplaces")) > 0.0 or not _missing(row.get("FireplaceQu"))
        pool = as_number(row.get("PoolArea")) > 0.0 or not _missing(row.get("PoolQC"))
        return {
            "HasGarage": float(garage), "HasBasement": float(basement),
            "HasFireplace": float(fireplace), "HasPool": float(pool),
            "HasFence": float(not _missing(row.get("Fence")) and str(row.get("Fence")).strip() != "None"),
            "HasAlley": float(not _missing(row.get("Alley")) and str(row.get("Alley")).strip() != "None"),
            "HasMiscFeature": float(not _missing(row.get("MiscFeature")) and str(row.get("MiscFeature")).strip() != "None"),
        }

    def fit_transform(self, rows: Sequence[Mapping[str, Any]], split_name: str = "train") -> ReferenceBatch:
        self.fit(rows)
        return self.transform(rows, split_name)

    def transform(self, rows: Sequence[Mapping[str, Any]], split_name: str = "transform") -> ReferenceBatch:
        if not self.fitted:
            raise ReferenceBaselineError("Phase 3 pipeline must be fit on training rows first")
        matrix: list[list[float]] = []
        ids: list[str] = []
        targets: list[float] | None = [] if any(TARGET_COLUMN in row for row in rows) else None
        for row in rows:
            ids.append(str(row.get(ID_COLUMN, "")))
            if targets is not None:
                try:
                    targets.append(float(row[TARGET_COLUMN]))
                except (TypeError, ValueError) as exc:
                    raise ReferenceBaselineError("SalePrice must be present and numeric") from exc
            indicators = self._indicator_values(row)
            encoded: dict[str, float] = {}
            for column in NUMERIC_COLUMNS:
                value = row.get(column)
                if column == "GarageYrBlt" and indicators["HasGarage"] == 0.0:
                    encoded[column] = 0.0
                elif _missing(value):
                    encoded[column] = self.numeric_medians[column]
                else:
                    try:
                        encoded[column] = float(value)
                    except (TypeError, ValueError) as exc:
                        raise ReferenceBaselineError(f"non-numeric value in numeric field {column}") from exc
            encoded.update(indicators)
            for column in GENUINE_MISSING_INDICATORS:
                raw_column = column.removesuffix("_is_missing")
                encoded[column] = float(_missing(row.get(raw_column)))
            for column in ORDINAL_COLUMNS:
                value = row.get(column)
                mapping = ORDINAL_LEVELS[column]
                if _missing(value):
                    score = 0 if column in STRUCTURAL_ABSENCE_COLUMNS else self.ordinal_medians[column]
                else:
                    label = str(value).strip()
                    if label not in mapping:
                        raise ReferenceBaselineError(f"unknown ordinal category in {column}")
                    score = mapping[label]
                encoded[column] = float(score)
            for column in NOMINAL_COLUMNS:
                value = row.get(column)
                if _missing(value):
                    value = STRUCTURAL_NOMINAL_SENTINELS.get(column, self.nominal_modes[column])
                label = str(value).strip()
                for level in self.nominal_levels[column]:
                    encoded[f"{column}_{level}"] = float(label == level)
            values = [encoded[name] for name in self.feature_names]
            if not all(math.isfinite(value) for value in values):
                raise ReferenceBaselineError("Phase 3 transform produced a non-finite feature")
            matrix.append(values)
        result = np.asarray(matrix, dtype=np.float64)
        if result.shape != (len(rows), len(self.feature_names)):
            raise ReferenceBaselineError("Phase 3 output matrix shape is inconsistent")
        return ReferenceBatch(ids, targets, list(self.feature_names), result)


def split_reference_rows(
    rows: Sequence[Mapping[str, str]], validation_fraction: float = 0.2, seed: int = REFERENCE_SPLIT_SEED
) -> tuple[list[int], list[int]]:
    """Return natural-order train/validation indices from the documented seeded permutation."""
    if len(rows) != 1460 or validation_fraction != 0.2 or seed != REFERENCE_SPLIT_SEED:
        raise ReferenceBaselineError("INIT B split requires 1,460 rows, 80/20, and seed 42")
    shuffled = list(range(len(rows)))
    random.Random(seed).shuffle(shuffled)
    training_size = int(round(len(rows) * (1.0 - validation_fraction)))
    training_set = set(shuffled[:training_size])
    validation_set = set(shuffled[training_size:])
    if training_set & validation_set or training_set | validation_set != set(range(len(rows))):
        raise ReferenceBaselineError("train/validation split membership is invalid")
    return sorted(training_set), sorted(validation_set)


def _membership_digest(indices: Sequence[int]) -> str:
    return _sha256(",".join(map(str, indices)).encode("ascii"))


def _feature_digest(names: Sequence[str]) -> str:
    return _sha256(json.dumps(list(names), ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def run_reference_phase3(config_path: str | os.PathLike[str]) -> dict[str, Any]:
    """Execute INIT B split and train-only transforms without persisting row data."""
    config = load_reference_config(config_path)
    headers, rows = read_reference_csv(config.source_csv)
    source_sha = _sha256(config.source_csv.read_bytes())
    if source_sha != config.values["data"]["sha256"]:
        raise ReferenceBaselineError("Phase 3 source changed after INIT B")
    if len([column for column in headers if column not in (ID_COLUMN, TARGET_COLUMN)]) != REFERENCE_RAW_PREDICTORS:
        raise ReferenceBaselineError("Phase 3 raw predictor count differs from INIT B")

    train_indices, validation_indices = split_reference_rows(rows)
    train_rows = [rows[index] for index in train_indices]
    validation_rows = [rows[index] for index in validation_indices]
    train_ids = [row[ID_COLUMN] for row in train_rows]
    validation_ids = [row[ID_COLUMN] for row in validation_rows]
    if len(set(train_ids + validation_ids)) != len(rows) or set(train_ids) & set(validation_ids):
        raise ReferenceBaselineError("Phase 3 split IDs are not unique and disjoint")

    pipeline = ReferencePhase3Pipeline()
    train_batch = pipeline.fit_transform(train_rows, "development_train")
    validation_batch = pipeline.transform(validation_rows, "validation_transform_only")
    train_missing = int(np.isnan(train_batch.matrix).sum())
    validation_missing = int(np.isnan(validation_batch.matrix).sum())

    # Read-only compatibility comparison: the new transformer is the result;
    # the legacy implementation is used only to identify behavior differences.
    from housing_regression.data_prep import AmesDataPreparationPipeline
    legacy = AmesDataPreparationPipeline().fit(train_rows)
    legacy_train = legacy.transform(train_rows, split_name="legacy_compare_train").to_numpy()
    legacy_validation = legacy.transform(validation_rows, split_name="legacy_compare_validation").to_numpy()
    same_names = pipeline.feature_names == legacy.feature_names
    train_equal = same_names and np.array_equal(train_batch.matrix, legacy_train)
    validation_equal = same_names and np.array_equal(validation_batch.matrix, legacy_validation)
    train_max_abs_difference = (
        float(np.max(np.abs(train_batch.matrix - legacy_train))) if same_names else None
    )
    validation_max_abs_difference = (
        float(np.max(np.abs(validation_batch.matrix - legacy_validation))) if same_names else None
    )

    from housing_regression.modeling.p4b_runner import compute_canonical_fingerprint
    development_digest = compute_canonical_fingerprint(train_rows)
    development_id_digest = _sha256(json.dumps(train_ids, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return {
        "status": "PASS" if train_batch.matrix.shape[1] == REFERENCE_FEATURES and train_missing == 0 and validation_missing == 0 else "FAIL",
        "config_sha256": config.config_sha256,
        "source_sha256": source_sha,
        "rows": len(rows), "columns": len(headers), "raw_predictors": len(headers) - 2,
        "training_rows": len(train_rows), "validation_rows": len(validation_rows),
        "training_index_sha256": _membership_digest(train_indices),
        "validation_index_sha256": _membership_digest(validation_indices),
        "development_data_sha256": development_digest,
        "development_id_membership_sha256": development_id_digest,
        "features": train_batch.n_features, "feature_names_sha256": _feature_digest(train_batch.feature_names),
        "training_matrix_shape": list(train_batch.matrix.shape),
        "validation_matrix_shape": list(validation_batch.matrix.shape),
        "training_missing_after_transform": train_missing,
        "validation_missing_after_transform": validation_missing,
        "fit_population": "development_train_only",
        "outlier_candidate_rows_retained": len(train_batch.y or []) + len(validation_batch.y or []),
        "legacy_pipeline_comparison": {
            "feature_names_match": same_names,
            "training_matrix_exact_match": bool(train_equal),
            "validation_matrix_exact_match": bool(validation_equal),
            "training_max_abs_difference": train_max_abs_difference,
            "validation_max_abs_difference": validation_max_abs_difference,
        },
        "learned_parameter_sha256": _sha256(json.dumps({
            "numeric_medians": pipeline.numeric_medians,
            "nominal_modes": pipeline.nominal_modes,
            "nominal_levels": pipeline.nominal_levels,
            "ordinal_medians": pipeline.ordinal_medians,
        }, sort_keys=True, separators=(",", ":")).encode("utf-8")),
    }


def run_fixed_lasso_cv(
    config_path: str | os.PathLike[str], *, code_head: str, run_id: str = REFERENCE_RUN_ID
) -> dict[str, Any]:
    """Run only the historically selected Lasso alpha=100 primary-OLS track.

    This executes exactly three fixed outer folds on the 1,168 Development rows;
    it does not enumerate or compare any other candidate configuration.
    """
    config = load_reference_config(config_path)
    headers, rows = read_reference_csv(config.source_csv)
    train_indices, _validation_indices = split_reference_rows(rows)
    development_rows = [rows[index] for index in train_indices]
    if len(development_rows) != REFERENCE_TRAIN_ROWS:
        raise ReferenceBaselineError("fixed Phase 4 input is not the 1,168-row Development partition")
    from sklearn.linear_model import Lasso
    from sklearn.model_selection import KFold
    from sklearn.preprocessing import StandardScaler
    from threadpoolctl import threadpool_limits
    from housing_regression.modeling.ols_cv import fold_assignment_digest, kfold_assignments
    from housing_regression.modeling.p4b_runner import compute_canonical_fingerprint

    fold_labels = kfold_assignments(len(development_rows), REFERENCE_OUTER_FOLDS, REFERENCE_SPLIT_SEED)
    fold_sha = fold_assignment_digest(fold_labels)
    data_sha = compute_canonical_fingerprint(development_rows)
    fold_results: list[dict[str, Any]] = []
    with threadpool_limits(limits=1):
        splitter = KFold(n_splits=REFERENCE_OUTER_FOLDS, shuffle=True, random_state=REFERENCE_SPLIT_SEED)
        for fold, (train_positions, validation_positions) in enumerate(splitter.split(development_rows)):
            train_records = [development_rows[int(index)] for index in train_positions]
            validation_records = [development_rows[int(index)] for index in validation_positions]
            fold_pipeline = ReferencePhase3Pipeline()
            train_batch = fold_pipeline.fit_transform(train_records, "fold_train")
            validation_batch = fold_pipeline.transform(validation_records, "fold_validation")
            X_train, X_validation = train_batch.matrix.copy(), validation_batch.matrix.copy()
            feature_names = train_batch.feature_names
            # Match the protocol: scale numeric/ordinal inputs on fold-train only;
            # keep one-hot and physical/missing indicators as 0/1 values.
            scale_columns = [
                index for index, name in enumerate(feature_names)
                if name not in STRUCTURAL_INDICATORS
                and not name.endswith("_is_missing")
                and not any(name.startswith(column + "_") for column in NOMINAL_COLUMNS)
            ]
            if scale_columns:
                scaler = StandardScaler()
                X_train[:, scale_columns] = scaler.fit_transform(X_train[:, scale_columns])
                X_validation[:, scale_columns] = scaler.transform(X_validation[:, scale_columns])
            y_train = np.asarray(train_batch.y, dtype=np.float64)
            y_validation = np.asarray(validation_batch.y, dtype=np.float64)
            lasso = Lasso(alpha=REFERENCE_LASSO_ALPHA, max_iter=10000, tol=1e-4, selection="cyclic")
            lasso.fit(X_train, y_train)
            selected = np.flatnonzero(np.abs(lasso.coef_) > 1e-8)
            if not len(selected) or not np.isfinite(lasso.coef_).all():
                raise ReferenceBaselineError("fixed Lasso did not produce a finite nonempty feature set")
            design_train = np.column_stack((np.ones(len(X_train)), X_train[:, selected]))
            design_validation = np.column_stack((np.ones(len(X_validation)), X_validation[:, selected]))
            coefficients, _residuals, rank, singular_values = np.linalg.lstsq(design_train, y_train, rcond=None)
            predictions = design_validation @ coefficients
            residual = y_validation - predictions
            rmse = float(np.sqrt(np.mean(np.square(residual))))
            mae = float(np.mean(np.abs(residual)))
            total = float(np.sum(np.square(y_validation - np.mean(y_validation))))
            r2 = float(1.0 - np.sum(np.square(residual)) / total) if total else None
            task_identity = {"run_id": run_id, "method": "lasso",
                             "candidate": {"alpha": REFERENCE_LASSO_ALPHA, "candidate_order": 3},
                             "fold": fold}
            fold_results.append({
                "fold": fold,
                "validation_rows": len(validation_positions),
                "status": "COMPLETED",
                "convergence_status": "CONVERGED" if int(lasso.n_iter_) < lasso.max_iter else "ITERATION_LIMIT_REACHED",
                "selected_feature_count": int(len(selected)),
                "ols_rank": int(rank),
                "ols_nullity": int(len(selected) + 1 - rank),
                "rmse": rmse, "mae": mae, "r2": r2,
                "task_id": _sha256(json.dumps(task_identity, sort_keys=True).encode("utf-8")),
                "max_ols_singular_value": float(singular_values[0]) if len(singular_values) else None,
            })
    if any(item["status"] != "COMPLETED" or item["convergence_status"] != "CONVERGED" for item in fold_results):
        raise ReferenceBaselineError("a fixed Lasso alpha=100 fold was not completed")
    rmse = [item["rmse"] for item in fold_results]
    mae = [item["mae"] for item in fold_results]
    r2 = [item["r2"] for item in fold_results]
    return {
        "run_id": run_id,
        "config_sha256": config.config_sha256,
        "code_head": code_head,
        "data_sha256": data_sha,
        "fold_sha256": fold_sha,
        "protocol": {"version": "v2.0", "method": "lasso", "alpha": REFERENCE_LASSO_ALPHA,
                     "primary_track": "selected_features_to_ols", "folds": REFERENCE_OUTER_FOLDS,
                     "seed": REFERENCE_SPLIT_SEED, "workers": 1, "threads": 1},
        "candidate_search": "NOT RUN",
        "fold_results": fold_results,
        "mean_fold_metrics": {
            "rmse": float(np.mean(rmse)), "rmse_sample_sd": float(np.std(rmse, ddof=1)),
            "mae": float(np.mean(mae)), "mae_sample_sd": float(np.std(mae, ddof=1)),
            "r2": float(np.mean(r2)), "r2_sample_sd": float(np.std(r2, ddof=1)),
        },
    }
