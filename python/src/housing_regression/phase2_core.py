"""Phase 2 synthetic CSV profiling with a fixed, conservative Ames taxonomy."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import statistics
from pathlib import Path
from typing import Any

from housing_regression.contracts import phase_schema_path, validate_document
from housing_regression.core_utils import PhaseCoreError, emit_json_artifact
from housing_regression.init_config import ConfigError, load_config


_FIELD_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_. -]{0,63}$")
_MISSING = {"", "na", "n/a", "nan", "null", "none"}

AMES_FIELD_TYPES = {
    **dict.fromkeys((
        "LotFrontage", "LotArea", "MasVnrArea", "BsmtFinSF1", "BsmtFinSF2", "BsmtUnfSF",
        "TotalBsmtSF", "1stFlrSF", "2ndFlrSF", "LowQualFinSF", "GrLivArea", "GarageArea",
        "WoodDeckSF", "OpenPorchSF", "EnclosedPorch", "3SsnPorch", "ScreenPorch", "PoolArea",
        "MiscVal", "YearBuilt", "YearRemodAdd", "GarageYrBlt",
    ), "continuous"),
    **dict.fromkeys((
        "BsmtFullBath", "BsmtHalfBath", "FullBath", "HalfBath", "BedroomAbvGr", "KitchenAbvGr",
        "TotRmsAbvGrd", "Fireplaces", "GarageCars", "MoSold", "YrSold",
    ), "discrete"),
    **dict.fromkeys((
        "OverallQual", "OverallCond", "ExterQual", "ExterCond", "BsmtQual", "BsmtCond",
        "BsmtExposure", "BsmtFinType1", "BsmtFinType2", "HeatingQC", "KitchenQual", "FireplaceQu",
        "GarageFinish", "GarageQual", "GarageCond", "PoolQC", "Fence", "Functional",
        "LotShape", "LandSlope",
    ), "ordinal"),
    **dict.fromkeys((
        "MSZoning", "Street", "Alley", "LotConfig", "Neighborhood", "Condition1", "Condition2",
        "BldgType", "HouseStyle", "RoofStyle", "RoofMatl", "Exterior1st", "Exterior2nd",
        "MasVnrType", "Foundation", "Heating", "CentralAir", "Electrical", "GarageType",
        "PavedDrive", "MiscFeature", "SaleType", "SaleCondition", "Utilities", "LandContour",
        "MSSubClass",
    ), "nominal"),
}


def _missing(value: str) -> bool:
    return value.strip().casefold() in _MISSING


def _format_number(value: float) -> int | float:
    rounded = round(value, 6)
    return int(rounded) if rounded.is_integer() else rounded


def _analysis(analysis_id: str, title: str, description: str, finding: str) -> dict[str, Any]:
    return {
        "id": analysis_id,
        "figure_id": f"figure-{analysis_id}",
        "title": title,
        "status": "MOCK",
        "image_ref": None,
        "table_ref": None,
        "description": description,
        "finding": finding,
        "limitations": (
            "MOCK from a synthetic CSV only; not an Ames research finding. "
            "Aggregate-only output; raw rows, row identifiers, and source paths are omitted."
        ),
        "provenance_ref": None,
    }


def _read_rows(
    config_path: Path, expected_sha: str, source_relative: str, target: str
) -> tuple[list[str], list[list[str]]]:
    source = config_path.parent / source_relative
    if source.is_symlink() or not source.is_file():
        raise PhaseCoreError("configured synthetic CSV is unavailable or unsafe")
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise PhaseCoreError("configured synthetic CSV cannot be read") from exc
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != expected_sha:
        raise PhaseCoreError("configured synthetic CSV SHA-256 changed")
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next(reader)
    except (UnicodeDecodeError, StopIteration, csv.Error) as exc:
        raise PhaseCoreError("synthetic CSV must have a valid UTF-8 header") from exc
    if not header or any(not column.strip() for column in header) or len(set(header)) != len(header):
        raise PhaseCoreError("synthetic CSV header must have unique non-empty columns")
    if any(not _FIELD_NAME.fullmatch(name) for name in header):
        raise PhaseCoreError("synthetic CSV has a field name outside the safe public-name pattern")
    if target not in header:
        raise PhaseCoreError("configured target is absent from the synthetic CSV")

    rows: list[list[str]] = []
    try:
        for line_number, row in enumerate(reader, start=2):
            if not row:
                continue
            if len(row) != len(header):
                raise PhaseCoreError(f"synthetic CSV has an invalid column count at line {line_number}")
            rows.append(row)
    except csv.Error as exc:
        raise PhaseCoreError("synthetic CSV has malformed quoting") from exc
    return header, rows


def build_phase2(
    config_path: str | os.PathLike[str],
    output_dir: str | os.PathLike[str],
) -> dict[str, Any]:
    """Write canonical ``analyses.json`` using synthetic-only aggregate profiling."""
    config_file = Path(config_path)
    try:
        config = load_config(config_file)
    except ConfigError as exc:
        raise PhaseCoreError("INIT config or source evidence is invalid") from exc
    data_config = config.values["data"]
    header, rows = _read_rows(
        config_file, config.source_sha256, data_config["path"], data_config["target"]
    )
    if not rows:
        document = {
            "schema_version": "1.0.0",
            "case_id": config.values["case_id"],
            "status": "UNAVAILABLE",
            "default_analysis_id": None,
            "analyses": [],
        }
        validate_document(document, phase_schema_path(2))
        emit_json_artifact(document, output_dir, "analyses.json")
        return document

    data_rows = {name: [] for name in header}
    for row in rows:
        for name, value in zip(header, row):
            data_rows[name].append(value)
    total_rows = len(rows)
    decisions: dict[str, tuple[str, str]] = {}
    numeric: dict[str, list[float]] = {}
    nominal_values: dict[str, set[str]] = {}
    invalid_numeric: set[str] = set()
    missing_counts = {name: sum(_missing(value) for value in data_rows[name]) for name in header}

    for name in header:
        if name == data_config["target"]:
            decisions[name] = ("target", "exclude")
        elif name.casefold() == "id":
            decisions[name] = ("identifier", "exclude")
        else:
            field_type = AMES_FIELD_TYPES.get(name, "unknown")
            if field_type == "unknown":
                decisions[name] = ("unknown", "exclude")
            else:
                decisions[name] = (field_type, "include")
                if field_type in ("continuous", "discrete"):
                    numeric[name] = []
                elif field_type == "nominal":
                    nominal_values[name] = set()

    for name, (field_type, decision) in decisions.items():
        if decision != "include":
            continue
        if field_type in ("continuous", "discrete"):
            for value in data_rows[name]:
                if _missing(value):
                    continue
                try:
                    numeric_value = float(value)
                except ValueError:
                    invalid_numeric.add(name)
                    break
                if not math.isfinite(numeric_value):
                    invalid_numeric.add(name)
                    break
                numeric[name].append(numeric_value)
        elif field_type == "nominal":
            nominal_values[name].update(value.strip() for value in data_rows[name] if not _missing(value))

    for name in invalid_numeric:
        decisions[name] = ("invalid_numeric", "exclude")

    decision_text = "; ".join(
        f"{name} [{kind}] {decision}"
        for name, (kind, decision) in decisions.items()
    ) or "No fields were present."
    missing_text = "; ".join(
        f"{name}={missing_counts[name]}/{total_rows}"
        for name in header
    ) or "No fields were present."
    numeric_summaries = []
    for name, values in numeric.items():
        if name in invalid_numeric or not values:
            continue
        numeric_summaries.append(
            f"{name}: n={len(values)}, min={_format_number(min(values))}, "
            f"median={_format_number(statistics.median(values))}, max={_format_number(max(values))}"
        )
    cardinalities = [f"{name}: {len(values)} distinct" for name, values in nominal_values.items()]
    summary_text = "; ".join(numeric_summaries + cardinalities) or "No supported included feature values."

    analyses = [
        _analysis(
            "field-decisions", "Field classification and feature decisions",
            "Fixed Ames field taxonomy; target and identifier are never features, and unknown columns are excluded.",
            decision_text,
        ),
        _analysis(
            "missingness", "Aggregate missingness",
            "Counts missing cells by field without exposing row values.",
            f"Rows={total_rows}; missing cells by field: {missing_text}",
        ),
        _analysis(
            "feature-summary", "Safe feature aggregates",
            "Numeric range summaries and nominal cardinalities for included features only.",
            summary_text,
        ),
    ]
    document = {
        "schema_version": "1.0.0",
        "case_id": config.values["case_id"],
        "status": "MOCK",
        "default_analysis_id": analyses[0]["id"],
        "analyses": analyses,
    }
    validate_document(document, phase_schema_path(2))
    emit_json_artifact(document, output_dir, "analyses.json")
    return document
