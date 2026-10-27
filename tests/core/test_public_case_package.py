"""Synthetic-only tests for safe public Case Package export primitives."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python" / "src"))

from housing_regression.public_case_package import (  # noqa: E402
    PublicPackageError,
    _public_copy,
    export_public_reference_package,
)


class PublicCasePackageTests(unittest.TestCase):
    def test_phase5_oof_source_path_is_removed_from_public_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            target = root / "target"
            source_file = source / "phases/phase-05/evaluations.json"
            source_file.parent.mkdir(parents=True)
            source_file.write_text(json.dumps({"release_id": None, "evaluations": [
                {"evidence": {"source_ref": "private/phase4-oof-predictions.csv",
                              "source_artifact_sha256": "a" * 64}}
            ]}), encoding="utf-8")

            _public_copy(source, target, "phases/phase-05/evaluations.json", "release-test-001")
            exported = json.loads((target / "phases/phase-05/evaluations.json").read_text(encoding="utf-8"))
            evidence = exported["evaluations"][0]["evidence"]
            self.assertIsNone(evidence["source_ref"])
            self.assertEqual(evidence["source_artifact_sha256"], "a" * 64)
            self.assertEqual(exported["release_id"], "release-test-001")

    def test_phase6_smoke_value_is_suppressed_and_private_paths_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            target = root / "target"
            path = source / "assets/phase6-inference-smoke.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"status": "PASS", "prediction_value": 123.4,
                                        "reload_verified": True, "local_inference_verified": True}), encoding="utf-8")

            _public_copy(source, target, "assets/phase6-inference-smoke.json", "release-test-001")
            exported = json.loads((target / "assets/phase6-inference-smoke.json").read_text(encoding="utf-8"))
            self.assertNotIn("prediction_value", exported)
            self.assertFalse(exported["prediction_value_included"])
            with self.assertRaises(PublicPackageError):
                _public_copy(source, target, "private/phase4-oof-predictions.csv", "release-test-001")
            with self.assertRaises(PublicPackageError):
                _public_copy(source, target, "../../outside.json", "release-test-001")

    def test_export_rejects_unverified_source_without_creating_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "not-a-package"
            source.mkdir()
            release = ROOT / "web/data/releases/release-test-001"
            with self.assertRaises(PublicPackageError):
                export_public_reference_package(source, release, "release-test-001")
            self.assertFalse(release.exists())


if __name__ == "__main__":
    unittest.main()
