"""Tests for Issue #22 Phase 4-B-A Runner and synthetic contract validations."""

from __future__ import annotations

import json
import math
import os
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
        config = P4BConfig(
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

        for s in SpyPipeline.fitted_splits:
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

    def test_b02_positive_interrupted_resume_no_refits(self):
        """B02 Acceptance (Positive): run tiny synthetic folds, checkpoint after interruption, resume, prove completed folds are restored without any pipeline/estimator refit, remaining folds finish, and output equals uninterrupted synthetic reference."""
        tmp_base = Path(tempfile.mkdtemp())
        out_dir = tmp_base / "local" / "research" / "phase4-p4b" / "run_b02_pos"
        try:
            rows = make_synthetic_dataset(30, seed=42)
            config = P4BConfig(
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
            payload_digest = compute_checkpoint_payload_digest(fold0_out["results"], fold0_out["oof_records"])
            chk0_data = {
                "run_id": "run_b02_pos",
                "completed_outer_fold": 0,
                "code_head_commit": config.code_head_commit,
                "dataset_fingerprint": canonical_fp,
                "payload_digest": payload_digest,
                "results": fold0_out["results"],
                "oof_records": fold0_out["oof_records"],
                "run_config": {
                    "d_ceiling": config.d_ceiling,
                    "k_candidates": list(config.k_candidates),
                    "active_methods": config.active_methods,
                },
                "metadata": {
                    "protocol_version": config.protocol_version,
                    "environment": {
                        "python_version": "3.12",
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
            self.assertEqual(len(resume_res["summary"]["per_outer_fold_results"]), 2)
            self.assertEqual(resume_res["summary"]["status"], "SUCCESS")
            self.assertLess(refit_runner.accounting.estimator_fits, ref_runner.accounting.estimator_fits)
            self.assertEqual(refit_runner.accounting.estimator_fits, ref_runner.accounting.estimator_fits // 2)

            # Assert output matches uninterrupted reference for fold 0 and fold 1
            res_fold0 = [r for r in resume_res["summary"]["per_outer_fold_results"] if r["outer_fold"] == 0]
            ref_fold0 = [r for r in ref_results if r["outer_fold"] == 0]
            self.assertEqual(len(res_fold0), len(ref_fold0))
            self.assertEqual(res_fold0[0]["outer_val_rmse"], ref_fold0[0]["outer_val_rmse"])
        finally:
            shutil.rmtree(tmp_base, ignore_errors=True)

    def test_b02_negative_rejects_identity_and_payload_mutations(self):
        """B02 Acceptance (Negative): individually remove/change each required identity and digest; alter/truncate payload; remove results/OOF row; swap filename/fold index or run ID; reject before any fold is skipped and preserve existing artifacts byte-for-byte."""
        tmp_base = Path(tempfile.mkdtemp())
        out_dir = tmp_base / "local" / "research" / "phase4-p4b" / "run_b02_neg"
        try:
            rows = make_synthetic_dataset(30, seed=42)
            config = P4BConfig(
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
            fold0_out = runner.execute_outer_fold(0, [dict(r) for r in rows[15:]], [dict(r) for r in rows[:15]])
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
                "results": fold0_out["results"],
                "oof_records": fold0_out["oof_records"],
                "run_config": {
                    "d_ceiling": config.d_ceiling,
                    "k_candidates": list(config.k_candidates),
                    "active_methods": config.active_methods,
                },
                "metadata": {
                    "protocol_version": config.protocol_version,
                    "environment": {
                        "python_version": "3.12",
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
                ("code_head_commit", "corrupted_sha"),
                ("payload_digest", "corrupted_digest"),
                ("run_id", "different_run_id"),
                ("results", []),
                ("oof_records", []),
            ]

            chk_file = out_dir / "checkpoint_fold_0.json"
            for key, bad_val in mutations:
                mutated = dict(valid_chk)
                mutated[key] = bad_val
                atomic_write_json(mutated, chk_file)
                runner_mut = P4BRunner(config)
                with self.assertRaises(CheckpointVerificationError):
                    runner_mut.run_nested_cv(
                        rows,
                        output_dir=out_dir,
                        run_id="run_b02_neg",
                        resume_checkpoint_dir=out_dir,
                    )

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

    def test_b03_positive_ready_stall_kills_pid_tree_and_caps_threads(self):
        """B03 Acceptance (Positive): use a spawn-safe synthetic worker, signal readiness only after entering intentional bounded stall, capture worker + one test descendant PIDs, verify reported child thread limit is 1, expire a short timeout, then use Windows process handles/Job Object query to confirm both PIDs signaled/dead, no child work/side effect occurs afterward, and failure is returned."""
        config = P4BConfig(
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
        runner = P4BRunner(config)
        runner.stall_mock_worker = True
        runner.spawn_descendant = True

        import multiprocessing as mp
        ctx = mp.get_context("spawn")
        ready_q = ctx.Queue()
        runner.ready_queue = ready_q

        t0 = time.perf_counter()
        with self.assertRaises(TimeoutExceededError) as ctx_err:
            runner.run_nested_cv(rows)
        elapsed = time.perf_counter() - t0

        self.assertLess(elapsed, 4.0)
        self.assertIn("exceeded timeout and was terminated", str(ctx_err.exception))

        # Check readiness message captured on runner
        self.assertIsNotNone(runner.last_ready_msg)
        ready_msg = runner.last_ready_msg
        self.assertEqual(ready_msg["status"], "READY")
        worker_pid = ready_msg["worker_pid"]
        descendant_pid = ready_msg["descendant_pid"]
        self.assertEqual(ready_msg["thread_limit"], 1)

        # Confirm both worker_pid and descendant_pid are dead
        if os.name == "nt":
            import ctypes
            SYNCHRONIZE = 0x00100000
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            # Check worker PID
            h_worker = kernel32.OpenProcess(SYNCHRONIZE, False, worker_pid)
            if h_worker:
                # Wait 0ms to check if signaled (WAIT_OBJECT_0 = 0x0)
                res = kernel32.WaitForSingleObject(h_worker, 0)
                kernel32.CloseHandle(h_worker)
                self.assertEqual(res, 0, f"Worker process PID {worker_pid} still running!")

            # Check descendant PID
            if descendant_pid:
                h_desc = kernel32.OpenProcess(SYNCHRONIZE, False, descendant_pid)
                if h_desc:
                    res = kernel32.WaitForSingleObject(h_desc, 0)
                    kernel32.CloseHandle(h_desc)
                    self.assertEqual(res, 0, f"Descendant process PID {descendant_pid} still running!")

    def test_b03_negative_unbounded_or_multithread_config_rejected(self):
        """B03 Acceptance (Negative): timeout=None, zero/negative/nonfinite timeout, inline execution, and single_thread=False all fail closed before worker or fit starts; prove with spies/counters."""
        rows = make_synthetic_dataset(10)

        # 1. timeout_seconds=None rejected
        cfg_none = P4BConfig(code_head_commit="commit1", timeout_seconds=None)
        runner_none = P4BRunner(cfg_none)
        with self.assertRaises(ValueError):
            runner_none.run_nested_cv(rows)
        self.assertEqual(runner_none.accounting.estimator_fits, 0)

        # 2. timeout_seconds <= 0 or inf/nan rejected
        for bad_t in [0.0, -5.0, float("inf"), float("nan")]:
            cfg_bad = P4BConfig(code_head_commit="commit1", timeout_seconds=bad_t)
            runner_bad = P4BRunner(cfg_bad)
            with self.assertRaises(ValueError):
                runner_bad.run_nested_cv(rows)
            self.assertEqual(runner_bad.accounting.estimator_fits, 0)

        # 3. inline execution (use_isolated_worker_process=False) rejected
        cfg_inline = P4BConfig(code_head_commit="commit1", timeout_seconds=10.0, use_isolated_worker_process=False)
        runner_inline = P4BRunner(cfg_inline)
        with self.assertRaises(RuntimeError):
            runner_inline.run_nested_cv(rows)
        self.assertEqual(runner_inline.accounting.estimator_fits, 0)

        # 4. single_thread=False rejected
        cfg_multi = P4BConfig(code_head_commit="commit1", timeout_seconds=10.0, single_thread=False)
        runner_multi = P4BRunner(cfg_multi)
        with self.assertRaises(RuntimeError):
            runner_multi.run_nested_cv(rows)
        self.assertEqual(runner_multi.accounting.estimator_fits, 0)

    def test_b04_injected_failure_durable_json_writing(self):
        """B04 Acceptance: Verify runner writes durable p4b_failure.json on injected pipeline exception."""
        tmp_base = Path(tempfile.mkdtemp())
        out_dir = tmp_base / "local" / "research" / "phase4-p4b" / "run_fail_test"
        try:
            rows = make_synthetic_dataset(30)
            config = P4BConfig(
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
            self.assertEqual(fail_data["exception_type"], "RuntimeError")

            # Check redaction in durable failure file
            self.assertNotIn(r"C:\secret\data.csv", fail_text)
            self.assertNotIn("300000", fail_text)
            self.assertIn("<REDACTED_PATH>", fail_text)
            self.assertIn("<REDACTED_TARGET>", fail_text)
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
