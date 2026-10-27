"""Create a manifest-verified public Case Package without private row/model artifacts."""

from __future__ import annotations

import copy
import hashlib
import json
import mimetypes
import os
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from housing_regression.contracts import validate_document
from housing_regression.reference_e2e import (
    CASE_ID,
    PHASE_PATHS,
    SCHEMAS,
    ReferenceE2EError,
    _json,
    _sha,
    validate_private_reference_package,
)


class PublicPackageError(ValueError):
    """A private reference package cannot be safely exported for static hosting."""


FORBIDDEN_SUFFIXES = {".csv", ".tsv", ".joblib", ".pkl", ".pickle", ".parquet"}
PUBLIC_NOTICE_REF = "assets/public-release-notice.json"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _public_copy(source_root: Path, destination_root: Path, relative: str, release_id: str) -> None:
    ref = PurePosixPath(relative)
    if ref.is_absolute() or ".." in ref.parts or "\\" in relative or "private" in ref.parts:
        raise PublicPackageError(f"private or unsafe path cannot be exported: {relative}")
    if Path(relative).suffix.lower() in FORBIDDEN_SUFFIXES:
        raise PublicPackageError(f"row/model artifact cannot be exported: {relative}")
    source = source_root.joinpath(*ref.parts)
    target = destination_root.joinpath(*ref.parts)
    if source.is_symlink() or not source.is_file():
        raise PublicPackageError(f"missing or unsafe source asset: {relative}")
    payload = source.read_bytes()
    if source.suffix.lower() == ".json":
        try:
            value = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PublicPackageError(f"invalid source JSON: {relative}") from exc
        if relative.endswith("/fold-tasks.json"):
            value["oof_artifact_ref"] = None
            value["predictions_included"] = False
        elif relative.endswith("/metadata.json") and "/phase-04/configurations/" in relative:
            value["oof_artifact_ref"] = None
        elif relative == PHASE_PATHS[5]:
            for evaluation in value.get("evaluations", []):
                evidence = evaluation.get("evidence")
                if isinstance(evidence, dict):
                    evidence["source_ref"] = None
            value["release_id"] = release_id
        elif relative == "assets/phase6-inference-smoke.json":
            value.pop("prediction_value", None)
            value["prediction_value_included"] = False
        payload = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def validate_public_reference_package(package_root: str | Path) -> dict[str, Any]:
    """Validate schemas, bundle bytes, references, and absence of private files/values."""
    root = Path(package_root)
    package = _json(root / "package.json")
    if package.get("case_id") != CASE_ID or set(package.get("phases", {})) != {f"phase{i}" for i in range(1, 7)}:
        raise PublicPackageError("public package identity or phase references are invalid")
    indexed = {entry["path"]: entry for entry in package.get("files", [])}
    if len(indexed) != len(package.get("files", [])):
        raise PublicPackageError("duplicate public package file path")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name != "package.json"}
    if actual != set(indexed):
        raise PublicPackageError("public manifest does not exactly cover package files")
    for relative, entry in indexed.items():
        ref = PurePosixPath(relative)
        if ref.is_absolute() or ".." in ref.parts or "\\" in relative or "private" in ref.parts:
            raise PublicPackageError(f"unsafe or private public path: {relative}")
        if Path(relative).suffix.lower() in FORBIDDEN_SUFFIXES:
            raise PublicPackageError(f"forbidden public artifact type: {relative}")
        path = root.joinpath(*ref.parts)
        if path.is_symlink() or not path.is_file():
            raise PublicPackageError(f"missing or unsafe public artifact: {relative}")
        payload = path.read_bytes()
        if len(payload) != entry["bytes"] or _sha(payload) != entry["sha256"]:
            raise PublicPackageError(f"public artifact hash/size mismatch: {relative}")
    documents = {}
    repo_root = Path(__file__).resolve().parents[3]
    for phase, expected_ref in PHASE_PATHS.items():
        phase_entry = package["phases"][f"phase{phase}"]
        ref = phase_entry.get("data_ref")
        if ref != expected_ref or ref not in indexed:
            raise PublicPackageError(f"Phase {phase} is not bundle-bound")
        document = _json(root / ref)
        if document.get("case_id") != CASE_ID or document.get("status") != phase_entry.get("status"):
            raise PublicPackageError(f"Phase {phase} identity/status mismatch")
        validate_document(document, repo_root / SCHEMAS[phase])
        documents[phase] = document
    def require_ref(ref: Any, label: str) -> None:
        if not isinstance(ref, str):
            raise PublicPackageError(f"missing package reference: {label}")
        safe = PurePosixPath(ref)
        if safe.is_absolute() or ".." in safe.parts or "\\" in ref or ref not in indexed:
            raise PublicPackageError(f"unresolved or unsafe package reference: {label}")

    require_ref(package.get("case_ref"), "case")
    require_ref(package.get("asset_manifest_ref"), "figure manifest")
    for analysis in documents[2].get("analyses", []):
        if analysis.get("image_ref"):
            require_ref(analysis["image_ref"], "Phase 2 figure")
    for config in documents[4].get("configurations", []):
        for key in ("metadata_ref", "fold_tasks_ref", "cv_metrics_ref"):
            if config.get(key):
                require_ref(config[key], f"Phase 4 {key}")
    require_ref("assets/phase6-inference-smoke.json", "Phase 6 smoke summary")
    for model in documents[6].get("models", []):
        require_ref(model.get("input_schema_ref"), "Phase 6 input schema")
    for phase in (4, 5, 6):
        run = documents[4]["execution_runs"][0]["execution_run_id"]
        config_ids = {item["configuration_id"] for item in documents[4]["configurations"]}
        if phase == 5:
            for evaluation in documents[5].get("evaluations", []):
                if evaluation["execution_run_id"] != run or evaluation["configuration_id"] not in config_ids:
                    raise PublicPackageError("Phase 5 source binding does not resolve to Phase 4")
                if evaluation.get("evidence", {}).get("source_ref") is not None:
                    raise PublicPackageError("public Phase 5 must not link to private OOF rows")
                for figure in evaluation.get("figures", []):
                    for key in ("asset_ref", "accessible_table_ref"):
                        if figure.get(key):
                            require_ref(figure[key], f"Phase 5 {key}")
                for metric in evaluation.get("metrics", {}).values():
                    if metric.get("evidence_ref"):
                        require_ref(metric["evidence_ref"], "Phase 5 metric evidence")
        if phase == 6:
            for model in documents[6].get("models", []):
                if model["source_execution_run_id"] != run or model["source_configuration_id"] not in config_ids:
                    raise PublicPackageError("Phase 6 source binding does not resolve to Phase 4")
    smoke = _json(root / "assets/phase6-inference-smoke.json")
    if "prediction_value" in smoke or smoke.get("prediction_value_included") is not False:
        raise PublicPackageError("private one-record inference value must be suppressed")
    def contains_row_record(value: Any) -> bool:
        if isinstance(value, dict):
            if "row_id" in value or {"actual", "predicted"}.issubset(value):
                return True
            return any(contains_row_record(child) for child in value.values())
        if isinstance(value, list):
            return any(contains_row_record(child) for child in value)
        return False

    for path in root.rglob("*.json"):
        text = path.read_text(encoding="utf-8").lower()
        value = json.loads(text)
        if (contains_row_record(value) or "/users/" in text or "local/" in text or "file://" in text):
            raise PublicPackageError(f"row-level prediction records found in {path.relative_to(root)}")
        if "private/phase4-oof-predictions.csv" in text or "phase6-development-model.joblib" in text:
            raise PublicPackageError(f"private artifact reference found in {path.relative_to(root)}")
    return {"status": "PASS", "case_id": CASE_ID, "phase_count": 6, "file_count": len(indexed),
            "package_status": package["package_status"], "private_artifacts_included": False}


def export_public_reference_package(
    source_package: str | Path,
    release_root: str | Path,
    release_id: str,
) -> dict[str, Any]:
    """Export the already validated real-data package into an immutable static release directory.

    The destination must be a new `web/data/releases/<release_id>/cases/<case_id>` directory.
    Existing releases are never overwritten.
    """
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,79}", release_id):
        raise PublicPackageError("release_id must be a lowercase URL-safe identifier")
    source = Path(source_package)
    release = Path(release_root)
    repo_root = Path(__file__).resolve().parents[3]
    expected_parent = (repo_root / "web/data/releases").resolve()
    release_dir = release.resolve()
    if not release_dir.is_relative_to(expected_parent):
        raise PublicPackageError("public release must stay under web/data/releases")
    if release_dir.name != release_id:
        raise PublicPackageError("release directory name must equal release_id")
    target = release_dir / "cases" / CASE_ID
    if target.exists() or target.is_symlink():
        raise PublicPackageError("refusing to overwrite an existing public Case Package")
    try:
        private_validation = validate_private_reference_package(source)
    except (ReferenceE2EError, OSError, json.JSONDecodeError) as exc:
        raise PublicPackageError(f"source private package failed validation: {exc}") from exc
    release_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{release_id}-", dir=release_dir.parent))
    staged_case = staging / "cases" / CASE_ID
    try:
        private_package = _json(source / "package.json")
        for entry in private_package["files"]:
            relative = entry["path"]
            if relative.startswith("private/"):
                continue
            _public_copy(source, staged_case, relative, release_id)
        _write_json(staged_case / PUBLIC_NOTICE_REF, {
            "schema_version": "1.0.0", "release_id": release_id, "case_id": CASE_ID,
            "data_scope": "aggregate Development research output",
            "excluded_artifacts": ["row-level Development OOF CSV", "fitted model binary", "one-record inference value"],
            "phase5_publication_review": "PENDING",
            "phase6_remote_inference": "UNAVAILABLE",
        })
        package = copy.deepcopy(private_package)
        package["package_revision"] = release_id
        package["publication"] = {"approved": False, "release_id": release_id, "review_status": "PENDING"}
        package["files"] = []
        for path in sorted(p for p in staged_case.rglob("*") if p.is_file() and p.name != "package.json"):
            relative = path.relative_to(staged_case).as_posix()
            package["files"].append({"path": relative, "sha256": _sha(path.read_bytes()), "bytes": path.stat().st_size,
                                     "mime": mimetypes.guess_type(relative)[0] or "application/octet-stream"})
        _write_json(staged_case / "package.json", package)
        status = validate_public_reference_package(staged_case)
        # Move the complete staged release as one directory to keep it immutable.
        if release_dir.exists():
            raise PublicPackageError("release destination unexpectedly appeared during export")
        staging.rename(release_dir)
        return {**status, "release_id": release_id, "package_root": str(target),
                "source_validation": private_validation}
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
