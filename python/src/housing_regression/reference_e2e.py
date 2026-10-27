"""Orchestrate one source-bound INIT B Development OOF → evaluation → local model package."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from housing_regression.contracts import validate_document
from housing_regression.phase5_evaluation import build_development_oof_evaluation
from housing_regression.reference_baseline import (
    REFERENCE_TRAIN_SHA256,
    fit_and_persist_reference_model,
    load_reference_config,
    run_fixed_lasso_cv,
)


class ReferenceE2EError(ValueError):
    """The real-data Development E2E cannot safely produce a complete package."""


CASE_ID = "ames-reference-init-a"
CONFIGURATION_ID = "ames-lasso100-primary-ols-3fold-v1"
PROTOCOL_ID = "historical-p4b-v2-fixed-lasso100"
PHASE_PATHS = {
    1: "phases/phase-01/content.json", 2: "phases/phase-02/analyses.json",
    3: "phases/phase-03/preparation.json", 4: "phases/phase-04/modeling.json",
    5: "phases/phase-05/evaluations.json", 6: "phases/phase-06/inference-catalog.json",
}
SCHEMAS = {
    1: "docs/design/data-contracts/schemas/phase-01.schema.json",
    2: "docs/design/data-contracts/schemas/phase-02.schema.json",
    3: "docs/design/data-contracts/schemas/phase-03.schema.json",
    4: "docs/design/data-contracts/schemas/phase-04.schema.json",
    5: "docs/ui-ux/case-package/phase-05/evaluation-index.schema.json",
    6: "docs/design/data-contracts/schemas/phase-06.schema.json",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _copy_verified(prior_root: Path, output_root: Path, relative: str) -> dict[str, Any]:
    source = prior_root / relative
    if source.is_symlink() or not source.is_file():
        raise ReferenceE2EError(f"reusable Phase 2/3 artifact is missing or unsafe: {relative}")
    target = output_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        raise ReferenceE2EError(f"refusing to overwrite package evidence: {relative}")
    shutil.copyfile(source, target)
    payload = target.read_bytes()
    if _sha(payload) != _sha(source.read_bytes()):
        raise ReferenceE2EError(f"reused artifact copy SHA mismatch: {relative}")
    return {"path": relative, "sha256": _sha(payload), "bytes": len(payload), "reused": True}


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReferenceE2EError(f"expected JSON object: {path.name}")
    return value


def _manifest_files(root: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "package.json"):
        if path.is_symlink():
            raise ReferenceE2EError("package may not include symlinks")
        relative = path.relative_to(root).as_posix()
        entries.append({"path": relative, "sha256": _sha(path.read_bytes()), "bytes": path.stat().st_size,
                        "mime": mimetypes.guess_type(relative)[0] or "application/octet-stream"})
    return entries


def validate_private_reference_package(package_root: str | Path) -> dict[str, Any]:
    """Strict local-only package validation, allowing source-bound private OOF/model assets."""
    root = Path(package_root)
    package = _json(root / "package.json")
    if package.get("case_id") != CASE_ID or set(package.get("phases", {})) != {f"phase{i}" for i in range(1, 7)}:
        raise ReferenceE2EError("Case Package identity or phase map is invalid")
    files = package.get("files")
    indexed = {item["path"]: item for item in files}
    if len(indexed) != len(files):
        raise ReferenceE2EError("Case Package file manifest has duplicate paths")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name != "package.json"}
    if actual != set(indexed):
        raise ReferenceE2EError("Case Package manifest does not exactly cover local files")
    docs = {}
    for phase, ref in PHASE_PATHS.items():
        entry = package["phases"][f"phase{phase}"]
        if entry.get("data_ref") != ref or ref not in indexed:
            raise ReferenceE2EError(f"Phase {phase} reference is missing from package manifest")
        doc = _json(root / ref)
        if doc.get("case_id") != CASE_ID or doc.get("status") != entry.get("status"):
            raise ReferenceE2EError(f"Phase {phase} identity/status mismatch")
        validate_document(doc, Path(__file__).resolve().parents[3] / SCHEMAS[phase])
        docs[phase] = doc
    for relative, entry in indexed.items():
        ref = PurePosixPath(relative)
        if ref.is_absolute() or ".." in ref.parts or "\\" in relative:
            raise ReferenceE2EError("unsafe Case Package file reference")
        data = (root / Path(*ref.parts)).read_bytes()
        if len(data) != entry["bytes"] or _sha(data) != entry["sha256"]:
            raise ReferenceE2EError(f"Case Package SHA/byte mismatch: {relative}")
    manifest_ref = package["asset_manifest_ref"]
    if manifest_ref not in indexed or _json(root / manifest_ref).get("case_id") != CASE_ID:
        raise ReferenceE2EError("figure manifest identity/reference mismatch")
    phase4_runs = {item["execution_run_id"] for item in docs[4]["execution_runs"]}
    phase4_configs = {item["configuration_id"]: item for item in docs[4]["configurations"]}
    for evaluation in docs[5]["evaluations"]:
        if evaluation["execution_run_id"] not in phase4_runs or evaluation["configuration_id"] not in phase4_configs:
            raise ReferenceE2EError("Phase 5 run/config references do not resolve to Phase 4")
    for model in docs[6]["models"]:
        if model["source_execution_run_id"] not in phase4_runs or model["source_configuration_id"] not in phase4_configs:
            raise ReferenceE2EError("Phase 6 model references do not resolve to Phase 4")
    oof_meta = _json(root / "private/phase4-oof-predictions.csv.metadata.json")
    if oof_meta.get("oof_sha256") != indexed["private/phase4-oof-predictions.csv"]["sha256"]:
        raise ReferenceE2EError("OOF metadata digest differs from Case Package files[]")
    return {"status": "PASS", "case_id": CASE_ID, "phase_count": 6, "file_count": len(files),
            "package_status": package["package_status"], "oof_rows": oof_meta["row_count"]}


def run_reference_e2e(
    *, config_path: str | Path, prior_package_root: str | Path,
    package_root: str | Path, run_id: str, code_head: str,
) -> dict[str, Any]:
    """Run fixed Development CV OOF, Phase 5, final local model and one package assembly.

    Previously validated Phase 2/3 artifacts are reused only after matching source,
    INIT B config and phase-transform fingerprints; all later phases use this run ID.
    """
    config = load_reference_config(config_path)
    if _sha(config.source_csv.read_bytes()) != REFERENCE_TRAIN_SHA256:
        raise ReferenceE2EError("formal train.csv fingerprint changed")
    prior = Path(prior_package_root)
    output = Path(package_root)
    if output.exists() or output.is_symlink():
        raise ReferenceE2EError("refusing to overwrite prior run or evidence")
    if prior.is_symlink() or not prior.is_dir() or output.parent.is_symlink() or not output.parent.is_dir():
        raise ReferenceE2EError("package roots must be existing safe directories")
    output.mkdir(exist_ok=False)
    for rel in [PHASE_PATHS[2], "phases/phase-02/figures/missingness.svg", "phases/phase-02/figures/target-distribution.svg", PHASE_PATHS[3]]:
        _copy_verified(prior, output, rel)
    phase2 = _json(output / PHASE_PATHS[2])
    phase3 = _json(output / PHASE_PATHS[3])
    if phase2["status"] != "VERIFIED" or phase3["status"] != "VERIFIED":
        raise ReferenceE2EError("reusable Phase 2/3 outputs are not verified")
    if phase3.get("case_id") != CASE_ID or phase3.get("split", {}).get("training_rows") != 1168 or phase3.get("stages", [])[-1].get("total") != 248:
        raise ReferenceE2EError("reusable Phase 3 output does not match INIT B contract")
    p1 = {"schema_version": "1.0.0", "case_id": CASE_ID, "status": "UNAVAILABLE", "sections": []}
    validate_document(p1, Path(__file__).resolve().parents[3] / SCHEMAS[1])
    _write(output / PHASE_PATHS[1], p1)

    private = output / "private"
    private.mkdir()
    oof_path = private / "phase4-oof-predictions.csv"
    phase4_result = run_fixed_lasso_cv(config_path, code_head=code_head, run_id=run_id, oof_output_path=oof_path)
    p5 = build_development_oof_evaluation(
        oof_path=oof_path, metadata_path=oof_path.with_suffix(oof_path.suffix + ".metadata.json"),
        output_root=output, run_id=run_id, configuration_id=CONFIGURATION_ID,
        config_sha256=config.config_sha256, source_sha256=_sha(config.source_csv.read_bytes()),
        development_data_sha256=phase4_result["data_sha256"], fold_sha256=phase4_result["fold_sha256"],
        phase4_summary=phase4_result,
        schema_path=Path(__file__).resolve().parents[3] / SCHEMAS[5],
    )
    _write(output / PHASE_PATHS[5], p5["index"])

    model_path = output / "private/phase6-development-model.joblib"
    phase6_result = fit_and_persist_reference_model(config_path, model_path, code_head=code_head, run_id=run_id)
    input_schema_ref = "assets/phase6-input-schema.json"
    _write(output / input_schema_ref, {"schema_version": "1.0.0", "case_id": CASE_ID,
        "predictor_count": 79, "target_excluded": True, "id_excluded": True,
        "columns": "Ames Housing train.csv predictor columns, exact canonical names; values are private and omitted."})
    _write(output / "assets/phase6-inference-smoke.json", {
        "status": "PASS", "run_id": run_id, "configuration_id": CONFIGURATION_ID,
        "model_sha256": phase6_result["model_sha256"], "reload_verified": True,
        "local_inference_verified": True, "prediction_finite": True,
        "prediction_value": phase6_result["prediction_value"], "input_scope": "one_development_training_record",
        "validation_partition_used": False, "deployable": False,
    })
    p6 = {"schema_version": "1.0.0", "case_id": CASE_ID, "status": "VERIFIED",
          "models": [{"model_id": phase6_result["model_id"], "model_version": run_id,
                      "source_execution_run_id": run_id, "source_configuration_id": CONFIGURATION_ID,
                      "model_status": "LOCAL_PRIVATE_VERIFIED", "input_schema_ref": input_schema_ref,
                      "readiness": {"predict_enabled": False, "scope": "local_only", "model_sha256": phase6_result["model_sha256"],
                                    "reload_verified": True, "local_inference_verified": True, "deployment": "NOT_DEPLOYED"}}],
          "readiness": {"predict_enabled": False, "reason_code": "LOCAL_ONLY_NO_SERVICE",
                        "message": "Development model was persisted, reloaded, and locally smoke-predicted; no public API or deployment is enabled."}}
    _write(output / PHASE_PATHS[6], p6)

    phase4_doc = _json(prior / PHASE_PATHS[4])
    phase4_doc["execution_runs"][0]["execution_run_id"] = run_id
    phase4_doc["execution_runs"][0]["status"] = "VERIFIED"
    phase4_doc["configurations"][0]["execution_run_id"] = run_id
    phase4_doc["configurations"][0]["metadata_ref"] = f"phases/phase-04/configurations/{CONFIGURATION_ID}/metadata.json"
    phase4_doc["configurations"][0]["fold_tasks_ref"] = f"phases/phase-04/configurations/{CONFIGURATION_ID}/fold-tasks.json"
    phase4_doc["configurations"][0]["cv_metrics_ref"] = f"phases/phase-04/configurations/{CONFIGURATION_ID}/cv-metrics.json"
    cfg_dir = output / "phases/phase-04/configurations" / CONFIGURATION_ID
    cfg_dir.mkdir(parents=True)
    _write(cfg_dir / "metadata.json", {
        "schema_version": "1.0.0", "run_id": run_id, "code_head": code_head,
        "config_sha256": config.config_sha256, "source_sha256": _sha(config.source_csv.read_bytes()),
        "development_data_sha256": phase4_result["data_sha256"], "fold_sha256": phase4_result["fold_sha256"],
        "protocol": phase4_result["protocol"], "candidate_search": "NOT RUN",
        "oof_artifact_ref": "private/phase4-oof-predictions.csv", "oof_sha256": phase4_result["oof"]["oof_sha256"],
        "oof_metadata_ref": "private/phase4-oof-predictions.csv.metadata.json",
    })
    _write(cfg_dir / "fold-tasks.json", {"schema_version": "1.0.0", "run_id": run_id,
        "folds": phase4_result["fold_results"], "predictions_included": True,
        "oof_artifact_ref": "private/phase4-oof-predictions.csv", "oof_sha256": phase4_result["oof"]["oof_sha256"]})
    _write(cfg_dir / "cv-metrics.json", {"schema_version": "1.0.0", "case_id": CASE_ID,
        "run_id": run_id, "config_sha256": config.config_sha256, "data_sha256": phase4_result["data_sha256"],
        "fold_sha256": phase4_result["fold_sha256"], "protocol": phase4_result["protocol"],
        "candidate_search": "NOT RUN", "fold_results": phase4_result["fold_results"],
        "mean_fold_metrics": phase4_result["mean_fold_metrics"]})
    validate_document(phase4_doc, Path(__file__).resolve().parents[3] / SCHEMAS[4])
    _write(output / PHASE_PATHS[4], phase4_doc)

    case_doc = {"schema_version": "1.0.0", "case_id": CASE_ID,
        "title": "Ames Housing — INIT B Reference Baseline", "case_status": "PARTIAL",
        "methodology_id": PROTOCOL_ID,
        "source": {"label": "Owner-authorized Ames Housing Development train.csv", "url": None, "license_review": "PENDING"},
        "target": {"raw_field_id": "SalePrice", "label": "SalePrice", "unit": "USD", "value_type": "number"},
        "language": "zh-Hant", "disclaimer": "Local Development reproduction. Phase 5 is awaiting review; Phase 6 is local-only and not deployed."}
    _write(output / "case.json", case_doc)
    figure_manifest = _json(prior / "assets/figure-manifest.json")
    for fig in p5["figures"]:
        figure_manifest["figures"].append({"figure_id": fig["figure_id"],
            "source_evaluation_id": fig["evaluation_id"], "source_configuration_id": CONFIGURATION_ID,
            "svg_ref": None, "png_ref": fig["asset_ref"], "sha256_png": fig["sha256"], "status": "PENDING_REVIEW"})
    _write(output / "assets/figure-manifest.json", figure_manifest)
    phase_execution = {
        "run_id": run_id, "code_head": code_head, "config_sha256": config.config_sha256,
        "source_sha256": _sha(config.source_csv.read_bytes()), "case_id": CASE_ID,
        "owner_authorization": "RegScope Owner Pipeline 目標更正 2026-10-28",
        "phase2": {"artifact_sha256": _sha((output / PHASE_PATHS[2]).read_bytes()), "reused_from_run": "initb-reference-20261028-01"},
        "phase3": {"artifact_sha256": _sha((output / PHASE_PATHS[3]).read_bytes()), "reused_from_run": "initb-reference-20261028-01", "development_data_sha256": phase4_result["data_sha256"]},
        "phase4": {"oof_sha256": phase4_result["oof"]["oof_sha256"], "fold_sha256": phase4_result["fold_sha256"], "candidate_search": "NOT RUN"},
        "phase5": {"oof_sha256": p5["oof_sha256"], "rows": p5["row_count"], "metrics": p5["pooled_oof_metrics"], "publication_state": "PENDING_REVIEW"},
        "phase6": {"model_sha256": phase6_result["model_sha256"], "reload_verified": True, "local_inference_verified": True, "deployable": False},
    }
    _write(output / "assets/execution-manifest.json", phase_execution)
    package = {
        "package_schema_version": "1.0.0", "package_id": f"{CASE_ID}-{run_id}",
        "case_id": CASE_ID, "package_revision": f"initb-development-{run_id}",
        "package_status": "PARTIAL", "publication": {"approved": False, "release_id": None, "review_status": "NOT_REVIEWED"},
        "case_ref": "case.json", "phases": {}, "asset_manifest_ref": "assets/figure-manifest.json",
        "files": [],
    }
    for phase, ref in PHASE_PATHS.items():
        doc = _json(output / ref)
        package["phases"][f"phase{phase}"] = {"status": doc["status"], "data_ref": ref}
    package["files"] = _manifest_files(output)
    _write(output / "package.json", package)
    validation = validate_private_reference_package(output)
    return {"status": "PASS", "run_id": run_id, "config_sha256": config.config_sha256,
        "source_sha256": _sha(config.source_csv.read_bytes()), "package_root": str(output),
        "package_validation": validation, "phase2_reused": True, "phase3_reused": True,
        "phase4": phase4_result, "phase5": p5, "phase6": phase6_result,
        "phase_statuses": {f"{i}": package["phases"][f"phase{i}"]["status"] for i in range(1,7)}}
