"""Synthetic-only Phase 5 Evaluation exporter.

This CLI never discovers data or reads anything outside an explicit gate allowlist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import socket
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA_PATH = Path(__file__).with_name("evaluation-index.schema.json")
METRIC_NAMES = ("mae", "rmse", "r2")
FIGURE_IDS = ("FIG-P5-01", "FIG-P5-02", "FIG-P5-03")


class CliError(Exception):
    def __init__(self, code: str, message: str, exit_code: int = 3) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CliError("INVALID_INPUT", f"cannot read {label}: {exc}", 3) from exc
    if not isinstance(value, dict):
        raise CliError("INVALID_INPUT", f"{label} must be a JSON object", 3)
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise CliError("INVALID_INPUT", f"cannot read source file: {exc}", 3) from exc
    return digest.hexdigest()


def _safe_relative(value: Any, *, label: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise CliError("PATH_BLOCKED", f"{label} must be a non-empty forward-slash relative path")
    path = Path(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise CliError("PATH_BLOCKED", f"{label} must not be absolute or traverse directories")
    if ":" in value:
        raise CliError("PATH_BLOCKED", f"{label} must not contain a drive or URL scheme")
    return path


def _resolve_allowlisted_source(manifest_path: Path, manifest: dict[str, Any], gate: dict[str, Any]) -> tuple[Path, str]:
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise CliError("INVALID_INPUT", "synthetic manifest needs a source object")
    relative = _safe_relative(source.get("path"), label="source.path")
    claimed_digest = source.get("sha256")
    if not isinstance(claimed_digest, str) or len(claimed_digest) != 64:
        raise CliError("HASH_MISMATCH", "source.sha256 must be a SHA-256 hex digest")
    try:
        int(claimed_digest, 16)
    except ValueError as exc:
        raise CliError("HASH_MISMATCH", "source.sha256 must be hexadecimal") from exc

    input_root_value = gate.get("input_root")
    if not isinstance(input_root_value, str) or not input_root_value:
        raise CliError("NOT_AUTHORIZED", "gate.input_root is required")
    input_root = Path(input_root_value).expanduser().resolve(strict=True)
    if not input_root.is_dir():
        raise CliError("NOT_AUTHORIZED", "gate.input_root must be an existing directory")

    # The manifest path is relative to the manifest directory, and must resolve to
    # the exact same allowlisted relative path beneath the approved input root.
    manifest_root = manifest_path.parent.resolve(strict=True)
    if manifest_root != input_root:
        raise CliError("NOT_AUTHORIZED", "manifest must reside directly under gate.input_root")
    candidate = manifest_root / relative
    cursor = manifest_root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise CliError("PATH_BLOCKED", "source path may not traverse symlinks")
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(input_root)
    except ValueError as exc:
        raise CliError("PATH_BLOCKED", "source path escapes gate.input_root") from exc
    if not resolved.is_file():
        raise CliError("INVALID_INPUT", "source path must be a regular file")

    allowlist = gate.get("input_allowlist")
    if not isinstance(allowlist, list):
        raise CliError("NOT_AUTHORIZED", "gate.input_allowlist must be a list")
    matching = [
        item for item in allowlist
        if isinstance(item, dict) and item.get("path") == relative.as_posix()
    ]
    if len(matching) != 1:
        raise CliError("NOT_AUTHORIZED", "source must appear exactly once in gate.input_allowlist")
    allowed_digest = matching[0].get("sha256")
    actual_digest = _sha256(resolved)
    if allowed_digest != claimed_digest or actual_digest != claimed_digest:
        raise CliError("HASH_MISMATCH", "source digest does not match manifest, gate, and file")
    if manifest.get("mode") != "synthetic" or source.get("kind") != "synthetic_prediction_pairs":
        raise CliError("NOT_AUTHORIZED", "only explicitly marked synthetic prediction pairs are accepted")
    return resolved, actual_digest


def _validate_gate(manifest_path: Path, manifest: dict[str, Any], gate: dict[str, Any],
                   output_root_arg: str, operation: str) -> Path:
    if gate.get("authorized") is not True or gate.get("mode") != "synthetic_only":
        raise CliError("NOT_AUTHORIZED", "gate must explicitly authorize synthetic_only processing")
    if not isinstance(gate.get("gate_id"), str) or not gate["gate_id"]:
        raise CliError("NOT_AUTHORIZED", "gate.gate_id is required")
    operations = gate.get("allowed_operations")
    if not isinstance(operations, list) or operation not in operations:
        raise CliError("NOT_AUTHORIZED", f"gate does not allow operation {operation!r}")

    host = gate.get("host")
    if not isinstance(host, dict):
        raise CliError("NOT_AUTHORIZED", "gate.host is required")
    input_root_value = gate.get("input_root")
    if not isinstance(input_root_value, str) or not input_root_value:
        raise CliError("NOT_AUTHORIZED", "gate.input_root is required")
    input_root = Path(input_root_value).expanduser().resolve(strict=True)
    if not input_root.is_dir():
        raise CliError("NOT_AUTHORIZED", "gate.input_root must be an existing directory")
    manifest_root = manifest_path.parent.resolve(strict=True)
    if manifest_root != input_root:
        raise CliError("NOT_AUTHORIZED", "manifest must reside directly under gate.input_root")

    actual_platform = {"darwin": "macos", "win32": "windows"}.get(sys.platform, sys.platform)
    if host.get("platform") != actual_platform:
        raise CliError("HOST_MISMATCH", "gate host platform does not match this runtime")
    if host.get("host_id") != socket.gethostname():
        raise CliError("HOST_MISMATCH", "gate host identity does not match this runtime")
    actual_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if host.get("python_version") != actual_python:
        raise CliError("HOST_MISMATCH", "gate Python version does not match this runtime")
    if host.get("python_executable") != str(Path(sys.executable).resolve()):
        raise CliError("HOST_MISMATCH", "gate Python executable does not match this runtime")

    output_root = Path(output_root_arg).expanduser().resolve(strict=True)
    allowed_root_value = gate.get("output_root")
    if not isinstance(allowed_root_value, str) or not allowed_root_value:
        raise CliError("NOT_AUTHORIZED", "gate.output_root is required")
    allowed_root = Path(allowed_root_value).expanduser().resolve(strict=True)
    if not output_root.is_dir() or output_root != allowed_root:
        raise CliError("PATH_BLOCKED", "--output-root must exactly match the existing gate.output_root directory")
    if manifest.get("manifest_version") != 1:
        raise CliError("INVALID_INPUT", "manifest_version must be 1")
    if manifest.get("case_id") is None:
        raise CliError("INVALID_INPUT", "manifest.case_id is required")
    return output_root


def _metric_values(pairs: list[tuple[float, float]]) -> dict[str, float | None]:
    if not pairs:
        raise CliError("INVALID_INPUT", "at least one prediction pair is required")
    actual = [pair[0] for pair in pairs]
    predicted = [pair[1] for pair in pairs]
    if any(not math.isfinite(value) for value in actual + predicted):
        raise CliError("INVALID_INPUT", "actual and predicted values must be finite")
    residuals = [y - yhat for y, yhat in pairs]
    try:
        mae = sum(abs(value) for value in residuals) / len(residuals)
        rmse = math.sqrt(sum(value * value for value in residuals) / len(residuals))
        mean_y = sum(actual) / len(actual)
        total = sum((value - mean_y) ** 2 for value in actual)
        r2 = None if total == 0 else 1.0 - sum(value * value for value in residuals) / total
    except OverflowError as exc:
        raise CliError("INVALID_INPUT", "synthetic metric calculation overflowed") from exc
    if not math.isfinite(mae) or not math.isfinite(rmse):
        raise CliError("INVALID_INPUT", "synthetic metric calculation is non-finite")
    if r2 is not None and not math.isfinite(r2):
        r2 = None
    return {"mae": mae, "rmse": rmse, "r2": r2}


def _mock_metric(value: float | None, digest: str, name: str) -> dict[str, Any]:
    if value is None or not math.isfinite(value):
        return {
            "value": None,
            "status": "UNAVAILABLE",
            "reason_code": "SYNTHETIC_METRIC_UNDEFINED",
            "evidence_ref": None,
        }
    return {
        "value": value,
        "status": "MOCK",
        "reason_code": "SYNTHETIC_ONLY_NOT_EMPIRICAL",
        "evidence_ref": f"synthetic-fixture:{digest}:{name}",
    }


def _figure_slots(evaluation_id: str, configuration_id: str, n: int,
                  prediction_origin: str, unit: str, digest: str) -> list[dict[str, Any]]:
    common = {
        "evaluation_id": evaluation_id,
        "configuration_id": configuration_id,
        "evaluation_population": "development_oof",
        "prediction_origin": prediction_origin,
        "n": n,
        "status": "UNAVAILABLE",
        "publication_review": "PENDING",
        "asset_ref": None,
        "sha256": None,
        "accessible_table_ref": None,
        "alt": None,
        "finding": None,
        "limitations": ["SYNTHETIC METADATA ONLY; NO FIGURE ASSET OR EMPIRICAL DATA"],
        "source_digest": digest,
    }
    axes = {
        "FIG-P5-01": {
            "x": {"field": "actual", "label": "Actual", "unit": unit},
            "y": {"field": "predicted", "label": "Predicted", "unit": unit},
            "reference_line": "y_equals_x",
        },
        "FIG-P5-02": {
            "x": {"field": "predicted", "label": "Predicted", "unit": unit},
            "y": {"field": "actual_minus_predicted", "label": "Actual - Predicted", "unit": unit},
            "reference_line": "y_equals_0",
        },
        "FIG-P5-03": {
            "x": {"field": "actual_minus_predicted", "label": "Residual", "unit": unit},
            "y": {"field": "count", "label": "Count", "unit": "count"},
            "reference_line": "x_equals_0",
        },
    }
    figures = []
    for figure_id in FIGURE_IDS:
        item = dict(common)
        item.update({
            "figure_id": figure_id,
            "axes": axes[figure_id],
            "residual_sign": "actual_minus_predicted" if figure_id != "FIG-P5-01" else None,
            "histogram": {
                "bin_count": 5,
                "bin_edges_ref": f"synthetic-only-fixed-bins:{digest}",
                "n": n,
            } if figure_id == "FIG-P5-03" else None,
        })
        figures.append(item)
    return figures


def _base_evaluation(evaluation_id: str, manifest: dict[str, Any], n: int,
                     metrics: dict[str, float | None], digest: str,
                     metric_source: str, fold_summary: dict[str, Any] | None,
                     linked: list[str]) -> dict[str, Any]:
    target = manifest["target"]
    return {
        "evaluation_id": evaluation_id,
        "execution_run_id": manifest["execution_run_id"],
        "configuration_id": manifest["configuration_id"],
        "final_fit_id": None,
        "model_id": None,
        "model_version": None,
        "evaluation_population": "development_oof",
        "prediction_origin": manifest["prediction_origin"],
        "metric_source": metric_source,
        "n": n,
        "target": {"column": target["column"], "unit": target["unit"]},
        "metrics": {name: _mock_metric(metrics[name], digest, name) for name in METRIC_NAMES},
        "fold_summary": fold_summary,
        "figures": [],
        "interval": {
            "int_f": {
                "status": "UNAVAILABLE",
                "reason_code": "SYNTHETIC_ONLY_NO_METHOD_REVIEW",
                "method": None,
                "assumptions_ref": None,
            },
            "int_s": {
                "status": "UNAVAILABLE",
                "reason_code": "SYNTHETIC_ONLY_NO_INTERVAL_EVIDENCE",
                "interval_type": None,
                "method": None,
                "nominal_level": None,
                "population": None,
                "asset_ref": None,
                "coverage_evidence": None,
                "review_url": None,
            },
        },
        "evidence": {
            "source_artifact_sha256": digest,
            "source_ref": "synthetic-input-only",
            "protocol_version": manifest["protocol_version"],
            "review_url": None,
        },
        "asset_status": "UNAVAILABLE",
        "review_status": "AWAITING_REVIEW",
        "limitations": ["SYNTHETIC MOCK ONLY; NOT A REAL EVALUATION"],
        "linked_evaluation_ids": linked,
    }


def _build_empty(manifest: dict[str, Any]) -> dict[str, Any]:
    case_id = manifest.get("case_id")
    if not isinstance(case_id, str):
        raise CliError("INVALID_INPUT", "empty manifest case_id must be a string")
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "release_id": None,
        "generated_at": None,
        "status": "UNAVAILABLE",
        "reason_code": manifest.get("reason_code") or "NO_APPROVED_EVALUATIONS",
        "publication_review": "PENDING",
        "default_evaluation_id": None,
        "evaluations": [],
        "ui": {
            "default_population": "development_oof",
            "population_options": [
                {"id": "development_oof", "label": "Development OOF"},
                {"id": "holdout", "label": "Holdout aggregate"},
            ],
            "figure_tabs": [
                {"figure_id": "FIG-P5-02", "label": "Residual vs Predicted", "kind": "residual_vs_predicted"},
                {"figure_id": "FIG-P5-01", "label": "Actual vs Predicted", "kind": "actual_vs_predicted"},
                {"figure_id": "FIG-P5-03", "label": "Residual Distribution", "kind": "residual_distribution"},
            ],
            "metric_order": list(METRIC_NAMES),
            "interval_figure_id": "FIG-P5-04",
        },
    }


def _build_synthetic(manifest: dict[str, Any], rows: list[dict[str, Any]], digest: str) -> dict[str, Any]:
    for key in ("execution_run_id", "configuration_id", "prediction_origin", "protocol_version"):
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            raise CliError("INVALID_INPUT", f"synthetic manifest {key} is required")
    target = manifest.get("target")
    if not isinstance(target, dict) or not isinstance(target.get("column"), str) or not isinstance(target.get("unit"), str):
        raise CliError("INVALID_INPUT", "target.column and target.unit are required strings")
    if not rows:
        raise CliError("INVALID_INPUT", "synthetic predictions must contain rows")

    folds: dict[str, list[tuple[float, float]]] = {}
    all_pairs: list[tuple[float, float]] = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("fold_id"), str):
            raise CliError("INVALID_INPUT", "each synthetic row needs a string fold_id")
        actual, predicted = row.get("actual"), row.get("predicted")
        if isinstance(actual, bool) or isinstance(predicted, bool) or not isinstance(actual, (int, float)) or not isinstance(predicted, (int, float)):
            raise CliError("INVALID_INPUT", "synthetic actual and predicted values must be numbers")
        pair = (float(actual), float(predicted))
        if not math.isfinite(pair[0]) or not math.isfinite(pair[1]):
            raise CliError("INVALID_INPUT", "synthetic actual and predicted values must be finite")
        folds.setdefault(row["fold_id"], []).append(pair)
        all_pairs.append(pair)
    if len(folds) < 2 or any(len(values) < 2 for values in folds.values()):
        raise CliError("INVALID_INPUT", "at least two folds with at least two rows each are required")

    per_fold = {fold_id: _metric_values(pairs) for fold_id, pairs in sorted(folds.items())}
    fold_mean = {
        name: (
            sum(values[name] for values in per_fold.values()) / len(per_fold)
            if all(values[name] is not None for values in per_fold.values())
            else None
        )
        for name in METRIC_NAMES
    }
    sample_sd = {}
    for name in METRIC_NAMES:
        values = [metrics[name] for metrics in per_fold.values()]
        sample_sd[name] = (
            statistics.stdev(values)
            if len(values) >= 2 and all(value is not None for value in values)
            else None
        )

    fold_id, pooled_id = "synthetic-fold-mean", "synthetic-pooled-oof"
    fold_eval = _base_evaluation(
        fold_id, manifest, len(all_pairs), fold_mean, digest, "cv_fold_mean",
        {
            "fold_count": len(folds),
            "aggregation": "fold_mean",
            "ddof": 1,
            "sample_sd": sample_sd,
            "fold_values_ref": None,
        },
        [pooled_id],
    )
    pooled_eval = _base_evaluation(
        pooled_id, manifest, len(all_pairs), _metric_values(all_pairs), digest,
        "pooled_oof", None, [fold_id],
    )
    pooled_eval["figures"] = _figure_slots(
        pooled_id, manifest["configuration_id"], len(all_pairs),
        manifest["prediction_origin"], target["unit"], digest,
    )
    return {
        "schema_version": "1.0.0",
        "case_id": manifest["case_id"],
        "release_id": None,
        "generated_at": None,
        "status": "MOCK",
        "reason_code": "SYNTHETIC_FIXTURE_ONLY",
        "publication_review": "PENDING",
        "default_evaluation_id": fold_id,
        "evaluations": [fold_eval, pooled_eval],
        "ui": _build_empty({"case_id": manifest["case_id"]})["ui"],
    }


def _validate_identity(index: dict[str, Any]) -> None:
    evaluations = index.get("evaluations")
    if not isinstance(evaluations, list):
        raise CliError("JOIN_BLOCKED", "evaluations must be a list", 4)
    ids = [item.get("evaluation_id") for item in evaluations if isinstance(item, dict)]
    if (len(ids) != len(evaluations)
            or any(not isinstance(value, str) for value in ids)
            or len(set(ids)) != len(ids)):
        raise CliError("JOIN_BLOCKED", "evaluation IDs must be present and unique", 4)
    by_id = {item["evaluation_id"]: item for item in evaluations}
    default_id = index.get("default_evaluation_id")
    if default_id is not None and (not isinstance(default_id, str) or default_id not in by_id):
        raise CliError("JOIN_BLOCKED", "default_evaluation_id must refer to an evaluation", 4)
    for item in evaluations:
        links = item.get("linked_evaluation_ids")
        if (not isinstance(links, list)
                or any(not isinstance(link, str) for link in links)
                or len(links) != len(set(links))):
            raise CliError("JOIN_BLOCKED", "linked_evaluation_ids must be a unique list", 4)
        for linked_id in links:
            other = by_id.get(linked_id)
            if other is None or item["evaluation_id"] not in other.get("linked_evaluation_ids", []):
                raise CliError("JOIN_BLOCKED", "evaluation links must exist and be reciprocal", 4)
            for key in ("execution_run_id", "configuration_id", "evaluation_population", "prediction_origin"):
                if item.get(key) != other.get(key):
                    raise CliError("JOIN_BLOCKED", f"linked evaluations disagree on {key}", 4)
            evidence = item.get("evidence")
            other_evidence = other.get("evidence")
            if not isinstance(evidence, dict) or not isinstance(other_evidence, dict):
                raise CliError("JOIN_BLOCKED", "linked evaluations need evidence objects", 4)
            for key in ("source_artifact_sha256", "protocol_version"):
                if evidence.get(key) != other_evidence.get(key):
                    raise CliError("JOIN_BLOCKED", f"linked evaluations disagree on evidence.{key}", 4)
            if item.get("metric_source") == other.get("metric_source"):
                raise CliError("JOIN_BLOCKED", "linked evaluations must have distinct metric_source values", 4)
        figures = item.get("figures")
        if not isinstance(figures, list):
            raise CliError("JOIN_BLOCKED", "figures must be a list", 4)
        figure_ids = []
        for figure in figures:
            if not isinstance(figure, dict):
                raise CliError("JOIN_BLOCKED", "each figure must be an object", 4)
            figure_ids.append(figure.get("figure_id"))
            for key in ("evaluation_id", "configuration_id", "evaluation_population", "prediction_origin", "n"):
                expected = item.get(key)
                if figure.get(key) != expected:
                    raise CliError("JOIN_BLOCKED", f"figure identity disagrees on {key}", 4)
        if any(not isinstance(value, str) for value in figure_ids) or len(set(figure_ids)) != len(figure_ids):
            raise CliError("JOIN_BLOCKED", "figure IDs must be unique strings within an evaluation", 4)


def _schema_validate(index: dict[str, Any]) -> None:
    try:
        import jsonschema
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:
        raise CliError("DEPENDENCY_MISSING", "install tools/phase5_evaluation/requirements.txt in the authorized isolated environment", 5) from exc
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(index),
            key=lambda error: list(map(str, error.absolute_path)),
        )
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        raise CliError("SCHEMA_FAIL", f"cannot validate pinned schema: {exc}", 4) from exc
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise CliError("SCHEMA_FAIL", f"{location}: {first.message}", 4)


def _atomic_write_new(path: Path, data: bytes) -> None:
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=".phase5-", suffix=".tmp", delete=False
        ) as stream:
            temporary_name = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # A same-directory hard link provides atomic creation with no replacement.
        # It fails if another process already created the destination.
        os.link(temporary_name, path)
    except FileExistsError as exc:
        raise CliError("OUTPUT_EXISTS", f"refusing to overwrite existing output: {path}", 5) from exc
    except OSError as exc:
        raise CliError("OUTPUT_WRITE_FAILED", f"atomic output creation failed: {exc}", 5) from exc
    finally:
        if temporary_name is not None:
            try:
                temporary_name.unlink(missing_ok=True)
            except OSError:
                pass


def _write_index(index: dict[str, Any], output_root: Path) -> Path:
    phase_dir = output_root / "phases" / "phase-05"
    output_file = phase_dir / "evaluations.json"
    if output_file.exists() or output_file.is_symlink():
        raise CliError("OUTPUT_EXISTS", f"refusing to overwrite existing output: {output_file}", 5)
    # Do not follow a pre-existing symlink in any output component.
    cursor = output_root
    for name in ("phases", "phase-05"):
        cursor = cursor / name
        if cursor.is_symlink():
            raise CliError("PATH_BLOCKED", f"output path contains a symlink: {cursor}")
        cursor.mkdir(exist_ok=True)
        if not cursor.is_dir():
            raise CliError("PATH_BLOCKED", f"output component is not a directory: {cursor}")
    try:
        output_file.resolve(strict=False).relative_to(output_root)
    except ValueError as exc:
        raise CliError("PATH_BLOCKED", "output path escapes gate.output_root") from exc
    payload = (json.dumps(index, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    _atomic_write_new(output_file, payload)
    return output_file


def _export(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).expanduser().resolve(strict=True)
    gate_path = Path(args.gate).expanduser().resolve(strict=True)
    manifest = _load_json(manifest_path, label="manifest")
    gate = _load_json(gate_path, label="gate")
    output_root = _validate_gate(manifest_path, manifest, gate, args.output_root, "export")

    mode = manifest.get("mode")
    if mode == "empty":
        if manifest.get("source") is not None:
            raise CliError("INVALID_INPUT", "empty manifest must not declare a source")
        index = _build_empty(manifest)
    elif mode == "synthetic":
        source_path, digest = _resolve_allowlisted_source(manifest_path, manifest, gate)
        source = _load_json(source_path, label="synthetic source")
        if source.get("fixture_kind") != "synthetic":
            raise CliError("NOT_AUTHORIZED", "source file is not marked fixture_kind=synthetic")
        rows = source.get("rows")
        if not isinstance(rows, list):
            raise CliError("INVALID_INPUT", "synthetic source rows must be a list")
        index = _build_synthetic(manifest, rows, digest)
    else:
        raise CliError("NOT_AUTHORIZED", "manifest.mode must be empty or synthetic")

    _validate_identity(index)
    _schema_validate(index)
    output = _write_index(index, output_root)
    print(f"EXPORTED {output}")
    return 0


def _validate(args: argparse.Namespace) -> int:
    index_path = Path(args.index).expanduser().resolve(strict=True)
    index = _load_json(index_path, label="evaluation index")
    _validate_identity(index)
    _schema_validate(index)
    print(f"VALID {index_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a Phase 5 evaluation index from explicitly authorized synthetic inputs."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    export_parser = subparsers.add_parser("export", help="export an authorized empty or synthetic index")
    export_parser.add_argument("--manifest", required=True, help="explicit UTF-8 JSON input manifest")
    export_parser.add_argument("--gate", required=True, help="explicit UTF-8 JSON authorization record")
    export_parser.add_argument("--output-root", required=True, help="existing private staging root allowed by the gate")
    export_parser.set_defaults(handler=_export)
    validate_parser = subparsers.add_parser("validate", help="validate a Phase 5 index against the pinned schema")
    validate_parser.add_argument("--index", required=True, help="evaluation-index JSON to validate")
    validate_parser.set_defaults(handler=_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except CliError as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        return exc.exit_code
    except (OSError, ValueError) as exc:
        print(f"INVALID_INPUT: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
