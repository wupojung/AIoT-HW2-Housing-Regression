"""Fail-closed package-builder tests using synthetic identity metadata only."""

import json
import tempfile
import unittest
from pathlib import Path

from housing_regression.used_car_case_package import (
    UsedCarPackageError,
    build_used_car_case_package,
    classify_raw_source_fields,
)


class UsedCarCasePackageTests(unittest.TestCase):
    def test_raw_source_classification_reconciles_categories_and_model_decisions(self):
        decisions = [
            ("ID", "identifier", "exclude"), ("condition", "nominal", "include"),
            ("cylinders", "nominal", "include"), ("drive", "nominal", "include"),
            ("engine", "text", "exclude"), ("est._monthly_pmt", "leakage_proxy", "exclude"),
            ("ext_color", "nominal", "include"), ("feature_count", "discrete", "include"),
            ("features_list", "text", "exclude"), ("fuel", "nominal", "include"),
            ("image_count", "discrete", "include"), ("int_color", "nominal", "include"),
            ("make", "text", "exclude"), ("mileage", "duplicate_representation", "exclude"),
            ("model", "text", "exclude"), ("odometer", "continuous", "include"),
            ("paint_color", "nominal", "include"), ("price", "target", "exclude"),
            ("scrape_timestamp", "temporal", "exclude"), ("search_price", "leakage_proxy", "exclude"),
            ("title", "text", "exclude"), ("title_status", "nominal", "include"),
            ("trans", "text", "exclude"), ("transmission", "nominal", "include"),
            ("trim", "nominal", "include"), ("type", "nominal", "include"),
            ("vin", "identifier", "exclude"), ("year", "discrete", "include"),
        ]
        result = classify_raw_source_fields(decisions)
        self.assertEqual(result["total"], 27)
        self.assertEqual(sum(result["counts"].values()), 27)
        self.assertEqual(result["counts"], {
            "nominal": 11, "ordinal": 0, "discrete": 3, "continuous": 2,
            "identifier": 2, "text": 6, "temporal": 1, "other": 2,
        })
        self.assertEqual(sum(item["decision"] == "exclude" for item in result["fields"]), 12)
        mileage = next(item for item in result["fields"] if item["field"] == "mileage")
        self.assertEqual(mileage["type_id"], "continuous")
        self.assertEqual(mileage["reason_status"], "PENDING")
        self.assertNotIn("price", {item["field"] for item in result["fields"]})

    def test_rejects_wrong_run_identity_before_creating_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "run"
            run.mkdir()
            (run / "checkpoint.json").write_text(json.dumps({
                "case_id": "used-car-price-optimized",
                "run_id": "not-the-authorized-run",
                "source_sha256": "a" * 64,
            }), encoding="utf-8")
            (run / "config.json").write_text(json.dumps({
                "source_sha256": "a" * 64,
            }), encoding="utf-8")
            destination = root / "package"
            with self.assertRaisesRegex(UsedCarPackageError, "source run identity"):
                build_used_car_case_package(run, destination)
            self.assertFalse(destination.exists())

    def test_refuses_existing_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "run"
            run.mkdir()
            destination = root / "existing-package"
            destination.mkdir()
            (destination / "owner-evidence.txt").write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(UsedCarPackageError, "refusing to overwrite"):
                build_used_car_case_package(run, destination)
            self.assertEqual((destination / "owner-evidence.txt").read_text(encoding="utf-8"), "preserve")


if __name__ == "__main__":
    unittest.main()
