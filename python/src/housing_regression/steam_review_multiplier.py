"""Reproducible, aggregate-first Steam Review Multiplier homework research."""

from __future__ import annotations

import ast
import csv
import json
import math
import re
import hashlib
import platform
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_selection import RFE, SelectKBest, f_regression
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Lasso, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor


CASE_ID = "steam-review-multiplier"
DATASET_FILE = "games_march2025_cleaned.csv"
MAY_FILE = "games_may2024_cleaned.csv"
SEED = 42
REVIEW_MINIMUM = 20
HOLDOUT_FRACTION = 0.20
CV_FOLDS = 3
TARGET_DESCRIPTION = "log1p((estimated_owners_low + estimated_owners_high) / 2 / review_count)"
RAW_CANDIDATE_FIELDS = [
    "genres", "categories", "tags", "price", "required_age", "dlc_count",
    "achievements", "release_date", "windows", "mac", "linux",
    "supported_languages", "full_audio_languages", "discount", "developers",
    "publishers", "screenshots", "movies", "website",
]
MODEL_INPUT_FIELDS = [
    "genres", "price", "required_age", "dlc_count", "achievements", "release_year",
    "windows", "mac", "linux", "genre_count", "category_count", "tag_count",
    "supported_language_count", "full_audio_language_count", "has_english",
    "has_traditional_chinese", "discount", "developer_count", "publisher_count",
    "screenshot_count", "movie_count", "has_website",
]
SELECTED_SOURCE_COLUMNS = [
    "appid", "name", "release_date", "required_age", "price", "dlc_count",
    "windows", "mac", "linux", "metacritic_score", "achievements", "supported_languages",
    "full_audio_languages", "categories", "genres", "positive", "negative",
    "estimated_owners", "discount", "tags", "num_reviews_total", "num_reviews_recent",
    "developers", "publishers", "screenshots", "movies", "website",
]


def parse_number(value: Any) -> float:
    if value is None:
        return math.nan
    text = str(value).strip().replace(",", "")
    if text in {"", "None", "nan", "-", "N/A"}:
        return math.nan
    try:
        number = float(text)
        return number if math.isfinite(number) else math.nan
    except ValueError:
        return math.nan


def parse_list(value: Any) -> list[str]:
    if value is None:
        return []
    text = str(value).strip()
    if not text or text == "[]":
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, dict):
            return [str(k) for k in parsed]
        if isinstance(parsed, (list, tuple, set)):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except (ValueError, SyntaxError):
        pass
    return [part.strip() for part in re.split(r"[,;|]", text.strip("[]")) if part.strip()]


def parse_owners(value: Any) -> tuple[float, float] | None:
    """Return SteamSpy's inclusive lower/upper interval, never a point observation."""
    text = str(value or "").strip().replace(",", "")
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)\s*", text)
    if not match:
        return None
    low, high = map(float, match.groups())
    if not (0 <= low <= high):
        return None
    return low, high


def review_count(row: dict[str, Any]) -> tuple[float, str]:
    total = parse_number(row.get("num_reviews_total"))
    pos, neg = parse_number(row.get("positive")), parse_number(row.get("negative"))
    sum_votes = pos + neg if math.isfinite(pos) and math.isfinite(neg) else math.nan
    if math.isfinite(total) and total >= 0:
        return total, "num_reviews_total"
    if math.isfinite(sum_votes) and sum_votes >= 0:
        return sum_votes, "positive_plus_negative"
    return math.nan, "unavailable"


def _parse_bool(value: Any) -> float:
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return 1.0
    if text in {"false", "0", "no"}:
        return 0.0
    return math.nan


def engineer_row(row: dict[str, Any]) -> dict[str, Any]:
    genres = parse_list(row.get("genres"))
    categories = parse_list(row.get("categories"))
    tags = parse_list(row.get("tags"))
    languages = parse_list(row.get("supported_languages"))
    audio = parse_list(row.get("full_audio_languages"))
    def missing_list(key: str) -> bool:
        return row.get(key) is None or not str(row.get(key)).strip() or str(row.get(key)).strip().lower() in {"none", "nan", "null"}
    date_text = str(row.get("release_date", "")).strip()
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", date_text)
    language_norm = {x.casefold() for x in languages}
    return {
        "genres": genres,
        "price": parse_number(row.get("price")),
        "required_age": parse_number(row.get("required_age")),
        "dlc_count": parse_number(row.get("dlc_count")),
        "achievements": parse_number(row.get("achievements")),
        "release_year": float(year_match.group(1)) if year_match else math.nan,
        "windows": _parse_bool(row.get("windows")),
        "mac": _parse_bool(row.get("mac")),
        "linux": _parse_bool(row.get("linux")),
        "genre_count": math.nan if missing_list("genres") else float(len(genres)),
        "category_count": math.nan if missing_list("categories") else float(len(categories)),
        "tag_count": math.nan if missing_list("tags") else float(len(tags)),
        "supported_language_count": math.nan if missing_list("supported_languages") else float(len(languages)),
        "full_audio_language_count": math.nan if missing_list("full_audio_languages") else float(len(audio)),
        "has_english": math.nan if missing_list("supported_languages") else float("english" in language_norm),
        "has_traditional_chinese": math.nan if missing_list("supported_languages") else float("traditional chinese" in language_norm),
        "discount": parse_number(row.get("discount")),
        # Counts retain low-cardinality metadata without exposing high-cardinality names/URLs.
        "developer_count": math.nan if missing_list("developers") else float(len(parse_list(row.get("developers")))),
        "publisher_count": math.nan if missing_list("publishers") else float(len(parse_list(row.get("publishers")))),
        "screenshot_count": math.nan if missing_list("screenshots") else float(len(parse_list(row.get("screenshots")))),
        "movie_count": math.nan if missing_list("movies") else float(len(parse_list(row.get("movies")))),
        # Missing website metadata is represented as no listed website in this snapshot.
        "has_website": float(bool(str(row.get("website") or "").strip())),
    }


def load_research_frame(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Stream the CSV once; keep only model fields and aggregate audit evidence."""
    rows: list[dict[str, Any]] = []
    missing = Counter()
    duplicate_ids = 0
    appids: set[str] = set()
    review_sources = Counter()
    review_mismatch = 0
    review_comparable = 0
    review_abs_diffs: list[float] = []
    source_rows = 0
    invalid_owners = 0
    valid_owners = 0
    zero_review = 0
    low_review = 0
    free_count = 0
    paid_count = 0
    added_feature_values: dict[str, list[float]] = {name: [] for name in (
        "developer_count", "publisher_count", "screenshot_count", "movie_count", "has_website")}
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        original_fields = list(reader.fieldnames or [])
        appid_field = "appid" if "appid" in original_fields else "AppID"
        for source_row in reader:
            source_rows += 1
            appid = str(source_row.get(appid_field, "")).strip()
            if appid in appids:
                duplicate_ids += 1
            appids.add(appid)
            for name in original_fields:
                value = source_row.get(name)
                if value is None or not value.strip():
                    missing[name] += 1
            total = parse_number(source_row.get("num_reviews_total"))
            pos, neg = parse_number(source_row.get("positive")), parse_number(source_row.get("negative"))
            vote_sum = pos + neg if math.isfinite(pos) and math.isfinite(neg) else math.nan
            if math.isfinite(total) and math.isfinite(vote_sum):
                review_comparable += 1
                review_abs_diffs.append(abs(total - vote_sum))
                if not math.isclose(total, vote_sum, rel_tol=0.0, abs_tol=0.0):
                    review_mismatch += 1
            count, source = review_count(source_row)
            review_sources[source] += 1
            if math.isfinite(count):
                zero_review += count == 0
                low_review += 0 < count < REVIEW_MINIMUM
            owner_interval = parse_owners(source_row.get("estimated_owners"))
            if owner_interval is None:
                invalid_owners += 1
            else:
                valid_owners += 1
            price = parse_number(source_row.get("price"))
            if math.isfinite(price):
                free_count += price == 0
                paid_count += price > 0
            features = engineer_row(source_row)
            for name, values in added_feature_values.items():
                value = features[name]
                if math.isfinite(value):
                    values.append(float(value))
            if owner_interval is not None and math.isfinite(count) and count > 0:
                low_owner, high_owner = owner_interval
                features.update({
                    "review_count": count,
                    "owners_low": low_owner,
                    "owners_high": high_owner,
                    "owners_midpoint_proxy": (low_owner + high_owner) / 2,
                    "k_low": low_owner / count,
                    "k_high": high_owner / count,
                    "k_midpoint_proxy": ((low_owner + high_owner) / 2) / count,
                    "is_free": int(price == 0) if math.isfinite(price) else 0,
                    "appid": appid,
                })
                rows.append(features)
    frame = pd.DataFrame(rows)
    audit = {
        "source_file": path.name,
        "source_bytes": path.stat().st_size,
        "source_fields": original_fields,
        "rows": source_rows,
        "model_rows_with_valid_owner_and_positive_reviews": int(len(frame)),
        "unique_appids": len(appids),
        "duplicate_appids": duplicate_ids,
        "missing_counts": dict(missing),
        "review_count_policy": "num_reviews_total when parseable; positive + negative fallback only when total is missing",
        "review_source_counts": dict(review_sources),
        "review_total_vs_positive_negative_comparable_rows": review_comparable,
        "review_total_disagreement_rows": review_mismatch,
        "review_total_disagreement_rate": review_mismatch / review_comparable if review_comparable else None,
        "review_abs_difference_quantiles": {str(q): float(np.quantile(review_abs_diffs, q)) for q in (.5,.9,.99)} if review_abs_diffs else {},
        "valid_owner_interval_rows": valid_owners,
        "invalid_owner_interval_rows": invalid_owners,
        "zero_review_rows": zero_review,
        "low_review_rows_1_to_19": low_review,
        "free_games": free_count,
        "paid_games": paid_count,
        "analysis_review_minimum": REVIEW_MINIMUM,
        "analysis_rows_removed_for_target_or_review_policy": None,
        "added_feature_quality": {name: {
            "valid_rows": len(values), "missing_rows": source_rows - len(values),
            "mean": float(np.mean(values)) if values else None,
            "median": float(np.median(values)) if values else None,
            "q95": float(np.quantile(values, .95)) if values else None,
            "unique_value_count": len(set(values)),
        } for name, values in added_feature_values.items()},
    }
    audit["analysis_rows_removed_for_target_or_review_policy"] = audit["rows"] - len(frame)
    return frame, audit


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def scan_inventory(path: Path) -> tuple[dict[str, Any], set[str]]:
    count = 0
    appids: set[str] = set()
    duplicates = 0
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        id_field = "appid" if "appid" in fields else "AppID"
        for row in reader:
            count += 1
            value = str(row.get(id_field, "")).strip()
            if value in appids:
                duplicates += 1
            appids.add(value)
    return {"file": path.name, "rows": count, "columns": len(fields), "fields": fields,
            "appid_field": id_field, "unique_appids": len(appids), "duplicate_appids": duplicates,
            "bytes": path.stat().st_size}, appids


class SteamFeatureEncoder(BaseEstimator, TransformerMixin):
    """Train-fold-fitted top-genre indicator expansion plus numeric inputs."""
    base_columns = [c for c in MODEL_INPUT_FIELDS if c != "genres"]

    def __init__(self, max_genres: int = 12):
        self.max_genres = max_genres

    def fit(self, X: pd.DataFrame, y=None):
        counts = Counter(g for values in X["genres"] for g in (values if isinstance(values, list) else []))
        self.genre_vocabulary_ = [name for name, _ in counts.most_common(self.max_genres)]
        return self

    def transform(self, X: pd.DataFrame):
        result = np.empty((len(X), len(self.base_columns) + len(self.genre_vocabulary_)), dtype=float)
        for j, column in enumerate(self.base_columns):
            result[:, j] = pd.to_numeric(X[column], errors="coerce").to_numpy(dtype=float)
        offset = len(self.base_columns)
        vocabulary = self.genre_vocabulary_
        for i, values in enumerate(X["genres"]):
            genres = set(values if isinstance(values, list) else [])
            for j, genre in enumerate(vocabulary):
                result[i, offset + j] = float(genre in genres)
        return result

    def get_feature_names_out(self, input_features=None):
        return np.asarray(self.base_columns + [f"genre::{g}" for g in self.genre_vocabulary_], dtype=object)


def make_pipeline(model_id: str, selector: str = "all") -> Pipeline:
    model = {
        "ols": LinearRegression(),
        "ridge": Ridge(alpha=10.0),
        "lasso": Lasso(alpha=0.001, max_iter=5000),
        "random_forest": RandomForestRegressor(n_estimators=100, min_samples_leaf=5,
                                                max_features=0.8, random_state=SEED, n_jobs=-1),
    }[model_id]
    steps: list[tuple[str, Any]] = [
        ("encode", SteamFeatureEncoder(max_genres=12)),
        ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("scale", StandardScaler()),
    ]
    if selector == "select_k_14":
        steps.append(("select", SelectKBest(score_func=f_regression, k=14)))
    elif selector == "lasso_rfe_14":
        # Sequential feature selection is fit only on the current training fold.
        steps.append(("select", RFE(estimator=Ridge(alpha=10.0), n_features_to_select=14, step=0.5)))
    steps.append(("model", model))
    return Pipeline(steps)


def log_to_k(values: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, np.expm1(np.asarray(values, dtype=float)))


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {"mae": float(mean_absolute_error(y_true, y_pred)),
            "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
            "r2": float(r2_score(y_true, y_pred))}


def _metric_row(name: str, y_true: np.ndarray, pred_k: np.ndarray, review: np.ndarray,
                owners_low: np.ndarray, owners_high: np.ndarray) -> dict[str, Any]:
    estimated = review * pred_k
    return {"model": name, **metrics(y_true, pred_k),
            "owners_interval_compatibility_rate": float(np.mean((estimated >= owners_low) & (estimated <= owners_high))),
            "median_estimated_owners": float(np.median(estimated))}


def genre_training_baseline(train: pd.DataFrame, holdout: pd.DataFrame) -> np.ndarray:
    sums: dict[str, list[float]] = {}
    for _, row in train.iterrows():
        for genre in row["genres"]:
            sums.setdefault(genre, []).append(float(row["k_midpoint_proxy"]))
    global_median = float(train["k_midpoint_proxy"].median())
    medians = {g: float(np.median(values)) for g, values in sums.items() if values}
    result = []
    for genres in holdout["genres"]:
        values = [medians[g] for g in genres if g in medians]
        result.append(float(np.mean(values)) if values else global_median)
    return np.asarray(result)


def profile(data_dir: Path, output_dir: Path, repo_root: Path) -> dict[str, Any]:
    inventories, id_sets = [], {}
    for filename in ["games_may2024_full.csv", MAY_FILE, "games_march2025_full.csv", DATASET_FILE]:
        info, values = scan_inventory(data_dir / filename)
        inventories.append(info)
        id_sets[filename] = values
    alignment = {
        "may2024_full_vs_cleaned_intersection": len(id_sets["games_may2024_full.csv"] & id_sets[MAY_FILE]),
        "may2024_full_only": len(id_sets["games_may2024_full.csv"] - id_sets[MAY_FILE]),
        "may2024_cleaned_only": len(id_sets[MAY_FILE] - id_sets["games_may2024_full.csv"]),
        "march2025_full_vs_cleaned_intersection": len(id_sets["games_march2025_full.csv"] & id_sets[DATASET_FILE]),
        "march2025_full_only": len(id_sets["games_march2025_full.csv"] - id_sets[DATASET_FILE]),
        "march2025_cleaned_only": len(id_sets[DATASET_FILE] - id_sets["games_march2025_full.csv"]),
        "cleaned_cross_snapshot_intersection": len(id_sets[MAY_FILE] & id_sets[DATASET_FILE]),
        "may_cleaned_only": len(id_sets[MAY_FILE] - id_sets[DATASET_FILE]),
        "march_cleaned_only": len(id_sets[DATASET_FILE] - id_sets[MAY_FILE]),
    }
    frame, audit = load_research_frame(data_dir / DATASET_FILE)
    may_frame, may_audit = load_research_frame(data_dir / MAY_FILE)
    valid = frame.loc[(frame["review_count"] >= REVIEW_MINIMUM) & (frame["owners_high"] > 0)].copy()
    audit["rows_removed_below_review_minimum"] = int((frame.review_count < REVIEW_MINIMUM).sum())
    audit["rows_removed_zero_owner_upper_bound"] = int((frame.owners_high == 0).sum())
    audit["analysis_rows_after_review_minimum"] = int(len(valid))
    audit["zero_owner_interval_rows"] = int((frame.owners_high == 0).sum())
    may_eligible = may_frame.loc[(may_frame.review_count >= REVIEW_MINIMUM) & (may_frame.owners_high > 0)]
    common = frame[["appid", "k_midpoint_proxy", "review_count"]].merge(
        may_eligible[["appid", "k_midpoint_proxy", "review_count"]], on="appid", suffixes=("_2025", "_2024"), how="inner")
    common = common.loc[(common.review_count_2025 >= REVIEW_MINIMUM) & (common.k_midpoint_proxy_2025 > 0) & (common.k_midpoint_proxy_2024 > 0)]
    audit["cross_snapshot_overlap"] = {
        "cleaned_shared_appids": alignment["cleaned_cross_snapshot_intersection"],
        "both_snapshots_valid_k_n": int(len(common)),
        "may2024_median_k_proxy": float(common.k_midpoint_proxy_2024.median()) if len(common) else None,
        "march2025_median_k_proxy": float(common.k_midpoint_proxy_2025.median()) if len(common) else None,
        "median_absolute_log_k_change": float(np.median(np.abs(np.log(common.k_midpoint_proxy_2025) - np.log(common.k_midpoint_proxy_2024)))) if len(common) else None,
        "log_k_spearman_rank_correlation": float(common[["k_midpoint_proxy_2024", "k_midpoint_proxy_2025"]].corr(method="spearman").iloc[0,1]) if len(common) > 2 else None,
        "interpretation": "Descriptive matched-AppID snapshot comparison only; no temporal generalization claim.",
    }
    audit["may2024_review_total_vs_vote_sum_disagreement_rate"] = may_audit["review_total_disagreement_rate"]
    audit["k_midpoint_proxy_quantiles"] = valid["k_midpoint_proxy"].quantile([.1,.25,.5,.75,.9,.95,.99]).to_dict()
    audit["k_interval_contains_20_30_50_rates"] = {
        str(k): float(np.mean((valid["k_low"] <= k) & (valid["k_high"] >= k))) for k in (20, 30, 50)
    }
    audit["price_groups"] = {
        "free": int((valid.price == 0).sum()),
        "paid": int((valid.price > 0).sum()),
        "price_missing": int(valid.price.isna().sum()),
    }
    genre_rows = []
    for genre in sorted({g for values in valid.genres for g in values}):
        subset = valid.loc[valid.genres.map(lambda values: genre in values), "k_midpoint_proxy"]
        if len(subset):
            genre_rows.append({"genre": genre, "n": len(subset), "median_k_proxy": float(subset.median()),
                               "mean_k_proxy": float(subset.mean()), "q25": float(subset.quantile(.25)),
                               "q75": float(subset.quantile(.75))})
    genre_rows.sort(key=lambda x: (-x["n"], x["genre"]))
    audit["genre_summary"] = genre_rows
    audit["genre_count_distribution"] = {str(k): int(v) for k, v in Counter(valid["genres"].map(len)).items()}
    year_bins = (valid.release_year.dropna().astype(int) // 5 * 5).value_counts().sort_index()
    audit["release_year_5y_counts"] = {f"{y}-{y+4}": int(v) for y, v in year_bins.items()}
    audit["candidate_raw_feature_fields"] = RAW_CANDIDATE_FIELDS
    audit["candidate_raw_feature_count"] = len(RAW_CANDIDATE_FIELDS)
    audit["platform_support_counts"] = {x: int((valid[x] == 1).sum()) for x in ["windows", "mac", "linux"]}
    audit["language_support_medians"] = {
        "supported_language_count": float(valid.supported_language_count.median()),
        "full_audio_language_count": float(valid.full_audio_language_count.median()),
        "traditional_chinese_supported_rows": int((valid.has_traditional_chinese == 1).sum()),
        "english_supported_rows": int((valid.has_english == 1).sum()),
    }
    audit["price_k_summary"] = {
        label: {"n": int(len(part)), "median_k_proxy": float(part.k_midpoint_proxy.median())}
        for label, part in [("free", valid.loc[valid.price == 0]), ("paid", valid.loc[valid.price > 0])]
    }
    audit["positive_target_definition"] = TARGET_DESCRIPTION
    audit["ownership_target_note"] = "SteamSpy estimated_owners interval midpoint is a proxy, not observed ownership or sales."
    audit["inventory"] = inventories
    audit["appid_alignment"] = alignment
    audit["software"] = {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
                          "scikit_learn": sklearn.__version__, "matplotlib": matplotlib.__version__}
    audit["data_sha256"] = {name: _sha_file(data_dir / name) for name in [MAY_FILE, DATASET_FILE]}
    _plot_eda(valid, audit, output_dir / "phase-02" / "figures")
    write_json(output_dir / "phase-02" / "data-understanding.json", audit)
    return audit


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _plot_eda(frame: pd.DataFrame, audit: dict[str, Any], figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")
    def save(fig, name: str):
        fig.tight_layout()
        fig.savefig(figure_dir / f"{name}.png", dpi=140)
        fig.savefig(figure_dir / f"{name}.svg")
        plt.close(fig)
    inventory = audit.get("inventory", [])
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar([Path(x["file"]).stem.replace("games_", "") for x in inventory], [x["rows"] for x in inventory], color="#4f8292")
    ax.set_title("Steam dataset snapshots · row counts")
    ax.set_ylabel("Games"); ax.tick_params(axis="x", rotation=20); save(fig, "dataset-overview")

    missing = audit["missing_counts"]
    top = sorted(missing.items(), key=lambda x: x[1], reverse=True)[:18]
    fig, ax = plt.subplots(figsize=(9, 5.4)); ax.barh([x[0] for x in top][::-1], [100*x[1]/audit["rows"] for x in top][::-1], color="#bd8759")
    ax.set_title("2025 cleaned · highest missingness fields"); ax.set_xlabel("Missing rows (%)"); save(fig, "missingness-overview")

    for column, title, filename, xlabel in [
        ("review_count", "Review count distribution (log scale)", "review-count-distribution.png", "num_reviews_total"),
        ("owners_midpoint_proxy", "SteamSpy ownership midpoint proxy (log scale)", "owners-distribution.png", "Estimated owners interval midpoint proxy"),
        ("k_midpoint_proxy", "Review Multiplier K midpoint proxy (log scale)", "k-distribution.png", "K interval midpoint proxy"),
    ]:
        fig, ax = plt.subplots(figsize=(8.5, 4.8)); vals = frame[column].clip(lower=0)
        ax.hist(vals, bins=np.logspace(0, np.log10(max(10, vals.quantile(.995))), 45), color="#4f8292", alpha=.9)
        ax.set_xscale("log"); ax.set_title(title); ax.set_xlabel(xlabel); ax.set_ylabel("Games"); save(fig, filename.removesuffix(".png"))

    genres = audit["genre_summary"][:18]
    fig, ax = plt.subplots(figsize=(9, 6)); ax.barh([x["genre"] for x in genres][::-1], [x["n"] for x in genres][::-1], color="#4f8292")
    ax.set_title("Genre presence · multi-label games counted in each genre"); ax.set_xlabel("Games"); save(fig, "genre-distribution")

    genre_data = [(x["genre"], frame.loc[frame.genres.map(lambda values: x["genre"] in values), "k_midpoint_proxy"].to_numpy()) for x in genres[:12]]
    fig, ax = plt.subplots(figsize=(10, 5.6)); ax.boxplot([np.clip(v, 0, np.quantile(frame.k_midpoint_proxy, .99)) for _, v in genre_data], tick_labels=[g for g, _ in genre_data], showfliers=False)
    ax.set_yscale("log"); ax.set_title("K proxy by most common genres · upper tail clipped for display only"); ax.set_ylabel("K midpoint proxy (log scale)"); ax.tick_params(axis="x", rotation=45); save(fig, "k-by-genre")

    paid = frame.loc[frame.price > 0].copy()
    paid["price_bin"] = pd.qcut(paid.price, q=8, duplicates="drop")
    price_summary = paid.groupby("price_bin", observed=True).k_midpoint_proxy.median()
    fig, ax = plt.subplots(figsize=(8.5, 4.8)); ax.plot(range(len(price_summary)), price_summary.values, marker="o", color="#4f8292")
    ax.set_xticks(range(len(price_summary)), [str(x) for x in price_summary.index], rotation=35, ha="right"); ax.set_yscale("log")
    ax.set_title("K proxy by paid-game price quantile"); ax.set_ylabel("Median K midpoint proxy"); save(fig, "k-vs-price")

    rates = [float(np.mean((frame.k_low <= k) & (frame.k_high >= k))) for k in (20, 30, 50)]
    fig, ax = plt.subplots(figsize=(6.5, 4.2)); ax.bar(["K=20", "K=30", "K=50"], rates, color=["#78a4a2", "#d39854", "#798cab"])
    ax.set_ylim(0, 1); ax.set_ylabel("Share of observed owners intervals containing K"); ax.set_title("Fixed multiplier interval compatibility"); save(fig, "fixed-k-interval-compatibility")


def run_models(data_dir: Path, output_dir: Path, repo_root: Path) -> dict[str, Any]:
    from joblib import dump

    frame, audit = load_research_frame(data_dir / DATASET_FILE)
    frame = frame.loc[(frame.review_count >= REVIEW_MINIMUM) & (frame.owners_high > 0)].reset_index(drop=True)
    X = frame[MODEL_INPUT_FIELDS]
    y = np.log1p(frame.k_midpoint_proxy.to_numpy(dtype=float))
    indices = np.arange(len(frame))
    train_idx, holdout_idx = train_test_split(indices, test_size=HOLDOUT_FRACTION, random_state=SEED)
    if set(frame.iloc[train_idx].appid) & set(frame.iloc[holdout_idx].appid):
        raise RuntimeError("AppID leakage across train and holdout")
    X_train, X_hold = X.iloc[train_idx], X.iloc[holdout_idx]
    y_train, y_hold = y[train_idx], y[holdout_idx]
    y_hold_k = frame.k_midpoint_proxy.to_numpy(dtype=float)[holdout_idx]
    review_hold = frame.review_count.to_numpy(dtype=float)[holdout_idx]
    low_hold = frame.owners_low.to_numpy(dtype=float)[holdout_idx]
    high_hold = frame.owners_high.to_numpy(dtype=float)[holdout_idx]
    cv = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED)
    configurations = [
        ("ols", "all"), ("ridge", "all"), ("lasso", "all"), ("random_forest", "all"),
        ("ridge", "select_k_14"), ("ridge", "lasso_rfe_14"),
    ]
    cv_results = []
    estimator_parameters = {
        "ols": {"fit_intercept": True},
        "ridge": {"alpha": 10.0},
        "lasso": {"alpha": 0.001, "max_iter": 5000},
        "random_forest": {"n_estimators": 100, "min_samples_leaf": 5, "max_features": 0.8, "random_state": SEED, "n_jobs": -1},
    }
    for model_id, selector in configurations:
        estimator = make_pipeline(model_id, selector)
        scores = cross_val_score(estimator, X_train, y_train, cv=cv,
                                 scoring="neg_root_mean_squared_error", n_jobs=1)
        cv_results.append({"configuration_id": f"{model_id}-{selector}", "model_id": model_id,
                           "feature_selection": selector, "fold_count": CV_FOLDS,
                           "estimator_parameters": estimator_parameters[model_id],
                           "selector_parameters": ({"k": 14} if selector == "select_k_14" else
                                                   {"estimator": "Ridge(alpha=10.0)", "n_features_to_select": 14, "step": 0.5} if selector == "lasso_rfe_14" else {}),
                           "fold_log_rmse": (-scores).tolist(), "mean_log_rmse": float((-scores).mean()),
                           "sd_log_rmse": float((-scores).std(ddof=1))})
    selected = min(cv_results, key=lambda x: (x["mean_log_rmse"], x["configuration_id"]))
    model = make_pipeline(selected["model_id"], selected["feature_selection"])
    model.fit(X_train, y_train)
    pred_hold = log_to_k(model.predict(X_hold))
    genre_pred = genre_training_baseline(frame.iloc[train_idx], frame.iloc[holdout_idx])
    baseline_rows = []
    for k in (20.0, 30.0, 50.0):
        baseline_rows.append(_metric_row(f"fixed-k-{int(k)}", y_hold_k, np.full_like(y_hold_k, k), review_hold, low_hold, high_hold))
    baseline_rows.append(_metric_row("genre-training-median", y_hold_k, genre_pred, review_hold, low_hold, high_hold))
    baseline_rows.append(_metric_row("machine-learning", y_hold_k, pred_hold, review_hold, low_hold, high_hold))

    holdout_genre_rows = []
    hold = frame.iloc[holdout_idx].copy()
    hold["predicted_k"] = pred_hold
    for genre, count in Counter(g for values in hold.genres for g in values).most_common():
        subset = hold.loc[hold.genres.map(lambda values: genre in values)]
        if len(subset) >= 30:
            holdout_genre_rows.append({"genre": genre, "n": int(len(subset)),
                                       "median_observed_k_proxy": float(subset.k_midpoint_proxy.median()),
                                       "median_predicted_k": float(subset.predicted_k.median()),
                                       "median_training_genre_baseline_k": float(np.median([x for x in genre_pred[[i for i, values in enumerate(frame.iloc[holdout_idx].genres) if genre in values]]]))})
    holdout_genre_rows.sort(key=lambda x: (-x["n"], x["genre"]))

    encoder = model.named_steps["encode"]
    imputer = model.named_steps["impute"]
    feature_names = encoder.get_feature_names_out()
    if "select" in model.named_steps:
        selection = model.named_steps["select"]
        feature_names = feature_names[selection.get_support()]
    fitted_estimator = model.named_steps["model"]
    if hasattr(fitted_estimator, "feature_importances_"):
        importance_values = fitted_estimator.feature_importances_
    elif hasattr(fitted_estimator, "coef_"):
        importance_values = np.abs(np.asarray(fitted_estimator.coef_).reshape(-1))
    else:
        importance_values = np.zeros(len(feature_names), dtype=float)
    feature_importance = sorted(
        [{"feature": str(name), "importance": float(value)} for name, value in zip(feature_names, importance_values)],
        key=lambda row: (-row["importance"], row["feature"]),
    )
    def id_digest(values) -> str:
        return hashlib.sha256("\n".join(sorted(map(str, values))).encode("utf-8")).hexdigest()
    fold_digests = []
    for fold_index, (fold_train, fold_validation) in enumerate(cv.split(X_train), start=1):
        fold_digests.append({"fold": fold_index, "train_appid_sha256": id_digest(frame.iloc[train_idx[fold_train]].appid),
                             "validation_appid_sha256": id_digest(frame.iloc[train_idx[fold_validation]].appid)})
    source_code = Path(__file__).resolve()
    runner_code = repo_root / "tools/steam/run_homework.py"
    report = {
        "case_id": CASE_ID,
        "run_id": "steam-review-multiplier-run-01",
        "source_file": DATASET_FILE,
        "data_sha256": _sha_file(data_dir / DATASET_FILE),
        "target": TARGET_DESCRIPTION,
        "target_transform": "log1p(K midpoint proxy); inverse with expm1 and clip negative predictions to zero",
        "review_minimum": REVIEW_MINIMUM,
        "source_rows": audit["rows"],
        "eligible_rows": int(len(frame)),
        "train_rows": int(len(train_idx)),
        "holdout_rows": int(len(holdout_idx)),
        "split": {"type": "random row split on unique AppID snapshot", "holdout_fraction": HOLDOUT_FRACTION,
                  "seed": SEED, "appids_unique": True,
                  "development_appid_sha256": id_digest(frame.iloc[train_idx].appid),
                  "holdout_appid_sha256": id_digest(frame.iloc[holdout_idx].appid)},
        "cv": {"folds": CV_FOLDS, "shuffle": True, "seed": SEED,
               "preprocessing_and_selection_fit_inside_each_fold": True, "fold_membership_sha256": fold_digests},
        "raw_candidate_field_count": len(RAW_CANDIDATE_FIELDS),
        "raw_candidate_fields": RAW_CANDIDATE_FIELDS,
        "model_input_fields": MODEL_INPUT_FIELDS,
        "cv_configurations": cv_results,
        "selected_configuration": selected["configuration_id"],
        "holdout_metrics": baseline_rows,
        "genre_holdout_summary": holdout_genre_rows,
        "selected_features": [str(x) for x in feature_names],
        "feature_importance": feature_importance,
        "feature_selection_note": "RFE configuration is available as a distinct CV candidate; final feature names reflect selected winner.",
        "software": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
                     "scikit_learn": sklearn.__version__},
        "source_code_sha256": {"research_module": _sha_file(source_code), "runner": _sha_file(runner_code)},
        "limitations": [
            "SteamSpy estimated_owners are interval estimates, not observed sales.",
            "The single-value target is the interval midpoint divided by review count.",
            "Rows with fewer than 20 reviews are excluded from the primary model due to unstable ratios.",
            "The 2025 snapshot is cross-sectional and does not establish causal effects.",
            "Random split metrics describe this dataset's proxy target, not future sales accuracy.",
            "Holdout metrics were inspected during implementation and rerun after correcting missing-list handling; no model or feature-selection choice was changed from holdout results, but this is not a sealed preregistered test.",
        ],
    }
    private = output_dir / "private"
    private.mkdir(parents=True, exist_ok=True)
    dump(model, private / "steam-review-multiplier.joblib", compress=3)
    write_json(private / "model-metadata.json", {"case_id": CASE_ID, "run_id": report["run_id"],
                "selected_configuration": report["selected_configuration"], "feature_names": report["selected_features"],
                "input_fields": MODEL_INPUT_FIELDS, "model_version": "1.0.0",
                "source_code_sha256": report["source_code_sha256"], "selected_estimator_parameters": selected["estimator_parameters"],
                "selected_selector_parameters": selected["selector_parameters"]})
    write_json(output_dir / "phase-04" / "modeling-results.json", {"cv": cv_results,
                "selected_configuration": report["selected_configuration"], "selected_features": report["selected_features"]})
    write_json(output_dir / "phase-05" / "holdout-evaluation.json", report)
    _plot_model_results(report, output_dir / "phase-04" / "figures", output_dir / "phase-05" / "figures",
                        y_hold_k, pred_hold)
    _write_private_predictions(frame.iloc[holdout_idx], pred_hold, genre_pred, private)
    return report


def _write_private_predictions(holdout: pd.DataFrame, predicted: np.ndarray, genre_pred: np.ndarray, destination: Path) -> None:
    # Kept under ignored local/ only; never copied into public Case Package assets.
    pd.DataFrame({"appid": holdout.appid.to_numpy(), "actual_k_proxy": holdout.k_midpoint_proxy.to_numpy(),
                  "predicted_k": predicted, "genre_baseline_k": genre_pred,
                  "review_count": holdout.review_count.to_numpy()}).to_csv(destination / "holdout-predictions-private.csv", index=False)


def _plot_model_results(report: dict[str, Any], phase4_dir: Path, phase5_dir: Path,
                        actual_k: np.ndarray, predicted_k: np.ndarray) -> None:
    phase4_dir.mkdir(parents=True, exist_ok=True); phase5_dir.mkdir(parents=True, exist_ok=True)
    cv = report["cv_configurations"]
    fig, ax = plt.subplots(figsize=(9, 4.8)); ax.bar([x["configuration_id"] for x in cv], [x["mean_log_rmse"] for x in cv], color="#4f8292")
    ax.set_ylabel("3-fold CV RMSE · log(1+K)"); ax.set_title("Model and feature-selection comparison"); ax.tick_params(axis="x", rotation=25); fig.tight_layout(); fig.savefig(phase4_dir / "cv-model-comparison.png", dpi=140); plt.close(fig)
    rows = report["holdout_metrics"]
    fig, ax = plt.subplots(figsize=(8.5, 4.8)); ax.bar([x["model"] for x in rows], [x["mae"] for x in rows], color="#bd8759")
    ax.set_ylabel("Holdout MAE · K midpoint proxy"); ax.set_title("Fixed, genre and ML K comparison"); ax.tick_params(axis="x", rotation=20); fig.tight_layout(); fig.savefig(phase5_dir / "holdout-baseline-comparison.png", dpi=140); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8.5, 4.8)); ax.bar([x["model"] for x in rows], [x["owners_interval_compatibility_rate"] for x in rows], color="#648b7c")
    ax.set_ylim(0,1); ax.set_ylabel("Holdout ownership interval compatibility"); ax.set_title("Estimated ownership compared with SteamSpy intervals"); ax.tick_params(axis="x", rotation=20); fig.tight_layout(); fig.savefig(phase5_dir / "holdout-interval-compatibility.png", dpi=140); plt.close(fig)
    genres = report["genre_holdout_summary"][:15]
    fig, ax = plt.subplots(figsize=(9,5.5)); ax.barh([x["genre"] for x in genres][::-1], [x["median_predicted_k"] for x in genres][::-1], color="#4f8292")
    ax.set_xscale("log"); ax.set_xlabel("Median predicted K"); ax.set_title("Holdout predictions summarized by multi-label genre"); fig.tight_layout(); fig.savefig(phase5_dir / "genre-predicted-k.png", dpi=140); plt.close(fig)
    order = np.argsort(predicted_k, kind="mergesort")
    bins = [part for part in np.array_split(order, 20) if len(part)]
    calibration = [{"n": int(len(part)), "mean_predicted_k": float(predicted_k[part].mean()),
                    "mean_observed_k_proxy": float(actual_k[part].mean()),
                    "mean_residual_actual_minus_predicted": float((actual_k[part] - predicted_k[part]).mean())}
                   for part in bins]
    (phase5_dir / "actual-predicted-bins.json").write_text(
        json.dumps(calibration, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    fig, ax = plt.subplots(figsize=(6.5,5.5)); ax.scatter([x["mean_predicted_k"] for x in calibration], [x["mean_observed_k_proxy"] for x in calibration], s=[max(18, x["n"]**.5*2) for x in calibration], color="#4f8292", alpha=.85)
    limits = [0, max(x["mean_predicted_k"] for x in calibration + [{"mean_predicted_k": max(x["mean_observed_k_proxy"] for x in calibration)}])]
    ax.plot(limits, limits, color="#bd8759", linestyle="--"); ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Mean predicted K"); ax.set_ylabel("Mean observed K midpoint proxy"); ax.set_title("Holdout calibration · 20 prediction-quantile bins"); fig.tight_layout(); fig.savefig(phase5_dir / "actual-vs-predicted.png", dpi=140); plt.close(fig)
    residuals = actual_k - predicted_k
    upper = np.quantile(np.abs(residuals), .99)
    fig, ax = plt.subplots(figsize=(8,4.5)); ax.hist(np.clip(residuals, -upper, upper), bins=45, color="#648b7c")
    ax.set_title("Holdout residual distribution · display clipped at 99th |residual| percentile"); ax.set_xlabel("Observed proxy K − predicted K"); ax.set_ylabel("Games"); fig.tight_layout(); fig.savefig(phase5_dir / "residual-distribution.png", dpi=140); plt.close(fig)


def predict_from_inputs(model_path: Path, values: dict[str, Any]) -> float:
    from joblib import load
    model = load(model_path)
    row = {name: values.get(name) for name in MODEL_INPUT_FIELDS}
    frame = pd.DataFrame([{**row, "genres": list(row.get("genres") or [])}])
    return float(log_to_k(model.predict(frame))[0])
