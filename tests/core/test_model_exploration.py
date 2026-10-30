import hashlib
import json
import statistics
import tempfile
import shutil
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from housing_regression.model_exploration import (
    ModelExplorationError,
    build_phase5_exploration,
    build_phase4_exploration,
)
from housing_regression.model_exploration_package import (
    ExplorationPackageError,
    validate_model_exploration_package,
)


METHOD_CANDIDATES = {
    "ols_baseline": [{"features": "all"}],
    "pearson": [{"k": k} for k in (2, 3, 5, 10, 20)],
    "mutual_information": [{"k": k} for k in (2, 3, 5, 10, 20)],
    "lasso": [{"alpha": alpha} for alpha in (0.1, 1.0, 10.0, 100.0)],
    "elastic_net": [
        {"alpha": alpha, "l1_ratio": ratio}
        for alpha in (0.1, 1.0, 10.0, 100.0)
        for ratio in (0.2, 0.5, 0.8)
    ],
    "ridge_rfe": [{"k": k} for k in (2, 3, 5, 10, 20)],
}


def _sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def historical_fixture():
    data_digest = _sha("development data")
    full_fold_digest = _sha("outer folds")
    metadata = {
        "run_id": "development_20261026_01",
        "data_boundary": {
            "development_rows": 1168,
            "dataset_fingerprint_verified": True,
            "digest_provenance": "VERIFIED_MATCH",
            "outer_fold_digest_expected": full_fold_digest,
            "outer_kfold": {"n_splits": 3, "shuffle": True, "random_state": 42},
        },
    }
    summary = {"metadata": metadata, "aggregate_results": [], "per_outer_fold_results": []}
    for method, candidates in METHOD_CANDIDATES.items():
        for candidate_index, candidate in enumerate(candidates):
            config_hash = _sha(f"{method}:{candidate}")
            invalid = method == "lasso" and candidate_index < 2
            metrics = {
                "rmse": [10.0 + candidate_index + fold for fold in range(3)],
                "mae": [5.0 + candidate_index + fold for fold in range(3)],
                "r2": [0.5 + candidate_index / 100 + fold / 1000 for fold in range(3)],
            }
            count = [4 + fold for fold in range(3)]
            fold_digests = [_sha(f"fold:{fold}") for fold in range(3)]
            for fold in range(3):
                completed = not invalid
                summary["per_outer_fold_results"].append({
                    "run_id": "development_20261026_01",
                    "method": method,
                    "candidate": candidate,
                    "config_hash": config_hash,
                    "data_digest": data_digest,
                    "fold_digest": fold_digests[fold],
                    "fold": fold,
                    "seed": 42,
                    "git_sha": "a" * 40,
                    "status": "COMPLETED" if completed else "INVALID",
                    "primary_valid": completed,
                    "rmse": metrics["rmse"][fold] if completed else None,
                    "mae": metrics["mae"][fold] if completed else None,
                    "r2": metrics["r2"][fold] if completed else None,
                    "encoded_count": count[fold] if completed else 0,
                    "selected_encoded_names": [f"feature_{fold}"] if completed else [],
                    "selected_raw_sources": [f"raw_{fold}"] if completed else [],
                    "feature_lineage": ([{
                        "encoded_name": f"feature_{fold}",
                        "raw_source_columns": [f"raw_{fold}"],
                        "provenance_status": "RESOLVED",
                    }] if completed else []),
                })
            aggregate = {
                "method": method,
                "config_hash": config_hash,
                "candidate": candidate,
                "status": "INVALID" if invalid else "COMPLETED",
                "expected_fold_count": 3,
                "observed_fold_count": 3,
                "valid_fold_count": 0 if invalid else 3,
                "coverage_complete": not invalid,
                "mean_selected_encoded_count": 0 if invalid else statistics.mean(count),
                "invalid_reasons": ["empty selection"] if invalid else [],
                "method_winner": candidate_index == len(candidates) - 1,
            }
            if not invalid:
                for metric in ("rmse", "mae", "r2"):
                    aggregate[f"selection_primary_cv_{metric}"] = statistics.mean(metrics[metric])
                    aggregate[f"selection_primary_cv_{metric}_sd"] = statistics.stdev(metrics[metric])
            else:
                for metric in ("rmse", "mae", "r2"):
                    aggregate[f"selection_primary_cv_{metric}"] = None
                    aggregate[f"selection_primary_cv_{metric}_sd"] = None
            summary["aggregate_results"].append(aggregate)

    summary_bytes = json.dumps(summary, separators=(",", ":")).encode()
    summary_sha = hashlib.sha256(summary_bytes).hexdigest()
    manifest = {
        "run_id": "development_20261026_01",
        "code_head_commit": "a" * 40,
        "phase3_contract_version": "v2.0",
        "dataset_provenance": {
            "development_rows": 1168,
            "canonical_development_dataset_sha256": data_digest,
            "outer_fold_digest_expected": full_fold_digest,
            "verification_status": "VERIFIED_MATCH",
        },
        "file_inventory": [{"relative_path": "p4b_public_summary.json", "sha256": summary_sha}],
    }
    manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode()
    return summary, manifest, summary_bytes, manifest_bytes


class HistoricalModelExplorationTests(unittest.TestCase):
    def _current_exploration_package(self):
        index = json.loads(Path("web/data/current-release.json").read_text(encoding="utf-8"))
        item = next(entry for entry in index["cases"] if entry["case_id"] == "ames-full-model-exploration")
        return Path("web/data") / Path(item["package_ref"]).parent

    def test_exports_only_complete_historical_aggregate_views(self):
        summary, manifest, summary_bytes, manifest_bytes = historical_fixture()
        phase4, artifacts = build_phase4_exploration(
            summary, manifest, summary_bytes, manifest_bytes, "ames-full-model-exploration"
        )
        self.assertEqual(32, len(phase4["configurations"]))
        self.assertEqual(30, sum(item["status"] == "VERIFIED" for item in phase4["configurations"]))
        self.assertEqual(2, sum(item["status"] == "ERROR" for item in phase4["configurations"]))
        self.assertEqual(30, len(artifacts["phases/phase-04/charts/method-comparison.json"]["points"]))
        self.assertEqual(30, len(artifacts["phases/phase-04/charts/feature-count-vs-cv-rmse.json"]["points"]))
        self.assertEqual("development_20261026_01", phase4["execution_runs"][0]["execution_run_id"])
        self.assertTrue(all("actual" not in json.dumps(doc) for doc in artifacts.values()))

    def test_rejects_summary_bytes_not_bound_by_manifest(self):
        summary, manifest, summary_bytes, manifest_bytes = historical_fixture()
        with self.assertRaisesRegex(ModelExplorationError, "summary SHA"):
            build_phase4_exploration(summary, manifest, summary_bytes + b" ", manifest_bytes, "case")

    def test_rejects_row_level_prediction_material(self):
        summary, manifest, summary_bytes, manifest_bytes = historical_fixture()
        summary["per_outer_fold_results"][0]["oof_records"] = [{"actual": 10, "predicted": 11}]
        summary_bytes = json.dumps(summary, separators=(",", ":")).encode()
        manifest["file_inventory"][0]["sha256"] = hashlib.sha256(summary_bytes).hexdigest()
        manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode()
        with self.assertRaisesRegex(ModelExplorationError, "row-level prediction"):
            build_phase4_exploration(summary, manifest, summary_bytes, manifest_bytes, "case")

    def test_rejects_mixed_fold_membership_across_candidates(self):
        summary, manifest, summary_bytes, manifest_bytes = historical_fixture()
        summary["per_outer_fold_results"][0]["fold_digest"] = _sha("different fold")
        summary_bytes = json.dumps(summary, separators=(",", ":")).encode()
        manifest["file_inventory"][0]["sha256"] = hashlib.sha256(summary_bytes).hexdigest()
        manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode()
        with self.assertRaisesRegex(ModelExplorationError, "membership digest"):
            build_phase4_exploration(summary, manifest, summary_bytes, manifest_bytes, "case")

    def _phase5_documents(self):
        summary, manifest, summary_bytes, manifest_bytes = historical_fixture()
        phase4, phase4_artifacts = build_phase4_exploration(
            summary, manifest, summary_bytes, manifest_bytes, "ames-full-model-exploration"
        )
        results = []
        folds = []
        for config in phase4["configurations"]:
            metadata = phase4_artifacts[config["metadata_ref"]]
            if config["status"] != "VERIFIED":
                continue
            metrics = phase4_artifacts[config["cv_metrics_ref"]]["mean_fold_metrics"]
            cv_folds = phase4_artifacts[config["cv_metrics_ref"]]["fold_results"]
            results.append({
                "config_hash": metadata["historical_config_hash"],
                "method": config["method_id"],
                "candidate": config["params"],
                "mean_fold_metrics": {key: metrics[key] for key in ("rmse", "mae", "r2")},
                "mean_fold_sample_sd": {key: metrics[f"{key}_sample_sd"] for key in ("rmse", "mae", "r2")},
                "pooled_oof_metrics": {"n": 1168, "rmse": metrics["rmse"] + 0.5,
                                       "mae": metrics["mae"] + 0.25, "r2": metrics["r2"] - 0.01},
            })
            for fold_row in cv_folds:
                fold = fold_row["fold"]
                folds.append({"config_hash": metadata["historical_config_hash"], "method": config["method_id"],
                              "fold": fold, "n": 389,
                              **{metric: fold_row[metric] for metric in ("rmse", "mae", "r2")}})
        oof = {"run_id": "development_20261026_01", "oof_publication": "PRIVATE_SOURCE_ROWS_NOT_INCLUDED",
               "source_oof_sha256": "f" * 64,
               "development_data_sha256": manifest["dataset_provenance"]["canonical_development_dataset_sha256"],
               "fold_sha256": manifest["dataset_provenance"]["outer_fold_digest_expected"],
               "configurations": results, "fold_metrics": folds}
        document, _assets = build_phase5_exploration(
            phase4, phase4_artifacts, oof, "ames-full-model-exploration", "ames-full-model-exploration-20261028-01"
        )
        return phase4, phase4_artifacts, oof, document, _assets

    def test_phase5_keeps_verified_metrics_separate_from_publication_review(self):
        phase4, phase4_artifacts, oof, document, _assets = self._phase5_documents()
        self.assertEqual("PLANNED", document["status"])
        self.assertEqual("PENDING", document["publication_review"])
        self.assertEqual(60, len(document["evaluations"]))
        self.assertTrue(all(metric["status"] == "VERIFIED"
                            for evaluation in document["evaluations"]
                            for metric in evaluation["metrics"].values()))
        schema_path = Path("docs/contracts/schemas/phase-05.schema.json")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document))
        self.assertEqual([], errors)
        cv = next(item for item in document["evaluations"] if item["metric_source"] == "cv_fold_mean")
        pooled = next(item for item in document["evaluations"] if item["metric_source"] == "pooled_oof")
        self.assertNotEqual(cv["metrics"]["rmse"]["value"], pooled["metrics"]["rmse"]["value"])

    def test_phase5_rejects_oof_data_or_fold_digest_mismatch(self):
        phase4, artifacts, oof, _document, _assets = self._phase5_documents()
        for key in ("development_data_sha256", "fold_sha256"):
            mismatched = dict(oof)
            mismatched[key] = "d" * 64 if key.startswith("development") else "e" * 64
            with self.subTest(key=key), self.assertRaisesRegex(ModelExplorationError, "digest"):
                build_phase5_exploration(phase4, artifacts, mismatched, "ames-full-model-exploration", "release-01")

    def test_phase5_rejects_mean_metrics_that_do_not_match_phase4_folds(self):
        phase4, artifacts, oof, _document, _assets = self._phase5_documents()
        mutated = json.loads(json.dumps(oof))
        mutated["configurations"][0]["mean_fold_metrics"]["rmse"] += 1
        with self.assertRaisesRegex(ModelExplorationError, "mean-fold rmse"):
            build_phase5_exploration(phase4, artifacts, mutated, "ames-full-model-exploration", "release-01")

    def test_phase5_rejects_fold_metric_mismatch_even_when_mean_is_unchanged(self):
        phase4, artifacts, oof, _document, _assets = self._phase5_documents()
        mutated = json.loads(json.dumps(oof))
        config_hash = mutated["configurations"][0]["config_hash"]
        fold_rows = [item for item in mutated["fold_metrics"] if item["config_hash"] == config_hash]
        original_mean = statistics.mean(item["rmse"] for item in fold_rows)
        fold_rows[0]["rmse"] += 1
        fold_rows[1]["rmse"] -= 1
        self.assertEqual(original_mean, statistics.mean(item["rmse"] for item in fold_rows))
        with self.assertRaisesRegex(ModelExplorationError, "fold 0 rmse"):
            build_phase5_exploration(phase4, artifacts, mutated, "ames-full-model-exploration", "release-01")

    def test_package_validator_rejects_mismatched_phase5_digest(self):
        case_root = self._current_exploration_package()
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "case"
            shutil.copytree(case_root, copied)
            fold_path = copied / "phases/phase-05/fold-metrics.json"
            fold_doc = json.loads(fold_path.read_text(encoding="utf-8"))
            fold_doc["development_data_sha256"] = "d" * 64
            fold_path.write_text(json.dumps(fold_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            package_path = copied / "package.json"
            package = json.loads(package_path.read_text(encoding="utf-8"))
            entry = next(item for item in package["files"] if item["path"] == "phases/phase-05/fold-metrics.json")
            payload = fold_path.read_bytes()
            entry["bytes"] = len(payload)
            entry["sha256"] = hashlib.sha256(payload).hexdigest()
            package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ExplorationPackageError, "identities disagree|data/fold digests"):
                validate_model_exploration_package(copied, Path("."))

    def test_package_validator_rejects_phase5_mean_metric_mismatch(self):
        case_root = self._current_exploration_package()
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "case"
            shutil.copytree(case_root, copied)
            eval_path = copied / "phases/phase-05/evaluations.json"
            evaluation_doc = json.loads(eval_path.read_text(encoding="utf-8"))
            cv_evaluation = next(item for item in evaluation_doc["evaluations"]
                                 if item["metric_source"] == "cv_fold_mean")
            cv_evaluation["metrics"]["rmse"]["value"] += 10
            eval_path.write_text(json.dumps(evaluation_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            package_path = copied / "package.json"
            package = json.loads(package_path.read_text(encoding="utf-8"))
            entry = next(item for item in package["files"] if item["path"] == "phases/phase-05/evaluations.json")
            payload = eval_path.read_bytes()
            entry["bytes"] = len(payload)
            entry["sha256"] = hashlib.sha256(payload).hexdigest()
            package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ExplorationPackageError, "evaluation value"):
                validate_model_exploration_package(copied, Path("."))


if __name__ == "__main__":
    unittest.main()
