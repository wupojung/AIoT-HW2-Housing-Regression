"""Assemble a schema-checked, aggregate-only CAR Case Package from a frozen run."""

from __future__ import annotations

import copy
import hashlib
import json
import mimetypes
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from housing_regression.e2e_package import PackageValidationError, validate_case_package


CASE_ID = "used-car-price-optimized"
EXPECTED_RUN_ID = "used-car-e2e-20261028-03"
PHASE_REFS = {
    1: "phases/phase-01/content.json",
    2: "phases/phase-02/analyses.json",
    3: "phases/phase-03/preparation.json",
    4: "phases/phase-04/modeling.json",
    5: "phases/phase-05/evaluations.json",
    6: "phases/phase-06/inference-catalog.json",
}
SCHEMA_REFS = {
    1: "docs/design/data-contracts/schemas/phase-01.schema.json",
    2: "docs/design/data-contracts/schemas/phase-02.schema.json",
    3: "docs/design/data-contracts/schemas/phase-03.schema.json",
    4: "docs/design/data-contracts/schemas/phase-04.schema.json",
    5: "docs/design/data-contracts/schemas/phase-05.schema.json",
    6: "docs/design/data-contracts/schemas/phase-06.schema.json",
}


class UsedCarPackageError(ValueError):
    """A CAR run cannot be packaged without changing or misrepresenting evidence."""


def _json_read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise UsedCarPackageError(f"expected JSON object: {path.name}")
    return value


def _json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _manifest_files(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise UsedCarPackageError("symlinks are not allowed in a Case Package")
        if not path.is_file() or path.name == "package.json":
            continue
        rel = path.relative_to(root).as_posix()
        payload = path.read_bytes()
        rows.append({"path": rel, "sha256": _sha(payload), "bytes": len(payload),
                     "mime": mimetypes.guess_type(rel)[0] or "application/octet-stream"})
    return rows


def _aggregate_plot_assets(run: Path, destination: Path) -> tuple[list[dict[str, Any]], str]:
    """Render three binned OOF diagnostics; no individual OOF records are copied."""
    private_oof = run / "private/winner-oof-private.csv"
    payload = private_oof.read_bytes()
    source_digest = _sha(payload)
    oof = pd.read_csv(private_oof)
    if list(oof.columns) != ["dev_index", "actual", "oof_predicted", "fold"] or len(oof) < 30:
        raise UsedCarPackageError("Run 03 private OOF evidence has an unexpected shape")
    actual = oof["actual"].to_numpy(dtype=float)
    predicted = oof["oof_predicted"].to_numpy(dtype=float)
    residual = actual - predicted
    if not (np.isfinite(actual).all() and np.isfinite(predicted).all() and np.isfinite(residual).all()):
        raise UsedCarPackageError("OOF evidence contains non-finite values")
    figures_dir = destination / "figures"
    diagnostics_dir = destination / "diagnostics"
    figures_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    specs = []

    # Quantile-binned means make the scatter diagnostics aggregate-only.
    order = np.argsort(predicted, kind="mergesort")
    groups = [part for part in np.array_split(order, min(20, len(order))) if len(part)]
    bins = [{"n": int(len(part)), "mean_predicted": float(predicted[part].mean()),
             "mean_actual": float(actual[part].mean()),
             "mean_residual": float(residual[part].mean())} for part in groups]
    table_ref = "phases/phase-05/diagnostics/oof-quantile-bins.json"
    specs.append({"figure_id": "FIG-P5-01", "label": "Actual vs Predicted", "kind": "actual_vs_predicted",
                  "filename": "actual-vs-predicted.png", "table_ref": table_ref})
    specs.append({"figure_id": "FIG-P5-02", "label": "Residual vs Predicted", "kind": "residual_vs_predicted",
                  "filename": "residual-vs-predicted.png", "table_ref": table_ref})
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.scatter([row["mean_actual"] for row in bins], [row["mean_predicted"] for row in bins],
               s=[max(12, row["n"] * 2) for row in bins], alpha=.75, color="#3977a8")
    low = min(float(actual.min()), float(predicted.min()))
    high = max(float(actual.max()), float(predicted.max()))
    ax.plot([low, high], [low, high], "--", color="#b6573a", linewidth=1)
    ax.set(title="Development OOF · Quantile-binned means", xlabel="Mean actual price (USD)", ylabel="Mean predicted price (USD)")
    fig.savefig(figures_dir / specs[0]["filename"], dpi=140)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.axhline(0, color="#b6573a", linestyle="--", linewidth=1)
    ax.scatter([row["mean_predicted"] for row in bins], [row["mean_residual"] for row in bins],
               s=[max(12, row["n"] * 2) for row in bins], alpha=.75, color="#3977a8")
    ax.set(title="Development OOF · Quantile-binned means", xlabel="Mean predicted price (USD)", ylabel="Mean residual (actual − predicted, USD)")
    fig.savefig(figures_dir / specs[1]["filename"], dpi=140)
    plt.close(fig)
    _json_write(diagnostics_dir / Path(table_ref).name, {
        "schema_version": "1.0.0", "case_id": CASE_ID, "run_id": EXPECTED_RUN_ID,
        "configuration_id": _json_read(run / "checkpoint.json")["winner_configuration_id"],
        "population": "development_oof", "source_digest": source_digest,
        "aggregation": "20 approximately equal-sized quantile bins over predictions",
        "points": bins,
    })

    hist_ref = "phases/phase-05/diagnostics/residual-histogram.json"
    hist, edges = np.histogram(residual, bins=20)
    histogram = {"bin_count": int(len(hist)), "bin_edges": [float(x) for x in edges],
                 "counts": [int(x) for x in hist], "n": int(len(residual))}
    _json_write(diagnostics_dir / Path(hist_ref).name, {
        "schema_version": "1.0.0", "case_id": CASE_ID, "run_id": EXPECTED_RUN_ID,
        "configuration_id": _json_read(run / "checkpoint.json")["winner_configuration_id"],
        "population": "development_oof", "source_digest": source_digest,
        **histogram,
    })
    specs.append({"figure_id": "FIG-P5-03", "label": "Residual Distribution", "kind": "residual_distribution",
                  "filename": "residual-distribution.png", "table_ref": hist_ref, "histogram": histogram})
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.hist(residual, bins=edges, color="#3977a8", edgecolor="white")
    ax.set_xscale("symlog", linthresh=1000)
    ax.set(title="Development OOF · Residual distribution", xlabel="Residual (actual − predicted, USD)", ylabel="Aggregate count")
    fig.savefig(figures_dir / specs[2]["filename"], dpi=140)
    plt.close(fig)
    for spec in specs:
        spec["asset_ref"] = f"phases/phase-05/figures/{spec['filename']}"
        spec["sha256"] = _sha((figures_dir / spec["filename"]).read_bytes())
    return specs, source_digest


def _adapt_phase4(doc: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(doc)
    result.pop("limitations", None)
    for chart in result.get("charts", []):
        chart.setdefault("chart_type", chart["chart_id"])
    return result


RAW_FIELD_TYPE_BY_SOURCE_TYPE = {
    "nominal": "nominal",
    "ordinal": "ordinal",
    "discrete": "discrete",
    "continuous": "continuous",
    "identifier": "identifier",
    "text": "text",
    "temporal": "temporal",
    "leakage_proxy": "other",
}
# Source-documented field meaning takes precedence over model-filter labels.
RAW_FIELD_TYPE_BY_FIELD = {
    "make": "nominal",
    "model": "nominal",
    "trans": "nominal",
    "mileage": "continuous",
    "est._monthly_pmt": "continuous",
    "search_price": "continuous",
}
RAW_FIELD_TYPE_LABELS = {
    "nominal": "名目類別 (Nominal)",
    "ordinal": "有序類別 (Ordinal)",
    "discrete": "離散數值 (Discrete)",
    "continuous": "連續數值 (Continuous)",
    "identifier": "識別碼 (Identifier)",
    "text": "自由文字 (Text)",
    "temporal": "時間欄位 (Temporal)",
    "other": "其他／洩漏代理 (Other / Leakage Proxy)",
}


def classify_raw_source_fields(
    decisions: list[tuple[str, str, str]],
    lineage_decisions: list[dict[str, Any]] | None = None,
    automatically_screened_fields: set[str] | None = None,
) -> dict[str, Any]:
    """Build a verified, mutually exclusive classification from recorded source-field decisions."""
    counts = {type_id: 0 for type_id in RAW_FIELD_TYPE_LABELS}
    fields = []
    seen: set[str] = set()
    evidence_by_field = {item.get("field"): item for item in (lineage_decisions or [])}
    automatically_screened_fields = automatically_screened_fields or set()
    for raw_name, source_type, decision in decisions:
        field = raw_name.strip()
        if field == "price":
            continue
        if not field or field in seen:
            raise UsedCarPackageError("Phase 2 field decisions contain an empty or duplicate source field")
        seen.add(field)
        type_id = RAW_FIELD_TYPE_BY_SOURCE_TYPE.get(source_type)
        type_id = RAW_FIELD_TYPE_BY_FIELD.get(field, type_id)
        if type_id is None:
            raise UsedCarPackageError(f"no reviewed raw-field classification for source type: {source_type}")
        if decision not in {"include", "exclude"}:
            raise UsedCarPackageError("Phase 2 field decision is not include/exclude")
        counts[type_id] += 1
        exclusion_category = None
        reason_status = "VERIFIED"
        if decision == "exclude":
            if field in automatically_screened_fields:
                exclusion_category = "High-cardinality / long-label screen"
            else:
                exclusion_category = {
                    "identifier": "Identifier",
                    "text": "Free Text",
                    "leakage_proxy": "Leakage Risk",
                    "temporal": "Temporal Metadata",
                    "duplicate_representation": "Redundant Feature",
                }.get(source_type, "Reason pending verification")
            if source_type == "duplicate_representation":
                exclusion_category = "Redundant Feature — basis pending verification"
                reason_status = "PENDING"
        fields.append({
            "field": field,
            "type_id": type_id,
            "source_semantic_type": source_type,
            "classification_basis": "Kaggle data dictionary / verified source field semantics" if field in RAW_FIELD_TYPE_BY_FIELD else "Run 03 Phase 2 field classification",
            "decision": decision,
            "reason": evidence_by_field.get(field, {}).get("reason", "eligible predictor" if decision == "include" else "Reason pending verification"),
            "exclusion_category": exclusion_category,
            "reason_status": reason_status,
        })
    total = len(fields)
    if not total or sum(counts.values()) != total:
        raise UsedCarPackageError("raw source-field classification does not reconcile to its field inventory")
    return {
        "status": "VERIFIED",
        "total": total,
        "counts": counts,
        "feature_types": [{"type_id": type_id, "label": label} for type_id, label in RAW_FIELD_TYPE_LABELS.items()],
        "fields": fields,
        "evidence": {
            "basis": "Kaggle data dictionary, source CSV schema, Run 03 Phase 2 field decisions and Phase 3 feature lineage",
            "mileage": "Numeric measurement. Excluded from modeling as a duplicate representation; exact equivalence to odometer remains pending.",
        },
    }


def _adapt_phase5(doc: dict[str, Any], figure_specs: list[dict[str, Any]], source_digest: str) -> dict[str, Any]:
    result = copy.deepcopy(doc)
    # Metrics were computed and independently reconciled, while publication
    # approval remains pending; keep those statuses separate.
    result["status"] = "PLANNED"
    result["release_id"] = None
    result["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result["publication_review"] = "PENDING"
    result["ui"] = {
        "default_population": "development_oof",
        "population_options": [
            {"id": "development_oof", "label": "Development OOF"},
            {"id": "holdout", "label": "Internal labeled Holdout"},
        ],
        "figure_tabs": [{"figure_id": f["figure_id"], "label": f["label"], "kind": f["kind"]} for f in figure_specs],
        "metric_order": ["mae", "rmse", "r2"],
        "interval_figure_id": "FIG-P5-04",
    }
    for evaluation in result["evaluations"]:
        evaluation["asset_status"] = "PENDING_REVIEW"
        evaluation["review_status"] = "AWAITING_REVIEW"
        evaluation["evidence"]["source_ref"] = None
        fold_summary = evaluation.get("fold_summary")
        if isinstance(fold_summary, dict) and fold_summary.get("aggregation") == "pooled_predictions":
            evaluation["fold_summary"] = {
                "fold_count": evaluation["fold_summary"]["fold_count"],
                "aggregation": "pooled_oof",
                "ddof": 1,
                "sample_sd": doc["evaluations"][0]["fold_summary"]["sample_sd"],
                "fold_values_ref": evaluation["fold_summary"]["fold_values_ref"],
            }
        if evaluation["evaluation_id"].endswith(".pooled-oof"):
            figures = []
            for item in figure_specs:
                figures.append({
                    "figure_id": item["figure_id"], "evaluation_id": evaluation["evaluation_id"],
                    "configuration_id": evaluation["configuration_id"], "evaluation_population": "development_oof",
                    "prediction_origin": "new_core_fold_local_oof", "n": evaluation["n"],
                    "status": "PLANNED", "publication_review": "PENDING",
                    "asset_ref": item["asset_ref"], "sha256": item["sha256"],
                    "accessible_table_ref": item["table_ref"],
                    "axes": {
                        "x": {"field": {"FIG-P5-01": "actual", "FIG-P5-02": "predicted",
                                        "FIG-P5-03": "actual_minus_predicted"}[item["figure_id"]],
                              "label": item["label"], "unit": "USD"},
                        "y": {"field": {"FIG-P5-01": "predicted", "FIG-P5-02": "actual_minus_predicted",
                                        "FIG-P5-03": "count"}[item["figure_id"]],
                              "label": item["label"], "unit": "count" if item["figure_id"] == "FIG-P5-03" else "USD"},
                        "reference_line": {"FIG-P5-01": "y_equals_x", "FIG-P5-02": "y_equals_0",
                                           "FIG-P5-03": "x_equals_0"}[item["figure_id"]],
                    },
                    "residual_sign": "actual_minus_predicted" if item["figure_id"] in {"FIG-P5-02", "FIG-P5-03"} else None,
                    "alt": f"{item['label']}，以 Development OOF 彙總分箱繪製，不公開逐筆值。",
                    "finding": None,
                    "limitations": ["Publication review pending; chart is aggregate-only and uses Development OOF."],
                    "source_digest": source_digest,
                    "histogram": ({"bin_count": item["histogram"]["bin_count"],
                                   "bin_edges_ref": item["table_ref"],
                                   "n": item["histogram"]["n"]} if item["figure_id"] == "FIG-P5-03" else None),
                })
            evaluation["figures"] = figures
    return result


def build_used_car_case_package(run_root: str | Path, package_root: str | Path) -> dict[str, Any]:
    """Build a new, non-overwriting local Case Package from immutable Run 03 outputs."""
    run = Path(run_root).resolve(strict=True)
    destination = Path(package_root).resolve()
    if destination.exists() or destination.is_symlink():
        raise UsedCarPackageError("refusing to overwrite an existing CAR Case Package")
    checkpoint = _json_read(run / "checkpoint.json")
    config = _json_read(run / "config.json")
    if checkpoint.get("case_id") != CASE_ID or checkpoint.get("run_id") != EXPECTED_RUN_ID:
        raise UsedCarPackageError("source run identity does not match the accepted Run 03")
    if checkpoint.get("source_sha256") != config.get("source_sha256"):
        raise UsedCarPackageError("Run 03 source/config fingerprint mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".used-car-package-", dir=destination.parent))
    try:
        source_phase2 = _json_read(run / PHASE_REFS[2])
        source_phase4 = _json_read(run / PHASE_REFS[4])
        source_phase5 = _json_read(run / PHASE_REFS[5])
        source_phase6 = _json_read(run / PHASE_REFS[6])
        phase2_doc = copy.deepcopy(source_phase2)
        phase3_doc = copy.deepcopy(_json_read(run / PHASE_REFS[3]))
        phase3_lineage_doc = _json_read(run / "phases/phase-03/feature-lineage.json")
        config_doc = _json_read(run / "config.json")
        phase1_doc = _json_read(run / PHASE_REFS[1])
        for section in phase1_doc.get("sections", []):
            section["body"] = section.get("body", "").replace(
                "原始 CSV 僅留在本機 ignored local/。",
                "原始 CSV 不納入本 Case Package；套件僅包含聚合研究結果與來源指紋。")
        field_analysis = next(item for item in phase2_doc["analyses"] if item["id"] == "field-decisions")
        decisions = re.findall(r"([^;]+?)\s+\[([^\]]+)\]\s+(include|exclude)", field_analysis["finding"])
        raw_predictors = [item for item in decisions if item[0].strip() != "price"]
        eligible_predictors = [item for item in raw_predictors if item[2] == "include"]
        exclusion_review = _json_read(run / "field-exclusion-review.json")
        automatic_text_fields = set(exclusion_review.get("automatically_detected_long_text_fields", {}))
        raw_classification = classify_raw_source_fields(
            decisions,
            phase3_lineage_doc.get("excluded_fields", []),
            automatic_text_fields,
        )
        if raw_classification["total"] != len(raw_predictors):
            raise UsedCarPackageError("raw field classification does not match Phase 2 candidate count")
        raw_classification["evidence"]["source_data_sha256"] = checkpoint["source_sha256"]
        raw_classification["evidence"]["schema_source"] = "train_data_v2.csv header reconciled with Phase 2 decisions; semantic types checked against Kaggle data dictionary; target price excluded"
        raw_classification["evidence"]["exclusion_review_source"] = "field-exclusion-review.json"
        raw_classification["evidence"]["dictionary_url"] = "https://www.kaggle.com/competitions/used-car-price-prediction-challenge/data"
        raw_stage = next(item for item in phase3_doc["stages"] if item["id"] == "raw")
        raw_stage["total"] = len(raw_predictors)
        raw_stage["segments"] = []
        raw_stage["distribution_status"] = "UNAVAILABLE"
        raw_stage["label"] = "目標以外的原始欄位（含排除候選）"
        lineage_raw = phase3_lineage_doc["stages"]["raw"]
        lineage_raw["total"] = len(raw_predictors)
        lineage_raw["counts"] = raw_classification["counts"]
        lineage_raw["eligible_predictor_columns"] = len(eligible_predictors)
        lineage_raw["classification_status"] = raw_classification["status"]
        phase3_lineage_doc["raw_classification"] = {
            key: value for key, value in raw_classification.items() if key != "fields"
        }
        phase3_lineage_doc["raw_fields"] = raw_classification["fields"]
        treatments = phase3_doc.get("treatments", [])
        treatment_fields = {item.get("field") for item in treatments}
        automatic_text = config_doc.get("automatic_text_exclusion", {})
        for treatment in treatments:
            field = treatment.get("field")
            if field in automatic_text:
                treatment["reason"] = automatic_text[field]
                treatment["source_csv_modified"] = False
        for field, semantic_type, decision in decisions:
            field = field.strip()
            if field == "price" or decision != "exclude" or semantic_type != "text" or field in treatment_fields:
                continue
            reason = automatic_text.get(field, "automatic free-text screening")
            treatments.append({"field": field, "action": "exclude_from_model_input",
                               "reason": reason, "source_csv_modified": False})
        phase3_doc["treatments"] = treatments
        phase_docs = {
            1: phase1_doc,
            2: phase2_doc,
            3: phase3_doc,
            4: _adapt_phase4(source_phase4),
            5: None,
            6: copy.deepcopy(source_phase6),
        }
        phase_docs[6].pop("local_private_verification", None)
        for phase, ref in PHASE_REFS.items():
            target = staging / ref
            if phase not in {2, 5}:
                _json_write(target, phase_docs[phase])

        # Phase 2 figures are referenced at the package's canonical locations.
        figure_rows = []
        for analysis in phase_docs[2].get("analyses", []):
            ref = analysis.get("image_ref")
            if not ref:
                continue
            filename = Path(ref).name
            canonical = f"phases/phase-02/figures/{filename}"
            source = run / "figures" / filename
            if not source.is_file():
                raise UsedCarPackageError(f"missing Run 03 Phase 2 figure: {filename}")
            target = staging / canonical
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            digest = _sha(target.read_bytes())
            analysis["image_ref"] = canonical
            figure_rows.append({"figure_id": analysis["figure_id"], "case_id": CASE_ID, "phase": 2,
                                "source_configuration_id": None, "source_evaluation_id": None,
                                "svg_ref": canonical, "png_ref": None, "width": 760,
                                "height": 130, "alt": analysis["description"],
                                "accessible_table_ref": None,
                                "source_evidence_ref": "assets/execution-manifest.json",
                                "sha256_svg": digest, "sha256_png": None,
                                "publication_review": "PENDING", "status": "PLANNED"})
        # Rewrite Phase 2 now that all refs are package-root relative.
        _json_write(staging / PHASE_REFS[2], phase_docs[2])
        asset_dir = staging / "assets"
        asset_dir.mkdir(parents=True)
        _json_write(asset_dir / "execution-manifest.json", {
            "schema_version": "1.0.0", "case_id": CASE_ID, "run_id": EXPECTED_RUN_ID,
            "source_file": "train_data_v2.csv", "source_sha256": checkpoint["source_sha256"],
            "config_sha256": checkpoint["config_sha256"],
            "code_sha256": config["code_sha256"],
            "python_dependencies": {"pandas": config["pandas_version"], "numpy": config["numpy_version"],
                                    "scikit_learn": config["sklearn_version"]},
            "test_data_accessed": False, "row_level_predictions_included": False,
            "phase_status": checkpoint["phase_status"],
        })
        _json_write(asset_dir / "figure-manifest.json", {
            "schema_version": "1.0.0", "case_id": CASE_ID, "run_id": EXPECTED_RUN_ID,
            "status": "PENDING_REVIEW", "figures": figure_rows,
        })
        _json_write(asset_dir / "publication-status.json", {
            "case_id": CASE_ID, "status": "PENDING",
            "reason": "The dataset page lists CC BY-NC-SA 4.0; competition rules require authenticated access and were not independently verified. This package is a local review artifact, not approved for public release.",
            "attribution": "Used Car Price Prediction Challenge dataset by ZeinaDallal, via Kaggle.",
            "license": "CC BY-NC-SA 4.0",
        })

        # Copy model-comparison JSON and per-configuration aggregate artifacts.
        phase4_assets: list[Path] = []
        phase4_doc = phase_docs[4]
        for rel in [chart["points_ref"] for chart in phase4_doc["charts"]]:
            phase4_assets.append(run / rel)
        for cfg in phase4_doc["configurations"]:
            for key in ("metadata_ref", "fold_tasks_ref", "cv_metrics_ref", "selected_features_ref"):
                rel = cfg.get(key)
                if rel:
                    phase4_assets.append(run / rel)
        for source in phase4_assets:
            rel = source.relative_to(run)
            target = staging / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        _json_write(staging / "phases/phase-03/feature-lineage.json", phase3_lineage_doc)
        _json_write(staging / "config.json", config_doc)
        diagnostics = run.parent / "diagnostics-01/baseline-and-data-quality.json"
        if not diagnostics.is_file():
            raise UsedCarPackageError("independent baseline and data-quality reconciliation is required")
        baseline_ref = "phases/phase-05/baseline-comparison.json"
        (staging / baseline_ref).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(diagnostics, staging / baseline_ref)

        chart_dir = staging / "phases/phase-05"
        chart_dir.mkdir(parents=True, exist_ok=True)
        figure_specs, oof_digest = _aggregate_plot_assets(run, chart_dir)
        phase_docs[5] = _adapt_phase5(source_phase5, figure_specs, oof_digest)
        _json_write(staging / PHASE_REFS[5], phase_docs[5])
        # Keep only aggregate Holdout metrics, never the row-level file.
        shutil.copyfile(run / "phases/phase-05/holdout-aggregate.json",
                        staging / "phases/phase-05/holdout-aggregate.json")
        _json_write(staging / "case.json", {
            "schema_version": "1.0.0", "case_id": CASE_ID,
            "title": "中古車售價預測與模型效能分析｜Used Car Price Prediction — Optimized Modeling",
            "case_status": "PARTIAL", "methodology_id": "CRISP-DM",
            "source": {"label": "Kaggle Used Car Price Prediction Challenge — train_data_v2.csv",
                       "url": "https://www.kaggle.com/competitions/used-car-price-prediction-challenge/data?select=train_data_v2.csv",
                       "license": "CC BY-NC-SA 4.0", "license_review": "PENDING"},
            "target": {"raw_field_id": "price", "label": "中古車刊登價格", "unit": "USD", "value_type": "number"},
            "language": "zh-Hant",
            "disclaimer": "Run 03 是有限候選比較；最佳候選仍未優於 Dummy Baseline。價格為網路刊登價，不是成交價；線上推論服務未提供。",
        })
        phases = {}
        for phase, ref in PHASE_REFS.items():
            document = _json_read(staging / ref)
            phases[f"phase{phase}"] = {"status": document["status"], "data_ref": ref}
        package = {
            "package_schema_version": "1.0.0",
            "package_id": f"{CASE_ID}-run03-r1",
            "case_id": CASE_ID,
            "package_revision": "run03-r1",
            "package_status": "PARTIAL",
            "publication": {"approved": False, "release_id": None, "review_status": "PENDING"},
            "case_ref": "case.json",
            "phases": phases,
            "asset_manifest_ref": "assets/figure-manifest.json",
            "files": _manifest_files(staging),
        }
        _json_write(staging / "package.json", package)
        validation = validate_case_package(staging)
        if destination.exists():
            raise UsedCarPackageError("destination appeared during package assembly")
        staging.rename(destination)
        return {"status": "PASS", "package_root": str(destination), "package_id": package["package_id"],
                "case_id": CASE_ID, "run_id": EXPECTED_RUN_ID, "files": len(package["files"]),
                "package_sha256": _sha((destination / "package.json").read_bytes()), "validation": validation}
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
