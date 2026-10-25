"""Tests for Issue #22 Phase 4-B-A Runner and synthetic contract validations."""

from __future__ import annotations

import json
import hashlib
import math
import os
import platform
import random
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "python" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from housing_regression.data_prep import AmesDataPreparationPipeline, TARGET_COLUMN
from housing_regression.data_prep.constants import ALL_PREDICTOR_COLUMNS
from housing_regression.modeling.ols_cv import (
    fold_assignment_digest,
    kfold_assignments,
)
from housing_regression.modeling.p4b_runner import (
    ALLOWED_K_CANDIDATES,
    DEFAULT_D_CEILING,
    BudgetExceededError,
    DimensionCeilingExceededError,
    FitAccounting,
    InvalidDataFormatError,
    P4BConfig,
    P4BRunner,
    EXPECTED_DEVELOPMENT_INDEX_DIGEST,
    EXPECTED_DEVELOPMENT_ROWS,
    EXPECTED_OUTER_FOLD_DIGEST,
    TimeoutExceededError,
    WORKER_STARTUP_TIMEOUT_SECONDS,
    compute_fold_plan_digest,
    compute_canonical_fingerprint,
    compute_pearson_correlations,
    fit_and_capture_convergence,
    encode_canonical_cell,
    estimate_preflight_budget,
    forward_sfs_greedy_path,
    rfe_ridge_path,
    select_features_filter,
    tie_break_elastic_net,
    tie_break_lasso_alpha,
    tie_break_subset_k,
    verify_development_provenance,
)
from tests.modeling.test_harness import run_test_in_bounded_subprocess
from housing_regression.modeling.p4b_artifacts import checkpoint_run_config


def make_synthetic_dataset(n_rows: int = 40, seed: int = 42) -> List[Dict[str, str]]:
    """Generate small synthetic row dictionaries using only known column names."""
    rng = random.Random(seed)
    rows: List[Dict[str, str]] = []
    neighborhoods = ["CollgCr", "Veenker", "Crawfor", "NoRidge", "Mitchel"]

    for i in range(n_rows):
        area = rng.randint(4000, 15000)
        qual = rng.randint(1, 10)
        nb = neighborhoods[i % len(neighborhoods)]
        price = 20000 + 8 * area + 15000 * qual + rng.gauss(0, 5000)
        row = {
            "Id": str(i + 1),
            "MSSubClass": "20" if i % 2 == 0 else "020",
            "LotArea": str(area),
            "OverallQual": str(qual),
            "Neighborhood": nb,
            "SalePrice": f"{price:.0f}",
        }
        rows.append(row)
    return rows


class FailingPipeline(AmesDataPreparationPipeline):
    def fit_transform(self, dataset, split_name: str = "train"):
        raise RuntimeError(r"Injected failure with path C:\secret\data.csv and target SalePrice: 300000")


class SpyPipeline(AmesDataPreparationPipeline):
    fitted_splits: List[str] = []
    pipe_fitted: bool = False

    def fit(self, dataset):
        SpyPipeline.pipe_fitted = True
        SpyPipeline.fitted_splits.append("train_fit")
        return super().fit(dataset)

    def fit_transform(self, dataset, split_name: str = "train"):
        SpyPipeline.pipe_fitted = True
        SpyPipeline.fitted_splits.append(split_name)
        return super().fit_transform(dataset, split_name=split_name)

    def transform(self, dataset, split_name: str = "val"):
        return super().transform(dataset, split_name=split_name)


class P4BContractTests(unittest.TestCase):
    """Synthetic unit tests validating P4-B-A modeling protocol contracts."""

    def test_outer_kfold_digest_expected(self):
        """TEST-P4B-01: Verify outer 5-fold split digest matches expected signature."""
        folds = kfold_assignments(1168, n_splits=5, random_state=42)
        digest = fold_assignment_digest(folds)
        self.assertEqual(digest, "7c9f1d00eb74d8a281ba41ed47d5ebbdbffa0513b4bb778b70d1571735ad6463")

    def test_production_membership_provenance_and_synthetic_unverified_status(self):
        config = P4BConfig(code_head_commit="synthetic-sha")
        rows = [{"Id": str(index)} for index in range(EXPECTED_DEVELOPMENT_ROWS)]
        provenance = {
            "labeled_rows_counted": 1460,
            "development_rows": EXPECTED_DEVELOPMENT_ROWS,
            "split_seed": 42,
            "val_fraction": 0.2,
            "development_index_digest": EXPECTED_DEVELOPMENT_INDEX_DIGEST,
            "source_basename": "train.csv",
            "id_uniqueness_verified": True,
            "unique_id_count": EXPECTED_DEVELOPMENT_ROWS,
            "row_id_membership_digest": hashlib.sha256(
                json.dumps([row["Id"] for row in rows], separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "dataset_fingerprint": compute_canonical_fingerprint(rows),
        }
        verified = verify_development_provenance(rows, provenance, config)
        self.assertTrue(verified["verified"])
        self.assertEqual(verified["outer_fold_digest"], EXPECTED_OUTER_FOLD_DIGEST)
        for key, bad_value in (
            ("development_index_digest", "wrong"),
            ("row_id_membership_digest", "wrong"),
            ("dataset_fingerprint", "wrong"),
            ("split_seed", 43),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_development_provenance(rows, {**provenance, key: bad_value}, config)
        duplicate = [*rows[:-1], dict(rows[0])]
        with self.assertRaises(ValueError):
            verify_development_provenance(duplicate, provenance, config)

        synthetic_config = P4BConfig(code_head_commit="synthetic-sha", synthetic_test_mode=True, outer_splits=2)
        synthetic = verify_development_provenance(make_synthetic_dataset(20), None, synthetic_config)
        self.assertFalse(synthetic["verified"])
        self.assertEqual(synthetic["verification_status"], "SYNTHETIC_UNVERIFIED")
        production_runner = P4BRunner(P4BConfig(code_head_commit="production-default"))
        with self.assertRaises(ValueError):
            production_runner.run_nested_cv(make_synthetic_dataset(20))
        self.assertEqual(production_runner.accounting.estimator_fits, 0)

        # A caller can fabricate a self-consistent Mapping, but the raw-row API
        # must not treat that mapping as evidence that Phase-3 loaded the rows.
        spoof_rows = [{"Id": str(index)} for index in range(EXPECTED_DEVELOPMENT_ROWS)]
        spoof_provenance = {
            **provenance,
            "row_id_membership_digest": hashlib.sha256(
                json.dumps([row["Id"] for row in spoof_rows], separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "dataset_fingerprint": compute_canonical_fingerprint(spoof_rows),
        }
        with self.assertRaisesRegex(ValueError, "P4B_RUN_FAILED:PREFLIGHT_VALIDATION_ERROR"):
            production_runner.run_nested_cv(spoof_rows, data_provenance=spoof_provenance)
        self.assertEqual(production_runner.accounting.estimator_fits, 0)

    def test_production_inner_fold_protocol_mismatch_fails_before_fit(self):
        rows = [{"Id": str(index)} for index in range(EXPECTED_DEVELOPMENT_ROWS)]
        invalid_protocols = (
            {"inner_splits": 2, "inner_seed": 1042},
            {"inner_splits": 3, "inner_seed": 1043},
        )
        for overrides in invalid_protocols:
            with self.subTest(**overrides):
                runner = P4BRunner(P4BConfig(code_head_commit="synthetic-fixture", **overrides))
                with self.assertRaisesRegex(ValueError, "P4B_RUN_FAILED:PREFLIGHT_VALIDATION_ERROR"):
                    runner.run_nested_cv(rows)
                self.assertEqual(runner.accounting.estimator_fits, 0)
                self.assertEqual(runner.accounting.preprocessor_fits, 0)

    def test_regularized_fit_records_convergence_warning(self):
        from sklearn.exceptions import ConvergenceWarning
        from sklearn.linear_model import Lasso

        config = P4BConfig(
            synthetic_test_mode=True,
            code_head_commit="synthetic-sha",
            outer_splits=2,
            inner_splits=2,
            active_methods=["lasso_cv"],
            k_candidates=(2,),
            lasso_alphas_count=2,
            elastic_net_alphas_count=2,
            elastic_net_l1_ratios=(0.5,),
            timeout_seconds=10,
        )
        rows = make_synthetic_dataset(30)
        original_fit = Lasso.fit

        def fit_with_warning(estimator, X, y, sample_weight=None):
            result = original_fit(estimator, X, y, sample_weight=sample_weight)
            import warnings as warnings_module
            warnings_module.warn("synthetic nonconvergence", ConvergenceWarning)
            return result

        runner = P4BRunner(config)
        with patch.object(Lasso, "fit", fit_with_warning):
            result = runner.execute_outer_fold(0, rows[:20], rows[20:])
        self.assertEqual({item["convergence_status"] for item in result["results"]}, {"CONVERGENCE_WARNING"})
        self.assertTrue(all(item["convergence_warning_count"] > 0 for item in result["results"]))
        self.assertTrue(all(item["outer_refit_n_iter"] is not None for item in result["results"]))

    def test_normal_worker_ready_deadline_and_active_pairs(self):
        rows = make_synthetic_dataset(30)
        config = P4BConfig(
            synthetic_test_mode=True,
            code_head_commit="synthetic-sha",
            outer_splits=2,
            inner_splits=2,
            active_pairs=[("filter_pearson", "Track A")],
            k_candidates=(2,),
            timeout_seconds=15.0,
        )
        runner = P4BRunner(config)
        result = runner.run_nested_cv(rows)
        self.assertEqual({(item["method"], item["track"]) for item in result["summary"]["per_outer_fold_results"]},
                         {("filter_pearson", "Track A")})
        self.assertEqual(runner.last_ready_msg["status"], "READY")
        timing = runner.last_worker_timing
        self.assertLess(runner.last_ready_msg["ready_sent_ns"], timing["parent_ready_received_ns"])
        self.assertLess(timing["parent_ready_received_ns"], timing["parent_worker_exit_verified_ns"])
        self.assertLessEqual(timing["worker_execution_deadline_ns"] - timing["parent_ready_received_ns"],
                             int(config.timeout_seconds * 1_000_000_000) + 10_000_000)
        with self.assertRaises(ValueError):
            P4BConfig(code_head_commit="x", active_pairs=[("lasso_cv", "Track A")]).validate_positive()

    def test_job_object_has_finite_queryable_memory_limit(self):
        from housing_regression.modeling.p4b_job import (
            JOB_OBJECT_LIMIT_JOB_MEMORY,
            close_job_object,
            create_kill_on_close_job_object,
            query_job_memory_limit,
        )

        limit_bytes = 128 * 1024 * 1024
        job = create_kill_on_close_job_object(limit_bytes)
        try:
            limit_flags, actual_limit = query_job_memory_limit(job)
            self.assertTrue(limit_flags & JOB_OBJECT_LIMIT_JOB_MEMORY)
            self.assertEqual(actual_limit, limit_bytes)
        finally:
            close_job_object(job)
        for invalid in (0, -1, True, 1.5):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                create_kill_on_close_job_object(invalid)
        for invalid in (0, -1, True, 1.5):
            with self.subTest(config_memory=invalid), self.assertRaises(ValueError):
                P4BConfig(code_head_commit="x", max_worker_memory_bytes=invalid).validate_positive()

    def test_canonical_fingerprint_and_parser(self):
        """TEST-P4B-14: Canonical fingerprinting, nominal code preservation, and float/int checks."""
        b20 = encode_canonical_cell("20", "MSSubClass")
        b020 = encode_canonical_cell("020", "MSSubClass")
        self.assertNotEqual(b20, b020)
        self.assertEqual(b20[0], 0x01)

        self.assertEqual(encode_canonical_cell("123", "YearBuilt")[0], 0x02)
        with self.assertRaises(InvalidDataFormatError):
            encode_canonical_cell("123.45", "YearBuilt")
        with self.assertRaises(InvalidDataFormatError):
            encode_canonical_cell("abc", "YearBuilt")

        self.assertEqual(encode_canonical_cell("123.45", "LotArea")[0], 0x03)
        with self.assertRaises(InvalidDataFormatError):
            encode_canonical_cell("inf", "LotArea")
        with self.assertRaises(InvalidDataFormatError):
            encode_canonical_cell("-inf", "LotArea")

        b_null = encode_canonical_cell(None, "Alley")
        b_empty = encode_canonical_cell("", "Alley")
        self.assertEqual(b_null, b_empty)
        self.assertEqual(b_null[0], 0x00)

        rows = make_synthetic_dataset(10)
        fp1 = compute_canonical_fingerprint(rows)
        fp2 = compute_canonical_fingerprint(rows)
        self.assertEqual(fp1, fp2)
        self.assertEqual(len(fp1), 64)

    def test_preflight_budget_estimation_and_rejection_spy(self):
        """Blocker 2: Preflight budget estimate rejects over-budget config before any fitting."""
        config = P4BConfig(synthetic_test_mode=True,
            code_head_commit="test_commit",
            estimator_fit_cap=50,
            preprocessor_fit_cap=10,
            active_methods=["filter_pearson"],
            k_candidates=(2, 3),
        )
        SpyPipeline.pipe_fitted = False
        rows = make_synthetic_dataset(20)
        runner = P4BRunner(config)

        with self.assertRaises(BudgetExceededError):
            runner.run_nested_cv(rows, pipeline_factory=SpyPipeline)

        self.assertFalse(SpyPipeline.pipe_fitted)

    def test_preprocessor_fitting_boundary_spy(self):
        """TEST-P4B-02: Verify preprocessor fit is called strictly on Train partitions, never Val."""
        SpyPipeline.fitted_splits = []
        rows = make_synthetic_dataset(30)
        config = P4BConfig(synthetic_test_mode=True,
            code_head_commit="test_commit",
            outer_splits=2,
            inner_splits=2,
            estimator_fit_cap=10000,
            preprocessor_fit_cap=100,
            active_methods=["filter_pearson"],
            k_candidates=(2, 3),
        )
        runner = P4BRunner(config)
        runner.run_nested_cv(rows, pipeline_factory=SpyPipeline)

        for s in SpyPipeline.fitted_splits:
            self.assertIn("train", s.lower())
            self.assertNotIn("val", s.lower())

    def test_dimension_ceiling_exceeded_error(self):
        """TEST-P4B-04: Fail-closed with DimensionCeilingExceededError if feature count exceeds D_ceiling."""
        config = P4BConfig(synthetic_test_mode=True,
            code_head_commit="test_commit",
            d_ceiling=5,
        )
        runner = P4BRunner(config)
        X_wide = np.random.randn(10, 8)
        X_val = np.random.randn(5, 8)
        names = [f"f{i}" for i in range(8)]

        with self.assertRaises(DimensionCeilingExceededError):
            runner._apply_partition_scaling(X_wide, X_val, names)

    def test_intra_method_tie_breaking(self):
        """TEST-P4B-08 & TEST-P4B-16: Deterministic intra-method tie-breaking rules."""
        cand_k = [(5, 0.25), (2, 0.25), (10, 0.25)]
        best_k = tie_break_subset_k(cand_k)
        self.assertEqual(best_k, 2)

        cand_lasso = [(0.1, 0, 0.30), (10.0, 1, 0.30), (1.0, 2, 0.30)]
        best_alpha, best_idx = tie_break_lasso_alpha(cand_lasso)
        self.assertEqual(best_alpha, 10.0)
        self.assertEqual(best_idx, 1)

        cand_en = [
            (1.0, 0.5, 0, 0.40),
            (10.0, 0.1, 1, 0.40),
            (10.0, 0.9, 2, 0.40),
        ]
        best_alpha, best_l1, best_idx = tie_break_elastic_net(cand_en)
        self.assertEqual(best_alpha, 10.0)
        self.assertEqual(best_l1, 0.9)
        self.assertEqual(best_idx, 2)

    @patch("housing_regression.modeling.p4b_artifacts.get_canonical_trusted_repo_root")
    def test_b02_positive_interrupted_resume_no_refits(self, trusted_root):
        """B02 Acceptance (Positive): run tiny synthetic folds, checkpoint after interruption, resume, prove completed folds are restored without any pipeline/estimator refit, remaining folds finish, and output equals uninterrupted synthetic reference."""
        tmp_base = Path(tempfile.mkdtemp())
        out_dir = tmp_base / "local" / "research" / "phase4-p4b" / "run_b02_pos"
        trusted_root.return_value = tmp_base.resolve()
        try:
            rows = make_synthetic_dataset(30, seed=42)
            config = P4BConfig(synthetic_test_mode=True,
                code_head_commit="1362035d211759fe4fd4e5a952e534416d350824",
                outer_splits=2,
                inner_splits=2,
                estimator_fit_cap=50000,
                preprocessor_fit_cap=100,
                active_methods=["filter_pearson"],
                k_candidates=(2, 3),
                repo_root=tmp_base,
                timeout_seconds=30.0,
            )

            # 1. Uninterrupted reference run
            ref_runner = P4BRunner(config)
            ref_res = ref_runner.run_nested_cv(rows)
            ref_results = ref_res["summary"]["per_outer_fold_results"]

            # 2. Simulate interruption after fold 0 by generating checkpoint_fold_0.json only
            out_dir.mkdir(parents=True, exist_ok=True)
            outer_folds = kfold_assignments(len(rows), config.outer_splits, config.outer_seed)
            tr_rows = [dict(rows[i]) for i, f in enumerate(outer_folds) if f != 0]
            va_rows = [dict(rows[i]) for i, f in enumerate(outer_folds) if f == 0]
            chk0_runner = P4BRunner(config)
            fold0_out = chk0_runner.execute_outer_fold(0, tr_rows, va_rows)
            from housing_regression.modeling.p4b_artifacts import (
                atomic_write_json,
                compute_checkpoint_payload_digest,
            )
            import sklearn
            import pandas as pd
            import scipy
            canonical_fp = compute_canonical_fingerprint(rows)
            from housing_regression.modeling.p4b_runner import verify_development_provenance
            input_provenance = verify_development_provenance(rows, None, config)
            payload_digest = compute_checkpoint_payload_digest(fold0_out["results"], fold0_out["oof_records"])
            chk0_data = {
                "run_id": "run_b02_pos",
                "completed_outer_fold": 0,
                "code_head_commit": config.code_head_commit,
                "dataset_fingerprint": canonical_fp,
                "payload_digest": payload_digest,
                "fold_plan_digest": compute_fold_plan_digest(len(rows), config),
                "results": fold0_out["results"],
                "oof_records": fold0_out["oof_records"],
                "run_config": checkpoint_run_config(config),
                "metadata": {
                    "protocol_version": config.protocol_version,
                    "environment": {
                        "python_version": platform.python_version(),
                        "sklearn_version": sklearn.__version__,
                        "numpy_version": np.__version__,
                        "pandas_version": pd.__version__,
                        "scipy_version": scipy.__version__,
                    },
                    "data_boundary": {
                        "outer_kfold": {"n_splits": config.outer_splits, "random_state": config.outer_seed},
                        "inner_kfold": {"n_splits": config.inner_splits, "random_state": config.inner_seed},
                        **input_provenance,
                    },
                },
            }
            atomic_write_json(chk0_data, out_dir / "checkpoint_fold_0.json")

            # 3. Resume run: verify fold 0 is NOT refit, and fold 1 finishes
            # To spy on execution without multiprocessing isolation confounding process boundaries,
            # or by tracking accounting fits:
            refit_runner = P4BRunner(config)
            resume_res = refit_runner.run_nested_cv(
                rows,
                output_dir=out_dir,
                run_id="run_b02_pos",
                resume_checkpoint_dir=out_dir,
            )

            # In uninterrupted 2-fold run, total estimator fits = 2 * (fits_per_fold).
            # On resume with 1 fold already complete, total estimator fits should be exactly 1 fold's worth!
            self.assertEqual(resume_res["summary"]["per_outer_fold_results"], ref_results)
            self.assertEqual(resume_res["oof_records"], ref_res["oof_records"])
            self.assertEqual(resume_res["summary"]["status"], "SUCCESS")
            self.assertLess(refit_runner.accounting.estimator_fits, ref_runner.accounting.estimator_fits)
            self.assertEqual(refit_runner.accounting.estimator_fits, ref_runner.accounting.estimator_fits // 2)

        finally:
            shutil.rmtree(tmp_base, ignore_errors=True)

    @patch("housing_regression.modeling.p4b_artifacts.get_canonical_trusted_repo_root")
    def test_b02_negative_rejects_identity_and_payload_mutations(self, trusted_root):
        """B02 Acceptance (Negative): individually remove/change each required identity and digest; alter/truncate payload; remove results/OOF row; swap filename/fold index or run ID; reject before any fold is skipped and preserve existing artifacts byte-for-byte."""
        tmp_base = Path(tempfile.mkdtemp())
        out_dir = tmp_base / "local" / "research" / "phase4-p4b" / "run_b02_neg"
        trusted_root.return_value = tmp_base.resolve()
        try:
            rows = make_synthetic_dataset(30, seed=42)
            config = P4BConfig(synthetic_test_mode=True,
                code_head_commit="1362035d211759fe4fd4e5a952e534416d350824",
                outer_splits=2,
                inner_splits=2,
                estimator_fit_cap=50000,
                preprocessor_fit_cap=100,
                active_methods=["filter_pearson"],
                k_candidates=(2, 3),
                repo_root=tmp_base,
                timeout_seconds=30.0,
            )
            # Create valid checkpoint file
            out_dir.mkdir(parents=True, exist_ok=True)
            runner = P4BRunner(config)
            outer_folds = kfold_assignments(len(rows), config.outer_splits, config.outer_seed)
            fold0_out = runner.execute_outer_fold(0,
                [dict(rows[i]) for i, f in enumerate(outer_folds) if f != 0],
                [dict(rows[i]) for i, f in enumerate(outer_folds) if f == 0])
            from housing_regression.modeling.p4b_artifacts import (
                atomic_write_json,
                compute_checkpoint_payload_digest,
                CheckpointVerificationError,
            )
            import sklearn, pandas as pd, scipy
            canonical_fp = compute_canonical_fingerprint(rows)
            payload_digest = compute_checkpoint_payload_digest(fold0_out["results"], fold0_out["oof_records"])
            valid_chk = {
                "run_id": "run_b02_neg",
                "completed_outer_fold": 0,
                "code_head_commit": config.code_head_commit,
                "dataset_fingerprint": canonical_fp,
                "payload_digest": payload_digest,
                "fold_plan_digest": compute_fold_plan_digest(len(rows), config),
                "results": fold0_out["results"],
                "oof_records": fold0_out["oof_records"],
                "run_config": checkpoint_run_config(config),
                "metadata": {
                    "protocol_version": config.protocol_version,
                    "environment": {
                        "python_version": platform.python_version(),
                        "sklearn_version": sklearn.__version__,
                        "numpy_version": np.__version__,
                        "pandas_version": pd.__version__,
                        "scipy_version": scipy.__version__,
                    },
                    "data_boundary": {
                        "outer_kfold": {"n_splits": config.outer_splits, "random_state": config.outer_seed},
                        "inner_kfold": {"n_splits": config.inner_splits, "random_state": config.inner_seed},
                    },
                },
            }

            mutations = [
                ("dataset_fingerprint", "corrupted_fp"),
                ("dataset_fingerprint", None),
                ("code_head_commit", "corrupted_sha"),
                ("code_head_commit", None),
                ("payload_digest", "corrupted_digest"),
                ("payload_digest", None),  # Missing digest must fail closed
                ("fold_plan_digest", "corrupted_fold_plan"),
                ("fold_plan_digest", None),
                ("run_id", "different_run_id"),
                ("run_id", None),
                ("results", []),
                ("oof_records", []),
                ("results", fold0_out["results"][:-1]),  # Truncated results (removed nonempty row)
                ("oof_records", fold0_out["oof_records"][:-1]),  # Truncated OOF
                ("run_config", dict(valid_chk["run_config"], tol=config.tol * 2)),
                ("run_config", dict(valid_chk["run_config"], max_iter=config.max_iter + 1)),
                ("run_config", {}),  # Missing run_config must fail closed
                ("metadata", dict(valid_chk["metadata"], protocol_version="wrong-protocol")),
                ("metadata", dict(valid_chk["metadata"], environment={**valid_chk["metadata"]["environment"], "sklearn_version": "wrong"})),
            ]
            for field, value in valid_chk["run_config"].items():
                changed_config = dict(valid_chk["run_config"])
                if isinstance(value, bool):
                    changed = not value
                elif isinstance(value, int):
                    changed = value + 1
                elif isinstance(value, float):
                    changed = value + 0.001
                elif isinstance(value, list):
                    changed = [*value, "unexpected"]
                else:
                    changed = "changed"
                changed_config[field] = changed
                mutations.append(("run_config", changed_config))
                omitted_config = dict(valid_chk["run_config"])
                omitted_config.pop(field)
                mutations.append(("run_config", omitted_config))

            chk_file = out_dir / "checkpoint_fold_0.json"
            for key, bad_val in mutations:
                mutated = dict(valid_chk)
                if bad_val is None:
                    mutated.pop(key, None)
                else:
                    mutated[key] = bad_val
                if key == "run_config" and bad_val is not None:
                    mutated[key] = bad_val
                atomic_write_json(mutated, chk_file)
                pre_stat = chk_file.read_bytes()
                runner_mut = P4BRunner(config)
                with self.assertRaises(CheckpointVerificationError):
                    runner_mut.run_nested_cv(
                        rows,
                        output_dir=out_dir,
                        run_id="run_b02_neg",
                        resume_checkpoint_dir=out_dir,
                    )
                # Verify byte preservation on rejection
                self.assertEqual(chk_file.read_bytes(), pre_stat)

            # Recompute payload digest so these cases prove the coverage contract itself rejects omissions.
            for payload_key in ("results", "oof_records"):
                incomplete = dict(valid_chk)
                incomplete[payload_key] = list(valid_chk[payload_key][:-1])
                incomplete["payload_digest"] = compute_checkpoint_payload_digest(
                    incomplete["results"], incomplete["oof_records"],
                )
                atomic_write_json(incomplete, chk_file)
                before_reject = chk_file.read_bytes()
                with self.assertRaises(CheckpointVerificationError):
                    P4BRunner(config).run_nested_cv(
                        rows, output_dir=out_dir, run_id="run_b02_neg", resume_checkpoint_dir=out_dir,
                    )
                self.assertEqual(chk_file.read_bytes(), before_reject)

            # Fold identities remain bound even when the altered payload digest is recomputed.
            for payload_key, fold_key in (("results", "outer_fold"), ("oof_records", "OuterFold")):
                changed_fold = dict(valid_chk)
                changed_fold[payload_key] = [dict(record) for record in valid_chk[payload_key]]
                changed_fold[payload_key][0][fold_key] = 1  # Valid configured fold, but not this checkpoint's fold.
                changed_fold["payload_digest"] = compute_checkpoint_payload_digest(
                    changed_fold["results"], changed_fold["oof_records"],
                )
                atomic_write_json(changed_fold, chk_file)
                before_reject = chk_file.read_bytes()
                with self.assertRaises(CheckpointVerificationError):
                    P4BRunner(config).run_nested_cv(
                        rows, output_dir=out_dir, run_id="run_b02_neg", resume_checkpoint_dir=out_dir,
                    )
                self.assertEqual(chk_file.read_bytes(), before_reject)

                bool_fold = dict(valid_chk)
                bool_fold[payload_key] = [dict(record) for record in valid_chk[payload_key]]
                bool_fold[payload_key][0][fold_key] = False  # bool compares equal to fold 0 but is not a valid integer identity.
                bool_fold["payload_digest"] = compute_checkpoint_payload_digest(
                    bool_fold["results"], bool_fold["oof_records"],
                )
                atomic_write_json(bool_fold, chk_file)
                before_reject = chk_file.read_bytes()
                with self.assertRaises(CheckpointVerificationError):
                    P4BRunner(config).run_nested_cv(
                        rows, output_dir=out_dir, run_id="run_b02_neg", resume_checkpoint_dir=out_dir,
                    )
                self.assertEqual(chk_file.read_bytes(), before_reject)

            # Test filename / fold index mismatch (checkpoint_fold_1.json has completed_outer_fold=0)
            chk_mismatch = out_dir / "checkpoint_fold_1.json"
            atomic_write_json(valid_chk, chk_mismatch)
            if chk_file.exists():
                chk_file.unlink()
            runner_mismatch = P4BRunner(config)
            with self.assertRaises(CheckpointVerificationError):
                runner_mismatch.run_nested_cv(
                    rows,
                    output_dir=out_dir,
                    run_id="run_b02_neg",
                    resume_checkpoint_dir=out_dir,
                )
        finally:
            shutil.rmtree(tmp_base, ignore_errors=True)

    @patch("housing_regression.modeling.p4b_artifacts.get_canonical_trusted_repo_root")
    def test_b03_positive_ready_stall_kills_pid_tree_and_caps_threads(self, trusted_root):
        """B03 Acceptance (Positive): use a spawn-safe synthetic worker, signal readiness only after entering intentional bounded stall, capture worker + one test descendant PIDs, verify reported child thread limit is 1, expire a short timeout, then use Windows process handles/Job Object query to confirm both PIDs signaled/dead, no child work/side effect occurs afterward, and failure is returned."""
        config = P4BConfig(synthetic_test_mode=True,
            code_head_commit="1362035d211759fe4fd4e5a952e534416d350824",
            outer_splits=2,
            inner_splits=2,
            estimator_fit_cap=50000,
            preprocessor_fit_cap=100,
            active_methods=["filter_pearson"],
            k_candidates=(2, 3),
            timeout_seconds=0.5,
            use_isolated_worker_process=True,
            single_thread=True,
        )
        rows = make_synthetic_dataset(30)
        tmp_root = Path(tempfile.mkdtemp(prefix="b03_failure_json_"))
        self.addCleanup(shutil.rmtree, tmp_root, True)
        trusted_root.return_value = tmp_root.resolve()
        run_id = f"b03_timeout_{time.time_ns()}"
        output_dir = tmp_root / "local" / "research" / "phase4-p4b" / run_id
        runner = P4BRunner(config)
        runner.stall_mock_worker = True
        runner.spawn_descendant = True

        import multiprocessing as mp
        ctx = mp.get_context("spawn")
        ready_q = ctx.Queue()
        runner.ready_queue = ready_q

        t0 = time.perf_counter()
        def report_b03_timing():
            runner.last_worker_timing["test_harness_timeout_seconds"] = 30.0
            if runner.last_ready_msg is not None:
                runner.last_worker_timing.update({
                    "stall_entered_ns": runner.last_ready_msg.get("stall_entered_ns"),
                    "ready_sent_ns": runner.last_ready_msg.get("ready_sent_ns"),
                    "ready_received_ns": runner.last_worker_timing.get("parent_ready_received_ns"),
                })
            runner.last_worker_timing["test_elapsed_ns"] = int((time.perf_counter() - t0) * 1_000_000_000)
            print("B03_TIMING_NS=" + json.dumps(runner.last_worker_timing, sort_keys=True))

        self.addCleanup(report_b03_timing)
        with self.assertRaises(TimeoutExceededError) as ctx_err:
            runner.run_nested_cv(rows, output_dir=output_dir, run_id=run_id)
        elapsed = time.perf_counter() - t0

        self.assertLess(elapsed, WORKER_STARTUP_TIMEOUT_SECONDS + config.timeout_seconds + 3.0)
        self.assertIn("TIMEOUT_EXCEEDED", str(ctx_err.exception))
        failure_path = output_dir / "p4b_failure.json"
        self.assertTrue(failure_path.is_file(), "Timeout did not produce the sanitized failure record")
        failure_data = json.loads(failure_path.read_text(encoding="utf-8"))
        failure_text = json.dumps(failure_data, sort_keys=True)
        self.assertEqual(failure_data["status"], "FAILED")
        self.assertEqual(failure_data["error_category"], "TIMEOUT_EXCEEDED")
        self.assertEqual(failure_data["error_code"], "TIMEOUT_EXCEEDED")
        self.assertEqual(failure_data["run_id"], run_id)
        self.assertNotIn("exception_message", failure_data)
        for sentinel in (
            "P4B_RUN_FAILED:TIMEOUT_EXCEEDED",
            str(output_dir),
            r"C:\secret\data.csv",
            "Neighborhood=OldTown",
            "Id=987",
            "SalePrice: 300000",
            "secret_api_token_123456",
        ):
            self.assertNotIn(sentinel, failure_text)

        # Check readiness message captured on runner
        self.assertIsNotNone(runner.last_ready_msg)
        ready_msg = runner.last_ready_msg
        self.assertEqual(ready_msg["status"], "READY")
        worker_pid = ready_msg["worker_pid"]
        descendant_pid = ready_msg["descendant_pid"]
        self.assertNotEqual(worker_pid, descendant_pid)
        self.assertLess(ready_msg["stall_entered_ns"], ready_msg["ready_sent_ns"])
        self.assertGreaterEqual(ready_msg["ready_sent_ns"] - ready_msg["stall_entered_ns"], 50_000_000)
        self.assertLess(ready_msg["ready_sent_ns"], runner.last_worker_timing["parent_ready_received_ns"])
        self.assertLess(
            runner.last_worker_timing["parent_ready_received_ns"] - ready_msg["ready_sent_ns"],
            1_000_000_000,
        )
        self.assertLess(runner.last_worker_timing["worker_target_entry_ns"],
                        runner.last_worker_timing["worker_gate_release_ns"])
        self.assertLess(runner.last_worker_timing["worker_gate_release_ns"], ready_msg["stall_entered_ns"])
        post_ready_elapsed_ns = (
            runner.last_worker_timing["parent_timeout_ns"]
            - runner.last_worker_timing["parent_ready_received_ns"]
        )
        self.assertGreaterEqual(post_ready_elapsed_ns, int(config.timeout_seconds * 1_000_000_000))
        self.assertLess(post_ready_elapsed_ns, int((config.timeout_seconds + 2.0) * 1_000_000_000))
        self.assertLess(runner.last_worker_timing["parent_timeout_ns"],
                        runner.last_worker_timing["overall_deadline_ns"])
        self.assertTrue(ready_msg["thread_limits"], "No BLAS thread pools were reported")
        self.assertTrue(all(limit == 1 for limit in ready_msg["thread_limits"]))

        # Confirm both worker_pid and descendant_pid are dead
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            from housing_regression.modeling.p4b_job import _get_kernel32
            kernel32 = _get_kernel32()
            SYNCHRONIZE = 0x00100000
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            desired_access = SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION

            # Check worker PID
            h_worker = kernel32.OpenProcess(desired_access, False, worker_pid)
            if h_worker:
                res = kernel32.WaitForSingleObject(h_worker, 0)
                code = wintypes.DWORD()
                self.assertTrue(kernel32.GetExitCodeProcess(h_worker, ctypes.byref(code)))
                kernel32.CloseHandle(h_worker)
                self.assertEqual(res, 0, f"Worker process PID {worker_pid} still running! Wait result: {res}")
                self.assertNotEqual(code.value, 259, "Worker process is still active")
            else:
                err = ctypes.get_last_error()
                self.assertEqual(err, 87, f"OpenProcess worker PID {worker_pid} unverifiable: {err}")

            # Check descendant PID
            self.assertIsNotNone(descendant_pid, "No descendant PID captured")
            h_desc = kernel32.OpenProcess(desired_access, False, descendant_pid)
            if h_desc:
                res = kernel32.WaitForSingleObject(h_desc, 0)
                code = wintypes.DWORD()
                self.assertTrue(kernel32.GetExitCodeProcess(h_desc, ctypes.byref(code)))
                kernel32.CloseHandle(h_desc)
                self.assertEqual(res, 0, f"Descendant process PID {descendant_pid} still running! Wait result: {res}")
                self.assertNotEqual(code.value, 259, "Descendant process is still active")
            else:
                err = ctypes.get_last_error()
                self.assertEqual(err, 87, f"OpenProcess descendant PID {descendant_pid} unverifiable: {err}")
            runner.last_worker_timing["os_death_verified_ns"] = time.perf_counter_ns()
            self.assertGreater(runner.last_worker_timing["parent_worker_exit_verified_ns"],
                               runner.last_worker_timing["job_close_end_ns"])
        else:
            self.fail("UNVERIFIED: Windows Job Object process-tree proof requires Windows.")

    def test_b03_negative_unbounded_or_multithread_config_rejected(self):
        """B03 Acceptance (Negative): timeout=None, zero/negative/nonfinite timeout, inline execution, and single_thread=False all fail closed before worker or fit starts; prove with spies/counters."""
        rows = make_synthetic_dataset(10)

        # 1. timeout_seconds=None rejected
        cfg_none = P4BConfig(synthetic_test_mode=True, code_head_commit="commit1", timeout_seconds=None)
        runner_none = P4BRunner(cfg_none)
        with self.assertRaises(ValueError):
            runner_none.run_nested_cv(rows)
        self.assertEqual(runner_none.accounting.estimator_fits, 0)

        # 2. timeout_seconds <= 0 or inf/nan rejected
        for bad_t in [0.0, -5.0, float("inf"), float("nan")]:
            cfg_bad = P4BConfig(synthetic_test_mode=True, code_head_commit="commit1", timeout_seconds=bad_t)
            runner_bad = P4BRunner(cfg_bad)
            with self.assertRaises(ValueError):
                runner_bad.run_nested_cv(rows)
            self.assertEqual(runner_bad.accounting.estimator_fits, 0)

        # 3. inline execution (use_isolated_worker_process=False) rejected
        cfg_inline = P4BConfig(synthetic_test_mode=True, code_head_commit="commit1", timeout_seconds=10.0, use_isolated_worker_process=False)
        runner_inline = P4BRunner(cfg_inline)
        with self.assertRaises(RuntimeError):
            runner_inline.run_nested_cv(rows)
        self.assertEqual(runner_inline.accounting.estimator_fits, 0)

        # 4. single_thread=False rejected
        cfg_multi = P4BConfig(synthetic_test_mode=True, code_head_commit="commit1", timeout_seconds=10.0, single_thread=False)
        runner_multi = P4BRunner(cfg_multi)
        with self.assertRaises(RuntimeError):
            runner_multi.run_nested_cv(rows)
        self.assertEqual(runner_multi.accounting.estimator_fits, 0)

    @patch("housing_regression.modeling.p4b_artifacts.get_canonical_trusted_repo_root")
    def test_b04_injected_failure_durable_json_writing(self, trusted_root):
        """B04 Acceptance: Verify runner writes durable p4b_failure.json on injected pipeline exception."""
        tmp_base = Path(tempfile.mkdtemp())
        out_dir = tmp_base / "local" / "research" / "phase4-p4b" / "run_fail_test"
        trusted_root.return_value = tmp_base.resolve()
        try:
            rows = make_synthetic_dataset(30)
            config = P4BConfig(synthetic_test_mode=True,
                code_head_commit="85487831551d277c8512ef53435ff1fd72bf8ffe",
                outer_splits=2,
                inner_splits=2,
                estimator_fit_cap=50000,
                preprocessor_fit_cap=100,
                active_methods=["filter_pearson"],
                k_candidates=(2, 3),
                repo_root=tmp_base,
            )
            runner = P4BRunner(config)

            with self.assertRaises(RuntimeError):
                runner.run_nested_cv(
                    rows,
                    output_dir=out_dir,
                    run_id="run_fail_test",
                    pipeline_factory=FailingPipeline,
                )

            fail_file = out_dir / "p4b_failure.json"
            self.assertTrue(fail_file.exists())
            fail_text = fail_file.read_text(encoding="utf-8")
            fail_data = json.loads(fail_text)
            self.assertEqual(fail_data["status"], "FAILED")
            self.assertEqual(fail_data["stage"], "OUTER_FOLD_0")
            self.assertEqual(fail_data["error_category"], "PIPELINE_FIT_ERROR")
            self.assertEqual(fail_data["error_code"], "PIPELINE_FIT_ERROR")

            # Check redaction in durable failure file
            self.assertNotIn(r"C:\secret\data.csv", fail_text)
            self.assertNotIn("300000", fail_text)
            self.assertNotIn("exception_message", fail_data)

            # With no output directory, the caller still receives only a structured safe fallback.
            with self.assertRaises(RuntimeError) as no_output_error:
                P4BRunner(config).run_nested_cv(rows, pipeline_factory=FailingPipeline)
            self.assertIn("P4B_RUN_FAILED:PIPELINE_FIT_ERROR", str(no_output_error.exception))
            self.assertNotIn(r"C:\secret\data.csv", str(no_output_error.exception))
            self.assertNotIn("300000", str(no_output_error.exception))
            self.assertFalse((tmp_base / "p4b_failure.json").exists())
        finally:
            shutil.rmtree(tmp_base, ignore_errors=True)

    def test_subprocess_timeout_termination_demonstration(self):
        """Demonstrate hard kill of blocking child process via test harness."""
        with self.assertRaises(TimeoutError):
            run_test_in_bounded_subprocess(
                test_module="tests.modeling.test_p4b_runner",
                test_case="P4BContractTests.test_canonical_fingerprint_and_parser",
                timeout_seconds=0.0001,
                cwd=REPO_ROOT,
            )


if __name__ == "__main__":
    unittest.main()
