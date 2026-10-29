import re
import hashlib
import json
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.sections = 0
        self.text = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.add(attributes["id"])
        if tag == "a" and "href" in attributes:
            self.links.append(attributes["href"])
        if tag == "section":
            self.sections += 1

    def handle_data(self, data):
        self.text.append(data)


class WebFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (WEB / "index.html").read_text(encoding="utf-8")
        cls.css = (WEB / "styles.css").read_text(encoding="utf-8")
        cls.js = (WEB / "app.js").read_text(encoding="utf-8")
        cls.parser = SiteParser()
        cls.parser.feed(cls.html)

    def test_primary_sections_and_navigation_targets_exist(self):
        expected = {"main", "app", "case-context", "case-select", "case-load-status", "phase-nav"}
        self.assertTrue(expected.issubset(self.parser.ids))
        self.assertIn("phase-${phase}", self.js)
        self.assertIn('data-crisp-link', self.html)

    def test_case_selector_exposes_loading_success_and_failure_states(self):
        self.assertIn('id="case-load-status" class="case-load-status" role="status" aria-live="polite"', self.html)
        self.assertIn('caseSelect.disabled = loading;', self.js)
        self.assertIn('研究案例載入中…', self.js)
        self.assertIn('研究案例載入失敗：', self.js)
        self.assertIn('研究案例載入完成，共 ${Object.keys(CASES).length} 個可用案例。', self.js)
        self.assertIn('caseLoadStatus.classList.toggle("is-error", failedCases.length > 0);', self.js)
        self.assertIn('console.warn("[RegScope] Case Package validation failed", {', self.js)
        self.assertIn('logPackageLoadFailure("ames-reference-init-a", stage, error);', self.js)
        self.assertIn('logPackageLoadFailure(EXPLORATION_CASE_ID, stage, error);', self.js)

    def test_car_case_loader_is_independent_and_manifest_bound(self):
        self.assertIn('const CAR_CASE_ID = "used-car-price-optimized";', self.js)
        self.assertIn('async function loadCarPackage()', self.js)
        self.assertIn('loadCarPackage();', self.js)
        self.assertIn('if (!releaseCase) return;', self.js)
        self.assertIn('caseInfo.packageMode === "car"', self.js)
        self.assertIn('else if (phase && caseData().packageMode === "car") app.innerHTML = renderCarPackagePhase(phase);', self.js)
        self.assertIn('function renderCarPhase3(pkg, doc)', self.js)
        self.assertIn('One-Hot 編碼後產生 70 個模型特徵', self.js)
        self.assertIn('Publication review：PENDING', self.js)
        self.assertIn('Prediction unavailable', self.js)

    def test_phase4_has_two_mode_controls_and_preserves_explorer_views(self):
        self.assertIn('explorationMode: "comparison"', self.js)
        self.assertIn('data-exploration-mode="comparison"', self.js)
        self.assertIn('data-exploration-mode="explorer"', self.js)
        self.assertIn('方法比較 Method Comparison', self.js)
        self.assertIn('單一方法探索 Method Explorer', self.js)
        self.assertIn('state.explorationMode = target.dataset.explorationMode; render();', self.js)
        self.assertIn('data-exploration-open-method', self.js)
        self.assertIn('data-exploration-perspective="selected_features"', self.js)
        self.assertIn('data-exploration-perspective="feature_count_cv_rmse"', self.js)
        self.assertNotIn('data-exploration-back', self.js)

    def test_phase5_uses_phase4_configuration_and_mean_fold_metrics_by_default(self):
        self.assertIn('item.metric_source === "cv_fold_mean"', self.js)
        self.assertIn('requestedId\n    ? phase4.configurations.find((item) => item.configuration_id === requestedId)', self.js)
        self.assertIn('meanEval.execution_run_id !== config.execution_run_id', self.js)
        self.assertIn('pooled.prediction_origin !== meanEval.prediction_origin', self.js)
        self.assertIn('pooled.evidence?.source_artifact_sha256 !== meanSourceSha', self.js)
        self.assertIn('phase5ComputationStatus(meanEval, doc.status)', self.js)
        self.assertIn('Evaluation ${esc(computationStatus)} · 發布審查', self.js)
        self.assertIn('href="#phase-4">在 Phase 4 變更模型', self.js)
        self.assertIn('三折交叉驗證指標的算術平均，並非獨立 Holdout Test 的結果。', self.js)
        self.assertNotIn('id="exploration-p5-config"', self.js)
        self.assertNotIn('data-exploration-metric-source=', self.js)

    def test_phase5_keeps_diagnostics_and_advanced_aggregations_separate(self):
        for figure_id in ("FIG-P5-01", "FIG-P5-02", "FIG-P5-03"):
            self.assertIn(figure_id, self.js)
        self.assertIn('data-exploration-p5-figure', self.js)
        self.assertIn('figure.source_digest === pooled.evidence?.source_artifact_sha256', self.js)
        self.assertIn('figure.evaluation_id === pooled.evaluation_id', self.js)
        self.assertIn('entry.mime === "image/png"', self.js)
        self.assertIn('Advanced Evaluation Details', self.js)
        self.assertIn('Pooled Development OOF', self.js)
        self.assertIn('未使用 Mock 圖或其他模型的結果代替。', self.js)

    def test_phase5_package_metric_and_figure_bindings_are_intact(self):
        release = json.loads((WEB / "data/current-release.json").read_text(encoding="utf-8"))
        for case_id in ("ames-reference-init-a", "ames-full-model-exploration"):
            entry = next(item for item in release["cases"] if item["case_id"] == case_id)
            package_path = WEB / "data" / entry["package_ref"]
            package_bytes = package_path.read_bytes()
            self.assertEqual(hashlib.sha256(package_bytes).hexdigest(), entry["package_sha256"])
            self.assertEqual(len(package_bytes), entry["package_bytes"])
            manifest = json.loads(package_bytes)
            package_root = package_path.parent
            files = {item["path"]: item for item in manifest["files"]}
            phase4_ref = manifest["phases"]["phase4"]["data_ref"]
            phase5_ref = manifest["phases"]["phase5"]["data_ref"]
            phase4 = json.loads((package_root / phase4_ref).read_text(encoding="utf-8"))
            phase5 = json.loads((package_root / phase5_ref).read_text(encoding="utf-8"))
            configs = {item["configuration_id"]: item for item in phase4["configurations"]}
            evaluations = phase5["evaluations"]
            for mean_eval in (item for item in evaluations if item["metric_source"] == "cv_fold_mean"):
                config = configs[mean_eval["configuration_id"]]
                self.assertEqual(mean_eval["execution_run_id"], config["execution_run_id"])
                self.assertEqual(mean_eval["n"], 1168)
                self.assertTrue(all(metric["value"] is not None for metric in mean_eval["metrics"].values()))
                pooled = next((item for item in evaluations if item["configuration_id"] == config["configuration_id"] and item["metric_source"] == "pooled_oof"), None)
                if pooled is None:
                    continue
                self.assertEqual(pooled["execution_run_id"], config["execution_run_id"])
                self.assertEqual(pooled["n"], mean_eval["n"])
                self.assertEqual(pooled["evaluation_population"], mean_eval["evaluation_population"])
                for figure in pooled["figures"]:
                    self.assertEqual(figure["evaluation_id"], pooled["evaluation_id"])
                    self.assertEqual(figure["configuration_id"], config["configuration_id"])
                    self.assertEqual(figure["source_digest"], pooled["evidence"]["source_artifact_sha256"])
                    listed = files[figure["asset_ref"]]
                    asset = (package_root / figure["asset_ref"]).read_bytes()
                    self.assertEqual(figure["sha256"], listed["sha256"])
                    self.assertEqual(hashlib.sha256(asset).hexdigest(), listed["sha256"])
                    self.assertEqual(listed["mime"], "image/png")

    def test_brand_course_and_project_links_are_present(self):
        text = " ".join(self.parser.text)
        self.assertIn("RegScope", text)
        self.assertIn("CRISP-DM", text)
        self.assertTrue(any("github.com/wupojung/AIoT-HW2-Housing-Regression" in href for href in self.parser.links))

    def test_unbuilt_analysis_sections_are_clearly_marked(self):
        text = (" ".join(self.parser.text) + self.js).lower()
        self.assertIn("mock", text)
        self.assertIn("not approved research results", text)
        self.assertIn("publication review remains pending", text)

    def test_responsive_navigation_and_reduced_motion_rules_exist(self):
        self.assertIn("@media (max-width: 700px)", self.css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css)
        self.assertIn('id="phase-nav"', self.html)
        self.assertIn('case-select', self.js)
        self.assertIn('data-dashboard-mode', self.js)

    def test_vercel_serves_only_the_static_web_directory(self):
        import json

        config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(config["outputDirectory"], "web")


if __name__ == "__main__":
    unittest.main()
