"""P4-A baseline: all-feature, unpenalized SVD-compatible OLS with fold-local preprocessing.

Data isolation contract:
- Only the Phase 3 development-train membership (80% of the labeled file, seed 42) may
  enter fitting or cross-validation. Membership is reproduced from row *indices* only,
  using the exact permutation of ``split_labeled_dataset``; holdout indices are never
  returned or retained.
- ``load_development_rows`` streams the labeled CSV line by line and tokenizes only the
  lines whose index is in the development membership. Holdout lines are skipped without
  parsing. The competition test file is never opened.
- Each CV fold fits a fresh ``AmesDataPreparationPipeline`` on its training rows only and
  transforms the validation rows without refitting.

Coefficients from a rank-deficient design are not unique (minimum-norm solution) and must
not be read as feature importance.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import random
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from sklearn.model_selection import KFold

from housing_regression.data_prep import (
    ID_COLUMN,
    TARGET_COLUMN,
    AmesDataPreparationPipeline,
)

P4A_SCHEMA_VERSION = "p4a-ols-cv/1"


def development_train_indices(
    n_total: int, val_fraction: float = 0.2, random_state: int = 42
) -> list[int]:
    """Return sorted development-train row indices matching ``split_labeled_dataset``.

    Mirrors the Phase 3 splitter permutation exactly but returns only the train-side
    indices; the holdout side is discarded and never exposed.
    """
    if n_total <= 0:
        raise ValueError("n_total must be positive.")
    if not 0.0 < val_fraction < 1.0:
        raise ValueError(f"val_fraction must be in (0, 1), got {val_fraction}")
    n_train = int(round(n_total * (1.0 - val_fraction)))
    rng = random.Random(random_state)
    shuffled = list(range(n_total))
    rng.shuffle(shuffled)
    return sorted(shuffled[:n_train])


def kfold_assignments(n_rows: int, n_splits: int = 5, random_state: int = 42) -> list[int]:
    """Deterministic shuffled K-fold: return fold id (0..k-1) for each development position.

    Implements exact ``sklearn.model_selection.KFold(n_splits=n_splits, shuffle=True, random_state=random_state)``.
    """
    if n_splits < 2 or n_rows < n_splits:
        raise ValueError("Need n_splits >= 2 and n_rows >= n_splits.")
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    folds = [0] * n_rows
    for fold_idx, (_train_idx, val_idx) in enumerate(kf.split(range(n_rows))):
        for pos in val_idx:
            folds[pos] = fold_idx
    return folds


def fold_assignment_digest(folds: Sequence[int]) -> str:
    """SHA-256 of the fold assignment vector (public-safe provenance, no row data)."""
    return hashlib.sha256(",".join(str(f) for f in folds).encode("ascii")).hexdigest()


def load_development_rows(
    train_csv: Path,
    val_fraction: float = 0.2,
    random_state: int = 42,
    expected_total: int | None = 1460,
    validate_id_uniqueness: bool = True,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Stream the labeled CSV and parse only development-train lines.

    Pass 1 counts physical data lines without tokenizing. Pass 2 tokenizes the header and
    the development lines only; other lines are skipped unparsed.
    """
    train_csv = Path(train_csv)
    if train_csv.name.lower() == "test.csv":
        raise ValueError("The competition test file must never be used for P4-A.")
    with open(train_csv, "r", encoding="utf-8", newline="") as f:
        f.readline()  # header
        n_total = sum(1 for line in f if line.strip())
    if expected_total is not None and n_total != expected_total:
        raise ValueError(f"Unexpected labeled row count {n_total}; refusing ambiguous split provenance.")
    dev_idx = development_train_indices(n_total, val_fraction, random_state)
    dev_set = set(dev_idx)
    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    with open(train_csv, "r", encoding="utf-8", newline="") as f:
        header = next(csv.reader([f.readline()]))
        i = 0
        for line in f:
            if not line.strip():
                continue
            if i in dev_set:
                values = next(csv.reader(io.StringIO(line)))
                if len(values) != len(header):
                    raise ValueError("Malformed CSV line in development membership.")
                row_dict = dict(zip(header, values))
                if validate_id_uniqueness:
                    row_id = row_dict.get(ID_COLUMN)
                    if not row_id:
                        raise ValueError("Missing or empty Id in development row.")
                    if row_id in seen_ids:
                        raise ValueError(f"Duplicate Id detected in development membership: {row_id}")
                    seen_ids.add(row_id)
                rows.append(row_dict)
            i += 1
    provenance = {
        "labeled_rows_counted": n_total,
        "development_rows": len(rows),
        "split_seed": random_state,
        "val_fraction": val_fraction,
        "lines_tokenized": len(rows),
        "development_index_digest": hashlib.sha256(
            ",".join(map(str, dev_idx)).encode("ascii")
        ).hexdigest(),
        "id_uniqueness_verified": validate_id_uniqueness,
        "unique_id_count": len(seen_ids) if validate_id_uniqueness else None,
    }
    return rows, provenance


def compute_numerical_diagnostics(design: np.ndarray) -> dict[str, Any]:
    """Compute SVD-based rank and conditioning diagnostics on design matrix."""
    n, p = design.shape
    s = np.linalg.svd(design, compute_uv=False)
    s_max = float(s[0]) if s.size else 0.0
    tol = float(max(n, p) * np.finfo(np.float64).eps * s_max)
    nonzero = s[s > tol]
    rank = int(len(nonzero))
    s_min_nonzero = float(nonzero[-1]) if nonzero.size else 0.0
    s_min = float(s[-1]) if s.size else 0.0
    return {
        "rank": rank,
        "nullity": p - rank,
        "tolerance": tol,
        "singular_value_max": s_max,
        "singular_value_min": s_min,
        "singular_value_min_nonzero": s_min_nonzero,
        "condition_number_effective": (s_max / s_min_nonzero) if s_min_nonzero > 0 else None,
        "condition_number_full": (s_max / s_min) if s_min > tol else None,
        "singular_values": [float(v) for v in s],
    }


def fit_ols_svd(X: np.ndarray, y: np.ndarray, add_intercept: bool = True) -> dict[str, Any]:
    """Unpenalized least squares solver via SVD (``numpy.linalg.lstsq``)."""
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    design = np.column_stack([np.ones(X.shape[0]), X]) if add_intercept else X
    n, p = design.shape
    coef, _res, rank, _sv = np.linalg.lstsq(design, y, rcond=None)
    return {
        "coef": coef,
        "add_intercept": add_intercept,
        "n_rows": n,
        "n_params": p,
        "solver": "numpy.linalg.lstsq (SVD, minimum-norm)",
        "design_matrix": design,
    }


def predict(fit: Mapping[str, Any], X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=np.float64)
    design = np.column_stack([np.ones(X.shape[0]), X]) if fit["add_intercept"] else X
    return design @ fit["coef"]


def _rmse(y: np.ndarray, yhat: np.ndarray) -> float:
    return float(math.sqrt(np.mean((y - yhat) ** 2)))


def _r2(y: np.ndarray, yhat: np.ndarray) -> float:
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return float(1.0 - np.sum((y - yhat) ** 2) / ss_tot) if ss_tot > 0 else float("nan")


def run_ols_cv(
    dev_rows: Sequence[Mapping[str, Any]],
    n_splits: int = 5,
    random_state: int = 42,
    pipeline_factory: Callable[[], AmesDataPreparationPipeline] = AmesDataPreparationPipeline,
) -> dict[str, Any]:
    """Run deterministic K-fold OLS CV with a fresh preprocessor fitted inside each fold."""
    folds = kfold_assignments(len(dev_rows), n_splits, random_state)
    per_fold: list[dict[str, Any]] = []
    for k in range(n_splits):
        tr = [dev_rows[i] for i, f in enumerate(folds) if f != k]
        va = [dev_rows[i] for i, f in enumerate(folds) if f == k]

        # 1. Preprocessing stage
        t0 = time.perf_counter()
        pipe = pipeline_factory()
        tr_res = pipe.fit_transform(tr, split_name=f"cv{k}_train")
        va_res = pipe.transform(va, split_name=f"cv{k}_val")
        t1 = time.perf_counter()

        X_tr, X_va = tr_res.to_numpy(), va_res.to_numpy()
        y_tr = np.asarray(tr_res.y, dtype=np.float64)
        y_va = np.asarray(va_res.y, dtype=np.float64)
        if ID_COLUMN in tr_res.feature_names or TARGET_COLUMN in tr_res.feature_names:
            raise AssertionError("Id/SalePrice leaked into X.")

        # 2. Model fit stage (solver only)
        t_fit_start = time.perf_counter()
        fit = fit_ols_svd(X_tr, y_tr)
        t_fit_end = time.perf_counter()

        # 3. Numerical diagnostics stage
        t_diag_start = time.perf_counter()
        diagnostics = compute_numerical_diagnostics(fit["design_matrix"])
        t_diag_end = time.perf_counter()

        # 4. Predict and evaluate stage
        t_pred_start = time.perf_counter()
        yhat_tr, yhat_va = predict(fit, X_tr), predict(fit, X_va)
        rmse_va = _rmse(y_va, yhat_va)
        r2_va = _r2(y_va, yhat_va)
        rmse_tr = _rmse(y_tr, yhat_tr)
        r2_tr = _r2(y_tr, yhat_tr)
        t_pred_end = time.perf_counter()

        model_diag = {k2: v for k2, v in fit.items() if k2 not in ("coef", "design_matrix")}
        model_diag.update(diagnostics)

        per_fold.append({
            "fold": k,
            "n_train": len(tr),
            "n_validation": len(va),
            "n_features": tr_res.n_features,
            "feature_names": list(tr_res.feature_names),
            "validation_unseen_categories": len(va_res.unseen_categories),
            "rmse_validation": rmse_va,
            "r2_validation": r2_va,
            "rmse_train": rmse_tr,
            "r2_train": r2_tr,
            "diagnostics": model_diag,
            "elapsed_seconds": {
                "preprocessing": t1 - t0,
                "model_fit": t_fit_end - t_fit_start,
                "numerical_diagnostics": t_diag_end - t_diag_start,
                "predict_and_evaluate": t_pred_end - t_pred_start,
            },
        })

    def _agg(key: str) -> dict[str, float]:
        vals = np.array([f[key] for f in per_fold], dtype=np.float64)
        return {"mean": float(vals.mean()), "std": float(vals.std(ddof=1))}

    def _agg_time(stage: str) -> dict[str, float]:
        vals = np.array([f["elapsed_seconds"][stage] for f in per_fold], dtype=np.float64)
        return {"mean": float(vals.mean()), "std": float(vals.std(ddof=1))}

    timing_stages = [
        "preprocessing",
        "model_fit",
        "numerical_diagnostics",
        "predict_and_evaluate",
    ]
    aggregate_timing = {stage: _agg_time(stage) for stage in timing_stages}
    total_times = np.array([sum(f["elapsed_seconds"].values()) for f in per_fold], dtype=np.float64)
    aggregate_timing["total_per_fold"] = {"mean": float(total_times.mean()), "std": float(total_times.std(ddof=1))}

    return {
        "schema_version": P4A_SCHEMA_VERSION,
        "model": "all-feature unpenalized OLS (SVD/minimum-norm) with intercept",
        "cv": {
            "n_splits": n_splits,
            "random_state": random_state,
            "shuffle": True,
            "n_development_rows": len(dev_rows),
            "fold_sizes": [sum(1 for f in folds if f == k) for k in range(n_splits)],
            "fold_assignment_sha256": fold_assignment_digest(folds),
        },
        "aggregate": {
            "rmse_validation": _agg("rmse_validation"),
            "r2_validation": _agg("r2_validation"),
            "rmse_train": _agg("rmse_train"),
            "r2_train": _agg("r2_train"),
            "timing_seconds": aggregate_timing,
            "std_ddof": 1,
        },
        "folds": per_fold,
        "_fold_assignments": folds,  # local-only provenance; strip before public export
    }


def public_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    """Strip local-only provenance and full singular spectra for public-safe export."""
    out = json.loads(json.dumps({k: v for k, v in result.items() if not k.startswith("_")}))
    for f in out["folds"]:
        f["diagnostics"].pop("singular_values", None)
    return out
