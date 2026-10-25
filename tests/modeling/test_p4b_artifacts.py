"""Tests for Issue #22 Phase 4-B-A Artifacts, provenance, and resume verification."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "python" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from housing_regression.modeling.p4b_artifacts import (
    CheckpointVerificationError,
    atomic_write_csv,
    atomic_write_json,
    compute_file_sha256_and_size,
    create_manifest,
    create_public_summary,
    is_path_git_ignored,
    verify_checkpoint_for_resume,
)
from housing_regression.modeling.p4b_runner import P4BConfig


class P4BArtifactsTests(unittest.TestCase):
    """Synthetic unit tests for artifact writing and safety boundaries."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_atomic_write_json_and_csv(self):
        """Verify atomic file writes via temp file and SHA-256 calculation."""
        json_path = self.tmp_dir / "test.json"
        data = {"hello": "world", "count": 42}
        sha, size = atomic_write_json(data, json_path)

        self.assertTrue(json_path.exists())
        self.assertFalse(json_path.with_suffix(".tmp").exists())
        self.assertGreater(size, 0)
        self.assertEqual(len(sha), 64)

        # Verify CSV atomic write
        csv_path = self.tmp_dir / "test.csv"
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
        self.assertNotIn("SalePrice", serialized)  # No raw target values
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
                    "sklearn_version": "1.8.0",  # mismatched
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
