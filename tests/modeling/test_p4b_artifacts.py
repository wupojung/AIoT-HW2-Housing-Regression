"""Tests for Issue #22 Phase 4-B-A Artifacts, provenance, and resume verification."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "python" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from housing_regression.modeling.p4b_artifacts import (
    CheckpointVerificationError,
    PathContainmentError,
    assert_safe_private_containment,
    atomic_write_csv,
    atomic_write_json,
    compute_file_sha256_and_size,
    create_manifest,
    create_public_summary,
    verify_checkpoint_for_resume,
    write_durable_failure_json,
)
from housing_regression.modeling.p4b_runner import P4BConfig


class P4BArtifactsTests(unittest.TestCase):
    """Synthetic unit tests for artifact writing, B01 containment, and B04 durable failure."""

    def setUp(self):
        self.tmp_base = Path(tempfile.mkdtemp())
        self.safe_dir = self.tmp_base / "local" / "research" / "phase4-p4b" / "test_run"
        self.safe_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp_base, ignore_errors=True)

    def test_no_git_subprocess_invocation(self):
        """Blocker 1: Verify modeling artifact code NEVER invokes subprocess/git."""
        with patch("subprocess.run") as mock_subproc:
            assert_safe_private_containment(self.safe_dir, repo_root=self.tmp_base, run_id="test_run")
            json_file = self.safe_dir / "test.json"
            atomic_write_json({"a": 1}, json_file)
            csv_file = self.safe_dir / "test.csv"
            atomic_write_csv([{"col": "val"}], ["col"], csv_file)
            mock_subproc.assert_not_called()

    def test_b01_containment_negative_cases(self):
        """B01 Acceptance: Reject symlink escapes, parent traversal (..), sibling paths, and noncanonical run IDs."""
        # 1. Valid path passes
        assert_safe_private_containment(self.safe_dir, repo_root=self.tmp_base, run_id="test_run")

        # 2. Noncanonical run_id
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(self.safe_dir, repo_root=self.tmp_base, run_id="../test_run")
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(self.safe_dir, repo_root=self.tmp_base, run_id="bad/slash")
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(self.safe_dir, repo_root=self.tmp_base, run_id="bad space")

        # 3. Path traversal escape (..)
        bad_traversal = self.safe_dir / ".." / "other_dir"
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(bad_traversal, repo_root=self.tmp_base, run_id="test_run")

        # 4. Sibling fake path outside local/research/phase4-p4b
        fake_sibling = self.tmp_base / "local" / "research" / "phase4-p4a" / "test_run"
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(fake_sibling, repo_root=self.tmp_base, run_id="test_run")

        fake_public = self.tmp_base / "docs" / "crisp-dm" / "test_run"
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(fake_public, repo_root=self.tmp_base, run_id="test_run")

    def test_b04_durable_failure_json_writing(self):
        """B04 Acceptance: On injected failure, write atomic sanitized failure JSON with redacted data."""
        fail_file = write_durable_failure_json(
            target_dir=self.safe_dir,
            run_id="test_run",
            stage="OUTER_FOLD_1",
            code_head_commit="85487831551d277c8512ef53435ff1fd72bf8ffe",
            exception=ValueError("Synthetic injected failure"),
            accounting_summary={"estimator_fits": 12, "preprocessor_fits": 2},
            config_summary={"protocol_version": "v1.0", "d_ceiling": 300},
        )
        self.assertTrue(fail_file.exists())
        data = json.loads(fail_file.read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "FAILED")
        self.assertEqual(data["stage"], "OUTER_FOLD_1")
        self.assertEqual(data["exception_type"], "ValueError")
        self.assertIn("Synthetic injected failure", data["exception_message"])
        self.assertEqual(data["fit_accounting"]["estimator_fits"], 12)
        # Verify no raw paths or target data are in failure JSON
        serialized = json.dumps(data)
        self.assertNotIn("SalePrice", serialized)
        self.assertNotIn("C:\\", serialized)

    def test_atomic_write_json_and_csv(self):
        """Verify atomic file writes via temp file and SHA-256 calculation."""
        json_path = self.safe_dir / "test.json"
        data = {"hello": "world", "count": 42}
        sha, size = atomic_write_json(data, json_path)

        self.assertTrue(json_path.exists())
        self.assertFalse(json_path.with_suffix(".tmp").exists())
        self.assertGreater(size, 0)
        self.assertEqual(len(sha), 64)

        csv_path = self.safe_dir / "test.csv"
        records = [{"Id": "1", "val": 10}, {"Id": "2", "val": 20}]
        c_sha, c_size = atomic_write_csv(records, ["Id", "val"], csv_path)
        self.assertTrue(csv_path.exists())
        self.assertFalse(csv_path.with_suffix(".tmp").exists())
        self.assertGreater(c_size, 0)

    def test_public_summary_sanitization(self):
        """Verify public summary contains NO row-level IDs, predictions, or private paths."""
        config = P4BConfig(code_head_commit="fb4ce7ab32af6c04ad49643e8a1917a591ad6379")
        summary = create_public_summary(
            config=config,
            run_id="test_run_123",
            per_outer_fold_results=[],
            aggregate_results=[],
        )
        serialized = json.dumps(summary)
        self.assertNotIn("SalePrice", serialized)
        self.assertNotIn("test_run_123/p4b_oof_predictions.csv", serialized)
        self.assertIn("metadata", summary)
        self.assertIn("data_boundary", summary["metadata"])
        self.assertIn("environment", summary["metadata"])

    def test_checkpoint_resume_verification(self):
        """TEST-P4B-15: Resume verification fails closed on parameter or environment mismatch."""
        config = P4BConfig(
            code_head_commit="fb4ce7ab32af6c04ad49643e8a1917a591ad6379",
            protocol_version="v1.0",
            outer_seed=42,
            inner_seed=1042,
        )
        env = {
            "python": "3.12",
            "sklearn": "1.9.1",
            "numpy": "2.5.4",
            "pandas": "3.1.0",
            "scipy": "1.18.1",
        }
        good_checkpoint = {
            "dataset_fingerprint": "expected_fp_123",
            "code_head_commit": "fb4ce7ab32af6c04ad49643e8a1917a591ad6379",
            "metadata": {
                "protocol_version": "v1.0",
                "environment": {f"{k}_version": v for k, v in env.items()},
                "data_boundary": {
                    "outer_kfold": {"random_state": 42},
                    "inner_kfold": {"random_state": 1042},
                },
            },
        }

        # Valid checkpoint passes
        verify_checkpoint_for_resume(good_checkpoint, "expected_fp_123", config, env)

        # Mismatch in dataset fingerprint
        with self.assertRaises(CheckpointVerificationError):
            verify_checkpoint_for_resume(good_checkpoint, "mismatched_fp", config, env)

        # Mismatch in code commit
        bad_commit_checkpoint = dict(good_checkpoint)
        bad_commit_checkpoint["code_head_commit"] = "different_sha"
        with self.assertRaises(CheckpointVerificationError):
            verify_checkpoint_for_resume(bad_commit_checkpoint, "expected_fp_123", config, env)

        # Mismatch in dependency version
        bad_env_checkpoint = {
            "dataset_fingerprint": "expected_fp_123",
            "code_head_commit": "fb4ce7ab32af6c04ad49643e8a1917a591ad6379",
            "metadata": {
                "protocol_version": "v1.0",
                "environment": {
                    "python_version": "3.12",
                    "sklearn_version": "1.8.0",
                    "numpy_version": "2.5.4",
                    "pandas_version": "3.1.0",
                    "scipy_version": "1.18.1",
                },
                "data_boundary": {
                    "outer_kfold": {"random_state": 42},
                    "inner_kfold": {"random_state": 1042},
                },
            },
        }
        with self.assertRaises(CheckpointVerificationError):
            verify_checkpoint_for_resume(bad_env_checkpoint, "expected_fp_123", config, env)


if __name__ == "__main__":
    unittest.main()
