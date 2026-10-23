#!/usr/bin/env python3
"""Create a descriptive profile of authorized Kaggle Ames CSVs.

This script does not clean, transform, split, or fit models to the data.
Raw inputs must remain under ignored local/datasets/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import csv
import math
import re
import statistics
from pathlib import Path


EXPECTED = {"train.csv", "test.csv", "data_description.txt"}
TARGET = "SalePrice"
IDENTIFIER = "Id"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def profile_csv(path: Path, output_dir: Path) -> dict:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    values = {c: [row.get(c, "") for row in rows] for c in columns}
    missing = {c: sum(v is None or not v.strip() for v in vs) for c, vs in values.items()}
    predictors = [c for c in columns if c not in {TARGET, IDENTIFIER}]
    numeric_values = {}
    dtypes = {}
    for column, items in values.items():
        present = [v for v in items if v is not None and v.strip()]
        try:
            nums = [float(v) for v in present]
            numeric_values[column] = nums
            dtypes[column] = "numeric (inferred from non-empty values)"
        except ValueError:
            dtypes[column] = "categorical/text (inferred from non-empty values)"
    result = {
        "file": path.name,
        "sha256": sha256(path),
        "shape": {"rows": len(rows), "columns": len(columns)},
        "predictor_count_excluding_Id_and_target": len(predictors),
        "dtypes": dtypes,
        "missing": {
            "total_cells": sum(missing.values()),
            "columns": {k: v for k, v in missing.items() if v},
        },
        "duplicate_rows": len(rows) - len({tuple(row.get(c, "") for c in columns) for row in rows}),
        "id": {
            "present": IDENTIFIER in columns,
            "unique": len(set(values[IDENTIFIER])) == len(rows) if IDENTIFIER in columns else None,
            "missing": missing[IDENTIFIER] if IDENTIFIER in columns else None,
        },
        "categorical_cardinality": {
            c: len({v for v in values[c] if v is not None and v.strip()})
            for c in columns if c not in numeric_values
        },
        "missingness_patterns": _missingness_patterns(columns, rows),
    }
    if TARGET in numeric_values:
        target = numeric_values[TARGET]
        result["target"] = {
            "name": TARGET,
            "count": len(target),
            "missing": missing[TARGET],
            "min": min(target) if target else None,
            "median": statistics.median(target) if target else None,
            "mean": statistics.mean(target) if target else None,
            "max": max(target) if target else None,
            "skew": _skew(target),
        }
        if target:
            _write_histogram(output_dir / f"{path.stem}_saleprice_distribution.svg", target)

    result["numeric_summary"] = {
        c: _numeric_summary(v) for c, v in numeric_values.items() if c != IDENTIFIER
    }
    result["numeric_anomaly_candidates_iqr"] = {
        c: _iqr_candidates(v) for c, v in numeric_values.items() if c != IDENTIFIER
    }
    result["numeric_correlation_with_target"] = {}
    if TARGET in columns:
        result["numeric_correlation_with_target"] = {
            c: _paired_correlation(values[c], values[TARGET])
            for c in numeric_values if c not in {TARGET, IDENTIFIER}
        }
    return result


def _numeric_summary(values: list[float]) -> dict:
    if not values:
        return {"count": 0}
    ordered = sorted(values)
    return {"count": len(values), "mean": statistics.mean(values), "std": statistics.stdev(values) if len(values) > 1 else None,
            "min": ordered[0], "25%": _quantile(ordered, .25), "50%": statistics.median(ordered),
            "75%": _quantile(ordered, .75), "max": ordered[-1]}


def _quantile(values: list[float], q: float) -> float:
    pos = (len(values) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def _skew(values: list[float]) -> float | None:
    if len(values) < 3:
        return None
    mean = statistics.mean(values)
    sd = statistics.pstdev(values)
    return sum(((v - mean) / sd) ** 3 for v in values) / len(values) if sd else 0.0


def _paired_correlation(left_values: list[str], right_values: list[str]) -> float | None:
    pairs = [(float(a), float(b)) for a, b in zip(left_values, right_values) if a and a.strip() and b and b.strip()]
    left, right = [p[0] for p in pairs], [p[1] for p in pairs]
    if len(left) < 2 or len(set(left)) < 2 or len(set(right)) < 2:
        return None
    return statistics.correlation(left, right)


def _iqr_candidates(values: list[float]) -> dict:
    if len(values) < 4:
        return {"lower_fence": None, "upper_fence": None, "count": 0}
    ordered = sorted(values)
    q1, q3 = _quantile(ordered, .25), _quantile(ordered, .75)
    spread = q3 - q1
    lower, upper = q1 - 1.5 * spread, q3 + 1.5 * spread
    return {"lower_fence": lower, "upper_fence": upper,
            "count": sum(v < lower or v > upper for v in values)}


def _missingness_patterns(columns: list[str], rows: list[dict]) -> list[dict]:
    patterns = {}
    for row in rows:
        absent = tuple(c for c in columns if row.get(c) is None or not row[c].strip())
        if absent:
            patterns[absent] = patterns.get(absent, 0) + 1
    return [{"missing_fields": list(fields), "rows": count}
            for fields, count in sorted(patterns.items(), key=lambda item: (-item[1], item[0]))[:100]]


def _write_histogram(path: Path, values: list[float]) -> None:
    bins = 40
    low, high = min(values), max(values)
    counts = [0] * bins
    for value in values:
        index = min(bins - 1, int((value - low) / (high - low) * bins)) if high > low else 0
        counts[index] += 1
    scale = 220 / max(counts)
    bars = "".join(f'<rect x="{40+i*15}" y="{250-count*scale:.1f}" width="13" height="{count*scale:.1f}" fill="#4c78a8"/>\n' for i, count in enumerate(counts))
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="680" height="300"><text x="40" y="22">SalePrice distribution (descriptive)</text>{bars}<text x="40" y="280">{low:g}</text><text x="600" y="280">{high:g}</text></svg>\n')


def _safe_local_path(path: Path, local_root: Path, *, allow_root: bool = False) -> Path:
    local_root = local_root.absolute()
    if local_root.is_symlink():
        raise ValueError("The ignored local/ directory must not be a symlink.")
    resolved_root = local_root.resolve()
    resolved = path.absolute().resolve()
    if not resolved.is_relative_to(resolved_root) or (not allow_root and resolved == resolved_root):
        raise ValueError(f"Path must resolve inside ignored local/: {path}")
    return resolved


def _dictionary_crosswalk(columns: set[str], description_path: Path) -> dict:
    text = description_path.read_text(encoding="utf-8-sig", errors="replace")
    described = set(re.findall(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*:", text, re.MULTILINE))
    status = {}
    for name in sorted(columns):
        if name == IDENTIFIER:
            status[name] = "identifier"
        elif name == TARGET:
            status[name] = "target"
        elif name in described:
            status[name] = "definition_present"
        else:
            status[name] = "not_found_in_dictionary"
    return {
        "field_status": status,
        "dictionary_fields_not_in_train_schema": sorted(described - columns),
    }


def run(data_dir: Path, output_dir: Path, access_date: str, terms_confirmed: bool,
        local_root: Path | None = None) -> dict:
    if not terms_confirmed:
        raise ValueError("Confirm Kaggle login and applicable competition terms before profiling.")
    if local_root is None:
        local_root = Path(__file__).resolve().parents[2] / "local"
    if not local_root.exists() or not local_root.is_dir():
        raise ValueError("The ignored local/ directory must exist before profiling.")
    safe_data_dir = _safe_local_path(data_dir, local_root)
    if safe_data_dir != (local_root / "datasets").resolve() or safe_data_dir.is_symlink():
        raise ValueError("Input CSVs must be directly in ignored local/datasets/.")
    safe_output_dir = _safe_local_path(output_dir, local_root)
    if (safe_output_dir == safe_data_dir or safe_output_dir.is_relative_to(safe_data_dir)
            or safe_data_dir.is_relative_to(safe_output_dir)):
        raise ValueError("EDA outputs must stay outside local/datasets/.")
    missing = EXPECTED - {p.name for p in data_dir.iterdir() if p.is_file()}
    if missing:
        raise FileNotFoundError(f"Missing required Owner-provided files: {', '.join(sorted(missing))}")
    safe_output_dir.mkdir(parents=True, exist_ok=True)
    # Report is an aggregate public-safe candidate; keep it local until reviewed.
    profiles = [profile_csv(safe_data_dir / name, safe_output_dir) for name in ("train.csv", "test.csv")]
    train_columns = set(profiles[0]["dtypes"])
    test_columns = set(profiles[1]["dtypes"])
    with (safe_data_dir / "train.csv").open(newline="", encoding="utf-8-sig") as stream:
        train_ids = {row[IDENTIFIER] for row in csv.DictReader(stream) if row.get(IDENTIFIER)}
    with (safe_data_dir / "test.csv").open(newline="", encoding="utf-8-sig") as stream:
        test_ids = {row[IDENTIFIER] for row in csv.DictReader(stream) if row.get(IDENTIFIER)}
    report = {
        "status": "descriptive_profile_generated_pending_review",
        "source_url": "https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data",
        "access_date": access_date,
        "terms_confirmed_by_owner": True,
        "data_dictionary_sha256": sha256(safe_data_dir / "data_description.txt"),
        "data_dictionary_crosswalk": _dictionary_crosswalk(train_columns, safe_data_dir / "data_description.txt"),
        "schema_checks": {
            "training_target_present": TARGET in train_columns,
            "test_target_absent": TARGET not in test_columns,
            "train_predictor_columns_missing_from_test": sorted((train_columns - {TARGET}) - test_columns),
            "test_predictor_columns_missing_from_train": sorted(test_columns - (train_columns - {TARGET})),
            "original_predictor_count_at_least_14": profiles[0]["predictor_count_excluding_Id_and_target"] >= 14,
            "train_test_id_overlap_count": len(train_ids & test_ids),
        },
        "files": profiles,
        "limitations": ["Descriptive only; no cleaning, feature selection, splitting, or model fitting."],
    }
    (safe_output_dir / "profile.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("local/datasets"))
    parser.add_argument("--output-dir", type=Path, default=Path("local/research/phase2-eda"))
    parser.add_argument("--access-date", required=True, help="Owner-recorded Kaggle access/download date (YYYY-MM-DD).")
    parser.add_argument("--terms-confirmed", action="store_true", help="Owner confirms login and current competition terms.")
    args = parser.parse_args()
    result = run(args.data_dir, args.output_dir, args.access_date, args.terms_confirmed)
    print(json.dumps({"status": result["status"], "output": str(args.output_dir / "profile.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
