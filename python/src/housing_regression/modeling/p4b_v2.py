"""Pure P4-B v2 fold evaluation and run-scoped control contracts.

This module does not create, signal, or inspect OS processes. Runtime process
containment remains the responsibility of the existing fail-closed Runner and
the separately authorized Phase C safety gate.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from sklearn.feature_selection import RFE, mutual_info_regression
from sklearn.linear_model import ElasticNet, Lasso, Ridge
from sklearn.preprocessing import StandardScaler

from housing_regression.data_prep.constants import (
    ALL_PREDICTOR_COLUMNS,
    NOMINAL_COLUMNS,
    ORDINAL_COLUMNS,
)
from housing_regression.data_prep.pipeline import AmesDataPreparationPipeline
from housing_regression.modeling.ols_cv import (
    compute_numerical_diagnostics,
    fit_ols_svd,
    predict as predict_ols,
)

METHOD_ORDER = ("pearson", "mutual_information", "lasso", "elastic_net", "ridge_rfe")
K_GRID = (2, 3, 5, 10, 20)
PENALTY_ALPHAS = (0.1, 1.0, 10.0, 100.0)
ELASTIC_NET_L1_RATIOS = (0.2, 0.5, 0.8)

STRUCTURAL_SOURCES = {
    "HasGarage": ("GarageType",),
    "HasBasement": ("BsmtQual", "TotalBsmtSF"),
    "HasFireplace": ("Fireplaces", "FireplaceQu"),
    "HasPool": ("PoolArea", "PoolQC"),
    "HasFence": ("Fence",),
    "HasAlley": ("Alley",),
    "HasMiscFeature": ("MiscFeature",),
    "MasVnrType_is_missing": ("MasVnrType",),
    "MasVnrArea_is_missing": ("MasVnrArea",),
}
if any(source not in ALL_PREDICTOR_COLUMNS for sources in STRUCTURAL_SOURCES.values() for source in sources):
    raise RuntimeError("The Phase 4 lineage map contains a source outside the approved Phase 3 predictor whitelist.")


class LineageResolutionError(ValueError):
    """Raised when a transformed feature cannot be tied to approved raw inputs."""


def task_specs(config: Any) -> list[tuple[str, dict[str, Any]]]:
    """Return the complete ordered set of primary fold task identities."""
    active = set(config.active_methods or METHOD_ORDER)
    if config.active_pairs is not None:
        active = {method for method, _track in config.active_pairs if method != "ols_baseline"}
    specs: list[tuple[str, dict[str, Any]]] = [("ols_baseline", {"features": "all"})]
    for method in ("pearson", "mutual_information"):
        if method in active:
            specs.extend((method, {"k": k, "candidate_order": i})
                         for i, k in enumerate(config.k_candidates))
    if "ridge_rfe" in active:
        specs.extend(("ridge_rfe", {"k": k, "candidate_order": i})
                     for i, k in enumerate(config.k_candidates))
    if "lasso" in active:
        specs.extend(("lasso", {"alpha": alpha, "candidate_order": i})
                     for i, alpha in enumerate(PENALTY_ALPHAS))
    if "elastic_net" in active:
        index = 0
        for alpha in PENALTY_ALPHAS:
            for l1_ratio in ELASTIC_NET_L1_RATIOS:
                specs.append(("elastic_net", {"alpha": alpha, "l1_ratio": l1_ratio,
                                              "candidate_order": index}))
                index += 1
    return specs


def canonical_digest(value: Any) -> str:
    """Return a stable SHA-256 digest for JSON-compatible run identity data."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_task_id(run_id: str, method: str, candidate: Mapping[str, Any], fold: int) -> str:
    """Create a deterministic, run-unique identity for one method/config/fold task."""
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", run_id):
        raise ValueError("run_id must be a canonical nonempty identifier.")
    if method not in METHOD_ORDER and method != "ols_baseline":
        raise ValueError("Unsupported method identity.")
    if isinstance(fold, bool) or not isinstance(fold, int) or fold < 0:
        raise ValueError("fold must be a nonnegative integer.")
    return "task_" + canonical_digest({"run_id": run_id, "method": method, "candidate": dict(candidate), "fold": fold})[:32]


def task_config_hash(config: Any, method: str, candidate: Mapping[str, Any]) -> str:
    """Digest every fixed selection choice for one candidate task."""
    return canonical_digest({
        "protocol_version": config.protocol_version,
        "method": method,
        "candidate": dict(candidate),
        "k_candidates": list(config.k_candidates),
        "alpha_grid": list(PENALTY_ALPHAS),
        "elastic_net_l1_ratios": list(ELASTIC_NET_L1_RATIOS),
        "outer_splits": config.outer_splits,
        "outer_seed": config.outer_seed,
        "d_ceiling": config.d_ceiling,
        "max_iter": config.max_iter,
        "tol": config.tol,
        "active_methods": sorted(
            {method for method, _track in config.active_pairs if method != "ols_baseline"}
        ) if config.active_pairs is not None else sorted(config.active_methods or METHOD_ORDER),
    })


def resolve_feature_lineage(feature_name: str) -> dict[str, Any]:
    """Resolve an encoded feature to whitelisted raw inputs; fail closed on unknowns."""
    if feature_name in STRUCTURAL_SOURCES:
        sources = list(STRUCTURAL_SOURCES[feature_name])
        return {"encoded_name": feature_name, "raw_source_columns": sources,
                "is_derived": True, "encoding_type": "derived_indicator",
                "provenance_status": "RESOLVED",
                "direct_raw_sources": [], "derived_dependencies": sources}

    if feature_name in ALL_PREDICTOR_COLUMNS:
        kind = "ordinal" if feature_name in ORDINAL_COLUMNS else "numeric"
        return {"encoded_name": feature_name, "raw_source_columns": [feature_name],
                "is_derived": False, "encoding_type": kind,
                "provenance_status": "RESOLVED",
                "direct_raw_sources": [feature_name], "derived_dependencies": []}

    # Nominal values may themselves contain underscores, so resolve by the
    # longest approved raw-column prefix and require a nonempty encoded level.
    for source in sorted(NOMINAL_COLUMNS, key=len, reverse=True):
        prefix = source + "_"
        if feature_name.startswith(prefix) and len(feature_name) > len(prefix):
            return {"encoded_name": feature_name, "raw_source_columns": [source],
                    "is_derived": False, "encoding_type": "one_hot",
                    "provenance_status": "RESOLVED",
                    "direct_raw_sources": [source], "derived_dependencies": []}
    raise LineageResolutionError(f"No approved raw source is known for encoded feature {feature_name!r}.")


def validate_process_identity(identity: Mapping[str, Any]) -> tuple[int, int, int]:
    """Validate the tuple required before a later-phase process action.

    This is a pure validator only. It never opens a process, sends a signal, or
    verifies that a supplied identity currently belongs to a live process.
    """
    pid, ppid = identity.get("pid"), identity.get("ppid")
    start = identity.get("creation_time_ns")
    if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in (pid, ppid, start)):
        raise ValueError("Process identity requires positive pid, ppid, and creation_time_ns integers.")
    return pid, ppid, start


def require_matching_process_identity(
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> tuple[int, int, int]:
    """Require exact PID, parent PID, and creation-time identity agreement."""
    expected_tuple = validate_process_identity(expected)
    observed_tuple = validate_process_identity(observed)
    if expected_tuple != observed_tuple:
        raise ValueError("Process identity changed; refusing any control action.")
    return expected_tuple


@dataclass
class RunControlState:
    """Run-scoped cooperative task admission; no OS process actions."""

    run_id: str
    status: str = "CREATED"
    frozen: bool = False
    stop_requested: bool = False
    shared_admission_flag: Any = None
    _lock: Any = field(default_factory=threading.RLock, repr=False, compare=False)
    _admitted_task_ids: set[str] = field(default_factory=set, init=False, repr=False, compare=False)

    def _shared_frozen(self) -> bool:
        flag = self.shared_admission_flag
        if flag is None:
            return False
        with flag.get_lock():
            return bool(flag.value)

    def admit_task(self, task_id: str) -> bool:
        """Atomically admit one not-yet-started task unless freeze/stop already won."""
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("Task admission requires a nonempty task_id.")
        with self._lock:
            if self.frozen or task_id in self._admitted_task_ids:
                return False
            flag = self.shared_admission_flag
            if flag is None:
                self._admitted_task_ids.add(task_id)
                return True
            with flag.get_lock():
                if flag.value:
                    self.frozen = True
                    return False
                self._admitted_task_ids.add(task_id)
                return True

    def begin_run(self, run_id: str, shared_admission_flag: Any) -> bool:
        """Bind a shared worker gate atomically with respect to freeze/stop requests."""
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("Run admission requires a nonempty run_id.")
        with self._lock:
            if self.frozen or self._shared_frozen():
                return False
            self.run_id = run_id
            self.status = "RUNNING"
            self.shared_admission_flag = shared_admission_flag
            self._admitted_task_ids.clear()
            return True

    def status_snapshot(self) -> dict[str, Any]:
        shared_frozen = self._shared_frozen()
        return {"run_id": self.run_id, "status": self.status,
                "frozen": self.frozen or shared_frozen,
                "stop_requested": self.stop_requested}

    def freeze(self) -> dict[str, Any]:
        with self._lock:
            flag = self.shared_admission_flag
            if flag is None:
                self.frozen = True
            else:
                with flag.get_lock():
                    flag.value = 1
                    self.frozen = True
            if self.status not in {"COMPLETED", "FAILED", "STOPPED"}:
                self.status = "FROZEN"
            return self.status_snapshot()

    def stop_all(self) -> dict[str, Any]:
        """Freeze admissions and record stop intent for Phase C to implement safely."""
        with self._lock:
            flag = self.shared_admission_flag
            if flag is None:
                self.frozen = True
            else:
                with flag.get_lock():
                    flag.value = 1
                    self.frozen = True
            self.stop_requested = True
            if self.status not in {"COMPLETED", "FAILED", "STOPPED"}:
                self.status = "STOP_REQUESTED"
            return self.status_snapshot()


def _metric_values(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    if not np.isfinite(y_pred).all():
        raise ValueError("Nonfinite predictions invalidate this candidate.")
    residual = y_true - y_pred
    total = float(np.sum((y_true - y_true.mean()) ** 2))
    return {
        "rmse": float(math.sqrt(float(np.mean(residual ** 2)))),
        "mae": float(np.mean(np.abs(residual))),
        "r2": float(1.0 - float(np.sum(residual ** 2)) / total) if total > 0 else None,
    }


def rank_features_by_score(
    scores: Sequence[float], feature_names: Sequence[str], *,
    score_kind: str,
    constant_feature_mask: Sequence[bool] | None = None,
    evidence_limit: int = 20,
) -> tuple[list[int], dict[str, Any]]:
    """Rank usable scores first; record nonfinite and constant Pearson features compactly."""
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1 or len(values) != len(feature_names):
        raise ValueError("Feature score vector must align with feature names.")
    if score_kind not in {"pearson", "mutual_information"}:
        raise ValueError("score_kind must be pearson or mutual_information.")
    if isinstance(evidence_limit, bool) or not isinstance(evidence_limit, int) or evidence_limit < 0:
        raise ValueError("evidence_limit must be a nonnegative integer.")

    finite_mask = np.isfinite(values)
    invalid_mask = ~finite_mask
    if constant_feature_mask is None:
        constant_mask = np.zeros(len(values), dtype=bool)
    else:
        constant_mask = np.asarray(constant_feature_mask, dtype=bool)
        if constant_mask.ndim != 1 or len(constant_mask) != len(values):
            raise ValueError("Constant-feature mask must align with feature names.")
    if score_kind == "pearson":
        invalid_mask |= constant_mask

    valid_indices = [i for i in range(len(values)) if not invalid_mask[i]]
    invalid_indices = [i for i in range(len(values)) if invalid_mask[i]]
    ranked = sorted(valid_indices, key=lambda i: (-float(values[i]), str(feature_names[i])))
    ranked.extend(sorted(invalid_indices, key=lambda i: str(feature_names[i])))

    invalid_names = sorted(str(feature_names[i]) for i in invalid_indices)
    reasons = []
    if bool((~finite_mask).any()):
        reasons.append("NONFINITE")
    if score_kind == "pearson" and bool(constant_mask.any()):
        reasons.append("CONSTANT_FEATURE")
    return ranked, {
        "score_invalid": bool(reasons),
        "score_invalid_reason": "+".join(reasons) if reasons else None,
        "score_kind": score_kind,
        "score_count": len(values),
        "finite_score_count": int(finite_mask.sum()),
        "constant_feature_count": int(constant_mask.sum()) if score_kind == "pearson" else 0,
        "invalid_score_count": len(invalid_names),
        "invalid_score_features": invalid_names[:evidence_limit],
        "invalid_score_features_truncated": len(invalid_names) > evidence_limit,
        "rank_tiebreak": "encoded_feature_name_ascending",
    }


def _package_versions() -> dict[str, str]:
    import pandas
    import scipy
    import sklearn

    return {
        "python": __import__("platform").python_version(),
        "sklearn": sklearn.__version__,
        "numpy": np.__version__,
        "pandas": pandas.__version__,
        "scipy": scipy.__version__,
    }


def _scale_for_penalty(X_train: np.ndarray, X_val: np.ndarray, names: Sequence[str]) -> tuple[np.ndarray, np.ndarray]:
    """Scale continuous/ordinal columns on training rows; preserve binary indicators."""
    binary = set(STRUCTURAL_SOURCES)
    scale = [i for i, name in enumerate(names)
             if name not in binary and not name.endswith("_is_missing")
             and not any(name.startswith(col + "_") for col in NOMINAL_COLUMNS)]
    tr, va = X_train.copy(), X_val.copy()
    if scale:
        scaler = StandardScaler()
        tr[:, scale] = scaler.fit_transform(tr[:, scale])
        va[:, scale] = scaler.transform(va[:, scale])
    return tr, va


def evaluate_fold(
    config: Any,
    fold: int,
    train_rows: Sequence[Mapping[str, Any]],
    val_rows: Sequence[Mapping[str, Any]],
    pipeline_factory: Callable[[], AmesDataPreparationPipeline] = AmesDataPreparationPipeline,
    accounting: Any = None,
    check_deadline: Callable[[], None] | None = None,
    control_state: RunControlState | None = None,
) -> dict[str, Any]:
    """Evaluate one fixed development fold with a single training-only fit."""
    if check_deadline:
        check_deadline()
    if accounting:
        accounting.record_preprocessor_fit()
    pipeline = pipeline_factory()
    train = pipeline.fit_transform(list(train_rows), split_name=f"fold{fold}_train")
    val = pipeline.transform(list(val_rows), split_name=f"fold{fold}_val")
    names = list(train.feature_names)
    Xtr, Xva = train.to_numpy(), val.to_numpy()
    ytr, yva = np.asarray(train.y, dtype=np.float64), np.asarray(val.y, dtype=np.float64)
    if Xtr.shape[1] > config.d_ceiling:
        raise ValueError(f"Observed feature dimension {Xtr.shape[1]} exceeds {config.d_ceiling}.")
    scaled_tr, scaled_va = _scale_for_penalty(Xtr, Xva, names)
    lineage = {name: resolve_feature_lineage(name) for name in names}
    tasks: list[dict[str, Any]] = []
    oof: list[dict[str, Any]] = []
    completed = set(getattr(config, "completed_task_ids", ()) or ())

    def admit_candidate(method: str, candidate: Mapping[str, Any]) -> bool:
        task_id = make_task_id(config.current_run_id, method, candidate, fold)
        selected = getattr(config, "selected_task_ids", None)
        if selected is not None and task_id not in selected:
            return False
        if task_id in completed:
            return False
        if control_state is not None and not control_state.admit_task(task_id):
            raise RuntimeError("TASK_ADMISSION_CLOSED: candidate task was not admitted.")
        return True

    def record(method: str, candidate: Mapping[str, Any], selected_idx: Sequence[int],
               pred: np.ndarray, valid: bool = True, invalid_reason: str | None = None,
               native_pred: np.ndarray | None = None, convergence: str = "CONVERGED",
               fit_count: int = 1, duration_seconds: float = 0.0,
               score_evidence: Mapping[str, Any] | None = None,
               ols_diagnostics: Mapping[str, Any] | None = None) -> None:
        if check_deadline:
            check_deadline()
        selected_names = [names[i] for i in selected_idx]
        selected_lineage = [lineage[name] for name in selected_names]
        raw_sources = sorted({source for entry in selected_lineage for source in entry["raw_source_columns"]})
        row = {
            "method": method,
            "track": "baseline" if method == "ols_baseline" else "primary",
            "primary_track": "all_features_ols" if method == "ols_baseline" else "selected_to_ols",
            "candidate": dict(candidate),
            "fold": fold,
            "seed": config.outer_seed,
            "git_sha": config.code_head_commit,
            "run_id": config.current_run_id,
            "data_digest": config.current_data_digest,
            "fold_digest": config.current_fold_digest,
            "config_hash": task_config_hash(config, method, candidate),
            "package_versions": _package_versions(),
            "encoded_count": len(selected_names),
            "raw_count": len(raw_sources),
            "selected_encoded_names": selected_names,
            "selected_raw_sources": raw_sources,
            "feature_lineage": selected_lineage,
            "primary_valid": bool(valid),
            "status": "COMPLETED" if valid else "INVALID",
            "invalid_reason": invalid_reason,
            "convergence_status": convergence,
            "warning": convergence if convergence != "CONVERGED" else None,
            "fit_count": fit_count,
            "duration_seconds": max(0.0, float(duration_seconds)),
            "rank_or_score": None,
            "coef_or_importance": None,
            "score_evidence": dict(score_evidence) if score_evidence is not None else None,
            "ols_diagnostics": dict(ols_diagnostics) if ols_diagnostics is not None else {
                "status": "NOT_COMPUTED",
                "reason": "PRIMARY_OLS_NOT_FIT",
                "rank": None,
                "nullity": None,
                "condition_number": None,
                "condition_number_effective": None,
                "condition_number_full": None,
                "tolerance": None,
            },
        }
        row.update(_metric_values(yva, pred) if valid else {"rmse": None, "mae": None, "r2": None})
        if native_pred is not None:
            try:
                row["native_diagnostic"] = _metric_values(yva, native_pred)
            except ValueError:
                row["native_diagnostic"] = {"status": "INVALID"}
        row["task_id"] = make_task_id(config.current_run_id, method, candidate, fold)
        tasks.append(row)
        for row_id, actual, predicted in zip(val.ids, yva, pred):
            oof.append({"Id": row_id, "fold": fold, "task_id": row["task_id"],
                        "method": method, "track": row["track"], "actual": float(actual),
                        "predicted": float(predicted) if valid else None})
        if config.current_checkpoint_dir:
            from housing_regression.modeling.p4b_artifacts import (
                assert_safe_private_containment,
                atomic_write_json,
                create_task_checkpoint,
            )

            checkpoint_root = assert_safe_private_containment(
                config.current_checkpoint_dir,
                repo_root=config.repo_root,
                run_id=config.current_run_id,
            )
            checkpoint = create_task_checkpoint(
                row,
                [item for item in oof if item["task_id"] == row["task_id"]],
                run_id=config.current_run_id,
                code_sha=config.code_head_commit,
                data_digest=config.current_data_digest,
                fold_digest=config.current_fold_digest,
            )
            atomic_write_json(checkpoint, checkpoint_root / f"checkpoint_task_{row['task_id']}.json")

    def fit_ols(indices: Sequence[int], method: str, candidate: Mapping[str, Any],
                valid: bool = True, reason: str | None = None,
                native_pred: np.ndarray | None = None,
                convergence: str = "CONVERGED",
                fit_count: int | None = None,
                started_at: float | None = None,
                score_evidence: Mapping[str, Any] | None = None) -> None:
        start = started_at if started_at is not None else time.perf_counter()
        diagnostics: dict[str, Any] = {
            "status": "NOT_COMPUTED",
            "reason": "PRIMARY_OLS_NOT_FIT",
            "rank": None,
            "nullity": None,
            "condition_number": None,
            "condition_number_effective": None,
            "condition_number_full": None,
            "tolerance": None,
        }
        if valid:
            if accounting:
                accounting.record_estimator_fit()
            fit = fit_ols_svd(Xtr[:, indices], ytr, add_intercept=True)
            pred = predict_ols(fit, Xva[:, indices])
            numerical = compute_numerical_diagnostics(fit["design_matrix"])
            diagnostics = {
                "status": "COMPUTED",
                "rank": numerical["rank"],
                "nullity": numerical["nullity"],
                "condition_number": numerical["condition_number_effective"],
                "condition_number_effective": numerical["condition_number_effective"],
                "condition_number_full": numerical["condition_number_full"],
                "tolerance": numerical["tolerance"],
            }
        else:
            pred = np.full_like(yva, np.nan)
        elapsed = time.perf_counter() - start
        record(method, candidate, indices, pred, valid, reason, native_pred, convergence,
               fit_count if fit_count is not None else (1 if valid else 0), elapsed,
               score_evidence=score_evidence, ols_diagnostics=diagnostics)

    baseline_candidate = {"features": "all"}
    if admit_candidate("ols_baseline", baseline_candidate):
        fit_ols(list(range(len(names))), "ols_baseline", baseline_candidate)

    k_grid = tuple(config.k_candidates)
    active_methods = (
        {method for method, _track in config.active_pairs if method != "ols_baseline"}
        if config.active_pairs is not None
        else set(config.active_methods or METHOD_ORDER)
    )
    for method in ("pearson", "mutual_information"):
        if method not in active_methods:
            continue
        for order, k in enumerate(k_grid):
            candidate = {"k": k, "candidate_order": order}
            if not admit_candidate(method, candidate):
                continue
            started = time.perf_counter()
            if method == "pearson":
                from housing_regression.modeling.p4b_runner import compute_pearson_correlations
                scores = np.abs(compute_pearson_correlations(Xtr, ytr))
            else:
                discrete = np.asarray([
                    any(name.startswith(col + "_") for col in NOMINAL_COLUMNS)
                    or name in STRUCTURAL_SOURCES or name.endswith("_is_missing")
                    for name in names
                ], dtype=bool)
                scores = mutual_info_regression(Xtr, ytr, discrete_features=discrete,
                                                n_neighbors=3, random_state=42)
            constant_features = np.all(Xtr == Xtr[0:1, :], axis=0) if method == "pearson" else None
            ranked, score_evidence = rank_features_by_score(
                scores, names, score_kind=method,
                constant_feature_mask=constant_features,
            )
            if k > len(names):
                fit_ols([], method, candidate, False, "K_EXCEEDS_FEATURE_COUNT",
                        started_at=started, score_evidence=score_evidence)
                continue
            idx = ranked[:k]
            fit_ols(idx, method, candidate, started_at=started,
                    score_evidence=score_evidence)

    for order, k in (enumerate(k_grid) if "ridge_rfe" in active_methods else ()):
        candidate = {"k": k, "candidate_order": order}
        if not admit_candidate("ridge_rfe", candidate):
            continue
        if k > len(names):
            fit_ols([], "ridge_rfe", candidate, False, "K_EXCEEDS_FEATURE_COUNT")
            continue
        started = time.perf_counter()
        stable_order = sorted(range(len(names)), key=lambda index: names[index])
        rfe_step = max(1, int(0.2 * len(names)))
        rfe_fit_count = int(math.ceil((len(names) - k) / rfe_step)) + 1
        if accounting:
            accounting.record_estimator_fit(rfe_fit_count)
        selector = RFE(Ridge(alpha=1.0), n_features_to_select=k, step=0.2)
        selector.fit(scaled_tr[:, stable_order], ytr)
        selected = [stable_order[index] for index in np.flatnonzero(selector.support_)]
        fit_ols(selected, "ridge_rfe", candidate, fit_count=rfe_fit_count + 1, started_at=started)

    for order, alpha in (enumerate(PENALTY_ALPHAS) if "lasso" in active_methods else ()):
        candidate = {"alpha": alpha, "candidate_order": order}
        if not admit_candidate("lasso", candidate):
            continue
        started = time.perf_counter()
        if accounting:
            accounting.record_estimator_fit()
        model = Lasso(alpha=alpha, max_iter=10000, tol=1e-4, selection="cyclic")
        from housing_regression.modeling.p4b_runner import fit_and_capture_convergence
        convergence = fit_and_capture_convergence(model, scaled_tr, ytr)
        selected = np.flatnonzero(np.abs(model.coef_) > 1e-8).tolist()
        native = model.predict(scaled_va)
        valid = bool(selected) and np.isfinite(model.coef_).all() and convergence["convergence_status"] == "CONVERGED"
        fit_ols(selected, "lasso", candidate, valid,
                None if valid else "EMPTY_SELECTION_OR_NONFINITE_OR_NO_CONVERGENCE", native,
                convergence["convergence_status"], fit_count=2 if valid else 1,
                started_at=started)

    en_order = 0
    for alpha in (PENALTY_ALPHAS if "elastic_net" in active_methods else ()):
        for l1_ratio in ELASTIC_NET_L1_RATIOS:
            candidate = {"alpha": alpha, "l1_ratio": l1_ratio, "candidate_order": en_order}
            if not admit_candidate("elastic_net", candidate):
                en_order += 1
                continue
            started = time.perf_counter()
            if accounting:
                accounting.record_estimator_fit()
            model = ElasticNet(alpha=alpha, l1_ratio=l1_ratio, max_iter=10000,
                               tol=1e-4, selection="cyclic")
            from housing_regression.modeling.p4b_runner import fit_and_capture_convergence
            convergence = fit_and_capture_convergence(model, scaled_tr, ytr)
            selected = np.flatnonzero(np.abs(model.coef_) > 1e-8).tolist()
            native = model.predict(scaled_va)
            valid = bool(selected) and np.isfinite(model.coef_).all() and convergence["convergence_status"] == "CONVERGED"
            fit_ols(selected, "elastic_net", candidate, valid,
                    None if valid else "EMPTY_SELECTION_OR_NONFINITE_OR_NO_CONVERGENCE", native,
                    convergence["convergence_status"], fit_count=2 if valid else 1,
                    started_at=started)
            en_order += 1

    return {"fold": fold, "results": tasks, "oof_records": oof,
            "data_digest": None, "fold_digest": None}


def aggregate_candidates(
    fold_results: Sequence[Mapping[str, Any]],
    config: Any,
    *,
    expected_folds: Sequence[int] = (0, 1, 2),
    expected_identity: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Aggregate only exact, identity-consistent, complete three-fold task coverage."""
    folds = tuple(expected_folds)
    if (
        len(folds) != 3
        or any(isinstance(fold, bool) or not isinstance(fold, int) for fold in folds)
        or folds != (0, 1, 2)
    ):
        raise ValueError("Protocol v2 aggregation requires exactly folds (0, 1, 2).")
    required_identity = ("run_id", "git_sha", "data_digest", "fold_digest", "package_versions")
    if any(key not in expected_identity or expected_identity[key] in (None, "") for key in required_identity):
        raise ValueError("Aggregation requires run/code/data/fold/package identity.")

    expected_specs = task_specs(config)
    expected_by_key = {
        (method, canonical_digest(candidate)): (method, dict(candidate))
        for method, candidate in expected_specs
    }
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    malformed: list[Mapping[str, Any]] = []
    for row in fold_results:
        method, candidate = row.get("method"), row.get("candidate")
        if not isinstance(method, str) or not isinstance(candidate, Mapping):
            malformed.append(row)
            continue
        key = (method, canonical_digest(dict(candidate)))
        grouped.setdefault(key, []).append(row)

    all_keys = set(expected_by_key) | set(grouped)
    ordered_keys = sorted(
        all_keys,
        key=lambda key: (0 if key in expected_by_key else 1,
                         METHOD_ORDER.index(key[0]) if key[0] in METHOD_ORDER else -1,
                         key[0], key[1]),
    )
    aggregates: list[dict[str, Any]] = []
    identity_keys = ("run_id", "git_sha", "data_digest", "fold_digest", "package_versions")

    for key in ordered_keys:
        expected = key in expected_by_key
        method, candidate = expected_by_key[key] if expected else (key[0], dict(grouped[key][0]["candidate"]))
        rows = grouped.get(key, [])
        reasons: set[str] = set()
        if not expected:
            reasons.add("UNEXPECTED_METHOD_CANDIDATE")

        expected_hash = task_config_hash(config, method, candidate) if expected else None
        fold_rows: dict[int, list[Mapping[str, Any]]] = {}
        observed_folds: set[int] = set()
        group_identity: dict[str, str] = {}
        row_issues: dict[int, set[str]] = {}

        for index, row in enumerate(rows):
            local: set[str] = set()
            raw_fold = row.get("fold")
            if isinstance(raw_fold, bool) or not isinstance(raw_fold, int):
                local.add("INVALID_FOLD")
            elif raw_fold not in folds:
                local.add("OUT_OF_RANGE_FOLD")
            else:
                observed_folds.add(raw_fold)
                fold_rows.setdefault(raw_fold, []).append(row)

            if dict(row.get("candidate", {})) != candidate or row.get("method") != method:
                local.add("CANDIDATE_IDENTITY_MISMATCH")
            if expected and row.get("config_hash") != expected_hash:
                local.add("CONFIG_HASH_MISMATCH")
            for field_name in identity_keys:
                value = row.get(field_name)
                if value in (None, ""):
                    local.add(f"MISSING_{field_name.upper()}")
                    continue
                digest = canonical_digest(value)
                if field_name in group_identity and group_identity[field_name] != digest:
                    local.add("MIXED_RUN_IDENTITY")
                group_identity.setdefault(field_name, digest)
                expected_value = expected_identity.get(field_name)
                if expected_value is not None and value != expected_value:
                    local.add(f"{field_name.upper()}_MISMATCH")

            expected_track = "baseline" if method == "ols_baseline" else "primary"
            expected_primary_track = "all_features_ols" if method == "ols_baseline" else "selected_to_ols"
            if row.get("track") != expected_track or row.get("primary_track") != expected_primary_track:
                local.add("PRIMARY_TRACK_MISMATCH")
            if raw_fold in folds and not isinstance(raw_fold, bool):
                expected_task_id = make_task_id(expected_identity["run_id"], method, candidate, raw_fold)
                if row.get("task_id") != expected_task_id:
                    local.add("TASK_IDENTITY_MISMATCH")
            if row.get("status") != "COMPLETED" or row.get("primary_valid") is not True:
                local.add("INVALID_TASK")
            rmse = row.get("rmse")
            if isinstance(rmse, bool) or not isinstance(rmse, (int, float)) or not math.isfinite(float(rmse)):
                local.add("INVALID_PRIMARY_METRIC")
            if local:
                reasons.update(local)
            row_issues[index] = local

        duplicate_folds = sorted(fold for fold, items in fold_rows.items() if len(items) != 1)
        if duplicate_folds:
            reasons.add("DUPLICATE_FOLD")
        missing_folds = sorted(set(folds) - observed_folds)
        if missing_folds:
            reasons.add("MISSING_FOLD")

        valid_folds: list[int] = []
        valid_rows: list[Mapping[str, Any]] = []
        for fold in folds:
            items = fold_rows.get(fold, [])
            if len(items) != 1:
                continue
            row_index = rows.index(items[0])
            if not row_issues.get(row_index):
                valid_folds.append(fold)
                valid_rows.append(items[0])
        if len(valid_folds) != len(folds):
            reasons.add("INCOMPLETE_OR_INVALID_COVERAGE")
        complete = expected and len(valid_folds) == len(folds) and not reasons
        primary_track = "all_features_ols" if method == "ols_baseline" else "selected_to_ols"
        winner_eligible = complete and method in METHOD_ORDER and primary_track == "selected_to_ols"

        scores = [float(row["rmse"]) for row in valid_rows] if complete else []
        maes = [float(row["mae"]) for row in valid_rows
                if complete and isinstance(row.get("mae"), (int, float)) and math.isfinite(float(row["mae"]))]
        r2s = [float(row["r2"]) for row in valid_rows
               if complete and isinstance(row.get("r2"), (int, float)) and math.isfinite(float(row["r2"]))]
        selected_counts = [int(row["encoded_count"]) for row in valid_rows
                           if complete and isinstance(row.get("encoded_count"), int)]
        native_rows = [row["native_diagnostic"] for row in valid_rows
                       if complete and isinstance(row.get("native_diagnostic"), Mapping)
                       and row["native_diagnostic"].get("rmse") is not None]
        native_rmses = [float(row["rmse"]) for row in native_rows
                        if isinstance(row.get("rmse"), (int, float)) and math.isfinite(float(row["rmse"]))]
        native_maes = [float(row["mae"]) for row in native_rows
                       if isinstance(row.get("mae"), (int, float)) and math.isfinite(float(row["mae"]))]
        native_r2s = [float(row["r2"]) for row in native_rows
                      if isinstance(row.get("r2"), (int, float)) and math.isfinite(float(row["r2"]))]
        aggregates.append({
            "method": method,
            "candidate": candidate,
            "config_hash": expected_hash,
            "expected_fold_count": len(folds),
            "observed_fold_count": len(observed_folds),
            "valid_fold_count": len(valid_folds),
            "expected_folds": list(folds),
            "observed_folds": sorted(observed_folds),
            "valid_folds": valid_folds,
            "observed_row_count": len(rows),
            "coverage_complete": complete,
            "invalid_reasons": sorted(reasons),
            "selection_primary_cv_rmse": float(np.mean(scores)) if scores else None,
            "selection_primary_cv_rmse_sd": float(np.std(scores, ddof=1)) if len(scores) > 1 else None,
            "selection_primary_cv_mae": float(np.mean(maes)) if len(maes) == len(folds) else None,
            "selection_primary_cv_mae_sd": float(np.std(maes, ddof=1)) if len(maes) == len(folds) and len(maes) > 1 else None,
            "selection_primary_cv_r2": float(np.mean(r2s)) if len(r2s) == len(folds) else None,
            "selection_primary_cv_r2_sd": float(np.std(r2s, ddof=1)) if len(r2s) == len(folds) and len(r2s) > 1 else None,
            "mean_selected_encoded_count": float(np.mean(selected_counts)) if len(selected_counts) == len(folds) else None,
            "native_diagnostic_cv_rmse": float(np.mean(native_rmses)) if len(native_rmses) == len(folds) else None,
            "native_diagnostic_cv_rmse_sd": float(np.std(native_rmses, ddof=1)) if len(native_rmses) == len(folds) and len(native_rmses) > 1 else None,
            "native_diagnostic_cv_mae": float(np.mean(native_maes)) if len(native_maes) == len(folds) else None,
            "native_diagnostic_cv_mae_sd": float(np.std(native_maes, ddof=1)) if len(native_maes) == len(folds) and len(native_maes) > 1 else None,
            "native_diagnostic_cv_r2": float(np.mean(native_r2s)) if len(native_r2s) == len(folds) else None,
            "native_diagnostic_cv_r2_sd": float(np.std(native_r2s, ddof=1)) if len(native_r2s) == len(folds) and len(native_r2s) > 1 else None,
            "primary_valid": complete,
            "winner_eligible": winner_eligible,
            "status": "COMPLETED" if complete else "INVALID",
        })

    for row in malformed:
        aggregates.append({
            "method": "UNKNOWN",
            "candidate": {},
            "config_hash": None,
            "expected_fold_count": len(folds),
            "observed_fold_count": 0,
            "valid_fold_count": 0,
            "expected_folds": list(folds),
            "observed_folds": [],
            "valid_folds": [],
            "observed_row_count": 1,
            "coverage_complete": False,
            "invalid_reasons": ["MALFORMED_TASK_IDENTITY"],
            "selection_primary_cv_rmse": None,
            "selection_primary_cv_rmse_sd": None,
            "selection_primary_cv_mae": None,
            "selection_primary_cv_mae_sd": None,
            "selection_primary_cv_r2": None,
            "selection_primary_cv_r2_sd": None,
            "mean_selected_encoded_count": None,
            "native_diagnostic_cv_rmse": None,
            "native_diagnostic_cv_rmse_sd": None,
            "native_diagnostic_cv_mae": None,
            "native_diagnostic_cv_mae_sd": None,
            "native_diagnostic_cv_r2": None,
            "native_diagnostic_cv_r2_sd": None,
            "primary_valid": False,
            "winner_eligible": False,
            "status": "INVALID",
        })

    blocked_methods: list[str] = []
    for method in METHOD_ORDER:
        eligible = [row for row in aggregates if row["method"] == method and row["winner_eligible"]]
        if eligible:
            eligible.sort(key=lambda row: (
                row["selection_primary_cv_rmse"],
                row["mean_selected_encoded_count"],
                row["candidate"].get("candidate_order", 0),
            ))
            best_score = eligible[0]["selection_primary_cv_rmse"]
            tied = [row for row in eligible if row["selection_primary_cv_rmse"] <= best_score + 1e-8]
            tied.sort(key=lambda row: (
                row["mean_selected_encoded_count"],
                row["candidate"].get("candidate_order", 0),
            ))
            tied[0]["method_winner"] = True
        else:
            blocked_methods.append(method)
    for row in aggregates:
        if row["method"] in METHOD_ORDER:
            row["method_status"] = "METHOD_BLOCKED" if row["method"] in blocked_methods else "METHOD_COMPLETE"
        row["blocked_methods"] = list(blocked_methods)
        row["overall_method_status"] = "METHOD_BLOCKED" if blocked_methods else "ALL_METHODS_COMPLETE"
    method_winners = [row for row in aggregates if row.get("method_winner") and row["winner_eligible"]]
    if method_winners and not blocked_methods:
        method_winners.sort(key=lambda row: (
            row["selection_primary_cv_rmse"],
            row["mean_selected_encoded_count"],
            METHOD_ORDER.index(row["method"]),
        ))
        best_score = method_winners[0]["selection_primary_cv_rmse"]
        tied_methods = [row for row in method_winners
                        if row["selection_primary_cv_rmse"] <= best_score + 1e-8]
        tied_methods.sort(key=lambda row: (
            row["mean_selected_encoded_count"],
            row["candidate"].get("candidate_order", 0),
            METHOD_ORDER.index(row["method"]),
        ))
        tied_methods[0]["five_method_winner"] = True
    return aggregates
