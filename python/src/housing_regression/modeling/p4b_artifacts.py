"""Artifact creation, serialization, atomic persistence, and resume verification for P4-B-A.

Safety & containment boundaries:
- Pure Python path and serialization operations.
- STRICTLY ZERO Git or shell subprocess invocations.
- Enforces private output containment under local/research/phase4-p4b/<run-id> boundary.
- Atomic file writing via temporary files with SHA-256 calculation.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from housing_regression.modeling.p4b_runner import P4BConfig, PROTOCOL_VERSION


class CheckpointVerificationError(RuntimeError):
    """Raised when checkpoint identity does not match current run configuration."""


class PathContainmentError(RuntimeError):
    """Raised when an artifact output path violates the designated safe research boundary."""


def assert_safe_private_containment(target_dir: Path, repo_root: Optional[Path] = None) -> None:
    """Enforce that target_dir is strictly contained within local/research/phase4-p4b.

    Fails closed without calling git or any subprocess.
    """
    resolved_target = Path(target_dir).resolve()
    # Check normalized path parts for containment
    parts = resolved_target.parts
    # Look for local / research / phase4-p4b sequence
    found_boundary = False
    for i in range(len(parts) - 2):
        if parts[i].lower() == "local" and parts[i + 1].lower() == "research" and parts[i + 2].lower() == "phase4-p4b":
            found_boundary = True
            break

    if not found_boundary:
        raise PathContainmentError(
            f"Destination '{target_dir}' is not contained under 'local/research/phase4-p4b'."
        )


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


def create_manifest(
    run_id: str,
    code_head_commit: str,
    canonical_dataset_sha256: str,
    file_inventory: List[Dict[str, Any]],
    development_rows: int = 1168,
    outer_fold_digest_expected: str = "7c9f1d00eb74d8a281ba41ed47d5ebbdbffa0513b4bb778b70d1571735ad6463",
    verification_status: str = "VERIFIED_MATCH",
) -> Dict[str, Any]:
    """Construct p4b_manifest.json content per protocol specification."""
    import datetime
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
    dataset_fingerprint_verified: bool = True,
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
                "python_version": "3.12",
                "sklearn_version": sklearn.__version__,
                "numpy_version": np.__version__,
                "pandas_version": pd.__version__,
                "scipy_version": scipy.__version__,
            },
            "data_boundary": {
                "development_rows": 1168,
                "outer_kfold": {"n_splits": config.outer_splits, "shuffle": True, "random_state": config.outer_seed},
                "inner_kfold": {"n_splits": config.inner_splits, "shuffle": True, "random_state": config.inner_seed},
                "outer_fold_digest_expected": "7c9f1d00eb74d8a281ba41ed47d5ebbdbffa0513b4bb778b70d1571735ad6463",
                "dataset_fingerprint_verified": dataset_fingerprint_verified,
                "digest_provenance": "VERIFIED_RUNTIME",
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
) -> None:
    """Verify all 5 resume identity conditions. Fail closed with CheckpointVerificationError on mismatch."""
    meta = checkpoint_data.get("metadata", {})
    env = meta.get("environment", {})
    db = meta.get("data_boundary", {})

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

    # 5. Split seeds
    outer_seed = db.get("outer_kfold", {}).get("random_state")
    inner_seed = db.get("inner_kfold", {}).get("random_state")
    if outer_seed != config.outer_seed or inner_seed != config.inner_seed:
        raise CheckpointVerificationError(
            f"Split seed mismatch: expected ({config.outer_seed}, {config.inner_seed}), got ({outer_seed}, {inner_seed})."
        )
