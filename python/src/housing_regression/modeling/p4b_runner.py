"""P4-B-A modeling runner: feature selection and regularization experiment protocol.

Data isolation & execution contract:
- Nested 5-fold outer / 3-fold inner cross-validation.
- Fold-local AmesDataPreparationPipeline fitted exclusively on current training partitions.
- Conservative preflight fit budget calculation before any fitting begins.
- Strict timeout deadline enforcement and killable worker process boundary on timeout.
- Single worker / single-thread execution via threadpoolctl.
- Containment enforcement: private research outputs strictly under local/research/phase4-p4b/<run-id>.
- Bounded checkpoint resume: reads and validates state before executing remaining folds.
- Durable atomic failure reporting on injected or unexpected errors.
- Zero Git or shell subprocess commands in runtime.
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import io
import json
import math
import multiprocessing as mp
import os
import re
import struct
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
from sklearn.linear_model import ElasticNet, Lasso, Ridge
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
import threadpoolctl

from housing_regression.data_prep import (
    ALL_PREDICTOR_COLUMNS,
    ID_COLUMN,
    NOMINAL_COLUMNS,
    ORDINAL_COLUMNS,
    TARGET_COLUMN,
    AmesDataPreparationPipeline,
    TransformResult,
)
from housing_regression.modeling.ols_cv import (
    compute_numerical_diagnostics,
    fit_ols_svd,
    kfold_assignments,
    predict as predict_ols,
)

PROTOCOL_VERSION: str = "v1.0"
DEFAULT_D_CEILING: int = 300
DEFAULT_ESTIMATOR_FIT_CAP: int = 150000
DEFAULT_PREPROCESSOR_FIT_CAP: int = 200

# 80-column canonical schema definitions
SCHEMA_STRING_COLUMNS: Set[str] = set(NOMINAL_COLUMNS + ORDINAL_COLUMNS)
SCHEMA_INT_COLUMNS: Set[str] = {
    "YearBuilt",
    "YearRemodAdd",
    "BsmtFullBath",
    "BsmtHalfBath",
    "FullBath",
    "HalfBath",
    "BedroomAbvGr",
    "KitchenAbvGr",
    "TotRmsAbvGrd",
    "Fireplaces",
    "GarageCars",
    "MoSold",
    "YrSold",
    "OverallQual",
    "OverallCond",
    TARGET_COLUMN,
}
SCHEMA_FLOAT_COLUMNS: Set[str] = {
    "LotFrontage",
    "LotArea",
    "MasVnrArea",
    "BsmtFinSF1",
    "BsmtFinSF2",
    "BsmtUnfSF",
    "TotalBsmtSF",
    "1stFlrSF",
    "2ndFlrSF",
    "LowQualFinSF",
    "GrLivArea",
    "GarageYrBlt",
    "GarageArea",
    "WoodDeckSF",
    "OpenPorchSF",
    "EnclosedPorch",
    "3SsnPorch",
    "ScreenPorch",
    "PoolArea",
    "MiscVal",
}

INT_REGEX = re.compile(r"^[+-]?[0-9]+$")

# Supported candidate K set
ALLOWED_K_CANDIDATES: Tuple[int, ...] = (2, 3, 5, 10, 20)

# Supported 7 method-track pairs
SUPPORTED_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("filter_pearson", "Track A"),
    ("forward_sfs", "Track A"),
    ("rfe_ridge", "Track A"),
    ("lasso_cv", "Track A"),
    ("lasso_cv", "Track B"),
    ("elastic_net_cv", "Track A"),
    ("elastic_net_cv", "Track B"),
)


class DimensionCeilingExceededError(RuntimeError):
    """Raised when observed feature dimension exceeds D_ceiling."""


class BudgetExceededError(RuntimeError):
    """Raised when estimator or preprocessor fit budget is exceeded."""


class TimeoutExceededError(RuntimeError):
    """Raised when execution exceeds the configured wall-clock timeout."""


class InvalidDataFormatError(ValueError):
    """Raised when raw CSV cell violates canonical data format."""


class ResumeVerificationError(RuntimeError):
    """Raised when checkpoint identity does not match current run parameters."""


@dataclass
class FitAccounting:
    estimator_fits: int = 0
    preprocessor_fits: int = 0
    estimator_fit_cap: int = DEFAULT_ESTIMATOR_FIT_CAP
    preprocessor_fit_cap: int = DEFAULT_PREPROCESSOR_FIT_CAP

    def record_estimator_fit(self, count: int = 1) -> None:
        if self.estimator_fits + count > self.estimator_fit_cap:
            raise BudgetExceededError(
                f"Estimator fit count {self.estimator_fits + count} exceeds cap {self.estimator_fit_cap}."
            )
        self.estimator_fits += count

    def record_preprocessor_fit(self, count: int = 1) -> None:
        if self.preprocessor_fits + count > self.preprocessor_fit_cap:
            raise BudgetExceededError(
                f"Preprocessor fit count {self.preprocessor_fits + count} exceeds cap {self.preprocessor_fit_cap}."
            )
        self.preprocessor_fits += count


@dataclass
class P4BConfig:
    code_head_commit: str
    protocol_version: str = PROTOCOL_VERSION
    d_ceiling: int = DEFAULT_D_CEILING
    estimator_fit_cap: int = DEFAULT_ESTIMATOR_FIT_CAP
    preprocessor_fit_cap: int = DEFAULT_PREPROCESSOR_FIT_CAP
    outer_splits: int = 5
    outer_seed: int = 42
    inner_splits: int = 3
    inner_seed: int = 1042
    k_candidates: Tuple[int, ...] = ALLOWED_K_CANDIDATES
    lasso_alphas_count: int = 50
    lasso_alpha_min: float = 0.1
    lasso_alpha_max: float = 1000.0
    elastic_net_l1_ratios: Tuple[float, ...] = (0.1, 0.5, 0.7, 0.9, 0.95, 0.99)
    elastic_net_alphas_count: int = 30
    elastic_net_alpha_min: float = 0.1
    elastic_net_alpha_max: float = 1000.0
    max_iter: int = 5000
    tol: float = 1e-4
    single_thread: bool = True
    timeout_seconds: Optional[float] = None
    use_isolated_worker_process: bool = True
    repo_root: Optional[Path] = None
    active_methods: Optional[List[str]] = None  # None means all 5 methods
    active_pairs: Optional[List[Tuple[str, str]]] = None  # None means all 7 pairs

    def validate_positive(self) -> None:
        if self.outer_splits < 2:
            raise ValueError(f"outer_splits must be >= 2, got {self.outer_splits}")
        if self.inner_splits < 2:
            raise ValueError(f"inner_splits must be >= 2, got {self.inner_splits}")
        if self.d_ceiling <= 0:
            raise ValueError(f"d_ceiling must be positive, got {self.d_ceiling}")
        if self.estimator_fit_cap <= 0:
            raise ValueError(f"estimator_fit_cap must be positive, got {self.estimator_fit_cap}")
        if self.preprocessor_fit_cap <= 0:
            raise ValueError(f"preprocessor_fit_cap must be positive, got {self.preprocessor_fit_cap}")


def estimate_preflight_budget(config: P4BConfig) -> Tuple[int, int]:
    """Calculate conservative upper bound on estimator fits and preprocessor fits."""
    config.validate_positive()
    M = config.outer_splits
    m = config.inner_splits
    d = config.d_ceiling
    k_count = len(config.k_candidates)
    max_k = max(config.k_candidates) if config.k_candidates else 20
    min_k = min(config.k_candidates) if config.k_candidates else 2

    preprocessor_fits = M * (m + 1)

    active_methods = config.active_methods or [
        "filter_pearson",
        "forward_sfs",
        "rfe_ridge",
        "lasso_cv",
        "elastic_net_cv",
    ]

    total_estimator_fits = 0

    if "filter_pearson" in active_methods:
        filter_per_outer = m * k_count + 1
        total_estimator_fits += M * filter_per_outer

    if "forward_sfs" in active_methods:
        sfs_steps_fits = sum(d - i for i in range(max_k))
        sfs_per_outer = m * (sfs_steps_fits + k_count) + sfs_steps_fits + 1
        total_estimator_fits += M * sfs_per_outer

    if "rfe_ridge" in active_methods:
        rfe_elim_fits = d - min_k + 1
        rfe_per_outer = m * (rfe_elim_fits + k_count) + rfe_elim_fits + 1
        total_estimator_fits += M * rfe_per_outer

    if "lasso_cv" in active_methods:
        alphas = config.lasso_alphas_count
        lasso_per_outer = m * alphas * 2 + 3
        total_estimator_fits += M * lasso_per_outer

    if "elastic_net_cv" in active_methods:
        en_grid_size = config.elastic_net_alphas_count * len(config.elastic_net_l1_ratios)
        en_per_outer = m * en_grid_size * 2 + 3
        total_estimator_fits += M * en_per_outer

    return total_estimator_fits, preprocessor_fits


def get_canonical_column_order() -> List[str]:
    """Return 79 predictor columns in ASCII ascending order followed by SalePrice."""
    predictors = sorted([c for c in SCHEMA_STRING_COLUMNS | SCHEMA_INT_COLUMNS | SCHEMA_FLOAT_COLUMNS if c != TARGET_COLUMN])
    return predictors + [TARGET_COLUMN]


def encode_canonical_cell(val: Optional[str], col_name: str) -> bytes:
    """Encode a raw CSV string cell into canonical binary packet format."""
    if val is None or val == "" or val.isspace():
        return struct.pack(">BI", 0x00, 0)

    if col_name in SCHEMA_STRING_COLUMNS:
        norm_val = unicodedata.normalize("NFC", val)
        payload = norm_val.encode("utf-8")
        return struct.pack(">BI", 0x01, len(payload)) + payload

    elif col_name in SCHEMA_INT_COLUMNS:
        if not INT_REGEX.match(val):
            raise InvalidDataFormatError(f"Column '{col_name}' value '{val}' violates INT format.")
        n = int(val)
        return struct.pack(">BIq", 0x02, 8, n)

    elif col_name in SCHEMA_FLOAT_COLUMNS:
        try:
            f = float(val)
        except ValueError as exc:
            raise InvalidDataFormatError(f"Column '{col_name}' value '{val}' is not a valid float.") from exc
        if math.isinf(f):
            raise InvalidDataFormatError(f"Column '{col_name}' value contains infinity: {val}")
        if math.isnan(f):
            return struct.pack(">BI", 0x00, 0)
        if f == 0.0:
            f = 0.0
        return struct.pack(">BId", 0x03, 8, f)

    raise InvalidDataFormatError(f"Unknown column: {col_name}")


def compute_canonical_fingerprint(rows: Sequence[Mapping[str, str]]) -> str:
    """Compute deterministic SHA-256 fingerprint over canonical binary stream of rows."""
    col_order = get_canonical_column_order()
    hasher = hashlib.sha256()
    for row in rows:
        for col in col_order:
            val = row.get(col)
            cell_bytes = encode_canonical_cell(val, col)
            hasher.update(cell_bytes)
    return hasher.hexdigest()


def compute_pearson_correlations(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Compute Pearson correlation absolute value |r| for each feature against y."""
    n_features = X.shape[1]
    y_mean = np.mean(y)
    y_diff = y - y_mean
    y_ss = np.sum(y_diff ** 2)

    corrs = np.zeros(n_features, dtype=np.float64)
    if y_ss == 0.0:
        return corrs

    for j in range(n_features):
        xj = X[:, j]
        if not np.all(np.isfinite(xj)):
            corrs[j] = -1.0
            continue
        x_mean = np.mean(xj)
        x_diff = xj - x_mean
        x_ss = np.sum(x_diff ** 2)
        if x_ss == 0.0:
            corrs[j] = 0.0
            continue
        numerator = np.sum(x_diff * y_diff)
        r = numerator / (math.sqrt(x_ss) * math.sqrt(y_ss))
        corrs[j] = abs(r)
    return corrs


def select_features_filter(
    X_train: np.ndarray,
    y_train: np.ndarray,
    feature_names: List[str],
    k: int,
    eps: float = 1e-9,
) -> Tuple[List[int], List[str]]:
    """Filter method: Pearson |r| with lexicographical tie-breaking."""
    if k > len(feature_names):
        raise ValueError(f"k ({k}) cannot exceed feature dimension ({len(feature_names)}).")
    corrs = compute_pearson_correlations(X_train, y_train)

    items = []
    for idx, (name, score) in enumerate(zip(feature_names, corrs)):
        items.append((idx, name, float(score)))

    def compare_key(item):
        idx, name, score = item
        bin_score = round(score / eps) * eps
        return (-bin_score, name)

    sorted_items = sorted(items, key=compare_key)
    selected = sorted_items[:k]
    selected_indices = [item[0] for item in selected]
    selected_names = [item[1] for item in selected]
    return selected_indices, selected_names


def forward_sfs_greedy_path(
    X_train: np.ndarray,
    y_train: np.ndarray,
    feature_names: List[str],
    max_k: int,
    accounting: FitAccounting,
    eps: float = 1e-9,
    check_deadline: Optional[Callable[[], None]] = None,
) -> List[Tuple[int, str]]:
    """Forward Sequential Feature Selection on training partition minimizing Train RMSE."""
    n_features = X_train.shape[1]
    limit_k = min(max_k, n_features)
    selected_indices: List[int] = []
    selected_names: List[str] = []
    remaining_indices = list(range(n_features))

    for step in range(limit_k):
        if check_deadline:
            check_deadline()
        best_candidate: Optional[int] = None
        best_rmse = float("inf")
        candidate_evals = []

        for cand_idx in remaining_indices:
            trial_indices = selected_indices + [cand_idx]
            X_sub = X_train[:, trial_indices]
            accounting.record_estimator_fit(1)
            fit = fit_ols_svd(X_sub, y_train, add_intercept=True)
            yhat = predict_ols(fit, X_sub)
            rmse = math.sqrt(float(np.mean((y_train - yhat) ** 2)))
            candidate_evals.append((cand_idx, feature_names[cand_idx], rmse))

        def sfs_cand_key(item):
            c_idx, name, rmse = item
            bin_rmse = round(rmse / eps) * eps
            return (bin_rmse, name)

        sorted_cands = sorted(candidate_evals, key=sfs_cand_key)
        best_chosen = sorted_cands[0]
        chosen_idx = best_chosen[0]
        chosen_name = best_chosen[1]

        selected_indices.append(chosen_idx)
        selected_names.append(chosen_name)
        remaining_indices.remove(chosen_idx)

    return list(zip(selected_indices, selected_names))


def rfe_ridge_path(
    X_train: np.ndarray,
    y_train: np.ndarray,
    feature_names: List[str],
    min_k: int,
    accounting: FitAccounting,
    random_state: int = 42,
    eps: float = 1e-9,
    check_deadline: Optional[Callable[[], None]] = None,
) -> Dict[int, Tuple[List[int], List[str]]]:
    """RFE using Ridge(alpha=1.0) step=1 down to min_k, storing feature subsets at each k."""
    current_indices = list(range(X_train.shape[1]))
    current_names = list(feature_names)
    k_map: Dict[int, Tuple[List[int], List[str]]] = {}

    while len(current_indices) >= min_k:
        if check_deadline:
            check_deadline()
        k_map[len(current_indices)] = (list(current_indices), list(current_names))
        if len(current_indices) == min_k:
            break

        accounting.record_estimator_fit(1)
        ridge = Ridge(alpha=1.0, random_state=random_state, solver="auto")
        ridge.fit(X_train[:, current_indices], y_train)
        coef_abs = np.abs(ridge.coef_)

        min_val = float(np.min(coef_abs))
        tied = [i for i, c in enumerate(coef_abs) if c - min_val <= eps]
        tied_names = [current_names[i] for i in tied]
        elim_name = max(tied_names)
        elim_pos = current_names.index(elim_name)

        current_indices.pop(elim_pos)
        current_names.pop(elim_pos)

    return k_map


def tie_break_subset_k(
    candidates_scores: List[Tuple[int, float]],
    eps: float = 1e-9,
) -> int:
    """Tie-set formation for K in {2,3,5,10,20}: min RMSE; within eps, smaller K (sparsity)."""
    min_score = min(score for _, score in candidates_scores)
    tied_k = [k for k, score in candidates_scores if score - min_score <= eps]
    return min(tied_k)


def tie_break_lasso_alpha(
    candidates_scores: List[Tuple[float, int, float]],
    eps: float = 1e-9,
) -> Tuple[float, int]:
    """Tie-break for Lasso alpha: min RMSE; within eps, larger alpha; if still tied, smaller grid index."""
    min_score = min(score for _, _, score in candidates_scores)
    tied = [(alpha, idx) for alpha, idx, score in candidates_scores if score - min_score <= eps]
    tied.sort(key=lambda item: (-item[0], item[1]))
    return tied[0]


def tie_break_elastic_net(
    candidates_scores: List[Tuple[float, float, int, float]],
    eps: float = 1e-9,
) -> Tuple[float, float, int]:
    """Tie-break for ElasticNet (alpha, l1_ratio): min RMSE; within eps, larger alpha; if tied, larger l1_ratio; if tied, smaller index."""
    min_score = min(score for _, _, _, score in candidates_scores)
    tied = [(alpha, l1, idx) for alpha, l1, idx, score in candidates_scores if score - min_score <= eps]
    tied.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return tied[0]


# Top-level worker target for isolated multiprocessing (Windows spawn compatible)
def _mp_worker_target(
    queue: Any,
    config: P4BConfig,
    outer_fold_idx: int,
    outer_train_rows: List[Dict[str, str]],
    outer_val_rows: List[Dict[str, str]],
    stall_before_fit: bool = False,
) -> None:
    try:
        # B03: enforce single-thread limits strictly inside child worker
        thread_limit = 1 if config.single_thread else None
        if thread_limit is not None:
            with threadpoolctl.threadpool_limits(limits=thread_limit):
                if stall_before_fit:
                    # Deliberately stall for timeout testing
                    time.sleep(30.0)
                runner = P4BRunner(config)
                res = runner.execute_outer_fold(outer_fold_idx, outer_train_rows, outer_val_rows)
                queue.put(("SUCCESS", res, runner.accounting.estimator_fits, runner.accounting.preprocessor_fits))
        else:
            if stall_before_fit:
                time.sleep(30.0)
            runner = P4BRunner(config)
            res = runner.execute_outer_fold(outer_fold_idx, outer_train_rows, outer_val_rows)
            queue.put(("SUCCESS", res, runner.accounting.estimator_fits, runner.accounting.preprocessor_fits))
    except Exception as exc:
        queue.put(("EXCEPTION", type(exc).__name__, str(exc)))


class P4BRunner:
    """Complete, leakage-safe Nested CV experiment runner for Phase 4-B-A."""

    def __init__(self, config: P4BConfig):
        self.config = config
        self.accounting = FitAccounting(
            estimator_fit_cap=config.estimator_fit_cap,
            preprocessor_fit_cap=config.preprocessor_fit_cap,
        )
        self.lasso_alphas = np.logspace(
            np.log10(config.lasso_alpha_max),
            np.log10(config.lasso_alpha_min),
            config.lasso_alphas_count,
        )
        self.en_alphas = np.logspace(
            np.log10(config.elastic_net_alpha_max),
            np.log10(config.elastic_net_alpha_min),
            config.elastic_net_alphas_count,
        )
        self.en_grid: List[Tuple[float, float, int]] = []
        grid_idx = 0
        for alpha in self.en_alphas:
            for l1 in config.elastic_net_l1_ratios:
                self.en_grid.append((float(alpha), float(l1), grid_idx))
                grid_idx += 1

        self.deadline: Optional[float] = None
        self.stall_mock_worker: bool = False

    def _check_deadline(self) -> None:
        """Enforce wall-clock timeout between units of work."""
        if self.deadline is not None and time.perf_counter() > self.deadline:
            raise TimeoutExceededError(
                f"Execution exceeded configured timeout limit ({self.config.timeout_seconds}s)."
            )

    def _apply_partition_scaling(
        self,
        X_train: np.ndarray,
        X_val: np.ndarray,
        feature_names: List[str],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Fit StandardScaler on numeric/ordinal features on train partition only, leaving one-hot unscaled."""
        d_obs = X_train.shape[1]
        if d_obs > self.config.d_ceiling:
            raise DimensionCeilingExceededError(
                f"Observed dimension {d_obs} exceeds ceiling {self.config.d_ceiling}."
            )

        X_tr = X_train.copy()
        X_va = X_val.copy()

        scale_indices = []
        for i, name in enumerate(feature_names):
            if name in NOMINAL_COLUMNS or "_" in name:
                continue
            scale_indices.append(i)

        if scale_indices:
            scaler = StandardScaler(with_mean=True, with_std=True)
            X_tr[:, scale_indices] = scaler.fit_transform(X_tr[:, scale_indices])
            X_va[:, scale_indices] = scaler.transform(X_va[:, scale_indices])

        return X_tr, X_va

    def execute_outer_fold(
        self,
        outer_fold_idx: int,
        outer_train_rows: List[Dict[str, str]],
        outer_val_rows: List[Dict[str, str]],
        pipeline_factory: Callable[[], AmesDataPreparationPipeline] = AmesDataPreparationPipeline,
    ) -> Dict[str, Any]:
        """Execute one complete Outer Fold with Inner 3-fold tuning and Outer Refit/Evaluation."""
        self._check_deadline()
        inner_kf = KFold(
            n_splits=self.config.inner_splits,
            shuffle=True,
            random_state=self.config.inner_seed,
        )
        inner_splits_indices = list(inner_kf.split(range(len(outer_train_rows))))

        # 1. Preprocess each of inner splits
        inner_partitions = []
        for inner_idx, (in_tr_idx, in_va_idx) in enumerate(inner_splits_indices):
            self._check_deadline()
            in_tr_rows = [outer_train_rows[i] for i in in_tr_idx]
            in_va_rows = [outer_train_rows[i] for i in in_va_idx]

            self.accounting.record_preprocessor_fit(1)
            pipe = pipeline_factory()
            tr_res = pipe.fit_transform(in_tr_rows, split_name=f"outer{outer_fold_idx}_inner{inner_idx}_train")
            va_res = pipe.transform(in_va_rows, split_name=f"outer{outer_fold_idx}_inner{inner_idx}_val")

            X_tr, X_va = self._apply_partition_scaling(
                tr_res.to_numpy(), va_res.to_numpy(), tr_res.feature_names
            )
            y_tr = np.asarray(tr_res.y, dtype=np.float64)
            y_va = np.asarray(va_res.y, dtype=np.float64)

            inner_partitions.append({
                "inner_idx": inner_idx,
                "feature_names": tr_res.feature_names,
                "X_tr": X_tr,
                "y_tr": y_tr,
                "X_va": X_va,
                "y_va": y_va,
            })

        # 2. Outer Train preprocessing (1 fit)
        self._check_deadline()
        self.accounting.record_preprocessor_fit(1)
        outer_pipe = pipeline_factory()
        out_tr_res = outer_pipe.fit_transform(outer_train_rows, split_name=f"outer{outer_fold_idx}_train")
        out_va_res = outer_pipe.transform(outer_val_rows, split_name=f"outer{outer_fold_idx}_val")

        X_out_tr, X_out_va = self._apply_partition_scaling(
            out_tr_res.to_numpy(), out_va_res.to_numpy(), out_tr_res.feature_names
        )
        y_out_tr = np.asarray(out_tr_res.y, dtype=np.float64)
        y_out_va = np.asarray(out_va_res.y, dtype=np.float64)

        outer_val_ids = list(out_va_res.ids)

        fold_results: List[Dict[str, Any]] = []
        oof_records: List[Dict[str, Any]] = []

        active_methods = self.config.active_methods or [
            "filter_pearson",
            "forward_sfs",
            "rfe_ridge",
            "lasso_cv",
            "elastic_net_cv",
        ]

        # --- A. Filter Pearson (Track A) ---
        if "filter_pearson" in active_methods:
            self._check_deadline()
            k_val_scores: Dict[int, List[float]] = {k: [] for k in self.config.k_candidates}
            for part in inner_partitions:
                for k in self.config.k_candidates:
                    self._check_deadline()
                    sel_indices, _ = select_features_filter(part["X_tr"], part["y_tr"], part["feature_names"], k)
                    self.accounting.record_estimator_fit(1)
                    fit = fit_ols_svd(part["X_tr"][:, sel_indices], part["y_tr"], add_intercept=True)
                    yhat = predict_ols(fit, part["X_va"][:, sel_indices])
                    rmse = math.sqrt(float(np.mean((part["y_va"] - yhat) ** 2)))
                    k_val_scores[k].append(rmse)

            avg_k_scores = [(k, float(np.mean(k_val_scores[k]))) for k in self.config.k_candidates]
            best_k = tie_break_subset_k(avg_k_scores)

            out_sel_idx, out_sel_names = select_features_filter(
                X_out_tr, y_out_tr, out_tr_res.feature_names, best_k
            )
            self.accounting.record_estimator_fit(1)
            final_fit = fit_ols_svd(X_out_tr[:, out_sel_idx], y_out_tr, add_intercept=True)
            yhat_va = predict_ols(final_fit, X_out_va[:, out_sel_idx])
            rmse_va = math.sqrt(float(np.mean((y_out_va - yhat_va) ** 2)))
            ss_tot = float(np.sum((y_out_va - y_out_va.mean()) ** 2))
            r2_va = float(1.0 - np.sum((y_out_va - yhat_va) ** 2) / ss_tot) if ss_tot > 0 else float("nan")

            diagnostics = compute_numerical_diagnostics(final_fit["design_matrix"])

            fold_results.append({
                "outer_fold": outer_fold_idx,
                "method": "filter_pearson",
                "track": "Track A",
                "selected_hyperparameter": {"k": best_k},
                "selected_feature_count": len(out_sel_names),
                "selected_feature_names": out_sel_names,
                "outer_val_rmse": rmse_va,
                "outer_val_r2": r2_va,
                "numerical_diagnostics": {
                    "rank": diagnostics["rank"],
                    "nullity": diagnostics["nullity"],
                    "effective_condition_number": diagnostics["condition_number_effective"],
                },
                "fit_accounting": {
                    "fold_estimator_fits": len(self.config.k_candidates) * self.config.inner_splits + 1,
                    "fold_preprocessor_fits": self.config.inner_splits + 1,
                },
                "convergence_status": "CONVERGED",
            })
            for row_id, act, pred in zip(outer_val_ids, y_out_va, yhat_va):
                oof_records.append({
                    "Id": row_id,
                    "OuterFold": outer_fold_idx,
                    "Method": "filter_pearson",
                    "Track": "Track A",
                    "ActualSalePrice": float(act),
                    "PredictedSalePrice": float(pred),
                })

        # --- B. Forward SFS (Track A) ---
        if "forward_sfs" in active_methods:
            self._check_deadline()
            max_cand_k = max(self.config.k_candidates)
            k_val_scores = {k: [] for k in self.config.k_candidates}
            for part in inner_partitions:
                path = forward_sfs_greedy_path(
                    part["X_tr"],
                    part["y_tr"],
                    part["feature_names"],
                    max_k=max_cand_k,
                    accounting=self.accounting,
                    check_deadline=self._check_deadline,
                )
                for k in self.config.k_candidates:
                    self._check_deadline()
                    sel_indices = [idx for idx, _ in path[:k]]
                    self.accounting.record_estimator_fit(1)
                    fit = fit_ols_svd(part["X_tr"][:, sel_indices], part["y_tr"], add_intercept=True)
                    yhat = predict_ols(fit, part["X_va"][:, sel_indices])
                    rmse = math.sqrt(float(np.mean((part["y_va"] - yhat) ** 2)))
                    k_val_scores[k].append(rmse)

            avg_k_scores = [(k, float(np.mean(k_val_scores[k]))) for k in self.config.k_candidates]
            best_k = tie_break_subset_k(avg_k_scores)

            outer_path = forward_sfs_greedy_path(
                X_out_tr,
                y_out_tr,
                out_tr_res.feature_names,
                max_k=best_k,
                accounting=self.accounting,
                check_deadline=self._check_deadline,
            )
            out_sel_idx = [idx for idx, _ in outer_path]
            out_sel_names = [name for _, name in outer_path]

            self.accounting.record_estimator_fit(1)
            final_fit = fit_ols_svd(X_out_tr[:, out_sel_idx], y_out_tr, add_intercept=True)
            yhat_va = predict_ols(final_fit, X_out_va[:, out_sel_idx])
            rmse_va = math.sqrt(float(np.mean((y_out_va - yhat_va) ** 2)))
            ss_tot = float(np.sum((y_out_va - y_out_va.mean()) ** 2))
            r2_va = float(1.0 - np.sum((y_out_va - yhat_va) ** 2) / ss_tot) if ss_tot > 0 else float("nan")

            diagnostics = compute_numerical_diagnostics(final_fit["design_matrix"])

            fold_results.append({
                "outer_fold": outer_fold_idx,
                "method": "forward_sfs",
                "track": "Track A",
                "selected_hyperparameter": {"k": best_k},
                "selected_feature_count": len(out_sel_names),
                "selected_feature_names": out_sel_names,
                "outer_val_rmse": rmse_va,
                "outer_val_r2": r2_va,
                "numerical_diagnostics": {
                    "rank": diagnostics["rank"],
                    "nullity": diagnostics["nullity"],
                    "effective_condition_number": diagnostics["condition_number_effective"],
                },
                "fit_accounting": {
                    "fold_estimator_fits": None,
                    "fold_preprocessor_fits": self.config.inner_splits + 1,
                },
                "convergence_status": "CONVERGED",
            })
            for row_id, act, pred in zip(outer_val_ids, y_out_va, yhat_va):
                oof_records.append({
                    "Id": row_id,
                    "OuterFold": outer_fold_idx,
                    "Method": "forward_sfs",
                    "Track": "Track A",
                    "ActualSalePrice": float(act),
                    "PredictedSalePrice": float(pred),
                })

        # --- C. RFE Ridge (Track A) ---
        if "rfe_ridge" in active_methods:
            self._check_deadline()
            min_cand_k = min(self.config.k_candidates)
            k_val_scores = {k: [] for k in self.config.k_candidates}
            for part in inner_partitions:
                k_map = rfe_ridge_path(
                    part["X_tr"],
                    part["y_tr"],
                    part["feature_names"],
                    min_k=min_cand_k,
                    accounting=self.accounting,
                    check_deadline=self._check_deadline,
                )
                for k in self.config.k_candidates:
                    self._check_deadline()
                    sel_indices, _ = k_map[k]
                    self.accounting.record_estimator_fit(1)
                    fit = fit_ols_svd(part["X_tr"][:, sel_indices], part["y_tr"], add_intercept=True)
                    yhat = predict_ols(fit, part["X_va"][:, sel_indices])
                    rmse = math.sqrt(float(np.mean((part["y_va"] - yhat) ** 2)))
                    k_val_scores[k].append(rmse)

            avg_k_scores = [(k, float(np.mean(k_val_scores[k]))) for k in self.config.k_candidates]
            best_k = tie_break_subset_k(avg_k_scores)

            outer_k_map = rfe_ridge_path(
                X_out_tr,
                y_out_tr,
                out_tr_res.feature_names,
                min_k=best_k,
                accounting=self.accounting,
                check_deadline=self._check_deadline,
            )
            out_sel_idx, out_sel_names = outer_k_map[best_k]

            self.accounting.record_estimator_fit(1)
            final_fit = fit_ols_svd(X_out_tr[:, out_sel_idx], y_out_tr, add_intercept=True)
            yhat_va = predict_ols(final_fit, X_out_va[:, out_sel_idx])
            rmse_va = math.sqrt(float(np.mean((y_out_va - yhat_va) ** 2)))
            ss_tot = float(np.sum((y_out_va - y_out_va.mean()) ** 2))
            r2_va = float(1.0 - np.sum((y_out_va - yhat_va) ** 2) / ss_tot) if ss_tot > 0 else float("nan")

            diagnostics = compute_numerical_diagnostics(final_fit["design_matrix"])

            fold_results.append({
                "outer_fold": outer_fold_idx,
                "method": "rfe_ridge",
                "track": "Track A",
                "selected_hyperparameter": {"k": best_k},
                "selected_feature_count": len(out_sel_names),
                "selected_feature_names": out_sel_names,
                "outer_val_rmse": rmse_va,
                "outer_val_r2": r2_va,
                "numerical_diagnostics": {
                    "rank": diagnostics["rank"],
                    "nullity": diagnostics["nullity"],
                    "effective_condition_number": diagnostics["condition_number_effective"],
                },
                "fit_accounting": {
                    "fold_estimator_fits": None,
                    "fold_preprocessor_fits": self.config.inner_splits + 1,
                },
                "convergence_status": "CONVERGED",
            })
            for row_id, act, pred in zip(outer_val_ids, y_out_va, yhat_va):
                oof_records.append({
                    "Id": row_id,
                    "OuterFold": outer_fold_idx,
                    "Method": "rfe_ridge",
                    "Track": "Track A",
                    "ActualSalePrice": float(act),
                    "PredictedSalePrice": float(pred),
                })

        # --- D. LassoCV (Track A & Track B) ---
        if "lasso_cv" in active_methods:
            self._check_deadline()
            alpha_track_a_scores: Dict[int, List[float]] = {i: [] for i in range(len(self.lasso_alphas))}
            alpha_track_b_scores: Dict[int, List[float]] = {i: [] for i in range(len(self.lasso_alphas))}

            for part in inner_partitions:
                for idx, alpha in enumerate(self.lasso_alphas):
                    self._check_deadline()
                    self.accounting.record_estimator_fit(1)
                    lasso = Lasso(alpha=alpha, max_iter=self.config.max_iter, tol=self.config.tol)
                    lasso.fit(part["X_tr"], part["y_tr"])

                    yhat_b = lasso.predict(part["X_va"])
                    rmse_b = math.sqrt(float(np.mean((part["y_va"] - yhat_b) ** 2)))
                    alpha_track_b_scores[idx].append(rmse_b)

                    non_zero = np.where(np.abs(lasso.coef_) > 1e-9)[0]
                    if len(non_zero) == 0:
                        yhat_a = np.full_like(part["y_va"], np.mean(part["y_tr"]))
                    else:
                        self.accounting.record_estimator_fit(1)
                        fit_a = fit_ols_svd(part["X_tr"][:, non_zero], part["y_tr"], add_intercept=True)
                        yhat_a = predict_ols(fit_a, part["X_va"][:, non_zero])
                    rmse_a = math.sqrt(float(np.mean((part["y_va"] - yhat_a) ** 2)))
                    alpha_track_a_scores[idx].append(rmse_a)

            cands_a = [
                (float(self.lasso_alphas[i]), i, float(np.mean(alpha_track_a_scores[i])))
                for i in range(len(self.lasso_alphas))
            ]
            cands_b = [
                (float(self.lasso_alphas[i]), i, float(np.mean(alpha_track_b_scores[i])))
                for i in range(len(self.lasso_alphas))
            ]
            best_alpha_a, best_idx_a = tie_break_lasso_alpha(cands_a)
            best_alpha_b, best_idx_b = tie_break_lasso_alpha(cands_b)

            # Track A Outer Refit
            self._check_deadline()
            self.accounting.record_estimator_fit(1)
            lasso_out_a = Lasso(alpha=best_alpha_a, max_iter=self.config.max_iter, tol=self.config.tol)
            lasso_out_a.fit(X_out_tr, y_out_tr)
            non_zero_a = np.where(np.abs(lasso_out_a.coef_) > 1e-9)[0]
            out_sel_names_a = [out_tr_res.feature_names[i] for i in non_zero_a]

            if len(non_zero_a) == 0:
                yhat_va_a = np.full_like(y_out_va, np.mean(y_out_tr))
                diag_a = {"rank": 1, "nullity": 0, "effective_condition_number": 1.0}
            else:
                self.accounting.record_estimator_fit(1)
                final_fit_a = fit_ols_svd(X_out_tr[:, non_zero_a], y_out_tr, add_intercept=True)
                yhat_va_a = predict_ols(final_fit_a, X_out_va[:, non_zero_a])
                diag_res = compute_numerical_diagnostics(final_fit_a["design_matrix"])
                diag_a = {
                    "rank": diag_res["rank"],
                    "nullity": diag_res["nullity"],
                    "effective_condition_number": diag_res["condition_number_effective"],
                }

            rmse_va_a = math.sqrt(float(np.mean((y_out_va - yhat_va_a) ** 2)))
            ss_tot = float(np.sum((y_out_va - y_out_va.mean()) ** 2))
            r2_va_a = float(1.0 - np.sum((y_out_va - yhat_va_a) ** 2) / ss_tot) if ss_tot > 0 else float("nan")

            fold_results.append({
                "outer_fold": outer_fold_idx,
                "method": "lasso_cv",
                "track": "Track A",
                "selected_hyperparameter": {"alpha": best_alpha_a, "grid_index": best_idx_a},
                "selected_feature_count": len(out_sel_names_a),
                "selected_feature_names": out_sel_names_a,
                "outer_val_rmse": rmse_va_a,
                "outer_val_r2": r2_va_a,
                "numerical_diagnostics": diag_a,
                "fit_accounting": {
                    "fold_estimator_fits": None,
                    "fold_preprocessor_fits": self.config.inner_splits + 1,
                },
                "convergence_status": "CONVERGED",
            })
            for row_id, act, pred in zip(outer_val_ids, y_out_va, yhat_va_a):
                oof_records.append({
                    "Id": row_id,
                    "OuterFold": outer_fold_idx,
                    "Method": "lasso_cv",
                    "Track": "Track A",
                    "ActualSalePrice": float(act),
                    "PredictedSalePrice": float(pred),
                })

            # Track B Outer Refit
            self._check_deadline()
            self.accounting.record_estimator_fit(1)
            lasso_out_b = Lasso(alpha=best_alpha_b, max_iter=self.config.max_iter, tol=self.config.tol)
            lasso_out_b.fit(X_out_tr, y_out_tr)
            yhat_va_b = lasso_out_b.predict(X_out_va)
            rmse_va_b = math.sqrt(float(np.mean((y_out_va - yhat_va_b) ** 2)))
            r2_va_b = float(1.0 - np.sum((y_out_va - yhat_va_b) ** 2) / ss_tot) if ss_tot > 0 else float("nan")
            non_zero_b = np.where(np.abs(lasso_out_b.coef_) > 1e-9)[0]
            out_sel_names_b = [out_tr_res.feature_names[i] for i in non_zero_b]

            fold_results.append({
                "outer_fold": outer_fold_idx,
                "method": "lasso_cv",
                "track": "Track B",
                "selected_hyperparameter": {"alpha": best_alpha_b, "grid_index": best_idx_b},
                "selected_feature_count": len(out_sel_names_b),
                "selected_feature_names": out_sel_names_b,
                "outer_val_rmse": rmse_va_b,
                "outer_val_r2": r2_va_b,
                "numerical_diagnostics": {
                    "rank": len(non_zero_b),
                    "nullity": X_out_tr.shape[1] - len(non_zero_b),
                    "effective_condition_number": None,
                },
                "fit_accounting": {
                    "fold_estimator_fits": None,
                    "fold_preprocessor_fits": self.config.inner_splits + 1,
                },
                "convergence_status": "CONVERGED",
            })
            for row_id, act, pred in zip(outer_val_ids, y_out_va, yhat_va_b):
                oof_records.append({
                    "Id": row_id,
                    "OuterFold": outer_fold_idx,
                    "Method": "lasso_cv",
                    "Track": "Track B",
                    "ActualSalePrice": float(act),
                    "PredictedSalePrice": float(pred),
                })

        # --- E. ElasticNetCV (Track A & Track B) ---
        if "elastic_net_cv" in active_methods:
            self._check_deadline()
            en_track_a_scores: Dict[int, List[float]] = {i: [] for i in range(len(self.en_grid))}
            en_track_b_scores: Dict[int, List[float]] = {i: [] for i in range(len(self.en_grid))}

            for part in inner_partitions:
                for alpha, l1_ratio, idx in self.en_grid:
                    self._check_deadline()
                    self.accounting.record_estimator_fit(1)
                    en = ElasticNet(alpha=alpha, l1_ratio=l1_ratio, max_iter=self.config.max_iter, tol=self.config.tol)
                    en.fit(part["X_tr"], part["y_tr"])

                    yhat_b = en.predict(part["X_va"])
                    rmse_b = math.sqrt(float(np.mean((part["y_va"] - yhat_b) ** 2)))
                    en_track_b_scores[idx].append(rmse_b)

                    non_zero = np.where(np.abs(en.coef_) > 1e-9)[0]
                    if len(non_zero) == 0:
                        yhat_a = np.full_like(part["y_va"], np.mean(part["y_tr"]))
                    else:
                        self.accounting.record_estimator_fit(1)
                        fit_a = fit_ols_svd(part["X_tr"][:, non_zero], part["y_tr"], add_intercept=True)
                        yhat_a = predict_ols(fit_a, part["X_va"][:, non_zero])
                    rmse_a = math.sqrt(float(np.mean((part["y_va"] - yhat_a) ** 2)))
                    en_track_a_scores[idx].append(rmse_a)

            cands_a = [
                (self.en_grid[i][0], self.en_grid[i][1], i, float(np.mean(en_track_a_scores[i])))
                for i in range(len(self.en_grid))
            ]
            cands_b = [
                (self.en_grid[i][0], self.en_grid[i][1], i, float(np.mean(en_track_b_scores[i])))
                for i in range(len(self.en_grid))
            ]
            best_alpha_a, best_l1_a, best_idx_a = tie_break_elastic_net(cands_a)
            best_alpha_b, best_l1_b, best_idx_b = tie_break_elastic_net(cands_b)

            # Track A Outer Refit
            self._check_deadline()
            self.accounting.record_estimator_fit(1)
            en_out_a = ElasticNet(alpha=best_alpha_a, l1_ratio=best_l1_a, max_iter=self.config.max_iter, tol=self.config.tol)
            en_out_a.fit(X_out_tr, y_out_tr)
            non_zero_a = np.where(np.abs(en_out_a.coef_) > 1e-9)[0]
            out_sel_names_a = [out_tr_res.feature_names[i] for i in non_zero_a]

            if len(non_zero_a) == 0:
                yhat_va_a = np.full_like(y_out_va, np.mean(y_out_tr))
                diag_a = {"rank": 1, "nullity": 0, "effective_condition_number": 1.0}
            else:
                self.accounting.record_estimator_fit(1)
                final_fit_a = fit_ols_svd(X_out_tr[:, non_zero_a], y_out_tr, add_intercept=True)
                yhat_va_a = predict_ols(final_fit_a, X_out_va[:, non_zero_a])
                diag_res = compute_numerical_diagnostics(final_fit_a["design_matrix"])
                diag_a = {
                    "rank": diag_res["rank"],
                    "nullity": diag_res["nullity"],
                    "effective_condition_number": diag_res["condition_number_effective"],
                }

            rmse_va_a = math.sqrt(float(np.mean((y_out_va - yhat_va_a) ** 2)))
            ss_tot = float(np.sum((y_out_va - y_out_va.mean()) ** 2))
            r2_va_a = float(1.0 - np.sum((y_out_va - yhat_va_a) ** 2) / ss_tot) if ss_tot > 0 else float("nan")

            fold_results.append({
                "outer_fold": outer_fold_idx,
                "method": "elastic_net_cv",
                "track": "Track A",
                "selected_hyperparameter": {"alpha": best_alpha_a, "l1_ratio": best_l1_a, "grid_index": best_idx_a},
                "selected_feature_count": len(out_sel_names_a),
                "selected_feature_names": out_sel_names_a,
                "outer_val_rmse": rmse_va_a,
                "outer_val_r2": r2_va_a,
                "numerical_diagnostics": diag_a,
                "fit_accounting": {
                    "fold_estimator_fits": None,
                    "fold_preprocessor_fits": self.config.inner_splits + 1,
                },
                "convergence_status": "CONVERGED",
            })
            for row_id, act, pred in zip(outer_val_ids, y_out_va, yhat_va_a):
                oof_records.append({
                    "Id": row_id,
                    "OuterFold": outer_fold_idx,
                    "Method": "elastic_net_cv",
                    "Track": "Track A",
                    "ActualSalePrice": float(act),
                    "PredictedSalePrice": float(pred),
                })

            # Track B Outer Refit
            self._check_deadline()
            self.accounting.record_estimator_fit(1)
            en_out_b = ElasticNet(alpha=best_alpha_b, l1_ratio=best_l1_b, max_iter=self.config.max_iter, tol=self.config.tol)
            en_out_b.fit(X_out_tr, y_out_tr)
            yhat_va_b = en_out_b.predict(X_out_va)
            rmse_va_b = math.sqrt(float(np.mean((y_out_va - yhat_va_b) ** 2)))
            r2_va_b = float(1.0 - np.sum((y_out_va - yhat_va_b) ** 2) / ss_tot) if ss_tot > 0 else float("nan")
            non_zero_b = np.where(np.abs(en_out_b.coef_) > 1e-9)[0]
            out_sel_names_b = [out_tr_res.feature_names[i] for i in non_zero_b]

            fold_results.append({
                "outer_fold": outer_fold_idx,
                "method": "elastic_net_cv",
                "track": "Track B",
                "selected_hyperparameter": {"alpha": best_alpha_b, "l1_ratio": best_l1_b, "grid_index": best_idx_b},
                "selected_feature_count": len(out_sel_names_b),
                "selected_feature_names": out_sel_names_b,
                "outer_val_rmse": rmse_va_b,
                "outer_val_r2": r2_va_b,
                "numerical_diagnostics": {
                    "rank": len(non_zero_b),
                    "nullity": X_out_tr.shape[1] - len(non_zero_b),
                    "effective_condition_number": None,
                },
                "fit_accounting": {
                    "fold_estimator_fits": None,
                    "fold_preprocessor_fits": self.config.inner_splits + 1,
                },
                "convergence_status": "CONVERGED",
            })
            for row_id, act, pred in zip(outer_val_ids, y_out_va, yhat_va_b):
                oof_records.append({
                    "Id": row_id,
                    "OuterFold": outer_fold_idx,
                    "Method": "elastic_net_cv",
                    "Track": "Track B",
                    "ActualSalePrice": float(act),
                    "PredictedSalePrice": float(pred),
                })

        return {
            "outer_fold": outer_fold_idx,
            "results": fold_results,
            "oof_records": oof_records,
        }

    def run_nested_cv(
        self,
        dev_rows: Sequence[Mapping[str, str]],
        output_dir: Optional[Path] = None,
        run_id: Optional[str] = None,
        resume_checkpoint_dir: Optional[Path] = None,
        pipeline_factory: Callable[[], AmesDataPreparationPipeline] = AmesDataPreparationPipeline,
    ) -> Dict[str, Any]:
        """Execute full nested cross-validation across all outer folds with preflight checks and outputs."""
        # 0. Enforce B03 Fail-Closed: timeout must be positive and isolated worker enabled
        if self.config.timeout_seconds is not None:
            if self.config.timeout_seconds <= 0:
                raise ValueError("timeout_seconds must be positive if specified.")
            if not self.config.use_isolated_worker_process:
                raise RuntimeError("FAIL_CLOSED: Timed execution requires use_isolated_worker_process=True.")

        # 1. Conservative Preflight Budget Check
        est_req, prep_req = estimate_preflight_budget(self.config)
        if est_req > self.config.estimator_fit_cap:
            raise BudgetExceededError(
                f"Preflight check rejected: estimated {est_req} estimator fits exceeds cap {self.config.estimator_fit_cap}."
            )
        if prep_req > self.config.preprocessor_fit_cap:
            raise BudgetExceededError(
                f"Preflight check rejected: estimated {prep_req} preprocessor fits exceeds cap {self.config.preprocessor_fit_cap}."
            )

        # 2. Setup threadpool limits if configured
        thread_limit = 1 if self.config.single_thread else None

        # 3. Setup timeout deadline
        start_time = time.perf_counter()
        if self.config.timeout_seconds is not None:
            self.deadline = start_time + self.config.timeout_seconds
        else:
            self.deadline = None

        # 4. Verify output containment if output_dir is provided
        from housing_regression.modeling.p4b_artifacts import (
            assert_safe_private_containment,
            atomic_write_csv,
            atomic_write_json,
            compute_checkpoint_payload_digest,
            create_manifest,
            create_public_summary,
            verify_checkpoint_for_resume,
            write_durable_failure_json,
        )

        canonical_fp = compute_canonical_fingerprint(dev_rows)

        if output_dir is not None:
            output_dir = assert_safe_private_containment(Path(output_dir), repo_root=self.config.repo_root, run_id=run_id)
            output_dir.mkdir(parents=True, exist_ok=True)

        # 5. Handle resume checkpoint reading if requested
        completed_folds: Dict[int, Dict[str, Any]] = {}
        if resume_checkpoint_dir is not None:
            resume_dir = Path(resume_checkpoint_dir)
            import sklearn
            import pandas as pd
            import scipy
            env_vers = {
                "python": "3.12",
                "sklearn": sklearn.__version__,
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "scipy": scipy.__version__,
            }
            chk_files = list(sorted(resume_dir.glob("checkpoint_fold_*.json")))
            if not chk_files:
                raise CheckpointVerificationError(f"No checkpoint files found in resume directory '{resume_dir}'.")
            for chk_file in chk_files:
                with open(chk_file, "r", encoding="utf-8") as f:
                    chk_data = json.load(f)
                verify_checkpoint_for_resume(chk_data, canonical_fp, self.config, env_vers)
                k = chk_data["completed_outer_fold"]
                completed_folds[k] = chk_data

        def _execute_loop() -> Dict[str, Any]:
            n_rows = len(dev_rows)
            outer_folds = kfold_assignments(n_rows, self.config.outer_splits, self.config.outer_seed)

            all_fold_results: List[Dict[str, Any]] = []
            all_oof_records: List[Dict[str, Any]] = []
            run_status = "SUCCESS"
            exception_info: Optional[str] = None
            current_stage = "STARTUP"

            try:
                for k in range(self.config.outer_splits):
                    current_stage = f"OUTER_FOLD_{k}"
                    self._check_deadline()

                    # Check if already completed from resume checkpoint
                    if k in completed_folds:
                        chk_data = completed_folds[k]
                        all_fold_results.extend(chk_data["results"])
                        all_oof_records.extend(chk_data["oof_records"])
                        continue

                    tr_rows = [dict(dev_rows[i]) for i, f in enumerate(outer_folds) if f != k]
                    va_rows = [dict(dev_rows[i]) for i, f in enumerate(outer_folds) if f == k]

                    if self.config.use_isolated_worker_process and self.config.timeout_seconds is not None:
                        ctx = mp.get_context("spawn")
                        queue = ctx.Queue()
                        proc = ctx.Process(
                            target=_mp_worker_target,
                            args=(queue, self.config, k, tr_rows, va_rows, self.stall_mock_worker),
                        )
                        proc.start()
                        remaining_timeout = max(0.01, self.deadline - time.perf_counter()) if self.deadline else None
                        proc.join(timeout=remaining_timeout)

                        if proc.is_alive():
                            child_pid = proc.pid
                            proc.terminate()
                            proc.join(timeout=1.0)
                            if proc.is_alive():
                                proc.kill()
                                proc.join()
                            assert not proc.is_alive(), f"Orphan process detected! PID {child_pid}"
                            raise TimeoutExceededError(
                                f"Worker process for outer fold {k} (PID {child_pid}) exceeded timeout and was terminated."
                            )

                        if queue.empty():
                            raise RuntimeError(f"Worker process for outer fold {k} died without returning output.")

                        msg = queue.get()
                        if msg[0] == "EXCEPTION":
                            raise RuntimeError(f"Worker process error ({msg[1]}): {msg[2]}")
                        fold_output = msg[1]
                        self.accounting.record_estimator_fit(msg[2])
                        self.accounting.record_preprocessor_fit(msg[3])
                    else:
                        fold_output = self.execute_outer_fold(
                            outer_fold_idx=k,
                            outer_train_rows=tr_rows,
                            outer_val_rows=va_rows,
                            pipeline_factory=pipeline_factory,
                        )

                    all_fold_results.extend(fold_output["results"])
                    all_oof_records.extend(fold_output["oof_records"])

                    # Intermediate fold checkpoint if output_dir is specified
                    if output_dir is not None:
                        import sklearn
                        import pandas as pd
                        import scipy
                        payload_digest = compute_checkpoint_payload_digest(fold_output["results"], fold_output["oof_records"])
                        fold_chk = {
                            "run_id": run_id,
                            "completed_outer_fold": k,
                            "code_head_commit": self.config.code_head_commit,
                            "dataset_fingerprint": canonical_fp,
                            "payload_digest": payload_digest,
                            "results": fold_output["results"],
                            "oof_records": fold_output["oof_records"],
                            "run_config": {
                                "d_ceiling": self.config.d_ceiling,
                                "k_candidates": list(self.config.k_candidates),
                                "active_methods": self.config.active_methods or [
                                    "filter_pearson",
                                    "forward_sfs",
                                    "rfe_ridge",
                                    "lasso_cv",
                                    "elastic_net_cv",
                                ],
                            },
                            "metadata": {
                                "protocol_version": self.config.protocol_version,
                                "environment": {
                                    "python_version": "3.12",
                                    "sklearn_version": sklearn.__version__,
                                    "numpy_version": np.__version__,
                                    "pandas_version": pd.__version__,
                                    "scipy_version": scipy.__version__,
                                },
                                "data_boundary": {
                                    "outer_kfold": {"n_splits": self.config.outer_splits, "random_state": self.config.outer_seed},
                                    "inner_kfold": {"n_splits": self.config.inner_splits, "random_state": self.config.inner_seed},
                                },
                            },
                        }
                        chk_file = Path(output_dir) / f"checkpoint_fold_{k}.json"
                        atomic_write_json(fold_chk, chk_file)

            except Exception as exc:
                run_status = "FAILED"
                exception_info = f"{type(exc).__name__}: {str(exc)}"
                if output_dir is not None:
                    write_durable_failure_json(
                        target_dir=output_dir,
                        run_id=run_id or "p4b_run",
                        stage=current_stage,
                        code_head_commit=self.config.code_head_commit,
                        exception=exc,
                        accounting_summary={
                            "estimator_fits": self.accounting.estimator_fits,
                            "preprocessor_fits": self.accounting.preprocessor_fits,
                            "elapsed_seconds": time.perf_counter() - start_time,
                        },
                        config_summary={
                            "protocol_version": self.config.protocol_version,
                            "d_ceiling": self.config.d_ceiling,
                            "outer_splits": self.config.outer_splits,
                            "inner_splits": self.config.inner_splits,
                        },
                    )
                raise exc

            finally:
                elapsed_total = time.perf_counter() - start_time

            pairs_seen: Set[Tuple[str, str]] = set()
            for item in all_fold_results:
                pair = (item["method"], item["track"])
                pairs_seen.add(pair)

            aggregate_results: List[Dict[str, Any]] = []
            for method, track in sorted(pairs_seen):
                matches = [r for r in all_fold_results if r["method"] == method and r["track"] == track]
                rmses = [r["outer_val_rmse"] for r in matches]
                r2s = [r["outer_val_r2"] for r in matches]
                mean_rmse = float(np.mean(rmses))
                std_rmse = float(np.std(rmses, ddof=1)) if len(rmses) > 1 else 0.0
                mean_r2 = float(np.mean(r2s))

                aggregate_results.append({
                    "method": method,
                    "track": track,
                    "mean_outer_rmse": mean_rmse,
                    "std_outer_rmse": std_rmse,
                    "mean_outer_r2": mean_r2,
                    "total_estimator_fits": self.accounting.estimator_fits,
                    "total_preprocessor_fits": self.accounting.preprocessor_fits,
                    "fit_cap_status": "WITHIN_CAP" if run_status == "SUCCESS" else "FAILED",
                })

            summary = {
                "run_id": run_id,
                "status": run_status,
                "exception": exception_info,
                "config": {
                    "protocol_version": self.config.protocol_version,
                    "code_head_commit": self.config.code_head_commit,
                    "outer_splits": self.config.outer_splits,
                    "inner_splits": self.config.inner_splits,
                    "d_ceiling": self.config.d_ceiling,
                },
                "fit_accounting": {
                    "total_estimator_fits": self.accounting.estimator_fits,
                    "total_preprocessor_fits": self.accounting.preprocessor_fits,
                    "estimator_fit_cap": self.accounting.estimator_fit_cap,
                    "preprocessor_fit_cap": self.accounting.preprocessor_fit_cap,
                    "elapsed_seconds": elapsed_total,
                },
                "per_outer_fold_results": all_fold_results,
                "aggregate_results": aggregate_results,
            }

            # Wire outputs if output_dir provided
            if output_dir is not None:
                out_path = Path(output_dir)

                # 1. Private OOF CSV
                oof_path = out_path / "p4b_oof_predictions.csv"
                oof_fields = ["Id", "OuterFold", "Method", "Track", "ActualSalePrice", "PredictedSalePrice"]
                oof_sha, oof_size = atomic_write_csv(all_oof_records, oof_fields, oof_path)

                # 2. Public summary JSON
                pub_summary_data = create_public_summary(
                    config=self.config,
                    run_id=run_id or "p4b_run",
                    per_outer_fold_results=all_fold_results,
                    aggregate_results=aggregate_results,
                )
                pub_path = out_path / "p4b_public_summary.json"
                pub_sha, pub_size = atomic_write_json(pub_summary_data, pub_path)

                # 3. Private details JSON
                details_path = out_path / "p4b_private_details.json"
                det_sha, det_size = atomic_write_json(summary, details_path)

                # 4. Manifest JSON
                file_inv = [
                    {"relative_path": "p4b_oof_predictions.csv", "sha256": oof_sha, "byte_size": oof_size, "is_public": False},
                    {"relative_path": "p4b_public_summary.json", "sha256": pub_sha, "byte_size": pub_size, "is_public": True},
                    {"relative_path": "p4b_private_details.json", "sha256": det_sha, "byte_size": det_size, "is_public": False},
                ]
                manifest_data = create_manifest(
                    run_id=run_id or "p4b_run",
                    code_head_commit=self.config.code_head_commit,
                    canonical_dataset_sha256=canonical_fp,
                    file_inventory=file_inv,
                    development_rows=len(dev_rows),
                )
                atomic_write_json(manifest_data, out_path / "p4b_manifest.json")

            return {
                "summary": summary,
                "oof_records": all_oof_records,
            }

        if thread_limit is not None:
            with threadpoolctl.threadpool_limits(limits=thread_limit):
                return _execute_loop()
        else:
            return _execute_loop()
