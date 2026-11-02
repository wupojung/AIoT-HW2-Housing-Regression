"""Build an aggregate-only Steam homework candidate in the existing package format."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from housing_regression.e2e_package import validate_case_package
from housing_regression.steam_review_multiplier import CASE_ID, MODEL_INPUT_FIELDS, RAW_CANDIDATE_FIELDS, write_json


REVISION = "steam-homework-20261102-01"
PHASE_REFS = {i: f"phases/phase-0{i}/" + name for i, name in enumerate([
    "content.json", "analyses.json", "preparation.json", "modeling.json", "evaluations.json", "inference-catalog.json"
], start=1)}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(root: Path) -> list[dict[str, Any]]:
    items = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Steam case candidate may not contain symlinks")
        if path.is_file() and path.name != "package.json":
            rel = path.relative_to(root).as_posix()
            mime = mimetypes.guess_type(rel)[0] or "application/octet-stream"
            items.append({"path": rel, "sha256": _sha(path), "bytes": path.stat().st_size, "mime": mime})
    return items


def _schema_check(repo_root: Path, root: Path) -> None:
    for phase, ref in PHASE_REFS.items():
        schema = json.loads((repo_root / f"docs/contracts/schemas/phase-0{phase}.schema.json").read_text(encoding="utf-8"))
        document = json.loads((root / ref).read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(document)


def _metric(value: float, evidence_ref: str) -> dict[str, Any]:
    return {"value": float(value), "status": "VERIFIED", "reason_code": None, "evidence_ref": evidence_ref}


def build_candidate(repo_root: Path, run_dir: Path) -> dict[str, Any]:
    destination = repo_root / "web/data/candidates/steam-review-multiplier"
    destination.mkdir(parents=True, exist_ok=True)
    for phase in range(1, 7):
        (destination / f"phases/phase-0{phase}").mkdir(parents=True, exist_ok=True)
    for phase in (2, 4, 5):
        (destination / f"phases/phase-0{phase}/figures").mkdir(parents=True, exist_ok=True)
    (destination / "phases/phase-04/charts").mkdir(parents=True, exist_ok=True)
    (destination / "assets").mkdir(parents=True, exist_ok=True)

    phase2 = json.loads((run_dir / "phase-02/data-understanding.json").read_text(encoding="utf-8"))
    model = json.loads((run_dir / "phase-04/modeling-results.json").read_text(encoding="utf-8"))
    evaluation = json.loads((run_dir / "phase-05/holdout-evaluation.json").read_text(encoding="utf-8"))
    source_code_provenance = {
        "run_01_original_source_code_sha256": {"research_module": "UNKNOWN", "runner": "UNKNOWN"},
        "current_verifiable_source_code": {
            "repository_commit": "19f587cfa7f2ab6ab6d6afff023832709554a861",
            "files": {
                "python/src/housing_regression/steam_review_multiplier.py": _sha(repo_root / "python/src/housing_regression/steam_review_multiplier.py"),
                "tools/steam/run_homework.py": _sha(repo_root / "tools/steam/run_homework.py"),
            },
            "interpretation": "These hashes identify currently verifiable repository files; they do not prove which exact bytes generated Run 01.",
        },
    }
    # Do not present persisted hashes as Run 01 provenance when its source snapshot is unavailable.
    evaluation.pop("source_code_sha256", None)
    evaluation["source_code_provenance"] = source_code_provenance
    train_rows, holdout_rows = evaluation["train_rows"], evaluation["holdout_rows"]
    eligible_rows = evaluation["eligible_rows"]
    execution_id = evaluation["run_id"]

    case = {
        "schema_version": "1.0.0", "case_id": CASE_ID,
        "title": "基於 Steam 遊戲特徵之 Review Multiplier 迴歸預測研究｜Predicting Steam Review Multipliers Using Game Features and Regression Models",
        "case_status": "PARTIAL", "methodology_id": "CRISP-DM",
        "source": {"label": "Steam Games Dataset 2025 · Kaggle", "url": "https://www.kaggle.com/datasets/artermiloff/steam-games-dataset",
                   "license": "MIT (as labelled by Kaggle)", "license_review": "PENDING",
                   "citation": "Ermilov et al. (2025), Kaggle dataset 10.34740/KAGGLE/DSV/11017460"},
        "target": {"raw_field_id": "estimated_owners / num_reviews_total", "label": "Review Multiplier K", "unit": "multiplier", "value_type": "number"},
        "language": "zh-Hant",
        "disclaimer": "本研究為課程實驗，預測結果皆為基於現有資料與模型的估計值，僅供研究方法探索與比較。",
        "sections": [
            {"section_id": "background", "title": "研究背景與問題", "body": "Steam 評論數量常被作為遊戲受眾規模的代理線索。本研究將固定 K=30 作為 Owner 經驗基準，並以 K=20、50 做敏感度比較；這些數字都不是正確標籤。SteamSpy estimated_owners 是區間估計，資料不包含可驗證的官方銷售量。"},
            {"section_id": "questions", "title": "Research Questions", "body": "RQ1：不同 Genre 的 K 代理值分布是否不同？RQ2：Genre、平台、語言、價格及遊戲屬性能否預測 K？RQ3：特徵選擇與迴歸模型如何影響結果？RQ4：ML K 相對固定 K=30，對 SteamSpy 擁有量區間的相容程度如何？"},
            {"section_id": "hypotheses", "title": "研究假設與成功條件", "body": "假設 Genre 間存在描述性差異；遊戲屬性模型可能改善 holdout K proxy 誤差；特徵選擇方法會改變表現。假設以 holdout 實驗檢驗。成功標準是提出清楚、可追溯的比較並如實解讀，不要求模型一定勝過基準。"},
            {"section_id": "target", "title": "研究標的與術語", "body": "Review Count 採 num_reviews_total（缺值才回退 positive+negative）；K 區間為 owners_low/review_count 至 owners_high/review_count；單值標籤使用區間中點 proxy。Estimated Ownership = Review Count × Predicted K。Estimated Ownership 不是官方銷售量。"},
            {"section_id": "source", "title": "資料來源與限制", "body": "來源為 Kaggle Steam Games Dataset 2025，作者 Artemiy Ermilov 與三位協作者，標示 MIT。Kaggle 描述其資料蒐集使用 Steam 商店頁面、Steam API 與 SteamSpy。May 2024／March 2025 Full 與 Cleaned 快照由本機檔案核對；兩個 Cleaned 的精確排除規則未知。"},
        ],
    }
    write_json(destination / "case.json", case)
    phase1 = {"schema_version": "1.0.0", "case_id": CASE_ID, "status": "VERIFIED",
              "sections": [{"section_id": s["section_id"], "title": s["title"], "body": s["body"]} for s in case["sections"]]}
    write_json(destination / PHASE_REFS[1], phase1)

    analyses = []
    figure_specs = [
        ("overview", "FIG-STEAM-01", "Dataset overview", "dataset-overview.svg", "四份本機快照資料列數與欄數；由逐檔串流盤點產生。"),
        ("missingness", "FIG-STEAM-02", "Missingness overview", "missingness-overview.svg", "2025 Cleaned 缺值比例最高的欄位。"),
        ("reviews", "FIG-STEAM-03", "Review count distribution", "review-count-distribution.svg", "num_reviews_total 在正值與有效 owners 區間資料中的長尾分布。"),
        ("owners", "FIG-STEAM-04", "Estimated owners distribution", "owners-distribution.svg", "SteamSpy owners 區間中點 proxy 的長尾分布，不是真實銷量。"),
        ("genres", "FIG-STEAM-05", "Genre distribution", "genre-distribution.svg", "一款遊戲可同時屬於多個 Genre，各組樣本有重疊。"),
        ("genre-k", "FIG-STEAM-06", "K proxy by genre", "k-by-genre.svg", "高頻 Genre K proxy 箱型圖；為可讀性只裁切圖面上尾，統計摘要未裁切。"),
        ("price-k", "FIG-STEAM-07", "K proxy by price", "k-vs-price.svg", "付費遊戲價格分位組的 K proxy 中位數。"),
        ("fixed-k", "FIG-STEAM-08", "K baseline interval compatibility", "fixed-k-interval-compatibility.svg", "固定 K=20／30／50 落在 K 區間內的比例。"),
    ]
    for aid, fid, title, image, description in figure_specs:
        analyses.append({"id": aid, "figure_id": fid, "title": title, "status": "VERIFIED",
                         "image_ref": f"phases/phase-02/figures/{image}",
                         "table_ref": "phases/phase-02/data-understanding.json",
                         "description": description, "finding": None,
                         "limitations": "圖表由指定 Kaggle CSV 彙總產生；owners 與 K 為區間／代理值，非官方銷量。",
                         "provenance_ref": "assets/execution-manifest.json"})
    phase2_doc = {"schema_version": "1.0.0", "case_id": CASE_ID, "status": "VERIFIED",
                  "default_analysis_id": "overview", "analyses": analyses}
    write_json(destination / PHASE_REFS[2], phase2_doc)
    write_json(destination / "phases/phase-02/data-understanding.json", phase2)
    for _, _, _, image, _ in figure_specs:
        figure_path = destination / "phases/phase-02/figures" / image
        shutil.copyfile(run_dir / "phase-02/figures" / image, figure_path)
        if figure_path.suffix == ".svg":
            # Matplotlib leaves trailing spaces on path commands; normalize generated text assets.
            lines = figure_path.read_text(encoding="utf-8").splitlines()
            figure_path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")

    lineage = {"case_id": CASE_ID, "source_file": phase2["source_file"], "raw_candidate_fields": RAW_CANDIDATE_FIELDS,
               "raw_candidate_field_count": len(RAW_CANDIDATE_FIELDS),
               "model_inputs": [{"field": name, "meaning": label, "source_fields": sources, "transformation": transform}
                   for name, label, sources, transform in [
                       ("genres", "Genre membership", ["genres"], "Top 12 genre indicators learned from training fold; multi-label"),
                       ("price", "Store price", ["price"], "Numeric USD; median imputation fitted on train"),
                       ("required_age", "Age rating", ["required_age"], "Numeric"),
                       ("dlc_count", "DLC count", ["dlc_count"], "Numeric"),
                       ("achievements", "Achievement count", ["achievements"], "Numeric"),
                       ("release_year", "Release year", ["release_date"], "Four-digit year parse; malformed dates missing"),
                       ("windows", "Windows support", ["windows"], "Boolean to 0/1"),
                       ("mac", "macOS support", ["mac"], "Boolean to 0/1"),
                       ("linux", "Linux support", ["linux"], "Boolean to 0/1"),
                       ("genre_count", "Number of genres", ["genres"], "List length"),
                       ("category_count", "Number of categories", ["categories"], "Parsed list length"),
                       ("tag_count", "Number of tags", ["tags"], "Parsed mapping/list length; no tag identities used"),
                       ("supported_language_count", "Supported language count", ["supported_languages"], "Parsed list length"),
                       ("full_audio_language_count", "Full audio language count", ["full_audio_languages"], "Parsed list length"),
                       ("has_english", "English support", ["supported_languages"], "Case-insensitive list membership"),
                       ("has_traditional_chinese", "Traditional Chinese support", ["supported_languages"], "Case-insensitive list membership"),
                       ("discount", "Snapshot discount", ["discount"], "Numeric; 2024 snapshot lacks field and is not in main model"),
                       ("developer_count", "Number of listed developers", ["developers"], "Parsed list length; names and identities excluded"),
                       ("publisher_count", "Number of listed publishers", ["publishers"], "Parsed list length; names and identities excluded"),
                       ("screenshot_count", "Number of store screenshots", ["screenshots"], "Parsed media list length; URLs excluded"),
                       ("movie_count", "Number of store videos", ["movies"], "Parsed media list length; URLs excluded"),
                       ("has_website", "Website listed on store metadata", ["website"], "Binary presence indicator"),
                   ]],
               "excluded_fields": [{"field": x, "reason": y} for x,y in [
                   ("appid", "Identifier; no predictive meaning"), ("name", "Identifier/free text"),
                   ("positive / negative / num_reviews_total", "Outcome-adjacent and would leak the ratio denominator"),
                   ("estimated_owners", "Target construction only"), ("recommendations / peak_ccu / playtime", "Popularity outcomes and leakage proxies"),
                   ("developer / publisher identities, descriptions, media / website URLs", "High-cardinality identity, free-text, or raw URL content excluded; low-cardinality counts/presence may be used"),
                   ("pct_pos_total / pct_pos_recent", "Review outcome proxies, excluded from game-attribute model"),
               ]],
               "missing_value_treatment": "Blank list fields remain missing; explicit empty lists map to count 0. Median imputation is inside every CV/development-fit pipeline; missing dates remain missing until imputation.",
               "split": evaluation["split"], "train_rows": train_rows, "holdout_rows": holdout_rows,
               "eligible_rows": eligible_rows, "excluded_rows": evaluation["source_rows"]-eligible_rows,
               "target": evaluation["target"], "thresholds": {"minimum_reviews": evaluation["review_minimum"], "positive_owner_upper_bound": True}}
    feature_count = len(model["selected_features"])
    model_input_by_name = {item["field"]: item for item in lineage["model_inputs"]}
    lineage["encoded_features"] = []
    for index, encoded_name in enumerate(model["selected_features"]):
        if encoded_name.startswith("genre::"):
            sources = ["genres"]
            transformation = "Train-fold-fitted binary membership for the observed top-12 genre vocabulary"
            semantic_type = "nominal"
        else:
            input_item = model_input_by_name[encoded_name]
            sources = input_item["source_fields"]
            transformation = input_item["transformation"]
            semantic_type = "continuous" if encoded_name in {"price", "release_year", "discount"} else "discrete"
        lineage["encoded_features"].append({"index": index, "encoded_feature": encoded_name,
                                             "source_columns": sources, "semantic_type": semantic_type,
                                             "transformation": transformation})
    lineage["encoded_feature_count"] = len(lineage["encoded_features"])
    write_json(destination / "phases/phase-03/feature-lineage.json", lineage)
    encoded_counts = {kind: sum(item["semantic_type"] == kind for item in lineage["encoded_features"])
                      for kind in ("nominal", "discrete", "continuous")}
    preparation = {"schema_version": "1.0.0", "case_id": CASE_ID, "status": "VERIFIED",
                   "feature_types": [{"type_id": "nominal", "label": "Multi-label game genre"},
                                     {"type_id": "discrete", "label": "Counts and binary platform/language indicators"},
                                     {"type_id": "continuous", "label": "Price, release year and discount"}],
                   "stages": [
                       {"id": "raw", "label": "Source dataset", "unit": "raw_columns", "total": len(phase2["source_fields"]), "total_status": "VERIFIED", "segments": [], "distribution_status": "VERIFIED"},
                       {"id": "filtered", "label": "Selected raw candidate fields", "unit": "pre_encoding_columns", "total": len(RAW_CANDIDATE_FIELDS), "total_status": "VERIFIED", "segments": [], "distribution_status": "VERIFIED"},
                       {"id": "processed", "label": "Engineered model inputs", "unit": "pre_encoding_columns", "total": len(MODEL_INPUT_FIELDS), "total_status": "VERIFIED", "segments": [{"type_id": "nominal", "count": 1}, {"type_id": "discrete", "count": 18}, {"type_id": "continuous", "count": 3}], "distribution_status": "VERIFIED", "fit_population": "development partition / training fold"},
                       {"id": "encoded", "label": "Selected model features", "unit": "encoded_features", "total": feature_count, "total_status": "VERIFIED", "segments": [{"type_id": kind, "count": count} for kind, count in encoded_counts.items()], "distribution_status": "VERIFIED", "fit_population": "development partition / training fold"},
                   ],
                   "treatments": [{"id": "target-proxy", "description": "K interval midpoint proxy; log1p response; zero upper-bound owners excluded"},
                                  {"id": "review-minimum", "description": "At least 20 num_reviews_total reviews"},
                                  {"id": "imputation-scaling", "description": "Median imputation and StandardScaler inside CV pipeline"},
                                  {"id": "leakage-control", "description": "Identifier, review counts, owners and popularity fields excluded from model input"}],
                   "split": {"source_labeled_rows": eligible_rows, "training_rows": train_rows, "holdout_rows": holdout_rows, "seed": 42, "status": "VERIFIED"},
                   "lineage_ref": "phases/phase-03/feature-lineage.json"}
    write_json(destination / PHASE_REFS[3], preparation)

    protocol_id = f"steam-3fold-log-k-seed{evaluation['split']['seed']}"
    methods = [
        {"method_id": "ols", "label": "OLS Linear Regression", "parameters": []},
        {"method_id": "ridge", "label": "Ridge Regression", "parameters": [{"parameter_id": "alpha", "label": "Alpha", "data_type": "number"}]},
        {"method_id": "lasso", "label": "Lasso Regression", "parameters": [{"parameter_id": "alpha", "label": "Alpha", "data_type": "number"}]},
        {"method_id": "random_forest", "label": "Random Forest Regressor", "parameters": [{"parameter_id": "n_estimators", "label": "Trees", "data_type": "integer"}]},
        {"method_id": "select_k_best", "label": "SelectKBest-14 + Ridge", "parameters": [{"parameter_id": "k", "label": "Encoded features", "data_type": "integer"}]},
        {"method_id": "ridge_rfe", "label": "RFE-14 + Ridge", "parameters": [{"parameter_id": "k", "label": "Encoded features", "data_type": "integer"}]},
    ]
    configurations = []
    for row in model["cv"]:
        cid = row["configuration_id"]
        method_id = {"select_k_14": "select_k_best", "lasso_rfe_14": "ridge_rfe"}.get(row["feature_selection"], row["model_id"])
        params = {"feature_selection": row["feature_selection"], "model": row["model_id"], "seed": 42,
                  "estimator_parameters": row["estimator_parameters"], "selector_parameters": row["selector_parameters"]}
        configurations.append({"configuration_id": cid, "execution_run_id": execution_id, "method_id": method_id,
                               "track_id": "training_only_cv", "params": params, "protocol_id": protocol_id,
                               "cv_metrics_ref": f"phases/phase-04/configurations/{cid}/cv-metrics.json", "status": "VERIFIED"})
        config_dir = destination / f"phases/phase-04/configurations/{cid}"
        write_json(config_dir / "cv-metrics.json", row)
        write_json(config_dir / "metadata.json", {"configuration_id": cid, "model_id": row["model_id"], "feature_selection": row["feature_selection"], "software": evaluation["software"]})
        write_json(config_dir / "fold-tasks.json", {"configuration_id": cid, "fold_count": 3, "seed": 42, "fold_log_rmse": row["fold_log_rmse"]})
        write_json(config_dir / "selected-features.json", {"note": "The selected winner's exact fit features are listed in modeling.json; per-fold one-hot vocabularies are fit inside each training fold.", "winner_features": model["selected_features"] if cid == model["selected_configuration"] else []})
        configurations[-1].update({"metadata_ref": f"phases/phase-04/configurations/{cid}/metadata.json", "fold_tasks_ref": f"phases/phase-04/configurations/{cid}/fold-tasks.json", "selected_features_ref": f"phases/phase-04/configurations/{cid}/selected-features.json"})
    chart_points = [{"configuration_id": x["configuration_id"], "model_id": x["model_id"], "feature_selection": x["feature_selection"], "mean_log_rmse": x["mean_log_rmse"], "sd_log_rmse": x["sd_log_rmse"]} for x in model["cv"]]
    write_json(destination / "phases/phase-04/charts/model-comparison.json", chart_points)
    shutil.copyfile(run_dir / "phase-04/figures/cv-model-comparison.png", destination / "phases/phase-04/figures/cv-model-comparison.png")
    modeling = {"schema_version": "1.1.0", "case_id": CASE_ID, "status": "VERIFIED",
                "cv": {"training_rows": train_rows, "fold_count": 3, "protocol_id": protocol_id, "status": "VERIFIED"},
                "methods": methods, "execution_runs": [{"execution_run_id": execution_id, "source_manifest_sha256": evaluation["data_sha256"], "status": "VERIFIED"}],
                "configurations": configurations, "default_configuration_id": model["selected_configuration"],
                "charts": [{"chart_id": "model-comparison", "chart_type": "bar", "points_ref": "phases/phase-04/charts/model-comparison.json", "axes": {"x": "configuration_id", "y": "mean_log_rmse"}, "comparison_protocol": {"protocol_id": protocol_id, "fold_count": 3, "track_id": "training_only_cv", "metric_source": "fold_mean", "metric": "RMSE", "target_unit": "log1p(K proxy)", "lower_is_better": True, "status": "VERIFIED"}, "status": "VERIFIED"}],
                }
    write_json(destination / "phases/phase-04/modeling-details.json", {
        "selected_configuration": model["selected_configuration"], "selected_features": model["selected_features"],
        "feature_importance": evaluation["feature_importance"][:20], "cv_configurations": model["cv"],
        "source_code_provenance": source_code_provenance})
    write_json(destination / PHASE_REFS[4], modeling)

    model_row = next(x for x in evaluation["holdout_metrics"] if x["model"] == "machine-learning")
    evaluation_id = f"{execution_id}.holdout.ml"
    config_id = model["selected_configuration"]
    summary_ref = "phases/phase-05/evaluation-summary.json"
    write_json(destination / summary_ref, evaluation)
    # Binned aggregate values only; no AppID, input row or point-level predictions enter the candidate.
    shutil.copyfile(run_dir / "phase-05/figures/actual-predicted-bins.json", destination / "phases/phase-05/actual-predicted-bins.json")
    for image in ["holdout-baseline-comparison.png", "holdout-interval-compatibility.png", "genre-predicted-k.png", "actual-vs-predicted.png", "residual-distribution.png"]:
        shutil.copyfile(run_dir / "phase-05/figures" / image, destination / "phases/phase-05/figures" / image)
    fig_specs = [
        ("FIG-P5-01", "actual-vs-predicted.png", "Aggregated actual versus predicted K proxy, binned by predicted K."),
        ("FIG-P5-02", "holdout-interval-compatibility.png", "Holdout ownership interval compatibility for fixed and learned multipliers."),
        ("FIG-P5-03", "residual-distribution.png", "Holdout K-proxy residual distribution; display is clipped for readability."),
    ]
    figures = []
    for fid, image, alt in fig_specs:
        asset = destination / "phases/phase-05/figures" / image
        figures.append({"figure_id": fid, "evaluation_id": evaluation_id, "configuration_id": config_id,
                        "evaluation_population": "holdout", "prediction_origin": "Refit selected pipeline on development partition",
                        "n": holdout_rows, "status": "VERIFIED", "publication_review": "PENDING",
                        "asset_ref": f"phases/phase-05/figures/{image}", "sha256": _sha(asset),
                        "accessible_table_ref": "phases/phase-05/actual-predicted-bins.json" if fid == "FIG-P5-01" else summary_ref,
                        "axes": {"x": {"field": "predicted_k" if fid == "FIG-P5-01" else "comparison", "label": "Predicted K" if fid == "FIG-P5-01" else "Comparison", "unit": "multiplier"},
                                 "y": {"field": "observed_k_proxy" if fid == "FIG-P5-01" else "holdout_metric", "label": "Observed K midpoint proxy" if fid == "FIG-P5-01" else "Holdout", "unit": "K proxy / interval rate"},
                                 "reference_line": "y_equals_x" if fid == "FIG-P5-01" else "y_equals_0"},
                        "residual_sign": "actual_minus_predicted" if fid == "FIG-P5-03" else None,
                        "alt": alt, "finding": None, "limitations": ["Target is SteamSpy interval midpoint proxy, not actual sales."],
                        "source_digest": evaluation["data_sha256"], "histogram": None})
    def metric_obj(key: str):
        return _metric(model_row[key], summary_ref)
    phase5 = {"schema_version": "1.0.0", "case_id": CASE_ID, "release_id": None,
              "generated_at": datetime.now(timezone.utc).isoformat(), "status": "PLANNED", "reason_code": "LOCAL_CANDIDATE_PUBLICATION_REVIEW_PENDING",
              "publication_review": "PENDING", "default_evaluation_id": evaluation_id,
              "evaluations": [{"evaluation_id": evaluation_id, "execution_run_id": execution_id,
                  "configuration_id": config_id, "final_fit_id": f"{execution_id}.development-refit",
                  "model_id": "steam-review-multiplier-random-forest", "model_version": "1.0.0",
                  "evaluation_population": "holdout", "prediction_origin": "Development refit; holdout scored once",
                  "metric_source": "holdout_aggregate", "n": holdout_rows,
                  "target": {"column": "K midpoint proxy", "unit": "multiplier"},
                  "metrics": {"mae": metric_obj("mae"), "rmse": metric_obj("rmse"), "r2": metric_obj("r2")},
                  # Chart assets remain in the candidate manifest and local UI. The current
                  # Phase 5 schema requires APPROVED for every VERIFIED figure, which would
                  # falsely imply public publication review for this Owner-authorized local preview.
                  "fold_summary": None, "figures": [],
                  "interval": {"int_f": {"status": "UNAVAILABLE", "reason_code": "NO_FORMAL_INTERVAL_METHOD", "method": None, "assumptions_ref": None},
                               "int_s": {"status": "UNAVAILABLE", "reason_code": "MODEL_UNCERTAINTY_INTERVAL_NOT_ESTIMATED", "interval_type": None, "method": None, "nominal_level": None, "population": None, "asset_ref": None, "coverage_evidence": None, "review_url": None}},
                  "evidence": {"source_artifact_sha256": evaluation["data_sha256"], "source_ref": DATASET_SOURCE_REF,
                               "protocol_version": protocol_id, "review_url": None},
                  "asset_status": "AVAILABLE", "review_status": "AWAITING_REVIEW",
                  "limitations": evaluation["limitations"], "linked_evaluation_ids": []}],
              "ui": {"default_population": "holdout", "population_options": [{"id": "holdout", "label": "Independent holdout"}],
                     "figure_tabs": [{"figure_id": "FIG-P5-01", "label": "Actual vs predicted", "kind": "actual_vs_predicted"},
                                     {"figure_id": "FIG-P5-02", "label": "Ownership intervals", "kind": "residual_vs_predicted"},
                                     {"figure_id": "FIG-P5-03", "label": "Residuals", "kind": "residual_distribution"}],
                     "metric_order": ["mae", "rmse", "r2"], "interval_figure_id": "FIG-P5-04"}}
    write_json(destination / PHASE_REFS[5], phase5)

    inference_schema = {"case_id": CASE_ID, "model_version": "1.0.0", "model_name": "Random Forest Regressor · " + config_id,
                        "target": "K midpoint proxy", "input_fields": MODEL_INPUT_FIELDS,
                        "required": [*MODEL_INPUT_FIELDS, "review_count"],
                        "genre_options": [x["genre"] for x in phase2["genre_summary"][:30]],
                        "limits": {"price_min": 0, "price_max": 1000, "release_year_min": 1970, "release_year_max": 2035,
                                   "review_count_min": 1, "review_count_max": 10000000},
                        "model_path": "private local model file; not in the Case Package"}
    write_json(destination / "phases/phase-06/input-schema.json", inference_schema)
    phase6 = {"schema_version": "1.0.0", "case_id": CASE_ID, "status": "VERIFIED",
              "models": [{"model_id": "steam-review-multiplier-random-forest", "model_version": "1.0.0",
                          "source_execution_run_id": execution_id, "source_configuration_id": config_id,
                          "model_status": "LOCAL_PRIVATE_VERIFIED", "input_schema_ref": "phases/phase-06/input-schema.json",
                          "readiness": {"predict_enabled": True, "scope": "local-loopback-preview-only", "message": "Fitted model is available to the local preview service; no public or Production inference endpoint."}}],
              "readiness": {"predict_enabled": True, "reason_code": "LOCAL_LOOPBACK_PREVIEW", "message": "本機 loopback 預覽可使用已訓練模型；不提供 Production API。"}}
    write_json(destination / PHASE_REFS[6], phase6)

    figure_manifest = {"schema_version": "1.0.0", "case_id": CASE_ID,
                       "figures": [{"figure_id": fid, "case_id": CASE_ID, "phase": 2,
                                    "analysis_id": aid, "svg_ref": f"phases/phase-02/figures/{image}",
                                    "png_ref": None, "sha256_svg": _sha(destination / f"phases/phase-02/figures/{image}"),
                                    "sha256_png": None, "status": "VERIFIED"}
                                   for aid, fid, _, image, _ in figure_specs]}
    write_json(destination / "assets/figure-manifest.json", figure_manifest)
    write_json(destination / "assets/execution-manifest.json", {
        "schema_version": "1.0.0", "case_id": CASE_ID, "run_id": execution_id,
        "source_dataset_sha256": evaluation["data_sha256"], "split_seed": 42,
        "python": evaluation["software"]["python"], "pandas": evaluation["software"]["pandas"],
        "numpy": evaluation["software"]["numpy"], "scikit_learn": evaluation["software"]["scikit_learn"],
        "source_code_provenance": source_code_provenance,
        "development_appid_sha256": evaluation["split"]["development_appid_sha256"],
        "holdout_appid_sha256": evaluation["split"]["holdout_appid_sha256"],
        "cv_fold_membership_sha256": evaluation["cv"]["fold_membership_sha256"],
        "raw_data_and_row_predictions_included": False})

    phases = {}
    for phase, ref in PHASE_REFS.items():
        doc = json.loads((destination / ref).read_text(encoding="utf-8"))
        phases[f"phase{phase}"] = {"status": doc["status"], "data_ref": ref}
    package = {"package_schema_version": "1.0.0", "package_id": f"{CASE_ID}-{REVISION}", "case_id": CASE_ID,
               "package_revision": REVISION, "package_status": "PARTIAL",
               "publication": {"approved": False, "release_id": None, "review_status": "PENDING"},
               "case_ref": "case.json", "phases": phases, "asset_manifest_ref": "assets/figure-manifest.json",
               "files": _manifest(destination)}
    write_json(destination / "package.json", package)
    _schema_check(repo_root, destination)
    validation = validate_case_package(destination)
    return {"status": "PASS", "package_root": str(destination), "case_id": CASE_ID,
            "revision": REVISION, "file_count": len(package["files"]), "package_sha256": _sha(destination / "package.json"),
            "schema_validation": "PASS", "contract_validation": validation}


DATASET_SOURCE_REF = "https://www.kaggle.com/datasets/artermiloff/steam-games-dataset"
