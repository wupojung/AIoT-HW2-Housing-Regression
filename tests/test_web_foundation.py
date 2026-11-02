import re
import hashlib
import json
import shutil
import subprocess
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
        self.assertIn('研究案例載入完成，共 ${publicCases.length} 個可用案例。', self.js)
        self.assertIn('caseLoadStatus.classList.toggle("is-error", failedCases.length > 0);', self.js)
        self.assertIn('console.warn("[RegScope] Case Package validation failed", {', self.js)
        self.assertIn('logPackageLoadFailure("ames-reference-init-a", stage, error);', self.js)
        self.assertIn('logPackageLoadFailure(EXPLORATION_CASE_ID, stage, error);', self.js)

    def test_car_case_loader_is_independent_and_manifest_bound(self):
        self.assertIn('const CAR_CASE_ID = "used-car-price-optimized";', self.js)
        self.assertIn('async function loadCarPackage()', self.js)
        self.assertIn('loadCarPackage();', self.js)
        self.assertIn('if (!releaseCase) return;', self.js)
        self.assertIn('if (state.caseId === EXPLORATION_CASE_ID)', self.js)
        self.assertIn('if (state.caseId === CAR_CASE_ID)', self.js)
        self.assertIn('caseInfo.packageMode === "car"', self.js)
        self.assertIn('else if (phase && caseData().packageMode === "car"', self.js)
        self.assertIn('&& !(phase === 6 && (LOCAL_CAR_TAILNET_PREVIEW || LOCAL_CAR_ONLINE_INFERENCE_MODE) && LOCAL_CAR_PREDICTION_API_MODE', self.js)
        self.assertIn('&& state.caseId === CAR_CASE_ID && carPackage)) app.innerHTML = renderCarPackagePhase(phase);', self.js)
        self.assertIn('if ((LOCAL_CAR_TAILNET_PREVIEW || LOCAL_CAR_ONLINE_INFERENCE_MODE) && LOCAL_CAR_PREDICTION_API_MODE && state.caseId === CAR_CASE_ID && carPackage) return renderCarPhase6LocalInference();', self.js)
        self.assertIn('const LOCAL_CAR_TAILNET_PREVIEW = location.protocol === "http:"', self.js)
        self.assertIn('PHASE6_QUERY.get("car-tailnet-preview") === "1"', self.js)
        self.assertIn('isTailscaleIPv4Host(location.hostname)', self.js)
        self.assertIn('const LOCAL_CAR_LOOPBACK_PREVIEW = ["localhost", "127.0.0.1"].includes(location.hostname)', self.js)
        self.assertIn('PHASE6_QUERY.get("car-phase6-prototype") === "1"', self.js)
        self.assertIn('location.origin === "http://127.0.0.1:8788"', self.js)
        self.assertIn('location.origin === "http://127.0.0.1:8766"', self.js)
        self.assertIn('const LOCAL_CAR_VERCEL_PREVIEW_MODE = location.protocol === "https:"', self.js)
        self.assertIn('&& isAuthorizedCarOnlinePreviewHost(location.hostname)', self.js)
        self.assertIn('const LOCAL_CAR_VERCEL_PRODUCTION_MODE = isAuthorizedCarProductionHost(location.protocol, location.hostname);', self.js)
        self.assertIn('const LOCAL_CAR_SAME_ORIGIN_API_MODE', self.js)
        self.assertIn('const LOCAL_CAR_API_BASE = LOCAL_CAR_SAME_ORIGIN_API_MODE ? ""', self.js)
        self.assertIn('if (localCarSchemaError || !localCarSchema)', self.js)
        self.assertNotIn('location.hostname.endsWith(".vercel.app")', self.js)
        self.assertIn('const LOCAL_CAR_PREDICTION_API_MODE =', self.js)
        self.assertIn('const localCarPhase6Route = LOCAL_CAR_PREDICTION_API_MODE', self.js)
        self.assertIn('&& state.caseId === CAR_CASE_ID && routePhase() === 6', self.js)
        self.assertIn('&& (LOCAL_CAR_PHASE6_PREVIEW || Boolean(carPackage));', self.js)
        self.assertIn('if (!LOCAL_CAR_PREDICTION_API_MODE || localCarSchema || localCarSchemaError || localCarSchemaLoading) return;', self.js)
        self.assertIn('function renderCarPhase3(pkg, doc)', self.js)
        self.assertIn('One-Hot 編碼後產生 ${lineage.encoded_features.length.toLocaleString()} 個模型特徵', self.js)
        self.assertIn('Publication review：PENDING', self.js)
        self.assertIn('Prediction unavailable', self.js)

    def test_car_phase1_displays_case_package_rights_without_changing_review_state(self):
        self.assertIn('pkg.publicationStatus = await boundJson("assets/publication-status.json");', self.js)
        self.assertIn('const source = pkg.caseDoc.source || {};', self.js)
        self.assertIn('source.license_review || "PENDING"', self.js)
        self.assertIn('publication.status || pkg.manifest.package_status', self.js)
        self.assertIn('https://creativecommons.org/licenses/by-nc-sa/4.0/', self.js)
        self.assertIn('href="${esc(source.url)}"', self.js)
        self.assertIn('Owner 聲明本服務用途為非商業大學課程作業與個人研究展示', self.js)
        self.assertIn('Competition-specific rules 尚未獨立核對', self.js)
        self.assertIn('Package publication：${esc(publication.status || pkg.manifest.package_status || "UNKNOWN")}', self.js)

    def test_car_phase6_keeps_quality_and_batch_safety_notices(self):
        self.assertIn('R² 為負值；單筆推論結果不是模型準確度證據', self.js)
        self.assertIn('1 MiB／100 筆', self.js)
        batch_source = (ROOT / "python/src/housing_regression/car_batch_prediction.py").read_text(encoding="utf-8")
        self.assertIn("MAX_BATCH_REQUEST_BYTES = 1024 * 1024", batch_source)
        self.assertIn("MAX_BATCH_ROWS = 100", batch_source)
        self.assertIn("MAX_BATCH_RESPONSE_BYTES = 4_000_000", batch_source)

    def test_car_batch_result_renderer_uses_defined_environment_gates(self):
        match = re.search(
            r"function renderLocalCarBatchPanels\(contract\) \{(?P<body>.*?)\n\}",
            self.js,
            re.S,
        )
        self.assertIsNotNone(match)
        source = match.group("body")
        self.assertNotIn("onlinePreview", source)
        self.assertIn('LOCAL_CAR_VERCEL_PRODUCTION_MODE ? "BATCH RESULT · PRODUCTION MODEL"', source)
        self.assertIn('"BATCH RESULT · PROTECTED PREVIEW MODEL"', source)
        self.assertIn('"BATCH RESULT · DEVELOPMENT MODEL"', source)

    def test_car_production_mode_is_exact_https_host_without_query_flag(self):
        host = "regscope-aiot.vercel.app"
        self.assertIn(f'const LOCAL_CAR_VERCEL_PRODUCTION_HOST = "{host}";', self.js)
        self.assertIn('const LOCAL_CAR_VERCEL_PRODUCTION_MODE = isAuthorizedCarProductionHost(location.protocol, location.hostname);', self.js)
        function = re.search(
            r"function isAuthorizedCarProductionHost\(protocol, hostname\) \{\s*return protocol === \"https:\" && hostname === LOCAL_CAR_VERCEL_PRODUCTION_HOST;\s*\}",
            self.js,
        )
        self.assertIsNotNone(function)
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is unavailable; exact-host source assertions still apply")
        script = (
            f'const LOCAL_CAR_VERCEL_PRODUCTION_HOST = "{host}";\n'
            f'{function.group(0)}\n'
            'const assert = require("node:assert/strict");\n'
            'assert.equal(isAuthorizedCarProductionHost("https:", "regscope-aiot.vercel.app"), true);\n'
            'assert.equal(isAuthorizedCarProductionHost("http:", "regscope-aiot.vercel.app"), false);\n'
            'assert.equal(isAuthorizedCarProductionHost("https:", "sub.regscope-aiot.vercel.app"), false);\n'
            'assert.equal(isAuthorizedCarProductionHost("https:", "regscope-other-preview.vercel.app"), false);\n'
        )
        result = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_car_online_preview_host_allows_only_authorized_branch_alias(self):
        host = "regscope-git-feat-phase6-online-8ac39b-wupojung-8919s-projects.vercel.app"
        self.assertIn(f'const LOCAL_CAR_VERCEL_PREVIEW_HOST = "{host}";', self.js)
        self.assertIn('return hostname === LOCAL_CAR_VERCEL_PREVIEW_HOST;', self.js)
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is unavailable; exact-host source assertions still apply")
        function = re.search(
            r"function isAuthorizedCarOnlinePreviewHost\(hostname\) \{\s*return hostname === LOCAL_CAR_VERCEL_PREVIEW_HOST;\s*\}",
            self.js,
        )
        self.assertIsNotNone(function)
        script = (
            f'const LOCAL_CAR_VERCEL_PREVIEW_HOST = "{host}";\n'
            f'{function.group(0)}\n'
            'const assert = require("node:assert/strict");\n'
            f'assert.equal(isAuthorizedCarOnlinePreviewHost("{host}"), true);\n'
            'assert.equal(isAuthorizedCarOnlinePreviewHost("regscope-aiot.vercel.app"), false);\n'
            'assert.equal(isAuthorizedCarOnlinePreviewHost("regscope-other-preview.vercel.app"), false);\n'
        )
        result = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_car_phase3_raw_bar_is_lineage_derived_and_keeps_later_stages_dynamic(self):
        self.assertIn('const rawFields = lineage.raw_fields || [];', self.js)
        self.assertIn('const rawClassification = lineage.raw_classification || {};', self.js)
        self.assertIn('const rawCountsMatch =', self.js)
        self.assertIn('rawClassification.evidence.source_data_sha256 === lineage.source_data_sha256', self.js)
        self.assertIn('rawClassification.total === rawFields.length', self.js)
        self.assertIn('segments: Object.entries(rawClassification.counts)', self.js)
        self.assertIn('stage.id === "raw");', self.js)
        self.assertIn('const inlineLabels = !compactLabels || percent >= 16', self.js)
        self.assertIn('const exclusionGroups = Object.entries(excludedFields.reduce', self.js)
        self.assertIn('rawFields.map((item) =>', self.js)
        self.assertNotIn('涵蓋 27 個目標以外', self.js)
        self.assertNotIn('保留 15 個原始特徵。', self.js)
        self.assertNotIn('產生 70 個模型特徵', self.js)

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

    def test_car_method_labels_are_exact_id_mapped_and_separate_from_regressor(self):
        expected = {
            'ols_baseline: { name: "OLS Baseline"',
            'pearson: { name: "Pearson Correlation"',
            'mutual_information: { name: "Mutual Information"',
            'lasso: { name: "Lasso Selection"',
            'elastic_net: { name: "Elastic Net"',
            'ridge_rfe: { name: "Ridge RFE"'
        }
        for mapping in expected:
            self.assertIn(mapping, self.js)
        self.assertIn('explorationMethodLabel(doc, method.method_id)', self.js)
        self.assertIn('explorationMethodLabel(doc, item.method_id)', self.js)
        self.assertIn('<dt>Feature Selection</dt>', self.js)
        self.assertIn('<dt>Regression Model</dt>', self.js)
        self.assertIn('fold_local_selected_features_to_primary_ols: "OLS"', self.js)
        self.assertIn('|| evaluation?.model_name', self.js)
        self.assertIn('doc.methods?.find((item) => item.method_id === methodId)', self.js)
        self.assertIn('以互資訊評估特徵與目標值的統計依賴關係。', self.js)

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
        for case_id in ("ames-full-model-exploration",):
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

    def test_public_release_has_ames_car_and_steam_cases(self):
        release = json.loads((WEB / "data/current-release.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [item["case_id"] for item in release["cases"]],
            ["ames-full-model-exploration", "used-car-price-optimized", "steam-review-multiplier"],
        )
        self.assertIn('const PUBLIC_CASE_IDS = [EXPLORATION_CASE_ID, CAR_CASE_ID, STEAM_CASE_ID];', self.js)
        self.assertIn('PUBLIC_CASE_IDS.filter((id) => CASES[id])', self.js)
        self.assertIn('caseId: "ames-full-model-exploration"', self.js)
        self.assertIn('title: "Steam Review Multiplier — Homework"', self.js)
        self.assertIn('const CAR_DISPLAY_NAME = "Used Car Price Prediction — Optimized Modeling";', self.js)
        self.assertNotIn('loadReferencePackage();\n  if (!explorationPackage', self.js)

    def test_steam_release_package_is_hash_bound_and_has_no_private_model_or_rows(self):
        release = json.loads((WEB / "data/current-release.json").read_text(encoding="utf-8"))
        entry = next(item for item in release["cases"] if item["case_id"] == "steam-review-multiplier")
        package_path = WEB / "data" / entry["package_ref"]
        package_bytes = package_path.read_bytes()
        self.assertEqual(hashlib.sha256(package_bytes).hexdigest(), entry["package_sha256"])
        self.assertEqual(len(package_bytes), entry["package_bytes"])
        manifest = json.loads(package_bytes)
        self.assertEqual(manifest["case_id"], entry["case_id"])
        self.assertEqual(manifest["package_status"], "PARTIAL")
        self.assertFalse(manifest["publication"]["approved"])
        package_root = package_path.parent
        for item in manifest["files"]:
            path = package_root / item["path"]
            data = path.read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"], item["path"])
            self.assertEqual(len(data), item["bytes"], item["path"])
            self.assertNotIn(path.suffix.lower(), {".csv", ".joblib", ".pkl", ".pickle"})
        self.assertIn('function renderSteamPhase(phase)', self.js)
        self.assertNotIn('/api/steam/predict', self.js)
        self.assertIn('id="steam-predict-form"', self.js)
        self.assertIn('未載入 Mock Prediction', self.js)
        self.assertIn('線上 Steam 預測目前不可用', self.js)
        self.assertIn('未載入 Mock Prediction，也不會改用固定 K。', self.js)

    def test_steam_package_load_is_lazy_until_steam_is_selected(self):
        render_start = self.js.index("function render() {")
        render_end = self.js.index("\nfunction ", render_start + 1)
        render_body = self.js[render_start:render_end]
        self.assertIn(
            "state.caseId === STEAM_CASE_ID && !steamPackage && !steamPackageError && !steamPackageLoading",
            render_body,
        )
        self.assertNotIn("if (!steamPackage && !steamPackageError && !steamPackageLoading)", render_body)

    def test_vercel_release_route_allows_only_release_index_package_paths(self):
        vercel = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        deny_rule = next(route for route in vercel["routes"] if route.get("status") == 404 and route.get("src", "").startswith("^/data/releases/"))
        pattern = re.compile(deny_rule["src"])
        release = json.loads((WEB / "data/current-release.json").read_text(encoding="utf-8"))
        for case in release["cases"]:
            package_ref = case["package_ref"].removeprefix("releases/")
            package_dir = package_ref.rsplit("/", 1)[0]
            request_path = f"/data/releases/{package_dir}/phase1/business-understanding.json"
            with self.subTest(case_id=case["case_id"]):
                self.assertIsNone(pattern.match(request_path))
        self.assertIsNotNone(pattern.match("/data/releases/unapproved/cases/example/package.json"))

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

    def test_steam_phase6_uses_verified_contract_and_real_same_origin_api(self):
        self.assertIn('if (state.caseId === STEAM_CASE_ID && !steamPackage', self.js)
        self.assertIn('void loadSteamInferenceSchema();', self.js)
        self.assertIn('document.schema_sha256 !== schemaEntry.sha256', self.js)
        self.assertIn('JSON.stringify(inputSchema) !== JSON.stringify(packageSchema)', self.js)
        self.assertIn('data-action="steam-fill-demo"', self.js)
        self.assertIn('data-action="steam-mode-batch"', self.js)
        self.assertIn('fetch("/api/predict"', self.js)
        self.assertIn('fetch("/api/predict-batch?case_id=steam-review-multiplier"', self.js)
        self.assertIn('data-action="steam-batch-download"', self.js)
        self.assertIn('22 個工程輸入均須提供', self.js)
        self.assertIn('K = 30 基準', self.js)
        self.assertIn('不會改用固定 K', self.js)

    def test_steam_release_revision_keeps_partial_unapproved_and_package_bound(self):
        import hashlib
        import json

        release = json.loads((WEB / "data/current-release.json").read_text(encoding="utf-8"))
        pointer = next(item for item in release["cases"] if item["case_id"] == "steam-review-multiplier")
        package_path = WEB / "data" / pointer["package_ref"]
        package_bytes = package_path.read_bytes()
        self.assertEqual(hashlib.sha256(package_bytes).hexdigest(), pointer["package_sha256"])
        package = json.loads(package_bytes)
        self.assertEqual(package["package_status"], "PARTIAL")
        self.assertFalse(package["publication"]["approved"])
        self.assertEqual(package["package_revision"], "steam-homework-20261102-02")
        for entry in package["files"]:
            payload = (package_path.parent / entry["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), entry["sha256"])
            self.assertEqual(len(payload), entry["bytes"])


if __name__ == "__main__":
    unittest.main()
