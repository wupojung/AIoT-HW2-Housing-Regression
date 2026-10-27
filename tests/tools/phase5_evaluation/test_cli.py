from __future__ import annotations

import hashlib
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
            ["python3", str(CLI_PATH), "--help"], cwd=REPO_ROOT,
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
