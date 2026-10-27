"""Synthetic INIT → Phase 1–6 → pinned schema and bundle validation smoke."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python" / "src"))

from housing_regression.e2e_package import (
    PackageValidationError,
    build_minimal_synthetic_package,
    validate_case_package,
)
from housing_regression.core_utils import PhaseCoreError
from housing_regression.init_config import initialize_case


FIXTURE = ROOT / "tests" / "fixtures" / "regscope_g2_synthetic.csv.fixture"


class MinimalE2EPackageTests(unittest.TestCase):
    def test_synthetic_runner_rejects_any_csv_other_than_fixed_fixture_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            alternate = root / "alternate.csv"
            alternate.write_bytes(FIXTURE.read_bytes())
            config_dir = root / "init"
            config_dir.mkdir()
            config = initialize_case(alternate, "e2e-alternate", "SalePrice", config_dir).config_path
            package_root = root / "case-package"

            with self.assertRaisesRegex(PhaseCoreError, "fixed repository synthetic CSV"):
                build_minimal_synthetic_package(config, package_root)

            self.assertFalse(package_root.exists())

    def test_synthetic_csv_to_phase6_package_validates_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_dir = root / "init"
            config_dir.mkdir()
            config = initialize_case(FIXTURE, "e2e-synthetic", "SalePrice", config_dir).config_path
            package_root = root / "case-package"

            e2e_run = build_minimal_synthetic_package(config, package_root)
            package = e2e_run["package"]
            result = validate_case_package(package_root)

            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["phase_count"], 6)
            self.assertEqual(package["package_status"], "MOCK")
            self.assertFalse(package["publication"]["approved"])
            self.assertEqual(
                [package["phases"][f"phase{n}"]["status"] for n in range(1, 7)],
                ["MOCK", "MOCK", "MOCK", "MOCK", "MOCK", "UNAVAILABLE"],
            )
            self.assertEqual(e2e_run["execution"]["phase3"]["rows"], 3)
            self.assertEqual(e2e_run["execution"]["phase3"]["encoded_features"], 2)
            self.assertEqual(e2e_run["execution"]["phase4_model_fit"], "PASS")
            self.assertEqual(e2e_run["execution"]["phase5_synthetic_metrics"], "PASS")
            self.assertEqual(e2e_run["execution"]["phase6_in_memory_prediction"], "PASS")
            self.assertEqual(e2e_run["execution"]["phase6_deployable_model"], "UNAVAILABLE")
            self.assertTrue((package_root / "phases/phase-01/content.json").is_file())
            self.assertTrue((package_root / "phases/phase-02/analyses.json").is_file())
            preparation = json.loads((package_root / "phases/phase-03/preparation.json").read_text(encoding="utf-8"))
            self.assertEqual(
                {item["strategy"] for item in preparation["treatments"]},
                {"median_imputation", "mode_imputation_then_one_hot"},
            )
            modeling = json.loads((package_root / "phases/phase-04/modeling.json").read_text(encoding="utf-8"))
            self.assertEqual(modeling["status"], "MOCK")
            evaluations = json.loads((package_root / "phases/phase-05/evaluations.json").read_text(encoding="utf-8"))
            evaluation = evaluations["evaluations"][0]
            self.assertEqual(evaluation["evaluation_population"], "training_in_sample")
            self.assertTrue(all(metric["status"] == "MOCK" for metric in evaluation["metrics"].values()))
            inference = json.loads((package_root / "phases/phase-06/inference-catalog.json").read_text(encoding="utf-8"))
            self.assertEqual(inference["models"], [])
            self.assertFalse(inference["readiness"]["predict_enabled"])
            self.assertFalse(any(path.suffix.lower() == ".csv" for path in package_root.rglob("*")))
            combined = "\n".join(path.read_text(encoding="utf-8") for path in package_root.rglob("*.json"))
            self.assertNotIn("DO_NOT_EXPORT_ROW_", combined)

            analyses = json.loads((package_root / "phases/phase-02/analyses.json").read_text(encoding="utf-8"))
            self.assertTrue(all(
                (package_root / item["image_ref"]).is_file()
                for item in analyses["analyses"] if item["image_ref"]
            ))

            target_asset = package_root / "phases/phase-02/figures/target-distribution.svg"
            original = target_asset.read_bytes()
            target_asset.write_bytes(original + b" ")
            with self.assertRaisesRegex(PackageValidationError, "integrity mismatch"):
                validate_case_package(package_root)
            target_asset.write_bytes(original)
            self.assertEqual(validate_case_package(package_root)["status"], "PASS")

            (package_root / "unmanifested.txt").write_text("unexpected", encoding="utf-8")
            with self.assertRaisesRegex(PackageValidationError, "exactly cover"):
                validate_case_package(package_root)

            with self.assertRaisesRegex(PhaseCoreError, "refusing to overwrite"):
                build_minimal_synthetic_package(config, package_root)


if __name__ == "__main__":
    unittest.main()
