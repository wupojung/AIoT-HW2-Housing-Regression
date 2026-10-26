"""Bounded pure contract tests for the protocol-v2 Phase B implementation."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "python" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from housing_regression.modeling.p4b_runner import P4BConfig, P4BRunner
from housing_regression.modeling.p4b_v2 import (
    LineageResolutionError,
    RunControlState,
    make_task_id,
    require_matching_process_identity,
    resolve_feature_lineage,
    task_specs,
)
from housing_regression.modeling.p4b_artifacts import (
    CheckpointVerificationError,
    create_task_checkpoint,
    verify_task_checkpoint_for_resume,
)


def synthetic_rows(count: int, offset: int = 0) -> list[dict[str, str]]:
    rng = random.Random(42 + offset)
    rows = []
    for i in range(count):
        area = 4000 + (i + offset) * 137
        quality = 2 + (i % 8)
        rows.append({
            "Id": str(i + offset + 1),
            "LotArea": str(area),
            "OverallQual": str(quality),
            "Neighborhood": ("A", "B", "C")[i % 3],
            "SalePrice": str(20000 + area * 5 + quality * 7000 + rng.randrange(3000)),
        })
    return rows


class P4BV2ContractTests(unittest.TestCase):
    def test_one_layer_fold_has_ols_baseline_and_selected_methods_without_inner_fits(self):
        config = P4BConfig(
            code_head_commit="synthetic-code-sha",
            active_methods=["pearson", "mutual_information"],
            k_candidates=(2,),
            synthetic_test_mode=True,
            current_run_id="unit_run",
            current_data_digest="d" * 64,
            current_fold_digest="f" * 64,
        )
        runner = P4BRunner(config)
        result = runner.execute_outer_fold(0, synthetic_rows(12), synthetic_rows(4, 30))
        methods = {item["method"] for item in result["results"]}
        self.assertEqual(methods, {"ols_baseline", "pearson", "mutual_information"})
        self.assertEqual(runner.accounting.preprocessor_fits, 1)
        self.assertTrue(all(item["task_id"].startswith("task_") for item in result["results"]))
        self.assertTrue(all(item["data_digest"] == "d" * 64 for item in result["results"]))
        self.assertTrue(all(item["fold_digest"] == "f" * 64 for item in result["results"]))
        self.assertEqual(len(result["oof_records"]), len(result["results"]) * 4)

    def test_task_ids_are_stable_and_fold_scoped(self):
        candidate = {"alpha": 1.0, "candidate_order": 1}
        first = make_task_id("run_1", "lasso", candidate, 0)
        self.assertEqual(first, make_task_id("run_1", "lasso", candidate, 0))
        self.assertNotEqual(first, make_task_id("run_1", "lasso", candidate, 1))
        self.assertEqual(task_specs(P4BConfig(code_head_commit="sha"))[0][0], "ols_baseline")

    def test_lineage_uses_real_multi_source_whitelist_and_fails_closed(self):
        basement = resolve_feature_lineage("HasBasement")
        self.assertEqual(basement["raw_source_columns"], ["BsmtQual", "TotalBsmtSF"])
        self.assertTrue(basement["is_derived"])
        self.assertEqual(resolve_feature_lineage("Neighborhood_NoRidge")["raw_source_columns"], ["Neighborhood"])
        with self.assertRaises(LineageResolutionError):
            resolve_feature_lineage("HasInventedFeature")

    def test_control_contract_is_run_scoped_and_never_signals_processes(self):
        state = RunControlState("run_1", status="RUNNING")
        self.assertEqual(state.status_snapshot()["status"], "RUNNING")
        frozen = state.freeze()
        self.assertTrue(frozen["frozen"])
        stopped = state.stop_all()
        self.assertEqual(stopped["status"], "STOP_REQUESTED")
        self.assertTrue(stopped["stop_requested"])

    def test_creation_identity_must_match_before_later_control(self):
        identity = {"pid": 10, "ppid": 5, "creation_time_ns": 123456}
        self.assertEqual(require_matching_process_identity(identity, dict(identity)), (10, 5, 123456))
        with self.assertRaises(ValueError):
            require_matching_process_identity(identity, {**identity, "creation_time_ns": 123457})
        with self.assertRaises(ValueError):
            require_matching_process_identity(identity, {**identity, "creation_time_ns": True})

    def test_task_checkpoint_verifies_run_and_payload_identity(self):
        result = {
            "task_id": "task_fixture",
            "method": "pearson",
            "candidate": {"k": 2, "candidate_order": 0},
            "fold": 1,
            "config_hash": "c" * 64,
            "status": "COMPLETED",
            "package_versions": {"python": "3.x", "sklearn": "1.x", "numpy": "2.x",
                                 "pandas": "3.x", "scipy": "1.x"},
        }
        oof = [{"Id": "synthetic-1", "fold": 1, "task_id": "task_fixture"}]
        checkpoint = create_task_checkpoint(
            result, oof, run_id="run_1", code_sha="a" * 40,
            data_digest="d" * 64, fold_digest="f" * 64,
        )
        args = dict(
            expected_run_id="run_1", expected_task_id="task_fixture",
            expected_code_sha="a" * 40, expected_data_digest="d" * 64,
            expected_fold_digest="f" * 64, expected_config_hash="c" * 64,
            expected_method="pearson", expected_candidate={"k": 2, "candidate_order": 0},
            expected_fold=1,
            expected_package_versions=result["package_versions"],
            expected_oof_ids=["synthetic-1"],
        )
        verify_task_checkpoint_for_resume(checkpoint, **args)
        with self.assertRaises(CheckpointVerificationError):
            verify_task_checkpoint_for_resume(checkpoint, **{**args, "expected_run_id": "other_run"})
        corrupted = {**checkpoint, "result": {**result, "status": "FAILED"}}
        with self.assertRaises(CheckpointVerificationError):
            verify_task_checkpoint_for_resume(corrupted, **args)


if __name__ == "__main__":
    unittest.main()
