from __future__ import annotations

import hashlib
import csv
import importlib.util
import json
import platform
import subprocess
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI_PATH = REPO_ROOT / "tools" / "phase5_evaluation" / "cli.py"
SCHEMA_PATH = REPO_ROOT / "tools" / "phase5_evaluation" / "evaluation-index.schema.json"

spec = importlib.util.spec_from_file_location("phase5_cli", CLI_PATH)
phase5_cli = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(phase5_cli)


class Phase5CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="phase5-synthetic-")
        self.root = Path(self.temp.name)
        self.input_root = self.root / "input"
        self.output_root = self.root / "output"
        self.input_root.mkdir()
        self.output_root.mkdir()
        self.gate_path = self.root / "gate.json"

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, path: Path, value) -> Path:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def write_source(self, name="predictions.json") -> tuple[Path, str]:
        source = {
            "fixture_kind": "synthetic",
            "rows": [
                {"fold_id": "fold-1", "actual": 10, "predicted": 12},
                {"fold_id": "fold-1", "actual": 20, "predicted": 18},
                {"fold_id": "fold-1", "actual": 30, "predicted": 25},
                {"fold_id": "fold-2", "actual": 40, "predicted": 42},
                {"fold_id": "fold-2", "actual": 50, "predicted": 47},
                {"fold_id": "fold-2", "actual": 60, "predicted": 65},
                {"fold_id": "fold-3", "actual": 70, "predicted": 66},
                {"fold_id": "fold-3", "actual": 80, "predicted": 83},
                {"fold_id": "fold-3", "actual": 90, "predicted": 88},
            ],
        }
        path = self.write_json(self.input_root / name, source)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return path, digest

    def write_gate(self, *, authorized=True, source_name=None, digest=None, output_root=None):
        gate = {
            "gate_id": "synthetic-test-gate",
            "authorized": authorized,
            "mode": "synthetic_only",
            "allowed_operations": ["export"],
            "input_root": str(self.input_root.resolve()),
            "input_allowlist": ([{"path": source_name, "sha256": digest}] if source_name else []),
            "output_root": str((output_root or self.output_root).resolve()),
            "host": {
                "platform": {"Darwin": "macos", "Windows": "windows"}.get(platform.system(), platform.system().lower()),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
                "python_executable": str(Path(sys.executable).resolve()),
                "host_id": socket.gethostname(),
            },
        }
        return self.write_json(self.gate_path, gate)

    def write_manifest(self, *, mode="synthetic", source_name="predictions.json", digest=None):
        manifest = {
            "manifest_version": 1,
            "mode": mode,
            "case_id": "synthetic-housing-demo",
        }
        if mode == "empty":
            manifest["reason_code"] = "NO_APPROVED_EVALUATIONS"
        else:
            manifest.update({
                "execution_run_id": "synthetic-run-01",
                "configuration_id": "synthetic-config-01",
                "prediction_origin": "synthetic_fold_specific_models",
                "protocol_version": "synthetic-protocol-v1",
                "target": {"column": "SyntheticTarget", "unit": "synthetic_units"},
                "source": {
                    "path": source_name,
                    "sha256": digest,
                    "kind": "synthetic_prediction_pairs",
                },
            })
        return self.write_json(self.input_root / "manifest.json", manifest)

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(CLI_PATH), *map(str, args)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )

    def export_synthetic(self):
        source, digest = self.write_source()
        manifest = self.write_manifest(digest=digest)
        self.write_gate(source_name=source.name, digest=digest)
        return self.run_cli(
            "export", "--manifest", manifest, "--gate", self.gate_path,
            "--output-root", self.output_root,
        )

    def test_help_and_argument_errors(self):
        help_result = subprocess.run(
            [sys.executable, str(CLI_PATH), "--help"], cwd=REPO_ROOT,
            text=True, capture_output=True,
        )
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("export", help_result.stdout)
        self.assertIn("validate", help_result.stdout)
        missing = self.run_cli("export")
        self.assertEqual(missing.returncode, 2)

    def test_authorized_empty_output_is_schema_valid(self):
        manifest = self.write_manifest(mode="empty")
        self.write_gate()
        result = self.run_cli(
            "export", "--manifest", manifest, "--gate", self.gate_path,
            "--output-root", self.output_root,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.output_root / "phases/phase-05/evaluations.json"
        index = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(index["status"], "UNAVAILABLE")
        self.assertEqual(index["evaluations"], [])
        self.assertIsNone(index["default_evaluation_id"])
        self.assertEqual(self.run_cli("validate", "--index", output).returncode, 0)

    def test_empty_export_requires_manifest_inside_gate_input_root(self):
        manifest = self.write_manifest(mode="empty")
        self.write_gate()
        outside = self.root / "outside"
        outside.mkdir()
        outside_manifest = self.write_json(
            outside / "manifest.json",
            json.loads(manifest.read_text(encoding="utf-8")),
        )
        misplaced = self.run_cli(
            "export", "--manifest", outside_manifest, "--gate", self.gate_path,
            "--output-root", self.output_root,
        )
        self.assertNotEqual(misplaced.returncode, 0)
        self.assertIn("NOT_AUTHORIZED", misplaced.stderr)
        self.assertFalse((self.output_root / "phases/phase-05/evaluations.json").exists())

        gate = json.loads(self.gate_path.read_text(encoding="utf-8"))
        gate.pop("input_root")
        self.write_json(self.gate_path, gate)
        missing_root = self.run_cli(
            "export", "--manifest", manifest, "--gate", self.gate_path,
            "--output-root", self.output_root,
        )
        self.assertNotEqual(missing_root.returncode, 0)
        self.assertIn("NOT_AUTHORIZED", missing_root.stderr)
        self.assertFalse((self.output_root / "phases/phase-05/evaluations.json").exists())

    def test_synthetic_metrics_are_separate_and_residual_sign_is_explicit(self):
        result = self.export_synthetic()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.output_root / "phases/phase-05/evaluations.json"
        index = json.loads(output.read_text(encoding="utf-8"))
        by_source = {item["metric_source"]: item for item in index["evaluations"]}
        fold_mean = by_source["cv_fold_mean"]
        pooled = by_source["pooled_oof"]
        self.assertNotEqual(fold_mean["evaluation_id"], pooled["evaluation_id"])
        self.assertEqual(fold_mean["linked_evaluation_ids"], [pooled["evaluation_id"]])
        self.assertEqual(pooled["linked_evaluation_ids"], [fold_mean["evaluation_id"]])
        self.assertNotEqual(fold_mean["metrics"]["rmse"]["value"], pooled["metrics"]["rmse"]["value"])
        self.assertAlmostEqual(pooled["metrics"]["mae"]["value"], 28 / 9)
        self.assertAlmostEqual(pooled["metrics"]["rmse"]["value"], 10 / 3)
        self.assertAlmostEqual(pooled["metrics"]["r2"]["value"], 59 / 60)
        self.assertAlmostEqual(fold_mean["metrics"]["mae"]["value"], (3 + 10 / 3 + 3) / 3)
        self.assertEqual(fold_mean["fold_summary"]["ddof"], 1)
        self.assertGreaterEqual(fold_mean["fold_summary"]["sample_sd"]["rmse"], 0)
        self.assertTrue(all(metric["status"] == "MOCK" for metric in pooled["metrics"].values()))
        self.assertTrue(all(item["asset_ref"] is None for item in pooled["figures"]))
        residuals = [row["actual"] - row["predicted"] for row in json.loads((self.input_root / "predictions.json").read_text())["rows"]]
        self.assertIn(-2, residuals)
        self.assertIn(2, residuals)
        residual_figure = next(item for item in pooled["figures"] if item["figure_id"] == "FIG-P5-02")
        self.assertEqual(residual_figure["axes"]["x"]["field"], "predicted")
        self.assertEqual(residual_figure["axes"]["y"]["field"], "actual_minus_predicted")
        self.assertEqual(residual_figure["axes"]["reference_line"], "y_equals_0")
        self.assertEqual(residual_figure["residual_sign"], "actual_minus_predicted")

    def test_denied_gate_and_digest_mismatch_fail_closed(self):
        source, digest = self.write_source()
        manifest = self.write_manifest(digest=digest)
        self.write_gate(authorized=False, source_name=source.name, digest=digest)
        denied = self.run_cli("export", "--manifest", manifest, "--gate", self.gate_path, "--output-root", self.output_root)
        self.assertEqual(denied.returncode, 3)
        self.assertIn("NOT_AUTHORIZED", denied.stderr)
        self.assertFalse((self.output_root / "phases/phase-05/evaluations.json").exists())

        self.write_gate(source_name=source.name, digest=digest)
        gate = json.loads(self.gate_path.read_text(encoding="utf-8"))
        gate["host"]["host_id"] = "unapproved-host"
        self.write_json(self.gate_path, gate)
        wrong_host = self.run_cli("export", "--manifest", manifest, "--gate", self.gate_path, "--output-root", self.output_root)
        self.assertEqual(wrong_host.returncode, 3)
        self.assertIn("HOST_MISMATCH", wrong_host.stderr)

        self.write_gate(source_name=source.name, digest="0" * 64)
        mismatch = self.run_cli("export", "--manifest", manifest, "--gate", self.gate_path, "--output-root", self.output_root)
        self.assertEqual(mismatch.returncode, 3)
        self.assertIn("HASH_MISMATCH", mismatch.stderr)
        self.assertFalse((self.output_root / "phases/phase-05/evaluations.json").exists())

        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        manifest_data["source"]["sha256"] = "0" * 64
        self.write_json(manifest, manifest_data)
        self.write_gate(source_name=source.name, digest="0" * 64)
        source_mismatch = self.run_cli("export", "--manifest", manifest, "--gate", self.gate_path, "--output-root", self.output_root)
        self.assertEqual(source_mismatch.returncode, 3)
        self.assertIn("HASH_MISMATCH", source_mismatch.stderr)
        self.assertFalse((self.output_root / "phases/phase-05/evaluations.json").exists())

    def test_source_path_traversal_is_rejected(self):
        source, digest = self.write_source()
        manifest = self.write_manifest(digest=digest)
        data = json.loads(manifest.read_text())
        data["source"]["path"] = "../outside.json"
        self.write_json(manifest, data)
        self.write_gate(source_name=source.name, digest=digest)
        result = self.run_cli("export", "--manifest", manifest, "--gate", self.gate_path, "--output-root", self.output_root)
        self.assertEqual(result.returncode, 3)
        self.assertIn("PATH_BLOCKED", result.stderr)
        self.assertFalse((self.output_root / "phases/phase-05/evaluations.json").exists())

        data["source"]["path"] = "predictions.json"
        self.write_json(manifest, data)
        alternate = self.root / "other-output"
        alternate.mkdir()
        self.write_gate(source_name=source.name, digest=digest, output_root=alternate)
        wrong_output = self.run_cli("export", "--manifest", manifest, "--gate", self.gate_path, "--output-root", self.output_root)
        self.assertEqual(wrong_output.returncode, 3)
        self.assertIn("PATH_BLOCKED", wrong_output.stderr)

    def test_no_overwrite_and_interrupted_atomic_write(self):
        target_dir = self.output_root / "phases/phase-05"
        target_dir.mkdir(parents=True)
        target = target_dir / "evaluations.json"
        target.write_text("sentinel", encoding="utf-8")
        manifest = self.write_manifest(mode="empty")
        self.write_gate()
        result = self.run_cli("export", "--manifest", manifest, "--gate", self.gate_path, "--output-root", self.output_root)
        self.assertEqual(result.returncode, 5)
        self.assertEqual(target.read_text(encoding="utf-8"), "sentinel")

        new_target = self.root / "atomic" / "evaluations.json"
        new_target.parent.mkdir(parents=True)
        with mock.patch.object(phase5_cli.os, "link", side_effect=OSError("simulated interrupted promotion")):
            with self.assertRaises(phase5_cli.CliError) as caught:
                phase5_cli._atomic_write_new(new_target, b"synthetic")
        self.assertEqual(caught.exception.code, "OUTPUT_WRITE_FAILED")
        self.assertFalse(new_target.exists())
        self.assertEqual(list(new_target.parent.glob(".phase5-*.tmp")), [])

    def _phase4_fixture(self):
        candidate = {"alpha": 100.0, "candidate_order": 3}
        config_id = "p4-" + hashlib.sha256(
            json.dumps(["lasso", "primary", candidate], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:24]
        tasks = []
        rows = []
        for fold, pairs in enumerate((((10, 12), (20, 19)), ((30, 29), (40, 42)), ((50, 52), (60, 58)))):
            task_id = f"task-{fold}"
            tasks.append({"task_id": task_id, "method": "lasso", "track": "primary", "primary_track": "selected_to_ols",
                          "fold": fold, "candidate": candidate, "status": "COMPLETED", "primary_valid": True})
            for index, (actual, predicted) in enumerate(pairs):
                rows.append({"Id": f"dev-{fold}-{index}", "fold": fold, "task_id": task_id,
                             "method": "lasso", "track": "primary", "actual": actual, "predicted": predicted})
        with tempfile.TemporaryDirectory(prefix="phase5-p4oof-") as temp:
            root = Path(temp)
            csv_path = root / "oof.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["Id", "fold", "task_id", "method", "track", "actual", "predicted"])
                writer.writeheader(); writer.writerows(rows)
            summary_path = self.write_json(root / "summary.json", {
                "metadata": {"run_id": "p4-run-01", "protocol_version": "p4b-v2",
                             "data_boundary": {"development_rows": len(rows)}},
                "per_outer_fold_results": tasks,
                "aggregate_results": [{"method": "lasso", "candidate": candidate,
                                       "status": "COMPLETED", "winner_eligible": True,
                                       "expected_fold_count": 3, "expected_folds": [0, 1, 2]}],
            })
            manifest = {"run_id": "p4-run-01", "phase3_contract_version": "p4b-v2"}
            gate = {"run_id": "p4-run-01", "protocol_version": "p4b-v2", "target": {"column": "SalePrice", "unit": "USD"},
                    "configurations": [{"configuration_id": config_id, "method": "lasso", "track": "primary", "candidate": candidate}]}
            data = phase5_cli._read_phase4_oof(summary_path, csv_path, manifest, gate,
                                               hashlib.sha256(summary_path.read_bytes()).hexdigest(),
                                               hashlib.sha256(csv_path.read_bytes()).hexdigest())
            return data, config_id

    def test_phase4_oof_join_metrics_and_pooled_diagnostics_use_only_synthetic_rows(self):
        data, config_id = self._phase4_fixture()
        index, plot_data = phase5_cli._build_phase4("synthetic-p4-case", data)
        self.assertEqual(len(index["evaluations"]), 2)
        by_source = {item["metric_source"]: item for item in index["evaluations"]}
        self.assertNotEqual(by_source["cv_fold_mean"]["evaluation_id"], by_source["pooled_oof"]["evaluation_id"])
        self.assertEqual(by_source["cv_fold_mean"]["linked_evaluation_ids"], [by_source["pooled_oof"]["evaluation_id"]])
        self.assertEqual(by_source["cv_fold_mean"]["fold_summary"]["ddof"], 1)
        self.assertEqual(by_source["pooled_oof"]["n"], 6)
        self.assertEqual([fig["figure_id"] for fig in by_source["pooled_oof"]["figures"]],
                         ["FIG-P5-02", "FIG-P5-01", "FIG-P5-03"])
        self.assertTrue(all(fig["evaluation_id"] == by_source["pooled_oof"]["evaluation_id"]
                            for fig in by_source["pooled_oof"]["figures"]))
        self.assertEqual(plot_data[by_source["pooled_oof"]["evaluation_id"]][0], (10.0, 12.0))
        self.assertEqual(config_id, by_source["pooled_oof"]["configuration_id"])
        with tempfile.TemporaryDirectory(prefix="phase5-p4oof-assets-") as temp:
            output_root = Path(temp)
            phase5_cli._write_real_figures(output_root, index, plot_data)
            phase5_cli._schema_validate(index)
            for figure in by_source["pooled_oof"]["figures"]:
                asset = output_root / "phases" / "phase-05" / figure["asset_ref"]
                self.assertTrue(asset.is_file())
                self.assertEqual(figure["sha256"], hashlib.sha256(asset.read_bytes()).hexdigest())
        phase5_cli._validate_identity(index)

    def test_phase4_oof_rejects_invalid_task_join_and_missing_prediction(self):
        data, _ = self._phase4_fixture()
        with tempfile.TemporaryDirectory(prefix="phase5-p4oof-bad-") as temp:
            root = Path(temp)
            csv_path = root / "oof.csv"
            csv_path.write_text("Id,fold,task_id,method,track,actual,predicted\nrow,0,unknown,lasso,primary,1,2\n", encoding="utf-8")
            summary_path = root / "summary.json"
            summary_path.write_text("{}", encoding="utf-8")
            manifest = {"run_id": "p4-run-01", "phase3_contract_version": "p4b-v2"}
            gate = {"run_id": "p4-run-01", "protocol_version": "p4b-v2"}
            with self.assertRaises(phase5_cli.CliError) as caught:
                phase5_cli._read_phase4_oof(summary_path, csv_path, manifest, gate, "0" * 64, "1" * 64)
            self.assertEqual(caught.exception.code, "JOIN_BLOCKED")

        data, _ = self._phase4_fixture()
        group = next(iter(data["groups"].values()))
        group["rows"][0] = (group["rows"][0][0], float("nan"))
        with self.assertRaises(phase5_cli.CliError):
            phase5_cli._build_phase4("synthetic-p4-case", data)

    def test_phase4_oof_manifest_inventory_and_gate_allowlist_are_exact(self):
        with tempfile.TemporaryDirectory(prefix="phase5-p4oof-allowlist-") as temp:
            root = Path(temp)
            summary = self.write_json(root / "p4b_public_summary.json", {"synthetic": True})
            oof = root / "p4b_oof_predictions.csv"
            oof.write_text("Id,fold,task_id,method,track,actual,predicted\n", encoding="utf-8")
            summary_sha = hashlib.sha256(summary.read_bytes()).hexdigest()
            oof_sha = hashlib.sha256(oof.read_bytes()).hexdigest()
            manifest = self.write_json(root / "p4b_manifest.json", {
                "file_inventory": [
                    {"relative_path": summary.name, "sha256": summary_sha, "is_public": True},
                    {"relative_path": oof.name, "sha256": oof_sha, "is_public": False},
                ],
            })
            manifest_sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
            gate = {"mode": "phase4_oof", "input_root": str(root), "manifest_sha256": manifest_sha,
                    "input_allowlist": [{"path": summary.name, "sha256": summary_sha},
                                        {"path": oof.name, "sha256": oof_sha}]}
            expected = {"p4b_manifest.json": manifest_sha,
                        "p4b_public_summary.json": summary_sha,
                        "p4b_oof_predictions.csv": oof_sha}
            with mock.patch.dict(phase5_cli.PHASE4_EVIDENCE_SHA256, expected):
                resolved_summary, resolved_summary_sha, resolved_oof, resolved_oof_sha = phase5_cli._resolve_phase4_files(
                    manifest, json.loads(manifest.read_text()), gate
                )
                self.assertEqual((resolved_summary, resolved_summary_sha), (summary.resolve(), summary_sha))
                self.assertEqual((resolved_oof, resolved_oof_sha), (oof.resolve(), oof_sha))
                gate["input_allowlist"].append({"path": "extra.csv", "sha256": "0" * 64})
                with self.assertRaises(phase5_cli.CliError) as caught:
                    phase5_cli._resolve_phase4_files(manifest, json.loads(manifest.read_text()), gate)
                self.assertEqual(caught.exception.code, "NOT_AUTHORIZED")

    def test_schema_and_cross_evaluation_join_validation(self):
        result = self.export_synthetic()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.output_root / "phases/phase-05/evaluations.json"
        index = json.loads(output.read_text(encoding="utf-8"))
        phase5_cli._schema_validate(index)
        index["evaluations"][1]["linked_evaluation_ids"] = []
        with self.assertRaises(phase5_cli.CliError) as caught:
            phase5_cli._validate_identity(index)
        self.assertEqual(caught.exception.code, "JOIN_BLOCKED")
        index["evaluations"][1]["linked_evaluation_ids"] = [index["evaluations"][0]["evaluation_id"]]
        index["evaluations"][1]["evaluation_id"] = index["evaluations"][0]["evaluation_id"]
        with self.assertRaises(phase5_cli.CliError) as duplicate:
            phase5_cli._validate_identity(index)
        self.assertEqual(duplicate.exception.code, "JOIN_BLOCKED")


if __name__ == "__main__":
    unittest.main()
