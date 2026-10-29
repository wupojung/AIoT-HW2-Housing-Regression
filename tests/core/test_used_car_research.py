"""Synthetic contract tests for the separate Used Car case runner."""

from __future__ import annotations

import csv
import json
import random
import tempfile
import unittest
from pathlib import Path

from housing_regression.used_car_research import CASE_ID, RUN_ID, run_used_car_research


class UsedCarResearchTests(unittest.TestCase):
    def _fixture(self, path: Path) -> None:
        rng = random.Random(42)
        columns = ["ID", "condition", "cylinders", "drive", "engine", "est._monthly_pmt", "dealer_description",
                   "ext_color", "feature_count", "features_list", "fuel", "image_count",
                   "int_color", "make", "mileage", "model", "odometer", "paint_color",
                   "price", "scrape_timestamp", "search_price", "title", "title_status",
                   "trans", "transmission", "trim", "type", "vin", "year"]
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for index in range(96):
                year = 2008 + index % 16
                odometer = 20000 + index * 900
                price = 18000 + (year - 2008) * 950 - odometer * 0.12 + rng.randrange(-500, 500)
                writer.writerow({
                    "ID": index + 1, "condition": ["good", "excellent", "fair"][index % 3],
                    "cylinders": ["4", "6", "8"][index % 3], "drive": ["fwd", "rwd", "awd"][index % 3],
                    "engine": f"engine text {index}", "est._monthly_pmt": round(price / 48, 2),
                    "dealer_description": f"Unique dealer listing description for vehicle number {index}, inspected and serviced recently.",
                    "ext_color": ["black", "white", "blue"][index % 3], "feature_count": index % 12,
                    "features_list": f"long text {index}", "fuel": ["gas", "diesel"][index % 2],
                    "image_count": index % 10, "int_color": ["black", "tan"][index % 2],
                    "make": ["A", "B", "C"][index % 3], "mileage": f"{odometer:,}",
                    "model": ["M1", "M2", "M3"][index % 3], "odometer": odometer,
                    "paint_color": ["black", "white", "blue"][index % 3], "price": round(price, 2),
                    "scrape_timestamp": "2026-01-01T00:00:00Z", "search_price": round(price, 2),
                    "title": f"listing title {index}", "title_status": "clean", "trans": "auto",
                    "transmission": ["automatic", "manual"][index % 2], "trim": ["base", "sport"][index % 2],
                    "type": ["sedan", "SUV"][index % 2], "vin": f"VIN{index:014d}", "year": f"{year} Make: listing prose",
                })

    def test_synthetic_run_is_fold_local_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output = root / "train.csv", root / "run"
            self._fixture(source)
            source_before = source.read_bytes()
            result = run_used_car_research(source, output)
            self.assertEqual(source.read_bytes(), source_before)
            self.assertEqual(result["case_id"], CASE_ID)
            self.assertEqual(result["run_id"], RUN_ID)
            self.assertEqual(result["phase_status"]["phase4"], "VERIFIED")
            self.assertEqual(result["phase_status"]["phase5"], "VERIFIED")
            self.assertEqual(result["phase_status"]["phase6"], "LOCAL_PRIVATE_VERIFIED")
            self.assertGreaterEqual(result["candidates_completed"], 16)
            self.assertEqual(result["publication_status"], "BLOCKED_PENDING_COMPETITION_TERMS_REVIEW")
            self.assertTrue((output / "private/final-model.joblib").is_file())
            self.assertTrue((output / "private/winner-oof-private.csv").is_file())
            self.assertTrue((output / "phases/phase-01/content.json").is_file())
            phase1 = json.loads((output / "phases/phase-01/content.json").read_text(encoding="utf-8"))
            self.assertTrue(any("中古車" in section["body"] for section in phase1["sections"]))
            config = json.loads((output / "config.json").read_text(encoding="utf-8"))
            self.assertIn("dealer_description", config["excluded_fields"])
            self.assertIn("condition", config["model_features"])
            self.assertIn("year", config["model_features"])
            self.assertIn("leading 4-digit", config["value_normalization"]["year"])
            phase2 = json.loads((output / "phases/phase-02/analyses.json").read_text(encoding="utf-8"))
            field_decisions = next(item for item in phase2["analyses"] if item["id"] == "field-decisions")["finding"]
            self.assertIn("dealer_description [text] exclude", field_decisions)
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                run_used_car_research(source, output)


if __name__ == "__main__":
    unittest.main()
