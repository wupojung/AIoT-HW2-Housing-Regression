"""Safety and shape checks for the CAR Phase 6 synthetic UI fixtures."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "web" / "data" / "fixtures"


class CarPhase6UiPrototypeTests(unittest.TestCase):
    def load_fixture(self, name):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def test_single_input_fixtures_have_expected_synthetic_field_counts(self):
        for filename, expected_count in (("car-single-small.json", 5), ("car-single-large.json", 15)):
            with self.subTest(filename=filename):
                fixture = self.load_fixture(filename)
                self.assertEqual(fixture["fixture_status"], "SYNTHETIC_UI_ONLY")
                self.assertEqual(fixture["case_id"], "used-car-price-optimized")
                self.assertEqual(len(fixture["input_features"]), expected_count)
                self.assertEqual(len({field["name"] for field in fixture["input_features"]}), expected_count)

    def test_fixture_controls_and_category_values_are_explicitly_synthetic(self):
        fixture = self.load_fixture("car-single-large.json")
        allowed_controls = {"number", "text", "select"}
        for field in fixture["input_features"]:
            self.assertIn(field["control_type"], allowed_controls)
            self.assertTrue(field["name"].startswith("demo_"))
            if field["control_type"] == "select":
                self.assertTrue(field["options"])
                self.assertTrue(all(option.startswith("SYNTHETIC_") for option in field["options"]))

    def test_batch_fixture_counts_match_synthetic_rows_and_errors(self):
        fixture = self.load_fixture("car-batch-preview.json")
        self.assertEqual(fixture["fixture_status"], "SYNTHETIC_UI_ONLY")
        self.assertEqual(fixture["summary"]["total_rows"], len(fixture["preview_rows"]))
        self.assertEqual(fixture["summary"]["valid_rows"] + fixture["summary"]["error_rows"], fixture["summary"]["total_rows"])
        self.assertEqual(fixture["summary"]["error_rows"], len(fixture["errors"]))
        self.assertTrue(all(column.startswith("demo_") for column in fixture["columns"]))

    def test_preview_is_local_opt_in_and_does_not_enable_prediction(self):
        source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('new URLSearchParams(location.search).get("car-phase6-prototype") === "1"', source)
        self.assertIn('disabled title="Prediction is not implemented"', source)
        self.assertIn("No model is loaded; no API is called.", source)
        self.assertIn("Run batch prediction · NOT OPEN", source)


if __name__ == "__main__":
    unittest.main()
