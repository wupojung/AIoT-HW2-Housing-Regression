from __future__ import annotations

import hashlib
import importlib.util
import csv
import json
import tempfile
import platform
import socket
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "tools/research_export/case_package_export.py"
spec = importlib.util.spec_from_file_location("case_package_export", MODULE)
exporter = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(exporter)


class CasePackageExporterTests(unittest.TestCase):
    def test_metadata_package_is_pinned_schema_valid_and_phase5_empty(self):
        run_id, protocol_id = "synthetic-run", "protocol-v1"
        config_hash = hashlib.sha256(b"synthetic-config").hexdigest()
        candidate = {"alpha": 0.1}
        tasks = [{"task_id": f"task-{fold}", "run_id": run_id, "config_hash": config_hash,
                  "method": "lasso", "candidate": candidate, "fold": fold,
                  "status": "COMPLETED", "primary_valid": True} for fold in (0, 1)]
        summary = {"metadata": {"run_id": run_id, "protocol_version": "p4b-v2",
                                "data_boundary": {"development_rows": 4,
                                                  "outer_kfold": {"n_splits": 2}}},
                   "per_outer_fold_results": tasks,
                   "aggregate_results": [{"config_hash": config_hash, "method": "lasso", "candidate": candidate,
                                          "status": "COMPLETED", "coverage_complete": True,
                                          "valid_fold_count": 2, "expected_fold_count": 2,
                                          "expected_folds": [0, 1]}]}
        gate = {"case_id": "synthetic-case", "protocol_id": protocol_id,
                "target": {"column": "SalePrice", "unit": "USD"}}
        files = exporter._package_values(gate, {"run_id": run_id}, summary, "a" * 64, "b" * 64)
        modeling = __import__("json").loads(files["phases/phase-04/modeling.json"])
        empty = __import__("json").loads(files["phases/phase-05/evaluations.json"])
        exporter._validate_schema(modeling, exporter.PHASE4_SCHEMA, "Phase 4 modeling")
        exporter._validate_schema(empty, exporter.PHASE5_SCHEMA, "empty Phase 5 evaluation index")
        self.assertEqual(modeling["status"], "UNAVAILABLE")
        self.assertEqual(modeling["configurations"][0]["configuration_id"], "cfg-" + config_hash)
        self.assertEqual(empty["evaluations"], [])
        self.assertNotIn("oof", " ".join(files.keys()).lower())

    def test_separate_oof_gate_writes_schema_valid_private_handoff_outside_package(self):
        with tempfile.TemporaryDirectory(prefix="phase4-handoff-synthetic-") as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            package_root = root / "case-package"
            handoff_root = root / "private-handoff"
            run_id, protocol_id = "synthetic-run", "protocol-v1"
            config_hash = hashlib.sha256(b"synthetic-config").hexdigest()
            config_id = "cfg-" + config_hash
            candidate = {"alpha": 0.1}
            summary = {"metadata": {"run_id": run_id, "protocol_version": "p4b-v2",
                                    "data_boundary": {"development_rows": 4}},
                       "per_outer_fold_results": [
                           {"task_id": f"task-{fold}", "run_id": run_id, "config_hash": config_hash,
                            "method": "lasso", "track": "primary", "candidate": candidate,
                            "fold": fold, "status": "COMPLETED", "primary_valid": True}
                           for fold in (0, 1)],
                       "aggregate_results": [{"config_hash": config_hash, "method": "lasso", "candidate": candidate,
                                              "status": "COMPLETED", "coverage_complete": True,
                                              "valid_fold_count": 2, "expected_fold_count": 2,
                                              "expected_folds": [0, 1]}]}
            summary_path = source / "p4b_public_summary.json"
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            summary_sha = hashlib.sha256(summary_path.read_bytes()).hexdigest()
            oof_path = source / "p4b_oof_predictions.csv"
            with oof_path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(exporter.OOF_COLUMNS)
                for fold in (0, 1):
                    for row in range(2):
                        writer.writerow([f"row-{fold}-{row}", fold, f"task-{fold}", "lasso", "primary", 10 + row, 11 + row])
            oof_sha = hashlib.sha256(oof_path.read_bytes()).hexdigest()
            manifest = {"run_id": run_id,
                        "file_inventory": [{"relative_path": summary_path.name, "sha256": summary_sha, "is_public": True},
                                           {"relative_path": oof_path.name, "sha256": oof_sha, "is_public": False}]}
            manifest_path = source / "p4b_manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            details = exporter._configuration_records(summary, run_id, protocol_id)[2]
            oof_gate = {"authorized": True, "mode": "phase4_oof_rows", "allowed_operations": ["export_oof"],
                        "manifest_sha256": manifest_sha, "execution_run_id": run_id,
                        "host": {"platform": {"Darwin": "macos", "Windows": "windows"}.get(platform.system(), sys.platform),
                                 "host_id": socket.gethostname(),
                                 "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
                                 "python_executable": str(Path(sys.executable).resolve())},
                        "input_root": str(source), "output_root": str(handoff_root),
                        "input_allowlist": [{"path": oof_path.name, "sha256": oof_sha}],
                        "protocol_id": protocol_id, "protocol_version": "p4b-v2",
                        "case_id": "synthetic-case", "target": {"column": "SalePrice", "unit": "USD"},
                        "configurations": [{"configuration_id": config_id, "method_id": "lasso", "track_id": "primary"}]}
            result_path, handoff = exporter._make_handoff(
                manifest, summary, manifest_sha, summary_sha, oof_path, oof_sha, oof_gate, handoff_root,
                {**details, "package_output_root": package_root.resolve()})
            self.assertEqual(result_path, handoff_root.resolve())
            self.assertFalse(result_path.is_relative_to(package_root.resolve()))
            exporter._validate_schema(handoff, exporter.HANDOFF_SCHEMA, "private OOF handoff")
            self.assertEqual((result_path / "oof.csv").read_text().splitlines()[0], ",".join(exporter.HANDOFF_COLUMNS))
            self.assertEqual((result_path / "handoff.json").exists(), True)

    def test_pinned_phase4_schema_digest_is_unchanged(self):
        digest = hashlib.sha256(exporter.PHASE4_SCHEMA.read_bytes()).hexdigest()
        self.assertEqual(digest, exporter.PHASE4_SCHEMA_SHA256)


if __name__ == "__main__":
    unittest.main()
