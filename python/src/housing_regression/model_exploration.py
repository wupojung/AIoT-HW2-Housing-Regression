"""Export provenance-checked historical Phase 4 aggregates for Model Explorer.

This adapter consumes only the public aggregate summary and its manifest. It
does not execute estimators and deliberately rejects row-level prediction
records so the resulting package contains research summaries only.
"""

from __future__ import annotations

import hashlib
import json
import csv
import math
import re
from collections import Counter
from math import isclose
from statistics import mean, stdev
from typing import Any, Mapping
from pathlib import Path


METHOD_LABELS = {
    "ols_baseline": "All-feature OLS baseline",
    "pearson": "Pearson filter → OLS",
    "mutual_information": "Mutual Information → OLS",
    "lasso": "Lasso selection → OLS",
    "elastic_net": "ElasticNet selection → OLS",
    "ridge_rfe": "Ridge RFE → OLS",
}
EXPECTED_FOLDS = 3


class ModelExplorationError(ValueError):
    """Historical aggregate evidence is incomplete or inconsistent."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _reject_row_data(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        keys = {str(key).lower() for key in value}
        if {"actual", "predicted"}.issubset(keys) or "row_id" in keys or "oof_records" in keys:
            raise ModelExplorationError(f"row-level prediction material is not accepted at {path}")
        for key, child in value.items():
            _reject_row_data(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_row_data(child, f"{path}[{index}]")


def validate_historical_summary(
    summary: Mapping[str, Any],
    manifest: Mapping[str, Any],
    summary_bytes: bytes,
    manifest_bytes: bytes,
) -> dict[str, Any]:
    """Validate source identity, digest binding, and complete fold coverage."""
    _reject_row_data(summary)
    metadata = summary.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ModelExplorationError("historical summary metadata is missing")
    run_id = metadata.get("run_id")
    if run_id != "development_20261026_01" or manifest.get("run_id") != run_id:
        raise ModelExplorationError("summary and manifest do not identify the authorized historical run")
    inventory = manifest.get("file_inventory")
    if not isinstance(inventory, list):
        raise ModelExplorationError("historical manifest file inventory is missing")
    summary_entry = next((entry for entry in inventory if entry.get("relative_path") == "p4b_public_summary.json"), None)
    if not summary_entry or summary_entry.get("sha256") != sha256_bytes(summary_bytes):
        raise ModelExplorationError("historical summary SHA does not match its run manifest")
    if json.loads(manifest_bytes.decode("utf-8")) != manifest:
        raise ModelExplorationError("historical manifest bytes do not match the parsed manifest")
    provenance = manifest.get("dataset_provenance", {})
    boundary = metadata.get("data_boundary", {})
    expected_data = provenance.get("canonical_development_dataset_sha256")
    expected_folds = provenance.get("outer_fold_digest_expected")
    if (not expected_data or expected_data != boundary.get("dataset_fingerprint_verified_value", expected_data)
            or boundary.get("dataset_fingerprint_verified") is not True
            or boundary.get("digest_provenance") != "VERIFIED_MATCH"):
        raise ModelExplorationError("historical Development data fingerprint is not verified")
    if expected_folds != boundary.get("outer_fold_digest_expected"):
        raise ModelExplorationError("historical outer-fold digest does not match the manifest")
    rows = boundary.get("development_rows")
    folds = boundary.get("outer_kfold", {})
    if rows != 1168 or folds.get("n_splits") != EXPECTED_FOLDS or folds.get("random_state") != 42:
        raise ModelExplorationError("historical CV population/configuration differs from the expected Development run")
    if folds.get("shuffle") is not True:
        raise ModelExplorationError("historical CV shuffle setting is not verified")

    aggregates = summary.get("aggregate_results")
    fold_results = summary.get("per_outer_fold_results")
    if not isinstance(aggregates, list) or not isinstance(fold_results, list):
        raise ModelExplorationError("historical candidate or fold aggregates are missing")
    by_key: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    fold_digests: dict[int, set[str]] = {}
    for record in fold_results:
        if not isinstance(record, Mapping):
            raise ModelExplorationError("invalid fold aggregate record")
        if record.get("run_id") != run_id or record.get("data_digest") != expected_data:
            raise ModelExplorationError("fold record run/data identity mismatch")
        if not isinstance(record.get("fold_digest"), str):
            raise ModelExplorationError("fold record is missing its fold digest")
        fold_digests.setdefault(record.get("fold"), set()).add(record["fold_digest"])
        if record.get("seed") != 42:
            raise ModelExplorationError("fold record seed mismatch")
        method = record.get("method")
        config_hash = record.get("config_hash")
        if method not in METHOD_LABELS or not isinstance(config_hash, str):
            raise ModelExplorationError("unknown method or missing configuration identity")
        by_key.setdefault((method, config_hash), []).append(record)

    seen: set[tuple[str, str]] = set()
    for aggregate in aggregates:
        if not isinstance(aggregate, Mapping):
            raise ModelExplorationError("invalid candidate aggregate record")
        method, config_hash = aggregate.get("method"), aggregate.get("config_hash")
        key = (method, config_hash)
        if method not in METHOD_LABELS or not isinstance(config_hash, str) or key in seen:
            raise ModelExplorationError("duplicate or unknown candidate configuration")
        seen.add(key)
        records = by_key.get(key, [])
        if len(records) != EXPECTED_FOLDS or {record.get("fold") for record in records} != {0, 1, 2}:
            raise ModelExplorationError("candidate does not have exactly three distinct fold records")
        if aggregate.get("expected_fold_count") != EXPECTED_FOLDS or aggregate.get("observed_fold_count") != EXPECTED_FOLDS:
            raise ModelExplorationError("candidate summary does not report complete three-fold coverage")
        for record in records:
            if record.get("candidate") != aggregate.get("candidate"):
                raise ModelExplorationError("candidate parameters differ between fold and aggregate records")
        status = aggregate.get("status")
        if status == "COMPLETED":
            if aggregate.get("coverage_complete") is not True or aggregate.get("valid_fold_count") != EXPECTED_FOLDS:
                raise ModelExplorationError("completed candidate lacks three valid folds")
            if not all(record.get("status") == "COMPLETED" and record.get("primary_valid") is True for record in records):
                raise ModelExplorationError("candidate fold status disagrees with completed aggregate")
            for metric, summary_key in (("rmse", "selection_primary_cv_rmse"),
                                        ("mae", "selection_primary_cv_mae"),
                                        ("r2", "selection_primary_cv_r2")):
                values = [record.get(metric) for record in records]
                if any(not isinstance(value, (int, float)) for value in values):
                    raise ModelExplorationError(f"completed candidate has missing fold {metric}")
                if not isclose(mean(values), aggregate.get(summary_key), rel_tol=1e-12, abs_tol=1e-9):
                    raise ModelExplorationError(f"candidate aggregate {metric} does not match its three fold values")
                sd_key = f"{summary_key}_sd"
                if not isclose(stdev(values), aggregate.get(sd_key), rel_tol=1e-12, abs_tol=1e-9):
                    raise ModelExplorationError(f"candidate aggregate {metric} sample SD does not match its folds")
            selected_counts = [record.get("encoded_count") for record in records]
            if any(not isinstance(value, int) for value in selected_counts):
                raise ModelExplorationError("completed candidate is missing per-fold encoded feature counts")
            if not isclose(mean(selected_counts), aggregate.get("mean_selected_encoded_count"), rel_tol=1e-12, abs_tol=1e-9):
                raise ModelExplorationError("candidate mean encoded feature count does not match its fold records")
        elif status != "INVALID":
            raise ModelExplorationError(f"unsupported historical candidate status: {status}")
    if set(by_key) != seen:
        raise ModelExplorationError("fold results contain unaggregated or unrecognized configurations")
    if set(fold_digests) != {0, 1, 2} or any(len(digests) != 1 for digests in fold_digests.values()):
        raise ModelExplorationError("candidates do not share one consistent membership digest per fold")
    if len(aggregates) != 32 or len(fold_results) != 96:
        raise ModelExplorationError("historical source candidate/fold counts do not match the identified run")
    return {
        "run_id": run_id,
        "code_head": manifest.get("code_head_commit"),
        "phase3_contract_version": manifest.get("phase3_contract_version"),
        "data_sha256": expected_data,
        "fold_sha256": expected_folds,
        "source_summary_sha256": summary_entry["sha256"],
        "source_manifest_sha256": sha256_bytes(manifest_bytes),
        "development_rows": rows,
        "fold_count": EXPECTED_FOLDS,
        "configuration_count": len(aggregates),
        "fold_record_count": len(fold_results),
        "status_counts": dict(Counter(record.get("status") for record in aggregates)),
    }


def build_phase4_exploration(
    summary: Mapping[str, Any],
    manifest: Mapping[str, Any],
    summary_bytes: bytes,
    manifest_bytes: bytes,
    case_id: str,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Return schema-shaped Phase 4 JSON plus referenced public artifacts.

    Artifacts are limited to aggregate CV metrics and fold-local selected
    feature names/lineage. No OOF rows or fitted model binaries are included.
    """
    identity = validate_historical_summary(summary, manifest, summary_bytes, manifest_bytes)
    run_id = identity["run_id"]
    by_key: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for record in summary["per_outer_fold_results"]:
        by_key.setdefault((record["method"], record["config_hash"]), []).append(record)

    configs: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    chart_points: list[dict[str, Any]] = []
    feature_points: list[dict[str, Any]] = []
    for aggregate in summary["aggregate_results"]:
        method = aggregate["method"]
        config_hash = aggregate["config_hash"]
        candidate = aggregate["candidate"]
        config_id = f"hist-{_slug(method)}-{config_hash[:12]}"
        records = sorted(by_key[(method, config_hash)], key=lambda item: item["fold"])
        status = "VERIFIED" if aggregate["status"] == "COMPLETED" else "ERROR"
        root_ref = f"phases/phase-04/configurations/{config_id}"
        metadata_ref = f"{root_ref}/metadata.json"
        fold_ref = f"{root_ref}/fold-tasks.json"
        metrics_ref = f"{root_ref}/cv-metrics.json"
        features_ref = f"{root_ref}/selected-features.json"
        fold_metrics = []
        feature_folds = []
        for record in records:
            fold_metrics.append({
                "fold": record["fold"],
                "status": record["status"],
                "rmse": record.get("rmse"),
                "mae": record.get("mae"),
                "r2": record.get("r2"),
                "task_id": record.get("task_id"),
            })
            lineage = record.get("feature_lineage", []) if record.get("status") == "COMPLETED" else []
            feature_folds.append({
                "fold": record["fold"],
                "status": record["status"],
                "selection_unit": "encoded_feature",
                "encoded_count": record.get("encoded_count"),
                "raw_source_count": record.get("raw_count"),
                "selected_encoded_names": record.get("selected_encoded_names", []),
                "selected_raw_sources": record.get("selected_raw_sources", []),
                "feature_lineage": lineage,
            })
        mean_metrics = {
            "rmse": aggregate.get("selection_primary_cv_rmse"),
            "rmse_sample_sd": aggregate.get("selection_primary_cv_rmse_sd"),
            "mae": aggregate.get("selection_primary_cv_mae"),
            "mae_sample_sd": aggregate.get("selection_primary_cv_mae_sd"),
            "r2": aggregate.get("selection_primary_cv_r2"),
            "r2_sample_sd": aggregate.get("selection_primary_cv_r2_sd"),
        }
        configuration = {
            "configuration_id": config_id,
            "execution_run_id": run_id,
            "method_id": method,
            "track_id": "selected_features_to_primary_ols",
            "params": candidate,
            "protocol_id": "historical-p4b-v2-development-3fold-seed42",
            "metadata_ref": metadata_ref,
            "fold_tasks_ref": fold_ref,
            "cv_metrics_ref": metrics_ref,
            "selected_features_ref": features_ref,
            "status": status,
        }
        configs.append(configuration)
        artifacts[metadata_ref] = {
            "schema_version": "1.0.0", "case_id": case_id,
            "run_id": run_id, "configuration_id": config_id,
            "historical_config_hash": config_hash,
            "candidate": candidate, "candidate_status": aggregate["status"],
            "winner_in_source_run": aggregate.get("method_winner", False),
            "source_summary_sha256": identity["source_summary_sha256"],
            "source_code_head": identity["code_head"],
            "data_sha256": identity["data_sha256"], "fold_sha256": identity["fold_sha256"],
            "execution_status_note": "Historical aggregate evidence; run metadata records an earlier failed attempt and a later successful finalization.",
            "primary_track": "selected_features_to_primary_ols",
            "native_diagnostic_cv_rmse": aggregate.get("native_diagnostic_cv_rmse"),
            "mean_selected_encoded_count": aggregate.get("mean_selected_encoded_count"),
            "valid_fold_count": aggregate.get("valid_fold_count"),
            "invalid_reasons": aggregate.get("invalid_reasons", []),
        }
        artifacts[fold_ref] = {
            "schema_version": "1.0.0", "case_id": case_id,
            "run_id": run_id, "configuration_id": config_id,
            "fold_count": EXPECTED_FOLDS, "folds": fold_metrics,
            "fold_size_evidence": "not present in the public candidate aggregate; see common protocol and fold digest",
            "selection_metric": "mean of per-fold RMSE; selection score, not independent generalization",
        }
        artifacts[metrics_ref] = {
            "schema_version": "1.0.0", "case_id": case_id,
            "run_id": run_id, "configuration_id": config_id,
            "source_code_head": identity["code_head"],
            "data_sha256": identity["data_sha256"], "fold_sha256": identity["fold_sha256"],
            "candidate": candidate, "status": aggregate["status"],
            "primary_track": "selected_features_to_primary_ols",
            "fold_results": fold_metrics,
            "mean_fold_metrics": mean_metrics,
            "native_diagnostic_metrics": {
                "rmse": aggregate.get("native_diagnostic_cv_rmse"),
                "rmse_sample_sd": aggregate.get("native_diagnostic_cv_rmse_sd"),
                "mae": aggregate.get("native_diagnostic_cv_mae"),
                "mae_sample_sd": aggregate.get("native_diagnostic_cv_mae_sd"),
                "r2": aggregate.get("native_diagnostic_cv_r2"),
                "r2_sample_sd": aggregate.get("native_diagnostic_cv_r2_sd"),
            },
            "selection_scope": "Development three-fold CV; candidate selection score is not independent generalization",
        }
        artifacts[features_ref] = {
            "schema_version": "1.0.0", "case_id": case_id,
            "run_id": run_id, "configuration_id": config_id,
            "selection_unit": "encoded_feature",
            "summary": "Selections are fold-local. No final all-Development refit feature list is asserted for this candidate.",
            "folds": feature_folds,
        }
        if aggregate["status"] == "COMPLETED":
            point = {
                "configuration_id": config_id, "method_id": method,
                "candidate": candidate,
                "feature_count_mean": aggregate.get("mean_selected_encoded_count"),
                "rmse_mean_fold": mean_metrics["rmse"],
                "mae_mean_fold": mean_metrics["mae"],
                "r2_mean_fold": mean_metrics["r2"],
                "method_winner": bool(aggregate.get("method_winner", False)),
                "status": "VERIFIED",
            }
            chart_points.append(point)
            feature_points.append({k: point[k] for k in ("configuration_id", "method_id", "candidate", "feature_count_mean", "rmse_mean_fold", "method_winner", "status")})

    methods = [{
        "method_id": method_id,
        "label": METHOD_LABELS[method_id],
        "parameters": ([{"parameter_id": "k", "label": "Selected encoded feature count K", "data_type": "integer"}]
                       if method_id in {"pearson", "mutual_information", "ridge_rfe"}
                       else ([{"parameter_id": "alpha", "label": "Alpha", "data_type": "number"}]
                             if method_id == "lasso" else
                             ([{"parameter_id": "alpha", "label": "Alpha", "data_type": "number"}, {"parameter_id": "l1_ratio", "label": "L1 ratio", "data_type": "number"}]
                              if method_id == "elastic_net" else []))),
    } for method_id in METHOD_LABELS if any(item["method_id"] == method_id for item in configs)]

    phase4 = {
        "schema_version": "1.1.0", "case_id": case_id, "status": "VERIFIED",
        "cv": {"training_rows": 1168, "fold_count": EXPECTED_FOLDS,
               "protocol_id": "historical-p4b-v2-development-3fold-seed42", "status": "VERIFIED"},
        "methods": methods,
        "execution_runs": [{"execution_run_id": run_id,
                            "source_manifest_sha256": identity["source_manifest_sha256"],
                            "status": "VERIFIED"}],
        "configurations": configs,
        "default_configuration_id": None,
        "source_reported_candidate_configuration_id": next((
            item["configuration_id"] for item in configs
            if item["method_id"] == "lasso" and item["params"].get("alpha") == 100.0
        ), None),
        "charts": [
            {"chart_id": "method-comparison", "chart_type": "method-comparison",
             "points_ref": "phases/phase-04/charts/method-comparison.json",
             "axes": {"x": "method_id", "y": "rmse_mean_fold"},
             "comparison_protocol": {"protocol_id": "historical-p4b-v2-development-3fold-seed42", "fold_count": EXPECTED_FOLDS,
                                     "track_id": "selected_features_to_primary_ols", "metric_source": "historical aggregate summary",
                                     "metric": "rmse_mean_fold", "target_unit": "USD", "lower_is_better": True,
                                     "status": "SOURCE_REPORTED_VERIFIED_MATCH"},
             "status": "VERIFIED"},
            {"chart_id": "feature-count-vs-cv-rmse", "chart_type": "feature-count-vs-cv-rmse",
             "points_ref": "phases/phase-04/charts/feature-count-vs-cv-rmse.json",
             "axes": {"x": "feature_count_mean", "y": "rmse_mean_fold"},
             "comparison_protocol": {"protocol_id": "historical-p4b-v2-development-3fold-seed42", "fold_count": EXPECTED_FOLDS,
                                     "track_id": "selected_features_to_primary_ols", "metric_source": "historical aggregate summary",
                                     "metric": "rmse_mean_fold", "target_unit": "USD", "lower_is_better": True,
                                     "status": "SOURCE_REPORTED_VERIFIED_MATCH"},
             "status": "VERIFIED"},
        ],
    }
    artifacts["phases/phase-04/charts/method-comparison.json"] = {
        "case_id": case_id, "run_id": run_id, "status": "VERIFIED", "points": chart_points,
    }
    artifacts["phases/phase-04/charts/feature-count-vs-cv-rmse.json"] = {
        "case_id": case_id, "run_id": run_id, "status": "VERIFIED", "points": feature_points,
        "x_definition": "mean selected encoded feature count across the three folds",
        "y_definition": "mean of per-fold primary OLS RMSE; not pooled OOF RMSE",
    }
    return phase4, artifacts


def verify_historical_oof(
    oof_path: str | Path,
    summary: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Independently reconcile Development OOF rows to fold and run aggregates.

    The function holds row values only in memory, returns aggregate metrics and
    digests, and never returns or writes identifiers, actuals, or predictions.
    Callers should persist only this returned aggregate document.
    """
    path = Path(oof_path)
    if path.is_symlink() or not path.is_file():
        raise ModelExplorationError("historical Development OOF must be a regular file")
    inventory = manifest.get("file_inventory", [])
    entry = next((item for item in inventory if item.get("relative_path") == "p4b_oof_predictions.csv"), None)
    if not entry or entry.get("is_public") is not False:
        raise ModelExplorationError("historical OOF privacy inventory is missing or unexpected")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != entry.get("sha256") or path.stat().st_size != entry.get("byte_size"):
        raise ModelExplorationError("historical OOF file does not match its run manifest")

    metadata = summary.get("metadata", {})
    run_id = metadata.get("run_id")
    expected_by_task: dict[str, Mapping[str, Any]] = {
        record["task_id"]: record for record in summary.get("per_outer_fold_results", [])
        if isinstance(record, Mapping) and isinstance(record.get("task_id"), str)
    }
    completed_configs = {
        (record["method"], record["config_hash"]): record
        for record in summary.get("aggregate_results", [])
        if record.get("status") == "COMPLETED" and record.get("primary_valid") is True
    }
    rows_by_config: dict[tuple[str, str], dict[int, list[tuple[float, float, str]]]] = {
        key: {0: [], 1: [], 2: []} for key in completed_configs
    }
    seen_ids: dict[tuple[str, str], set[str]] = {key: set() for key in completed_configs}
    actual_by_id: dict[str, float] = {}
    row_total = 0
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != ["Id", "fold", "task_id", "method", "track", "actual", "predicted"]:
            raise ModelExplorationError("historical OOF CSV columns differ from the expected schema")
        for row in reader:
            row_total += 1
            task = expected_by_task.get(row["task_id"])
            if task is None:
                raise ModelExplorationError("OOF record refers to an unknown fold task")
            key = (task["method"], task["config_hash"])
            if key not in completed_configs:
                continue
            fold = int(row["fold"])
            if fold != task["fold"] or row["method"] != task["method"] or row["track"] != task["track"]:
                raise ModelExplorationError("OOF row identity disagrees with its fold task")
            identifier = row["Id"]
            if not identifier or identifier in seen_ids[key]:
                raise ModelExplorationError("duplicate or missing Development identifier within a configuration")
            seen_ids[key].add(identifier)
            actual = float(row["actual"])
            predicted = float(row["predicted"])
            if not (math.isfinite(actual) and math.isfinite(predicted)):
                raise ModelExplorationError("OOF contains a non-finite target or prediction")
            prior_actual = actual_by_id.setdefault(identifier, actual)
            if prior_actual != actual:
                raise ModelExplorationError("Development actual values differ between candidate OOF records")
            rows_by_config[key][fold].append((actual, predicted, identifier))

    def metrics(pairs: list[tuple[float, float, str]]) -> dict[str, float]:
        actual = [pair[0] for pair in pairs]
        predicted = [pair[1] for pair in pairs]
        n = len(actual)
        if not n:
            raise ModelExplorationError("OOF fold or configuration is empty")
        residuals = [a - p for a, p in zip(actual, predicted)]
        mse = sum(value * value for value in residuals) / n
        mae = sum(abs(value) for value in residuals) / n
        center = sum(actual) / n
        total = sum((value - center) ** 2 for value in actual)
        r2 = 1 - sum(value * value for value in residuals) / total if total else float("nan")
        return {"n": n, "rmse": math.sqrt(mse), "mae": mae, "r2": r2}

    fold_results: list[dict[str, Any]] = []
    pooled_results: list[dict[str, Any]] = []
    expected_sizes = {0: 390, 1: 389, 2: 389}
    for key, aggregate in sorted(completed_configs.items()):
        fold_rows = rows_by_config[key]
        if {fold: len(values) for fold, values in fold_rows.items()} != expected_sizes:
            raise ModelExplorationError("completed candidate OOF fold row counts do not match the fixed Development split")
        if len(seen_ids[key]) != 1168:
            raise ModelExplorationError("completed candidate OOF does not cover 1,168 unique Development rows")
        records = [
            record for record in summary["per_outer_fold_results"]
            if (record["method"], record["config_hash"]) == key
        ]
        for fold in (0, 1, 2):
            calculated = metrics(fold_rows[fold])
            reported = next(record for record in records if record["fold"] == fold)
            comparisons = (("rmse", calculated["rmse"], reported["rmse"]),
                           ("mae", calculated["mae"], reported["mae"]),
                           ("r2", calculated["r2"], reported["r2"]))
            if any(not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-6)
                   for _name, actual, expected in comparisons):
                raise ModelExplorationError(f"independent OOF {key[0]} fold {fold} metrics do not match the run summary")
            fold_results.append({"method": key[0], "config_hash": key[1], "fold": fold, **calculated})
        pooled = metrics([pair for fold in (0, 1, 2) for pair in fold_rows[fold]])
        pooled_results.append({
            "method": key[0], "config_hash": key[1], "candidate": aggregate.get("candidate"),
            "pooled_oof_metrics": pooled,
            "mean_fold_metrics": {
                "rmse": aggregate["selection_primary_cv_rmse"],
                "mae": aggregate["selection_primary_cv_mae"],
                "r2": aggregate["selection_primary_cv_r2"],
            },
            "mean_fold_sample_sd": {
                "rmse": aggregate["selection_primary_cv_rmse_sd"],
                "mae": aggregate["selection_primary_cv_mae_sd"],
                "r2": aggregate["selection_primary_cv_r2_sd"],
            },
        })
    return {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "source_oof_sha256": entry["sha256"],
        "source_oof_bytes": entry["byte_size"],
        "oof_publication": "PRIVATE_SOURCE_ROWS_NOT_INCLUDED",
        "development_data_sha256": manifest["dataset_provenance"]["canonical_development_dataset_sha256"],
        "fold_sha256": manifest["dataset_provenance"]["outer_fold_digest_expected"],
        "source_row_records": row_total,
        "verified_completed_configurations": len(pooled_results),
        "verified_fold_evaluations": len(fold_results),
        "fold_metrics": fold_results,
        "configurations": pooled_results,
        "methodology": "Independent metrics calculated from Development OOF only; no Holdout or Competition Test used.",
        "tolerance": {"relative": 1e-10, "absolute": 1e-6},
    }


def build_phase5_exploration(
    phase4: Mapping[str, Any],
    phase4_artifacts: Mapping[str, Mapping[str, Any]],
    oof_reconciliation: Mapping[str, Any],
    case_id: str,
    release_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build Development-CV and pooled-OOF evaluations from verified OOF metrics."""
    run_id = oof_reconciliation.get("run_id")
    if run_id not in {run["execution_run_id"] for run in phase4.get("execution_runs", [])}:
        raise ModelExplorationError("Phase 5 OOF run is not bound to a Phase 4 execution run")
    if oof_reconciliation.get("oof_publication") != "PRIVATE_SOURCE_ROWS_NOT_INCLUDED":
        raise ModelExplorationError("Phase 5 source privacy status is missing")
    config_by_hash = {}
    for item in phase4.get("configurations", []):
        if item.get("status") != "VERIFIED":
            continue
        metadata = phase4_artifacts.get(item.get("metadata_ref"), {})
        historical_hash = metadata.get("historical_config_hash")
        if not isinstance(historical_hash, str) or historical_hash in config_by_hash:
            raise ModelExplorationError("Phase 4 configuration hash binding is missing or duplicated")
        config_by_hash[historical_hash] = item
    if len(config_by_hash) != 30:
        raise ModelExplorationError("Phase 5 requires all 30 valid Phase 4 configurations")
    evaluations: list[dict[str, Any]] = []
    fold_values: list[dict[str, Any]] = []
    pooled_summaries: list[dict[str, Any]] = []
    for config_result in oof_reconciliation.get("configurations", []):
        config = config_by_hash.get(config_result.get("config_hash"))
        if not config:
            raise ModelExplorationError("Phase 5 OOF configuration does not resolve to Phase 4")
        config_id = config["configuration_id"]
        cv_eval_id = f"{run_id}.{config_id}.cv-mean"
        pooled_eval_id = f"{run_id}.{config_id}.pooled-oof"
        mean_metrics = config_result.get("mean_fold_metrics", {})
        pooled_metrics = config_result.get("pooled_oof_metrics", {})
        sample_sd = {
            "mae": config_result.get("mean_fold_sample_sd", {}).get("mae"),
            "rmse": config_result.get("mean_fold_sample_sd", {}).get("rmse"),
            "r2": config_result.get("mean_fold_sample_sd", {}).get("r2"),
        }
        fold_values.append({
            "configuration_id": config_id,
            "method_id": config["method_id"],
            "folds": [item for item in oof_reconciliation["fold_metrics"]
                      if item["config_hash"] == config_result["config_hash"]],
        })
        pooled_summaries.append({
            "configuration_id": config_id,
            "method_id": config["method_id"],
            "candidate": config["params"],
            "pooled_oof_metrics": pooled_metrics,
        })
        linked = [cv_eval_id, pooled_eval_id]
        for evaluation_id, source, metrics, aggregation in (
            (cv_eval_id, "cv_fold_mean", mean_metrics, "fold_mean"),
            (pooled_eval_id, "pooled_oof", pooled_metrics, "pooled_oof"),
        ):
            evaluations.append({
                "evaluation_id": evaluation_id,
                "execution_run_id": run_id,
                "configuration_id": config_id,
                "final_fit_id": None,
                "model_id": None,
                "model_version": None,
                "evaluation_population": "development_oof",
                "prediction_origin": "phase4_historical_oof",
                "metric_source": source,
                "n": 1168,
                "target": {"column": "SalePrice", "unit": "USD"},
                "metrics": {
                    metric: {"value": metrics[metric], "status": "VERIFIED",
                             "reason_code": None,
                             "evidence_ref": "phases/phase-05/pooled-oof-metrics.json" if source == "pooled_oof" else "phases/phase-05/fold-metrics.json"}
                    for metric in ("mae", "rmse", "r2")
                },
                "fold_summary": {
                    "fold_count": EXPECTED_FOLDS,
                    "aggregation": aggregation,
                    "ddof": 1,
                    "sample_sd": sample_sd,
                    "fold_values_ref": "phases/phase-05/fold-metrics.json",
                },
                "figures": [],
                "interval": {
                    "int_f": {"status": "UNAVAILABLE", "reason_code": "NOT_COMPUTED", "method": None, "assumptions_ref": None},
                    "int_s": {"status": "UNAVAILABLE", "reason_code": "NOT_COMPUTED", "interval_type": None,
                              "method": None, "nominal_level": None, "population": None,
                              "asset_ref": None, "coverage_evidence": None, "review_url": None},
                },
                "evidence": {
                    "source_artifact_sha256": oof_reconciliation["source_oof_sha256"],
                    "source_ref": None,
                    "protocol_version": "v2.0",
                    "review_url": None,
                },
                "asset_status": "UNAVAILABLE",
                "review_status": "AWAITING_REVIEW",
                "limitations": [
                    "Development OOF is internal resampling, not independent generalization testing.",
                    "Historical run-state metadata records an earlier failed attempt followed by successful finalization.",
                    "Prediction rows remain private; diagnostic figures have not been generated for this release.",
                    "Research publication review is pending.",
                ],
                "linked_evaluation_ids": linked,
            })
    document = {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "release_id": release_id,
        "generated_at": None,
        "status": "PLANNED",
        "reason_code": "PUBLICATION_REVIEW_PENDING",
        "publication_review": "PENDING",
        "default_evaluation_id": None,
        "evaluations": evaluations,
        "ui": {
            "default_population": "development_oof",
            "population_options": [{"id": "development_oof", "label": "Development OOF"}],
            "figure_tabs": [
                {"figure_id": "FIG-P5-01", "label": "Actual vs Predicted", "kind": "actual_vs_predicted"},
                {"figure_id": "FIG-P5-02", "label": "Residual vs Predicted", "kind": "residual_vs_predicted"},
                {"figure_id": "FIG-P5-03", "label": "Residual Distribution", "kind": "residual_distribution"},
            ],
            "metric_order": ["mae", "rmse", "r2"],
            "interval_figure_id": "FIG-P5-04",
        },
    }
    assets = {
        "phases/phase-05/fold-metrics.json": {
            "schema_version": "1.0.0", "case_id": case_id,
            "run_id": run_id, "source_oof_sha256": oof_reconciliation["source_oof_sha256"],
            "development_data_sha256": oof_reconciliation["development_data_sha256"],
            "fold_sha256": oof_reconciliation["fold_sha256"],
            "aggregation": "per-fold RMSE/MAE/R2 recomputed independently from private Development OOF; sample SD uses ddof=1",
            "configurations": fold_values,
        },
        "phases/phase-05/pooled-oof-metrics.json": {
            "schema_version": "1.0.0", "case_id": case_id,
            "run_id": run_id, "source_oof_sha256": oof_reconciliation["source_oof_sha256"],
            "development_data_sha256": oof_reconciliation["development_data_sha256"],
            "fold_sha256": oof_reconciliation["fold_sha256"],
            "aggregation": "pooled metrics recomputed over each 1,168-row Development OOF configuration",
            "configurations": pooled_summaries,
        },
    }
    return document, assets
