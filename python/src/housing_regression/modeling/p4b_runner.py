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
import platform
import queue as queue_module
import re
import struct
import time
import unicodedata
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
from sklearn.linear_model import ElasticNet, Lasso, Ridge
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning
import threadpoolctl
from housing_regression.modeling.p4b_job import (
    assign_process_to_job,
    close_job_object,
    create_kill_on_close_job_object,
    terminate_job_object,
)

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
    fold_assignment_digest,
    kfold_assignments,
    load_development_rows,
    predict as predict_ols,
)

PROTOCOL_VERSION: str = "v1.0"
DEFAULT_D_CEILING: int = 300
DEFAULT_ESTIMATOR_FIT_CAP: int = 150000
DEFAULT_PREPROCESSOR_FIT_CAP: int = 200
WORKER_STARTUP_TIMEOUT_SECONDS: float = 10.0
DEFAULT_WORKER_MEMORY_LIMIT_BYTES: int = 2 * 1024 * 1024 * 1024
EXPECTED_DEVELOPMENT_ROWS: int = 1168
EXPECTED_DEVELOPMENT_INDEX_DIGEST: str = "3981ebb16dde1b26400a431ef7c5d318b970f7ede50f42390d8221300eb299f4"
EXPECTED_OUTER_FOLD_DIGEST: str = "7c9f1d00eb74d8a281ba41ed47d5ebbdbffa0513b4bb778b70d1571735ad6463"

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


def expected_method_pairs(config: "P4BConfig") -> List[Tuple[str, str]]:
    if config.active_pairs is not None:
        return sorted(tuple(pair) for pair in config.active_pairs)
    methods = set(config.active_methods or ("filter_pearson", "forward_sfs", "rfe_ridge", "lasso_cv", "elastic_net_cv"))
    return sorted(pair for pair in SUPPORTED_PAIRS if pair[0] in methods)


def active_methods_for_config(config: "P4BConfig") -> Set[str]:
    if config.active_pairs is not None:
        return {method for method, _track in expected_method_pairs(config)}
    return set(config.active_methods or ("filter_pearson", "forward_sfs", "rfe_ridge", "lasso_cv", "elastic_net_cv"))


def compute_fold_plan_digest(n_rows: int, config: "P4BConfig") -> str:
    """Digest exact outer and nested inner row-index assignments for this run."""
    outer = kfold_assignments(n_rows, config.outer_splits, config.outer_seed)
    plan = {"outer": outer, "inner": {}}
    for fold_idx in range(config.outer_splits):
        train_indices = [index for index, assigned in enumerate(outer) if assigned != fold_idx]
        inner_assignment = kfold_assignments(len(train_indices), config.inner_splits, config.inner_seed)
        plan["inner"][str(fold_idx)] = [
            {
                "train": [train_indices[i] for i, assigned in enumerate(inner_assignment) if assigned != inner_idx],
                "validation": [train_indices[i] for i, assigned in enumerate(inner_assignment) if assigned == inner_idx],
            }
            for inner_idx in range(config.inner_splits)
        ]
    return hashlib.sha256(json.dumps(plan, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


def verify_development_provenance(
    rows: Sequence[Mapping[str, str]],
    provenance: Optional[Mapping[str, Any]],
    config: "P4BConfig",
) -> Dict[str, Any]:
    """Fail closed unless production rows carry the frozen Phase-3 split provenance."""
    row_ids = [row.get(ID_COLUMN) for row in rows]
    row_id_digest = hashlib.sha256(
        json.dumps(row_ids, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if config.synthetic_test_mode:
        actual_fold_digest = (
            fold_assignment_digest(kfold_assignments(len(rows), config.outer_splits, config.outer_seed))
            if len(rows) >= config.outer_splits
            else None
        )
        return {
            "verified": False,
            "verification_status": "SYNTHETIC_UNVERIFIED",
            "development_rows": len(rows),
            "development_index_digest": None,
            "row_id_membership_digest": row_id_digest,
            "outer_fold_digest": actual_fold_digest,
        }

    if len(rows) != EXPECTED_DEVELOPMENT_ROWS:
        raise ValueError("Production input row count does not match frozen development membership.")
    if config.inner_splits != 3 or config.inner_seed != 1042:
        raise ValueError("Production inner-fold provenance must match the frozen P4-B protocol.")
    folds = kfold_assignments(len(rows), config.outer_splits, config.outer_seed)
    actual_fold_digest = fold_assignment_digest(folds)
    if config.outer_splits != 5 or config.outer_seed != 42 or actual_fold_digest != EXPECTED_OUTER_FOLD_DIGEST:
        raise ValueError("Production outer-fold provenance does not match the frozen P4-A assignment.")
    if not isinstance(provenance, Mapping):
        raise ValueError("Production input must come from the Phase-3 development loader.")
    required_provenance = {
        "labeled_rows_counted": 1460,
        "development_rows": EXPECTED_DEVELOPMENT_ROWS,
        "split_seed": 42,
        "val_fraction": 0.2,
        "development_index_digest": EXPECTED_DEVELOPMENT_INDEX_DIGEST,
        "source_basename": "train.csv",
        "id_uniqueness_verified": True,
        "unique_id_count": EXPECTED_DEVELOPMENT_ROWS,
        "row_id_membership_digest": row_id_digest,
        "dataset_fingerprint": compute_canonical_fingerprint(rows),
    }
    if any(provenance.get(key) != value for key, value in required_provenance.items()):
        raise ValueError("Phase-3 loader provenance does not match frozen development membership.")
    ids = [row.get(ID_COLUMN) for row in rows]
    if any(not isinstance(row_id, str) or not row_id for row_id in ids) or len(set(ids)) != EXPECTED_DEVELOPMENT_ROWS:
        raise ValueError("Production development input must contain unique nonempty row IDs.")
    return {
        "verified": True,
        "verification_status": "VERIFIED_MATCH",
        "development_rows": len(rows),
        "development_index_digest": EXPECTED_DEVELOPMENT_INDEX_DIGEST,
        "row_id_membership_digest": row_id_digest,
        "dataset_fingerprint": compute_canonical_fingerprint(rows),
        "outer_fold_digest": actual_fold_digest,
    }


def fit_and_capture_convergence(estimator: Any, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    """Fit an iterative sklearn estimator and report observed convergence warnings/iterations."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        estimator.fit(X, y)
    warning_count = sum(1 for item in caught if issubclass(item.category, ConvergenceWarning))
    n_iter = getattr(estimator, "n_iter_", None)
    if isinstance(n_iter, np.ndarray):
        n_iter = n_iter.tolist()
    elif isinstance(n_iter, np.generic):
        n_iter = n_iter.item()
    return {
        "convergence_status": "CONVERGENCE_WARNING" if warning_count else "CONVERGED",
        "convergence_warning_count": warning_count,
        "n_iter": n_iter,
    }


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
    timeout_seconds: Optional[float] = 300.0
    use_isolated_worker_process: bool = True
    repo_root: Optional[Path] = None
    active_methods: Optional[List[str]] = None  # None means all 5 methods
    active_pairs: Optional[List[Tuple[str, str]]] = None  # None means all 7 pairs
    max_worker_memory_bytes: int = DEFAULT_WORKER_MEMORY_LIMIT_BYTES
    synthetic_test_mode: bool = False

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
        if isinstance(self.max_worker_memory_bytes, bool) or not isinstance(self.max_worker_memory_bytes, int) or self.max_worker_memory_bytes <= 0:
            raise ValueError("max_worker_memory_bytes must be a positive integer.")
        valid_methods = {method for method, _track in SUPPORTED_PAIRS}
        if self.active_methods is not None and (not self.active_methods or not set(self.active_methods) <= valid_methods):
            raise ValueError("active_methods must contain only supported methods.")
        if self.active_pairs is not None:
            pair_tuples = [tuple(pair) for pair in self.active_pairs]
            if not pair_tuples or len(set(pair_tuples)) != len(pair_tuples) or not set(pair_tuples) <= set(SUPPORTED_PAIRS):
                raise ValueError("active_pairs must contain unique supported method-track pairs.")
            pair_methods = {method for method, _track in pair_tuples}
            if self.active_methods is not None and pair_methods != set(self.active_methods):
                raise ValueError("active_methods must exactly match the methods selected by active_pairs.")
            for method in ("lasso_cv", "elastic_net_cv"):
                selected_tracks = {track for pair_method, track in pair_tuples if pair_method == method}
                if selected_tracks and selected_tracks != {"Track A", "Track B"}:
                    raise ValueError("active_pairs must include both tracks for each regularized method.")


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

    active_methods = active_methods_for_config(config)

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
    ready_queue: Optional[Any] = None,
    spawn_descendant: bool = False,
    pipeline_factory: Optional[Callable[[], AmesDataPreparationPipeline]] = None,
    start_event: Optional[Any] = None,
    timing_ns: Optional[Any] = None,
) -> None:
    try:
        if timing_ns is not None:
            timing_ns[0] = time.perf_counter_ns()  # Worker target entry.
        if config.single_thread is not True:
            raise RuntimeError("Worker isolation requires single_thread=True.")
        # B03: Wait for start_event gate released only after parent assigns Job Object
        if start_event is not None:
            start_event.wait()
        if timing_ns is not None:
            timing_ns[1] = time.perf_counter_ns()  # Job-assigned start gate released.

        # B03: enforce single-thread limits strictly inside child worker
        thread_limit = 1
        with threadpoolctl.threadpool_limits(limits=thread_limit):
            descendant_pid = None
            if spawn_descendant:
                # Spawn a child worker process to verify process tree containment and termination
                sub_ctx = mp.get_context("spawn")
                sub_proc = sub_ctx.Process(target=_descendant_worker_target)
                sub_proc.start()
                descendant_pid = sub_proc.pid
                if timing_ns is not None and descendant_pid is not None:
                    timing_ns[4] = descendant_pid

            tp_info = threadpoolctl.threadpool_info()
            if stall_before_fit:
                # Confirm the worker has entered the stall before reporting readiness.
                if ready_queue is not None:
                    import numpy as _np
                    _ = _np.zeros((10, 10)) @ _np.zeros((10, 10))
                    stall_entered_ns = time.perf_counter_ns()
                    if timing_ns is not None:
                        timing_ns[2] = stall_entered_ns
                    time.sleep(0.05)
                    ready_sent_ns = time.perf_counter_ns()
                    if timing_ns is not None:
                        timing_ns[3] = ready_sent_ns
                    ready_queue.put({
                        "status": "READY",
                        "worker_pid": os.getpid(),
                        "descendant_pid": descendant_pid,
                        "thread_limits": [pool["num_threads"] for pool in tp_info],
                        "stall_entered_ns": stall_entered_ns,
                        "ready_sent_ns": ready_sent_ns,
                    })
                time.sleep(30.0)
            elif ready_queue is not None:
                ready_queue.put({
                    "status": "READY",
                    "worker_pid": os.getpid(),
                    "descendant_pid": descendant_pid,
                    "thread_limits": [pool["num_threads"] for pool in tp_info],
                    "ready_sent_ns": time.perf_counter_ns(),
                })

            runner = P4BRunner(config)
            kwargs = {}
            if pipeline_factory is not None:
                kwargs["pipeline_factory"] = pipeline_factory
            res = runner.execute_outer_fold(outer_fold_idx, outer_train_rows, outer_val_rows, **kwargs)
            queue.put(("SUCCESS", res, runner.accounting.estimator_fits, runner.accounting.preprocessor_fits))
    except Exception as exc:
        queue.put(("EXCEPTION", type(exc).__name__, str(exc)))


def _descendant_worker_target() -> None:
    """Descendant worker target to verify process tree termination under Job Object."""
    try:
        time.sleep(30.0)
    except Exception:
        pass


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
        self.ready_queue: Optional[Any] = None
        self.last_ready_msg: Optional[Dict[str, Any]] = None
        self.last_worker_timing: Dict[str, Any] = {}
        self.spawn_descendant: bool = False

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

        active_methods = active_methods_for_config(self.config)

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
            alpha_fit_convergence: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(len(self.lasso_alphas))}

            for part in inner_partitions:
                for idx, alpha in enumerate(self.lasso_alphas):
                    self._check_deadline()
                    self.accounting.record_estimator_fit(1)
                    lasso = Lasso(alpha=alpha, max_iter=self.config.max_iter, tol=self.config.tol)
                    alpha_fit_convergence[idx].append(fit_and_capture_convergence(lasso, part["X_tr"], part["y_tr"]))

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
            lasso_outer_a_convergence = fit_and_capture_convergence(lasso_out_a, X_out_tr, y_out_tr)
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
                "convergence_status": (
                    "CONVERGENCE_WARNING"
                    if lasso_outer_a_convergence["convergence_warning_count"]
                    or any(item["convergence_warning_count"] for item in alpha_fit_convergence[best_idx_a])
                    else "CONVERGED"
                ),
                "convergence_warning_count": lasso_outer_a_convergence["convergence_warning_count"]
                + sum(item["convergence_warning_count"] for item in alpha_fit_convergence[best_idx_a]),
                "outer_refit_n_iter": lasso_outer_a_convergence["n_iter"],
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
            lasso_outer_b_convergence = fit_and_capture_convergence(lasso_out_b, X_out_tr, y_out_tr)
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
                "convergence_status": (
                    "CONVERGENCE_WARNING"
                    if lasso_outer_b_convergence["convergence_warning_count"]
                    or any(item["convergence_warning_count"] for item in alpha_fit_convergence[best_idx_b])
                    else "CONVERGED"
                ),
                "convergence_warning_count": lasso_outer_b_convergence["convergence_warning_count"]
                + sum(item["convergence_warning_count"] for item in alpha_fit_convergence[best_idx_b]),
                "outer_refit_n_iter": lasso_outer_b_convergence["n_iter"],
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
            en_fit_convergence: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(len(self.en_grid))}

            for part in inner_partitions:
                for alpha, l1_ratio, idx in self.en_grid:
                    self._check_deadline()
                    self.accounting.record_estimator_fit(1)
                    en = ElasticNet(alpha=alpha, l1_ratio=l1_ratio, max_iter=self.config.max_iter, tol=self.config.tol)
                    en_fit_convergence[idx].append(fit_and_capture_convergence(en, part["X_tr"], part["y_tr"]))

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
            en_outer_a_convergence = fit_and_capture_convergence(en_out_a, X_out_tr, y_out_tr)
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
                "convergence_status": (
                    "CONVERGENCE_WARNING"
                    if en_outer_a_convergence["convergence_warning_count"]
                    or any(item["convergence_warning_count"] for item in en_fit_convergence[best_idx_a])
                    else "CONVERGED"
                ),
                "convergence_warning_count": en_outer_a_convergence["convergence_warning_count"]
                + sum(item["convergence_warning_count"] for item in en_fit_convergence[best_idx_a]),
                "outer_refit_n_iter": en_outer_a_convergence["n_iter"],
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
            en_outer_b_convergence = fit_and_capture_convergence(en_out_b, X_out_tr, y_out_tr)
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
                "convergence_status": (
                    "CONVERGENCE_WARNING"
                    if en_outer_b_convergence["convergence_warning_count"]
                    or any(item["convergence_warning_count"] for item in en_fit_convergence[best_idx_b])
                    else "CONVERGED"
                ),
                "convergence_warning_count": en_outer_b_convergence["convergence_warning_count"]
                + sum(item["convergence_warning_count"] for item in en_fit_convergence[best_idx_b]),
                "outer_refit_n_iter": en_outer_b_convergence["n_iter"],
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

    def run_nested_cv_from_training_csv(
        self,
        train_csv: Path,
        output_dir: Optional[Path] = None,
        run_id: Optional[str] = None,
        resume_checkpoint_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Load only the frozen development membership from the labeled training CSV, then run."""
        path = Path(train_csv)
        if path.name.lower() != "train.csv":
            raise ValueError("Production runner accepts only the authorized labeled train.csv source.")
        rows, provenance = load_development_rows(
            path, val_fraction=0.2, random_state=42, expected_total=1460, validate_id_uniqueness=True
        )
        provenance["source_basename"] = path.name
        provenance["dataset_fingerprint"] = compute_canonical_fingerprint(rows)
        provenance["row_id_membership_digest"] = hashlib.sha256(
            json.dumps([row[ID_COLUMN] for row in rows], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return self._run_nested_cv_with_provenance(
            rows,
            output_dir=output_dir,
            run_id=run_id,
            resume_checkpoint_dir=resume_checkpoint_dir,
            data_provenance=provenance,
        )

    def run_nested_cv(
        self,
        dev_rows: Sequence[Mapping[str, str]],
        output_dir: Optional[Path] = None,
        run_id: Optional[str] = None,
        resume_checkpoint_dir: Optional[Path] = None,
        pipeline_factory: Callable[[], AmesDataPreparationPipeline] = AmesDataPreparationPipeline,
        data_provenance: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Caller supplied mappings are assertions, not evidence of loader origin.
        # Only the CSV entrypoint may forward provenance to the internal runner.
        return self._run_nested_cv_with_provenance(
            dev_rows, output_dir, run_id, resume_checkpoint_dir, pipeline_factory, None
        )

    def _run_nested_cv_with_provenance(
        self,
        dev_rows: Sequence[Mapping[str, str]],
        output_dir: Optional[Path] = None,
        run_id: Optional[str] = None,
        resume_checkpoint_dir: Optional[Path] = None,
        pipeline_factory: Callable[[], AmesDataPreparationPipeline] = AmesDataPreparationPipeline,
        data_provenance: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            return self._run_nested_cv(
                dev_rows, output_dir, run_id, resume_checkpoint_dir, pipeline_factory, data_provenance
            )
        except Exception as exc:
            from housing_regression.modeling.p4b_artifacts import (
                assert_safe_private_containment,
                classify_error_category,
                write_durable_failure_json,
            )
            category = classify_error_category(exc, getattr(self, "_failure_stage", "STARTUP"))
            safe_target = None
            if output_dir is not None and run_id:
                try:
                    safe_target = assert_safe_private_containment(Path(output_dir), self.config.repo_root, run_id)
                    safe_target.mkdir(parents=True, exist_ok=True)
                    if not (safe_target / "p4b_failure.json").exists():
                        write_durable_failure_json(
                        safe_target, run_id, getattr(self, "_failure_stage", "STARTUP"), self.config.code_head_commit, exc,
                        {"estimator_fits": self.accounting.estimator_fits, "preprocessor_fits": self.accounting.preprocessor_fits},
                        {"protocol_version": self.config.protocol_version, "d_ceiling": self.config.d_ceiling,
                         "outer_splits": self.config.outer_splits, "inner_splits": self.config.inner_splits},
                        )
                except Exception:
                    safe_target = None
                    category = "SAFE_FAILURE_RECORD_UNAVAILABLE"
            message = f"P4B_RUN_FAILED:{category}"
            try:
                safe_exc = type(exc)(message)
            except Exception:
                safe_exc = RuntimeError(message)
            pending_safe_exc = safe_exc
        raise pending_safe_exc

    def _run_nested_cv(
        self,
        dev_rows: Sequence[Mapping[str, str]],
        output_dir: Optional[Path] = None,
        run_id: Optional[str] = None,
        resume_checkpoint_dir: Optional[Path] = None,
        pipeline_factory: Callable[[], AmesDataPreparationPipeline] = AmesDataPreparationPipeline,
        data_provenance: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute full nested cross-validation across all outer folds with preflight checks and outputs."""
        self._failure_stage = "PREFLIGHT"
        # 0. Enforce B03 Fail-Closed: timeout must be positive, single_thread=True, and isolated worker enabled
        if os.name != "nt":
            raise RuntimeError("FAIL_CLOSED: Win32 Job Object process isolation is required.")
        if self.config.timeout_seconds is None:
            raise ValueError("FAIL_CLOSED: timeout_seconds must be explicitly provided (cannot be None).")
        if isinstance(self.config.timeout_seconds, bool) or not math.isfinite(self.config.timeout_seconds) or self.config.timeout_seconds <= 0:
            raise ValueError(f"FAIL_CLOSED: timeout_seconds must be a positive finite float, got {self.config.timeout_seconds}.")
        if self.config.use_isolated_worker_process is not True:
            raise RuntimeError("FAIL_CLOSED: Timed execution requires use_isolated_worker_process=True.")
        if self.config.single_thread is not True:
            raise RuntimeError("FAIL_CLOSED: single_thread must be True.")

        input_provenance = verify_development_provenance(dev_rows, data_provenance, self.config)

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
        thread_limit = 1

        # 3. Setup timeout deadline
        start_time = time.perf_counter()
        if self.config.timeout_seconds is not None:
            # Reserve a separate finite allowance for Windows process bootstrap;
            # each ready worker still gets only timeout_seconds for execution.
            self.deadline = start_time + WORKER_STARTUP_TIMEOUT_SECONDS + self.config.timeout_seconds
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
            checkpoint_run_config,
        )

        canonical_fp = compute_canonical_fingerprint(dev_rows)

        if output_dir is not None:
            self._failure_stage = "PATH_VALIDATION"
            output_dir = assert_safe_private_containment(Path(output_dir), repo_root=self.config.repo_root, run_id=run_id)

        if resume_checkpoint_dir is not None and not run_id:
            raise CheckpointVerificationError("Resume requires a nonempty expected run_id.")
        if resume_checkpoint_dir is not None:
            self._failure_stage = "PATH_VALIDATION"
            resume_checkpoint_dir = assert_safe_private_containment(
                Path(resume_checkpoint_dir), repo_root=self.config.repo_root, run_id=run_id,
            )
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)

        outer_folds_for_identity = kfold_assignments(len(dev_rows), self.config.outer_splits, self.config.outer_seed)
        fold_plan_identity = compute_fold_plan_digest(len(dev_rows), self.config)

        # 5. Handle resume checkpoint reading if requested
        completed_folds: Dict[int, Dict[str, Any]] = {}
        if resume_checkpoint_dir is not None:
            resume_dir = Path(resume_checkpoint_dir)
            import sklearn
            import pandas as pd
            import scipy
            env_vers = {
                "python": platform.python_version(),
                "sklearn": sklearn.__version__,
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "scipy": scipy.__version__,
            }
            chk_files = list(sorted(resume_dir.glob("checkpoint_fold_*.json")))
            if not chk_files:
                raise CheckpointVerificationError(f"No checkpoint files found in resume directory '{resume_dir}'.")
            for chk_file in chk_files:
                # Extract expected fold idx from filename
                fold_match = re.search(r"checkpoint_fold_(\d+)\.json$", chk_file.name)
                expected_fold_idx = int(fold_match.group(1)) if fold_match else None
                with open(chk_file, "r", encoding="utf-8") as f:
                    chk_data = json.load(f)
                verify_checkpoint_for_resume(
                    chk_data,
                    expected_fingerprint=canonical_fp,
                    config=self.config,
                    env_versions=env_vers,
                    expected_run_id=run_id,
                    expected_fold_idx=expected_fold_idx,
                    expected_fold_plan_digest=fold_plan_identity,
                    expected_oof_ids=[str(dev_rows[i][ID_COLUMN]) for i, assigned in enumerate(outer_folds_for_identity) if assigned == expected_fold_idx],
                    expected_data_provenance=input_provenance,
                )
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
                    self._failure_stage = current_stage
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
                        worker_ready_queue = self.ready_queue if self.ready_queue is not None else ctx.Queue()
                        start_event = ctx.Event()
                        worker_timing_ns = ctx.Array("q", 5)
                        self.last_worker_timing = {
                            "fold": k,
                            "configured_timeout_seconds": self.config.timeout_seconds,
                            "startup_allowance_seconds": WORKER_STARTUP_TIMEOUT_SECONDS,
                            "overall_deadline_ns": int(self.deadline * 1_000_000_000),
                            "parent_launch_ns": time.perf_counter_ns(),
                        }
                        proc = ctx.Process(
                            target=_mp_worker_target,
                            args=(
                                queue,
                                self.config,
                                k,
                                tr_rows,
                                va_rows,
                                self.stall_mock_worker,
                                worker_ready_queue,
                                self.spawn_descendant,
                                pipeline_factory if pipeline_factory is not AmesDataPreparationPipeline else None,
                                start_event,
                                worker_timing_ns,
                            ),
                        )
                        proc.start()
                        self.last_worker_timing["parent_start_return_ns"] = time.perf_counter_ns()
                        self.last_worker_timing["worker_pid"] = proc.pid

                        # Windows: Enclose worker process in kill-on-close Job Object before releasing start_event
                        worker_job = None
                        if os.name == "nt":
                            try:
                                worker_job = create_kill_on_close_job_object(self.config.max_worker_memory_bytes)
                                import ctypes
                                from housing_regression.modeling.p4b_job import _get_kernel32
                                kernel32 = _get_kernel32()
                                h_proc = kernel32.OpenProcess(0x1F0FFF, False, proc.pid)
                                if not h_proc:
                                    raise RuntimeError(f"OpenProcess failed for PID {proc.pid}: error {ctypes.get_last_error()}")
                                try:
                                    assign_process_to_job(worker_job, h_proc)
                                finally:
                                    kernel32.CloseHandle(h_proc)
                            except Exception:
                                # Fail closed: kill worker immediately and raise before any fitting occurs
                                proc.terminate()
                                proc.join(timeout=1.0)
                                if proc.is_alive():
                                    proc.kill()
                                    proc.join(timeout=1.0)
                                if proc.is_alive():
                                    raise RuntimeError("FAIL_CLOSED: worker termination could not be verified.") from None
                                if worker_job:
                                    close_job_object(worker_job)
                                raise RuntimeError("FAIL_CLOSED: Job Object installation failed.") from None

                        # Release start_event so worker can now proceed knowing it's protected by Job Object
                        start_event.set()
                        self.last_worker_timing["parent_gate_release_ns"] = time.perf_counter_ns()

                        try:
                            worker_deadline = min(
                                self.deadline,
                                time.perf_counter() + self.config.timeout_seconds,
                            )
                            # Startup allowance is enforced separately on every worker path.
                            readiness_deadline = min(
                                self.deadline,
                                time.perf_counter() + WORKER_STARTUP_TIMEOUT_SECONDS,
                            )
                            readiness_remaining = readiness_deadline - time.perf_counter()
                            if readiness_remaining <= 0:
                                self.last_worker_timing["parent_timeout_ns"] = time.perf_counter_ns()
                                raise TimeoutExceededError("Worker readiness exceeded the configured deadline.")
                            try:
                                ready_msg = worker_ready_queue.get(timeout=readiness_remaining)
                                if not isinstance(ready_msg, Mapping) or ready_msg.get("status") != "READY":
                                    raise RuntimeError("Worker failed the readiness contract.")
                                self.last_ready_msg = ready_msg
                                self.last_worker_timing["parent_ready_received_ns"] = time.perf_counter_ns()
                                worker_deadline = min(
                                    self.deadline,
                                    time.perf_counter() + self.config.timeout_seconds,
                                )
                                self.last_worker_timing["worker_execution_deadline_ns"] = int(
                                    worker_deadline * 1_000_000_000
                                )
                            except queue_module.Empty:
                                self.last_worker_timing["parent_timeout_ns"] = time.perf_counter_ns()
                                raise TimeoutExceededError("Worker readiness exceeded the configured deadline.") from None

                            remaining_timeout = worker_deadline - time.perf_counter()
                            if remaining_timeout <= 0:
                                self.last_worker_timing["parent_timeout_ns"] = time.perf_counter_ns()
                                raise TimeoutExceededError("Worker startup exceeded the configured deadline.")
                            proc.join(timeout=remaining_timeout)

                            if proc.is_alive():
                                self.last_worker_timing["parent_timeout_ns"] = time.perf_counter_ns()
                                raise TimeoutExceededError("Worker exceeded the configured deadline.")

                            result_remaining = worker_deadline - time.perf_counter()
                            if result_remaining <= 0:
                                self.last_worker_timing["parent_timeout_ns"] = time.perf_counter_ns()
                                raise TimeoutExceededError("Worker result exceeded the configured deadline.")
                            try:
                                msg = queue.get(timeout=result_remaining)
                            except queue_module.Empty:
                                raise RuntimeError("Worker exited without returning output.") from None
                            if not isinstance(msg, tuple) or not msg:
                                raise RuntimeError("Worker returned an invalid result envelope.")
                            if msg[0] == "EXCEPTION" and len(msg) == 3:
                                raise RuntimeError(f"Worker process error ({msg[1]}): {msg[2]}")
                            if not isinstance(msg, tuple) or len(msg) != 4 or msg[0] != "SUCCESS":
                                raise RuntimeError("Worker returned an invalid result envelope.")
                            fold_output = msg[1]
                            self.accounting.record_estimator_fit(msg[2])
                            self.accounting.record_preprocessor_fit(msg[3])
                        finally:
                            cleanup_verified = True
                            if worker_job:
                                self.last_worker_timing["job_close_start_ns"] = time.perf_counter_ns()
                                try:
                                    close_job_object(worker_job)
                                except Exception:
                                    try:
                                        terminate_job_object(worker_job)
                                    except Exception:
                                        cleanup_verified = False
                                    else:
                                        try:
                                            close_job_object(worker_job)
                                        except Exception:
                                            cleanup_verified = False
                                worker_job = None
                                self.last_worker_timing["job_close_end_ns"] = time.perf_counter_ns()
                            try:
                                proc.join(timeout=1.0)
                            except Exception:
                                cleanup_verified = False
                            try:
                                worker_alive = proc.is_alive()
                            except Exception:
                                cleanup_verified = False
                                worker_alive = True
                            if worker_alive:
                                try:
                                    self.last_worker_timing["terminate_requested_ns"] = time.perf_counter_ns()
                                    proc.terminate()
                                    proc.join(timeout=1.0)
                                except Exception:
                                    cleanup_verified = False
                                try:
                                    worker_alive = proc.is_alive()
                                except Exception:
                                    cleanup_verified = False
                                    worker_alive = True
                            if worker_alive:
                                try:
                                    self.last_worker_timing["kill_requested_ns"] = time.perf_counter_ns()
                                    proc.kill()
                                    proc.join(timeout=1.0)
                                except Exception:
                                    cleanup_verified = False
                                try:
                                    worker_alive = proc.is_alive()
                                except Exception:
                                    cleanup_verified = False
                                    worker_alive = True
                            if worker_alive or not cleanup_verified:
                                raise RuntimeError("FAIL_CLOSED: worker process-tree termination could not be verified.") from None
                            self.last_worker_timing["parent_worker_exit_verified_ns"] = time.perf_counter_ns()
                            self.last_worker_timing["worker_target_entry_ns"] = worker_timing_ns[0] or None
                            self.last_worker_timing["worker_gate_release_ns"] = worker_timing_ns[1] or None
                            self.last_worker_timing["worker_stall_entered_ns"] = worker_timing_ns[2] or None
                            self.last_worker_timing["worker_ready_sent_ns"] = worker_timing_ns[3] or None
                            self.last_worker_timing["descendant_pid"] = worker_timing_ns[4] or None
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
                            "fold_plan_digest": fold_plan_identity,
                            "results": fold_output["results"],
                            "oof_records": fold_output["oof_records"],
                            "run_config": checkpoint_run_config(self.config),
                            "metadata": {
                                "protocol_version": self.config.protocol_version,
                                "environment": {
                        "python_version": platform.python_version(),
                                    "sklearn_version": sklearn.__version__,
                                    "numpy_version": np.__version__,
                                    "pandas_version": pd.__version__,
                                    "scipy_version": scipy.__version__,
                                },
                                "data_boundary": {
                                    "outer_kfold": {"n_splits": self.config.outer_splits, "random_state": self.config.outer_seed},
                                    "inner_kfold": {"n_splits": self.config.inner_splits, "random_state": self.config.inner_seed},
                                    **input_provenance,
                                },
                            },
                        }
                        chk_file = Path(output_dir) / f"checkpoint_fold_{k}.json"
                        atomic_write_json(fold_chk, chk_file)

            except Exception as exc:
                run_status = "FAILED"
                exception_info = f"{type(exc).__name__}: {str(exc)}"
                raise

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
                "input_provenance": input_provenance,
                "exception": exception_info,
                "config": {
                    "protocol_version": self.config.protocol_version,
                    "code_head_commit": self.config.code_head_commit,
                    "outer_splits": self.config.outer_splits,
                    "inner_splits": self.config.inner_splits,
                    "d_ceiling": self.config.d_ceiling,
                    "max_worker_memory_bytes": self.config.max_worker_memory_bytes,
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
                    dataset_fingerprint_verified=input_provenance["verified"],
                    development_rows=input_provenance["development_rows"],
                    outer_fold_digest=input_provenance["outer_fold_digest"],
                    digest_provenance=input_provenance["verification_status"],
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
                    outer_fold_digest_expected=input_provenance["outer_fold_digest"],
                    verification_status=input_provenance["verification_status"],
                )
                atomic_write_json(manifest_data, out_path / "p4b_manifest.json")

            return {
                "summary": summary,
                "oof_records": all_oof_records,
            }

        with threadpoolctl.threadpool_limits(limits=thread_limit):
            return _execute_loop()
