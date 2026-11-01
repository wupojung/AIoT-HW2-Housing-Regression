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
        self.assertIn('PHASE6_QUERY.get("car-phase6-prototype") === "1"', source)
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

    def test_local_preview_routes_only_to_phase6_and_guards_other_routes(self):
        source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        render = source[source.index("function render() {"):source.index("function csvRows(")]
        self.assertLess(
            render.index("if (LOCAL_CAR_PHASE6_PREVIEW) {\n    if (phase === 6)"),
            render.index('if (state.route === "home")'),
        )
        self.assertIn("if (phase === 6)", render)
        self.assertIn("此預覽僅包含 Phase 6", render)
        self.assertIn("${esc(requested)} 未包含於此原型", render)
        self.assertIn("不會顯示 Ames 或 CAR 的正式研究內容", render)
        self.assertNotIn("renderDashboard()", render[:render.index('if (state.route === "home")')])
        self.assertIn("const visiblePhases = LOCAL_CAR_PHASE6_PREVIEW ? [PHASES[5]] : PHASES", source)

    def test_contract_helper_failure_does_not_block_the_application(self):
        source = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn("contractHelpers.onload = loadApplication", source)
        self.assertIn("contractHelpers.onerror = loadApplication", source)

    def test_tailnet_preview_is_https_opt_in_and_uses_same_origin_api(self):
        source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('location.protocol === "http:"', source)
        self.assertIn("isTailscaleIPv4Host(location.hostname)", source)
        self.assertIn("octets[0] === 100 && octets[1] >= 64 && octets[1] <= 127", source)
        self.assertIn('PHASE6_QUERY.get("car-tailnet-preview") === "1"', source)
        self.assertIn('const LOCAL_CAR_SAME_ORIGIN_API_MODE = PHASE6_QUERY.get("car-local-inference") === "1"', source)
        self.assertIn('const LOCAL_CAR_API_BASE = LOCAL_CAR_SAME_ORIGIN_API_MODE ? ""', source)
        self.assertIn('fetch(`${LOCAL_CAR_API_BASE}/api/schema`', source)
        self.assertIn('fetch(`${LOCAL_CAR_API_BASE}/api/predict`', source)
        self.assertIn('location.origin === "http://127.0.0.1:8766"', source)
        self.assertIn("const LOCAL_CAR_PHASE6_PREVIEW = LOCAL_CAR_LOOPBACK_PREVIEW", source)
        self.assertIn("if (LOCAL_CAR_TAILNET_PREVIEW && LOCAL_CAR_PREDICTION_API_MODE && state.caseId === CAR_CASE_ID && carPackage)", source)
        self.assertIn("&& state.caseId === CAR_CASE_ID && routePhase() === 6", source)
        self.assertIn("const visiblePhases = LOCAL_CAR_PHASE6_PREVIEW ? [PHASES[5]] : PHASES", source)
        self.assertIn("if (!explorationPackage && !explorationPackageError && !explorationPackageLoading) loadExplorationPackage()", source)
        self.assertIn("if (!carPackage && !carPackageError && !carPackageLoading) loadCarPackage()", source)

    def test_tailnet_mode_preserves_normal_case_and_phase_navigation(self):
        source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("const LOCAL_CAR_PHASE6_PREVIEW = LOCAL_CAR_LOOPBACK_PREVIEW", source)
        self.assertIn("const visiblePhases = LOCAL_CAR_PHASE6_PREVIEW ? [PHASES[5]] : PHASES", source)
        self.assertIn("if (LOCAL_CAR_PHASE6_PREVIEW) publicCases = [[CAR_CASE_ID, CASES[CAR_CASE_ID]]];", source)
        self.assertIn("if (LOCAL_CAR_TAILNET_PREVIEW && LOCAL_CAR_PREDICTION_API_MODE && state.caseId === CAR_CASE_ID && carPackage)", source)
        self.assertIn("if (!explorationPackage && !explorationPackageError && !explorationPackageLoading) loadExplorationPackage()", source)
        self.assertIn("if (!carPackage && !carPackageError && !carPackageLoading) loadCarPackage()", source)

    def test_direct_ip_package_and_schema_hashes_do_not_require_webcrypto(self):
        app_source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        helper_source = (ROOT / "web" / "input-contract.js").read_text(encoding="utf-8")
        self.assertNotIn("crypto.subtle.digest", app_source)
        self.assertIn("window.RegScopeInputContract.sha256Hex(", app_source)
        self.assertIn("function sha256HexFallback(input)", helper_source)
        self.assertIn("return sha256HexFallback(input)", helper_source)


if __name__ == "__main__":
    unittest.main()
