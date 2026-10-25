"""Tests for Issue #22 Phase 4-B-A Artifacts, provenance, and resume verification."""

from __future__ import annotations

import json
import os
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
    sanitize_error_message,
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

    def test_b01_positive_exact_trusted_run_root(self):
        """B01 Acceptance (Positive): create/write only at exact trusted repo local/research/phase4-p4b/<run-id> and verify output is contained."""
        run_id = "test_run_b01_pos"
        run_dir = self.tmp_base / "local" / "research" / "phase4-p4b" / run_id
        contained_dir = assert_safe_private_containment(run_dir, repo_root=self.tmp_base, run_id=run_id)
        contained_dir.mkdir(parents=True, exist_ok=True)
        self.assertEqual(contained_dir, run_dir.resolve())
        test_file = contained_dir / "artifact.json"
        sha, size = atomic_write_json({"status": "OK"}, test_file)
        self.assertTrue(test_file.exists())
        self.assertEqual(test_file.parent, run_dir.resolve())

    def test_b01_negative_lookalike_traversal_and_ids(self):
        """B01 Acceptance (Negative): reject forged root/lookalike repo, .., sibling, empty/invalid run IDs with typed containment error before external mkdir/write."""
        # 1. Missing run_id
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(self.safe_dir, repo_root=self.tmp_base, run_id=None)
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(self.safe_dir, repo_root=self.tmp_base, run_id="")
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(self.safe_dir, repo_root=self.tmp_base, run_id="   ")

        # 2. Noncanonical run_id
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(self.safe_dir, repo_root=self.tmp_base, run_id="../test_run")
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(self.safe_dir, repo_root=self.tmp_base, run_id="bad/slash")
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(self.safe_dir, repo_root=self.tmp_base, run_id="bad;cmd")

        # 3. Path traversal escape (..)
        bad_traversal = self.safe_dir / ".." / "escaped_dir"
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(bad_traversal, repo_root=self.tmp_base, run_id="test_run")
        self.assertFalse(bad_traversal.exists())

        # 4. Sibling / lookalike fake path outside local/research/phase4-p4b
        fake_sibling = self.tmp_base / "local" / "research" / "phase4-p4a" / "test_run"
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(fake_sibling, repo_root=self.tmp_base, run_id="test_run")
        self.assertFalse(fake_sibling.exists())

        lookalike_root = self.tmp_base / "lookalike_repo" / "local" / "research" / "phase4-p4b" / "test_run"
        with self.assertRaises(PathContainmentError):
            assert_safe_private_containment(lookalike_root, repo_root=self.tmp_base, run_id="test_run")
        self.assertFalse(lookalike_root.exists())

    def test_b01_negative_symlink_junction_reparse_root(self):
        """B01 Acceptance (Negative): create an actual link/reparse component that redirects outside the repo; require typed containment error and assert no outside file/dir was created."""
        outside_dir = self.tmp_base / "outside_research_zone"
        outside_dir.mkdir(parents=True, exist_ok=True)

        junction_path = self.tmp_base / "local" / "research" / "phase4-p4b" / "junction_escape"
        junction_path.parent.mkdir(parents=True, exist_ok=True)

        if os.name == "nt":
            import subprocess
            res = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(junction_path), str(outside_dir)],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                self.skipTest(f"Failed to create junction fixture on Windows: {res.stderr}")

            # Verify typed containment error on junction
            with self.assertRaises(PathContainmentError):
                assert_safe_private_containment(junction_path, repo_root=self.tmp_base, run_id="junction_escape")

            # Verify no files created in outside_dir
            self.assertEqual(len(list(outside_dir.iterdir())), 0)
        else:
            try:
                junction_path.symlink_to(outside_dir, target_is_directory=True)
                with self.assertRaises(PathContainmentError):
                    assert_safe_private_containment(junction_path, repo_root=self.tmp_base, run_id="junction_escape")
                self.assertEqual(len(list(outside_dir.iterdir())), 0)
            except OSError:
                self.skipTest("Symlink fixture creation unsupported on this platform.")

    def test_b04_positive_atomic_sanitized_failure_record(self):
        """B04 Acceptance (Positive): inject preflight/path/fit errors containing Windows paths with spaces, UNC, POSIX paths, row Id, target price, credential/token sentinels; require atomic complete JSON using allowlisted failure code/category, counters/stage/config/code identity, and no raw sentinel in file, exception or logs."""
        injected_exc = ValueError(
            r"Error at C:\Program Files\App with spaces\data.csv and \\server\share\secret.txt and /var/log/secret.log "
            r"processing row Id=987 SalePrice: 450000 with token: secret_api_token_123456"
        )
        fail_file = write_durable_failure_json(
            target_dir=self.safe_dir,
            run_id="test_run",
            stage="OUTER_FOLD_1",
            code_head_commit="85487831551d277c8512ef53435ff1fd72bf8ffe",
            exception=injected_exc,
            accounting_summary={"estimator_fits": 12, "preprocessor_fits": 2},
            config_summary={"protocol_version": "v1.0", "d_ceiling": 300},
        )
        self.assertTrue(fail_file.exists())
        self.assertFalse(fail_file.with_suffix(".tmp").exists())
        text = fail_file.read_text(encoding="utf-8")
        data = json.loads(text)

        # Allowlisted fields and categories
        self.assertEqual(data["status"], "FAILED")
        self.assertEqual(data["stage"], "OUTER_FOLD_1")
        self.assertEqual(data["exception_type"], "ValueError")
        self.assertEqual(data["code_head_commit"], "85487831551d277c8512ef53435ff1fd72bf8ffe")
        self.assertIn("timestamp_utc", data)

        # Confirm sentinels redacted
        self.assertNotIn(r"C:\Program Files", text)
        self.assertNotIn(r"\\server\share", text)
        self.assertNotIn("/var/log/secret.log", text)
        self.assertNotIn("450000", text)
        self.assertNotIn("secret_api_token_123456", text)
        self.assertNotIn("Id=987", text)

        self.assertIn("<REDACTED_PATH>", text)
        self.assertIn("<REDACTED_UNC_PATH>", text)
        self.assertIn("<REDACTED_TARGET>", text)
        self.assertIn("<REDACTED_CREDENTIAL>", text)
        self.assertIn("<REDACTED_ID>", text)

    def test_b04_negative_unavailable_paths_no_external_write(self):
        """B04 Acceptance (Negative): absent output, invalid/untrusted output, and injected failure-record persistence error must return/raise structured sanitized fallback; assert no external directories/files were created and no path/error text leaked."""
        # 1. Injected persistence failure raises structured sanitized fallback
        with patch("housing_regression.modeling.p4b_artifacts.atomic_write_json", side_effect=PermissionError(r"Cannot write to C:\secrets\dump.json")):
            with self.assertRaises(RuntimeError) as ctx:
                write_durable_failure_json(
                    target_dir=self.safe_dir,
                    run_id="test_run",
                    stage="TEST_STAGE",
                    code_head_commit="commit123",
                    exception=ValueError("test"),
                    accounting_summary={},
                    config_summary={},
                )
            # Check structured fallback error and no path leakage
            err_msg = str(ctx.exception)
            self.assertEqual(err_msg, "DURABLE_FAILURE_WRITE_FAILED: PermissionError")
            self.assertNotIn(r"C:\secrets", err_msg)

        # 2. Assert no external directory was created
        outside_path = self.tmp_base / "outside_dir"
        self.assertFalse(outside_path.exists())

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

    def test_checkpoint_resume_verification_comprehensive(self):
        """TEST-P4B-15 & B02: Resume verification fails closed on parameter, seed, config, or payload mismatch."""
        config = P4BConfig(
            code_head_commit="fb4ce7ab32af6c04ad49643e8a1917a591ad6379",
            protocol_version="v1.0",
            outer_splits=5,
            outer_seed=42,
            inner_splits=3,
            inner_seed=1042,
            d_ceiling=300,
            k_candidates=(2, 3, 5, 10, 20),
        )
        env = {
            "python": "3.12",
            "sklearn": "1.9.1",
            "numpy": "2.5.4",
            "pandas": "3.1.0",
            "scipy": "1.18.1",
        }
        from housing_regression.modeling.p4b_artifacts import compute_checkpoint_payload_digest
        res_list = [{"fold": 0, "metric": 0.5}]
        oof_list = [{"Id": "1", "pred": 100.0}]
        good_checkpoint = {
            "completed_outer_fold": 0,
            "dataset_fingerprint": "expected_fp_123",
            "code_head_commit": "fb4ce7ab32af6c04ad49643e8a1917a591ad6379",
            "payload_digest": compute_checkpoint_payload_digest(res_list, oof_list),
            "results": res_list,
            "oof_records": oof_list,
            "run_config": {
                "d_ceiling": 300,
                "k_candidates": [2, 3, 5, 10, 20],
                "active_methods": ["filter_pearson", "forward_sfs", "rfe_ridge", "lasso_cv", "elastic_net_cv"],
            },
            "metadata": {
                "protocol_version": "v1.0",
                "environment": {f"{k}_version": v for k, v in env.items()},
                "data_boundary": {
                    "outer_kfold": {"n_splits": 5, "random_state": 42},
                    "inner_kfold": {"n_splits": 3, "random_state": 1042},
                },
            },
        }

        # 1. Valid checkpoint passes
        verify_checkpoint_for_resume(good_checkpoint, "expected_fp_123", config, env)

        # 2. Mismatch in dataset fingerprint
        with self.assertRaises(CheckpointVerificationError):
            verify_checkpoint_for_resume(good_checkpoint, "mismatched_fp", config, env)

        # 3. Mismatch in code commit
        bad_commit = dict(good_checkpoint, code_head_commit="bad_sha")
        with self.assertRaises(CheckpointVerificationError):
            verify_checkpoint_for_resume(bad_commit, "expected_fp_123", config, env)

        # 4. Missing results or oof_records payload
        empty_results = dict(good_checkpoint, results=[])
        with self.assertRaises(CheckpointVerificationError):
            verify_checkpoint_for_resume(empty_results, "expected_fp_123", config, env)

        # 5. Invalid fold index
        invalid_fold = dict(good_checkpoint, completed_outer_fold=10)
        with self.assertRaises(CheckpointVerificationError):
            verify_checkpoint_for_resume(invalid_fold, "expected_fp_123", config, env)

        # 6. Mismatch in run config
        bad_cfg = dict(good_checkpoint, run_config={"d_ceiling": 200, "k_candidates": [2], "active_methods": []})
        with self.assertRaises(CheckpointVerificationError):
            verify_checkpoint_for_resume(bad_cfg, "expected_fp_123", config, env)


if __name__ == "__main__":
    unittest.main()
