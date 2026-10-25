"""Artifact creation, serialization, atomic persistence, and resume verification for P4-B-A.

Safety & containment boundaries:
- Pure Python path and serialization operations.
- STRICTLY ZERO Git or shell subprocess invocations.
- Enforces private output containment under local/research/phase4-p4b/<run-id> boundary.
- Atomic file writing via temporary files with SHA-256 calculation.
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import tempfile
from dataclasses import fields
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from housing_regression.modeling.p4b_runner import P4BConfig, PROTOCOL_VERSION, SUPPORTED_PAIRS

RUN_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


class CheckpointVerificationError(RuntimeError):
    """Raised when checkpoint identity does not match current run configuration."""


class PathContainmentError(RuntimeError):
    """Raised when an artifact output path violates the designated safe research boundary."""

    def __init__(self, message: str, reason_code: str = "PATH_CONTAINMENT_VIOLATION") -> None:
        super().__init__(message)
        self.reason_code = reason_code


FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF


def is_reparse_point_or_link(path: Path) -> bool:
    """Check if an existing path component is a symlink, junction, or reparse point without calling subprocess."""
    # If path does not exist, it cannot be a reparse point or link
    try:
        if not path.exists() and not path.is_symlink():
            return False
    except OSError as exc:
        raise PathContainmentError("Unable to inspect containment component.", "LINK_CHECK_UNAVAILABLE") from exc

    # 1. Standard python symlink check
    try:
        if path.is_symlink():
            return True
    except OSError as exc:
        raise PathContainmentError("Unable to inspect containment component.", "LINK_CHECK_UNAVAILABLE") from exc

    # 2. On Windows, check GetFileAttributesW for FILE_ATTRIBUTE_REPARSE_POINT
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.GetFileAttributesW.restype = wintypes.DWORD
            kernel32.GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
            attrs = kernel32.GetFileAttributesW(str(path))
            if attrs != INVALID_FILE_ATTRIBUTES and bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT):
                return True
            if attrs == INVALID_FILE_ATTRIBUTES and ctypes.get_last_error() not in {2, 3}:
                raise OSError(ctypes.get_last_error(), "GetFileAttributesW failed")
        except Exception as exc:
            raise PathContainmentError("Unable to inspect Windows reparse attributes.", "LINK_CHECK_UNAVAILABLE") from exc

    return False


def get_canonical_trusted_repo_root() -> Path:
    """Derive canonical repository root from the verified codebase location without Git subprocesses."""
    # p4b_artifacts.py is in python/src/housing_regression/modeling/
    # parents[4] is the repository root checkout
    return Path(__file__).resolve().parents[4]


def _reject_reparse_components(path: Path) -> None:
    curr = Path(os.path.abspath(path))
    max_components = len(curr.parts) + 1
    for _ in range(max_components):
        if is_reparse_point_or_link(curr):
            raise PathContainmentError("Reparse points, junctions, and symlinks are prohibited.", "REPARSE_COMPONENT")
        if curr.parent == curr:
            return
        curr = curr.parent
    raise PathContainmentError("Unable to verify every containment component.", "LINK_CHECK_UNAVAILABLE")


def assert_safe_private_containment(
    target_dir: Path,
    repo_root: Optional[Path] = None,
    run_id: Optional[str] = None,
) -> Path:
    """Enforce that target_dir is strictly contained within trusted repo_root/local/research/phase4-p4b/<run_id>.

    Rejects forged/lookalike roots, symlinks, directory junctions, reparse points,
    parent directory escapes (..), sibling paths, and missing or noncanonical run IDs.
    Fails closed without calling git or any subprocess.
    """
    if not isinstance(run_id, str) or not run_id.strip():
        raise PathContainmentError("A canonical run identifier is required.", "INVALID_RUN_ID")

    if not RUN_ID_REGEX.match(run_id):
        raise PathContainmentError("The run identifier is not canonical.", "INVALID_RUN_ID")

    canonical_root = get_canonical_trusted_repo_root()
    if repo_root is not None:
        raw_repo_root = Path(repo_root)
        _reject_reparse_components(raw_repo_root)
        resolved_repo_root = raw_repo_root.resolve()
        # Verify that caller-provided repo_root is identical to canonical root
        if resolved_repo_root != canonical_root:
            raise PathContainmentError(
                "The repository root does not match the trusted checkout.", "UNTRUSTED_REPO_ROOT"
            )
    else:
        resolved_repo_root = canonical_root

    raw_target = Path(target_dir)
    if ".." in raw_target.parts:
        raise PathContainmentError("Directory traversal is prohibited.", "PATH_TRAVERSAL")

    # Reject if target_dir or any parent up to filesystem root is a symlink, junction, or reparse point
    _reject_reparse_components(raw_target)

    canonical_research_base = (resolved_repo_root / "local" / "research" / "phase4-p4b").resolve()
    expected_run_dir = (canonical_research_base / run_id).resolve()
    resolved_target = raw_target.resolve()

    if resolved_target != expected_run_dir:
        raise PathContainmentError(
            "The destination is not the exact authorized run directory.", "UNEXPECTED_RUN_PATH"
        )

    try:
        rel = resolved_target.relative_to(canonical_research_base)
    except ValueError as exc:
        raise PathContainmentError(
            "The destination is outside the authorized research area.", "UNEXPECTED_RUN_PATH"
        ) from exc

    if ".." in rel.parts:
        raise PathContainmentError("Directory traversal is prohibited.", "PATH_TRAVERSAL")

    return resolved_target


def compute_file_sha256_and_size(path: Path) -> tuple[str, int]:
    """Calculate file SHA-256 and byte size."""
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def atomic_write_json(data: Mapping[str, Any], target_path: Path) -> tuple[str, int]:
    """Write data to JSON atomically via temporary file and compute SHA-256."""
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(".tmp")

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    sha256, size = compute_file_sha256_and_size(tmp_path)
    shutil.move(str(tmp_path), str(target_path))
    return sha256, size


def atomic_write_csv(records: Sequence[Mapping[str, Any]], fieldnames: Sequence[str], target_path: Path) -> tuple[str, int]:
    """Write records to CSV atomically via temporary file and compute SHA-256."""
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(".tmp")

    with open(tmp_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    sha256, size = compute_file_sha256_and_size(tmp_path)
    shutil.move(str(tmp_path), str(target_path))
    return sha256, size


def sanitize_error_message(msg: str) -> str:
    """Return a fixed safe message; exception text is never suitable for serialization."""
    del msg
    return "P4B operation failed. See the sanitized error category."


ALLOWLISTED_ERROR_CATEGORIES = {
    "PREFLIGHT_BUDGET_EXCEEDED",
    "PREFLIGHT_VALIDATION_ERROR",
    "PATH_CONTAINMENT_VIOLATION",
    "ESTIMATOR_FIT_ERROR",
    "PIPELINE_FIT_ERROR",
    "TIMEOUT_EXCEEDED",
    "CHECKPOINT_RESUME_MISMATCH",
    "UNHANDLED_EXCEPTION",
    "SAFE_FAILURE_RECORD_UNAVAILABLE",
}


def classify_error_category(exception: BaseException, stage: str = "") -> str:
    """Classify an exception into an allowlisted categorical error code."""
    name = type(exception).__name__
    if "BudgetExceeded" in name:
        return "PREFLIGHT_BUDGET_EXCEEDED"
    if "PathContainment" in name:
        return "PATH_CONTAINMENT_VIOLATION"
    if "Timeout" in name:
        return "TIMEOUT_EXCEEDED"
    if "Checkpoint" in name or "Resume" in name:
        return "CHECKPOINT_RESUME_MISMATCH"
    if name in {"ValueError", "InvalidDataFormatError", "DimensionCeilingExceededError"}:
        return "PREFLIGHT_VALIDATION_ERROR"
    if stage.startswith("OUTER_FOLD_"):
        return "PIPELINE_FIT_ERROR"
    return "UNHANDLED_EXCEPTION"


def write_durable_failure_json(
    target_dir: Path,
    run_id: str,
    stage: str,
    code_head_commit: str,
    exception: BaseException,
    accounting_summary: Mapping[str, Any],
    config_summary: Mapping[str, Any],
) -> Path:
    """B04: Write atomic sanitized failure JSON before re-raising.

    Uses strictly allowlisted error code/category and bounded safe metadata.
    Never serializes free-form exception text, raw paths, row values, or credentials.
    Surfaces secondary write failures with sanitized status.
    """
    verified_target = assert_safe_private_containment(Path(target_dir), run_id=run_id)
    failure_path = verified_target / "p4b_failure.json"
    error_cat = classify_error_category(exception, stage)
    def bounded_int(value: Any, default: int, upper: int) -> int:
        return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= upper else default

    safe_protocol = config_summary.get("protocol_version", PROTOCOL_VERSION)
    if not isinstance(safe_protocol, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,24}", safe_protocol):
        safe_protocol = "unknown"
    safe_commit = code_head_commit if isinstance(code_head_commit, str) and re.fullmatch(r"[0-9a-fA-F]{40}", code_head_commit) else "unknown"
    data = {
        "run_id": run_id,
        "status": "FAILED",
        "stage": stage if isinstance(stage, str) and re.fullmatch(r"(?:STARTUP|PREFLIGHT|PATH_VALIDATION|OUTER_FOLD_[0-9]{1,3})", stage) else "UNKNOWN",
        "error_category": error_cat,
        "error_code": error_cat,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "code_head_commit": safe_commit,
        "fit_accounting": {
            "estimator_fits": bounded_int(accounting_summary.get("estimator_fits"), 0, 10_000_000),
            "preprocessor_fits": bounded_int(accounting_summary.get("preprocessor_fits"), 0, 10_000_000),
        },
        "config_summary": {
            "protocol_version": safe_protocol,
            "d_ceiling": bounded_int(config_summary.get("d_ceiling"), 300, 100_000),
            "outer_splits": bounded_int(config_summary.get("outer_splits"), 5, 1_000),
            "inner_splits": bounded_int(config_summary.get("inner_splits"), 3, 1_000),
        },
    }
    try:
        atomic_write_json(data, failure_path)
    except Exception:
        raise RuntimeError("DURABLE_FAILURE_WRITE_FAILED:UNAVAILABLE") from None
    return failure_path


def compute_checkpoint_payload_digest(results: Sequence[Mapping[str, Any]], oof_records: Sequence[Mapping[str, Any]]) -> str:
    """Compute deterministic SHA-256 digest over checkpoint result payloads."""
    h = hashlib.sha256()
    payload_str = json.dumps({"results": list(results), "oof_records": list(oof_records)}, sort_keys=True)
    h.update(payload_str.encode("utf-8"))
    return h.hexdigest()


def checkpoint_run_config(config: P4BConfig) -> Dict[str, Any]:
    """Serialize every run-defining config field without local paths or execution controls."""
    excluded = {"repo_root"}
    result: Dict[str, Any] = {}
    for item in fields(config):
        if item.name in excluded:
            continue
        value = getattr(config, item.name)
        if item.name == "active_methods":
            value = sorted({method for method, _track in config.active_pairs}) if config.active_pairs is not None else list(
                value or ["filter_pearson", "forward_sfs", "rfe_ridge", "lasso_cv", "elastic_net_cv"]
            )
        elif item.name == "active_pairs":
            selected_methods = set(config.active_methods or ("filter_pearson", "forward_sfs", "rfe_ridge", "lasso_cv", "elastic_net_cv"))
            pairs = value if value is not None else [pair for pair in SUPPORTED_PAIRS if pair[0] in selected_methods]
            value = [list(pair) for pair in pairs]
        elif isinstance(value, tuple):
            value = list(value)
        result[item.name] = value
    return result


def create_manifest(
    run_id: str,
    code_head_commit: str,
    canonical_dataset_sha256: str,
    file_inventory: List[Dict[str, Any]],
    development_rows: int = 1168,
    outer_fold_digest_expected: Optional[str] = None,
    verification_status: str = "UNVERIFIED",
) -> Dict[str, Any]:
    """Construct p4b_manifest.json content per protocol specification."""
    return {
        "run_id": run_id,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "code_head_commit": code_head_commit,
        "phase3_contract_version": PROTOCOL_VERSION,
        "dataset_provenance": {
            "development_rows": development_rows,
            "outer_fold_digest_expected": outer_fold_digest_expected,
            "canonical_development_dataset_sha256": canonical_dataset_sha256,
            "verification_status": verification_status,
        },
        "file_inventory": file_inventory,
    }


def create_public_summary(
    config: P4BConfig,
    run_id: str,
    per_outer_fold_results: List[Dict[str, Any]],
    aggregate_results: List[Dict[str, Any]],
    dataset_fingerprint_verified: bool = False,
    development_rows: Optional[int] = None,
    outer_fold_digest: Optional[str] = None,
    digest_provenance: str = "UNVERIFIED",
) -> Dict[str, Any]:
    """Construct sanitized p4b_public_summary.json without private paths, IDs, or row predictions."""
    import sklearn
    import numpy as np
    import pandas as pd
    import scipy

    return {
        "metadata": {
            "protocol_version": config.protocol_version,
            "issue_reference": "Issue #21 / Issue #22",
            "base_commit": "ee03a51978a0f615f39b656bee318946dcddd890",
            "historical_p4a_reference": {
                "outer_mean_rmse": 36855.78,
                "outer_std_rmse": 7938.31,
                "outer_mean_r2": 0.763579,
                "context_note": "Historical baseline from docs/crisp-dm/04-modeling-p4a-ols-baseline.md",
            },
            "run_id": run_id,
            "environment": {
                "python_version": platform.python_version(),
                "sklearn_version": sklearn.__version__,
                "numpy_version": np.__version__,
                "pandas_version": pd.__version__,
                "scipy_version": scipy.__version__,
            },
            "data_boundary": {
                "development_rows": development_rows,
                "outer_kfold": {"n_splits": config.outer_splits, "shuffle": True, "random_state": config.outer_seed},
                "inner_kfold": {"n_splits": config.inner_splits, "shuffle": True, "random_state": config.inner_seed},
                "outer_fold_digest_expected": outer_fold_digest,
                "dataset_fingerprint_verified": dataset_fingerprint_verified,
                "digest_provenance": digest_provenance,
            },
        },
        "method_contract": {
            "filter_pearson": {"k_candidates": list(config.k_candidates)},
            "forward_sfs": {"estimator": "SVD_OLS", "k_candidates": list(config.k_candidates)},
            "rfe_ridge": {"estimator": "Ridge(alpha=1.0)", "k_candidates": list(config.k_candidates)},
            "lasso_cv": {"alphas_count": config.lasso_alphas_count, "inner_cv": config.inner_splits, "adapter": "caller_managed_grid"},
            "elastic_net_cv": {
                "l1_ratios": list(config.elastic_net_l1_ratios),
                "alphas_count": config.elastic_net_alphas_count,
                "inner_cv": config.inner_splits,
                "adapter": "caller_managed_grid",
            },
        },
        "per_outer_fold_results": per_outer_fold_results,
        "aggregate_results": aggregate_results,
    }


def verify_checkpoint_for_resume(
    checkpoint_data: Mapping[str, Any],
    expected_fingerprint: str,
    config: P4BConfig,
    env_versions: Mapping[str, str],
    expected_run_id: Optional[str],
    expected_fold_idx: Optional[int],
    expected_fold_plan_digest: Optional[str] = None,
    expected_oof_ids: Optional[Sequence[str]] = None,
    expected_data_provenance: Optional[Mapping[str, Any]] = None,
) -> None:
    """Verify all resume identity conditions, run config, and payload integrity.

    Fail closed with CheckpointVerificationError on any mismatch.
    """
    meta = checkpoint_data.get("metadata", {})
    env = meta.get("environment", {})
    db = meta.get("data_boundary", {})
    cfg = checkpoint_data.get("run_config", {})

    if not isinstance(expected_run_id, str) or not expected_run_id:
        raise CheckpointVerificationError("Expected run identity is required.")
    if not isinstance(expected_fold_idx, int) or isinstance(expected_fold_idx, bool):
        raise CheckpointVerificationError("Expected fold identity is required.")
    if not 0 <= expected_fold_idx < config.outer_splits:
        raise CheckpointVerificationError("Expected fold identity is outside the configured plan.")
    if not isinstance(expected_fingerprint, str) or not expected_fingerprint:
        raise CheckpointVerificationError("Expected dataset identity is required.")
    required_packages = {"python", "sklearn", "numpy", "pandas", "scipy"}
    if (
        not isinstance(env_versions, Mapping)
        or set(env_versions) != required_packages
        or any(not isinstance(env_versions[pkg], str) or not env_versions[pkg] for pkg in required_packages)
    ):
        raise CheckpointVerificationError("Complete dependency identity is required.")

    # 0. Run ID check
    actual_run_id = checkpoint_data.get("run_id")
    if actual_run_id != expected_run_id:
        raise CheckpointVerificationError(
            f"Run ID mismatch: expected {expected_run_id}, got {actual_run_id}."
        )

    # 1. Dataset fingerprint
    actual_fp = checkpoint_data.get("dataset_fingerprint") or meta.get("dataset_fingerprint")
    if actual_fp != expected_fingerprint:
        raise CheckpointVerificationError(
            f"Dataset fingerprint mismatch: expected {expected_fingerprint}, got {actual_fp}."
        )

    # 2. Git code HEAD commit
    actual_commit = checkpoint_data.get("code_head_commit") or meta.get("code_head_commit")
    if actual_commit != config.code_head_commit:
        raise CheckpointVerificationError(
            f"Code HEAD commit mismatch: expected {config.code_head_commit}, got {actual_commit}."
        )

    # 3. Protocol version
    actual_proto = meta.get("protocol_version")
    if actual_proto != config.protocol_version:
        raise CheckpointVerificationError(
            f"Protocol version mismatch: expected {config.protocol_version}, got {actual_proto}."
        )

    # 4. Dependency versions
    for pkg, exp_ver in env_versions.items():
        act_ver = env.get(f"{pkg}_version")
        if act_ver != exp_ver:
            raise CheckpointVerificationError(
                f"Dependency version mismatch for {pkg}: expected {exp_ver}, got {act_ver}."
            )

    # 5. Split seeds & fold plan
    outer_seed = db.get("outer_kfold", {}).get("random_state")
    inner_seed = db.get("inner_kfold", {}).get("random_state")
    outer_splits = db.get("outer_kfold", {}).get("n_splits")
    inner_splits = db.get("inner_kfold", {}).get("n_splits")
    if (
        outer_seed != config.outer_seed
        or inner_seed != config.inner_seed
        or outer_splits != config.outer_splits
        or inner_splits != config.inner_splits
    ):
        raise CheckpointVerificationError("Split plan/seed mismatch in checkpoint.")
    if expected_data_provenance is None:
        raise CheckpointVerificationError("Expected input provenance was not supplied by caller.")
    for key in (
        "verified",
        "verification_status",
        "development_rows",
        "development_index_digest",
        "row_id_membership_digest",
        "dataset_fingerprint",
        "outer_fold_digest",
    ):
        checkpoint_value = db.get(key)
        expected_value = expected_data_provenance.get(key)
        if checkpoint_value != expected_value:
            raise CheckpointVerificationError("Input membership/fold provenance mismatch in checkpoint.")

    # 6. Run-defining configuration (mandatory)
    if not cfg:
        raise CheckpointVerificationError("Missing required run_config in checkpoint.")
    if cfg != checkpoint_run_config(config):
        raise CheckpointVerificationError("Run-defining config parameters mismatch in checkpoint.")

    # 7. Fold index validity and filename/fold matching
    fold_idx = checkpoint_data.get("completed_outer_fold")
    if not isinstance(fold_idx, int) or isinstance(fold_idx, bool) or not (0 <= fold_idx < config.outer_splits):
        raise CheckpointVerificationError(f"Invalid fold index {fold_idx} for splits {config.outer_splits}.")

    if fold_idx != expected_fold_idx:
        raise CheckpointVerificationError(
            f"Fold index mismatch: expected {expected_fold_idx} from filename, got {fold_idx} in checkpoint."
        )

    results = checkpoint_data.get("results")
    oof_records = checkpoint_data.get("oof_records")
    if not isinstance(results, list) or not isinstance(oof_records, list):
        raise CheckpointVerificationError("Checkpoint payload shape is invalid.")
    if any(not isinstance(item, Mapping) for item in results + oof_records):
        raise CheckpointVerificationError("Checkpoint payload records are invalid.")
    if any(
        not isinstance(item.get("outer_fold"), int)
        or isinstance(item.get("outer_fold"), bool)
        or item.get("outer_fold") != expected_fold_idx
        for item in results
    ):
        raise CheckpointVerificationError("Checkpoint result is bound to a different outer fold.")
    if any(
        not isinstance(item.get("OuterFold"), int)
        or isinstance(item.get("OuterFold"), bool)
        or item.get("OuterFold") != expected_fold_idx
        for item in oof_records
    ):
        raise CheckpointVerificationError("Checkpoint OOF row is bound to a different outer fold.")
    expected_pairs = [tuple(pair) for pair in checkpoint_run_config(config)["active_pairs"]]
    result_pairs = [(item.get("method"), item.get("track")) for item in results]
    if any(not isinstance(method, str) or not isinstance(track, str) for method, track in result_pairs):
        raise CheckpointVerificationError("Checkpoint method-track identity is invalid.")
    if len(result_pairs) != len(expected_pairs) or set(result_pairs) != set(expected_pairs):
        raise CheckpointVerificationError("Checkpoint results do not provide exactly one result per active method-track pair.")
    fold_plan_digest = checkpoint_data.get("fold_plan_digest")
    if not isinstance(fold_plan_digest, str) or not fold_plan_digest:
        raise CheckpointVerificationError("Missing required fold-plan digest.")
    if expected_fold_plan_digest is None or fold_plan_digest != expected_fold_plan_digest:
        raise CheckpointVerificationError("Fold-plan digest mismatch.")
    if expected_oof_ids is None:
        raise CheckpointVerificationError("Expected OOF identity coverage was not supplied by caller.")
    expected_ids = set(map(str, expected_oof_ids))
    if not expected_ids:
        raise CheckpointVerificationError("Expected OOF identity coverage cannot be empty.")
    for method, track in expected_pairs:
        rows_for_pair = [r for r in oof_records if r.get("Method") == method and r.get("Track") == track]
        actual_ids = [str(r.get("Id")) for r in rows_for_pair]
        if len(actual_ids) != len(expected_ids) or set(actual_ids) != expected_ids:
            raise CheckpointVerificationError("Checkpoint OOF payload is missing or duplicates expected row coverage.")
    if len(oof_records) != len(expected_pairs) * len(expected_ids):
        raise CheckpointVerificationError("Checkpoint OOF payload contains unexpected method-track rows.")

    # 8. Checkpoint payload digest verification
    expected_digest = checkpoint_data.get("payload_digest")
    if expected_digest is None:
        raise CheckpointVerificationError("Missing required payload_digest in checkpoint.")

    actual_digest = compute_checkpoint_payload_digest(results, oof_records)
    if actual_digest != expected_digest:
        raise CheckpointVerificationError(
            f"Checkpoint payload digest mismatch: expected {expected_digest}, computed {actual_digest}."
        )
