"""Build a public aggregate-only Case Package for historical Phase 4 exploration."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import math
import os
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from housing_regression.model_exploration import ModelExplorationError


class ExplorationPackageError(ValueError):
    """Exploration package evidence failed bundle or contract validation."""


PHASE_PATHS = {
    1: "phases/phase-01/content.json",
    2: "phases/phase-02/analyses.json",
    3: "phases/phase-03/preparation.json",
    4: "phases/phase-04/modeling.json",
    5: "phases/phase-05/evaluations.json",
    6: "phases/phase-06/inference-catalog.json",
}
SCHEMAS = {
    1: "docs/design/data-contracts/schemas/phase-01.schema.json",
    2: "docs/design/data-contracts/schemas/phase-02.schema.json",
    3: "docs/design/data-contracts/schemas/phase-03.schema.json",
    4: "docs/design/data-contracts/schemas/phase-04.schema.json",
    5: "docs/design/data-contracts/schemas/phase-05.schema.json",
    6: "docs/design/data-contracts/schemas/phase-06.schema.json",
}


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ExplorationPackageError(f"expected JSON object at {path.name}")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _safe_ref(ref: Any) -> bool:
    if not isinstance(ref, str) or "\\" in ref:
        return False
    path = PurePosixPath(ref)
    return not path.is_absolute() and bool(path.parts) and all(part not in {"", ".", ".."} for part in path.parts)


def _validate_schema(document: Mapping[str, Any], schema_path: Path) -> None:
    schema = _read_json(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda error: (tuple(map(str, error.absolute_path)), error.message))
    if errors:
        error = errors[0]
        pointer = "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path)
        raise ExplorationPackageError(f"{pointer}: {error.message}")


def _contains_row_record(value: Any) -> bool:
    if isinstance(value, Mapping):
        keys = {str(key).lower() for key in value}
        if "row_id" in keys or {"actual", "predicted"}.issubset(keys) or "oof_records" in keys:
            return True
        return any(_contains_row_record(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_row_record(child) for child in value)
    return False


def _file_manifest(case_root: Path) -> list[dict[str, Any]]:
    files = []
    for path in sorted(item for item in case_root.rglob("*") if item.is_file() and item.name != "package.json"):
        relative = path.relative_to(case_root).as_posix()
        payload = path.read_bytes()
        files.append({"path": relative, "sha256": _sha(payload), "bytes": len(payload), "mime": mimetypes.guess_type(relative)[0] or "application/octet-stream"})
    return files


def build_model_exploration_package(
    source_case_root: str | Path,
    output_case_root: str | Path,
    *,
    case_id: str,
    release_id: str,
    source_data_sha256: str,
    phase4: Mapping[str, Any],
    phase4_artifacts: Mapping[str, Mapping[str, Any]],
    phase5: Mapping[str, Any],
    phase5_artifacts: Mapping[str, Mapping[str, Any]],
    repository_root: str | Path,
) -> dict[str, Any]:
    """Create a new package atomically; never overwrite an existing package."""
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", case_id):
        raise ExplorationPackageError("case_id must be lowercase URL-safe")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,79}", release_id):
        raise ExplorationPackageError("release_id must be lowercase URL-safe")
    if not re.fullmatch(r"[0-9a-f]{64}", source_data_sha256):
        raise ExplorationPackageError("source data SHA-256 is required")
    source_root = Path(source_case_root)
    destination = Path(output_case_root)
    repo = Path(repository_root)
    if source_root.is_symlink() or not source_root.is_dir():
        raise ExplorationPackageError("source Case Package directory is missing or unsafe")
    if destination.exists() or destination.is_symlink():
        raise ExplorationPackageError("refusing to overwrite an existing exploration package")
    if destination.name != case_id or destination.parent.name != "cases":
        raise ExplorationPackageError("destination must be <release>/cases/<case_id>")
    release_root = destination.parent.parent
    if release_root.name != release_id:
        raise ExplorationPackageError("release directory must match release_id")
    if release_root.exists() or release_root.is_symlink():
        raise ExplorationPackageError("refusing to overwrite an existing release directory")

    source_package = _read_json(source_root / "package.json")
    source_files = {item["path"]: item for item in source_package.get("files", [])}
    source_phases = source_package.get("phases", {})

    def read_bound(relative: str) -> tuple[dict[str, Any], bytes]:
        if not _safe_ref(relative) or relative not in source_files:
            raise ExplorationPackageError(f"source package reference is not manifest-bound: {relative}")
        path = source_root.joinpath(*PurePosixPath(relative).parts)
        if path.is_symlink() or not path.is_file():
            raise ExplorationPackageError(f"source package file is missing or unsafe: {relative}")
        payload = path.read_bytes()
        entry = source_files[relative]
        if len(payload) != entry.get("bytes") or _sha(payload) != entry.get("sha256"):
            raise ExplorationPackageError(f"source package hash mismatch: {relative}")
        return json.loads(payload.decode("utf-8")), payload

    phase2_ref = source_phases.get("phase2", {}).get("data_ref", PHASE_PATHS[2])
    phase3_ref = source_phases.get("phase3", {}).get("data_ref", PHASE_PATHS[3])
    phase2, _ = read_bound(phase2_ref)
    phase3, _ = read_bound(phase3_ref)
    if phase2.get("case_id") != source_package.get("case_id") or phase3.get("case_id") != source_package.get("case_id"):
        raise ExplorationPackageError("source Phase 2/3 identities disagree with source package")

    temp_parent = release_root.parent
    temp_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{release_id}-", dir=temp_parent))
    staged_case = staging / "cases" / case_id
    try:
        phase2["case_id"] = case_id
        phase3["case_id"] = case_id
        phase1 = {"schema_version": "1.0.0", "case_id": case_id, "status": "UNAVAILABLE", "sections": []}
        phase6 = {
            "schema_version": "1.0.0", "case_id": case_id, "status": "UNAVAILABLE", "models": [],
            "readiness": {"predict_enabled": False, "reason_code": "NO_FINAL_MODEL_FOR_EXPLORATION_RUN",
                          "message": "This exploration run has no matching final-fit model for its selected configurations; local and online prediction are unavailable."},
        }
        case_document = {
            "schema_version": "1.0.0", "case_id": case_id,
            "title": "Ames Housing — Full Model Exploration",
            "case_status": "PARTIAL",
            "methodology_id": "historical-p4b-v2-full-model-exploration",
            "source": {"label": "Owner-authorized Ames Housing Development train.csv", "url": None, "license_review": "PENDING"},
            "target": {"raw_field_id": "SalePrice", "label": "SalePrice", "unit": "USD", "value_type": "number"},
            "language": "zh-Hant",
            "disclaimer": "Historical Development-CV exploration. Phase 5 publication review is pending; this case has no matching final-fit model or prediction service.",
        }
        _write_json(staged_case / "case.json", case_document)

        for phase, document in ((1, phase1), (2, phase2), (3, phase3), (4, phase4), (5, phase5), (6, phase6)):
            relative = PHASE_PATHS[phase]
            _write_json(staged_case / relative, document)
            _validate_schema(document, repo / SCHEMAS[phase])

        source_figure_refs: set[str] = set()
        def find_fig_refs(value: Any) -> None:
            if isinstance(value, Mapping):
                for key, child in value.items():
                    if key in {"image_ref", "table_ref"} and isinstance(child, str) and child.startswith("phases/phase-02/"):
                        source_figure_refs.add(child)
                    find_fig_refs(child)
            elif isinstance(value, list):
                for child in value:
                    find_fig_refs(child)
        find_fig_refs(phase2)
        figure_entries = []
        for relative in sorted(source_figure_refs):
            if relative not in source_files:
                raise ExplorationPackageError(f"Phase 2 figure is not source-manifest-bound: {relative}")
            source_path = source_root.joinpath(*PurePosixPath(relative).parts)
            payload = source_path.read_bytes()
            entry = source_files[relative]
            if _sha(payload) != entry.get("sha256") or len(payload) != entry.get("bytes"):
                raise ExplorationPackageError(f"Phase 2 figure source hash mismatch: {relative}")
            target = staged_case.joinpath(*PurePosixPath(relative).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            figure_entries.append({"path": relative, "sha256": _sha(payload), "bytes": len(payload), "mime": entry.get("mime")})

        for relative, value in list(phase4_artifacts.items()) + list(phase5_artifacts.items()):
            if not _safe_ref(relative) or not relative.startswith(("phases/phase-04/", "phases/phase-05/")):
                raise ExplorationPackageError("generated aggregate artifact has an unsafe package path")
            _write_json(staged_case / relative, value)
        for relative, value in {
            "assets/figure-manifest.json": {"schema_version": "1.0.0", "case_id": case_id, "figures": figure_entries},
            "assets/phase6-inference-smoke.json": {
                "schema_version": "1.0.0", "case_id": case_id,
                "status": "UNAVAILABLE", "prediction_value_included": False,
                "reason_code": "NO_MATCHING_FINAL_MODEL",
            },
            "assets/execution-manifest.json": {
                "schema_version": "1.0.0", "case_id": case_id, "release_id": release_id,
                "source_data_sha256": source_data_sha256,
                "phase_runs": {
                    "phase1": None,
                    "phase2": source_package.get("phases", {}).get("phase2", {}).get("run_id"),
                    "phase3": source_package.get("phases", {}).get("phase3", {}).get("run_id"),
                    "phase4": phase4["execution_runs"][0]["execution_run_id"],
                    "phase5": phase5["evaluations"][0]["execution_run_id"] if phase5.get("evaluations") else None,
                    "phase6": None,
                },
                "phase2_source_case_id": source_package.get("case_id"),
                "phase2_source_package_sha256": _sha((source_root / "package.json").read_bytes()),
                "phase4_source_summary_sha256": phase4["execution_runs"][0]["source_manifest_sha256"],
                "phase4_candidate_count": len(phase4["configurations"]),
                "phase5_metric_evaluation_count": len(phase5.get("evaluations", [])),
            },
        }.items():
            _write_json(staged_case / relative, value)

        phase_status = {
            "phase1": "UNAVAILABLE", "phase2": phase2.get("status", "UNAVAILABLE"),
            "phase3": phase3.get("status", "UNAVAILABLE"), "phase4": phase4.get("status", "UNAVAILABLE"),
            "phase5": phase5.get("status", "PLANNED"), "phase6": "UNAVAILABLE",
        }
        package = {
            "package_schema_version": "1.0.0",
            "package_id": f"{case_id}-{phase4['execution_runs'][0]['execution_run_id']}",
            "case_id": case_id, "package_revision": release_id, "package_status": "PARTIAL",
            "publication": {"approved": False, "release_id": release_id, "review_status": "PENDING"},
            "case_ref": "case.json",
            "phases": {f"phase{phase}": {"status": phase_status[f"phase{phase}"], "data_ref": PHASE_PATHS[phase]} for phase in range(1, 7)},
            "asset_manifest_ref": "assets/figure-manifest.json",
        }
        package["files"] = _file_manifest(staged_case)
        _write_json(staged_case / "package.json", package)
        validation = validate_model_exploration_package(staged_case, repo)
        release_root.mkdir(parents=True, exist_ok=False)
        final_case = release_root / "cases" / case_id
        final_case.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged_case), str(final_case))
        return validation
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def validate_model_exploration_package(package_root: str | Path, repository_root: str | Path) -> dict[str, Any]:
    root = Path(package_root)
    repo = Path(repository_root)
    package = _read_json(root / "package.json")
    case_id = package.get("case_id")
    if package.get("package_status") != "PARTIAL" or package.get("publication", {}).get("approved") is not False:
        raise ExplorationPackageError("exploration case must remain partial and unpublished pending review")
    indexed = {item.get("path"): item for item in package.get("files", [])}
    if len(indexed) != len(package.get("files", [])):
        raise ExplorationPackageError("duplicate package manifest path")
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.name != "package.json"}
    if actual != set(indexed):
        raise ExplorationPackageError("package files do not match its manifest")
    for relative, entry in indexed.items():
        if not _safe_ref(relative) or "private" in PurePosixPath(relative).parts or Path(relative).suffix.lower() in {".csv", ".joblib", ".pkl", ".pickle"}:
            raise ExplorationPackageError("private or unsafe artifact path in public package")
        path = root.joinpath(*PurePosixPath(relative).parts)
        if path.is_symlink() or not path.is_file():
            raise ExplorationPackageError("unsafe or missing package artifact")
        payload = path.read_bytes()
        if len(payload) != entry.get("bytes") or _sha(payload) != entry.get("sha256"):
            raise ExplorationPackageError(f"package artifact SHA mismatch: {relative}")
        if relative.endswith(".json"):
            document = json.loads(payload.decode("utf-8"))
            if _contains_row_record(document):
                raise ExplorationPackageError("row-level records are not allowed in the public package")
            text = payload.decode("utf-8").lower()
            if any(token in text for token in ("/users/", "local/", "file://", "private/", "phase4-oof-predictions.csv", ".joblib")):
                raise ExplorationPackageError("local path or private artifact reference in public package")

    if package.get("case_ref") not in indexed or package.get("asset_manifest_ref") not in indexed:
        raise ExplorationPackageError("case document or figure manifest is not package-bound")
    case_document = _read_json(root / package["case_ref"])
    if case_document.get("case_id") != case_id or case_document.get("case_status") != package.get("package_status"):
        raise ExplorationPackageError("Case document identity/status mismatch")

    documents = {}
    for phase, relative in PHASE_PATHS.items():
        if relative not in indexed:
            raise ExplorationPackageError(f"Phase {phase} document is not in package manifest")
        document = _read_json(root / relative)
        if document.get("case_id") != case_id or document.get("status") != package["phases"][f"phase{phase}"]["status"]:
            raise ExplorationPackageError(f"Phase {phase} identity/status mismatch")
        _validate_schema(document, repo / SCHEMAS[phase])
        documents[phase] = document

    for phase in (2,):
        def check_refs(value: Any) -> None:
            if isinstance(value, Mapping):
                for key, child in value.items():
                    if key in {"image_ref", "table_ref"} and child is not None and child not in indexed:
                        raise ExplorationPackageError("Phase 2 figure reference is unresolved")
                    check_refs(child)
            elif isinstance(value, list):
                for child in value: check_refs(child)
        check_refs(documents[phase])

    phase4 = documents[4]
    run_ids = {run["execution_run_id"] for run in phase4["execution_runs"]}
    config_ids = {item["configuration_id"] for item in phase4["configurations"]}
    for config in phase4["configurations"]:
        if config["execution_run_id"] not in run_ids:
            raise ExplorationPackageError("Phase 4 configuration run binding is invalid")
        for key in ("metadata_ref", "fold_tasks_ref", "cv_metrics_ref", "selected_features_ref"):
            ref = config.get(key)
            if not ref or ref not in indexed:
                raise ExplorationPackageError("Phase 4 configuration evidence reference is unresolved")
        for key in ("metadata_ref", "fold_tasks_ref", "cv_metrics_ref", "selected_features_ref"):
            evidence = _read_json(root / config[key])
            if evidence.get("case_id") != case_id or evidence.get("run_id") != config["execution_run_id"]:
                raise ExplorationPackageError("Phase 4 evidence identity mismatch")
            if evidence.get("configuration_id") != config["configuration_id"]:
                raise ExplorationPackageError("Phase 4 evidence configuration mismatch")
    for chart in phase4.get("charts", []):
        if chart.get("points_ref") not in indexed:
            raise ExplorationPackageError("Phase 4 chart points are not package-bound")

    phase5 = documents[5]
    fold_ref = "phases/phase-05/fold-metrics.json"
    pooled_ref = "phases/phase-05/pooled-oof-metrics.json"
    if fold_ref not in indexed or pooled_ref not in indexed:
        raise ExplorationPackageError("Phase 5 aggregate evidence is not package-bound")
    fold_evidence = _read_json(root / fold_ref)
    pooled_evidence = _read_json(root / pooled_ref)
    if fold_evidence.get("run_id") != pooled_evidence.get("run_id"):
        raise ExplorationPackageError("Phase 5 aggregate evidence run identities disagree")
    source_oof_sha = fold_evidence.get("source_oof_sha256")
    data_sha = fold_evidence.get("development_data_sha256")
    fold_sha = fold_evidence.get("fold_sha256")
    if (not isinstance(source_oof_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", source_oof_sha)
            or not isinstance(data_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", data_sha)
            or not isinstance(fold_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", fold_sha)):
        raise ExplorationPackageError("Phase 5 OOF/data/fold evidence digests are invalid")
    if any(evidence.get(key) != value for evidence in (pooled_evidence,)
           for key, value in (("source_oof_sha256", source_oof_sha),
                              ("development_data_sha256", data_sha), ("fold_sha256", fold_sha))):
        raise ExplorationPackageError("Phase 5 OOF/data/fold evidence identities disagree")
    run_by_id = {item["execution_run_id"]: item for item in phase4["execution_runs"]}
    if fold_evidence.get("run_id") not in run_by_id:
        raise ExplorationPackageError("Phase 5 evidence run does not resolve to Phase 4")
    execution_manifest = _read_json(root / "assets/execution-manifest.json")
    if (execution_manifest.get("phase_runs", {}).get("phase4") != fold_evidence.get("run_id")
            or execution_manifest.get("phase_runs", {}).get("phase5") != fold_evidence.get("run_id")):
        raise ExplorationPackageError("Phase 4/5 execution manifest binding is inconsistent")

    phase4_by_id = {item["configuration_id"]: item for item in phase4["configurations"]}
    fold_configs = {item.get("configuration_id"): item for item in fold_evidence.get("configurations", [])}
    pooled_configs = {item.get("configuration_id"): item for item in pooled_evidence.get("configurations", [])}
    if len(fold_configs) != len(fold_evidence.get("configurations", [])) or set(fold_configs) != set(pooled_configs):
        raise ExplorationPackageError("Phase 5 aggregate configuration coverage is inconsistent")
    for configuration_id, fold_config in fold_configs.items():
        config = phase4_by_id.get(configuration_id)
        if not config or config.get("status") != "VERIFIED" or config.get("execution_run_id") != fold_evidence.get("run_id"):
            raise ExplorationPackageError("Phase 5 aggregate configuration does not bind to verified Phase 4")
        metadata = _read_json(root / config["metadata_ref"])
        cv_metrics = _read_json(root / config["cv_metrics_ref"])
        if fold_config.get("config_hash") != metadata.get("historical_config_hash"):
            raise ExplorationPackageError("Phase 5 fold configuration identity is inconsistent")
        if any(evidence.get(key) != value for evidence in (metadata, cv_metrics)
               for key, value in (("data_sha256", data_sha), ("fold_sha256", fold_sha))):
            raise ExplorationPackageError("Phase 5 data/fold digests do not match Phase 4")
        cv_folds = {item.get("fold"): item for item in cv_metrics.get("fold_results", [])}
        reported_folds = {item.get("fold"): item for item in fold_config.get("folds", [])}
        if set(cv_folds) != {0, 1, 2} or set(reported_folds) != {0, 1, 2}:
            raise ExplorationPackageError("Phase 5 fold metrics do not cover the Phase 4 folds")
        for fold_id, reported in reported_folds.items():
            for metric in ("rmse", "mae", "r2"):
                if not math.isclose(reported.get(metric, float("nan")), cv_folds[fold_id].get(metric, float("nan")),
                                    rel_tol=1e-10, abs_tol=1e-6):
                    raise ExplorationPackageError("Phase 5 fold metric does not match Phase 4")
        phase4_means = cv_metrics.get("mean_fold_metrics", {})
        for metric in ("rmse", "mae", "r2"):
            if not math.isclose(phase4_means.get(metric, float("nan")),
                                math.fsum(item[metric] for item in reported_folds.values()) / 3,
                                rel_tol=1e-10, abs_tol=1e-6):
                raise ExplorationPackageError("Phase 5 mean metric does not match Phase 4 folds")
        pooled_config = pooled_configs[configuration_id]
        if pooled_config.get("config_hash") != metadata.get("historical_config_hash"):
            raise ExplorationPackageError("Phase 5 pooled metric configuration identity is inconsistent")

    evaluation_ids = {item["evaluation_id"] for item in phase5["evaluations"]}
    evaluation_by_key = {(item.get("configuration_id"), item.get("metric_source")): item
                         for item in phase5["evaluations"]}
    if len(evaluation_by_key) != len(phase5["evaluations"]):
        raise ExplorationPackageError("Phase 5 evaluation configuration/source pair is duplicated")
    for evaluation in phase5["evaluations"]:
        if (evaluation["configuration_id"] not in config_ids
                or evaluation["execution_run_id"] != fold_evidence.get("run_id")
                or evaluation["execution_run_id"] not in run_ids):
            raise ExplorationPackageError("Phase 5 evaluation does not bind to Phase 4")
        if evaluation.get("evidence", {}).get("source_ref") is not None:
            raise ExplorationPackageError("public Phase 5 cannot expose OOF row references")
        if evaluation.get("evidence", {}).get("source_artifact_sha256") != source_oof_sha:
            raise ExplorationPackageError("Phase 5 evaluation OOF source digest is inconsistent")
        for metric in evaluation["metrics"].values():
            ref = metric.get("evidence_ref")
            if ref and ref not in indexed:
                raise ExplorationPackageError("Phase 5 metric evidence reference is unresolved")
        if any(link not in evaluation_ids for link in evaluation["linked_evaluation_ids"]):
            raise ExplorationPackageError("Phase 5 linked evaluation is unresolved")
        metric_source = evaluation.get("metric_source")
        if metric_source == "cv_fold_mean":
            expected = _read_json(root / phase4_by_id[evaluation["configuration_id"]]["cv_metrics_ref"])["mean_fold_metrics"]
        elif metric_source == "pooled_oof":
            expected = pooled_configs[evaluation["configuration_id"]].get("pooled_oof_metrics", {})
        else:
            raise ExplorationPackageError("Phase 5 metric source is unsupported")
        for metric in ("mae", "rmse", "r2"):
            actual = evaluation["metrics"][metric]["value"]
            if not math.isclose(actual, expected.get(metric, float("nan")), rel_tol=1e-10, abs_tol=1e-6):
                raise ExplorationPackageError("Phase 5 evaluation value does not match its bound evidence")
    if documents[6]["models"] or documents[6]["readiness"]["predict_enabled"]:
        raise ExplorationPackageError("exploration case cannot claim a model without matching final-fit evidence")
    return {"status": "PASS", "case_id": case_id, "file_count": len(indexed),
            "configuration_count": len(config_ids), "phase5_evaluation_count": len(phase5["evaluations"]),
            "package_status": package["package_status"], "raw_oof_included": False, "model_binary_included": False}
