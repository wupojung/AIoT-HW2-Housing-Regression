from __future__ import annotations

import hashlib
import csv
import argparse
import copy
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

    def _handoff_fixture(self, config_count=1):
        package_root = self.root / "case-package"
        (package_root / "phases/phase-04").mkdir(parents=True)
        (package_root / "phases/phase-05").mkdir()
        case_id, run_id, protocol_id = "synthetic-case", "synthetic-run", "protocol-v1"
        configurations = []
        model_configs = []
        for number in range(config_count):
            config_hash = hashlib.sha256(f"synthetic-config-{number}".encode()).hexdigest()
            config_id = "cfg-" + config_hash
            configurations.append({"configuration_id": config_id, "config_hash": config_hash,
                                   "method_id": "lasso", "track_id": "primary", "status": "COMPLETED",
                                   "fold_tasks": [{"fold_index": 0, "task_id": f"task-{number}-0"},
                                                  {"fold_index": 1, "task_id": f"task-{number}-1"}]})
            model_configs.append({"configuration_id": config_id, "execution_run_id": run_id,
                                  "method_id": "lasso", "track_id": "primary", "params": {"fixture": number},
                                  "protocol_id": protocol_id, "status": "VERIFIED"})
        case_doc = {"schema_version": "1.0.0", "case_id": case_id}
        modeling = {"schema_version": "1.0.0", "case_id": case_id, "status": "UNAVAILABLE",
                    "cv": {"training_rows": 4, "fold_count": 2, "protocol_id": protocol_id,
                           "status": "SOURCE_REPORTED_NOT_VERIFIED"},
                    "methods": [{"method_id": "lasso", "label": "Lasso", "parameters": []}],
                    "execution_runs": [{"execution_run_id": run_id, "source_manifest_sha256": "a" * 64,
                                         "status": "UNAVAILABLE"}],
                    "configurations": model_configs, "default_configuration_id": None, "charts": []}
        empty = phase5_cli._build_empty({"case_id": case_id})
        payloads = {"case.json": case_doc, "phases/phase-04/modeling.json": modeling,
                    "phases/phase-05/evaluations.json": empty}
        files = []
        for rel, value in payloads.items():
            raw = json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n"
            (package_root / rel).write_bytes(raw)
            files.append({"path": rel, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                          "mime": "application/json"})
        self.write_json(package_root / "package.json", {
            "package_schema_version": "1.0.0", "package_id": "synthetic-package", "case_id": case_id,
            "package_revision": "synthetic-r1", "package_status": "PLANNED",
            "publication": {"approved": False, "release_id": None, "review_status": "PENDING"},
            "case_ref": "case.json", "phases": {"phase5": {"status": "UNAVAILABLE",
                                                                  "data_ref": "phases/phase-05/evaluations.json"}},
            "asset_manifest_ref": None, "files": files})

        handoff_root = self.root / "handoff"
        handoff_root.mkdir()
        csv_path = handoff_root / "oof.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["row_id", "configuration_id", "fold_index", "task_id", "actual", "predicted"])
            for number, config in enumerate(configurations):
                for fold, values in ((0, ((10, 12), (20, 19))), (1, ((30, 29), (40, 42)))):
                    for row_number, (actual, predicted) in enumerate(values):
                        writer.writerow([f"c{number}-r{fold}-{row_number}", config["configuration_id"], fold,
                                         f"task-{number}-{fold}", actual, predicted])
        csv_sha = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        handoff = {"schema_version": "1.0.0", "case_id": case_id, "execution_run_id": run_id,
                   "protocol_id": protocol_id, "protocol_version": "p4b-v2", "population": "development_oof",
                   "target": {"column": "SalePrice", "unit": "USD"},
                   "source_artifacts": {"manifest_sha256": "a" * 64, "summary_sha256": "b" * 64,
                                         "oof_sha256": "c" * 64},
                   "csv": {"path": "oof.csv", "sha256": csv_sha,
                           "columns": ["row_id", "configuration_id", "fold_index", "task_id", "actual", "predicted"]},
                   "row_count": config_count * 4, "n_per_configuration": 4, "expected_fold_ids": [0, 1],
                   "configurations": configurations}
        handoff_path = self.write_json(handoff_root / "handoff.json", handoff)
        handoff_sha = hashlib.sha256(handoff_path.read_bytes()).hexdigest()
        gate = {"gate_id": "synthetic-handoff-gate", "authorized": True,
                "mode": "phase5_handoff_evaluation", "allowed_operations": ["evaluate_handoff"],
                "input_root": str(handoff_root.resolve()), "output_root": str(package_root.resolve()),
                "host": {"platform": {"Darwin": "macos", "Windows": "windows"}.get(platform.system(), sys.platform),
                         "host_id": socket.gethostname(), "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
                         "python_executable": str(Path(sys.executable).resolve())},
                "input_allowlist": [{"path": "handoff.json", "sha256": handoff_sha},
                                    {"path": "oof.csv", "sha256": csv_sha}],
                "handoff_sha256": handoff_sha, "case_id": case_id, "execution_run_id": run_id,
                "protocol_id": protocol_id, "protocol_version": "p4b-v2", "manifest_sha256": "a" * 64}
        gate_path = self.write_json(self.root / "handoff-gate.json", gate)
        return package_root, handoff_root, gate_path

    def test_evaluate_handoff_uses_normalized_contract_and_updates_package(self):
        package_root, handoff_root, gate = self._handoff_fixture()
        result = self.run_cli("evaluate-handoff", "--package-root", package_root,
                              "--handoff-root", handoff_root, "--gate", gate)
        self.assertEqual(result.returncode, 0, result.stderr)
        index_path = package_root / "phases/phase-05/evaluations.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertEqual(index["status"], "PLANNED")
        self.assertEqual(len(index["evaluations"]), 2)
        phase5_cli._schema_validate(index)
        package = json.loads((package_root / "package.json").read_text(encoding="utf-8"))
        records = {record["path"]: record for record in package["files"]}
        self.assertEqual(records["phases/phase-05/evaluations.json"]["sha256"],
                         hashlib.sha256(index_path.read_bytes()).hexdigest())
        self.assertEqual(package["phases"]["phase5"]["status"], index["status"])
        self.assertEqual(package["asset_manifest_ref"], "assets/figure-manifest.json")
        asset_manifest_path = package_root / package["asset_manifest_ref"]
        asset_manifest = json.loads(asset_manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(asset_manifest["status"], "PLANNED")
        self.assertEqual(len(asset_manifest["figures"]), 3)
        for figure in asset_manifest["figures"]:
            image_path = package_root / figure["png_ref"]
            self.assertEqual(figure["sha256_png"], hashlib.sha256(image_path.read_bytes()).hexdigest())
            self.assertGreater(figure["width"], 0)
            self.assertGreater(figure["height"], 0)
            self.assertTrue(figure["alt"])
            self.assertEqual(figure["publication_review"], "PENDING")
            self.assertEqual(figure["status"], "PLANNED")
        for relative, record in records.items():
            artifact = package_root / relative
            self.assertEqual(record["bytes"], artifact.stat().st_size)
            self.assertEqual(record["sha256"], hashlib.sha256(artifact.read_bytes()).hexdigest())

    def test_multi_configuration_reuses_stable_tokens_with_distinct_asset_joins(self):
        package_root, handoff_root, gate = self._handoff_fixture(config_count=2)
        result = self.run_cli("evaluate-handoff", "--package-root", package_root,
                              "--handoff-root", handoff_root, "--gate", gate)
        self.assertEqual(result.returncode, 0, result.stderr)
        index = json.loads((package_root / "phases/phase-05/evaluations.json").read_text(encoding="utf-8"))
        manifest_path = package_root / "assets/figure-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        pooled = {item["evaluation_id"]: item for item in index["evaluations"]
                  if item["metric_source"] == "pooled_oof"}
        self.assertEqual(len(pooled), 2)
        self.assertEqual(len(manifest["figures"]), 6)
        self.assertEqual({figure["figure_id"] for figure in manifest["figures"]},
                         {"FIG-P5-01", "FIG-P5-02", "FIG-P5-03"})
        composite_keys = [(figure["phase"], figure["source_evaluation_id"], figure["figure_id"])
                          for figure in manifest["figures"]]
        self.assertEqual(len(composite_keys), len(set(composite_keys)))
        png_refs = [figure["png_ref"] for figure in manifest["figures"]]
        self.assertEqual(len(png_refs), len(set(png_refs)))
        for entry in manifest["figures"]:
            owner = pooled[entry["source_evaluation_id"]]
            owned_figure = next(item for item in owner["figures"] if item["figure_id"] == entry["figure_id"])
            self.assertEqual(entry["source_configuration_id"], owner["configuration_id"])
            self.assertEqual(entry["png_ref"], owned_figure["asset_ref"])
            self.assertEqual(entry["sha256_png"], owned_figure["sha256"])

    def test_figure_manifest_rejects_duplicate_wrong_join_shared_path_and_bad_digest(self):
        package_root, handoff_root, gate = self._handoff_fixture(config_count=2)
        result = self.run_cli("evaluate-handoff", "--package-root", package_root,
                              "--handoff-root", handoff_root, "--gate", gate)
        self.assertEqual(result.returncode, 0, result.stderr)
        index_path = package_root / "phases/phase-05/evaluations.json"
        index_bytes = index_path.read_bytes()
        index = json.loads(index_bytes)
        manifest_path = package_root / "assets/figure-manifest.json"
        original_payload = manifest_path.read_bytes()
        original_manifest = json.loads(original_payload)
        package = json.loads((package_root / "package.json").read_text(encoding="utf-8"))
        records = {record["path"]: dict(record) for record in package["files"]}

        duplicate_index = copy.deepcopy(index)
        pooled_index_eval = next(item for item in duplicate_index["evaluations"]
                                 if item["metric_source"] == "pooled_oof")
        pooled_index_eval["figures"].append(copy.deepcopy(pooled_index_eval["figures"][0]))
        with self.assertRaises(phase5_cli.CliError) as duplicate_error:
            phase5_cli._validate_figure_manifest("synthetic-case", duplicate_index, original_manifest,
                                                 package_root, records, original_payload, index_bytes)
        self.assertEqual(duplicate_error.exception.code, "JOIN_BLOCKED")

        mutations = []
        duplicate = copy.deepcopy(original_manifest)
        duplicate["figures"].append(copy.deepcopy(duplicate["figures"][0]))
        mutations.append(("same-evaluation duplicate token", duplicate, "JOIN_BLOCKED"))

        wrong_join = copy.deepcopy(original_manifest)
        different_evaluation = next(entry["source_evaluation_id"] for entry in wrong_join["figures"]
                                    if entry["source_configuration_id"] != wrong_join["figures"][0]["source_configuration_id"])
        wrong_join["figures"][0]["source_evaluation_id"] = different_evaluation
        mutations.append(("cross-evaluation/configuration misbinding", wrong_join, "JOIN_BLOCKED"))

        shared_path = copy.deepcopy(original_manifest)
        shared_path["figures"][1]["png_ref"] = shared_path["figures"][0]["png_ref"]
        mutations.append(("shared physical path", shared_path, "JOIN_BLOCKED"))

        wrong_digest = copy.deepcopy(original_manifest)
        wrong_digest["figures"][0]["sha256_png"] = "0" * 64
        mutations.append(("bad digest", wrong_digest, "HASH_MISMATCH"))

        try:
            for label, manifest, expected_code in mutations:
                with self.subTest(label=label):
                    payload = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                    manifest_path.write_bytes(payload)
                    test_records = {path: dict(record) for path, record in records.items()}
                    test_records["assets/figure-manifest.json"] = {
                        "path": "assets/figure-manifest.json", "sha256": hashlib.sha256(payload).hexdigest(),
                        "bytes": len(payload), "mime": "application/json"}
                    with self.assertRaises(phase5_cli.CliError) as caught:
                        phase5_cli._validate_figure_manifest("synthetic-case", index, manifest,
                                                             package_root, test_records, payload, index_bytes)
                    self.assertEqual(caught.exception.code, expected_code)
        finally:
            manifest_path.write_bytes(original_payload)

    def test_evaluate_handoff_rejects_tampered_csv_without_package_change(self):
        package_root, handoff_root, gate = self._handoff_fixture()
        before = (package_root / "package.json").read_bytes()
        with (handoff_root / "oof.csv").open("a", encoding="utf-8") as stream:
            stream.write("tamper\n")
        result = self.run_cli("evaluate-handoff", "--package-root", package_root,
                              "--handoff-root", handoff_root, "--gate", gate)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((package_root / "package.json").read_bytes(), before)
        self.assertEqual(json.loads((package_root / "phases/phase-05/evaluations.json").read_text())["evaluations"], [])

    def test_evaluate_handoff_rejects_package_hash_and_identity_mismatches(self):
        package_root, handoff_root, gate_path = self._handoff_fixture()
        modeling_path = package_root / "phases/phase-04/modeling.json"
        original_modeling = modeling_path.read_bytes()
        modeling_path.write_bytes(original_modeling + b" ")
        bad_package = self.run_cli("evaluate-handoff", "--package-root", package_root,
                                   "--handoff-root", handoff_root, "--gate", gate_path)
        self.assertNotEqual(bad_package.returncode, 0)
        self.assertIn("HASH_MISMATCH", bad_package.stderr)
        modeling_path.write_bytes(original_modeling)

        handoff_path = handoff_root / "handoff.json"
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        handoff["execution_run_id"] = "different-run"
        self.write_json(handoff_path, handoff)
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        handoff_sha = hashlib.sha256(handoff_path.read_bytes()).hexdigest()
        gate["handoff_sha256"] = handoff_sha
        gate["input_allowlist"][0]["sha256"] = handoff_sha
        self.write_json(gate_path, gate)
        bad_identity = self.run_cli("evaluate-handoff", "--package-root", package_root,
                                    "--handoff-root", handoff_root, "--gate", gate_path)
        self.assertNotEqual(bad_identity.returncode, 0)
        self.assertIn("JOIN_BLOCKED", bad_identity.stderr)
        self.assertEqual(json.loads((package_root / "phases/phase-05/evaluations.json").read_text())["evaluations"], [])

    def test_evaluate_handoff_requires_declared_phase4_modeling_file(self):
        package_root, handoff_root, gate = self._handoff_fixture()
        package_root = package_root.resolve()
        handoff_root = handoff_root.resolve()
        package_path = package_root / "package.json"
        package = json.loads(package_path.read_text(encoding="utf-8"))
        package["files"] = [record for record in package["files"]
                            if record["path"] != "phases/phase-04/modeling.json"]
        self.write_json(package_path, package)
        result = self.run_cli("evaluate-handoff", "--package-root", package_root,
                              "--handoff-root", handoff_root, "--gate", gate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not declare its Phase 4 modeling file", result.stderr)
        self.assertEqual(json.loads((package_root / "phases/phase-05/evaluations.json").read_text())["evaluations"], [])

    def test_evaluate_handoff_joins_manifest_digest_to_execution_run(self):
        package_root, handoff_root, gate_path = self._handoff_fixture()
        handoff_path = handoff_root / "handoff.json"
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        handoff["source_artifacts"]["manifest_sha256"] = "d" * 64
        self.write_json(handoff_path, handoff)
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        handoff_sha = hashlib.sha256(handoff_path.read_bytes()).hexdigest()
        gate["handoff_sha256"] = handoff_sha
        gate["input_allowlist"][0]["sha256"] = handoff_sha
        gate["manifest_sha256"] = "d" * 64
        self.write_json(gate_path, gate)
        result = self.run_cli("evaluate-handoff", "--package-root", package_root,
                              "--handoff-root", handoff_root, "--gate", gate_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not join to Phase 4 modeling", result.stderr)
        self.assertEqual(json.loads((package_root / "phases/phase-05/evaluations.json").read_text())["evaluations"], [])

    def test_package_manifest_update_failure_rolls_back_owned_assets_and_retries(self):
        package_root, handoff_root, gate_path = self._handoff_fixture()
        package_root = package_root.resolve()
        handoff_root = handoff_root.resolve()
        assets = package_root / "assets"
        assets.mkdir()
        preexisting = assets / "pre-existing.bin"
        preexisting.write_bytes(b"keep this existing asset")
        package_path = package_root / "package.json"
        package = json.loads(package_path.read_text(encoding="utf-8"))
        package["files"].append({"path": "assets/pre-existing.bin",
                                 "sha256": hashlib.sha256(preexisting.read_bytes()).hexdigest(),
                                 "bytes": preexisting.stat().st_size, "mime": "application/octet-stream"})
        self.write_json(package_path, package)
        package_before = package_path.read_bytes()
        index_path = package_root / "phases/phase-05/evaluations.json"
        index_before = index_path.read_bytes()
        original_replace = phase5_cli._atomic_replace_existing
        failed = False

        def fail_package_manifest_once(path, payload):
            nonlocal failed
            if path == package_path and not failed:
                failed = True
                raise phase5_cli.CliError("OUTPUT_WRITE_FAILED", "injected package manifest update failure", 5)
            return original_replace(path, payload)

        args = argparse.Namespace(package_root=str(package_root), handoff_root=str(handoff_root), gate=str(gate_path))
        with mock.patch.object(phase5_cli, "_atomic_replace_existing", side_effect=fail_package_manifest_once):
            with self.assertRaises(phase5_cli.CliError):
                phase5_cli._evaluate_handoff(args)
        self.assertEqual(package_path.read_bytes(), package_before)
        self.assertEqual(index_path.read_bytes(), index_before)
        self.assertEqual(sorted(path.name for path in assets.iterdir()), ["pre-existing.bin"])
        self.assertEqual(preexisting.read_bytes(), b"keep this existing asset")

        result = phase5_cli._evaluate_handoff(args)
        self.assertEqual(result, 0)
        updated_package = json.loads(package_path.read_text(encoding="utf-8"))
        self.assertEqual(updated_package["phases"]["phase5"]["status"], "PLANNED")
        self.assertTrue((assets / "figure-manifest.json").is_file())
        self.assertEqual(preexisting.read_bytes(), b"keep this existing asset")

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
