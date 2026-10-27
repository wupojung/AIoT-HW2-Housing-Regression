#!/usr/bin/env python3
"""Phase 6 inference for the serialized Ames Housing development model.

Examples:
    # No input: create an empty CSV template in the current directory.
    python tools/modeling/run_phase6_inference.py

    # JSON input: print a JSON prediction response to stdout.
    python tools/modeling/run_phase6_inference.py \
        --model path/to/model.joblib \
        --json '{"Id": 1, "LotArea": 8450, ...}'

    # CSV input: write a prediction CSV beside the input file by default.
    python tools/modeling/run_phase6_inference.py \
        --model path/to/model.joblib --input-csv houses.csv

JSON and CSV inputs must contain all Ames predictor columns. Individual values
may be blank; the fitted Phase 3 preprocessing pipeline handles missing values.
For CSV input, any existing SalePrice values are replaced in the new output file.
When labeled SalePrice values are present, an aggregate error summary JSON is also written.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "python" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from housing_regression.data_prep import ALL_PREDICTOR_COLUMNS, ID_COLUMN, TARGET_COLUMN  # noqa: E402
from housing_regression.phase6_inference import (  # noqa: E402
    load_model_bundle,
    predict_json_text,
    predict_records,
)


def _read_csv(input_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not input_path.is_file():
        raise FileNotFoundError(f"Input CSV does not exist: {input_path}")

    with input_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames
        if not headers:
            raise ValueError("Input CSV must have a header row.")
        if len(headers) != len(set(headers)):
            raise ValueError("Input CSV contains duplicate column names.")
        missing = sorted(set(ALL_PREDICTOR_COLUMNS) - set(headers))
        if missing:
            raise ValueError(f"Input CSV is missing required Ames predictor columns: {', '.join(missing)}")

        rows = []
        for line_number, row in enumerate(reader, start=2):
            if row is None or not any(value not in (None, "") for value in row.values()):
                continue
            if None in row:
                raise ValueError(f"Input CSV row {line_number} has more values than the header.")
            rows.append(dict(row))

    if not rows:
        raise ValueError("Input CSV contains no data rows.")
    return rows, headers


def _serialize_csv_template() -> bytes:
    headers = [ID_COLUMN, *ALL_PREDICTOR_COLUMNS]
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(headers)
    return stream.getvalue().encode("utf-8")


def _serialize_prediction_csv(
    input_rows: Sequence[Mapping[str, Any]],
    input_headers: Sequence[str],
    predictions: Sequence[Mapping[str, Any]],
) -> bytes:
    headers = list(input_headers)
    if TARGET_COLUMN not in headers:
        headers.append(TARGET_COLUMN)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=headers)
    writer.writeheader()
    for input_row, prediction in zip(input_rows, predictions):
        output_row = dict(input_row)
        output_row[TARGET_COLUMN] = prediction[TARGET_COLUMN]
        writer.writerow(output_row)
    return stream.getvalue().encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _commit_output_set(outputs: Mapping[Path, bytes | None], force: bool) -> None:
    """Commit related output files with rollback and atomic per-file replacements.

    A ``None`` payload removes a stale sidecar inside the same transaction.
    Existing outputs are backed up first so an ordinary write/rename failure can
    restore the complete previous output set.
    """
    normalized: dict[Path, bytes | None] = {}
    for path, payload in outputs.items():
        target = path.resolve()
        if target in normalized:
            raise ValueError("Output paths must be distinct.")
        normalized[target] = payload

    for target in normalized:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_dir():
            raise IsADirectoryError(f"Output path is a directory: {target}")
        if target.exists() and not force:
            raise FileExistsError(f"Output already exists: {target} (use --force to overwrite it)")

    temp_paths: dict[Path, Path] = {}
    backup_paths: dict[Path, Path] = {}
    committed: list[Path] = []
    try:
        for target, payload in normalized.items():
            if payload is None:
                continue
            fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.tmp-", dir=target.parent)
            temp_path = Path(temp_name)
            temp_paths[target] = temp_path
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())

        for target in normalized:
            if not target.exists():
                continue
            fd, backup_name = tempfile.mkstemp(prefix=f".{target.name}.bak-", dir=target.parent)
            os.close(fd)
            backup_path = Path(backup_name)
            backup_path.unlink()
            os.replace(target, backup_path)
            backup_paths[target] = backup_path

        for target, payload in normalized.items():
            if payload is None:
                if target in backup_paths:
                    committed.append(target)
                continue
            os.replace(temp_paths[target], target)
            committed.append(target)
    except Exception as exc:
        rollback_errors: list[str] = []
        for target in reversed(committed):
            try:
                target.unlink(missing_ok=True)
            except OSError as rollback_exc:
                rollback_errors.append(f"remove {target.name}: {rollback_exc}")
        for target, backup_path in backup_paths.items():
            if not backup_path.exists():
                continue
            try:
                os.replace(backup_path, target)
            except OSError as rollback_exc:
                rollback_errors.append(f"restore {target.name}: {rollback_exc}")
        if rollback_errors:
            raise RuntimeError(
                "Output transaction failed and automatic rollback was incomplete: "
                + "; ".join(rollback_errors)
            ) from exc
        raise RuntimeError("Output transaction failed; previous output files were restored.") from exc
    else:
        cleanup_errors: list[str] = []
        for backup_path in backup_paths.values():
            try:
                backup_path.unlink(missing_ok=True)
            except OSError as cleanup_exc:
                cleanup_errors.append(f"{backup_path.name}: {cleanup_exc}")
        if cleanup_errors:
            raise RuntimeError(
                "Outputs committed, but temporary backup cleanup failed: " + "; ".join(cleanup_errors)
            )
    finally:
        for temp_path in temp_paths.values():
            temp_path.unlink(missing_ok=True)


def _is_missing_actual(value: Any) -> bool:
    return value is None or str(value).strip().lower() in {"", "na", "nan", "null"}


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _build_evaluation_report(
    input_rows: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
    prediction_file: str,
    source_file_sha256: str,
    prediction_file_sha256: str,
    model_file_sha256: str,
    model_metadata: Mapping[str, Any],
) -> dict[str, Any] | None:
    actual_values: list[float] = []
    predicted_values: list[float] = []
    missing_actual_count = 0

    for row_index, (input_row, prediction) in enumerate(zip(input_rows, predictions), start=1):
        raw_actual = input_row.get(TARGET_COLUMN)
        if _is_missing_actual(raw_actual):
            missing_actual_count += 1
            continue
        try:
            actual = float(raw_actual)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"CSV row {row_index + 1} has a non-numeric {TARGET_COLUMN} value."
            ) from exc
        predicted = float(prediction[TARGET_COLUMN])
        if not math.isfinite(actual):
            raise ValueError(f"CSV row {row_index + 1} has a non-finite {TARGET_COLUMN} value.")
        actual_values.append(actual)
        predicted_values.append(predicted)

    if not actual_values:
        return None

    residuals = [actual - predicted for actual, predicted in zip(actual_values, predicted_values)]
    absolute_errors = [abs(residual) for residual in residuals]
    mae = sum(absolute_errors) / len(absolute_errors)
    rmse = math.sqrt(sum(residual * residual for residual in residuals) / len(residuals))
    actual_mean = sum(actual_values) / len(actual_values)
    total_sum_squares = sum((actual - actual_mean) ** 2 for actual in actual_values)
    if len(actual_values) < 2:
        r2 = None
        r2_status = "UNDEFINED_INSUFFICIENT_ROWS"
    elif total_sum_squares == 0:
        r2 = None
        r2_status = "UNDEFINED_CONSTANT_ACTUALS"
    else:
        r2 = 1.0 - sum(residual * residual for residual in residuals) / total_sum_squares
        r2_status = "COMPUTED"

    return {
        "report_type": "prediction_error_summary",
        "status": "LOCAL_DIAGNOSTIC_NOT_PHASE5",
        "target": {"column": TARGET_COLUMN, "unit": "USD"},
        "prediction_file": prediction_file,
        "prediction_file_sha256": prediction_file_sha256,
        "source": {
            "kind": "caller_supplied_labeled_csv",
            "source_id": f"sha256:{source_file_sha256}",
            "file_sha256": source_file_sha256,
            "rows_in_input": len(input_rows),
            "labeled_rows": len(actual_values),
            "authorization_status": "NOT_ASSESSED_BY_CLI",
            "population_independence_status": "NOT_ASSESSED_BY_CLI",
        },
        "model": {
            "run_id": model_metadata.get("run_id"),
            "artifact_type": model_metadata.get("artifact_type"),
            "code_head_commit": model_metadata.get("code_head_commit"),
            "artifact_sha256": model_file_sha256,
        },
        "evaluation_scope": {
            "population": "labeled rows present in caller-supplied CSV",
            "phase5_evaluation": False,
            "case_package_release_approved": False,
            "limitations": [
                "This is an inference-run diagnostic, not a canonical Phase 5 evaluation.",
                "The CLI does not verify data-use authorization or population independence.",
                "Do not publish or add this report to a Case Package without separate review.",
            ],
        },
        "counts": {
            "rows_predicted": len(input_rows),
            "rows_evaluated": len(actual_values),
            "rows_without_actual": missing_actual_count,
        },
        "metrics": {
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "r2_status": r2_status,
            "mean_prediction_minus_actual": -sum(residuals) / len(residuals),
            "residual_definition": "actual_minus_predicted",
        },
        "absolute_error_distribution": {
            "minimum": min(absolute_errors),
            "median": _quantile(absolute_errors, 0.50),
            "p90": _quantile(absolute_errors, 0.90),
            "p95": _quantile(absolute_errors, 0.95),
            "maximum": max(absolute_errors),
        },
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 6: predict SalePrice from JSON or CSV, create an input template, "
            "and report aggregate errors when CSV labels are available."
        )
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--json", help="One JSON object or a JSON array of objects.")
    input_group.add_argument("--input-csv", type=Path, help="CSV file containing Ames predictor fields.")
    parser.add_argument(
        "--model",
        type=Path,
        help="Path to a trusted Phase 4 joblib bundle (required for prediction).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file. JSON defaults to stdout; CSV defaults beside the input; template defaults to ./inference-input-template.csv.",
    )
    parser.add_argument("--force", action="store_true", help="Allow overwriting the selected output file.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.json is None and args.input_csv is None:
            output_path = args.output or Path.cwd() / "inference-input-template.csv"
            _commit_output_set({output_path: _serialize_csv_template()}, args.force)
            print(f"Input CSV template written: {output_path}")
            return 0

        if args.model is None:
            parser.error("--model is required when --json or --input-csv is provided.")
        model_path = args.model.resolve()
        model, model_metadata = load_model_bundle(model_path)
        model_file_sha256 = _sha256_file(model_path)

        if args.json is not None:
            response = predict_json_text(model, args.json)
            if args.output is None:
                print(response)
            else:
                json_output_path = args.output.resolve()
                if json_output_path == model_path:
                    raise ValueError("JSON output must not overwrite the model artifact.")
                _commit_output_set(
                    {json_output_path: (response + "\n").encode("utf-8")},
                    args.force,
                )
            return 0

        input_path = args.input_csv.resolve()
        rows, headers = _read_csv(input_path)
        rows_for_prediction = [
            {key: value for key, value in row.items() if key != TARGET_COLUMN}
            for row in rows
        ]
        result = predict_records(model, rows_for_prediction)
        predictions = result if isinstance(result, list) else [result]
        output_path = args.output or input_path.with_name(f"{input_path.stem}-predictions.csv")
        output_path = output_path.resolve()
        if output_path in {input_path, model_path}:
            raise ValueError("Prediction output must not overwrite the input CSV or model artifact.")
        replaced_count = sum(
            row.get(TARGET_COLUMN) not in (None, "")
            and str(row.get(TARGET_COLUMN)).strip() != ""
            for row in rows
        )
        input_sha256 = _sha256_file(input_path)
        prediction_payload = _serialize_prediction_csv(rows, headers, predictions)
        prediction_sha256 = hashlib.sha256(prediction_payload).hexdigest()
        evaluation_report = None
        if TARGET_COLUMN in headers:
            evaluation_report = _build_evaluation_report(
                rows,
                predictions,
                output_path.name,
                input_sha256,
                prediction_sha256,
                model_file_sha256,
                model_metadata,
            )
        evaluation_path = output_path.with_name(f"{output_path.stem}-evaluation.json")
        if evaluation_path.resolve() in {input_path, output_path.resolve()}:
            raise ValueError("Evaluation JSON path must be separate from the input and prediction files.")
        if evaluation_path.resolve() == model_path:
            raise ValueError("Evaluation JSON path must not overwrite the model artifact.")

        evaluation_payload = None
        if evaluation_report is not None:
            evaluation_payload = (
                json.dumps(evaluation_report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
            ).encode("utf-8")
        had_evaluation_report = evaluation_path.exists()
        output_set: dict[Path, bytes | None] = {output_path: prediction_payload}
        if evaluation_payload is not None or had_evaluation_report:
            output_set[evaluation_path] = evaluation_payload
        _commit_output_set(output_set, args.force)
        print(f"Predictions written: {output_path} ({len(predictions)} rows)")
        if replaced_count:
            print(
                f"NOTICE: Replaced existing {TARGET_COLUMN} values for {replaced_count} row(s) "
                "in the output CSV; the input file was left unchanged."
            )
        elif TARGET_COLUMN in headers:
            print(
                f"NOTICE: Wrote new predictions to the existing {TARGET_COLUMN} column; "
                "no prior values were overwritten. The input file was left unchanged."
            )
        else:
            print(f"NOTICE: Added a new {TARGET_COLUMN} prediction column; the input file was left unchanged.")
        if evaluation_report is not None:
            print(
                f"Evaluation summary written: {evaluation_path} "
                f"({evaluation_report['counts']['rows_evaluated']} labeled row(s))"
            )
        elif TARGET_COLUMN in headers:
            print(f"NOTICE: No non-missing {TARGET_COLUMN} values; no evaluation JSON was generated.")
        if evaluation_report is None and had_evaluation_report:
            print("NOTICE: Removed the stale evaluation summary for this prediction output.")
        return 0
    except (FileNotFoundError, FileExistsError, OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
