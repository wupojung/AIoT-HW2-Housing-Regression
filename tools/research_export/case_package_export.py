#!/usr/bin/env python3
"""Build a Phase 4 Case Package and, under a separate gate, a private OOF handoff."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import mimetypes
import os
import platform
import socket
import sys
import tempfile
from pathlib import Path
from typing import Any

PHASE4_SCHEMA = Path(__file__).with_name("phase-04.schema.json")
PHASE5_SCHEMA = Path(__file__).parents[1] / "phase5_evaluation" / "evaluation-index.schema.json"
HANDOFF_SCHEMA = Path(__file__).parents[1] / "phase5_evaluation" / "private-oof-handoff.schema.json"
PHASE4_SCHEMA_SHA256 = "74afdd3365867d9fb82f0a9052a1bfa19bfe389471869817dc4d7932f818f023"
OOF_COLUMNS = ["Id", "fold", "task_id", "method", "track", "actual", "predicted"]
HANDOFF_COLUMNS = ["row_id", "configuration_id", "fold_index", "task_id", "actual", "predicted"]
METHOD_LABELS = {
    "pearson": "Pearson Correlation", "mutual_information": "Mutual Information",
    "lasso": "Lasso", "elastic_net": "Elastic Net", "ridge_rfe": "Ridge RFE",
    "ols_baseline": "All-feature OLS",
}


class ExportError(Exception):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        result = json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ExportError(f"cannot read {label}: {exc}") from exc
    if not isinstance(result, dict):
        raise ExportError(f"{label} must be a JSON object")
    return result


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _safe_rel(value: Any) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ExportError("manifest paths must be nonempty forward-slash relative paths")
    path = Path(value)
    if path.is_absolute() or ":" in value or any(part in ("", ".", "..") for part in value.split("/")):
        raise ExportError("manifest path is absolute or traverses directories")
    return path


def _host_matches(host: Any) -> bool:
    actual_platform = {"darwin": "macos", "win32": "windows"}.get(sys.platform, sys.platform)
    return isinstance(host, dict) and host.get("platform") == actual_platform \
        and host.get("host_id") == socket.gethostname() \
        and host.get("python_version") == f"{sys.version_info.major}.{sys.version_info.minor}" \
        and host.get("python_executable") == str(Path(sys.executable).resolve())


def _future_path(value: Any, *, must_not_exist: bool = False) -> Path:
    if not isinstance(value, str) or not value:
        raise ExportError("gate output path is required")
    path = Path(value).expanduser().absolute()
    parent = path.parent.resolve(strict=True)
    resolved = parent / path.name
    if must_not_exist and (resolved.exists() or resolved.is_symlink()):
        raise ExportError("gate output path already exists")
    return resolved


def _validate_schema(value: dict[str, Any], schema_path: Path, label: str) -> None:
    try:
        import jsonschema
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:
        raise ExportError("install tools/research_export/requirements.txt in the task-local environment") from exc
    schema = _json(schema_path, label=f"{label} schema")
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value))
    if errors:
        error = min(errors, key=lambda item: list(map(str, item.absolute_path)))
        location = ".".join(map(str, error.absolute_path)) or "$"
        raise ExportError(f"{label} schema failed at {location}: {error.message}")


def _empty_phase5(case_id: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0", "case_id": case_id, "release_id": None, "generated_at": None,
        "status": "UNAVAILABLE", "reason_code": "NO_APPROVED_EVALUATIONS", "publication_review": "PENDING",
        "default_evaluation_id": None, "evaluations": [],
        "ui": {
            "default_population": "development_oof",
            "population_options": [{"id": "development_oof", "label": "Development OOF"}, {"id": "holdout", "label": "Holdout aggregate"}],
            "figure_tabs": [
                {"figure_id": "FIG-P5-02", "label": "Residual vs Predicted", "kind": "residual_vs_predicted"},
                {"figure_id": "FIG-P5-01", "label": "Actual vs Predicted", "kind": "actual_vs_predicted"},
                {"figure_id": "FIG-P5-03", "label": "Residual Distribution", "kind": "residual_distribution"},
            ],
            "metric_order": ["mae", "rmse", "r2"], "interval_figure_id": "FIG-P5-04",
        },
    }


def _validate_source_gate(manifest_path: Path, gate: dict[str, Any], summary_sha: str) -> tuple[Path, Path]:
    if gate.get("authorized") is not True or gate.get("mode") != "phase4_case_package":
        raise ExportError("gate must authorize phase4_case_package")
    if "export_modeling" not in gate.get("allowed_operations", []):
        raise ExportError("gate does not allow export_modeling")
    if not isinstance(gate.get("gate_id"), str) or not gate["gate_id"]:
        raise ExportError("gate.gate_id is required")
    input_root = Path(gate.get("input_root", "")).expanduser().resolve(strict=True)
    if not input_root.is_dir() or manifest_path.parent.resolve(strict=True) != input_root:
        raise ExportError("manifest must be directly inside gate.input_root")
    manifest_sha = _sha256(manifest_path)
    if manifest_sha != gate.get("manifest_sha256"):
        raise ExportError("manifest SHA does not match gate")
    allowlist = gate.get("input_allowlist")
    if not isinstance(allowlist, list) or len(allowlist) != 2:
        raise ExportError("modeling gate allowlist must contain only manifest and public summary")
    allowed = {item.get("path"): item.get("sha256") for item in allowlist if isinstance(item, dict)}
    if allowed != {"p4b_manifest.json": manifest_sha, "p4b_public_summary.json": summary_sha}:
        raise ExportError("modeling gate allowlist does not match the manifest and public summary")
    if not _host_matches(gate.get("host")):
        raise ExportError("gate host does not match this runtime")
    output_root = _future_path(gate.get("output_root"), must_not_exist=True)
    return input_root, output_root


def _load_allowlisted_sources(manifest_path: Path, gate: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], Path, Path, str, str]:
    manifest = _json(manifest_path, label="P4-B manifest")
    inventory = manifest.get("file_inventory")
    if not isinstance(inventory, list):
        raise ExportError("manifest file_inventory must be a list")
    entries = [item for item in inventory if isinstance(item, dict) and item.get("relative_path") == "p4b_public_summary.json"]
    if len(entries) != 1 or entries[0].get("is_public") is not True:
        raise ExportError("manifest must list exactly one public summary")
    summary_path = manifest_path.parent / _safe_rel(entries[0]["relative_path"])
    if summary_path.is_symlink() or not summary_path.is_file():
        raise ExportError("public summary must be a regular, non-symlink file")
    summary_sha = _sha256(summary_path)
    if summary_sha != entries[0].get("sha256"):
        raise ExportError("public summary SHA does not match manifest inventory")
    _, _ = _validate_source_gate(manifest_path, gate, summary_sha)
    summary = _json(summary_path, label="P4-B public summary")
    run_id = manifest.get("run_id")
    metadata = summary.get("metadata")
    if not isinstance(run_id, str) or not run_id or not isinstance(metadata, dict) or metadata.get("run_id") != run_id:
        raise ExportError("manifest and summary run identity do not agree")
    if gate.get("case_id") is None or gate.get("case_id") == "":
        raise ExportError("gate.case_id is required")
    if gate.get("execution_run_id") != run_id:
        raise ExportError("gate run identity does not match the source manifest")
    if gate.get("protocol_version") != metadata.get("protocol_version"):
        raise ExportError("gate protocol_version does not match the public summary")
    protocol_id = gate.get("protocol_id")
    if not isinstance(protocol_id, str) or not protocol_id:
        raise ExportError("gate.protocol_id is required")
    return manifest, summary, summary_path, manifest_path, _sha256(manifest_path), summary_sha


def _configuration_records(summary: dict[str, Any], run_id: str, protocol_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    metadata = summary["metadata"]
    boundary = metadata.get("data_boundary") if isinstance(metadata.get("data_boundary"), dict) else {}
    fold_records = summary.get("per_outer_fold_results")
    aggregates = summary.get("aggregate_results")
    if not isinstance(fold_records, list) or not isinstance(aggregates, list):
        raise ExportError("public summary must include fold and aggregate result lists")
    tasks_by_hash: dict[str, list[dict[str, Any]]] = {}
    task_ids: set[str] = set()
    for row in fold_records:
        if not isinstance(row, dict):
            raise ExportError("fold result entry must be an object")
        task_id, config_hash = row.get("task_id"), row.get("config_hash")
        if not isinstance(task_id, str) or not task_id or task_id in task_ids:
            raise ExportError("fold task IDs must be present and unique")
        if not isinstance(config_hash, str) or len(config_hash) != 64 or any(c not in "0123456789abcdef" for c in config_hash):
            raise ExportError("fold config_hash must be a lowercase SHA-256")
        task_ids.add(task_id)
        if row.get("run_id") != run_id:
            raise ExportError("fold record run_id mismatch")
        tasks_by_hash.setdefault(config_hash, []).append(row)
    config_by_id: dict[str, Any] = {}
    configs = []
    methods_by_id: dict[str, dict[str, Any]] = {}
    for aggregate in aggregates:
        if not isinstance(aggregate, dict):
            raise ExportError("aggregate entry must be an object")
        config_hash, method = aggregate.get("config_hash"), aggregate.get("method")
        if not isinstance(config_hash, str) or config_hash not in tasks_by_hash or not isinstance(method, str) or not method:
            raise ExportError("aggregate entry has no matching fold tasks or method")
        candidate = aggregate.get("candidate")
        if not isinstance(candidate, dict) or any(row.get("method") != method or row.get("candidate") != candidate for row in tasks_by_hash[config_hash]):
            raise ExportError("aggregate candidate/method does not join to fold tasks")
        configuration_id = "cfg-" + config_hash
        if configuration_id in config_by_id:
            raise ExportError("duplicate configuration hash")
        track_id = "baseline" if method == "ols_baseline" else "primary"
        aggregate_folds = aggregate.get("expected_folds")
        if not isinstance(aggregate_folds, list):
            aggregate_folds = sorted({row.get("fold") for row in tasks_by_hash[config_hash]})
        task_fold_ids = [row.get("fold") for row in tasks_by_hash[config_hash]]
        valid = (aggregate.get("status") == "COMPLETED" and aggregate.get("coverage_complete") is True
                 and aggregate.get("valid_fold_count") == aggregate.get("expected_fold_count")
                 and len(task_fold_ids) == aggregate.get("expected_fold_count")
                 and sorted(task_fold_ids) == sorted(aggregate_folds)
                 and all(task.get("status") == "COMPLETED" and task.get("primary_valid") is True
                         for task in tasks_by_hash[config_hash]))
        params = {key: value for key, value in candidate.items() if key != "candidate_order"}
        if "k" in params:
            params["top_k"] = params.pop("k")
        if method == "ols_baseline":
            params = {"features": "all_encoded_columns"}
        config = {"configuration_id": configuration_id, "execution_run_id": run_id, "method_id": method,
                  "track_id": track_id, "params": params, "protocol_id": protocol_id,
                  "status": "VERIFIED" if valid else "UNAVAILABLE"}
        config_by_id[configuration_id] = {"aggregate": aggregate, "tasks": tasks_by_hash[config_hash], "valid": valid,
                                           "config_hash": config_hash, "method_id": method, "track_id": track_id}
        configs.append(config)
        if method not in methods_by_id:
            parameters = []
            for key, value in params.items():
                if isinstance(value, bool):
                    kind = "boolean"
                elif isinstance(value, int):
                    kind = "integer"
                elif isinstance(value, float):
                    kind = "number"
                else:
                    kind = "string"
                parameters.append({"parameter_id": key, "label": key.replace("_", " ").title(), "data_type": kind})
            methods_by_id[method] = {"method_id": method, "label": METHOD_LABELS.get(method, method.replace("_", " ").title()),
                                     "parameters": parameters}
    if set(tasks_by_hash) != {item["config_hash"] for item in config_by_id.values()}:
        raise ExportError("summary contains fold-task groups without aggregate configuration records")
    fold_ids = sorted({task.get("fold") for row in fold_records for task in [row] if isinstance(task.get("fold"), int)})
    rows = boundary.get("development_rows")
    if isinstance(rows, bool) or not isinstance(rows, int) or rows < 1:
        raise ExportError("summary data_boundary.development_rows must be a positive integer")
    fold_count = boundary.get("outer_kfold", {}).get("n_splits") if isinstance(boundary.get("outer_kfold"), dict) else len(fold_ids)
    if not isinstance(fold_count, int) or fold_count < 2:
        raise ExportError("summary does not declare a valid CV fold count")
    cv = {"training_rows": rows, "fold_count": fold_count, "protocol_id": protocol_id,
          "status": "SOURCE_REPORTED_NOT_VERIFIED"}
    return configs, list(methods_by_id.values()), {"cv": cv, "configurations": config_by_id,
                                                  "fold_ids": fold_ids, "protocol_id": protocol_id}


def _package_values(gate: dict[str, Any], manifest: dict[str, Any], summary: dict[str, Any],
                    manifest_sha: str, summary_sha: str) -> dict[str, bytes]:
    case_id = gate["case_id"]
    run_id = manifest["run_id"]
    protocol_id = gate["protocol_id"]
    configurations, methods, details = _configuration_records(summary, run_id, protocol_id)
    modeling = {
        "schema_version": "1.0.0", "case_id": case_id, "status": "UNAVAILABLE", "cv": details["cv"],
        "methods": methods,
        "execution_runs": [{"execution_run_id": run_id, "source_manifest_sha256": manifest_sha, "status": "UNAVAILABLE"}],
        "configurations": configurations, "default_configuration_id": None, "charts": [],
    }
    target = gate.get("target")
    if not isinstance(target, dict) or not isinstance(target.get("column"), str) or not isinstance(target.get("unit"), str):
        raise ExportError("gate.target must contain column and unit strings")
    case_doc = {"schema_version": "1.0.0", "case_id": case_id,
                "title": gate.get("case_title") or case_id, "case_status": "PLANNED",
                "methodology_id": protocol_id,
                "source": {"label": gate.get("source_label") or "Research source", "url": gate.get("source_url") or "", "license_review": "PENDING"},
                "target": {"raw_field_id": target["column"], "label": gate.get("target_label") or target["column"],
                           "unit": target["unit"], "value_type": "number"},
                "language": "zh-Hant", "disclaimer": "Private staging package; independent review and publication approval pending."}
    package_files = {
        "case.json": case_doc,
        "phases/phase-04/modeling.json": modeling,
        "phases/phase-05/evaluations.json": _empty_phase5(case_id),
    }
    _validate_schema(modeling, PHASE4_SCHEMA, "Phase 4 modeling")
    _validate_schema(package_files["phases/phase-05/evaluations.json"], PHASE5_SCHEMA, "empty Phase 5 evaluation index")
    encoded = {path: _json_bytes(value) for path, value in package_files.items()}
    files = []
    for rel, data in sorted(encoded.items()):
        files.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                      "mime": mimetypes.guess_type(rel)[0] or "application/json"})
    package = {
        "package_schema_version": "1.0.0", "package_id": f"{case_id}-{run_id}-staging-{summary_sha[:12]}",
        "case_id": case_id, "package_revision": f"private-staging-{summary_sha[:12]}", "package_status": "PLANNED",
        "publication": {"approved": False, "release_id": None, "review_status": "PENDING"}, "case_ref": "case.json",
        "phases": {
            "phase1": {"status": "UNAVAILABLE", "data_ref": None},
            "phase2": {"status": "UNAVAILABLE", "data_ref": None},
            "phase3": {"status": "UNAVAILABLE", "data_ref": None},
            "phase4": {"status": "UNAVAILABLE", "data_ref": "phases/phase-04/modeling.json"},
            "phase5": {"status": "UNAVAILABLE", "data_ref": "phases/phase-05/evaluations.json"},
            "phase6": {"status": "UNAVAILABLE", "data_ref": None},
        }, "asset_manifest_ref": None, "files": files,
    }
    encoded["package.json"] = _json_bytes(package)
    return encoded


def _publish_new_directory(destination: Path, files: dict[str, bytes]) -> None:
    if destination.exists() or destination.is_symlink():
        raise ExportError("output root already exists; refusing overwrite")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".phase4-package-", dir=destination.parent) as temp:
        stage = Path(temp)
        for rel, payload in files.items():
            path = stage / _safe_rel(rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        for rel, payload in files.items():
            path = stage / rel
            if not path.is_file() or path.is_symlink() or path.read_bytes() != payload:
                raise ExportError(f"staged package integrity check failed: {rel}")
        os.rename(stage, destination)


def _make_handoff(manifest: dict[str, Any], summary: dict[str, Any], manifest_sha: str, summary_sha: str,
                  oof_path: Path, oof_sha: str, oof_gate: dict[str, Any], handoff_root: Path,
                  metadata: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    if oof_gate.get("authorized") is not True or oof_gate.get("mode") != "phase4_oof_rows":
        raise ExportError("separate OOF gate must authorize phase4_oof_rows")
    if "export_oof" not in oof_gate.get("allowed_operations", []):
        raise ExportError("separate OOF gate does not allow export_oof")
    if oof_gate.get("manifest_sha256") != manifest_sha or oof_gate.get("execution_run_id") != manifest.get("run_id"):
        raise ExportError("OOF gate manifest/run identity mismatch")
    if not _host_matches(oof_gate.get("host")):
        raise ExportError("OOF gate host does not match this runtime")
    root = Path(oof_gate.get("input_root", "")).expanduser().resolve(strict=True)
    if oof_path.parent.resolve(strict=True) != root or oof_path.is_symlink() or not oof_path.is_file():
        raise ExportError("OOF CSV must be a direct, non-symlink file under the separately authorized input root")
    inventory = manifest.get("file_inventory", [])
    entries = [entry for entry in inventory if isinstance(entry, dict) and entry.get("relative_path") == oof_path.name]
    if len(entries) != 1 or entries[0].get("sha256") != oof_sha:
        raise ExportError("OOF CSV must match exactly one manifest inventory entry")
    allowlist = oof_gate.get("input_allowlist")
    if not isinstance(allowlist, list) or len(allowlist) != 1 or allowlist[0] != {"path": oof_path.name, "sha256": oof_sha}:
        raise ExportError("separate OOF gate allowlist must bind exactly the source CSV")
    output_root = _future_path(oof_gate.get("output_root"), must_not_exist=True)
    package_root = metadata["package_output_root"]
    if (output_root == package_root or output_root.is_relative_to(package_root)
            or package_root.is_relative_to(output_root)):
        raise ExportError("private OOF handoff must be outside the Case Package")

    selected = oof_gate.get("configurations")
    if not isinstance(selected, list) or not selected:
        raise ExportError("OOF gate must explicitly select configurations")
    selected_by_id = {}
    for config in selected:
        if not isinstance(config, dict) or not isinstance(config.get("configuration_id"), str):
            raise ExportError("each OOF selection needs a canonical configuration_id")
        config_id = config["configuration_id"]
        details = metadata["configurations"].get(config_id)
        if details is None or details["valid"] is not True:
            raise ExportError("OOF gate selected a missing or invalid configuration")
        if (config.get("method_id") != details["method_id"] or config.get("track_id") != details["track_id"]
                or config_id != "cfg-" + details["config_hash"]):
            raise ExportError("OOF selection identity does not match the source summary")
        selected_by_id[config_id] = details
    if len(selected_by_id) != len(selected):
        raise ExportError("OOF gate configuration IDs must be unique")

    tasks = {}
    for config_id, details in selected_by_id.items():
        for task in details["tasks"]:
            if task.get("status") != "COMPLETED" or task.get("primary_valid") is not True:
                raise ExportError("selected OOF configuration contains a non-completed fold task")
            task_id = task.get("task_id")
            if not isinstance(task_id, str) or task_id in tasks:
                raise ExportError("selected OOF task IDs must be unique")
            tasks[task_id] = (config_id, task)

    rows = []
    row_ids: dict[str, set[str]] = {config_id: set() for config_id in selected_by_id}
    folds_by_config: dict[str, dict[int, int]] = {config_id: {} for config_id in selected_by_id}
    try:
        with oof_path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != OOF_COLUMNS:
                raise ExportError("source OOF CSV columns differ from the exact Phase 4 contract")
            for row in reader:
                if None in row or any(row.get(key) is None for key in OOF_COLUMNS):
                    raise ExportError("source OOF CSV row has missing or extra fields")
                task_info = tasks.get(row["task_id"])
                if task_info is None:
                    continue
                config_id, task = task_info
                if (row["method"] != task.get("method") or row["track"] != task.get("track")
                        or row["fold"] != str(task.get("fold"))):
                    raise ExportError("OOF row identity does not match its summary task")
                row_id = row["Id"]
                if not row_id or row_id in row_ids[config_id]:
                    raise ExportError("OOF row IDs must be present and unique per configuration")
                row_ids[config_id].add(row_id)
                try:
                    actual, predicted = float(row["actual"]), float(row["predicted"])
                except (TypeError, ValueError) as exc:
                    raise ExportError("selected OOF actual/predicted values must be finite numbers") from exc
                if not math.isfinite(actual) or not math.isfinite(predicted):
                    raise ExportError("selected OOF actual/predicted values must be finite numbers")
                fold = int(row["fold"])
                folds_by_config[config_id][fold] = folds_by_config[config_id].get(fold, 0) + 1
                rows.append([row_id, config_id, fold, row["task_id"], actual, predicted])
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ExportError(f"cannot read authorized OOF CSV: {exc}") from exc
    expected_rows = summary.get("metadata", {}).get("data_boundary", {}).get("development_rows")
    expected_folds = metadata.get("fold_ids")
    if not isinstance(expected_folds, list) or not expected_folds:
        raise ExportError("selected OOF fold allowlist is empty")
    if isinstance(expected_rows, bool) or not isinstance(expected_rows, int) or expected_rows < 1:
        raise ExportError("summary does not declare the Development row count")
    for config_id in selected_by_id:
        if (len(row_ids[config_id]) != expected_rows or sorted(folds_by_config[config_id]) != expected_folds
                or any(count < 1 for count in folds_by_config[config_id].values())):
            raise ExportError("selected configuration has missing OOF rows or fold coverage")

    csv_stream = io.StringIO(newline="")
    writer = csv.writer(csv_stream, lineterminator="\n")
    writer.writerow(HANDOFF_COLUMNS)
    writer.writerows(rows)
    csv_bytes = csv_stream.getvalue().encode("utf-8")
    csv_sha = hashlib.sha256(csv_bytes).hexdigest()
    protocol_id = oof_gate["protocol_id"]
    protocol_version = summary["metadata"]["protocol_version"]
    if protocol_id != metadata["protocol_id"] or oof_gate.get("protocol_version") != protocol_version:
        raise ExportError("OOF gate protocol_id must match the Phase 4 modeling gate")
    handoff = {
        "schema_version": "1.0.0", "case_id": oof_gate["case_id"], "execution_run_id": manifest["run_id"],
        "protocol_id": protocol_id, "protocol_version": protocol_version, "population": "development_oof",
        "target": oof_gate["target"],
        "source_artifacts": {"manifest_sha256": manifest_sha, "summary_sha256": summary_sha, "oof_sha256": oof_sha},
        "csv": {"path": "oof.csv", "sha256": csv_sha, "columns": HANDOFF_COLUMNS},
        "row_count": len(rows), "n_per_configuration": expected_rows, "expected_fold_ids": expected_folds,
        "configurations": [
            {"configuration_id": config_id, "config_hash": details["config_hash"], "method_id": details["method_id"],
             "track_id": details["track_id"], "status": "COMPLETED",
             "fold_tasks": [{"fold_index": task["fold"], "task_id": task["task_id"]}
                            for task in sorted(details["tasks"], key=lambda item: item["fold"])]}
            for config_id, details in selected_by_id.items()
        ],
    }
    _validate_schema(handoff, HANDOFF_SCHEMA, "private OOF handoff")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".phase5-oof-handoff-", dir=output_root.parent) as temp:
        stage = Path(temp) / "handoff"
        stage.mkdir()
        (stage / "oof.csv").write_bytes(csv_bytes)
        (stage / "handoff.json").write_bytes(_json_bytes(handoff))
        if _sha256(stage / "oof.csv") != csv_sha:
            raise ExportError("staged OOF handoff CSV digest mismatch")
        os.rename(stage, output_root)
    return output_root, handoff


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Phase 4 Case Package metadata; optionally create a separate gated private OOF handoff.")
    parser.add_argument("--manifest", required=True, type=Path, help="explicit P4-B manifest path")
    parser.add_argument("--gate", required=True, type=Path, help="Owner gate for manifest, public summary and Case Package output")
    parser.add_argument("--oof-gate", type=Path, help="separate Owner gate required before reading the OOF CSV")
    parser.add_argument("--handoff-root", type=Path, help="new private output directory required with --oof-gate")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        manifest_path = args.manifest.expanduser().resolve(strict=True)
        gate = _json(args.gate.expanduser().resolve(strict=True), label="Phase 4 modeling gate")
        manifest, summary, _, _, manifest_sha, summary_sha = _load_allowlisted_sources(manifest_path, gate)
        _, output_root = _validate_source_gate(manifest_path, gate, summary_sha)
        source_root = manifest_path.parent.resolve(strict=True)
        if output_root == source_root or output_root.is_relative_to(source_root):
            raise ExportError("Case Package output must be outside the source run directory")
        metadata = summary.get("metadata", {})
        if (args.oof_gate is None) != (args.handoff_root is None):
            raise ExportError("--oof-gate and --handoff-root must be supplied together")
        package_output = _package_values(gate, manifest, summary, manifest_sha, summary_sha)
        handoff = None
        if args.oof_gate is not None:
            oof_gate = _json(args.oof_gate.expanduser().resolve(strict=True), label="separate OOF gate")
            if oof_gate.get("case_id") != gate.get("case_id"):
                raise ExportError("OOF gate case_id differs from Case Package gate")
            if (oof_gate.get("protocol_id") != gate.get("protocol_id")
                    or oof_gate.get("target") != gate.get("target")):
                raise ExportError("OOF gate protocol/target identity differs from Case Package gate")
            input_root = Path(oof_gate.get("input_root", "")).expanduser().resolve(strict=True)
            oof_path = input_root / "p4b_oof_predictions.csv"
            inventory = manifest.get("file_inventory", [])
            entries = [entry for entry in inventory if isinstance(entry, dict) and entry.get("relative_path") == oof_path.name]
            if len(entries) != 1 or not oof_path.is_file() or oof_path.is_symlink():
                raise ExportError("manifest-listed OOF CSV is missing or unsafe")
            oof_sha = _sha256(oof_path)
            if oof_sha != entries[0].get("sha256"):
                raise ExportError("OOF CSV SHA does not match source manifest")
            details = _configuration_records(summary, manifest["run_id"], gate["protocol_id"])[2]
            handoff_root = _future_path(oof_gate.get("output_root"), must_not_exist=True)
            if args.handoff_root.expanduser().absolute() != handoff_root:
                raise ExportError("--handoff-root must match the separately authorized OOF output_root")
            handoff = _make_handoff(manifest, summary, manifest_sha, summary_sha, oof_path, oof_sha,
                                    oof_gate, handoff_root, {**details, "package_output_root": output_root})
        _publish_new_directory(output_root, package_output)
        print(json.dumps({"status": "EXPORTED", "case_id": gate["case_id"], "execution_run_id": manifest["run_id"],
                          "package_file_count": len(package_output) - 1,
                          "private_oof_handoff": str(handoff[0]) if handoff else None}, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"EXPORT_BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
