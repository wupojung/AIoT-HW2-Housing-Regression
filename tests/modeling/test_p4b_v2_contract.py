"""Bounded pure contract tests for the protocol-v2 Phase B implementation."""

from __future__ import annotations

import copy
import random
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "python" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from housing_regression.modeling.p4b_runner import (
    P4BConfig,
    P4BRunner,
    compute_pearson_correlations,
)
from housing_regression.modeling.p4b_v2 import (
    LineageResolutionError,
    RunControlState,
    make_task_id,
    rank_features_by_score,
    require_matching_process_identity,
    resolve_feature_lineage,
    task_config_hash,
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
            "Id": f"SYNTHETIC-{i + offset + 1}",
            "LotArea": str(area),
            "OverallQual": str(quality),
            "Neighborhood": ("A", "B", "C")[i % 3],
            "SalePrice": str(20000 + area * 5 + quality * 7000 + rng.randrange(3000)),
        })
    return rows


class P4BV2ContractTests(unittest.TestCase):
    def aggregation_config_and_rows(self):
        config = P4BConfig(
            code_head_commit="a" * 40,
            active_methods=["pearson"],
            k_candidates=(2, 3),
        )
        identity = {
            "run_id": "synthetic_aggregate_run",
            "git_sha": config.code_head_commit,
            "data_digest": "d" * 64,
            "fold_digest": "f" * 64,
            "package_versions": {
                "python": "3.x", "sklearn": "1.x", "numpy": "2.x",
                "pandas": "3.x", "scipy": "1.x",
            },
        }
        rows = []
        for method, candidate in task_specs(config):
            for fold in (0, 1, 2):
                primary_track = "all_features_ols" if method == "ols_baseline" else "selected_to_ols"
                metric = 900.0 + fold if method == "ols_baseline" else float(candidate.get("k", 2) * 100 + fold)
                row = {
                    **identity,
                    "task_id": make_task_id(identity["run_id"], method, candidate, fold),
                    "method": method,
                    "candidate": dict(candidate),
                    "fold": fold,
                    "config_hash": task_config_hash(config, method, candidate),
                    "track": "baseline" if method == "ols_baseline" else "primary",
                    "primary_track": primary_track,
                    "status": "COMPLETED",
                    "primary_valid": True,
                    "rmse": metric,
                    "mae": metric / 2,
                    "r2": 0.8,
                    "encoded_count": int(candidate.get("k", 8)) if method != "ols_baseline" else 35,
                }
                if method == "pearson" and candidate.get("k") == 3:
                    row["native_diagnostic"] = {"rmse": 0.001, "mae": 0.001, "r2": 1.0}
                rows.append(row)
        return config, identity, rows

    @staticmethod
    def find_aggregate(aggregates, method, candidate):
        return next(
            row for row in aggregates
            if row["method"] == method and row["candidate"] == candidate
        )

    def test_one_layer_fold_has_ols_baseline_and_selected_methods_without_inner_fits(self):
        config = P4BConfig(
            code_head_commit="synthetic-code-sha",
            active_methods=["pearson", "mutual_information"],
            k_candidates=(2, 999),
            synthetic_test_mode=True,
            current_run_id="unit_run",
            current_data_digest="d" * 64,
            current_fold_digest="f" * 64,
        )
        runner = P4BRunner(config)
        result = runner.evaluate_synthetic_fold_for_test(0, synthetic_rows(12), synthetic_rows(4, 30))
        methods = {item["method"] for item in result["results"]}
        self.assertEqual(methods, {"ols_baseline", "pearson", "mutual_information"})
        self.assertEqual(runner.accounting.preprocessor_fits, 1)
        self.assertTrue(all(item["task_id"].startswith("task_") for item in result["results"]))
        self.assertTrue(all(item["data_digest"] == "d" * 64 for item in result["results"]))
        self.assertTrue(all(item["fold_digest"] == "f" * 64 for item in result["results"]))
        self.assertEqual(len(result["oof_records"]), len(result["results"]) * 4)
        computed_diagnostics = [
            row["ols_diagnostics"] for row in result["results"]
            if row["primary_valid"]
        ]
        self.assertTrue(computed_diagnostics)
        for diagnostics in computed_diagnostics:
            self.assertEqual(diagnostics["status"], "COMPUTED")
            self.assertIsInstance(diagnostics["rank"], int)
            self.assertIsInstance(diagnostics["nullity"], int)
            self.assertIn("condition_number", diagnostics)
            self.assertIn("condition_number_effective", diagnostics)
            self.assertIn("tolerance", diagnostics)
        invalid_rows = [row for row in result["results"] if not row["primary_valid"]]
        self.assertTrue(invalid_rows)
        self.assertTrue(all(row["ols_diagnostics"]["status"] == "NOT_COMPUTED" for row in invalid_rows))
        selector_rows = [row for row in result["results"] if row["method"] in {"pearson", "mutual_information"}]
        self.assertTrue(all(isinstance(row["score_evidence"]["score_invalid"], bool) for row in selector_rows))
        self.assertTrue(all(len(row["score_evidence"]["invalid_score_features"]) <= 20 for row in selector_rows))

    def test_aggregation_requires_exact_valid_three_fold_coverage_for_each_expected_candidate(self):
        config, identity, rows = self.aggregation_config_and_rows()
        aggregates = P4BRunner.aggregate_task_results(rows, config, expected_identity=identity)
        baseline = self.find_aggregate(aggregates, "ols_baseline", {"features": "all"})
        first = self.find_aggregate(aggregates, "pearson", {"k": 2, "candidate_order": 0})
        second = self.find_aggregate(aggregates, "pearson", {"k": 3, "candidate_order": 1})
        self.assertTrue(baseline["coverage_complete"])
        self.assertEqual(baseline["expected_fold_count"], 3)
        self.assertEqual(baseline["observed_fold_count"], 3)
        self.assertEqual(baseline["valid_fold_count"], 3)
        self.assertFalse(baseline["winner_eligible"])
        self.assertTrue(first["method_winner"])
        self.assertTrue(second["winner_eligible"])
        self.assertGreater(second["selection_primary_cv_rmse"], first["selection_primary_cv_rmse"])
        self.assertLess(second["native_diagnostic_cv_rmse"], first["selection_primary_cv_rmse"])
        self.assertNotIn("method_winner", second)

        absent_candidate = [
            row for row in rows
            if not (row["method"] == "pearson" and row["candidate"].get("k") == 3)
        ]
        absent_result = self.find_aggregate(
            P4BRunner.aggregate_task_results(absent_candidate, config, expected_identity=identity),
            "pearson", {"k": 3, "candidate_order": 1},
        )
        self.assertEqual(absent_result["observed_fold_count"], 0)
        self.assertFalse(absent_result["winner_eligible"])
        self.assertIn("MISSING_FOLD", absent_result["invalid_reasons"])

        pearson_first = lambda source: self.find_aggregate(
            P4BRunner.aggregate_task_results(source, config, expected_identity=identity),
            "pearson", {"k": 2, "candidate_order": 0},
        )
        target = lambda source: next(
            row for row in source
            if row["method"] == "pearson" and row["candidate"]["k"] == 2 and row["fold"] == 2
        )

        missing = [row for row in rows if not (row["method"] == "pearson" and row["candidate"].get("k") == 2 and row["fold"] == 2)]
        self.assertFalse(pearson_first(missing)["coverage_complete"])
        self.assertIn("MISSING_FOLD", pearson_first(missing)["invalid_reasons"])

        duplicate = rows + [copy.deepcopy(next(
            row for row in rows if row["method"] == "pearson" and row["candidate"].get("k") == 2 and row["fold"] == 0
        ))]
        self.assertFalse(pearson_first(duplicate)["coverage_complete"])
        self.assertIn("DUPLICATE_FOLD", pearson_first(duplicate)["invalid_reasons"])

        out_of_range = copy.deepcopy(rows)
        target(out_of_range)["fold"] = 3
        result = pearson_first(out_of_range)
        self.assertFalse(result["coverage_complete"])
        self.assertIn("OUT_OF_RANGE_FOLD", result["invalid_reasons"])
        self.assertIn("MISSING_FOLD", result["invalid_reasons"])

        invalid_fold = copy.deepcopy(rows)
        target(invalid_fold)["fold"] = "2"
        result = pearson_first(invalid_fold)
        self.assertFalse(result["coverage_complete"])
        self.assertIn("INVALID_FOLD", result["invalid_reasons"])

        wrong_config = copy.deepcopy(rows)
        target(wrong_config)["config_hash"] = "0" * 64
        result = pearson_first(wrong_config)
        self.assertFalse(result["coverage_complete"])
        self.assertIn("CONFIG_HASH_MISMATCH", result["invalid_reasons"])

        wrong_identity = copy.deepcopy(rows)
        target(wrong_identity)["run_id"] = "another_run"
        result = pearson_first(wrong_identity)
        self.assertFalse(result["coverage_complete"])
        self.assertTrue(any("RUN_ID_MISMATCH" in reason for reason in result["invalid_reasons"]))

        wrong_candidate = copy.deepcopy(rows)
        target(wrong_candidate)["candidate"] = {"k": 99, "candidate_order": 0}
        result = pearson_first(wrong_candidate)
        self.assertFalse(result["coverage_complete"])
        self.assertIn("MISSING_FOLD", result["invalid_reasons"])
        unexpected = self.find_aggregate(
            P4BRunner.aggregate_task_results(wrong_candidate, config, expected_identity=identity),
            "pearson", {"k": 99, "candidate_order": 0},
        )
        self.assertFalse(unexpected["winner_eligible"])
        self.assertIn("UNEXPECTED_METHOD_CANDIDATE", unexpected["invalid_reasons"])

        invalid_fold = copy.deepcopy(rows)
        target(invalid_fold).update(status="INVALID", primary_valid=False)
        result = pearson_first(invalid_fold)
        self.assertFalse(result["coverage_complete"])
        self.assertIn("INVALID_TASK", result["invalid_reasons"])

        missing_baseline = [row for row in rows if not (row["method"] == "ols_baseline" and row["fold"] == 1)]
        baseline_result = self.find_aggregate(
            P4BRunner.aggregate_task_results(missing_baseline, config, expected_identity=identity),
            "ols_baseline", {"features": "all"},
        )
        self.assertFalse(baseline_result["coverage_complete"])
        self.assertFalse(baseline_result["winner_eligible"])

    def test_score_invalid_is_recorded_and_ranked_last(self):
        ranked, evidence = rank_features_by_score(
            [0.2, float("nan"), 0.8], ["feature_b", "feature_a", "feature_c"],
            score_kind="pearson",
        )
        self.assertEqual(ranked, [2, 0, 1])
        self.assertTrue(evidence["score_invalid"])
        self.assertEqual(evidence["score_invalid_reason"], "NONFINITE")
        self.assertEqual(evidence["invalid_score_features"], ["feature_a"])
        self.assertEqual(evidence["invalid_score_count"], 1)

        pearson_ranked, pearson_evidence = rank_features_by_score(
            [0.0, 0.0, 0.0], ["feature_z", "feature_a", "feature_m"],
            score_kind="pearson", constant_feature_mask=[False, True, False],
        )
        self.assertEqual(pearson_ranked, [2, 0, 1])
        self.assertTrue(pearson_evidence["score_invalid"])
        self.assertEqual(pearson_evidence["score_invalid_reason"], "CONSTANT_FEATURE")
        self.assertEqual(pearson_evidence["invalid_score_features"], ["feature_a"])

        mi_ranked, mi_evidence = rank_features_by_score(
            [0.5, 0.5, 0.5], ["feature_z", "feature_a", "feature_m"],
            score_kind="mutual_information",
        )
        self.assertEqual(mi_ranked, [1, 2, 0])
        self.assertFalse(mi_evidence["score_invalid"])
        self.assertIsNone(mi_evidence["score_invalid_reason"])

    def test_pearson_nonfinite_scorer_value_stays_invalid_through_ranking(self):
        X = np.asarray([
            [1.0, np.nan, 7.0],
            [2.0, 1.0, 7.0],
            [3.0, 2.0, 7.0],
            [4.0, 3.0, 7.0],
        ])
        y = np.asarray([1.0, 2.0, 3.0, 4.0])
        names = ["finite_signal", "nonfinite_z", "constant_a"]
        scores = np.abs(compute_pearson_correlations(X, y))
        constant_mask = np.all(X == X[0:1, :], axis=0)
        ranked, evidence = rank_features_by_score(
            scores, names, score_kind="pearson", constant_feature_mask=constant_mask,
        )

        self.assertTrue(np.isfinite(scores[0]))
        self.assertTrue(np.isnan(scores[1]))
        self.assertEqual(ranked, [0, 2, 1])
        self.assertTrue(evidence["score_invalid"])
        self.assertEqual(evidence["score_invalid_reason"], "NONFINITE+CONSTANT_FEATURE")
        self.assertEqual(evidence["invalid_score_features"], ["constant_a", "nonfinite_z"])
        self.assertEqual(evidence["invalid_score_features"][-1], names[ranked[-1]])

    def test_public_runner_fails_closed_on_macos_and_synthetic_seam_rejects_real_ids(self):
        runner = P4BRunner(P4BConfig(code_head_commit="synthetic-code-sha", synthetic_test_mode=True))
        train, val = synthetic_rows(12), synthetic_rows(4, 30)
        with patch("housing_regression.modeling.p4b_runner.os.name", "posix"):
            with self.assertRaisesRegex(RuntimeError, "FAIL_CLOSED"):
                runner.execute_outer_fold(0, train, val)
        self.assertEqual(runner.accounting.preprocessor_fits, 0)
        with self.assertRaisesRegex(ValueError, "SYNTHETIC-"):
            runner.evaluate_synthetic_fold_for_test(
                0, [{**train[0], "Id": "123"}], val
            )

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
        self.assertTrue(state.admit_task("candidate-1"))
        frozen = state.freeze()
        self.assertTrue(frozen["frozen"])
        self.assertFalse(state.admit_task("candidate-2"))
        stopped = state.stop_all()
        self.assertEqual(stopped["status"], "STOP_REQUESTED")
        self.assertTrue(stopped["stop_requested"])
        self.assertFalse(state.admit_task("candidate-3"))

    def test_freeze_and_stop_gate_is_shared_atomically_with_worker_state(self):
        class SharedGate:
            def __init__(self):
                self.value = 0
                self._lock = threading.RLock()

            def get_lock(self):
                return self._lock

        gate = SharedGate()
        coordinator_state = RunControlState("run_shared", shared_admission_flag=gate)
        worker_state = RunControlState("run_shared", shared_admission_flag=gate)
        self.assertTrue(worker_state.admit_task("candidate-admitted-before-freeze"))
        coordinator_state.freeze()
        self.assertFalse(worker_state.admit_task("candidate-after-freeze"))
        self.assertFalse(coordinator_state.begin_run("run_shared_again", SharedGate()))

        stopped_gate = SharedGate()
        coordinator_stop = RunControlState("run_stopped", shared_admission_flag=stopped_gate)
        worker_stop = RunControlState("run_stopped", shared_admission_flag=stopped_gate)
        coordinator_stop.stop_all()
        self.assertFalse(worker_stop.admit_task("candidate-after-stop"))

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
        oof = [{
            "Id": "synthetic-1",
            "fold": 1,
            "task_id": "task_fixture",
            "method": "pearson",
        }]
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
        with self.assertRaises(CheckpointVerificationError):
            verify_task_checkpoint_for_resume(checkpoint, **{**args, "expected_fold": 0})
        with self.assertRaises(CheckpointVerificationError):
            verify_task_checkpoint_for_resume(
                checkpoint, **{**args, "expected_candidate": {"k": 3, "candidate_order": 0}}
            )
        with self.assertRaises(CheckpointVerificationError):
            verify_task_checkpoint_for_resume(checkpoint, **{**args, "expected_data_digest": "e" * 64})
        with self.assertRaises(CheckpointVerificationError):
            verify_task_checkpoint_for_resume(
                checkpoint, **{**args, "expected_oof_ids": ["synthetic-1", "synthetic-2"]}
            )
        duplicate_oof_checkpoint = create_task_checkpoint(
            result, [oof[0], oof[0]], run_id="run_1", code_sha="a" * 40,
            data_digest="d" * 64, fold_digest="f" * 64,
        )
        with self.assertRaises(CheckpointVerificationError):
            verify_task_checkpoint_for_resume(
                duplicate_oof_checkpoint,
                **{**args, "expected_oof_ids": ["synthetic-1", "synthetic-2"]},
            )
        with self.assertRaises(CheckpointVerificationError):
            verify_task_checkpoint_for_resume(checkpoint, **{**args, "expected_fold_digest": "e" * 64})
        with self.assertRaises(CheckpointVerificationError):
            verify_task_checkpoint_for_resume(checkpoint, **{**args, "expected_code_sha": "e" * 40})
        corrupted = {**checkpoint, "result": {**result, "status": "FAILED"}}
        with self.assertRaises(CheckpointVerificationError):
            verify_task_checkpoint_for_resume(corrupted, **args)

    def test_restored_checkpoints_use_same_complete_coverage_gate(self):
        config, identity, rows = self.aggregation_config_and_rows()
        restored = []
        for row in rows:
            oof = [
                {
                    "Id": f"SYNTHETIC-{row['fold']}-{number}",
                    "fold": row["fold"],
                    "task_id": row["task_id"],
                    "method": row["method"],
                }
                for number in (0, 1)
            ]
            checkpoint = create_task_checkpoint(
                row, oof,
                run_id=identity["run_id"], code_sha=identity["git_sha"],
                data_digest=identity["data_digest"], fold_digest=identity["fold_digest"],
            )
            verify_task_checkpoint_for_resume(
                checkpoint,
                expected_run_id=identity["run_id"],
                expected_task_id=row["task_id"],
                expected_code_sha=identity["git_sha"],
                expected_data_digest=identity["data_digest"],
                expected_fold_digest=identity["fold_digest"],
                expected_config_hash=row["config_hash"],
                expected_method=row["method"],
                expected_candidate=row["candidate"],
                expected_fold=row["fold"],
                expected_package_versions=identity["package_versions"],
                expected_oof_ids=[f"SYNTHETIC-{row['fold']}-{n}" for n in (0, 1)],
            )
            restored.append(checkpoint["result"])

        complete = P4BRunner.aggregate_task_results(restored, config, expected_identity=identity)
        complete_candidate = self.find_aggregate(
            complete, "pearson", {"k": 2, "candidate_order": 0}
        )
        self.assertTrue(complete_candidate["coverage_complete"])
        self.assertTrue(complete_candidate["method_winner"])

        partial = [
            row for row in restored
            if not (row["method"] == "pearson" and row["candidate"].get("k") == 2 and row["fold"] == 2)
        ]
        partial_candidate = self.find_aggregate(
            P4BRunner.aggregate_task_results(partial, config, expected_identity=identity),
            "pearson", {"k": 2, "candidate_order": 0},
        )
        self.assertFalse(partial_candidate["coverage_complete"])
        self.assertNotIn("method_winner", partial_candidate)

        repeated = restored + [copy.deepcopy(next(
            row for row in restored
            if row["method"] == "pearson" and row["candidate"].get("k") == 2 and row["fold"] == 0
        ))]
        repeated_candidate = self.find_aggregate(
            P4BRunner.aggregate_task_results(repeated, config, expected_identity=identity),
            "pearson", {"k": 2, "candidate_order": 0},
        )
        self.assertFalse(repeated_candidate["coverage_complete"])
        self.assertIn("DUPLICATE_FOLD", repeated_candidate["invalid_reasons"])
        self.assertNotIn("method_winner", repeated_candidate)


if __name__ == "__main__":
    unittest.main()
