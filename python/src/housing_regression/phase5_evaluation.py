"""Development-only Phase 5 evaluation from source-bound Phase 4 OOF records."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from housing_regression.contracts import validate_document


class EvaluationError(ValueError):
    """Phase 5 OOF source, metric, figure, or contract validation failed."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metric(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    residual = actual - predicted
    total = float(np.sum((actual - np.mean(actual)) ** 2))
    if not len(actual) or total == 0 or not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise EvaluationError("OOF metrics require finite values and non-constant actuals")
    return {
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual ** 2))),
        "r2": float(1.0 - np.sum(residual ** 2) / total),
    }


def _exclusive_json(path: Path, value: Any) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()


def build_development_oof_evaluation(
    *, oof_path: str | Path, metadata_path: str | Path, output_root: str | Path,
    run_id: str, configuration_id: str, config_sha256: str, source_sha256: str,
    development_data_sha256: str, fold_sha256: str, phase4_summary: dict[str, Any],
    schema_path: str | Path,
) -> dict[str, Any]:
    """Verify an exact Development OOF file, rescore it, and create local draft diagnostics."""
    oof = Path(oof_path)
    meta = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    digest = _sha(oof)
    expected_meta = {
        "run_id": run_id, "configuration_id": configuration_id,
        "evaluation_population": "development_oof", "row_count": 1168,
        "config_sha256": config_sha256, "source_sha256": source_sha256,
        "development_data_sha256": development_data_sha256,
        "fold_assignment_sha256": fold_sha256, "oof_sha256": digest,
        "validation_partition_used": False,
    }
    if any(meta.get(key) != value for key, value in expected_meta.items()):
        raise EvaluationError("OOF metadata identity, source fingerprint, count, or SHA mismatch")
    with oof.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        expected_fields = ["run_id", "configuration_id", "fold", "row_id", "actual", "predicted"]
        if reader.fieldnames != expected_fields:
            raise EvaluationError("OOF CSV columns do not match the Phase 4 OOF contract")
        records = list(reader)
    if len(records) != 1168 or len({row["row_id"] for row in records}) != 1168:
        raise EvaluationError("OOF must contain 1,168 unique Development row predictions")
    if any(row["run_id"] != run_id or row["configuration_id"] != configuration_id for row in records):
        raise EvaluationError("OOF contains rows bound to a different run or configuration")
    try:
        folds = np.asarray([int(row["fold"]) for row in records], dtype=np.int64)
        actual = np.asarray([float(row["actual"]) for row in records], dtype=np.float64)
        predicted = np.asarray([float(row["predicted"]) for row in records], dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise EvaluationError("OOF numeric fields are malformed") from exc
    if set(folds.tolist()) != {0, 1, 2} or not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise EvaluationError("OOF fold labels or values are invalid")
    fold_counts = {str(fold): int(np.sum(folds == fold)) for fold in range(3)}
    if fold_counts != {"0": 390, "1": 389, "2": 389} or fold_counts != meta.get("fold_counts"):
        raise EvaluationError("OOF fold coverage differs from the fixed three-fold protocol")
    residuals = actual - predicted
    fold_metrics = []
    for fold in range(3):
        mask = folds == fold
        fold_metrics.append({"fold": fold, "n": int(mask.sum()), **_metric(actual[mask], predicted[mask])})
    for fresh, core in zip(fold_metrics, phase4_summary["fold_results"], strict=True):
        for key in ("mae", "rmse", "r2"):
            if not math.isclose(fresh[key], float(core[key]), rel_tol=0.0, abs_tol=1e-7):
                raise EvaluationError(f"independent Phase 5 {key} differs from Phase 4 fold output")
    mean_metrics = {key: float(np.mean([fold[key] for fold in fold_metrics])) for key in ("mae", "rmse", "r2")}
    pooled_metrics = _metric(actual, predicted)
    sample_sd = {key: float(np.std([fold[key] for fold in fold_metrics], ddof=1)) for key in ("mae", "rmse", "r2")}
    root = Path(output_root)
    assets = root / "phases/phase-05/assets"
    assets.mkdir(parents=True, exist_ok=False)
    fold_ref = "phases/phase-05/fold-metrics.json"
    _exclusive_json(root / fold_ref, {"run_id": run_id, "configuration_id": configuration_id, "fold_metrics": fold_metrics, "mean_fold_metrics": mean_metrics, "sample_sd_ddof1": sample_sd})

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plots = [
        ("FIG-P5-01", "actual-vs-predicted.png", "Actual vs Predicted", actual, predicted, "Actual SalePrice", "OOF prediction SalePrice", "y_equals_x"),
        ("FIG-P5-02", "residual-vs-predicted.png", "Residual vs Predicted", predicted, residuals, "OOF prediction SalePrice", "Actual − predicted SalePrice", "y_equals_0"),
    ]
    figure_rows: list[dict[str, Any]] = []
    eval_id = f"{run_id}.development-oof.pooled"
    for figure_id, name, title, x, y, xlabel, ylabel, ref_line in plots:
        fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
        ax.scatter(x, y, s=10, alpha=0.45, color="#187b77", edgecolors="none")
        if ref_line == "y_equals_x":
            low, high = float(min(np.min(x), np.min(y))), float(max(np.max(x), np.max(y)))
            ax.plot([low, high], [low, high], color="#ad5e22", linewidth=1)
        else:
            ax.axhline(0, color="#ad5e22", linewidth=1)
        ax.set(title=f"{title} · DEVELOPMENT OOF · LOCAL DRAFT", xlabel=xlabel, ylabel=ylabel)
        path = assets / name
        fig.savefig(path, dpi=130, metadata={"Title": title, "Description": "Development OOF aggregate diagnostic; pending review."})
        plt.close(fig)
        x_field, y_field = ("actual", "predicted") if figure_id == "FIG-P5-01" else ("predicted", "actual_minus_predicted")
        figure_rows.append({
            "figure_id": figure_id, "evaluation_id": eval_id, "configuration_id": configuration_id,
            "evaluation_population": "development_oof", "prediction_origin": "phase4_fixed_cv_oof",
            "n": len(records), "status": "PLANNED", "publication_review": "PENDING",
            "asset_ref": f"phases/phase-05/assets/{name}", "sha256": _sha(path),
            "accessible_table_ref": fold_ref,
            "axes": {"x": {"field": x_field, "label": xlabel, "unit": "USD"},
                     "y": {"field": y_field, "label": ylabel, "unit": "USD"}, "reference_line": ref_line},
            "residual_sign": None if figure_id == "FIG-P5-01" else "actual_minus_predicted",
            "alt": f"{title} scatter plot for {len(records)} Development out-of-fold predictions; local draft, pending review.",
            "finding": "Computed from this run's fixed three-fold Development OOF records; not an independent holdout result.",
            "limitations": ["Development OOF only", "Local engineering output pending independent review", "Not publication-approved"],
            "source_digest": digest, "histogram": None,
        })
    hist_ref = "phases/phase-05/assets/residual-histogram.json"
    counts, edges = np.histogram(residuals, bins=30)
    hist_payload = {"bin_edges": [float(v) for v in edges], "counts": [int(v) for v in counts], "n": int(len(residuals)), "residual_sign": "actual_minus_predicted"}
    _exclusive_json(root / hist_ref, hist_payload)
    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
    ax.hist(residuals, bins=edges, color="#187b77", alpha=0.8)
    ax.axvline(0, color="#ad5e22", linewidth=1)
    ax.set(title="Residual Distribution · DEVELOPMENT OOF · LOCAL DRAFT", xlabel="Actual − predicted SalePrice", ylabel="Count")
    hist_path = assets / "residual-distribution.png"
    fig.savefig(hist_path, dpi=130, metadata={"Title": "Residual distribution", "Description": "Development OOF histogram; pending review."})
    plt.close(fig)
    figure_rows.append({
        "figure_id": "FIG-P5-03", "evaluation_id": eval_id, "configuration_id": configuration_id,
        "evaluation_population": "development_oof", "prediction_origin": "phase4_fixed_cv_oof",
        "n": len(records), "status": "PLANNED", "publication_review": "PENDING",
        "asset_ref": "phases/phase-05/assets/residual-distribution.png", "sha256": _sha(hist_path),
        "accessible_table_ref": hist_ref,
        "axes": {"x": {"field": "actual_minus_predicted", "label": "Actual − predicted SalePrice", "unit": "USD"},
                 "y": {"field": "count", "label": "Count", "unit": "count"}, "reference_line": "x_equals_0"},
        "residual_sign": "actual_minus_predicted", "alt": "Thirty-bin histogram of Development OOF residuals, actual minus predicted; local draft, pending review.",
        "finding": "Histogram counts derive from this run's Development OOF residuals.",
        "limitations": ["Development OOF only", "Local engineering output pending independent review", "Not publication-approved"],
        "source_digest": digest, "histogram": {"bin_count": 30, "bin_edges_ref": hist_ref, "n": len(records)},
    })

    def metric_record(values: dict[str, float]) -> dict[str, Any]:
        return {name: {"value": values[name], "status": "VERIFIED", "reason_code": None,
                       "evidence_ref": fold_ref} for name in ("mae", "rmse", "r2")}
    def record(suffix: str, metric_source: str, values: dict[str, float], fs: dict[str, Any], figures: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "evaluation_id": f"{run_id}.development-oof.{suffix}", "execution_run_id": run_id,
            "configuration_id": configuration_id, "final_fit_id": None,
            "model_id": "ames-reference-local-ols", "model_version": run_id,
            "evaluation_population": "development_oof", "prediction_origin": "phase4_fixed_cv_oof",
            "metric_source": metric_source, "n": len(records), "target": {"column": "SalePrice", "unit": "USD"},
            "metrics": metric_record(values), "fold_summary": fs, "figures": figures,
            "interval": {"int_f": {"status": "UNAVAILABLE", "reason_code": "NOT_COMPUTED", "method": None, "assumptions_ref": None},
                         "int_s": {"status": "UNAVAILABLE", "reason_code": "NOT_COMPUTED", "interval_type": None, "method": None, "nominal_level": None, "population": None, "asset_ref": None, "coverage_evidence": None, "review_url": None}},
            "evidence": {"source_artifact_sha256": digest, "source_ref": "private/phase4-oof-predictions.csv", "protocol_version": "v2.0", "review_url": None},
            "asset_status": "PENDING_REVIEW" if figures else "UNAVAILABLE",
            "review_status": "AWAITING_REVIEW", "limitations": ["Development OOF is internal resampling, not independent generalization testing.", "Publication review is pending."],
            "linked_evaluation_ids": [],
        }
    cv_record = record("cv-mean", "cv_fold_mean", mean_metrics,
                       {"fold_count": 3, "aggregation": "fold_mean", "ddof": 1, "sample_sd": sample_sd, "fold_values_ref": fold_ref}, [])
    pooled_record = record("pooled", "pooled_oof", pooled_metrics,
                           {"fold_count": 3, "aggregation": "pooled_oof", "ddof": 1, "sample_sd": sample_sd, "fold_values_ref": fold_ref}, figure_rows)
    cv_record["linked_evaluation_ids"] = [pooled_record["evaluation_id"]]
    pooled_record["linked_evaluation_ids"] = [cv_record["evaluation_id"]]
    index = {
        "schema_version": "1.0.0", "case_id": "ames-reference-init-a", "release_id": None,
        "generated_at": None, "status": "PLANNED", "reason_code": "PUBLICATION_REVIEW_PENDING",
        "publication_review": "PENDING", "default_evaluation_id": pooled_record["evaluation_id"],
        "evaluations": [cv_record, pooled_record],
        "ui": {"default_population": "development_oof", "population_options": [
            {"id": "development_oof", "label": "Development OOF"}, {"id": "holdout", "label": "Validation aggregate"}, {"id": "training_in_sample", "label": "Training in-sample"}],
            "figure_tabs": [{"figure_id": "FIG-P5-01", "label": "Actual vs predicted", "kind": "actual_vs_predicted"},
                            {"figure_id": "FIG-P5-02", "label": "Residual vs predicted", "kind": "residual_vs_predicted"},
                            {"figure_id": "FIG-P5-03", "label": "Residual distribution", "kind": "residual_distribution"}],
            "metric_order": ["mae", "rmse", "r2"], "interval_figure_id": "FIG-P5-04"},
    }
    validate_document(index, schema_path)
    return {"index": index, "oof_sha256": digest, "row_count": len(records),
            "fold_counts": fold_counts, "fold_metrics": fold_metrics,
            "mean_fold_metrics": mean_metrics, "pooled_oof_metrics": pooled_metrics,
            "independent_phase4_comparison": "PASS", "figures": figure_rows}
