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
import time
from dataclasses import dataclass
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
    """Run-scoped, in-memory status/freeze/stop intent; no OS process actions."""

    run_id: str
    status: str = "CREATED"
    frozen: bool = False
    stop_requested: bool = False

    def status_snapshot(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "status": self.status,
                "frozen": self.frozen, "stop_requested": self.stop_requested}

    def freeze(self) -> dict[str, Any]:
        self.frozen = True
        if self.status not in {"COMPLETED", "FAILED", "STOPPED"}:
            self.status = "FROZEN"
        return self.status_snapshot()

    def stop_all(self) -> dict[str, Any]:
        """Freeze admissions and record stop intent for Phase C to implement safely."""
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
    scores: Sequence[float], feature_names: Sequence[str], *, evidence_limit: int = 20,
) -> tuple[list[int], dict[str, Any]]:
    """Rank finite scores first, with deterministic name ties and bounded invalid evidence."""
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1 or len(values) != len(feature_names):
        raise ValueError("Feature score vector must align with feature names.")
    if isinstance(evidence_limit, bool) or not isinstance(evidence_limit, int) or evidence_limit < 0:
        raise ValueError("evidence_limit must be a nonnegative integer.")

    finite_mask = np.isfinite(values)
    finite_values = values[finite_mask]
    constant = bool(finite_values.size > 0 and np.all(finite_values == finite_values[0]))
    invalid_mask = ~finite_mask
    if constant:
        invalid_mask = np.ones(len(values), dtype=bool)

    valid_indices = [i for i in range(len(values)) if not invalid_mask[i]]
    invalid_indices = [i for i in range(len(values)) if invalid_mask[i]]
    ranked = sorted(valid_indices, key=lambda i: (-float(values[i]), str(feature_names[i])))
    ranked.extend(sorted(invalid_indices, key=lambda i: str(feature_names[i])))

    invalid_names = sorted(str(feature_names[i]) for i in invalid_indices)
    if constant and not invalid_names:
        # Constant scores invalidate the complete vector, including all features.
        invalid_names = sorted(map(str, feature_names))
    reasons = []
    if bool((~finite_mask).any()):
        reasons.append("NONFINITE")
    if constant:
        reasons.append("CONSTANT")
    return ranked, {
        "score_invalid": bool(reasons),
        "score_invalid_reason": "+".join(reasons) if reasons else None,
        "score_count": len(values),
        "finite_score_count": int(finite_mask.sum()),
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

    def already_done(method: str, candidate: Mapping[str, Any]) -> bool:
        return make_task_id(config.current_run_id, method, candidate, fold) in completed

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
    if not already_done("ols_baseline", baseline_candidate):
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
            if already_done(method, candidate):
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
            ranked, score_evidence = rank_features_by_score(scores, names)
            if k > len(names):
                fit_ols([], method, candidate, False, "K_EXCEEDS_FEATURE_COUNT",
                        started_at=started, score_evidence=score_evidence)
                continue
            idx = ranked[:k]
            fit_ols(idx, method, candidate, started_at=started,
                    score_evidence=score_evidence)

    for order, k in (enumerate(k_grid) if "ridge_rfe" in active_methods else ()):
        candidate = {"k": k, "candidate_order": order}
        if already_done("ridge_rfe", candidate):
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
        if already_done("lasso", candidate):
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
            if already_done("elastic_net", candidate):
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


def aggregate_candidates(fold_results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate each method/config across folds and mark deterministic winners."""
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for row in fold_results:
        key = (str(row["method"]), canonical_digest(row["candidate"]))
        grouped.setdefault(key, []).append(row)
    aggregates: list[dict[str, Any]] = []
    for (method, cfg_hash), rows in grouped.items():
        valid = [row for row in rows if row.get("primary_valid") and row.get("rmse") is not None]
        scores = [float(row["rmse"]) for row in valid]
        maes = [float(row["mae"]) for row in valid]
        r2s = [float(row["r2"]) for row in valid if row.get("r2") is not None and np.isfinite(row["r2"])]
        selected_counts = [int(row["encoded_count"]) for row in rows]
        native_rows = [
            row["native_diagnostic"]
            for row in rows
            if isinstance(row.get("native_diagnostic"), Mapping)
            and row["native_diagnostic"].get("rmse") is not None
        ]
        native_rmses = [float(row["rmse"]) for row in native_rows]
        native_maes = [float(row["mae"]) for row in native_rows]
        native_r2s = [float(row["r2"]) for row in native_rows
                      if row.get("r2") is not None and np.isfinite(row["r2"])]
        aggregates.append({
            "method": method,
            "candidate": dict(rows[0]["candidate"]),
            "config_hash": cfg_hash,
            "fold_count": len(rows),
            "valid_fold_count": len(valid),
            "selection_primary_cv_rmse": float(np.mean(scores)) if scores else None,
            "selection_primary_cv_rmse_sd": float(np.std(scores, ddof=1)) if len(scores) > 1 else None,
            "selection_primary_cv_mae": float(np.mean(maes)) if maes else None,
            "selection_primary_cv_mae_sd": float(np.std(maes, ddof=1)) if len(maes) > 1 else None,
            "selection_primary_cv_r2": float(np.mean(r2s)) if r2s else None,
            "selection_primary_cv_r2_sd": float(np.std(r2s, ddof=1)) if len(r2s) > 1 else None,
            "mean_selected_encoded_count": float(np.mean(selected_counts)) if selected_counts else None,
            "native_diagnostic_cv_rmse": float(np.mean(native_rmses)) if native_rmses else None,
            "native_diagnostic_cv_rmse_sd": float(np.std(native_rmses, ddof=1)) if len(native_rmses) > 1 else None,
            "native_diagnostic_cv_mae": float(np.mean(native_maes)) if native_maes else None,
            "native_diagnostic_cv_mae_sd": float(np.std(native_maes, ddof=1)) if len(native_maes) > 1 else None,
            "native_diagnostic_cv_r2": float(np.mean(native_r2s)) if native_r2s else None,
            "native_diagnostic_cv_r2_sd": float(np.std(native_r2s, ddof=1)) if len(native_r2s) > 1 else None,
            "primary_valid": len(valid) == len(rows),
            "status": "COMPLETED" if len(valid) == len(rows) else "INVALID",
        })
    for method in METHOD_ORDER:
        eligible = [row for row in aggregates if row["method"] == method and row["primary_valid"]]
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
    method_winners = [row for row in aggregates if row.get("method_winner")]
    if method_winners:
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
