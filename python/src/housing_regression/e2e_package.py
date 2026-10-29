"""Minimal synthetic Phase 1–6 package assembly and fail-closed bundle checks."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import statistics
from typing import Any
import xml.etree.ElementTree as ET

import numpy as np
from sklearn.linear_model import Ridge

from housing_regression.contracts import ContractValidationError, validate_document
from housing_regression.core_utils import PhaseCoreError
from housing_regression.init_config import ConfigError, load_config
from housing_regression.phase1_core import build_phase1
from housing_regression.phase2_core import build_phase2


_PHASE_REFS = {
    1: ("phases/phase-01/content.json", "docs/design/data-contracts/schemas/phase-01.schema.json"),
    2: ("phases/phase-02/analyses.json", "docs/design/data-contracts/schemas/phase-02.schema.json"),
    3: ("phases/phase-03/preparation.json", "docs/design/data-contracts/schemas/phase-03.schema.json"),
    4: ("phases/phase-04/modeling.json", "docs/design/data-contracts/schemas/phase-04.schema.json"),
    5: (
        "phases/phase-05/evaluations.json",
        "docs/design/data-contracts/schemas/phase-05.schema.json",
    ),
    6: ("phases/phase-06/inference-catalog.json", "docs/design/data-contracts/schemas/phase-06.schema.json"),
}
class PackageValidationError(PhaseCoreError):
    """A Case Package reference, schema, privacy, or integrity check failed."""


def _json_write_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise PhaseCoreError(f"refusing to overwrite {path.name}") from exc
    except OSError as exc:
        raise PhaseCoreError(f"could not write {path.name}") from exc


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageValidationError(f"invalid UTF-8 JSON at {path.name}") from exc
    if not isinstance(value, dict):
        raise PackageValidationError(f"JSON root must be an object: {path.name}")
    return value


def _safe_package_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or "\\" in value:
        raise PackageValidationError("package references must be POSIX relative paths")
    ref = PurePosixPath(value)
    if ref.is_absolute() or not ref.parts or any(part in ("", ".", "..") for part in ref.parts):
        raise PackageValidationError("package reference escapes its root")
    return ref


def _phase_unavailable(phase: int, case_id: str) -> dict[str, Any]:
    if phase != 6:
        raise ValueError("Only Phase 6 has an unavailable template in the synthetic E2E")
    return {
        "schema_version": "1.0.0", "case_id": case_id, "status": "UNAVAILABLE",
        "models": [],
        "readiness": {
            "predict_enabled": False, "reason_code": "NO_APPROVED_MODEL",
            "message": "Synthetic in-memory inference ran, but no approved deployable model exists.",
        },
    }


def _read_synthetic_rows(config_path: Path, config: Any) -> tuple[list[str], list[dict[str, str]], str]:
    repo_root = Path(__file__).resolve().parents[3]
    expected_fixture = (repo_root / "tests/fixtures/regscope_g2_synthetic.csv.fixture").resolve(strict=True)
    source = (config_path.resolve(strict=True).parent / config.values["data"]["path"]).resolve(strict=True)
    if source != expected_fixture:
        raise PhaseCoreError("synthetic E2E accepts only the fixed repository synthetic CSV fixture")
    payload = source.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != config.source_sha256:
        raise PhaseCoreError("synthetic source SHA-256 changed after INIT")
    try:
        text = payload.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if not reader.fieldnames:
            raise ValueError("missing CSV header")
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        raise PhaseCoreError("synthetic CSV cannot be parsed") from exc
    if not rows or any(None in row for row in rows):
        raise PhaseCoreError("synthetic CSV must contain complete-width data rows")
    return list(reader.fieldnames), rows, digest


def _synthetic_preprocess(
    case_id: str, headers: list[str], rows: list[dict[str, str]], phase2: dict[str, Any], target: str
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, dict[str, Any]]:
    decision_text = phase2["analyses"][0]["finding"]
    decisions = {
        name: (kind, action)
        for name, kind, action in re.findall(r"([A-Za-z0-9_]+) \[([^]]+)\] (include|exclude)", decision_text)
    }
    feature_names = [
        name for name in headers
        if name not in (target, "Id") and decisions.get(name, ("unknown", "exclude"))[1] == "include"
    ]
    if not feature_names:
        raise PhaseCoreError("synthetic Phase 3 requires at least one supported feature")

    matrix_columns: list[list[float]] = []
    encoded_types: list[str] = []
    treatments: list[dict[str, Any]] = []
    field_counts: dict[str, int] = {}
    for name in feature_names:
        kind = decisions[name][0]
        if kind in ("continuous", "discrete"):
            parsed: list[float | None] = []
            for row in rows:
                value = row[name].strip()
                if value in ("", "NA"):
                    parsed.append(None)
                    continue
                try:
                    number = float(value)
                except ValueError as exc:
                    raise PhaseCoreError(f"synthetic numeric field {name} contains non-numeric data") from exc
                if not math.isfinite(number):
                    raise PhaseCoreError(f"synthetic numeric field {name} contains a non-finite value")
                parsed.append(number)
            present = [value for value in parsed if value is not None]
            if not present:
                raise PhaseCoreError(f"synthetic numeric field {name} has no observed values")
            fill = float(statistics.median(present))
            matrix_columns.append([fill if value is None else value for value in parsed])
            encoded_types.append(kind)
            treatments.append({
                "field_id": name, "strategy": "median_imputation", "fit_population": "all synthetic smoke rows",
                "status": "MOCK",
            })
            field_counts[kind] = field_counts.get(kind, 0) + 1
        elif kind == "nominal":
            values = [row[name].strip() for row in rows]
            present = [value for value in values if value not in ("", "NA")]
            if not present:
                raise PhaseCoreError(f"synthetic categorical field {name} has no observed levels")
            counts: dict[str, int] = {}
            for value in present:
                counts[value] = counts.get(value, 0) + 1
            fill = min(counts, key=lambda value: (-counts[value], value))
            resolved = [fill if value in ("", "NA") else value for value in values]
            levels = sorted(set(resolved))
            for level in levels:
                matrix_columns.append([1.0 if value == level else 0.0 for value in resolved])
                encoded_types.append("nominal")
            treatments.append({
                "field_id": name, "strategy": "mode_imputation_then_one_hot", "fit_population": "all synthetic smoke rows",
                "status": "MOCK",
            })
            field_counts["nominal"] = field_counts.get("nominal", 0) + 1
        else:
            raise PhaseCoreError(f"synthetic Phase 3 does not implement {kind} encoding")

    target_values = []
    for row in rows:
        value = row[target].strip()
        if value in ("", "NA"):
            raise PhaseCoreError("synthetic smoke target must be present for the in-sample model smoke")
        target_values.append(float(value))
    matrix = np.asarray(matrix_columns, dtype=np.float64).T
    if matrix.ndim != 2 or matrix.shape[0] != len(rows) or not np.isfinite(matrix).all():
        raise PhaseCoreError("synthetic Phase 3 transform produced an invalid feature matrix")
    y = np.asarray(target_values, dtype=np.float64)
    raw_known_counts = dict(field_counts)
    known = sum(raw_known_counts.values())
    raw_predictor_count = sum(1 for name in headers if name not in (target, "Id"))
    unknown_count = raw_predictor_count - known
    encoded_counts = {kind: encoded_types.count(kind) for kind in set(encoded_types)}
    stages = [
        {"id": "raw", "label": "Synthetic CSV predictors", "unit": "raw_columns", "total": raw_predictor_count,
         "total_status": "MOCK", "segments": [{"type_id": k, "count": v} for k, v in sorted(raw_known_counts.items())],
         "distribution_status": "UNAVAILABLE" if unknown_count else "MOCK"},
        {"id": "filtered", "label": "Supported configured features", "unit": "pre_encoding_columns", "total": known,
         "total_status": "MOCK", "segments": [{"type_id": k, "count": v} for k, v in sorted(raw_known_counts.items())],
         "distribution_status": "MOCK"},
        {"id": "processed", "label": "Imputed synthetic features", "unit": "pre_encoding_columns", "total": known,
         "total_status": "MOCK", "segments": [{"type_id": k, "count": v} for k, v in sorted(raw_known_counts.items())],
         "distribution_status": "MOCK", "fit_population": "all synthetic smoke rows", "pipeline_version": "synthetic-prep-v1"},
        {"id": "encoded", "label": "Numeric and one-hot features", "unit": "encoded_features", "total": matrix.shape[1],
         "total_status": "MOCK", "segments": [{"type_id": k, "count": v} for k, v in sorted(encoded_counts.items())],
         "distribution_status": "MOCK", "fit_population": "all synthetic smoke rows", "pipeline_version": "synthetic-prep-v1"},
    ]
    document = {
        "schema_version": "1.0.0", "case_id": case_id, "status": "MOCK",
        "feature_types": [
            {"type_id": kind, "label": {"continuous": "Continuous numeric", "discrete": "Discrete numeric", "nominal": "Nominal category"}[kind]}
            for kind in sorted(set(field_counts))
        ],
        "stages": stages, "treatments": treatments,
        "split": {"source_labeled_rows": len(rows), "training_rows": None, "holdout_rows": None,
                  "seed": None, "status": "UNAVAILABLE"},
        "lineage_ref": None,
    }
    return document, matrix, y, {"rows": len(rows), "raw_predictors": raw_predictor_count,
                                  "filtered_features": known, "encoded_features": int(matrix.shape[1])}


def _synthetic_model_and_evaluation(
    case_id: str, target: str, source_sha256: str, matrix: np.ndarray, y: np.ndarray
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Ridge, dict[str, Any]]:
    if matrix.shape[0] < 2 or len(set(y.tolist())) < 2:
        raise PhaseCoreError("synthetic model smoke requires two rows and variable targets")
    run_id = "synthetic-e2e-run-001"
    configuration_id = "synthetic-e2e-ridge-alpha1"
    model = Ridge(alpha=1.0)
    model.fit(matrix, y)
    predictions = model.predict(matrix)
    residuals = y - predictions
    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    variance = float(np.sum((y - np.mean(y)) ** 2))
    r2 = float(1.0 - np.sum(residuals ** 2) / variance) if variance else 0.0
    metric_values = {"mae": mae, "rmse": rmse, "r2": r2}
    phase4 = {
        "schema_version": "1.1.0", "case_id": case_id, "status": "MOCK",
        "cv": {"training_rows": None, "fold_count": None, "protocol_id": None, "status": "UNAVAILABLE"},
        "methods": [{"method_id": "ridge-synthetic-smoke", "label": "Ridge Regression (synthetic smoke)",
                     "parameters": [{"parameter_id": "alpha", "label": "Alpha", "data_type": "number"}]}],
        "execution_runs": [{"execution_run_id": run_id, "source_manifest_sha256": source_sha256, "status": "MOCK"}],
        "configurations": [{
            "configuration_id": configuration_id, "execution_run_id": run_id,
            "method_id": "ridge-synthetic-smoke", "track_id": "synthetic-in-sample",
            "params": {"alpha": 1.0}, "protocol_id": "synthetic-in-sample-smoke-v1",
            "status": "MOCK",
        }],
        "default_configuration_id": None, "charts": [],
    }
    metric_docs = {
        key: {"value": round(value, 6), "status": "MOCK", "reason_code": "SYNTHETIC_IN_SAMPLE_ONLY",
              "evidence_ref": run_id}
        for key, value in metric_values.items()
    }
    phase5 = {
        "schema_version": "1.0.0", "case_id": case_id, "release_id": None,
        "generated_at": None, "status": "MOCK", "reason_code": "SYNTHETIC_IN_SAMPLE_ONLY",
        "publication_review": "PENDING", "default_evaluation_id": None,
        "evaluations": [{
            "evaluation_id": "synthetic-e2e-ridge-training-metrics", "execution_run_id": run_id,
            "configuration_id": configuration_id, "final_fit_id": None, "model_id": None,
            "model_version": None, "evaluation_population": "training_in_sample",
            "prediction_origin": "synthetic-ridge-fit", "metric_source": "training_in_sample",
            "n": int(len(y)), "target": {"column": target, "unit": "synthetic units"},
            "metrics": metric_docs, "fold_summary": None, "figures": [],
            "interval": {
                "int_f": {"status": "UNAVAILABLE", "reason_code": "NO_INTERVAL_SMOKE", "method": None, "assumptions_ref": None},
                "int_s": {"status": "UNAVAILABLE", "reason_code": "NO_INTERVAL_SMOKE", "interval_type": None,
                          "method": None, "nominal_level": None, "population": None, "asset_ref": None,
                          "coverage_evidence": None, "review_url": None},
            },
            "evidence": {"source_artifact_sha256": source_sha256, "source_ref": "Synthetic repository fixture",
                         "protocol_version": "synthetic-in-sample-smoke-v1", "review_url": None},
            "asset_status": "UNAVAILABLE", "review_status": "AWAITING_REVIEW",
            "limitations": ["In-sample metrics on a tiny synthetic fixture; not scientific evidence.",
                            "No train/validation split, CV, real data, or publication review was used."],
            "linked_evaluation_ids": [],
        }],
        "ui": {
            "default_population": "training_in_sample",
            "population_options": [
                {"id": "development_oof", "label": "Development OOF"},
                {"id": "holdout", "label": "Holdout aggregate (not accessed)"},
                {"id": "training_in_sample", "label": "Synthetic training in-sample"},
            ],
            "figure_tabs": [
                {"figure_id": "FIG-P5-02", "label": "Residual vs Predicted", "kind": "residual_vs_predicted"},
                {"figure_id": "FIG-P5-01", "label": "Actual vs Predicted", "kind": "actual_vs_predicted"},
                {"figure_id": "FIG-P5-03", "label": "Residual Distribution", "kind": "residual_distribution"},
            ],
            "metric_order": ["mae", "rmse", "r2"], "interval_figure_id": "FIG-P5-04",
        },
    }
    phase6 = _phase_unavailable(6, case_id)
    execution = {
        "phase4_model_fit": "PASS", "phase5_synthetic_metrics": "PASS",
        "phase6_in_memory_prediction": "PASS" if len(model.predict(matrix[:1])) == 1 else "FAIL",
        "phase5_training_in_sample_metrics": {key: round(value, 6) for key, value in metric_values.items()},
        "phase6_deployable_model": "UNAVAILABLE",
    }
    return phase4, phase5, phase6, model, execution


def _figure_manifest(package_root: Path, analyses: dict[str, Any], case_id: str) -> dict[str, Any]:
    entries = []
    for analysis in analyses["analyses"]:
        ref = analysis.get("image_ref")
        if ref is None:
            continue
        safe_ref = _safe_package_path(ref)
        asset_path = package_root.joinpath(*safe_ref.parts)
        try:
            asset_path.resolve(strict=True).relative_to(package_root.resolve(strict=True))
            svg_root = ET.parse(asset_path).getroot()
        except (OSError, ValueError, ET.ParseError) as exc:
            raise PackageValidationError("Phase 2 SVG is missing or invalid") from exc
        view_box = svg_root.attrib.get("viewBox", "0 0 0 0").split()
        if len(view_box) != 4:
            raise PackageValidationError("SVG requires an accessible viewBox")
        width, height = int(float(view_box[2])), int(float(view_box[3]))
        digest = hashlib.sha256(asset_path.read_bytes()).hexdigest()
        entries.append({
            "figure_id": analysis["figure_id"], "case_id": case_id, "phase": 2,
            "source_configuration_id": None, "source_evaluation_id": None,
            "svg_ref": ref, "png_ref": None, "width": width, "height": height,
            "alt": analysis["description"], "accessible_table_ref": None,
            "source_evidence_ref": "Synthetic fixture output; not research evidence.",
            "sha256_svg": digest, "sha256_png": None,
            "publication_review": "NOT_REVIEWED", "status": "MOCK",
        })
    return {"schema_version": "1.0.0", "case_id": case_id, "status": "MOCK", "figures": entries}


def _file_manifest(package_root: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(package_root.rglob("*")):
        if path.is_symlink():
            raise PackageValidationError("symlinks are forbidden inside a Case Package")
        if not path.is_file() or path.name == "package.json":
            continue
        relative = path.relative_to(package_root).as_posix()
        mime = mimetypes.guess_type(relative)[0] or "application/octet-stream"
        payload = path.read_bytes()
        entries.append({"path": relative, "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload), "mime": mime})
    return entries


def build_minimal_synthetic_package(
    config_path: str | os.PathLike[str], package_root: str | os.PathLike[str]
) -> dict[str, Any]:
    """Run the synthetic Core path and package real transformations with honest mock labels."""
    root = Path(package_root)
    if root.exists() or root.is_symlink():
        raise PhaseCoreError("refusing to overwrite an existing Case Package path")
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        raise PhaseCoreError("INIT config or source evidence is invalid") from exc
    headers, rows, source_sha256 = _read_synthetic_rows(Path(config_path), config)
    root.mkdir(parents=True, exist_ok=False)
    case_id = config.values["case_id"]
    target = config.values["data"]["target"]

    phase1_dir = root / "phases" / "phase-01"
    phase1_dir.mkdir(parents=True)
    phase1 = build_phase1(config_path, phase1_dir, {
        "business_question": "Can the synthetic fixture pass through the RegScope case workflow?",
        "source_description": "Fixed repository synthetic CSV fixture; no real research data is used.",
        "license_or_rights": "Synthetic test fixture authored for software validation; no research rights claim.",
    })
    phase2 = build_phase2(config_path, root)

    phase3, matrix, y, prep_summary = _synthetic_preprocess(
        case_id, headers, rows, phase2, target
    )
    phase4, phase5, phase6, _, execution_summary = _synthetic_model_and_evaluation(
        case_id, target, source_sha256, matrix, y
    )
    for phase, document in ((3, phase3), (4, phase4), (5, phase5), (6, phase6)):
        ref, _ = _PHASE_REFS[phase]
        _json_write_exclusive(root / ref, document)

    _json_write_exclusive(root / "case.json", {
        "schema_version": "1.0.0", "case_id": case_id,
        "title": "RegScope Synthetic E2E Fixture", "case_status": "MOCK",
        "methodology_id": None,
        "source": {"label": "Synthetic repository fixture", "url": None, "license_review": "PENDING"},
        "target": {"raw_field_id": target, "label": target, "unit": "synthetic units", "value_type": "number"},
        "language": "zh-Hant",
        "disclaimer": "Synthetic software smoke only. Phase 3–5 computations are MOCK; no scientific result or deployable model is provided.",
    })
    _json_write_exclusive(root / "assets/figure-manifest.json", _figure_manifest(root, phase2, case_id))

    phase_documents = {1: phase1, 2: phase2}
    for phase in range(3, 7):
        phase_documents[phase] = _read_json(root / _PHASE_REFS[phase][0])
    phases = {
        f"phase{phase}": {"status": phase_documents[phase]["status"], "data_ref": _PHASE_REFS[phase][0]}
        for phase in range(1, 7)
    }
    package = {
        "package_schema_version": "1.0.0", "package_id": f"{case_id}-synthetic-e2e-r1",
        "case_id": case_id, "package_revision": "synthetic-r1", "package_status": "MOCK",
        "publication": {"approved": False, "release_id": None, "review_status": "NOT_REVIEWED"},
        "case_ref": "case.json", "phases": phases,
        "asset_manifest_ref": "assets/figure-manifest.json", "files": _file_manifest(root),
    }
    _json_write_exclusive(root / "package.json", package)
    validate_case_package(root)
    return {"package": package, "execution": {"phase3": prep_summary, **execution_summary}}


def validate_case_package(package_root: str | os.PathLike[str]) -> dict[str, Any]:
    """Validate pinned Phase schemas, path/ID references, file SHA/bytes/MIME, and bundle coverage."""
    root = Path(package_root)
    if root.is_symlink() or not root.is_dir():
        raise PackageValidationError("package_root must be an existing non-symlink directory")
    package = _read_json(root / "package.json")
    required = {
        "package_schema_version", "package_id", "case_id", "package_revision", "package_status",
        "publication", "case_ref", "phases", "asset_manifest_ref", "files",
    }
    if set(package) != required or package["package_schema_version"] != "1.0.0":
        raise PackageValidationError("package.json does not match Case Package v1 required fields")
    case_ref = _safe_package_path(package["case_ref"])
    case_doc = _read_json(root.joinpath(*case_ref.parts))
    case_id = package["case_id"]
    if case_doc.get("case_id") != case_id or case_doc.get("case_status") != package["package_status"]:
        raise PackageValidationError("case identity or status does not match package manifest")
    if package["publication"].get("approved") is not False or package["publication"].get("release_id") is not None:
        raise PackageValidationError("synthetic E2E package cannot be publication-approved")
    if set(package["phases"]) != {f"phase{i}" for i in range(1, 7)}:
        raise PackageValidationError("package must reference all six phases")

    entries = package["files"]
    if not isinstance(entries, list) or not entries:
        raise PackageValidationError("package files manifest must not be empty")
    by_path: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "bytes", "mime"}:
            raise PackageValidationError("invalid files[] entry")
        safe_ref = _safe_package_path(entry["path"])
        normalized = safe_ref.as_posix()
        if normalized == "package.json" or normalized in by_path:
            raise PackageValidationError("duplicate path or package self-hash in files[]")
        path = root.joinpath(*safe_ref.parts)
        if path.is_symlink() or not path.is_file():
            raise PackageValidationError(f"manifest file is missing or unsafe: {normalized}")
        payload = path.read_bytes()
        expected_mime = mimetypes.guess_type(normalized)[0] or "application/octet-stream"
        if (
            entry["sha256"] != hashlib.sha256(payload).hexdigest()
            or entry["bytes"] != len(payload)
            or entry["mime"] != expected_mime
        ):
            raise PackageValidationError(f"manifest integrity mismatch: {normalized}")
        if Path(normalized).suffix.lower() in {".csv", ".joblib", ".pkl", ".pickle"}:
            raise PackageValidationError("raw data and fitted-model binaries are forbidden in this E2E package")
        by_path[normalized] = entry

    actual_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "package.json"
    }
    if actual_files != set(by_path):
        raise PackageValidationError("files[] does not exactly cover package contents")

    phase_docs = {}
    repo_root = Path(__file__).resolve().parents[3]
    for phase, (ref, schema_relative) in _PHASE_REFS.items():
        phase_entry = package["phases"][f"phase{phase}"]
        if set(phase_entry) != {"status", "data_ref"} or phase_entry["data_ref"] != ref:
            raise PackageValidationError(f"invalid phase{phase} package reference")
        if ref not in by_path or Path(ref).suffix != ".json":
            raise PackageValidationError(f"phase{phase} reference is not in files[]")
        document = _read_json(root / ref)
        if document.get("case_id") != case_id or phase_entry["status"] != document.get("status"):
            raise PackageValidationError(f"phase{phase} case_id/status mismatch")
        try:
            validate_document(document, repo_root / schema_relative)
        except ContractValidationError as exc:
            raise PackageValidationError(f"phase{phase} schema validation failed: {exc}") from exc
        phase_docs[phase] = document

    phase4 = phase_docs[4]
    run_ids = {item["execution_run_id"] for item in phase4["execution_runs"]}
    method_ids = {item["method_id"] for item in phase4["methods"]}
    configuration_ids = {item["configuration_id"] for item in phase4["configurations"]}
    if (
        len(run_ids) != len(phase4["execution_runs"])
        or len(method_ids) != len(phase4["methods"])
        or len(configuration_ids) != len(phase4["configurations"])
        or any(item["execution_run_id"] not in run_ids for item in phase4["configurations"])
        or any(item["method_id"] not in method_ids for item in phase4["configurations"])
    ):
        raise PackageValidationError("Phase 4 run/configuration/method ID references are inconsistent")
    for evaluation in phase_docs[5]["evaluations"]:
        if evaluation["execution_run_id"] not in run_ids or evaluation["configuration_id"] not in configuration_ids:
            raise PackageValidationError("Phase 5 references a missing Phase 4 run or configuration")
    for model in phase_docs[6]["models"]:
        if (
            model["source_execution_run_id"] not in run_ids
            or model["source_configuration_id"] not in configuration_ids
        ):
            raise PackageValidationError("Phase 6 model references a missing Phase 4 run or configuration")

    manifest_ref = _safe_package_path(package["asset_manifest_ref"])
    if manifest_ref.as_posix() not in by_path:
        raise PackageValidationError("asset manifest ref is absent from files[]")
    figure_manifest = _read_json(root.joinpath(*manifest_ref.parts))
    if figure_manifest.get("case_id") != case_id or not isinstance(figure_manifest.get("figures"), list):
        raise PackageValidationError("figure manifest identity or figures array is invalid")
    figures = {item.get("figure_id"): item for item in figure_manifest["figures"]}
    if len(figures) != len(figure_manifest["figures"]):
        raise PackageValidationError("duplicate figure_id in figure manifest")
    for analysis in phase_docs[2]["analyses"]:
        ref = analysis.get("image_ref")
        if ref is None:
            continue
        safe_ref = _safe_package_path(ref).as_posix()
        figure = figures.get(analysis.get("figure_id"))
        if (
            safe_ref not in by_path or figure is None or figure.get("svg_ref") != safe_ref
            or figure.get("sha256_svg") != by_path[safe_ref]["sha256"]
        ):
            raise PackageValidationError("Phase 2 image_ref is not covered by the figure manifest and files[]")
    return {"status": "PASS", "case_id": case_id, "phase_count": 6, "file_count": len(entries), "figure_count": len(figures)}
