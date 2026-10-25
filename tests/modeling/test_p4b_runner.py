"""Tests for Issue #22 Phase 4-B-A Runner and synthetic contract validations."""

from __future__ import annotations

import math
import random
import shutil
import sys
import tempfile
import time
import unittest
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
    TimeoutExceededError,
    compute_canonical_fingerprint,
    compute_pearson_correlations,
    encode_canonical_cell,
    estimate_preflight_budget,
    forward_sfs_greedy_path,
    rfe_ridge_path,
    select_features_filter,
    tie_break_elastic_net,
    tie_break_lasso_alpha,
    tie_break_subset_k,
)
from tests.modeling.test_harness import run_test_in_bounded_subprocess


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


class P4BContractTests(unittest.TestCase):
    """Synthetic unit tests validating P4-B-A modeling protocol contracts."""

    def test_outer_kfold_digest_expected(self):
        """TEST-P4B-01: Verify outer 5-fold split digest matches expected signature."""
        folds = kfold_assignments(1168, n_splits=5, random_state=42)
        digest = fold_assignment_digest(folds)
        self.assertEqual(digest, "7c9f1d00eb74d8a281ba41ed47d5ebbdbffa0513b4bb778b70d1571735ad6463")

    def test_canonical_fingerprint_and_parser(self):
        """TEST-P4B-14: Canonical fingerprinting, nominal code preservation, and float/int checks."""
        # 1. Nominal code distinction: "20" vs "020"
        b20 = encode_canonical_cell("20", "MSSubClass")
        b020 = encode_canonical_cell("020", "MSSubClass")
        self.assertNotEqual(b20, b020)
        self.assertEqual(b20[0], 0x01)

        # 2. Int parser strictness
        self.assertEqual(encode_canonical_cell("123", "YearBuilt")[0], 0x02)
        with self.assertRaises(InvalidDataFormatError):
            encode_canonical_cell("123.45", "YearBuilt")
        with self.assertRaises(InvalidDataFormatError):
            encode_canonical_cell("abc", "YearBuilt")

        # 3. Float parser and infinity rejection
        self.assertEqual(encode_canonical_cell("123.45", "LotArea")[0], 0x03)
        with self.assertRaises(InvalidDataFormatError):
            encode_canonical_cell("inf", "LotArea")
        with self.assertRaises(InvalidDataFormatError):
            encode_canonical_cell("-inf", "LotArea")

        # 4. Null vs empty string
        b_null = encode_canonical_cell(None, "Alley")
        b_empty = encode_canonical_cell("", "Alley")
        self.assertEqual(b_null, b_empty)
        self.assertEqual(b_null[0], 0x00)

        # 5. Full row hashing consistency
        rows = make_synthetic_dataset(10)
        fp1 = compute_canonical_fingerprint(rows)
        fp2 = compute_canonical_fingerprint(rows)
        self.assertEqual(fp1, fp2)
        self.assertEqual(len(fp1), 64)

    def test_preflight_budget_estimation_and_rejection_spy(self):
        """Blocker 2: Preflight budget estimate rejects over-budget config before any fitting."""
        config = P4BConfig(
            code_head_commit="test_commit",
            estimator_fit_cap=50,  # Far too low for any nested run
            preprocessor_fit_cap=10,
            active_methods=["filter_pearson"],
            k_candidates=(2, 3),
        )

        pipe_fitted = False

        class SpyPipeline(AmesDataPreparationPipeline):
            def fit(self, dataset):
                nonlocal pipe_fitted
                pipe_fitted = True
                return super().fit(dataset)

            def fit_transform(self, dataset, split_name: str = "train"):
                nonlocal pipe_fitted
                pipe_fitted = True
                return super().fit_transform(dataset, split_name=split_name)

        rows = make_synthetic_dataset(20)
        runner = P4BRunner(config)

        # Preflight must reject immediately with BudgetExceededError
        with self.assertRaises(BudgetExceededError):
            runner.run_nested_cv(rows, pipeline_factory=SpyPipeline)

        # Assert no pipeline fitting occurred!
        self.assertFalse(pipe_fitted)

    def test_preprocessor_fitting_boundary_spy(self):
        """TEST-P4B-02: Verify preprocessor fit is called strictly on Train partitions, never Val."""
        fitted_splits: List[str] = []

        class SpyPipeline(AmesDataPreparationPipeline):
            def fit(self, dataset):
                fitted_splits.append("train_fit")
                return super().fit(dataset)

            def fit_transform(self, dataset, split_name: str = "train"):
                fitted_splits.append(split_name)
                return super().fit_transform(dataset, split_name=split_name)

            def transform(self, dataset, split_name: str = "val"):
                return super().transform(dataset, split_name=split_name)

        rows = make_synthetic_dataset(30)
        config = P4BConfig(
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

        for s in fitted_splits:
            self.assertIn("train", s.lower())
            self.assertNotIn("val", s.lower())

    def test_dimension_ceiling_exceeded_error(self):
        """TEST-P4B-04: Fail-closed with DimensionCeilingExceededError if feature count exceeds D_ceiling."""
        config = P4BConfig(
            code_head_commit="test_commit",
            d_ceiling=5,
        )
        runner = P4BRunner(config)
        X_wide = np.random.randn(10, 8)
        X_val = np.random.randn(5, 8)
        names = [f"f{i}" for i in range(8)]

        with self.assertRaises(DimensionCeilingExceededError):
            runner._apply_partition_scaling(X_wide, X_val, names)

    def test_timeout_enforcement(self):
        """Blocker 3: Verify TimeoutExceededError when execution exceeds deadline."""
        config = P4BConfig(
            code_head_commit="test_commit",
            outer_splits=2,
            inner_splits=2,
            estimator_fit_cap=50000,
            preprocessor_fit_cap=100,
            active_methods=["forward_sfs"],
            k_candidates=(2, 3, 5),
            timeout_seconds=0.0001,  # Instantly expire
        )
        rows = make_synthetic_dataset(30)
        runner = P4BRunner(config)

        with self.assertRaises(TimeoutExceededError):
            runner.run_nested_cv(rows)

    def test_intra_method_tie_breaking(self):
        """TEST-P4B-08 & TEST-P4B-16: Deterministic intra-method tie-breaking rules."""
        # 1. K candidates tie: smaller K wins
        cand_k = [(5, 0.25), (2, 0.25), (10, 0.25)]
        best_k = tie_break_subset_k(cand_k)
        self.assertEqual(best_k, 2)

        # 2. Lasso alpha tie: larger alpha wins
        cand_lasso = [(0.1, 0, 0.30), (10.0, 1, 0.30), (1.0, 2, 0.30)]
        best_alpha, best_idx = tie_break_lasso_alpha(cand_lasso)
        self.assertEqual(best_alpha, 10.0)
        self.assertEqual(best_idx, 1)

        # 3. ElasticNet (alpha, l1_ratio) tie: larger alpha wins; if equal, larger l1_ratio wins
        cand_en = [
            (1.0, 0.5, 0, 0.40),
            (10.0, 0.1, 1, 0.40),
            (10.0, 0.9, 2, 0.40),
        ]
        best_alpha, best_l1, best_idx = tie_break_elastic_net(cand_en)
        self.assertEqual(best_alpha, 10.0)
        self.assertEqual(best_l1, 0.9)
        self.assertEqual(best_idx, 2)

    def test_end_to_end_synthetic_nested_cv_with_artifacts_wiring(self):
        """Blocker 4 & 5: End-to-end small synthetic test verifying artifacts writing & containment."""
        tmp_base = Path(tempfile.mkdtemp())
        out_dir = tmp_base / "local" / "research" / "phase4-p4b" / "test_run_e2e"
        try:
            rows = make_synthetic_dataset(30, seed=123)
            config = P4BConfig(
                code_head_commit="a2544bff224bebc64391b31be33066baa910bdf1",
                outer_splits=2,
                inner_splits=2,
                estimator_fit_cap=50000,
                preprocessor_fit_cap=100,
                k_candidates=(2, 3),
                lasso_alphas_count=3,
                elastic_net_alphas_count=2,
                elastic_net_l1_ratios=(0.5, 0.9),
                max_iter=500,
            )
            runner = P4BRunner(config)
            output = runner.run_nested_cv(rows, output_dir=out_dir, run_id="test_run_e2e")

            summary = output["summary"]
            self.assertEqual(summary["status"], "SUCCESS")
            self.assertIsNone(summary["exception"])
            self.assertGreater(summary["fit_accounting"]["elapsed_seconds"], 0)

            # Check that files were written to out_dir
            self.assertTrue((out_dir / "p4b_oof_predictions.csv").exists())
            self.assertTrue((out_dir / "p4b_public_summary.json").exists())
            self.assertTrue((out_dir / "p4b_private_details.json").exists())
            self.assertTrue((out_dir / "p4b_manifest.json").exists())
            self.assertTrue((out_dir / "checkpoint_fold_0.json").exists())
            self.assertTrue((out_dir / "checkpoint_fold_1.json").exists())

            # Read public summary and ensure no row-level data
            pub_text = (out_dir / "p4b_public_summary.json").read_text(encoding="utf-8")
            self.assertNotIn("SalePrice", pub_text)
        finally:
            shutil.rmtree(tmp_base, ignore_errors=True)

    def test_subprocess_timeout_termination_demonstration(self):
        """Blocker 3: Demonstrate hard kill of blocking child process via test harness."""
        # Run a test with a deliberately tiny timeout on a test that sleeps/takes time
        with self.assertRaises(TimeoutError):
            run_test_in_bounded_subprocess(
                test_module="tests.modeling.test_p4b_runner",
                test_case="P4BContractTests.test_canonical_fingerprint_and_parser",
                timeout_seconds=0.0001,  # Deliberately impossible timeout
                cwd=REPO_ROOT,
            )


if __name__ == "__main__":
    unittest.main()
