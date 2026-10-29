"""Bounded, reproducible Used Car Price case pipeline.

The competition test file is deliberately never read.  All preprocessing and
feature selection are fitted inside the applicable training fold.  Raw rows,
OOF predictions and serialized estimators stay in the caller's ignored output
directory; the public projection contains aggregate evidence only.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_selection import RFE, f_regression, mutual_info_regression
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


CASE_ID = "used-car-price-optimized"
CASE_TITLE = "中古車售價預測｜Used Car Price Lab"
RUN_ID = "used-car-e2e-20261028-03"
SUPERSEDES_RUN_ID = "used-car-e2e-20261028-02"
SOURCE_URL = "https://www.kaggle.com/competitions/used-car-price-prediction-challenge/data?select=train_data_v2.csv"
DATASET_LICENSE = "CC BY-NC-SA 4.0"
ATTRIBUTION = "Used Car Price Prediction Challenge dataset by ZeinaDallal, via Kaggle; web-scraped vehicle listings."
SEED = 42
HOLDOUT_FRACTION = 0.20
CV_FOLDS = 3
MISSING_TOKENS = {"", "NA", "N/A", "NULL", "NaN", "nan"}

TARGET = "price"
IDENTIFIERS = {"ID", "vin"}
LEAKAGE_OR_PROXY = {"search_price", "est._monthly_pmt"}
TEXT_FIELDS = {"engine", "features_list", "title"}
TEMPORAL_FIELDS = {"scrape_timestamp"}
DUPLICATE_REPRESENTATIONS = {"mileage", "trans"}
NUMERIC_FIELDS = {"odometer", "year", "feature_count", "image_count"}

# Small, declared candidate set. "Best" means best among these completed
# candidates by mean-fold Development RMSE, never a global optimum claim.
CANDIDATES: tuple[dict[str, Any], ...] = (
    {"method_id": "ols_baseline", "params": {"selection": "all"}},
    *({"method_id": "pearson", "params": {"k": k}} for k in (10, 20, 40)),
    *({"method_id": "mutual_information", "params": {"k": k}} for k in (10, 20, 40)),
    *({"method_id": "lasso", "params": {"alpha": alpha}} for alpha in (0.01, 0.1, 1.0)),
    *({"method_id": "elastic_net", "params": {"alpha": alpha, "l1_ratio": ratio}}
      for alpha in (0.01, 0.1) for ratio in (0.5, 0.9)),
    *({"method_id": "ridge_rfe", "params": {"k": k}} for k in (10, 20, 40)),
)


class UsedCarResearchError(ValueError):
    """Input or evidence does not meet this case's frozen contract."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _json_bytes(value)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(payload)
    os.replace(temp, path)


def _missing_mask(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.apply(lambda column: column.astype("string").isin(MISSING_TOKENS))


def _detect_free_text_fields(frame: pd.DataFrame) -> dict[str, str]:
    """Identify free-text predictors without treating every string category as text.

    Known long-form/listing fields are excluded by semantic policy. For other
    fields, a conservative high-cardinality + long-value rule catches unseen
    free text while retaining short categorical labels.
    """
    detected: dict[str, str] = {field: "known free-text/listing field" for field in TEXT_FIELDS if field in frame}
    missing = _missing_mask(frame)
    for field in frame.columns:
        if field in detected or field in NUMERIC_FIELDS or field in IDENTIFIERS or field == TARGET:
            continue
        values = frame.loc[~missing[field], field].astype(str)
        if len(values) < 20:
            continue
        lengths = values.str.len()
        unique_ratio = values.nunique(dropna=True) / max(1, len(values))
        # Short, repeated labels remain categorical; long, mostly unique text is
        # excluded from model input and recorded in field decisions.
        if float(lengths.median()) >= 40 and float(unique_ratio) >= 0.50:
            detected[str(field)] = "automatic free-text rule: median length >= 40 and unique ratio >= 0.50"
    return detected


def _normalize_source(path: Path) -> tuple[pd.DataFrame, pd.Series, list[str], list[str], list[str], dict[str, str]]:
    frame = pd.read_csv(path, dtype="string", keep_default_na=False, encoding="utf-8", low_memory=False)
    required = {TARGET, "ID", "vin"}
    if not required.issubset(frame.columns):
        raise UsedCarResearchError("source CSV is missing required target or identity fields")
    if frame.empty:
        raise UsedCarResearchError("source CSV has no records")
    target = pd.to_numeric(frame[TARGET].str.replace(",", "", regex=False), errors="coerce")
    valid_target = target.notna() & np.isfinite(target) & (target > 0)
    frame = frame.loc[valid_target].copy()
    target = target.loc[valid_target].astype(float)
    if len(frame) < 30:
        raise UsedCarResearchError("too few positive labeled records for the declared CV and holdout protocol")
    frame[TARGET] = target
    for field in NUMERIC_FIELDS:
        if field in frame:
            if field == "year":
                # Source field contains a year prefix followed by scraped listing
                # prose. Preserve the CSV; use only a leading four-digit year.
                prefix = frame[field].str.strip().str.extract(r"^((?:19|20)\d{2})(?:\b|\s)", expand=False)
                frame[field] = pd.to_numeric(prefix, errors="coerce")
            else:
                frame[field] = pd.to_numeric(frame[field].str.replace(",", "", regex=False), errors="coerce")
    text_fields = _detect_free_text_fields(frame)
    excluded = IDENTIFIERS | LEAKAGE_OR_PROXY | set(text_fields) | TEMPORAL_FIELDS | DUPLICATE_REPRESENTATIONS | {TARGET}
    features = [field for field in frame.columns if field not in excluded]
    if not features:
        raise UsedCarResearchError("no eligible predictors remain after the declared exclusions")
    numeric = [field for field in features if field in NUMERIC_FIELDS]
    categorical = [field for field in features if field not in numeric]
    return frame, target, features, numeric, categorical, text_fields


def _preprocessor(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    numeric_pipe = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=5, sparse_output=True)),
    ])
    return ColumnTransformer(
        [("num", numeric_pipe, numeric), ("cat", categorical_pipe, categorical)],
        remainder="drop", sparse_threshold=1.0, verbose_feature_names_out=True,
    )


def _encoded_features(transformer: ColumnTransformer, raw_features: list[str], numeric: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
    names = [str(value) for value in transformer.get_feature_names_out()]
    lineage = []
    for index, name in enumerate(names):
        source = None
        if name.startswith("num__"):
            source = name.removeprefix("num__")
        elif name.startswith("cat__"):
            encoded = name.removeprefix("cat__")
            source = next((field for field in sorted(raw_features, key=len, reverse=True)
                           if field not in numeric and (encoded == field or encoded.startswith(field + "_"))), None)
        if source is None:
            raise UsedCarResearchError("could not bind an encoded feature to a source field")
        semantic = "discrete" if source in {"year", "feature_count", "image_count"} else ("continuous" if source in numeric else "nominal")
        lineage.append({"index": index, "encoded_feature": name, "source_columns": [source],
                        "semantic_type": semantic, "transformation": "median_impute_and_scale" if source in numeric else "mode_impute_and_one_hot"})
    return names, lineage


def _select(method: str, params: Mapping[str, Any], matrix: Any, y: np.ndarray, names: list[str]) -> np.ndarray:
    count = matrix.shape[1]
    if method == "ols_baseline":
        return np.ones(count, dtype=bool)
    if method in {"pearson", "mutual_information"}:
        k = min(int(params["k"]), count)
        if method == "pearson":
            # Dense input avoids sparse norm round-off warnings on constant
            # one-hot columns; the row count and encoded matrix are bounded.
            dense = matrix.toarray() if hasattr(matrix, "toarray") else np.asarray(matrix)
            scores, _ = f_regression(dense, y, force_finite=True)
        else:
            discrete = np.asarray([not name.startswith("num__") for name in names], dtype=bool)
            dense = matrix.toarray() if hasattr(matrix, "toarray") else np.asarray(matrix)
            scores = mutual_info_regression(dense, y, random_state=SEED, discrete_features=discrete)
        scores = np.nan_to_num(np.asarray(scores, dtype=float), nan=-np.inf, posinf=-np.inf, neginf=-np.inf)
        selected = np.argsort(scores, kind="stable")[-k:]
        mask = np.zeros(count, dtype=bool)
        mask[selected] = True
        return mask
    target_sd = float(np.std(y)) or 1.0
    scaled_y = (y - float(np.mean(y))) / target_sd
    if method == "lasso":
        estimator = Lasso(alpha=float(params["alpha"]), max_iter=10000, tol=1e-4, random_state=SEED)
        estimator.fit(matrix, scaled_y)
        mask = np.abs(estimator.coef_) > 1e-10
        if not mask.any():
            raise UsedCarResearchError("Lasso selected no encoded features for this fold")
        return mask
    if method == "elastic_net":
        estimator = ElasticNet(alpha=float(params["alpha"]), l1_ratio=float(params["l1_ratio"]),
                               max_iter=10000, tol=1e-4, random_state=SEED, selection="cyclic")
        estimator.fit(matrix, scaled_y)
        mask = np.abs(estimator.coef_) > 1e-10
        if not mask.any():
            raise UsedCarResearchError("Elastic Net selected no encoded features for this fold")
        return mask
    if method == "ridge_rfe":
        k = min(int(params["k"]), count)
        selector = RFE(Ridge(alpha=1.0), n_features_to_select=k, step=0.5)
        selector.fit(matrix, scaled_y)
        return selector.support_
    raise UsedCarResearchError(f"unknown feature-selection method: {method}")


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {"mae": float(mean_absolute_error(actual, predicted)),
            "rmse": float(math.sqrt(mean_squared_error(actual, predicted))),
            "r2": float(r2_score(actual, predicted))}


def _config_id(candidate: Mapping[str, Any]) -> str:
    payload = _json_bytes(dict(candidate))
    return f"car-{candidate['method_id'].replace('_', '-')}-{sha256_bytes(payload)[:12]}"


def _safe_hist_svg(title: str, values: np.ndarray, xlabel: str, bins: int = 12) -> str:
    counts, edges = np.histogram(values, bins=min(bins, max(3, int(math.sqrt(len(values))))))
    width, height = 760, 360
    left, top, plot_w, plot_h = 68, 86, 650, 205
    max_count = max(int(value) for value in counts) or 1
    slot = plot_w / len(counts)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             f'<title id="title">{title}</title><desc id="desc">Aggregated histogram; raw records are not displayed. {len(values)} eligible observations.</desc>',
             '<rect width="100%" height="100%" fill="#fff"/><style>text{font:12px Arial;fill:#243447}.bar{fill:#3977a8}</style>',
             f'<text x="18" y="28" font-size="18">{title}</text>',
             '<text x="18" y="52" fill="#8a3c20">REAL TRAINING DATA · AGGREGATED</text>',
             f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="#536273"/>']
    for i, count in enumerate(counts):
        bar_h = plot_h * int(count) / max_count
        x = left + i * slot + 2
        y = top + plot_h - bar_h
        parts.append(f'<rect class="bar" x="{x:.2f}" y="{y:.2f}" width="{max(1,slot-4):.2f}" height="{bar_h:.2f}"/>')
        parts.append(f'<text x="{x+slot/2:.2f}" y="{max(76,y-5):.2f}" text-anchor="middle">{int(count)}</text>')
    parts.extend([f'<text x="{left+plot_w/2}" y="{height-18}" text-anchor="middle">{xlabel} (binned)</text>', '</svg>'])
    return "\n".join(parts) + "\n"


def _phase1_sections(source_sha: str) -> list[dict[str, str]]:
    return [
        {"section_id": "research-question", "title": "研究背景與問題｜Research Background & Questions",
         "body": "本研究以中古車網路刊登資料為對象，探討特徵選擇與迴歸模型預測刊登價格的表現。資料包含車輛規格、使用狀況與刊登資訊；加入更多欄位不一定能持續改善誤差，因此比較不同選擇策略及特徵數量的取捨。研究問題：RQ1 不同特徵選擇方法是否影響預測表現？RQ2 特徵數量與預測誤差有何關係？RQ3 能否在維持預測品質下減少模型特徵？這些是待檢驗問題，不是已證實結論。"},
        {"section_id": "research-objectives", "title": "研究目標｜Research Objectives",
         "body": "建立可重現的中古車價格迴歸流程；檢查資料品質，將識別欄位、自由文字及疑似價格洩漏欄位自模型輸入排除並逐欄記錄；使用訓練折內擬合的補值與類別編碼比較基準模型和特徵選擇方法；對混有刊登文字的年份欄只解析開頭四位年份，原始 CSV 保持不變；記錄特徵數量、交叉驗證與內部保留集結果；以可追溯 Case Package 呈現計算結果。"},
        {"section_id": "methodology", "title": "研究方法｜CRISP-DM Methodology",
         "body": "依 CRISP-DM 六階段進行：Phase 1 定義研究問題；Phase 2 檢視欄位、缺失、重複與價格分布，並逐欄記錄排除原因；Phase 3 以訓練資料擬合補值與 One-Hot Encoding；Phase 4 以固定種子及三折交叉驗證比較預先列明的線性迴歸候選；Phase 5 分開報告 Development OOF 與內部 Holdout；Phase 6 驗證本機模型重載與推論能力。可訓練的短類別欄位仍保留；長篇自由文字欄位不直接送入模型。Kaggle 的 test_data_v2.csv 不參與訓練、調參、模型選擇或指標計算。"},
        {"section_id": "evaluation", "title": "評估指標｜Evaluation Metrics",
         "body": "RMSE（美元 USD）為主要誤差指標，越低越好，且對較大誤差更敏感；MAE（美元 USD）為輔助平均絕對誤差；R² 描述目標變異的解釋程度，不是預測正確率；Selected Feature Count 用於觀察特徵數量與模型誤差的取捨。比較只在相同資料切分及評估母體下解讀。"},
        {"section_id": "scope-limitations", "title": "研究範圍與限制｜Scope & Limitations",
         "body": "資料來自網路刊登而非已驗證成交紀錄，預測目標是刊登價格，不應解讀為市場估價。資料量與來源市場有限，欄位缺漏、重複表示、時間漂移及高基數類別可能影響結果。Development CV／OOF 與內部 Holdout 分開呈現；特徵選擇不代表因果關係；候選搜尋結果只代表已執行的有限候選，不保證全域最佳。網站目前提供研究展示，不宣稱已部署線上預測 API。"},
        {"section_id": "data-provenance", "title": "研究資料與來源｜Data Provenance",
         "body": f"訓練來源：train_data_v2.csv；來源頁面：{SOURCE_URL}；資料集標示授權：{DATASET_LICENSE}；作者署名：{ATTRIBUTION}；訓練檔 SHA-256：{source_sha}。原始 CSV 僅留在本機 ignored local/。Competition rules 的完整條款與公開發布適用性仍需核對；公開產物只包含聚合統計與圖表，不包含原始列、VIN、ID 或逐筆預測。"},
    ]


def run_used_car_research(input_csv: str | Path, output_root: str | Path) -> dict[str, Any]:
    """Run one bounded train-only data/model experiment into a fresh local path.

    This function never reads a competition test CSV and never overwrites an
    existing output directory. Returns the private checkpoint summary.
    """
    started = time.monotonic()
    source = Path(input_csv).expanduser().resolve(strict=True)
    output = Path(output_root)
    if output.exists():
        raise UsedCarResearchError("output directory already exists; refusing to overwrite evidence")
    if source.suffix.lower() != ".csv" or not source.is_file():
        raise UsedCarResearchError("input must be an existing CSV file")
    output.parent.mkdir(parents=True, exist_ok=True)
    source_sha = sha256_file(source)
    raw, y_all, features, numeric, categorical, text_fields = _normalize_source(source)
    full = raw.copy()
    full[TARGET] = y_all
    # Keep the source untouched; field removals apply only to model inputs.
    X = full[features].copy()
    y = y_all.to_numpy(dtype=float)
    row_positions = np.arange(len(full))
    dev_pos, holdout_pos = train_test_split(row_positions, test_size=HOLDOUT_FRACTION, random_state=SEED)
    X_dev, X_holdout = X.iloc[dev_pos], X.iloc[holdout_pos]
    y_dev, y_holdout = y[dev_pos], y[holdout_pos]
    cv = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED)
    fold_splits = list(cv.split(X_dev, y_dev))
    candidate_results: list[dict[str, Any]] = []
    winner_oof: dict[str, np.ndarray] = {}
    winner_details: dict[str, Any] = {}
    folds_cache = []
    run_dir = output / "private"
    run_dir.mkdir(parents=True)

    fold_membership = np.zeros(len(y_dev), dtype=int)
    for fold_no, (train_idx, valid_idx) in enumerate(fold_splits, start=1):
        fold_membership[valid_idx] = fold_no
        transformer = _preprocessor(numeric, categorical)
        train_matrix = transformer.fit_transform(X_dev.iloc[train_idx])
        valid_matrix = transformer.transform(X_dev.iloc[valid_idx])
        scaler = StandardScaler(with_mean=False)
        train_matrix = scaler.fit_transform(train_matrix)
        valid_matrix = scaler.transform(valid_matrix)
        encoded_names, lineage = _encoded_features(transformer, features, numeric)
        folds_cache.append({"fold": fold_no, "train_idx": train_idx, "valid_idx": valid_idx,
                            "train_matrix": train_matrix, "valid_matrix": valid_matrix,
                            "train_y": y_dev[train_idx], "valid_y": y_dev[valid_idx],
                            "encoded_names": encoded_names, "lineage": lineage})

    for candidate_order, candidate in enumerate(CANDIDATES):
        config_id = _config_id(candidate)
        per_fold = []
        oof = np.full(len(y_dev), np.nan, dtype=float)
        selected_by_fold = []
        encoded_counts = []
        error = None
        for cached in folds_cache:
            try:
                mask = _select(candidate["method_id"], candidate["params"], cached["train_matrix"], cached["train_y"], cached["encoded_names"])
                if int(mask.sum()) < 1:
                    raise UsedCarResearchError("selector returned no features")
                estimator = LinearRegression()
                estimator.fit(cached["train_matrix"][:, mask], cached["train_y"])
                prediction = estimator.predict(cached["valid_matrix"][:, mask])
                actual = cached["valid_y"]
                metrics = _metrics(actual, prediction)
                oof[cached["valid_idx"]] = prediction
                names = [name for name, keep in zip(cached["encoded_names"], mask) if keep]
                sources = sorted({source for item in cached["lineage"] if item["encoded_feature"] in set(names) for source in item["source_columns"]})
                per_fold.append({"fold": cached["fold"], "status": "VERIFIED", "n_train": len(cached["train_idx"]),
                                 "n_validation": len(cached["valid_idx"]), **metrics})
                selected_by_fold.append({"fold": cached["fold"], "encoded_count": len(cached["encoded_names"]),
                                         "selected_encoded_names": names, "selected_raw_sources": sources,
                                         "feature_lineage": [item for item in cached["lineage"] if item["encoded_feature"] in set(names)]})
                encoded_counts.append(len(cached["encoded_names"]))
            except Exception as exc:  # bounded candidate failure is isolated and recorded
                error = f"{type(exc).__name__}: {str(exc)[:180]}"
                break
        if error or len(per_fold) != CV_FOLDS or not np.isfinite(oof).all():
            candidate_results.append({"configuration_id": config_id, "candidate_order": candidate_order,
                                      "method_id": candidate["method_id"], "params": candidate["params"],
                                      "status": "ERROR", "error": error or "incomplete OOF fold coverage",
                                      "fold_results": per_fold, "selected_features_by_fold": selected_by_fold})
            continue
        mean_metrics = {key: float(np.mean([fold[key] for fold in per_fold])) for key in ("mae", "rmse", "r2")}
        std_metrics = {key: float(np.std([fold[key] for fold in per_fold], ddof=1)) for key in ("mae", "rmse", "r2")}
        item = {"configuration_id": config_id, "candidate_order": candidate_order,
                "method_id": candidate["method_id"], "params": candidate["params"], "status": "VERIFIED",
                "fold_results": per_fold, "mean_fold_metrics": mean_metrics, "sample_sd": std_metrics,
                "feature_count_mean": float(np.mean([len(fold["selected_encoded_names"]) for fold in selected_by_fold])),
                "encoded_count_mean": float(np.mean(encoded_counts)), "selected_features_by_fold": selected_by_fold}
        candidate_results.append(item)

    completed = [item for item in candidate_results if item["status"] == "VERIFIED"]
    if not completed:
        raise UsedCarResearchError("all declared CV candidates failed; no model result will be published")
    method_winners = []
    for method in sorted({item["method_id"] for item in completed}):
        method_winners.append(min((item for item in completed if item["method_id"] == method),
                                  key=lambda item: (item["mean_fold_metrics"]["rmse"], item["feature_count_mean"], item["candidate_order"])))
    winner = min(method_winners, key=lambda item: (item["mean_fold_metrics"]["rmse"], item["feature_count_mean"], item["candidate_order"]))
    best_candidate = CANDIDATES[winner["candidate_order"]]

    # One sealed internal holdout evaluation after CV-based selection.
    holdout_transformer = _preprocessor(numeric, categorical)
    dev_matrix = holdout_transformer.fit_transform(X_dev)
    holdout_matrix = holdout_transformer.transform(X_holdout)
    holdout_scaler = StandardScaler(with_mean=False)
    dev_matrix = holdout_scaler.fit_transform(dev_matrix)
    holdout_matrix = holdout_scaler.transform(holdout_matrix)
    holdout_names, holdout_lineage = _encoded_features(holdout_transformer, features, numeric)
    holdout_mask = _select(best_candidate["method_id"], best_candidate["params"], dev_matrix, y_dev, holdout_names)
    holdout_estimator = LinearRegression().fit(dev_matrix[:, holdout_mask], y_dev)
    holdout_pred = holdout_estimator.predict(holdout_matrix[:, holdout_mask])
    holdout_metrics = _metrics(y_holdout, holdout_pred)

    winning_oof = np.full(len(y_dev), np.nan, dtype=float)
    # Reconstruct only the winner's OOF predictions; no candidate is refit on
    # validation folds, and these row-level values remain in the ignored area.
    for cached in folds_cache:
        mask = _select(best_candidate["method_id"], best_candidate["params"], cached["train_matrix"], cached["train_y"], cached["encoded_names"])
        fitted = LinearRegression().fit(cached["train_matrix"][:, mask], cached["train_y"])
        winning_oof[cached["valid_idx"]] = fitted.predict(cached["valid_matrix"][:, mask])
    if not np.isfinite(winning_oof).all():
        raise UsedCarResearchError("winning OOF coverage is incomplete")
    pooled_oof = _metrics(y_dev, winning_oof)

    # Fit a final local-only inference pipeline on all labeled training rows.
    final_transformer = _preprocessor(numeric, categorical)
    final_matrix = final_transformer.fit_transform(X)
    final_scaled = StandardScaler(with_mean=False)
    final_matrix = final_scaled.fit_transform(final_matrix)
    final_names, final_lineage = _encoded_features(final_transformer, features, numeric)
    final_mask = _select(best_candidate["method_id"], best_candidate["params"], final_matrix, y, final_names)
    final_estimator = LinearRegression().fit(final_matrix[:, final_mask], y)
    from joblib import dump, load
    model_bundle = {"transformer": final_transformer, "scaler": final_scaled, "mask": final_mask,
                    "estimator": final_estimator, "features": features, "target": TARGET,
                    "configuration_id": winner["configuration_id"], "run_id": RUN_ID, "source_sha256": source_sha}
    model_path = run_dir / "final-model.joblib"
    dump(model_bundle, model_path)
    reloaded = load(model_path)
    smoke = reloaded["estimator"].predict(reloaded["scaler"].transform(reloaded["transformer"].transform(X.iloc[[0]]) )[:, reloaded["mask"]])
    if len(smoke) != 1 or not np.isfinite(smoke[0]):
        raise UsedCarResearchError("reloaded final model failed its local inference smoke")

    pd.DataFrame({"dev_index": dev_pos, "actual": y_dev, "oof_predicted": winning_oof,
                  "fold": fold_membership}).to_csv(run_dir / "winner-oof-private.csv", index=False)
    # Holdout row predictions are retained privately for audit only.
    pd.DataFrame({"source_position": holdout_pos, "actual": y_holdout, "predicted": holdout_pred}).to_csv(run_dir / "holdout-private.csv", index=False)

    # Aggregate-only figures; no raw row points or identifiers are published.
    figs_dir = output / "figures"
    figs_dir.mkdir()
    (figs_dir / "target-distribution.svg").write_text(_safe_hist_svg("中古車刊登價格分布", y, "價格 USD"), encoding="utf-8")
    residual = y_dev - winning_oof
    (figs_dir / "residual-distribution.svg").write_text(_safe_hist_svg("OOF 殘差分布", residual, "實際值 − 預測值 USD"), encoding="utf-8")
    # Missingness chart from the original CSV cells, based on the declared tokens.
    original = pd.read_csv(source, dtype="string", keep_default_na=False, encoding="utf-8", low_memory=False)
    missing_counts = _missing_mask(original).sum().sort_values(ascending=False)
    top_missing = [(str(key), int(value)) for key, value in missing_counts.items() if int(value) > 0][:18]
    width, height = 760, max(130, 82 + 25 * len(top_missing))
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="t d" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<title id="t">中古車資料缺失值概況</title><desc id="d">訓練 CSV 聚合缺失值筆數；不含資料列內容。</desc>',
           '<rect width="100%" height="100%" fill="#fff"/><style>text{font:12px Arial;fill:#243447}.bar{fill:#3977a8}</style>',
           '<text x="18" y="25" font-size="18">缺失值欄位概況</text><text x="18" y="47" fill="#8a3c20">REAL TRAINING DATA · AGGREGATED</text>']
    for i, (field, count) in enumerate(top_missing):
        yy = 66 + i * 25
        svg.extend([f'<text x="18" y="{yy+14}">{field}</text>',
                    f'<rect class="bar" x="220" y="{yy}" width="{min(420,420*count/max(1,len(original))):.2f}" height="16"/>',
                    f'<text x="650" y="{yy+13}">{count} ({count/len(original)*100:.1f}%)</text>'])
    svg.append('</svg>')
    (figs_dir / "missingness.svg").write_text("\n".join(svg)+"\n", encoding="utf-8")

    source_bytes = source.read_bytes()
    config = {"case_id": CASE_ID, "run_id": RUN_ID, "source_file": "train_data_v2.csv", "source_sha256": source_sha,
              "target": TARGET, "target_unit": "USD", "excluded_fields": sorted(set(excluded_fields()) | set(text_fields)),
              "model_features": features, "split": {"type": "random_holdout", "fraction": HOLDOUT_FRACTION, "seed": SEED},
              "cv": {"folds": CV_FOLDS, "shuffle": True, "seed": SEED},
              "candidate_count": len(CANDIDATES), "candidate_rule": "method winner by minimum mean-fold Development RMSE; tie-break fewer selected features then declared order",
              "numeric_features": numeric, "categorical_features": categorical,
              "preprocessing": {"numeric_imputer": "median", "categorical_imputer": "most_frequent", "one_hot_min_frequency": 5, "fit_scope": "each training fold; holdout evaluation fitted on Development only"},
              "value_normalization": {"year": "extract leading 4-digit 19xx/20xx year only; discard trailing scraped text"},
              "automatic_text_exclusion": {field: reason for field, reason in text_fields.items()},
              "code_sha256": sha256_file(Path(__file__).resolve()), "sklearn_version": __import__("sklearn").__version__,
              "pandas_version": pd.__version__, "numpy_version": np.__version__}
    config_sha = sha256_bytes(_json_bytes(config))
    _write_json(output / "config.json", config)
    original_missing = _missing_mask(original)
    field_decisions = []
    for field in original.columns:
        if field == TARGET:
            action, semantic = "exclude", "target"
        elif field in IDENTIFIERS:
            action, semantic = "exclude", "identifier"
        elif field in LEAKAGE_OR_PROXY:
            action, semantic = "exclude", "leakage_proxy"
        elif field in text_fields:
            action, semantic = "exclude", "text"
        elif field in TEMPORAL_FIELDS:
            action, semantic = "exclude", "temporal"
        elif field in DUPLICATE_REPRESENTATIONS:
            action, semantic = "exclude", "duplicate_representation"
        else:
            action = "include"
            semantic = "discrete" if field in {"year", "feature_count", "image_count"} else ("continuous" if field in numeric else "nominal")
        field_decisions.append({"field": str(field), "semantic_type": semantic, "decision": action,
                                "reason": (text_fields[field] if field in text_fields else "not used as a predictor; source CSV preserved") if action == "exclude" else "eligible predictor"})
    target_valid_count = len(y)
    missing_count = int(original_missing.to_numpy().sum())
    target_hist, target_edges = np.histogram(y, bins=min(12, max(3, int(math.sqrt(len(y))))))
    phase1 = {"schema_version": "1.0.0", "case_id": CASE_ID, "status": "VERIFIED", "sections": _phase1_sections(source_sha)}
    phase2 = {
        "schema_version": "1.0.0", "case_id": CASE_ID, "status": "VERIFIED", "default_analysis_id": "field-decisions",
        "analyses": [
            {"id": "field-decisions", "figure_id": "figure-field-decisions", "title": "欄位分類與特徵決策", "status": "VERIFIED", "image_ref": None, "table_ref": None,
             "description": "依欄位語意分類；排除目標、識別碼、自由文字、時間戳、重複表示與價格代理欄位。排除只作用於模型輸入，原始 CSV 不變。",
             "finding": "; ".join(f"{item['field']} [{item['semantic_type']}] {item['decision']}" for item in field_decisions),
             "limitations": "資料來源為中古車網路刊登；分類是本研究的建模決策，不是欄位的普遍因果解釋。", "provenance_ref": "assets/execution-manifest.json"},
            {"id": "missingness", "figure_id": "figure-missingness", "title": "缺失值分析", "status": "VERIFIED", "image_ref": "phases/phase-02/figures/missingness.svg", "table_ref": None,
             "description": f"{len(original)} 筆、{len(original.columns)} 欄原始訓練資料的缺失概況。缺失判定採明列 token；合法字串 None 不視為缺失。",
             "finding": "Rows=" + str(len(original)) + "; missing cells by field: " + "; ".join(f"{field}={int(count)}/{len(original)}" for field, count in original_missing.sum().items()),
             "limitations": "圖表僅顯示聚合筆數與比例，不包含逐列資料。", "provenance_ref": "assets/execution-manifest.json"},
            {"id": "target-distribution", "figure_id": "figure-target-distribution", "title": "刊登價格分布", "status": "VERIFIED", "image_ref": "phases/phase-02/figures/target-distribution.svg", "table_ref": None,
             "description": "訓練資料中有效正值價格的分箱分布；不使用 Kaggle 測試資料。",
             "finding": f"Positive numeric price values={target_valid_count}; excluded missing/non-numeric/non-positive target rows={len(original)-target_valid_count}.",
             "limitations": "分箱圖只呈現聚合分布；價格為刊登價，不等同成交價。", "provenance_ref": "assets/execution-manifest.json"},
            {"id": "data-quality", "figure_id": "figure-data-quality", "title": "資料品質與欄位摘要", "status": "VERIFIED", "image_ref": None, "table_ref": None,
             "description": "欄位數、有效價格筆數、完全重複檢查與模型輸入排除策略。",
             "finding": f"Rows={len(original)}; columns={len(original.columns)}; valid_price_rows={target_valid_count}; missing_cells={missing_count}; exact_duplicates_ignoring_ID_VIN_timestamp={int(original.drop(columns=[c for c in ['ID','vin','scrape_timestamp'] if c in original],errors='ignore').duplicated().sum())}; model_predictor_columns={len(features)}.",
             "limitations": "完全重複檢查不等同於近似車輛或重複刊登的人工核對。", "provenance_ref": "assets/execution-manifest.json"},
        ]}
    _write_json(output / "phases/phase-01/content.json", phase1)
    _write_json(output / "phases/phase-02/analyses.json", phase2)
    stage_counts = {kind: sum(1 for item in field_decisions if item["decision"] == "include" and item["semantic_type"] == kind)
                    for kind in ("nominal", "ordinal", "discrete", "continuous")}
    raw_total = len(features)
    encoded_counts = {kind: sum(1 for item in final_lineage if item["semantic_type"] == kind)
                      for kind in ("nominal", "ordinal", "discrete", "continuous")}
    phase3_lineage = {
        "schema_version": "1.0.0", "case_id": CASE_ID, "source_data_sha256": source_sha,
        "config_sha256": config_sha, "phase3_result_sha256": None, "pipeline_source_sha256": config["code_sha256"],
        "pipeline_version": "used-car-fold-local-preprocessing-v1", "training_index_sha256": sha256_bytes(np.asarray(dev_pos,dtype=np.int64).tobytes()),
        "feature_names_sha256": sha256_bytes("\n".join(final_names).encode("utf-8")), "fit_population": "development_train_only",
        "training_rows": len(X_dev), "validation_rows": len(X_holdout),
        "classification_method": "vehicle field semantics; one-hot outputs inherit nominal source semantics; numeric outputs retain discrete/continuous semantics.",
        "stages": {"raw": {"total": raw_total, "counts": stage_counts}, "filtered": {"total": raw_total, "counts": stage_counts},
                   "processed": {"total": raw_total, "counts": stage_counts}, "encoded": {"total": len(final_names), "counts": encoded_counts}},
        "excluded_fields": field_decisions, "encoded_features": final_lineage,
    }
    phase3 = {
        "schema_version": "1.0.0", "case_id": CASE_ID, "status": "VERIFIED",
        "feature_types": [{"type_id": kind, "label": label} for kind,label in (("nominal","名目類別"),("ordinal","有序類別"),("discrete","離散數值"),("continuous","連續數值"))],
        "stages": [
            {"id":"raw","label":"原始可用預測欄位","unit":"raw_columns","total":raw_total,"total_status":"VERIFIED","segments":[{"type_id":k,"count":v} for k,v in stage_counts.items()],"distribution_status":"VERIFIED"},
            {"id":"filtered","label":"排除識別／文字／洩漏欄位後","unit":"pre_encoding_columns","total":raw_total,"total_status":"VERIFIED","segments":[{"type_id":k,"count":v} for k,v in stage_counts.items()],"distribution_status":"VERIFIED"},
            {"id":"processed","label":"訓練折內補值","unit":"pre_encoding_columns","total":raw_total,"total_status":"VERIFIED","segments":[{"type_id":k,"count":v} for k,v in stage_counts.items()],"distribution_status":"VERIFIED","fit_population":"each_development_training_fold","pipeline_version":"used-car-fold-local-preprocessing-v1"},
            {"id":"encoded","label":"One-Hot 編碼特徵","unit":"encoded_features","total":len(final_names),"total_status":"VERIFIED","segments":[{"type_id":k,"count":v} for k,v in encoded_counts.items()],"distribution_status":"VERIFIED","fit_population":"development_training_only","pipeline_version":"used-car-fold-local-preprocessing-v1"},
        ],
        "treatments":[{"field":field,"action":"exclude_from_model_input","reason":reason} for field,reason in (("ID","identifier"),("vin","vehicle identifier"),("search_price","price proxy/leakage risk"),("est._monthly_pmt","price-derived proxy risk"),("engine","free text"),("features_list","long text and possible personal content"),("title","free text and possible price/contact leakage"),("scrape_timestamp","temporal drift/proxy risk"),("mileage","duplicate representation; canonical odometer retained"),("trans","duplicate transmission representation; cleaned transmission retained"))],
        "split":{"source_labeled_rows":int(len(y)),"training_rows":int(len(X_dev)),"holdout_rows":int(len(X_holdout)),"seed":SEED,"status":"VERIFIED"},
        "lineage_ref":"phases/phase-03/feature-lineage.json"}
    _write_json(output / "phases/phase-03/preparation.json", phase3)
    _write_json(output / "phases/phase-03/feature-lineage.json", phase3_lineage)

    # Persist aggregate model results and private prediction evidence.
    private_oof_path = run_dir / "winner-oof-private.csv"
    private_holdout_path = run_dir / "holdout-private.csv"
    files = {"source_sha256": source_sha, "config_sha256": config_sha, "run_id": RUN_ID,
             "oof_sha256": sha256_file(private_oof_path), "holdout_predictions_sha256": sha256_file(private_holdout_path),
             "final_model_sha256": sha256_file(model_path)}
    summary = {
        "schema_version":"1.0.0", "case_id":CASE_ID, "run_id":RUN_ID, "config_sha256":config_sha,
        "source_sha256":source_sha, "development_rows":len(X_dev), "holdout_rows":len(X_holdout),
        "fold_count":CV_FOLDS, "seed":SEED, "candidates_declared":len(CANDIDATES),
        "candidates_completed":len(completed), "candidates_failed":len(candidate_results)-len(completed),
        "candidate_results":candidate_results, "method_winners":[item["configuration_id"] for item in method_winners],
        "winner_configuration_id":winner["configuration_id"], "winner_method_id":winner["method_id"],
        "winner_params":winner["params"], "winner_mean_fold_metrics":winner["mean_fold_metrics"],
        "winner_sample_sd":winner["sample_sd"], "winner_pooled_oof_metrics":pooled_oof,
        "winner_holdout_metrics":holdout_metrics, "winner_feature_count_mean":winner["feature_count_mean"],
        "winner_selected_feature_folds":winner["selected_features_by_fold"],
        "holdout_selected_feature_count":int(holdout_mask.sum()),
        "final_encoded_feature_count":len(final_names), "final_selected_feature_count":int(final_mask.sum()),
        "local_model_reload_smoke":"PASS", "local_prediction_finite":bool(np.isfinite(smoke[0])),
        "private_artifacts":files, "elapsed_seconds":round(time.monotonic()-started,3),
        "license":{"name":DATASET_LICENSE,"attribution":ATTRIBUTION,"publication_review":"PENDING_COMPETITION_TERMS"},
    }
    _write_json(output / "private/checkpoint.json", summary)
    _write_json(output / "private/run-manifest.json", {
        "run_id":RUN_ID,"case_id":CASE_ID,"source_data_sha256":source_sha,"config_sha256":config_sha,
        "code_sha256":config["code_sha256"],"seed":SEED,"split":{"holdout_fraction":HOLDOUT_FRACTION,"holdout_rows":len(X_holdout),"development_rows":len(X_dev)},
        "cv":{"folds":CV_FOLDS,"shuffle":True,"seed":SEED,"fold_valid_rows":[len(valid) for _,valid in fold_splits]},
        "competition_test_file_accessed":False,"supersedes_run_id":SUPERSEDES_RUN_ID,
        "supersession_reason":"Run 03 fixes the bounded dense-input requirement for mutual-information selection; Run 02 artifacts remain preserved for comparison.",
        "model_artifact_private_path":"private/final-model.joblib",
        "research_parameters":config,"integrity":files,
    })

    # Build aggregate-only cross-validation and evaluation outputs.
    phase4, phase5, phase6 = _build_phase4_phase5_phase6(summary, output, source_sha, config_sha, final_names, final_lineage, winner, candidate_results, method_winners, pooled_oof, holdout_metrics, files)
    _write_json(output / "phases/phase-04/modeling.json", phase4)
    _write_json(output / "phases/phase-05/evaluations.json", phase5)
    _write_json(output / "phases/phase-05/fold-metrics.json", {"schema_version":"1.0.0","case_id":CASE_ID,"run_id":RUN_ID,"configuration_id":winner["configuration_id"],"fold_results":winner["fold_results"]})
    _write_json(output / "phases/phase-05/pooled-oof-metrics.json", {"schema_version":"1.0.0","case_id":CASE_ID,"run_id":RUN_ID,"configuration_id":winner["configuration_id"],"metrics":pooled_oof,"n":len(y_dev)})
    _write_json(output / "phases/phase-06/inference-catalog.json", phase6)

    checkpoint = {**summary,"phase_status":{"phase1":"VERIFIED","phase2":"VERIFIED","phase3":"VERIFIED","phase4":"VERIFIED","phase5":"VERIFIED","phase6":"LOCAL_PRIVATE_VERIFIED"},
                  "package_created":False,"publication_status":"BLOCKED_PENDING_COMPETITION_TERMS_REVIEW","source_csv_modified":False}
    _write_json(output / "checkpoint.json", checkpoint)
    return checkpoint


def excluded_fields() -> set[str]:
    return IDENTIFIERS | LEAKAGE_OR_PROXY | TEXT_FIELDS | TEMPORAL_FIELDS | DUPLICATE_REPRESENTATIONS | {TARGET}


def _build_phase4_phase5_phase6(summary: Mapping[str, Any], output: Path, source_sha: str, config_sha: str,
                                final_names: list[str], final_lineage: list[dict[str, Any]], winner: Mapping[str, Any],
                                candidates: list[dict[str, Any]], method_winners: list[dict[str, Any]],
                                pooled_oof: Mapping[str, float], holdout_metrics: Mapping[str, float],
                                files: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    # Materialize schema-compatible Phase 4 artifacts and simple research charts.
    package_root = output
    config_records = []
    method_labels = {"ols_baseline":"全特徵 OLS 基準","pearson":"Pearson 篩選 → OLS","mutual_information":"互資訊篩選 → OLS","lasso":"Lasso 篩選 → OLS","elastic_net":"Elastic Net 篩選 → OLS","ridge_rfe":"Ridge RFE → OLS"}
    cv_mean_points = []
    curve_points = []
    for candidate in candidates:
        config_id = candidate["configuration_id"]
        base = f"phases/phase-04/configurations/{config_id}"
        status = candidate["status"]
        cv_ref, selected_ref, task_ref, metadata_ref = [f"{base}/{name}" for name in ("cv-metrics.json","selected-features.json","fold-tasks.json","metadata.json")]
        if status == "VERIFIED":
            _write_json(package_root / cv_ref, {"schema_version":"1.0.0","case_id":CASE_ID,"configuration_id":config_id,"run_id":RUN_ID,"mean_fold_metrics":candidate["mean_fold_metrics"],"sample_sd":candidate["sample_sd"],"fold_results":candidate["fold_results"]})
            _write_json(package_root / selected_ref, {"schema_version":"1.0.0","case_id":CASE_ID,"configuration_id":config_id,"run_id":RUN_ID,"selection_unit":"encoded_feature","summary":"各折僅以該折訓練資料擬合前處理與特徵選擇。","folds":candidate["selected_features_by_fold"]})
        else:
            _write_json(package_root / cv_ref, {"schema_version":"1.0.0","case_id":CASE_ID,"configuration_id":config_id,"run_id":RUN_ID,"status":"ERROR","reason":candidate.get("error","candidate failed")})
            _write_json(package_root / selected_ref, {"schema_version":"1.0.0","case_id":CASE_ID,"configuration_id":config_id,"run_id":RUN_ID,"status":"ERROR","folds":[]})
        _write_json(package_root / task_ref, {"schema_version":"1.0.0","case_id":CASE_ID,"configuration_id":config_id,"run_id":RUN_ID,"folds":[{"fold":item["fold"],"status":item["status"],"n_train":item["n_train"],"n_validation":item["n_validation"]} for item in candidate.get("fold_results",[])]})
        _write_json(package_root / metadata_ref, {"schema_version":"1.0.0","case_id":CASE_ID,"configuration_id":config_id,"run_id":RUN_ID,"source_data_sha256":source_sha,"config_sha256":config_sha,"method_id":candidate["method_id"],"params":candidate["params"],"status":status})
        config_records.append({"configuration_id":config_id,"execution_run_id":RUN_ID,"method_id":candidate["method_id"],"track_id":"fold_local_selected_features_to_primary_ols","params":candidate["params"],"protocol_id":"used-car-dev-80-20-seed42-3fold-v1","metadata_ref":metadata_ref,"fold_tasks_ref":task_ref,"cv_metrics_ref":cv_ref,"selected_features_ref":selected_ref,"status":status})
        if status == "VERIFIED":
            cv_mean_points.append({"configuration_id":config_id,"method_id":candidate["method_id"],"status":"VERIFIED","feature_count_mean":candidate["feature_count_mean"],"rmse_mean_fold":candidate["mean_fold_metrics"]["rmse"],"mae_mean_fold":candidate["mean_fold_metrics"]["mae"],"r2_mean_fold":candidate["mean_fold_metrics"]["r2"],"method_winner":candidate["configuration_id"] in {item["configuration_id"] for item in method_winners}})
            curve_points.append(cv_mean_points[-1])
    method_comparison_ref = "phases/phase-04/charts/method-comparison.json"
    feature_curve_ref = "phases/phase-04/charts/feature-count-vs-cv-rmse.json"
    _write_json(package_root / method_comparison_ref,{"schema_version":"1.0.0","case_id":CASE_ID,"run_id":RUN_ID,"points":cv_mean_points})
    _write_json(package_root / feature_curve_ref,{"schema_version":"1.0.0","case_id":CASE_ID,"run_id":RUN_ID,"points":curve_points})
    method_ids = list(dict.fromkeys(item["method_id"] for item in CANDIDATES))
    methods = [{"method_id":mid,"label":method_labels[mid],"parameters":[]} for mid in method_ids]
    phase4 = {"schema_version":"1.1.0","case_id":CASE_ID,"status":"VERIFIED","cv":{"training_rows":summary["development_rows"],"fold_count":CV_FOLDS,"protocol_id":"used-car-dev-80-20-seed42-3fold-v1","status":"VERIFIED"},
              "methods":methods,"execution_runs":[{"execution_run_id":RUN_ID,"source_manifest_sha256":sha256_bytes(_json_bytes(files)),"status":"VERIFIED"}],"configurations":config_records,
              "default_configuration_id":winner["configuration_id"],"charts":[{"chart_id":"method-comparison","points_ref":method_comparison_ref,"status":"VERIFIED"},{"chart_id":"feature-count-vs-cv-rmse","points_ref":feature_curve_ref,"status":"VERIFIED"}],
              "limitations":["有限候選集；最佳值僅代表已執行候選。","所有補值、編碼及選擇器皆於各訓練折內擬合。","Kaggle competition test_data_v2.csv 未讀取。"]}
    pooled_ref = "phases/phase-05/pooled-oof-metrics.json"
    fold_ref = "phases/phase-05/fold-metrics.json"
    oof_sha = files["oof_sha256"]
    mean_id = f"{RUN_ID}.{winner['configuration_id']}.cv-mean"
    pooled_id = f"{RUN_ID}.{winner['configuration_id']}.pooled-oof"
    holdout_id = f"{RUN_ID}.{winner['configuration_id']}.internal-holdout"
    def metric_block(values: Mapping[str, float], ref: str) -> dict[str, Any]:
        return {key:{"value":float(values[key]),"status":"VERIFIED","reason_code":None,"evidence_ref":ref} for key in ("mae","rmse","r2")}
    mean_metrics = winner["mean_fold_metrics"]
    fold_summary={"fold_count":CV_FOLDS,"aggregation":"fold_mean","ddof":1,"sample_sd":winner["sample_sd"],"fold_values_ref":fold_ref}
    unavailable_int={"int_f":{"status":"UNAVAILABLE","reason_code":"NOT_COMPUTED","method":None,"assumptions_ref":None},"int_s":{"status":"UNAVAILABLE","reason_code":"NOT_COMPUTED","interval_type":None,"method":None,"nominal_level":None,"population":None,"asset_ref":None,"coverage_evidence":None,"review_url":None}}
    base_eval={"execution_run_id":RUN_ID,"configuration_id":winner["configuration_id"],"final_fit_id":None,"model_id":f"{CASE_ID}-{winner['configuration_id']}","model_version":source_sha[:12],"target":{"column":TARGET,"unit":"USD"},"evidence":{"source_artifact_sha256":oof_sha,"source_ref":"private OOF CSV SHA retained locally; row records are not in the public package","protocol_version":"used-car-dev-80-20-seed42-3fold-v1","review_url":None},"asset_status":"VERIFIED","review_status":"PENDING","limitations":["資料為刊登價，不是成交價。","Development 評估不代表外部市場泛化。","逐筆 OOF 與 Holdout 預測未納入公開 Package。","Package 資料集授權與競賽條款審查仍待完成。"],"linked_evaluation_ids":[mean_id,pooled_id]}
    evaluations=[{**base_eval,"evaluation_id":mean_id,"evaluation_population":"development_oof","prediction_origin":"new_core_fold_local_oof","metric_source":"cv_fold_mean","n":summary["development_rows"],"metrics":metric_block(mean_metrics,fold_ref),"fold_summary":fold_summary,"figures":[],"interval":unavailable_int},
                 {**base_eval,"evaluation_id":pooled_id,"evaluation_population":"development_oof","prediction_origin":"new_core_fold_local_oof","metric_source":"pooled_oof","n":summary["development_rows"],"metrics":metric_block(pooled_oof,pooled_ref),"fold_summary":{"fold_count":CV_FOLDS,"aggregation":"pooled_predictions","ddof":None,"sample_sd":None,"fold_values_ref":fold_ref},"figures":[],"interval":unavailable_int},
                 {**base_eval,"evaluation_id":holdout_id,"evaluation_population":"holdout","prediction_origin":"internal_labeled_holdout_once_after_cv_selection","metric_source":"holdout_aggregate","n":summary["holdout_rows"],"metrics":metric_block(holdout_metrics,"phases/phase-05/holdout-aggregate.json"),"fold_summary":None,"figures":[],"interval":unavailable_int,"linked_evaluation_ids":[holdout_id]}]
    phase5={"schema_version":"1.0.0","case_id":CASE_ID,"release_id":None,"generated_at":None,"status":"VERIFIED","reason_code":None,"publication_review":"PENDING","default_evaluation_id":mean_id,"evaluations":evaluations,"ui":{"default_metric_source":"cv_fold_mean","default_diagnostic":"FIG-P5-01","show_holdout_separately":True}}
    # Save aggregate holdout evidence separate from Development OOF.
    _write_json(package_root / "phases/phase-05/holdout-aggregate.json",{"schema_version":"1.0.0","case_id":CASE_ID,"run_id":RUN_ID,"configuration_id":winner["configuration_id"],"population":"internal_holdout","n":summary["holdout_rows"],"metrics":dict(holdout_metrics),"competition_test_data_used":False})
    # Real final-fit model is kept private; public catalog explicitly says no
    # remote inference service is provided.
    phase6={"schema_version":"1.0.0","case_id":CASE_ID,"status":"UNAVAILABLE","models":[],"readiness":{"predict_enabled":False,"reason_code":"NO_PUBLIC_INFERENCE_SERVICE","message":"本機 final-fit 模型已重載並完成推論 smoke；模型檔保留於私有本機路徑，網站未提供線上推論服務。"},"local_private_verification":{"status":"LOCAL_PRIVATE_VERIFIED","run_id":RUN_ID,"configuration_id":winner["configuration_id"],"model_sha256":files["final_model_sha256"],"row_prediction_included":False}}
    return phase4, phase5, phase6
