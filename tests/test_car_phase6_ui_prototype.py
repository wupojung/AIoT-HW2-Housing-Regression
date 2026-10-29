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
        self.assertIn('disabled title="預測功能尚未實作"', source)
        self.assertIn("未載入模型，也不會呼叫 API。", source)
        self.assertIn("執行批次預測 · 尚未開放", source)

    def test_phase6_copy_and_provenance_are_chinese_first_and_distinct(self):
        source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        for label in (
            "單筆輸入",
            "CSV 批次輸入",
            "數值欄位",
            "類別欄位",
            "文字欄位",
            "資料身分與來源",
            "目前使用的合成 Fixture",
            "Prediction Input Schema v0.1",
            "尚未接入本原型",
        ):
            with self.subTest(label=label):
                self.assertIn(label, source)
        self.assertIn('data-car-field-group="${key}"', source)
        self.assertIn('app.addEventListener("toggle"', source)
        self.assertIn("SYNTHETIC_UI_ONLY", source)
        self.assertIn("不代表已核准的 CAR 輸入契約", source)

    def test_csv_upload_and_prediction_actions_remain_disabled(self):
        source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('class="p6-demo-upload" aria-disabled="true"', source)
        self.assertIn("選擇檔案 · Demo 尚未開放", source)
        self.assertIn("下載範本 · 尚未開放", source)
        self.assertIn("下載預測結果 CSV · 尚未開放", source)
        self.assertIn("不會產生或顯示預測價格", source)


if __name__ == "__main__":
    unittest.main()
