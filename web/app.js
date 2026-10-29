const SOURCE = "PR #35 HEAD 08413d08f5cabbbf519b8ceee4ed68b7187d2669";
const REF = {
  phase1: "docs/ui-ux/case-package/sample/ames-housing/phases/phase-01/content.json",
  phase2: "docs/ui-ux/case-package/sample/ames-housing/phases/phase-02/analyses.json",
  phase3: "docs/ui-ux/case-package/sample/ames-housing/phases/phase-03/preparation.json",
  phase4: "docs/ui-ux/case-package/sample/ames-housing/phases/phase-04/modeling.json",
  phase5: "docs/ui-ux/case-package/phase-05/sample/evaluations.json",
  phase6: "docs/ui-ux/case-package/sample/ames-housing/phases/phase-06/inference-catalog.json"
};
const PHASES = [
  [1, "Business Understanding", "業務理解"],
  [2, "Data Understanding", "資料理解"],
  [3, "Data Preparation", "資料準備"],
  [4, "Modeling", "模型建立"],
  [5, "Evaluation", "模型評估"],
  [6, "Deployment", "模型預測實驗室"]
];
const TYPES = [
  ["nominal", "名目 (Nominal)", "#55d6c2"],
  ["ordinal", "次序 (Ordinal)", "#a9df62"],
  ["discrete", "離散 (Discrete)", "#70b5e8"],
  ["continuous", "連續 (Continuous)", "#f1b45b"]
];
const AMES_NEIGHBORHOODS = ["Blmngtn", "Blueste", "BrDale", "BrkSide", "ClearCr", "CollgCr", "Crawfor", "Edwards", "Gilbert", "IDOTRR", "MeadowV", "Mitchel", "NAmes", "NPkVill", "NWAmes", "NoRidge", "NridgHt", "OldTown", "SWISU", "Sawyer", "SawyerW", "Somerst", "StoneBr", "Timber", "Veenker"];
const OVERALL_QUALITY_LABELS = {
  1: "Very Poor · 非常差", 2: "Poor · 差", 3: "Fair · 尚可", 4: "Below Average · 低於平均", 5: "Average · 平均",
  6: "Above Average · 高於平均", 7: "Good · 良好", 8: "Very Good · 非常好", 9: "Excellent · 優秀", 10: "Very Excellent · 極佳"
};
const CASES = {
  "ames-housing": {
    id: "ames-housing", title: "Ames Housing — MOCK UI Sample", status: "MOCK",
    source: "Kaggle House Prices", sourceUrl: "https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data",
    license: "PENDING", target: { column: "SalePrice", label: "售價", unit: "USD" },
    methodology: "mlr-feature-selection-v1", packageRevision: "sample-r1",
    sections: [
      { title: "研究問題 Research question", body: "合成案例示意：住宅結構與位置特徵可能如何與售價相關？ Synthetic case prompt: how might structural and location features relate to sale price?" },
      { title: "研究目標 Research objective", body: "示意以多元線性迴歸建立基準，並比較特徵選擇方法。 Illustrate a regression baseline and feature-selection comparison." },
      { title: "限制 Limitations", body: "研究問題與內容為 UI mock；不代表真實研究結論。 Research prompts are mock UI content, not verified findings." }
    ],
    analyses: [
      ["overview", "FIG-01", "資料集概覽"],
      ["missingness", "FIG-02", "缺失值分析"],
      ["saleprice", "FIG-03", "售價分布"],
      ["correlation", "FIG-06", "數值相關分析"]
    ].map(([id, figureId, title]) => ({ id, figureId, title, status: "UNAVAILABLE", imageRef: null, tableRef: null,
      description: "待綁定已核准圖資", finding: null,
      limitations: "圖資尚未通過此 Sample 的發布審查", provenanceRef: null })).map((analysis) => ({
      ...analysis,
      status: "MOCK",
      description: "合成 UI 示意資料，僅用來預覽圖表與互動。",
      finding: "以下數值為人工合成，不能解讀成 Ames Housing 的研究發現。",
      limitations: "所有圖表數值皆為 MOCK，未由原始資料計算。",
      mockData: ({
        overview: [{ label: "資料列 Rows", value: 1460 }, { label: "預測欄位 Predictors", value: 79 }, { label: "目標欄位 Target", value: 1 }, { label: "缺值欄位 Fields with missing values", value: 15 }],
        missingness: [{ label: "Feature A", value: 42 }, { label: "Feature B", value: 27 }, { label: "Feature C", value: 18 }, { label: "Feature D", value: 9 }],
        saleprice: [{ label: "0–100k USD", value: 12 }, { label: "100–200k USD", value: 39 }, { label: "200–300k USD", value: 31 }, { label: "300–400k USD", value: 13 }, { label: "400k+ USD", value: 5 }],
        correlation: [{ label: "Feature A ↔ target", value: 78 }, { label: "Feature B ↔ target", value: 64 }, { label: "Feature C ↔ target", value: 41 }, { label: "Feature D ↔ target", value: 22 }]
      })[analysis.id]
    })),
    stages: null,
    split: null,
    cv: { trainingRows: 1168, foldCount: 3, protocolId: null, status: "SOURCE_REPORTED_NOT_VERIFIED" },
    methods: [
      { id: "pearson", label: "Pearson", parameters: [{ id: "top_k", label: "Top K", dataType: "integer" }] },
      { id: "lasso", label: "Lasso", parameters: [{ id: "alpha", label: "Alpha", dataType: "number" }] },
      { id: "elastic_net", label: "Elastic Net", parameters: [{ id: "alpha", label: "Alpha", dataType: "number" }, { id: "l1_ratio", label: "L1 Ratio", dataType: "number" }] }
    ],
    configurations: [],
    mockModelRuns: [
      { id: "MOCK-RUN-01", method: "Pearson + Linear Regression", featureCount: 24, rmse: 31250, mae: 21800, r2: 0.84, selectedFeatures: ["Feature A", "Feature C", "Feature F", "Feature H"] },
      { id: "MOCK-RUN-02", method: "Lasso + Linear Regression", featureCount: 18, rmse: 29800, mae: 20750, r2: 0.86, selectedFeatures: ["Feature A", "Feature B", "Feature F", "Feature K"] },
      { id: "MOCK-RUN-03", method: "Elastic Net + Linear Regression", featureCount: 21, rmse: 30420, mae: 21200, r2: 0.85, selectedFeatures: ["Feature A", "Feature C", "Feature H", "Feature M"] }
    ],
    mockFeatureCurve: [{ features: 8, rmse: 34200 }, { features: 16, rmse: 31100 }, { features: 24, rmse: 29800 }, { features: 32, rmse: 30500 }, { features: 40, rmse: 31900 }],
    mockInference: { modelId: "MOCK-MODEL-01", runId: "MOCK-RUN-02", estimate: 238500, lower: 210000, upper: 267000, target: "SalePrice", unit: "USD" },
    evaluation: { status: "MOCK", reasonCode: "MOCK_UI_ONLY", evaluations: [], figures: [
      ["FIG-P5-02", "殘差對預測值 Residual vs Predicted"], ["FIG-P5-01", "實際值對預測值 Actual vs Predicted"], ["FIG-P5-03", "殘差分布 Residual Distribution"]
    ], intervalF: "MOCK", intervalS: "MOCK", mock: {
      configId: "MOCK-CONFIG-02", runId: "MOCK-RUN-02", evaluationId: "MOCK-EVAL-01", population: "Development OOF",
      metrics: { mae: 20750, rmse: 29800, r2: 0.86 },
      intervals: { method: "Synthetic bootstrap interval", lower: 82000, upper: 365000, coverage: 0.91 },
      predictions: [{ actual: 110000, predicted: 118000 }, { actual: 160000, predicted: 151000 }, { actual: 210000, predicted: 218000 }, { actual: 280000, predicted: 267000 }, { actual: 360000, predicted: 374000 }, { actual: 440000, predicted: 421000 }],
      residuals: [-8000, 9000, -8000, 13000, -14000, 19000],
      histogram: [{ label: "≤ -20k", value: 8 }, { label: "-20k to -10k", value: 17 }, { label: "-10k to 0", value: 29 }, { label: "0 to 10k", value: 28 }, { label: "10k to 20k", value: 14 }, { label: "≥ 20k", value: 4 }]
    } },
    inference: { status: "UNAVAILABLE", models: [], reasonCode: "NO_APPROVED_MODEL", message: "此模型尚未準備好；請返回 Phase 4 或選擇已核准模型。" }
  },
  "planned-case": {
    id: "planned-case", title: "Planned Case — Placeholder", status: "PLANNED", source: null, sourceUrl: null, license: "PENDING",
    target: null, methodology: null, packageRevision: "sample-r1", sections: [], analyses: [], stages: [], split: null,
    cv: null, methods: [], configurations: [], evaluation: null,
    inference: { status: "UNAVAILABLE", models: [], reasonCode: "NO_APPROVED_MODEL", message: "此案例尚無研究成果或可用模型。" }
  }
};
CASES["ames-housing-formal"] = {
  ...CASES["ames-housing"],
  title: "Ames Housing — Formal Case Package · Phase 5",
  packageStatus: "VERIFIED",
  packageMode: "formal",
  packageRevision: "local-staging-p5-formal-data-test-20261027-01"
};
CASES["ames-housing"].packageMode = "mock";

const state = {
  caseId: "ames-housing", route: "home", analysisId: "overview", perspective: "method_comparison",
  phase4RunId: "MOCK-RUN-02", phase6MockSubmitted: false,
  referenceAnalysisId: "figure-field-decisions",
  referenceFigureId: "FIG-P5-01",
  phase6InputMode: "manual", phase6Csv: null, phase6CsvMessage: "尚未選擇 CSV 檔案。",
  phase6Values: { neighborhood: "CollgCr", quality: "6", bedrooms: "3", area: "1800" },
  phase5Figure: "FIG-P5-02", p5Population: "development_oof", p5DetailsOpen: false, phase5ConfigId: "",
  explorationMode: "comparison", explorationPerspective: "selected_features", explorationMethodId: "", explorationConfigurationId: "", explorationP5Figure: "FIG-P5-01",
  dashboardMode: "verified", customSource: "file", customFile: null, customUrl: "", customHeaders: [], customRows: [],
  targetField: "", featureFields: [], csvMessage: "尚未載入資料。CSV 僅在此瀏覽器本機預覽，不會上傳。", customValidated: false
};
const app = document.querySelector("#app");
const phaseNav = document.querySelector("#phase-nav");
const caseContext = document.querySelector("#case-context");
const caseSelect = document.querySelector("#case-select");
const WEB_BASE = location.pathname.startsWith("/web/") ? "/web" : "";
const IS_LOCAL_STAGING_PREVIEW = ["localhost", "127.0.0.1"].includes(location.hostname) && location.pathname.startsWith("/web/");
const REFERENCE_RELEASE_INDEX = `${WEB_BASE}/data/current-release.json`;
let REFERENCE_PACKAGE_ROOT = null;
const PHASE5_PACKAGE_ROOT = IS_LOCAL_STAGING_PREVIEW
  ? "/local/staging/formal-data-test-20261027-01/case-package"
  : null;
let phase5PackageData = null;
let phase5PackageLoading = false;
let phase5PackageLoadError = null;

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}
function qualityScaleLabel(value) { return `${value} · ${OVERALL_QUALITY_LABELS[value] || ""}`; }
function statusLabel(status) {
  const labels = { MOCK: "示意資料 MOCK", UNAVAILABLE: "無可用資料 UNAVAILABLE", PLANNED: "規劃中 PLANNED", PUBLISHED: "已發布 PUBLISHED", VERIFIED: "已驗證 VERIFIED", LOCAL_PRIVATE_VERIFIED: "本機私有模型已驗證 LOCAL PRIVATE VERIFIED", ERROR: "錯誤 ERROR", SOURCE_REPORTED_NOT_VERIFIED: "來源回報・尚未驗證 SOURCE REPORTED · NOT VERIFIED" };
  return labels[status] || status || "未知 UNKNOWN";
}
function statusClass(status) {
  return ({ MOCK: "mock", UNAVAILABLE: "unavailable", PLANNED: "planned", PUBLISHED: "published", VERIFIED: "verified", LOCAL_PRIVATE_VERIFIED: "verified", ERROR: "error", SOURCE_REPORTED_NOT_VERIFIED: "mock" })[status] || "unavailable";
}
function badge(status) { return `<span class="status ${statusClass(status)}">${esc(statusLabel(status))}</span>`; }
function caseData() { return CASES[state.caseId] || CASES["planned-case"]; }
function isPhaseRoute() { return state.route.startsWith("phase-"); }
function routePhase() { return isPhaseRoute() ? Number(state.route.slice(6)) || 1 : 0; }
function setRoute(route) { location.hash = route; }
function setPhase(phase) { setRoute(`phase-${phase}`); }
function banner(caseInfo = caseData()) {
  const formalPackage = caseInfo.packageMode === "formal";
  const explorationPackageMode = caseInfo.packageMode === "exploration";
  const reason = formalPackage
    ? `Formal Case Package ${caseInfo.packageRevision} · only Phase 5 reads local staging; Phases 1–4 remain MOCK UI previews. This is not a public release.`
    : caseInfo.packageMode === "car"
    ? `CAR research package ${caseInfo.packageRevision} · local review only; publication approval is pending.`
    : caseInfo.packageMode === "reference"
    ? `公開 Case Package ${caseInfo.packageRevision} · INIT B 正式 Development 計算；Phase 5 為 OOF 評估，研究發布審查仍待完成。`
    : explorationPackageMode
    ? `Historical Development model exploration · package revision ${caseInfo.packageRevision} · completed configurations only; publication review pending.`
    : caseInfo.status === "MOCK"
    ? `UI fixture only · package revision ${caseInfo.packageRevision} · ${SOURCE}. These values are not approved research results.`
    : "Planned placeholder only · no research package, data, or model is available.";
  const bannerStatus = caseInfo.status;
  return `<div class="fixture-banner"><span><strong>${formalPackage ? "Formal package preview" : explorationPackageMode ? "Historical exploration package" : caseInfo.status === "MOCK" ? "Fixture preview" : "Planned case"}</strong> · ${esc(reason)}</span>${badge(bannerStatus)}</div>`;
}
function updateShell() {
  const phase = routePhase();
  caseContext.hidden = !phase || state.route === "home" || state.route === "dashboard";
  phaseNav.hidden = !phase || state.route === "home" || state.route === "dashboard";
  phaseNav.innerHTML = PHASES.map(([n, en, zh]) => `<a class="phase-tab" href="#phase-${n}" ${phase === n ? 'aria-current="page"' : ""}><span class="num">0${n}</span><span class="phase-zh">${esc(zh)}</span><span class="phase-en">${esc(en)}</span></a>`).join("");
  document.querySelector("[data-home-link]").setAttribute("aria-current", state.route === "home" ? "page" : "false");
  document.querySelector("[data-crisp-link]").setAttribute("aria-current", phase ? "page" : "false");
  caseSelect.innerHTML = Object.entries(CASES).map(([key, c]) => `<option value="${esc(key)}" ${key === state.caseId ? "selected" : ""}>${esc(c.title)} · ${c.packageMode === "formal" ? "FORMAL PACKAGE" : esc(c.status)}</option>`).join("");
  const caseLoadStatus = document.querySelector("#case-load-status");
  const loading = referencePackageLoading || explorationPackageLoading || carPackageLoading;
  const failedCases = [
    referencePackageError ? "INIT B Reference Baseline" : null,
    explorationPackageError ? "Full Model Exploration" : null,
    carPackageError ? "Used Car Price Prediction" : null
  ].filter(Boolean);
  caseSelect.disabled = loading;
  caseLoadStatus.classList.toggle("is-error", failedCases.length > 0);
  if (loading) {
    caseLoadStatus.setAttribute("role", failedCases.length ? "alert" : "status");
    caseLoadStatus.textContent = failedCases.length
      ? `研究案例載入中…（${failedCases.join("、")}載入失敗；其餘案例仍在驗證）`
      : "研究案例載入中…";
  } else if (failedCases.length) {
    caseLoadStatus.setAttribute("role", "alert");
    caseLoadStatus.textContent = `研究案例載入失敗：${failedCases.join("、")}。其餘已驗證案例仍可使用。`;
  } else {
    caseLoadStatus.setAttribute("role", "status");
    caseLoadStatus.textContent = `研究案例載入完成，共 ${Object.keys(CASES).length} 個可用案例。`;
  }
}

// Reference packages are resolved from a small pointer to an immutable static release.
let referencePackage = null;
let referencePackageError = null;
let referencePackageLoading = false;
let explorationPackage = null;
let explorationPackageError = null;
let explorationPackageLoading = false;
let carPackage = null;
let carPackageError = null;
let carPackageLoading = false;
const EXPLORATION_CASE_ID = "ames-full-model-exploration";
const CAR_CASE_ID = "used-car-price-optimized";
const explorationArtifactPromises = new Map();
function safePackageRef(ref) {
  return typeof ref === "string" && !ref.startsWith("/") && !ref.includes("\\")
    && ref.split("/").every((part) => part && part !== "." && part !== "..");
}
function validatePhase3Lineage(pkg, preparation, lineage) {
  const sourceSha = pkg.executionManifest?.source_data_sha256 || pkg.executionManifest?.source_sha256;
  if (!lineage || lineage.case_id !== pkg.manifest.case_id
      || !/^[0-9a-f]{64}$/.test(sourceSha || "")
      || lineage.source_data_sha256 !== sourceSha
      || lineage.fit_population !== "development_train_only") {
    throw new Error("Phase 3 feature lineage identity or source binding mismatch.");
  }
  const encoded = lineage.encoded_features;
  const encodedStage = preparation.stages?.find((stage) => stage.id === "encoded");
  if (!Array.isArray(encoded) || !encodedStage || encoded.length !== encodedStage.total
      || new Set(encoded.map((item) => item.encoded_feature)).size !== encoded.length
      || encoded.some((item) => !item.encoded_feature || !Array.isArray(item.source_columns)
        || !item.source_columns.length || !item.semantic_type || !item.transformation)) {
    throw new Error("Phase 3 encoded feature lineage is incomplete or inconsistent.");
  }
  const counts = Object.fromEntries(["nominal", "ordinal", "discrete", "continuous"].map((type) => [type, 0]));
  for (const item of encoded) {
    if (!Object.hasOwn(counts, item.semantic_type)) throw new Error("Phase 3 lineage contains an unknown feature type.");
    counts[item.semantic_type] += 1;
  }
  const expected = Object.fromEntries((encodedStage.segments || []).map((segment) => [segment.type_id, segment.count]));
  if (Object.keys(counts).some((type) => counts[type] !== expected[type])) {
    throw new Error("Phase 3 encoded feature lineage counts disagree with the Case Package.");
  }
  return lineage;
}
function logPackageLoadFailure(caseId, stage, error) {
  const detail = error instanceof Error ? error.message : "Unknown error";
  const safeDetail = detail
    .replace(/https?:\/\/\S+/g, "[URL]")
    .replace(/(?:\/(?:Users|private|tmp|var|home)\/\S+|[A-Za-z]:\\[^\s]+)/g, "[local path]")
    .slice(0, 180);
  console.warn("[RegScope] Case Package validation failed", {
    caseId,
    stage,
    errorName: error instanceof Error ? error.name : "Error",
    detail: safeDetail
  });
}
async function loadReferencePackage() {
  if (referencePackage || referencePackageError || referencePackageLoading) return;
  referencePackageLoading = true;
  let stage = "release_index";
  try {
    const releaseResponse = await fetch(REFERENCE_RELEASE_INDEX);
    if (!releaseResponse.ok) throw new Error(`Release index request failed (${releaseResponse.status}).`);
    const releaseIndex = await releaseResponse.json();
    if (releaseIndex.schema_version !== "1.0.0" || !Array.isArray(releaseIndex.cases)) throw new Error("Invalid Case Package release index.");
    const releaseCase = releaseIndex.cases.find((entry) => entry.case_id === "ames-reference-init-a");
    const packageRef = releaseCase?.package_ref;
    const packagePath = typeof packageRef === "string" ? packageRef.split("/") : [];
    if (!safePackageRef(packageRef) || packagePath.length !== 5 || packagePath[0] !== "releases" || packagePath[2] !== "cases" || packagePath[3] !== "ames-reference-init-a" || packagePath[4] !== "package.json" || !/^[a-z0-9][a-z0-9._-]{2,79}$/.test(packagePath[1])) {
      throw new Error("Release index has no safe reference for the Ames case.");
    }
    REFERENCE_PACKAGE_ROOT = `${WEB_BASE}/data/${packagePath.slice(0, -1).join("/")}`;
    stage = "package_manifest";
    const packageResponse = await fetch(`${WEB_BASE}/data/${packageRef}`);
    if (!packageResponse.ok) throw new Error(`Case Package request failed (${packageResponse.status}).`);
    const packageBytes = await packageResponse.arrayBuffer();
    const packageDigest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", packageBytes))].map((v) => v.toString(16).padStart(2,"0")).join("");
    if (packageDigest !== releaseCase.package_sha256 || packageBytes.byteLength !== releaseCase.package_bytes) throw new Error("Release index package digest/size mismatch.");
    const manifest = JSON.parse(new TextDecoder().decode(packageBytes));
    if (manifest.package_revision !== packagePath[1] || manifest.package_status !== releaseCase.package_status) throw new Error("Release index and Case Package metadata disagree.");
    if (manifest.case_id !== "ames-reference-init-a" || !Array.isArray(manifest.files)) throw new Error("Unexpected Case Package identity or file manifest.");
    const listed = new Map(manifest.files.map((entry) => [entry.path, entry]));
    if (listed.size !== manifest.files.length) throw new Error("Duplicate Case Package file entry.");
    const docs = {};
    stage = "phase_documents";
    for (const [phase, fallback] of [[1,"phases/phase-01/content.json"],[2,"phases/phase-02/analyses.json"],[3,"phases/phase-03/preparation.json"],[4,"phases/phase-04/modeling.json"],[5,"phases/phase-05/evaluations.json"],[6,"phases/phase-06/inference-catalog.json"]]) {
      const ref = manifest.phases?.[`phase${phase}`]?.data_ref || fallback;
      const entry = listed.get(ref);
      if (!entry) throw new Error(`Phase ${phase} reference is not package-manifest-listed.`);
      const response = await fetch(`${REFERENCE_PACKAGE_ROOT}/${ref}`);
      if (!response.ok) throw new Error(`Phase ${phase} request failed (${response.status}).`);
      const bytes = await response.arrayBuffer();
      const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map((v) => v.toString(16).padStart(2,"0")).join("");
      if (digest !== entry.sha256 || bytes.byteLength !== entry.bytes) throw new Error(`Phase ${phase} manifest digest/size mismatch.`);
      docs[phase] = JSON.parse(new TextDecoder().decode(bytes));
      if (docs[phase].case_id !== manifest.case_id) throw new Error(`Phase ${phase} Case ID mismatch.`);
    }
    stage = "phase3_lineage";
    const phase3LineageRef = docs[3].lineage_ref;
    const phase3LineageEntry = listed.get(phase3LineageRef);
    if (!safePackageRef(phase3LineageRef) || !phase3LineageEntry) throw new Error("Phase 3 lineage is not package-manifest-listed.");
    const phase3LineageResponse = await fetch(`${REFERENCE_PACKAGE_ROOT}/${phase3LineageRef}`);
    if (!phase3LineageResponse.ok) throw new Error(`Phase 3 lineage request failed (${phase3LineageResponse.status}).`);
    const phase3LineageBytes = await phase3LineageResponse.arrayBuffer();
    const phase3LineageDigest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", phase3LineageBytes))].map((v) => v.toString(16).padStart(2,"0")).join("");
    if (phase3LineageDigest !== phase3LineageEntry.sha256 || phase3LineageBytes.byteLength !== phase3LineageEntry.bytes) throw new Error("Phase 3 lineage manifest digest/size mismatch.");
    const phase3LineageDocument = JSON.parse(new TextDecoder().decode(phase3LineageBytes));
    stage = "execution_manifest";
    const executionEntry = listed.get("assets/execution-manifest.json");
    if (!executionEntry) throw new Error("Execution manifest is not package-manifest-listed.");
    const executionResponse = await fetch(`${REFERENCE_PACKAGE_ROOT}/assets/execution-manifest.json`);
    if (!executionResponse.ok) throw new Error(`Execution manifest request failed (${executionResponse.status}).`);
    const executionBytes = await executionResponse.arrayBuffer();
    const executionDigest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", executionBytes))].map((v) => v.toString(16).padStart(2,"0")).join("");
    if (executionDigest !== executionEntry.sha256 || executionBytes.byteLength !== executionEntry.bytes) throw new Error("Execution manifest digest/size mismatch.");
    const executionManifest = JSON.parse(new TextDecoder().decode(executionBytes));
    if (executionManifest.case_id !== manifest.case_id) throw new Error("Execution manifest Case ID mismatch.");
    const phase3Lineage = validatePhase3Lineage({ manifest, executionManifest }, docs[3], phase3LineageDocument);
    stage = "case_document";
    const caseEntry = listed.get(manifest.case_ref);
    if (!caseEntry || !safePackageRef(manifest.case_ref)) throw new Error("Case document is not package-manifest-listed.");
    const caseResponse = await fetch(`${REFERENCE_PACKAGE_ROOT}/${manifest.case_ref}`);
    if (!caseResponse.ok) throw new Error(`Case document request failed (${caseResponse.status}).`);
    const caseBytes = await caseResponse.arrayBuffer();
    const caseDigest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", caseBytes))].map((v) => v.toString(16).padStart(2,"0")).join("");
    if (caseDigest !== caseEntry.sha256 || caseBytes.byteLength !== caseEntry.bytes) throw new Error("Case document manifest digest/size mismatch.");
    const caseDoc = JSON.parse(new TextDecoder().decode(caseBytes));
    if (caseDoc.case_id !== manifest.case_id || caseDoc.case_status !== manifest.package_status) throw new Error("Case document identity/status mismatch.");
    stage = "figures";
    for (const entry of manifest.files.filter((item) => ["image/svg+xml", "image/png"].includes(item.mime))) {
      if (!safePackageRef(entry.path)) throw new Error("Unsafe figure path reference.");
      const response = await fetch(`${REFERENCE_PACKAGE_ROOT}/${entry.path}`);
      if (!response.ok) throw new Error(`Figure request failed (${response.status}).`);
      const bytes = await response.arrayBuffer();
      const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map((v) => v.toString(16).padStart(2,"0")).join("");
      if (digest !== entry.sha256 || bytes.byteLength !== entry.bytes) throw new Error("Figure manifest digest/size mismatch.");
    }
    stage = "phase4_metrics";
    const defaultConfig = docs[4].configurations.find((item) => item.configuration_id === docs[4].default_configuration_id);
    const metricsRef = defaultConfig?.cv_metrics_ref;
    const metricsEntry = manifest.files.find((entry) => entry.path === metricsRef);
    if (!metricsEntry || !safePackageRef(metricsRef)) throw new Error("Phase 4 CV metrics reference is not package-bound.");
    const metricsResponse = await fetch(`${REFERENCE_PACKAGE_ROOT}/${metricsRef}`);
    if (!metricsResponse.ok) throw new Error(`Phase 4 metrics request failed (${metricsResponse.status}).`);
    const metricsBytes = await metricsResponse.arrayBuffer();
    const metricsDigest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", metricsBytes))].map((v) => v.toString(16).padStart(2,"0")).join("");
    if (metricsDigest !== metricsEntry.sha256 || metricsBytes.byteLength !== metricsEntry.bytes) throw new Error("Phase 4 metrics manifest digest/size mismatch.");
    const cvMetrics = JSON.parse(new TextDecoder().decode(metricsBytes));
    if (cvMetrics.case_id !== manifest.case_id || cvMetrics.run_id !== defaultConfig.execution_run_id) throw new Error("Phase 4 metrics identity mismatch.");
    stage = "phase6_smoke";
    const smokeRef = "assets/phase6-inference-smoke.json";
    const smokeEntry = listed.get(smokeRef);
    if (!smokeEntry) throw new Error("Phase 6 inference smoke evidence is not package-manifest-listed.");
    const smokeResponse = await fetch(`${REFERENCE_PACKAGE_ROOT}/${smokeRef}`);
    if (!smokeResponse.ok) throw new Error(`Phase 6 smoke evidence request failed (${smokeResponse.status}).`);
    const smokeBytes = await smokeResponse.arrayBuffer();
    const smokeDigest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", smokeBytes))].map((v) => v.toString(16).padStart(2,"0")).join("");
    if (smokeDigest !== smokeEntry.sha256 || smokeBytes.byteLength !== smokeEntry.bytes) throw new Error("Phase 6 smoke evidence manifest digest/size mismatch.");
    const phase6Smoke = JSON.parse(new TextDecoder().decode(smokeBytes));
    referencePackage = { manifest, caseDoc, docs, cvMetrics, phase6Smoke, phase3Lineage, executionManifest, root: REFERENCE_PACKAGE_ROOT, figurePaths: manifest.files.filter((item) => ["image/svg+xml", "image/png"].includes(item.mime)).map((item) => item.path) };
    CASES[manifest.case_id] = { id: manifest.case_id, title: "Ames Housing — INIT B Reference Baseline", status: manifest.package_status, packageMode: "reference", packageRevision: manifest.package_revision, analyses: [] };
  } catch (error) {
    referencePackageError = error instanceof Error ? error.message : "Unable to verify Case Package.";
    logPackageLoadFailure("ames-reference-init-a", stage, error);
  } finally {
    referencePackageLoading = false;
    updateShell();
    if (state.caseId === "ames-reference-init-a") render();
  }
}

async function loadExplorationPackage() {
  if (explorationPackage || explorationPackageError || explorationPackageLoading) return;
  explorationPackageLoading = true;
  let stage = "release_index";
  try {
    const releaseResponse = await fetch(REFERENCE_RELEASE_INDEX);
    if (!releaseResponse.ok) throw new Error(`Release index request failed (${releaseResponse.status}).`);
    const releaseIndex = await releaseResponse.json();
    const releaseCase = releaseIndex.cases?.find((entry) => entry.case_id === EXPLORATION_CASE_ID);
    const packageRef = releaseCase?.package_ref;
    if (!safePackageRef(packageRef) || !packageRef.endsWith(`/cases/${EXPLORATION_CASE_ID}/package.json`)) throw new Error("Release index has no safe Model Exploration package reference.");
    const parts = packageRef.split("/");
    if (parts.length !== 5 || parts[0] !== "releases" || parts[2] !== "cases" || parts[3] !== EXPLORATION_CASE_ID || parts[4] !== "package.json" || !/^[a-z0-9][a-z0-9._-]{2,79}$/.test(parts[1])) throw new Error("Model Exploration package path does not match an immutable release layout.");
    const root = `${WEB_BASE}/data/${parts.slice(0, -1).join("/")}`;
    stage = "package_manifest";
    const packageResponse = await fetch(`${WEB_BASE}/data/${packageRef}`);
    if (!packageResponse.ok) throw new Error(`Model Exploration package request failed (${packageResponse.status}).`);
    const packageBytes = await packageResponse.arrayBuffer();
    const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", packageBytes))].map((v) => v.toString(16).padStart(2,"0")).join("");
    if (digest !== releaseCase.package_sha256 || packageBytes.byteLength !== releaseCase.package_bytes) throw new Error("Model Exploration release pointer digest/size mismatch.");
    const manifest = JSON.parse(new TextDecoder().decode(packageBytes));
    if (manifest.case_id !== EXPLORATION_CASE_ID || manifest.package_revision !== parts[1] || manifest.package_status !== releaseCase.package_status || !Array.isArray(manifest.files)) throw new Error("Model Exploration package identity/revision mismatch.");
    const listed = new Map(manifest.files.map((entry) => [entry.path, entry]));
    if (listed.size !== manifest.files.length) throw new Error("Duplicate Model Exploration manifest entry.");
    const pkg = { manifest, root, artifacts: new Map(), caseDoc: null, docs: {} };
    async function boundBytes(ref) {
      if (!safePackageRef(ref)) throw new Error("Unsafe Model Exploration package reference.");
      const entry = listed.get(ref);
      if (!entry) throw new Error(`Model Exploration file is not manifest-bound: ${ref}`);
      const response = await fetch(`${root}/${encodeURI(ref)}`);
      if (!response.ok) throw new Error(`Model Exploration asset request failed (${response.status}).`);
      const bytes = await response.arrayBuffer();
      const actual = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map((v) => v.toString(16).padStart(2,"0")).join("");
      if (actual !== entry.sha256 || bytes.byteLength !== entry.bytes) throw new Error(`Model Exploration manifest digest/size mismatch: ${ref}`);
      return bytes;
    }
    async function boundJson(ref) {
      if (pkg.artifacts.has(ref)) return pkg.artifacts.get(ref);
      const bytes = await boundBytes(ref);
      const value = JSON.parse(new TextDecoder().decode(bytes));
      pkg.artifacts.set(ref, value);
      return value;
    }
    stage = "phase_documents";
    for (let phase = 1; phase <= 6; phase += 1) {
      const ref = manifest.phases?.[`phase${phase}`]?.data_ref;
      const bytes = await boundBytes(ref);
      pkg.docs[phase] = JSON.parse(new TextDecoder().decode(bytes));
      if (pkg.docs[phase].case_id !== manifest.case_id) throw new Error(`Model Exploration Phase ${phase} Case ID mismatch.`);
    }
    const caseBytes = await boundBytes(manifest.case_ref);
    pkg.caseDoc = JSON.parse(new TextDecoder().decode(caseBytes));
    if (pkg.caseDoc.case_id !== manifest.case_id || pkg.caseDoc.case_status !== manifest.package_status) throw new Error("Model Exploration case document identity/status mismatch.");
    stage = "execution_manifest";
    pkg.executionManifest = await boundJson("assets/execution-manifest.json");
    if (pkg.executionManifest.case_id !== manifest.case_id) throw new Error("Execution manifest Case ID mismatch.");
    stage = "phase3_lineage";
    pkg.phase3Lineage = validatePhase3Lineage(pkg, pkg.docs[3], await boundJson(pkg.docs[3].lineage_ref));
    stage = "figures";
    for (const entry of manifest.files.filter((item) => ["image/svg+xml", "image/png"].includes(item.mime))) await boundBytes(entry.path);
    stage = "phase4_charts";
    const phase4 = pkg.docs[4];
    for (const chart of phase4.charts || []) {
      const chartDoc = await boundJson(chart.points_ref);
      if (chartDoc.case_id !== manifest.case_id || chartDoc.run_id !== phase4.execution_runs?.[0]?.execution_run_id) throw new Error("Model Exploration chart identity mismatch.");
    }
    stage = "phase5_metrics";
    const phase5 = pkg.docs[5];
    for (const ref of ["phases/phase-05/fold-metrics.json", "phases/phase-05/pooled-oof-metrics.json"]) {
      const metricsDoc = await boundJson(ref);
      if (metricsDoc.case_id !== manifest.case_id) throw new Error("Model Exploration Phase 5 metrics identity mismatch.");
    }
    stage = "default_configuration_artifacts";
    const defaultConfig = phase4.configurations.find((item) => item.configuration_id === phase4.default_configuration_id) || phase4.configurations.find((item) => item.status === "VERIFIED");
    if (defaultConfig) {
      const [cvMetrics, selectedFeatures] = await Promise.all([boundJson(defaultConfig.cv_metrics_ref), boundJson(defaultConfig.selected_features_ref)]);
      if (cvMetrics.configuration_id !== defaultConfig.configuration_id || selectedFeatures.configuration_id !== defaultConfig.configuration_id || cvMetrics.run_id !== defaultConfig.execution_run_id || selectedFeatures.run_id !== defaultConfig.execution_run_id) throw new Error("Default Phase 4 configuration artifacts are not identity-bound.");
      state.explorationConfigurationId = defaultConfig.configuration_id;
      state.explorationMethodId = defaultConfig.method_id;
    }
    explorationPackage = pkg;
    CASES[EXPLORATION_CASE_ID] = { id: EXPLORATION_CASE_ID, title: pkg.caseDoc.title, status: manifest.package_status, packageMode: "exploration", packageRevision: manifest.package_revision };
  } catch (error) {
    explorationPackageError = error instanceof Error ? error.message : "Unable to verify Model Exploration Case Package.";
    logPackageLoadFailure(EXPLORATION_CASE_ID, stage, error);
  } finally {
    explorationPackageLoading = false;
    updateShell();
    if (state.caseId === EXPLORATION_CASE_ID) render();
  }
}

async function loadCarPackage() {
  if (carPackage || carPackageError || carPackageLoading) return;
  carPackageLoading = true;
  let stage = "release_index";
  try {
    const releaseResponse = await fetch(REFERENCE_RELEASE_INDEX);
    if (!releaseResponse.ok) throw new Error(`Release index request failed (${releaseResponse.status}).`);
    const releaseIndex = await releaseResponse.json();
    if (releaseIndex.schema_version !== "1.0.0" || !Array.isArray(releaseIndex.cases)) throw new Error("Invalid Case Package release index.");
    const releaseCase = releaseIndex.cases.find((entry) => entry.case_id === CAR_CASE_ID);
    if (!releaseCase) return;
    const packageRef = releaseCase?.package_ref;
    const parts = typeof packageRef === "string" ? packageRef.split("/") : [];
    if (!safePackageRef(packageRef) || parts.length !== 5 || parts[0] !== "releases" || parts[2] !== "cases"
        || parts[3] !== CAR_CASE_ID || parts[4] !== "package.json" || !/^[a-z0-9][a-z0-9._-]{2,79}$/.test(parts[1])) {
      throw new Error("Release index has no safe CAR Case Package reference.");
    }
    const root = `${WEB_BASE}/data/${parts.slice(0, -1).join("/")}`;
    stage = "package_manifest";
    const manifestResponse = await fetch(`${WEB_BASE}/data/${packageRef}`);
    if (!manifestResponse.ok) throw new Error(`CAR Case Package request failed (${manifestResponse.status}).`);
    const manifestBytes = await manifestResponse.arrayBuffer();
    const manifestDigest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", manifestBytes))].map((v) => v.toString(16).padStart(2, "0")).join("");
    if (manifestDigest !== releaseCase.package_sha256 || manifestBytes.byteLength !== releaseCase.package_bytes) throw new Error("CAR release pointer digest/size mismatch.");
    const manifest = JSON.parse(new TextDecoder().decode(manifestBytes));
    if (manifest.case_id !== CAR_CASE_ID || manifest.package_revision !== parts[1]
        || manifest.package_status !== releaseCase.package_status || !Array.isArray(manifest.files)) throw new Error("CAR package identity or revision mismatch.");
    const listed = new Map(manifest.files.map((entry) => [entry.path, entry]));
    if (listed.size !== manifest.files.length || manifest.files.some((entry) => !safePackageRef(entry.path) || !/^[0-9a-f]{64}$/.test(entry.sha256) || !Number.isInteger(entry.bytes))) {
      throw new Error("CAR package manifest has duplicate or invalid file entries.");
    }
    const pkg = { manifest, root, artifacts: new Map(), docs: {}, caseDoc: null };
    async function boundBytes(ref) {
      if (!safePackageRef(ref)) throw new Error("Unsafe CAR package reference.");
      const entry = listed.get(ref);
      if (!entry) throw new Error(`CAR file is not manifest-listed: ${ref}`);
      const response = await fetch(`${root}/${encodeURI(ref)}`);
      if (!response.ok) throw new Error(`CAR asset request failed (${response.status}): ${ref}`);
      const bytes = await response.arrayBuffer();
      const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map((v) => v.toString(16).padStart(2, "0")).join("");
      if (digest !== entry.sha256 || bytes.byteLength !== entry.bytes) throw new Error(`CAR manifest digest/size mismatch: ${ref}`);
      return bytes;
    }
    async function boundJson(ref) {
      if (pkg.artifacts.has(ref)) return pkg.artifacts.get(ref);
      const value = JSON.parse(new TextDecoder().decode(await boundBytes(ref)));
      if (value.case_id !== CAR_CASE_ID) throw new Error(`CAR artifact Case ID mismatch: ${ref}`);
      pkg.artifacts.set(ref, value);
      return value;
    }
    stage = "phase_documents";
    for (let phase = 1; phase <= 6; phase += 1) {
      const ref = manifest.phases?.[`phase${phase}`]?.data_ref;
      const document = await boundJson(ref);
      pkg.docs[phase] = document;
    }
    pkg.caseDoc = await boundJson(manifest.case_ref);
    if (pkg.caseDoc.case_status !== manifest.package_status) throw new Error("CAR case document status mismatch.");
    stage = "execution_manifest";
    pkg.executionManifest = await boundJson("assets/execution-manifest.json");
    stage = "phase3_lineage";
    pkg.phase3Lineage = await boundJson(pkg.docs[3].lineage_ref);
    const lineage = pkg.phase3Lineage;
    const encodedCount = pkg.docs[3].stages.find((item) => item.id === "encoded")?.total;
    if (lineage.source_data_sha256 !== (pkg.executionManifest.source_sha256 || pkg.executionManifest.source_data_sha256)
        || lineage.config_sha256 !== pkg.executionManifest.config_sha256 || lineage.fit_population !== "development_train_only"
        || !Array.isArray(lineage.encoded_features) || lineage.encoded_features.length !== encodedCount
        || !/^[0-9a-f]{64}$/.test(lineage.feature_names_sha256 || "")) throw new Error("CAR Phase 3 lineage is not bound to its source, config, or encoded feature count.");
    stage = "phase4_artifacts";
    const charts = pkg.docs[4].charts || [];
    for (const chart of charts) await boundJson(chart.points_ref);
    const config = pkg.docs[4].configurations.find((item) => item.configuration_id === pkg.docs[4].default_configuration_id);
    if (!config) throw new Error("CAR default Phase 4 configuration is missing.");
    const [metrics, features] = await Promise.all([boundJson(config.cv_metrics_ref), boundJson(config.selected_features_ref)]);
    if (metrics.configuration_id !== config.configuration_id || metrics.run_id !== config.execution_run_id
        || features.configuration_id !== config.configuration_id) throw new Error("CAR default configuration artifact identity mismatch.");
    stage = "package_bundle";
    const assets = manifest.files.filter((item) => item.path !== "package.json");
    for (let start = 0; start < assets.length; start += 6) {
      await Promise.all(assets.slice(start, start + 6).map((entry) => boundBytes(entry.path)));
    }
    carPackage = pkg;
    CASES[CAR_CASE_ID] = {
      id: CAR_CASE_ID, title: pkg.caseDoc.title, status: manifest.package_status,
      packageMode: "car", packageRevision: manifest.package_revision, analyses: []
    };
    state.explorationConfigurationId = config.configuration_id;
    state.explorationMethodId = config.method_id;
  } catch (error) {
    carPackageError = error instanceof Error ? error.message : "Unable to verify CAR Case Package.";
    logPackageLoadFailure(CAR_CASE_ID, stage, error);
  } finally {
    carPackageLoading = false;
    updateShell();
    if (state.caseId === CAR_CASE_ID) render();
  }
}

async function loadExplorationArtifact(pkg, ref) {
  if (pkg.artifacts.has(ref)) return pkg.artifacts.get(ref);
  if (!safePackageRef(ref) || !pkg.manifest.files.some((entry) => entry.path === ref)) throw new Error("Requested artifact is not package-bound.");
  if (!explorationArtifactPromises.has(ref)) explorationArtifactPromises.set(ref, (async () => {
    const response = await fetch(`${pkg.root}/${encodeURI(ref)}`);
    if (!response.ok) throw new Error(`Artifact request failed (${response.status}).`);
    const bytes = await response.arrayBuffer();
    const entry = pkg.manifest.files.find((item) => item.path === ref);
    const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map((v) => v.toString(16).padStart(2,"0")).join("");
    if (digest !== entry.sha256 || bytes.byteLength !== entry.bytes) throw new Error("Artifact manifest digest/size mismatch.");
    const value = JSON.parse(new TextDecoder().decode(bytes));
    if (value.case_id !== pkg.manifest.case_id) throw new Error("Artifact Case ID mismatch.");
    pkg.artifacts.set(ref, value);
    return value;
  })());
  try { return await explorationArtifactPromises.get(ref); }
  finally { explorationArtifactPromises.delete(ref); }
}
async function loadExplorationConfigurationArtifacts(pkg, configuration) {
  const [cvMetrics, selectedFeatures] = await Promise.all([
    loadExplorationArtifact(pkg, configuration.cv_metrics_ref),
    loadExplorationArtifact(pkg, configuration.selected_features_ref)
  ]);
  for (const artifact of [cvMetrics, selectedFeatures]) {
    if (artifact.configuration_id !== configuration.configuration_id || artifact.run_id !== configuration.execution_run_id) throw new Error("Phase 4 artifact Configuration/Run identity mismatch.");
  }
  return { cvMetrics, selectedFeatures };
}
function renderReferencePackagePhase(phase) {
  const pkg = referencePackage;
  const c = caseData();
  const doc = pkg?.docs[phase];
  if (!pkg || !doc) return `<div class="page">${pageHeading(`PHASE 0${phase} / REFERENCE PACKAGE`, "INIT B Reference Baseline", "Package 載入與驗證狀態。", referencePackageError ? "ERROR" : "UNAVAILABLE")}<section class="state-panel" role="${referencePackageError ? "alert" : "status"}"><h3>${referencePackageError ? "Case Package 驗證失敗" : "載入 Reference Baseline Case Package"}</h3><p>${esc(referencePackageError || "網站正從目前發布版本載入套件。")}</p></section></div>`;
  const unavailable = doc.status === "UNAVAILABLE";
  let body = "";
  if (phase === 1 || unavailable) body = renderReferencePhase1(pkg, doc);
  else if (phase === 2) body = renderReferencePhase2(pkg, doc);
  else if (phase === 3) body = renderReferencePhase3(pkg, doc);
  else if (phase === 4) body = renderReferencePhase4(pkg, doc);
  else if (phase === 5) body = renderReferencePhase5(pkg, doc);
  else if (phase === 6) body = renderReferencePhase6(pkg, doc);
  const phaseStatus = phase === 5 && doc.evaluations?.some((item) => Object.values(item.metrics || {}).length > 0 && Object.values(item.metrics || {}).every((metric) => metric.status === "VERIFIED")) ? "VERIFIED" : doc.status;
  const prev = phase > 1 ? [phase - 1, PHASES[phase - 2][2]] : null;
  const next = phase < 6 ? [phase + 1, PHASES[phase][2]] : null;
  return `<div class="page reference-page" data-reference-phase="${phase}"><div class="fixture-banner"><span><strong>INIT B · Reference Baseline</strong> · ${esc(pkg.manifest.package_revision)} · 本頁數據來自已驗證的公開 Case Package。</span>${badge(phaseStatus)}</div>${pageHeading(`PHASE 0${phase} / ${PHASES[phase-1][1].toUpperCase()}`, PHASES[phase-1][2], referencePhaseSubtitle(phase), phaseStatus)}${body}<p class="stage-note package-verification-note">本頁資料與圖表均通過 Package SHA／bytes 驗證。Package status: ${esc(pkg.manifest.package_status)}.</p>${referenceFooterNav(prev,next)}</div>`;
}

function referencePhaseSubtitle(phase) {
  return ({
    1: "研究案例與資料來源；未提供的業務證據保持明確未提供。",
    2: "探索原始資料的欄位、缺失與分布。選擇分析查看摘要與圖表。",
    3: "追蹤從原始候選欄位、訓練集前處理到編碼特徵的轉換。",
    4: "固定 Reference Baseline 的三折交叉驗證結果；其他模型沒有在此執行。",
    5: "以 Phase 4 Development OOF 計算的評估；這不是獨立 Holdout 測試。",
    6: "本機模型與推論 Smoke 已驗證；網站未提供遠端預測服務。"
  })[phase];
}
function referenceFooterNav(prev, next) {
  return `<nav class="phase-footer" aria-label="前後階段">${prev ? `<a class="button" href="#phase-${prev[0]}">← ${esc(prev[1])}</a>` : "<span></span>"}${next ? `<a class="button primary" href="#phase-${next[0]}">${esc(next[1])} →</a>` : "<span></span>"}</nav>`;
}

function parseFieldDecisions(text) {
  if (typeof text !== "string") return [];
  return [...text.matchAll(/([^;]+?)\s+\[([^\]]+)\]\s+(include|exclude)/g)].map((m) => ({ field: m[1].trim(), type: m[2], action: m[3] }));
}
function parseMissingness(text) {
  const match = typeof text === "string" && text.match(/^Rows=(\d+); missing cells by field: (.+)$/);
  if (!match) return null;
  const fields = [...match[2].matchAll(/([^;=]+)=(\d+)\/(\d+)/g)].map((m) => ({ field: m[1].trim(), missing: Number(m[2]), rows: Number(m[3]) }));
  if (!fields.length || fields.some((item) => item.rows !== Number(match[1]))) return null;
  return { rows: Number(match[1]), fields };
}
function parseFeatureSummary(text) {
  if (typeof text !== "string") return null;
  const numeric = [...text.matchAll(/([^;]+): n=(\d+), min=([^,;]+), median=([^,;]+), max=([^;]+)/g)]
    .map((m) => ({ field: m[1].trim(), n: Number(m[2]), min: m[3].trim(), median: m[4].trim(), max: m[5].trim() }));
  const nominal = [...text.matchAll(/([^;:]+): (\d+) distinct/g)].map((m) => ({ field: m[1].trim(), distinct: Number(m[2]) }));
  return numeric.length || nominal.length ? { numeric, nominal } : null;
}
function referenceAnalysis(pkg) {
  const doc = pkg.docs[2];
  return doc.analyses.find((a) => a.figure_id === state.referenceAnalysisId || a.id === state.referenceAnalysisId)
    || doc.analyses.find((a) => a.figure_id === doc.default_analysis_id) || doc.analyses[0];
}
function packageFigure(pkg, ref, alt, className = "package-figure") {
  const entry = pkg.manifest.files.find((item) => item.path === ref);
  if (!safePackageRef(ref) || !entry || !["image/svg+xml", "image/png"].includes(entry.mime)) return "";
  const dimensions = ref.endsWith("missingness.svg") ? [760, 575]
    : ref.endsWith("target-distribution.svg") ? [760, 360]
      : entry.mime === "image/png" ? [910, 650] : [760, 575];
  return `<figure class="reference-figure"><img class="${className}" src="${pkg.root || REFERENCE_PACKAGE_ROOT}/${encodeURI(ref)}" alt="${esc(alt)}" width="${dimensions[0]}" height="${dimensions[1]}" loading="lazy" decoding="async"><figcaption>${esc(alt)}</figcaption></figure>`;
}
function renderReferencePhase1(pkg, doc) {
  const c = pkg.caseDoc;
  const source = c.source || {};
  const sections = Array.isArray(doc.sections) ? doc.sections : [];
  return `<section class="reference-summary-grid grid three"><article class="reference-stat-card"><span class="eyebrow">研究案例 CASE</span><strong>${esc(c.title)}</strong><small>Case ID · ${esc(c.case_id)}</small></article><article class="reference-stat-card"><span class="eyebrow">資料來源 SOURCE</span><strong>${esc(source.label || "未提供來源說明")}</strong><small>${esc(source.accession || "來源識別資訊未提供")}</small></article><article class="reference-stat-card"><span class="eyebrow">預測目標 TARGET</span><strong>${esc(c.target?.raw_field_id || "—")}</strong><small>${esc(c.target?.unit || "單位未提供")}</small></article></section><section class="card reference-note-card"><div class="card-head"><div><p class="eyebrow">BUSINESS UNDERSTANDING</p><h2>業務證據尚未提供</h2></div>${badge(doc.status)}</div><div class="card-body"><p>此 Package 沒有已核准的研究問題、商業目標或授權敘述。此頁只呈現 Case 文件中可追溯的來源與目標資訊。</p>${sections.length ? `<details class="disclosure"><summary>查看 Package 提供的說明</summary><div class="disclosure-body">${sections.map((item) => `<p><strong>${esc(item.title || "")}</strong><br>${esc(item.body || "")}</p>`).join("")}</div></details>` : ""}</div></section>`;
}
function renderReferencePhase2(pkg, doc) {
  const analyses = Array.isArray(doc.analyses) ? doc.analyses : [];
  const selected = referenceAnalysis(pkg);
  if (!selected) return `<section class="state-panel"><h2>沒有可用的 Phase 2 分析</h2>${badge("UNAVAILABLE")}</section>`;
  const buttons = analyses.map((item) => `<button type="button" class="selector-button" data-reference-analysis="${esc(item.figure_id)}" aria-pressed="${item.figure_id === selected.figure_id}">${esc(item.title)}</button>`).join("");
  let content = `<p class="body-copy">${esc(selected.description || "")}</p>`;
  if (selected.figure_id === "figure-field-decisions") {
    const fields = parseFieldDecisions(selected.finding);
    const rowSource = analyses.find((item) => item.figure_id === "figure-missingness");
    const sourceRows = parseMissingness(rowSource?.finding)?.rows;
    const includedFields = fields.filter((item) => item.action === "include");
    const classificationTypes = ["nominal", "ordinal", "discrete", "continuous"];
    const counts = new Map(classificationTypes.map((type) => [type, 0]));
    for (const field of includedFields) {
      if (counts.has(field.type)) counts.set(field.type, counts.get(field.type) + 1);
    }
    const classificationTotal = classificationTypes.reduce((sum, type) => sum + counts.get(type), 0);
    const classificationsComplete = classificationTotal === includedFields.length;
    const classificationLegend = classificationTypes.map((type) => {
      const count = counts.get(type);
      const percentage = classificationTotal ? count / classificationTotal * 100 : 0;
      return `<span class="reference-classification-item" data-classification-type="${type}" data-count="${count}" data-percent="${percentage.toFixed(1)}"><i class="reference-classification-swatch ${type}" aria-hidden="true"></i><span>${typeLabel(type)}</span><strong>${count.toLocaleString()}</strong><small>${percentage.toFixed(1)}%</small></span>`;
    }).join("");
    const classificationBar = classificationsComplete && classificationTotal ? `<div class="reference-classification-bar" role="img" aria-label="四種欄位分類共 ${classificationTotal} 個特徵；下方圖例列出各類數量與百分比">${classificationTypes.map((type) => {
      const count = counts.get(type);
      return `<span class="reference-classification-segment ${type}" data-classification-type="${type}" data-count="${count}" style="flex-grow:${count}" title="${typeLabel(type)} ${count.toLocaleString()}（${(count / classificationTotal * 100).toFixed(1)}%）"></span>`;
    }).join("")}</div><div class="reference-classification-legend" aria-label="欄位分類圖例">${classificationLegend}</div>` : `<p class="state-panel">欄位分類總數不完整，未繪製比例圖。</p>`;
    content += fields.length ? `<div class="reference-summary-grid grid four">${[["資料列", sourceRows?.toLocaleString() || "—"],["原始欄位", String(fields.length)],["納入預測欄位", String(includedFields.length)],["排除欄位", String(fields.filter((item) => item.action === "exclude").length)]].map(([label,value]) => `<article class="reference-stat-card"><span>${label}</span><strong>${value}</strong></article>`).join("")}</div><section class="reference-classification"><div class="reference-classification-heading"><h3>欄位分類</h3><span>${classificationTotal.toLocaleString()} 個納入特徵</span></div>${classificationBar}</section><details class="disclosure"><summary>檢視欄位分類與決策 (${fields.length})</summary><div class="table-scroll"><table class="mock-data-table"><thead><tr><th>欄位</th><th>分類</th><th>決策</th></tr></thead><tbody>${fields.map((item) => `<tr><td>${esc(item.field)}</td><td>${esc(typeLabel(item.type))}</td><td>${item.action === "include" ? "納入" : "排除"}</td></tr>`).join("")}</tbody></table></div></details>` : `<p class="state-panel">欄位摘要格式不符合可驗證規則，未解析顯示。</p>`;
  } else if (selected.figure_id === "figure-missingness") {
    const missing = parseMissingness(selected.finding);
    const sorted = missing?.fields.filter((item) => item.missing).sort((a,b) => b.missing-a.missing || a.field.localeCompare(b.field)) || [];
    const total = missing?.fields.reduce((sum,item) => sum + item.missing, 0) || 0;
    content += missing ? `<div class="reference-summary-grid grid three"><article class="reference-stat-card"><span>資料列 ROWS</span><strong>${missing.rows.toLocaleString()}</strong></article><article class="reference-stat-card"><span>缺失儲存格 MISSING</span><strong>${total.toLocaleString()}</strong></article><article class="reference-stat-card"><span>有缺失欄位 FIELDS</span><strong>${sorted.length}</strong></article></div><div class="reference-missing-bars">${sorted.slice(0, 8).map((item) => `<div class="reference-bar-row"><span>${esc(item.field)}</span><span class="reference-bar-track"><i style="width:${Math.min(100, item.missing / missing.rows * 100)}%"></i></span><strong>${item.missing.toLocaleString()} <small>(${(item.missing / missing.rows * 100).toFixed(1)}%)</small></strong></div>`).join("")}</div>${packageFigure(pkg, selected.image_ref, "正式資料缺失值欄位分布") }<details class="disclosure"><summary>檢視完整缺失統計 (${missing.fields.length} 欄)</summary><div class="table-scroll"><table class="mock-data-table"><thead><tr><th>欄位</th><th>缺失筆數</th><th>比例</th></tr></thead><tbody>${sorted.concat(missing.fields.filter((item) => !item.missing)).map((item) => `<tr><td>${esc(item.field)}</td><td>${item.missing}</td><td>${(item.missing / missing.rows * 100).toFixed(2)}%</td></tr>`).join("")}</tbody></table></div></details>` : `<p class="state-panel">缺失摘要格式不符合可驗證規則，未解析顯示。</p>`;
  } else if (selected.figure_id === "figure-target-distribution") {
    content += packageFigure(pkg, selected.image_ref, `正式訓練資料 ${pkg.caseDoc.target?.raw_field_id || "target"} 分布圖`) || `<p class="state-panel">此分析沒有可用圖表檔案。</p>`;
    content += `<p class="stage-note">${esc(selected.finding || "")} 圖表呈現分箱分布；Package 未提供逐箱表格，因此不額外重建或推測箱內數值。</p>`;
  } else if (selected.figure_id === "figure-feature-summary") {
    const summary = parseFeatureSummary(selected.finding);
    content += summary ? `<div class="reference-summary-grid grid two"><article class="reference-stat-card"><span>數值欄位摘要</span><strong>${summary.numeric.length}</strong><small>n、最小值、中位數、最大值</small></article><article class="reference-stat-card"><span>名目欄位基數</span><strong>${summary.nominal.length}</strong><small>不同類別數</small></article></div><details class="disclosure" open><summary>數值欄位摘要</summary><div class="table-scroll"><table class="mock-data-table"><thead><tr><th>欄位</th><th>有效筆數</th><th>最小值</th><th>中位數</th><th>最大值</th></tr></thead><tbody>${summary.numeric.map((item) => `<tr><td>${esc(item.field)}</td><td>${item.n.toLocaleString()}</td><td>${esc(item.min)}</td><td>${esc(item.median)}</td><td>${esc(item.max)}</td></tr>`).join("")}</tbody></table></div></details><details class="disclosure"><summary>名目欄位不同類別數 (${summary.nominal.length})</summary><div class="table-scroll"><table class="mock-data-table"><thead><tr><th>欄位</th><th>不同類別數</th></tr></thead><tbody>${summary.nominal.map((item) => `<tr><td>${esc(item.field)}</td><td>${item.distinct}</td></tr>`).join("")}</tbody></table></div></details>` : `<p class="state-panel">沒有可解析的聚合摘要。</p>`;
  } else content += `<p>${esc(selected.finding || "")}</p>`;
  return `<section class="card"><div class="card-head"><div><p class="eyebrow">DATA EXPLORATION</p><h2>選擇分析項目</h2></div>${badge(selected.status)}</div><div class="card-body"><div class="selector-row reference-analysis-selector" role="group" aria-label="Phase 2 analysis">${buttons}</div><p class="sr-only" aria-live="polite">${esc(selected.title)} selected.</p><section class="reference-analysis-panel"><div class="reference-analysis-heading"><div><p class="eyebrow">${esc(selected.figure_id)}</p><h2>${esc(selected.title)}</h2></div>${badge(selected.status)}</div>${content}<details class="disclosure"><summary>研究說明與限制</summary><div class="disclosure-body"><p>${esc(selected.limitations || "Package 未提供額外限制說明。")}</p><p>Phase 2 使用原始資料，尚未套用 Phase 3 補值或編碼。</p></div></details></section></div></section>`;
}
function typeLabel(type) { return ({ nominal: "名目", ordinal: "次序", discrete: "離散", continuous: "連續" })[type] || type; }
function renderReferencePhase3(pkg, doc) {
  const stages = Array.isArray(doc.stages) ? doc.stages : [];
  const fieldDecisionAnalysis = pkg.docs?.[2]?.analyses?.find((item) => item.figure_id === "figure-field-decisions");
  const sourceFields = parseFieldDecisions(fieldDecisionAnalysis?.finding);
  const sourcePredictors = sourceFields.filter((item) => item.action === "include").length;
  const sourceColumnCount = sourceFields.length;
  const stageCards = stages.map((stage,index) => {
    const sourceSegments = stage.segments || [];
    const total = Number(stage.total);
    const segmentTotal = sourceSegments.reduce((sum,item) => sum + Number(item.count || 0), 0);
    const track = stage.distribution_status === "VERIFIED" && segmentTotal === total
      ? renderSegments(stage, doc.feature_types || [])
      : `<div class="stack-track is-unknown" role="img" aria-label="欄位分類未驗證">欄位分類資料不可用 UNAVAILABLE</div>`;
    const notes = {
      raw: sourceColumnCount && sourcePredictors === total
        ? `${sourceColumnCount} 個 CSV 欄位中，${sourcePredictors} 個是模型預測特徵；欄位分類採 Phase 2 的語意分類。`
        : "欄位分類依 Phase 2 的欄位決策資料。",
      filtered: "篩選後仍保留相同的 79 個預測欄位，因此分類比例與 Step 01 相同。",
      processed: "79 個原始預測欄位加上 9 個衍生指示特徵，共 88 個；補值與指示特徵只使用 Development 訓練資料擬合。",
      encoded: "248 個特徵分類依逐欄來源沿革計算；one-hot 特徵沿用名目語意，衍生指示特徵列為離散。",
    };
    const title = stage.id === "filtered" ? "Predictor fields retained for preparation"
      : stage.id === "processed" ? "Train-only imputation and derived indicators" : stage.label;
    const lineageRows = stage.id === "encoded" ? (pkg.phase3Lineage?.encoded_features || []).map((item) =>
      `<tr><td>${esc(item.index + 1)}</td><td>${esc(item.encoded_feature)}</td><td>${esc(item.source_columns.join(", "))}</td><td>${esc(typeLabel(item.semantic_type))}</td><td>${esc(item.transformation)}</td></tr>`).join("") : "";
    const lineageDetails = lineageRows
      ? `<details class="disclosure reference-lineage-disclosure"><summary>檢視 248 個編碼特徵的原始欄位對照</summary><div class="table-scroll"><table class="mock-data-table"><thead><tr><th>#</th><th>編碼特徵</th><th>來源欄位</th><th>分類</th><th>轉換</th></tr></thead><tbody>${lineageRows}</tbody></table></div><p class="stage-note">Source SHA-256 ${esc(pkg.phase3Lineage.source_data_sha256)} · Config SHA-256 ${esc(pkg.phase3Lineage.config_sha256)} · 特徵名稱 SHA-256 ${esc(pkg.phase3Lineage.feature_names_sha256)} · fit: development_train_only.</p></details>` : "";
    return `<article class="stage-card"><div class="stage-head"><div class="stage-title"><span class="index" aria-label="步驟 ${index + 1} Step ${index + 1}"><span>步驟 · STEP</span><b>0${index + 1}</b></span><h2>${esc(title)}</h2></div><span class="stage-total">總數 Total: ${Number.isInteger(total) ? total.toLocaleString() : "—"} ${esc(stage.unit)} ${badge(stage.total_status)}</span></div>${track}<p class="stage-note">${esc(notes[stage.id] || "")}</p>${lineageDetails}</article>`;
  }).join("");
  const split = doc.split || {};
  const train = Number(split.training_rows) || 0, validation = Number(split.holdout_rows) || 0, total = train + validation;
  const treatments = (doc.treatments || []).map((item) => `<div class="treatment-item"><strong>${esc(item.field_group || item.variable_type || item.strategy || "處理策略")}</strong><span>${esc(item.strategy || item.method || item.description || JSON.stringify(item))}</span></div>`).join("");
  return `<section class="card"><div class="card-head"><div><p class="eyebrow">FEATURE TRANSFORMATION · FOUR STAGES</p><h2>資料如何轉成模型特徵</h2></div>${badge(doc.status)}</div><div class="card-body"><div class="stage-list">${stageCards}</div><p class="stage-note">四階段分類分別對應原始欄位、篩選後欄位、加上 9 個指示特徵的處理欄位，以及 248 個最終模型特徵。</p><section class="reference-split"><div class="reference-analysis-heading"><div><p class="eyebrow">DEVELOPMENT SPLIT</p><h2>固定訓練／驗證切分</h2></div><strong>Seed ${esc(split.seed)}</strong></div><div class="row-split"><span style="width:${total ? train / total * 100 : 0}%">Development · ${train.toLocaleString()}</span><span style="width:${total ? validation / total * 100 : 0}%">Validation · ${validation.toLocaleString()}</span></div><p class="stage-note">${Number(split.source_labeled_rows).toLocaleString()} labeled rows · 80/20 split · preprocessing fit scope: training data only. Validation rows are shown as split context and are not used for this page’s CV scores.</p></section>${treatments ? `<details class="disclosure"><summary>查看實際補值與編碼策略</summary><div class="treatment-list">${treatments}</div></details>` : ""}</div></section>`;
}
function renderReferencePhase4(pkg, doc) {
  const cfg = doc.configurations.find((item) => item.configuration_id === doc.default_configuration_id);
  const folds = pkg.cvMetrics.fold_results || [];
  const mean = pkg.cvMetrics.mean_fold_metrics || {};
  const metrics = [["RMSE",mean.rmse,"USD，越低越好"],["MAE",mean.mae,"USD，越低越好"],["R²",mean.r2,"折間平均"]];
  const cards = metrics.map(([label,value,note]) => `<article class="metric-card"><span class="metric-label">${label}</span><strong class="metric-value">${Number(value).toLocaleString("en-US",{maximumFractionDigits:label === "R²" ? 6 : 2})}</strong><span class="metric-note">${note}</span></article>`).join("");
  const foldRows = folds.map((fold) => `<tr><td>Fold ${fold.fold + 1}</td><td>${fold.validation_rows}</td><td>${Number(fold.rmse).toLocaleString("en-US",{maximumFractionDigits:2})}</td><td>${Number(fold.mae).toLocaleString("en-US",{maximumFractionDigits:2})}</td><td>${Number(fold.r2).toFixed(6)}</td></tr>`).join("");
  const foldVisual = folds.map((fold) => {
    const validationShare = Number(doc.cv.training_rows) ? fold.validation_rows / doc.cv.training_rows * 100 : 0;
    return `<div class="reference-fold"><span>Fold ${fold.fold + 1}</span><div class="cv-track"><span class="cv-train" style="width:${100 - validationShare}%">Training folds</span><span class="cv-valid" style="width:${validationShare}%">Validation</span></div><small>${fold.validation_rows} validation rows</small></div>`;
  }).join("");
  const params = cfg?.params || {};
  return `<section class="grid two reference-model-grid"><article class="card"><div class="card-head"><div><p class="eyebrow">FIXED REFERENCE MODEL</p><h2>Lasso selection → OLS</h2></div>${badge(doc.status)}</div><div class="card-body"><p class="body-copy">固定歷史設定以 Lasso α=${esc(params.alpha ?? "—")} 選擇特徵，再由 OLS 執行三折 Development CV。這裡只有一個已執行配置，不代表模型比較。</p><dl class="data-row"><dt>CV 母體</dt><dd>${Number(doc.cv.training_rows).toLocaleString()} Development rows</dd></dl><dl class="data-row"><dt>折數</dt><dd>${doc.cv.fold_count} fixed folds</dd></dl><dl class="data-row"><dt>選模搜尋</dt><dd>未執行</dd></dl></div></article><article class="card"><div class="card-head"><div><p class="eyebrow">FOLD ROTATION</p><h2>三折交叉驗證</h2></div></div><div class="card-body reference-fold-list">${foldVisual}</div></article></section><section class="card reference-metrics-card"><div class="card-head"><div><p class="eyebrow">MEAN FOLD METRICS · DEVELOPMENT CV</p><h2>模型表現摘要</h2></div>${badge(doc.status)}</div><div class="card-body"><div class="metrics">${cards}</div><div class="table-scroll"><table class="mock-data-table"><thead><tr><th>Fold</th><th>驗證筆數</th><th>RMSE</th><th>MAE</th><th>R²</th></tr></thead><tbody>${foldRows}</tbody></table></div><p class="stage-note">指標直接來自已驗證的 Phase 4 fold-metrics 檔案。這是 Development 交叉驗證，不是獨立 Holdout 泛化評估。</p><details class="disclosure"><summary>技術細節</summary><div class="disclosure-body"><p>Configuration ${esc(cfg?.configuration_id || "—")} · Run ${esc(cfg?.execution_run_id || "—")} · Protocol ${esc(cfg?.protocol_id || "—")}</p><pre class="package-json">${esc(JSON.stringify(params,null,2))}</pre></div></details></div></section>`;
}
function renderReferencePhase5(pkg, doc) {
  const configs = pkg.docs[4]?.configurations || [];
  const config = configs.find((item) => item.configuration_id === doc.evaluations?.[0]?.configuration_id);
  const selected = (doc.evaluations || []).find((item) => item.configuration_id === config?.configuration_id && item.metric_source === "cv_fold_mean");
  const pooled = (doc.evaluations || []).find((item) => item.configuration_id === config?.configuration_id && item.metric_source === "pooled_oof");
  if (!selected || !config) return `<section class="state-panel"><h2>沒有可用的 Development CV 評估</h2><p>此案例沒有與 Phase 4 預設 Configuration 綁定的 Mean-fold 評估。</p>${badge("UNAVAILABLE")}</section>`;
  const method = pkg.docs[4].methods?.find((item) => item.method_id === config.method_id);
  const figure = phase5BoundFigure(pkg, pooled, state.referenceFigureId);
  return renderPhase5EvaluationCard(pkg, doc, config, method?.label || config.method_id, selected, pooled, figure, state.referenceFigureId, "data-reference-figure");
}
function renderReferencePhase6(pkg, doc) {
  const model = doc.models?.[0];
  const smoke = pkg.phase6Smoke;
  const reload = Boolean(smoke?.reload_verified), inference = Boolean(smoke?.local_inference_verified);
  return `<section class="grid two reference-model-grid"><article class="card"><div class="card-head"><div><p class="eyebrow">LOCAL MODEL ARTIFACT</p><h2>Development 模型封裝</h2></div>${badge(model?.model_status || doc.status)}</div><div class="card-body"><dl class="data-row"><dt>來源配置</dt><dd>${esc(model?.source_configuration_id || "—")}</dd></dl><dl class="data-row"><dt>模型版本</dt><dd>${esc(model?.model_version || "—")}</dd></dl><dl class="data-row"><dt>重新載入</dt><dd>${reload ? "PASS" : "NOT VERIFIED"}</dd></dl><dl class="data-row"><dt>本機推論 Smoke</dt><dd>${inference ? "PASS · 預測值未公開" : "NOT VERIFIED"}</dd></dl></div></article><article class="card"><div class="card-head"><div><p class="eyebrow">SERVING AVAILABILITY</p><h2>網站推論能力</h2></div>${badge("UNAVAILABLE")}</div><div class="card-body"><p class="body-copy">這個公開網站目前只提供靜態研究套件，沒有即時模型 API。不能在此輸入房屋條件並取得模型預測。</p><div class="state-panel"><h3>遠端預測未部署</h3><p>本機模型重新載入與推論驗證，不等同於公開服務。</p></div><details class="disclosure"><summary>模型來源識別</summary><div class="disclosure-body"><p>Model ${esc(model?.model_id || "—")} · Run ${esc(model?.source_execution_run_id || "—")}</p></div></details></div></article></section>`;
}
function explorationArtifact(pkg, ref) { return pkg.artifacts.get(ref) || null; }
function activeExplorationPackage() { return caseData().packageMode === "car" ? carPackage : explorationPackage; }
function explorationSelectedConfig(pkg) {
  const doc = pkg.docs[4];
  const methodId = state.explorationMethodId
    || doc.configurations.find((item) => item.configuration_id === doc.default_configuration_id)?.method_id;
  const methodConfigs = doc.configurations.filter((item) => item.method_id === methodId);
  return methodConfigs.find((item) => item.configuration_id === state.explorationConfigurationId)
    || methodConfigs.find((item) => item.configuration_id === doc.default_configuration_id)
    || methodConfigs.find((item) => item.status === "VERIFIED")
    || methodConfigs[0] || null;
}
function explorationDefaultConfigForMethod(pkg, methodId) {
  const doc = pkg.docs[4];
  const methodChart = (doc.charts || []).find((item) => item.chart_id === "method-comparison");
  const points = explorationArtifact(pkg, methodChart?.points_ref)?.points || [];
  const candidates = points.filter((item) => item.method_id === methodId && item.status === "VERIFIED");
  const winner = candidates.find((item) => item.method_winner) || candidates[0];
  return doc.configurations.find((item) => item.configuration_id === winner?.configuration_id && item.method_id === methodId)
    || doc.configurations.find((item) => item.method_id === methodId && item.status === "VERIFIED")
    || doc.configurations.find((item) => item.method_id === methodId) || null;
}
function explorationMethodLabel(doc, methodId) { return doc.methods.find((item) => item.method_id === methodId)?.label || methodId; }
function explorationMetric(value, key) {
  return Number(value).toLocaleString("en-US", { maximumFractionDigits: key === "r2" ? 6 : 2 });
}
function explorationMetricsCards(metrics) {
  return [["RMSE", "rmse", "USD · 越低越好"], ["MAE", "mae", "USD · 越低越好"], ["R²", "r2", "Development folds"]].map(([label,key,note]) =>
    `<article class="metric-card"><span class="metric-label">${label}</span><strong class="metric-value">${metrics?.[key] == null ? "—" : explorationMetric(metrics[key], key)}</strong><span class="metric-note">${note}</span></article>`).join("");
}
const PHASE5_FIGURES = [
  ["FIG-P5-01", "Actual vs Predicted", "實際值與預測值"],
  ["FIG-P5-02", "Residual vs Predicted", "殘差與預測值"],
  ["FIG-P5-03", "Residual Distribution", "殘差分布"]
];
function phase5BoundFigure(pkg, pooled, figureId) {
  if (!pooled) return null;
  const figure = pooled.figures?.find((item) => item.figure_id === figureId);
  if (!figure) return null;
  const entry = pkg.manifest.files.find((item) => item.path === figure.asset_ref);
  const identityMatches = figure.evaluation_id === pooled.evaluation_id
    && figure.configuration_id === pooled.configuration_id
    && figure.evaluation_population === pooled.evaluation_population
    && figure.prediction_origin === pooled.prediction_origin
    && figure.n === pooled.n
    && figure.source_digest === pooled.evidence?.source_artifact_sha256;
  const assetMatches = safePackageRef(figure.asset_ref) && entry
    && entry.sha256 === figure.sha256 && entry.mime === "image/png";
  return identityMatches && assetMatches ? figure : null;
}
function phase5MetricValue(evaluation, key) {
  const metric = evaluation?.metrics?.[key];
  return metric?.status === "VERIFIED" && Number.isFinite(metric.value) ? metric.value : null;
}
function phase5FormatMetric(value, key) {
  return value == null ? "—" : key === "r2"
    ? Number(value).toFixed(6)
    : Number(value).toLocaleString("en-US", { maximumFractionDigits: 2 });
}
function phase5ComputationStatus(evaluation, fallback) {
  const metrics = ["mae", "rmse", "r2"].map((key) => evaluation?.metrics?.[key]);
  return metrics.every((metric) => metric?.status === "VERIFIED" && Number.isFinite(metric.value))
    ? "VERIFIED" : fallback || "UNAVAILABLE";
}
function phase5ConfigurationDescription(config) {
  const params = config?.params || {};
  const useful = Object.entries(params).filter(([key]) => !["seed", "selection", "selection_search", "max_iter", "tol"].includes(key));
  if (!useful.length) return "固定 Reference Configuration";
  return useful.map(([key, value]) => `${key} ${String(value)}`).join(" · ");
}
function renderPhase5EvaluationCard(pkg, doc, config, methodLabel, meanEval, pooledEval, figure, selectedFigureId, figureAttribute) {
  const computationStatus = phase5ComputationStatus(meanEval, doc.status);
  const metrics = [
    ["MAE", "mae", "平均絕對誤差 · USD"],
    ["RMSE", "rmse", "均方根誤差 · USD"],
    ["R²", "r2", "決定係數"]
  ].map(([label, key, note]) => `<article class="metric-card"><span class="metric-label">${label}</span><strong class="metric-value">${phase5FormatMetric(phase5MetricValue(meanEval, key), key)}</strong><span class="metric-note">${note}</span></article>`).join("");
  const diagnosticButtons = PHASE5_FIGURES.map(([id, en, zh]) => `<button type="button" class="selector-button" ${figureAttribute}="${id}" aria-pressed="${id === selectedFigureId}">${en}<span>${zh}</span></button>`).join("");
  const advancedMetricRows = ["mae", "rmse", "r2"].map((key) => {
    const mean = phase5MetricValue(meanEval, key), pooled = phase5MetricValue(pooledEval, key);
    const delta = mean == null || pooled == null ? null : pooled - mean;
    return `<tr><th>${key.toUpperCase()}</th><td>${phase5FormatMetric(mean, key)}</td><td>${phase5FormatMetric(pooled, key)}</td><td>${phase5FormatMetric(delta, key)}</td></tr>`;
  }).join("");
  const foldCount = meanEval.fold_summary?.fold_count || pkg.docs[4]?.cv?.fold_count || "—";
  const sourceSha = meanEval.evidence?.source_artifact_sha256 || pooledEval?.evidence?.source_artifact_sha256 || "—";
  const configLink = `<a class="text-link" href="#phase-4">在 Phase 4 變更模型 →</a>`;
  const figureContent = figure
    ? `${packageFigure(pkg, figure.asset_ref, figure.alt || PHASE5_FIGURES.find(([id]) => id === figure.figure_id)?.[1], "package-figure phase5-diagnostic-image")}<p class="stage-note">圖表狀態 ${esc(figure.status)} · Publication review ${esc(figure.publication_review)}. 此為 Development OOF 診斷，不代表獨立 Holdout。</p>`
    : `<div class="state-panel"><h3>此模型的診斷圖目前不可用</h3><p>找不到與目前 Configuration、Pooled Development OOF、來源指紋及 Package Manifest 完全匹配的圖表。未使用 Mock 圖或其他模型的結果代替。</p>${badge("UNAVAILABLE")}</div>`;
  const methodName = methodLabel || meanEval.method_id || "Reference Baseline";
  const modelType = config.track_id?.includes("primary_ols") || config.track_id?.includes("selected_features_to_primary_ols")
    ? "OLS（主要模型）" : (meanEval.model_id || "依研究 Configuration");
  return `<section class="grid two phase5-summary-grid"><article class="card"><div class="card-head"><div><p class="eyebrow">SELECTED MODEL SUMMARY</p><h2>目前評估的模型</h2></div>${badge(computationStatus)}</div><div class="card-body"><dl class="data-row"><dt>特徵選擇方法</dt><dd>${esc(methodName)}</dd></dl><dl class="data-row"><dt>模型類型</dt><dd>${esc(modelType)}</dd></dl><dl class="data-row"><dt>Configuration</dt><dd>${esc(phase5ConfigurationDescription(config))}</dd></dl><dl class="data-row"><dt>評估母體</dt><dd>Development OOF · 三折交叉驗證</dd></dl><dl class="data-row"><dt>Development 筆數</dt><dd>${Number(meanEval.n).toLocaleString()}</dd></dl><dl class="data-row"><dt>交叉驗證折數</dt><dd>${esc(foldCount)}</dd></dl><dl class="data-row"><dt>研究狀態</dt><dd>Evaluation ${esc(computationStatus)} · 發布審查 ${esc(doc.publication_review)}</dd></dl><div class="phase5-model-change">${configLink}</div></div></article><article class="card"><div class="card-head"><div><p class="eyebrow">MEAN-FOLD CV METRICS</p><h2>三折交叉驗證摘要</h2></div>${badge(computationStatus)}</div><div class="card-body"><div class="metrics reference-p5-metrics">${metrics}</div><p class="body-copy">三折交叉驗證指標的算術平均，並非獨立 Holdout Test 的結果。</p><p class="stage-note">指標僅對應目前選取的 Configuration。Publication review：${esc(doc.publication_review)}。</p></div></article></section><section class="card phase5-diagnostics-card"><div class="card-head"><div><p class="eyebrow">CORE DIAGNOSTICS · DEVELOPMENT OOF</p><h2>${esc(PHASE5_FIGURES.find(([id]) => id === selectedFigureId)?.[1] || "Actual vs Predicted")}</h2></div>${badge(figure?.status || "UNAVAILABLE")}</div><div class="card-body"><div class="selector-row phase5-diagnostic-tabs" role="group" aria-label="Core diagnostics">${diagnosticButtons}</div>${figureContent}</div></section><details class="disclosure phase5-advanced"><summary>Advanced Evaluation Details</summary><div class="disclosure-body"><p>Mean-fold 是三折各自指標的算術平均；Pooled OOF 是將所有 Development OOF 預測合併後計算。兩者是不同統計量，不會混合或平均。</p><div class="table-scroll"><table class="mock-data-table"><thead><tr><th>Metric</th><th>Mean-fold CV</th><th>Pooled Development OOF</th><th>Pooled − Mean-fold</th></tr></thead><tbody>${advancedMetricRows}</tbody></table></div><dl class="data-row"><dt>Evaluation IDs</dt><dd>Mean ${esc(meanEval.evaluation_id)}<br>Pooled ${esc(pooledEval?.evaluation_id || "UNAVAILABLE")}</dd></dl><dl class="data-row"><dt>Run ID</dt><dd>${esc(meanEval.execution_run_id)}</dd></dl><dl class="data-row"><dt>Configuration ID</dt><dd>${esc(config.configuration_id)}</dd></dl><dl class="data-row"><dt>資料筆數／折數</dt><dd>${Number(meanEval.n).toLocaleString()} rows · ${esc(foldCount)} folds</dd></dl><dl class="data-row"><dt>Research Evidence Reference / Source SHA-256</dt><dd><code>${esc(meanEval.evidence?.source_ref || sourceSha)}</code></dd></dl><dl class="data-row"><dt>Publication Review</dt><dd>${esc(doc.publication_review)} · ${esc(meanEval.review_status || "PENDING")}</dd></dl><pre class="package-json">${esc(JSON.stringify(config.params || {}, null, 2))}</pre></div></details>`;
}
function explorationComparisonChart(points) {
  const usable = points.filter((item) => item.status === "VERIFIED" && Number.isFinite(Number(item.feature_count_mean)) && Number.isFinite(Number(item.rmse_mean_fold)));
  if (!usable.length) return `<div class="state-panel"><h3>尚無可繪製的已完成比較</h3><p>此視角不會以示意值補出缺少的研究結果。</p></div>`;
  const width = 760, height = 330, left = 74, top = 28, plotW = 640, plotH = 230;
  const minX = Math.min(...usable.map((p) => Number(p.feature_count_mean))), maxX = Math.max(...usable.map((p) => Number(p.feature_count_mean)));
  const minY = Math.min(...usable.map((p) => Number(p.rmse_mean_fold))), maxY = Math.max(...usable.map((p) => Number(p.rmse_mean_fold)));
  const x = (v) => left + (maxX === minX ? 0.5 : (Number(v) - minX) / (maxX - minX)) * plotW;
  const y = (v) => top + plotH - (maxY === minY ? 0.5 : (Number(v) - minY) / (maxY - minY)) * plotH;
  const dots = usable.map((p) => `<circle cx="${x(p.feature_count_mean).toFixed(1)}" cy="${y(p.rmse_mean_fold).toFixed(1)}" r="${p.method_winner ? 6 : 4}" fill="${p.method_winner ? "#f1b45b" : "#55d6c2"}"><title>${esc(p.configuration_id)} · ${Number(p.feature_count_mean).toFixed(1)} features · RMSE ${explorationMetric(p.rmse_mean_fold, "rmse")}</title></circle>`).join("");
  return `<figure class="reference-figure"><svg class="mock-svg exploration-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Development CV feature count versus mean-fold RMSE"><line x1="${left}" y1="${top+plotH}" x2="${left+plotW}" y2="${top+plotH}"/><line x1="${left}" y1="${top}" x2="${left}" y2="${top+plotH}"/>${dots}<text x="${left+plotW/2}" y="${height-12}" text-anchor="middle">Mean selected encoded feature count</text><text transform="translate(20 ${top+plotH/2}) rotate(-90)" text-anchor="middle">Mean-fold CV RMSE</text><text x="${left}" y="${top+plotH+20}">${minX.toFixed(0)}</text><text x="${left+plotW}" y="${top+plotH+20}" text-anchor="end">${maxX.toFixed(0)}</text></svg><figcaption>Only completed Development CV configurations are plotted; ${usable.length} configurations. Incomplete and failed candidates are omitted, not interpolated.</figcaption></figure>`;
}
function renderExplorationPhase4(pkg, doc) {
  const methods = doc.methods || [];
  const configs = doc.configurations || [];
  const selected = explorationSelectedConfig(pkg);
  const selectedMethod = state.explorationMethodId || selected?.method_id || methods[0]?.method_id;
  const selectedForMethod = configs.filter((item) => item.method_id === selectedMethod);
  const activeConfig = selectedForMethod.find((item) => item.configuration_id === state.explorationConfigurationId)
    || selectedForMethod.find((item) => item.status === "VERIFIED") || selectedForMethod[0] || null;
  const methodChart = (doc.charts || []).find((item) => item.chart_id === "method-comparison");
  const curveChart = (doc.charts || []).find((item) => item.chart_id === "feature-count-vs-cv-rmse");
  const comparison = explorationArtifact(pkg, methodChart?.points_ref)?.points || [];
  const curve = explorationArtifact(pkg, curveChart?.points_ref)?.points || [];
  const cv = activeConfig?.status === "VERIFIED" ? explorationArtifact(pkg, activeConfig?.cv_metrics_ref) : null;
  const selectedFeatures = activeConfig?.status === "VERIFIED" ? explorationArtifact(pkg, activeConfig?.selected_features_ref) : null;
  const winnerRows = methods.map((method) => {
    const candidates = comparison.filter((item) => item.method_id === method.method_id && item.status === "VERIFIED");
    const winner = candidates.find((item) => item.method_winner) || candidates[0];
    const candidateCount = configs.filter((item) => item.method_id === method.method_id).length;
    const methodStatus = winner ? "VERIFIED" : configs.some((item) => item.method_id === method.method_id && item.status === "ERROR") ? "ERROR" : "UNAVAILABLE";
    const action = `<button class="selector-button exploration-method-link" type="button" data-exploration-open-method="${esc(method.method_id)}" data-exploration-open-configuration="${esc(winner?.configuration_id || "")}">探索方法 →</button>`;
    return `<tr><td>${esc(method.label)}</td><td>${winner ? esc(winner.configuration_id) : "—"}</td><td>${winner ? Number(winner.feature_count_mean).toFixed(1) : "—"}</td><td>${winner ? explorationMetric(winner.rmse_mean_fold,"rmse") : "—"}</td><td>${badge(methodStatus)}</td><td>${candidateCount} 個 configurations</td><td>${action}</td></tr>`;
  }).join("");
  const folds = cv?.fold_results || [];
  const foldRows = folds.map((fold) => `<tr><td>Fold ${Number(fold.fold)+1}</td><td>${explorationMetric(fold.rmse,"rmse")}</td><td>${explorationMetric(fold.mae,"mae")}</td><td>${explorationMetric(fold.r2,"r2")}</td></tr>`).join("");
  const featureFolds = selectedFeatures?.folds || [];
  const perspectiveBody = state.explorationPerspective === "selected_features"
      ? activeConfig?.status !== "VERIFIED" ? `<div class="state-panel"><h3>此 Configuration 沒有完成可用的特徵選擇</h3><p>保留來源狀態 ${esc(activeConfig?.status || "UNAVAILABLE")}；不會顯示指標或補造特徵。</p></div>` : selectedFeatures ? `<p>${esc(selectedFeatures.summary || "Fold-local selected feature sets.")}</p><div class="grid three">${featureFolds.map((fold) => `<article class="reference-stat-card"><span class="eyebrow">FOLD ${Number(fold.fold)+1} · ${Number(fold.encoded_count).toLocaleString()} ENCODED FEATURES</span><strong>${Number(fold.selected_encoded_names?.length || 0).toLocaleString()} selected</strong><details class="disclosure"><summary>檢視特徵名稱</summary><div class="disclosure-body"><ul class="feature-name-list">${(fold.selected_encoded_names || []).map((name) => `<li>${esc(name)}</li>`).join("")}</ul></div></details></article>`).join("")}</div>` : `<div class="state-panel"><h3>${explorationArtifactPromises.has(activeConfig?.selected_features_ref) ? "載入 fold-local features…" : "Selected feature evidence unavailable"}</h3><p>每折特徵各自從訓練 fold 選出；不代表全 Development 最終重訓特徵集。</p></div>`
      : `${explorationComparisonChart(curve.filter((item) => item.method_id === selectedMethod))}<p class="stage-note">X 軸為 fold 平均 encoded feature 數；Y 軸為三折 RMSE 的算術平均。未執行或失敗的候選不會補值。</p>`;
  const methodOptions = methods.map((item) => `<option value="${esc(item.method_id)}" ${item.method_id === selectedMethod ? "selected" : ""}>${esc(item.label)}</option>`).join("");
  const configOptions = selectedForMethod.map((item) => `<option value="${esc(item.configuration_id)}" ${item.configuration_id === activeConfig?.configuration_id ? "selected" : ""}>${esc(item.configuration_id)} · ${esc(item.status)}</option>`).join("");
  const isExplorer = state.explorationMode === "explorer";
  const comparisonView = `<div class="table-scroll"><table class="mock-data-table"><thead><tr><th>方法 Method</th><th>最佳 Configuration</th><th>平均特徵數</th><th>CV RMSE</th><th>狀態</th><th>已記錄配置</th><th>操作</th></tr></thead><tbody>${winnerRows}</tbody></table></div><p class="stage-note">比較列只呈現同一歷史 Protocol、相同三折 Development CV 母體與 selected-features → primary OLS track 的完成結果；不同評估母體不可直接排名。</p>`;
  const modeSwitch = `<div class="mode-switch exploration-mode-switch" role="group" aria-label="Phase 4 research mode"><button type="button" data-exploration-mode="comparison" aria-pressed="${state.explorationMode === "comparison"}">方法比較 Method Comparison</button><button type="button" data-exploration-mode="explorer" aria-pressed="${state.explorationMode === "explorer"}">單一方法探索 Method Explorer</button></div>`;
  const explorerView = `<div class="control-row"><label class="control">Feature-selection method<select id="exploration-method">${methodOptions}</select></label><label class="control">Configuration / Run<select id="exploration-config" ${selectedForMethod.length ? "" : "disabled"}>${configOptions}</select></label></div><div class="selector-row" role="group" aria-label="Method Explorer view"><button type="button" class="selector-button" data-exploration-perspective="selected_features" aria-pressed="${state.explorationPerspective === "selected_features"}">Selected Features</button><button type="button" class="selector-button" data-exploration-perspective="feature_count_cv_rmse" aria-pressed="${state.explorationPerspective === "feature_count_cv_rmse"}">Feature Count vs. CV RMSE</button></div><div class="metrics exploration-selected-metrics">${activeConfig?.status === "VERIFIED" && cv?.mean_fold_metrics ? explorationMetricsCards(cv.mean_fold_metrics) : `<div class="state-panel"><h3>此 Configuration 沒有可用的已完成指標</h3><p>保留來源狀態 ${esc(activeConfig?.status || "UNAVAILABLE")}；不以其他 Configuration 或 Mock 數值補齊。</p></div>`}</div><div class="exploration-view">${perspectiveBody}</div><section class="card exploration-fold-card"><div class="card-head"><div><p class="eyebrow">THREE-FOLD CROSS VALIDATION</p><h3>${esc(activeConfig?.configuration_id || "Configuration unavailable")}</h3></div>${badge(activeConfig?.status || "UNAVAILABLE")}</div><div class="card-body">${foldRows ? `<div class="table-scroll"><table class="mock-data-table"><thead><tr><th>Fold</th><th>RMSE</th><th>MAE</th><th>R²</th></tr></thead><tbody>${foldRows}</tbody></table></div>` : `<p>${explorationArtifactPromises.has(activeConfig?.cv_metrics_ref) ? "Loading fold metrics…" : "Fold metrics unavailable for this configuration."}</p>`}<p class="stage-note">Fold metrics are bound to the selected Configuration and source-linked Development CV. They are not Holdout scores and do not establish independent generalization.</p><details class="disclosure"><summary>Technical details</summary><div class="disclosure-body"><p>${esc(explorationMethodLabel(doc, activeConfig?.method_id || ""))} · ${esc(activeConfig?.configuration_id || "—")} · Run ${esc(activeConfig?.execution_run_id || "—")}</p><pre class="package-json">${esc(JSON.stringify(activeConfig?.params || {},null,2))}</pre><code>${esc(activeConfig?.protocol_id || "")}</code></div></details></div></section>`;
  const seed = pkg.docs[3]?.split?.seed ?? doc.cv.seed ?? "—";
  return `<section class="card"><div class="card-head"><div><p class="eyebrow">PHASE 4 · DEVELOPMENT CV</p><h2>Model Explorer</h2></div>${badge(doc.status)}</div><div class="card-body">${modeSwitch}<p class="body-copy">${configs.length} recorded configurations · ${configs.filter((item)=>item.status === "VERIFIED").length} completed · ${configs.filter((item)=>item.status === "ERROR").length} failed. Run ${esc(doc.execution_runs?.[0]?.execution_run_id)} · ${Number(doc.cv.training_rows).toLocaleString()} Development rows · ${doc.cv.fold_count}-fold · seed ${esc(seed)}.</p>${isExplorer ? explorerView : comparisonView}</div></section>`;
}
function renderExplorationPhase5(pkg, doc) {
  const phase4 = pkg.docs[4];
  const requestedId = state.explorationConfigurationId;
  const config = requestedId
    ? phase4.configurations.find((item) => item.configuration_id === requestedId)
    : phase4.configurations.find((item) => item.configuration_id === phase4.default_configuration_id)
      || phase4.configurations.find((item) => item.status === "VERIFIED");
  if (!config) return `<section class="state-panel"><h2>沒有可用的 Phase 4 Configuration</h2><p>尚未找到可作為預設值的研究設定。</p>${badge("UNAVAILABLE")}</section>`;
  const evaluations = (doc.evaluations || []).filter((item) => item.configuration_id === config.configuration_id);
  const meanEval = evaluations.find((item) => item.metric_source === "cv_fold_mean");
  const pooled = evaluations.find((item) => item.metric_source === "pooled_oof");
  const meanSourceSha = meanEval?.evidence?.source_artifact_sha256;
  if (!meanEval || meanEval.execution_run_id !== config.execution_run_id
      || !/^[0-9a-f]{64}$/.test(meanSourceSha || "")
      || (pooled && (pooled.execution_run_id !== config.execution_run_id || pooled.n !== meanEval.n
        || pooled.evaluation_population !== meanEval.evaluation_population
        || pooled.prediction_origin !== meanEval.prediction_origin
        || pooled.evidence?.source_artifact_sha256 !== meanSourceSha))) {
    return `<section class="state-panel"><h2>此 Phase 4 Configuration 沒有一致的 Phase 5 評估</h2><p>Configuration ${esc(config.configuration_id)} 的 Run、資料筆數或評估母體無法與 Phase 5 記錄一致；未切換到其他模型。</p>${badge("UNAVAILABLE")}</section>`;
  }
  const method = phase4.methods?.find((item) => item.method_id === config.method_id);
  const figure = phase5BoundFigure(pkg, pooled, state.explorationP5Figure);
  return renderPhase5EvaluationCard(pkg, doc, config, method?.label || config.method_id, meanEval, pooled, figure, state.explorationP5Figure, "data-exploration-p5-figure");
}
function renderCarPhase1(pkg, doc) {
  const source = pkg.caseDoc.source || {};
  return `<section class="reference-summary-grid grid three"><article class="reference-stat-card"><span class="eyebrow">研究案例 CASE</span><strong>${esc(pkg.caseDoc.title)}</strong><small>Case ID · ${esc(pkg.caseDoc.case_id)}</small></article><article class="reference-stat-card"><span class="eyebrow">資料來源 SOURCE</span><strong>${esc(source.label || "來源未提供")}</strong><small>授權審查 ${esc(source.license_review || "PENDING")}</small></article><article class="reference-stat-card"><span class="eyebrow">預測目標 TARGET</span><strong>${esc(pkg.caseDoc.target?.label || "price")}</strong><small>${esc(pkg.caseDoc.target?.unit || "單位未提供")}</small></article></section><section class="grid two">${(doc.sections || []).map((section) => `<article class="card"><div class="card-head"><div><p class="eyebrow">BUSINESS UNDERSTANDING</p><h2>${esc(section.title)}</h2></div>${badge(doc.status)}</div><div class="card-body"><p class="body-copy">${esc(section.body)}</p></div></article>`).join("")}</section><section class="card" style="margin-top:18px"><div class="card-head"><div><p class="eyebrow">EVIDENCE STATUS</p><h2>研究與發布狀態</h2></div>${badge(pkg.manifest.package_status)}</div><div class="card-body"><p>候選比較結果有限；目前最佳候選未優於 Dummy Baseline。研究結果不構成可靠價格預測能力證明。</p><p class="stage-note">Dataset license review：${esc(source.license_review || "PENDING")} · Package publication：PENDING · 原始車輛列與私有模型未包含於此本機展示套件。</p></div></section>`;
}
function renderCarPhase3(pkg, doc) {
  const lineage = pkg.phase3Lineage;
  const cards = (doc.stages || []).map((stage, index) => {
    const total = Number(stage.total);
    const segments = renderSegments(stage, doc.feature_types || []);
    const note = stage.id === "raw" ? "目標 price 不列入預測特徵；原始資料共有 27 個其他欄位，分類比例未完整驗證。"
      : stage.id === "filtered" ? "依欄位語意移除識別碼、自由文字、時間戳及洩漏代理欄位後，保留 15 個原始特徵。"
        : stage.id === "processed" ? "缺失值處理與類別編碼在每個 Development 訓練 Fold 內 fit，避免驗證折資料洩漏。"
          : "One-Hot 編碼後產生 70 個模型特徵；分類依來源欄位語意及 feature lineage 記錄。";
    return `<article class="stage-card"><div class="stage-head"><div class="stage-title"><span class="index"><span>步驟 · STEP</span><b>0${index + 1}</b></span><h2>${esc(stage.label)}</h2></div><span class="stage-total">總數 Total: ${Number.isInteger(total) ? total.toLocaleString() : "—"} ${esc(stage.unit)} ${badge(stage.total_status)}</span></div>${segments}<p class="stage-note">${esc(note)}</p>${stage.id === "encoded" ? `<details class="disclosure"><summary>檢視 ${lineage.encoded_features.length} 個編碼特徵與來源欄位</summary><div class="table-scroll"><table class="mock-data-table"><thead><tr><th>#</th><th>編碼特徵</th><th>來源欄位</th><th>分類</th><th>轉換</th></tr></thead><tbody>${lineage.encoded_features.map((item) => `<tr><td>${Number(item.index) + 1}</td><td>${esc(item.encoded_feature)}</td><td>${esc((item.source_columns || []).join(", "))}</td><td>${esc(typeLabel(item.semantic_type))}</td><td>${esc(item.transformation)}</td></tr>`).join("")}</tbody></table></div><p class="stage-note">Source SHA-256 ${esc(lineage.source_data_sha256)} · Config SHA-256 ${esc(lineage.config_sha256)} · fit: ${esc(lineage.fit_population)}.</p></details>` : ""}</article>`;
  }).join("");
  const split = doc.split || {};
  const totalRows = Number(split.training_rows || 0) + Number(split.holdout_rows || 0);
  const treatments = (doc.treatments || []).map((item) => `<div class="treatment-item"><strong>${esc(item.field || "欄位處理")}</strong><span>${esc(item.reason || item.action)}</span></div>`).join("");
  return `<section class="card"><div class="card-head"><div><p class="eyebrow">FEATURE TRANSFORMATION · FOUR STAGES</p><h2>中古車資料的特徵處理</h2></div>${badge(doc.status)}</div><div class="card-body"><div class="stage-list">${cards}</div><section class="reference-split"><div class="reference-analysis-heading"><div><p class="eyebrow">DEVELOPMENT SPLIT</p><h2>Development／內部 Holdout</h2></div><strong>Seed ${esc(split.seed)}</strong></div><div class="row-split"><span style="width:${totalRows ? split.training_rows / totalRows * 100 : 0}%">Development · ${Number(split.training_rows).toLocaleString()}</span><span style="width:${totalRows ? split.holdout_rows / totalRows * 100 : 0}%">Internal Holdout · ${Number(split.holdout_rows).toLocaleString()}</span></div><p class="stage-note">${Number(split.source_labeled_rows).toLocaleString()} 筆有標籤資料 · 80/20 split · 前處理與特徵選擇只在訓練 Fold fit。此為內部分區，非 Kaggle competition test set。</p></section>${treatments ? `<details class="disclosure"><summary>查看欄位排除與處理紀錄</summary><div class="treatment-list">${treatments}</div></details>` : ""}</div></section>`;
}
function renderCarPhase6(doc) {
  const readiness = doc.readiness || {};
  return `<section class="grid two"><article class="card"><div class="card-head"><div><p class="eyebrow">LOCAL MODEL SMOKE</p><h2>本機模型重載</h2></div>${badge("VERIFIED")}</div><div class="card-body"><p>${esc(readiness.message || "本機模型重載 Smoke 已完成；私有模型未放入 Case Package。")}</p><p class="stage-note">Reload Smoke 只確認本機載入及介面流程，不證明模型具有可靠預測能力。</p></div></article><article class="card"><div class="card-head"><div><p class="eyebrow">ONLINE SERVING</p><h2>線上推論服務</h2></div>${badge(doc.status)}</div><div class="card-body"><p>Prediction unavailable。此案例目前沒有公開推論 API；網站僅展示經核對的研究結果。</p><p class="stage-note">${esc(readiness.reason_code || "NO_PUBLIC_INFERENCE_SERVICE")} · 未公開私有模型或逐筆資料。</p></div></article></section>`;
}
function renderCarPackagePhase(phase) {
  const pkg = carPackage;
  if (!pkg || !pkg.docs[phase]) return `<div class="page"><section class="state-panel" role="${carPackageError ? "alert" : "status"}"><h2>${carPackageError ? "CAR Package 驗證失敗" : "載入 CAR Case Package"}</h2><p>${esc(carPackageError || "正在驗證本機研究套件。")}</p></section></div>`;
  const doc = pkg.docs[phase];
  let body = "";
  if (phase === 1) body = renderCarPhase1(pkg, doc);
  else if (phase === 2) body = renderReferencePhase2(pkg, doc);
  else if (phase === 3) body = renderCarPhase3(pkg, doc);
  else if (phase === 4) body = renderExplorationPhase4(pkg, doc);
  else if (phase === 5) body = renderExplorationPhase5(pkg, doc);
  else body = renderCarPhase6(doc);
  const prev = phase > 1 ? [phase - 1, PHASES[phase - 2][2]] : null;
  const next = phase < 6 ? [phase + 1, PHASES[phase][2]] : null;
  return `<div class="page reference-page" data-car-phase="${phase}"><div class="fixture-banner"><span><strong>中古車研究案例</strong> · ${esc(pkg.manifest.package_revision)} · 本機檢視；公開授權審查待確認。</span>${badge(pkg.manifest.package_status)}</div>${pageHeading(`PHASE 0${phase} / ${PHASES[phase-1][1].toUpperCase()}`, PHASES[phase-1][2], phase === 4 ? "Run 03 中已記錄的同一協定候選比較；失敗組態保留為錯誤狀態。" : phase === 5 ? "使用該 Run 的 Development CV／OOF 指標；Holdout 與 Development CV 分開呈現。" : referencePhaseSubtitle(phase), doc.status)}${body}<p class="stage-note package-verification-note">本機 Case Package 的 Manifest、Phase 文件與列入套件的檔案已逐一驗證 SHA-256／bytes。Publication review：PENDING。</p>${referenceFooterNav(prev, next)}</div>`;
}
function renderExplorationPackagePhase(phase) {
  const pkg = explorationPackage;
  if (!pkg) return `<div class="page">${pageHeading(`PHASE 0${phase} / MODEL EXPLORATION`, "Ames Housing — Full Model Exploration", "Package integrity and availability.", explorationPackageError ? "ERROR" : "UNAVAILABLE")}<section class="state-panel" role="${explorationPackageError ? "alert" : "status"}"><h3>${explorationPackageError ? "Case Package validation failed" : "Loading Model Exploration package"}</h3><p>${esc(explorationPackageError || "Loading the immutable package and verifying its manifest references.")}</p></section></div>`;
  const doc = pkg.docs[phase];
  let body = "";
  if (phase === 1) body = renderReferencePhase1(pkg, doc);
  else if (phase === 2) body = renderReferencePhase2(pkg, doc);
  else if (phase === 3) body = renderReferencePhase3(pkg, doc);
  else if (phase === 4) body = renderExplorationPhase4(pkg, doc);
  else if (phase === 5) body = renderExplorationPhase5(pkg, doc);
  else body = `<section class="state-panel"><h2>Prediction unavailable</h2><p>${esc(doc.readiness?.message || "No matching final model or prediction service is available for this exploration case.")}</p>${badge("UNAVAILABLE")}</section>`;
  const prev = phase > 1 ? [phase - 1, PHASES[phase - 2][2]] : null;
  const next = phase < 6 ? [phase + 1, PHASES[phase][2]] : null;
  return `<div class="page reference-page" data-exploration-phase="${phase}"><div class="fixture-banner"><span><strong>Ames Housing · Full Model Exploration</strong> · ${esc(pkg.manifest.package_revision)} · Historical Development research; package remains PARTIAL.</span>${badge(pkg.manifest.package_status)}</div>${pageHeading(`PHASE 0${phase} / ${PHASES[phase-1][1].toUpperCase()}`, PHASES[phase-1][2], phase === 4 ? "Compare only completed configurations from the same historical CV protocol." : phase === 5 ? "Development OOF metrics are bound to the selected Phase 4 configuration; publication review is pending." : referencePhaseSubtitle(phase), doc.status)}${body}<p class="stage-note package-verification-note">Package file references and the Phase documents shown here were SHA-256 / byte-count verified. Case Package status: ${esc(pkg.manifest.package_status)}.</p>${referenceFooterNav(prev,next)}</div>`;
}
function pageHeading(kicker, title, subtitle, status = caseData().status) {
  return `<div class="page-heading"><div><p class="kicker">${esc(kicker)}</p><h1>${esc(title)}</h1><p class="lede">${esc(subtitle)}</p></div><div class="page-meta">${badge(status)}</div></div>`;
}
function footerNav(prev, next) {
  const phase = routePhase();
  const samplePath = phase === 3
    ? "web/data/cases/ames-housing/phase-03/preparation.json"
    : phase === 5 && PHASE5_PACKAGE_ROOT
      ? `${PHASE5_PACKAGE_ROOT}/phases/phase-05/evaluations.json`
      : REF[`phase${phase}`];
  const schemaPath = phase === 5
    ? "docs/ui-ux/case-package/phase-05/evaluation-index.schema.json"
    : `docs/design/data-contracts/schemas/phase-0${phase}.schema.json`;
  const fileUrl = (path) => path?.startsWith("/")
    ? path
    : path?.startsWith("web/")
      ? `${WEB_BASE}/${path.slice(4)}`
      : path ? `https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/08413d08f5cabbbf519b8ceee4ed68b7187d2669/${path}` : null;
  const provenanceLabel = phase === 5 ? "Case Package files · Phase 5 formal reference" : `Fixture / contract provenance · ${SOURCE}`;
  const manifestLabel = "Schema ↗";
  const source = `<div class="source-note"><span>${esc(provenanceLabel)}</span>${fileUrl(samplePath) ? `<a href="${fileUrl(samplePath)}" target="_blank" rel="noreferrer">${phase === 5 ? "Evaluation index ↗" : "Sample JSON ↗"}</a>` : ""}${fileUrl(schemaPath) ? `<a href="${fileUrl(schemaPath)}" target="_blank" rel="noreferrer">${manifestLabel}</a>` : ""}</div>`;
  return `${source}<nav class="phase-footer" aria-label="前後階段">${prev ? `<a class="button" href="#phase-${prev[0]}">← ${esc(prev[1])}</a>` : `<span></span>`}${next ? `<a class="button primary" href="#phase-${next[0]}">${esc(next[1])} →</a>` : `<span></span>`}</nav>`;
}
function plannedPanel(message = "此案例目前沒有可用的研究資料。") {
  return `<section class="state-panel"><span class="state-icon" aria-hidden="true">i</span><h3>此階段尚未提供資料</h3><p>${esc(message)}切換至此案例不會沿用 Ames 的文字、圖表或狀態。</p>${badge("PLANNED")}</section>`;
}
function renderHome() {
  return `<div class="page home-page"><section class="home-hero"><div class="home-copy"><p class="kicker">研究入口 · RESEARCH WORKSPACE</p><h1>從研究問題<br>走向可追溯的證據</h1><p class="home-en-title">From research questions to traceable evidence</p><p>以清楚可追溯的方式呈現住宅迴歸研究。<br>Explore housing regression research through a clear, traceable workflow.</p><a class="button" href="#phase-1">進入 CRISP-DM · Enter CRISP-DM <span aria-hidden="true">→</span></a></div><div class="home-visual" aria-hidden="true"><svg viewBox="0 0 440 390" role="presentation"><circle class="home-orbit home-orbit-outer" cx="220" cy="195" r="145"/><circle class="home-orbit home-orbit-inner" cx="220" cy="195" r="93"/><path class="home-trace" d="M92 113 169 160 268 117 344 177 290 270 177 251 92 113M169 160 177 251M268 117 290 270"/><circle class="home-trace-node" cx="92" cy="113" r="8"/><circle class="home-trace-node" cx="169" cy="160" r="7"/><circle class="home-trace-node" cx="268" cy="117" r="7"/><circle class="home-trace-node" cx="344" cy="177" r="8"/><circle class="home-trace-node" cx="290" cy="270" r="7"/><circle class="home-trace-node" cx="177" cy="251" r="7"/></svg><div class="home-visual-core"><span>RESEARCH</span><b>→</b><span>EVIDENCE</span></div><span class="home-visual-label label-a">01 · CASE</span><span class="home-visual-label label-b">02 · DATA</span><span class="home-visual-label label-c">03 · MODEL</span><span class="home-visual-label label-d">04 · RESULT</span></div></section></div>`;
}
function renderPhase1() {
  const c = caseData();
  if (c.status === "PLANNED") return `<div class="page">${banner(c)}${pageHeading("PHASE 01 / BUSINESS UNDERSTANDING", "業務理解", "案例脈絡、研究目標與預測標的。", "PLANNED")}${plannedPanel("尚未提供案例來源、研究問題或預測標的。")}${footerNav(null, [2, "資料理解"])}</div>`;
  const sections = c.sections.map((s) => `<article class="card"><div class="card-head"><div><p class="eyebrow">CASE NARRATIVE</p><h2>${esc(s.title)}</h2></div>${badge("MOCK")}</div><div class="card-body"><p class="body-copy">${esc(s.body)}</p></div></article>`).join("");
  const caseCard = `<article class="card"><div class="card-head"><div><p class="eyebrow">資料集與研究案例 DATASET / CASE</p><h2>${esc(c.title)}</h2></div>${badge(c.status)}</div><div class="card-body"><dl class="data-row"><dt>資料集 Dataset</dt><dd>House Prices · 住宅價格</dd></dl><dl class="data-row"><dt>來源 Source</dt><dd>${esc(c.source)}</dd></dl><dl class="data-row"><dt>來源連結 Source URL</dt><dd><a class="text-link" href="${esc(c.sourceUrl)}" target="_blank" rel="noreferrer">開啟資料來源 Open source ↗</a></dd></dl><dl class="data-row"><dt>授權審查 License review</dt><dd>${esc(c.license)} · 待確認 Pending</dd></dl></div></article>`;
  const target = `<article class="card"><div class="card-head"><div><p class="eyebrow">預測目標 PREDICTION TARGET</p><h2>預測標的 Target variable</h2></div>${badge("MOCK")}</div><div class="card-body"><dl class="data-row"><dt>欄位 Field</dt><dd>${esc(c.target.label)} (${esc(c.target.column)})</dd></dl><dl class="data-row"><dt>單位 Unit</dt><dd>${esc(c.target.unit)}</dd></dl><div class="method-ribbon"><strong>示意研究方法 Mock methodology</strong><span>多元線性迴歸 Multiple Linear Regression → 特徵選擇 Feature Selection → 評估 Evaluation<br>方法識別碼 Methodology ID: ${esc(c.methodology)}</span></div></div></article>`;
  return `<div class="page">${banner(c)}${pageHeading("PHASE 01 / BUSINESS UNDERSTANDING", "業務理解", "研究案例介紹：資料來源、問題、研究目標與預測標的。", c.status)}<div class="grid three phase1-grid">${caseCard}${sections}${target}</div>${footerNav(null, [2, "資料理解"])}</div>`;
}

function renderPhase2() {
  const c = caseData();
  if (c.status === "PLANNED") return `<div class="page">${banner(c)}${pageHeading("PHASE 02 / DATA UNDERSTANDING", "資料理解", "瀏覽已產生並核准的靜態 EDA 證據。", "PLANNED")}${plannedPanel()}${footerNav([1,"業務理解"],[3,"資料準備"])}</div>`;
  const selected = c.analyses.find((a) => a.id === state.analysisId) || c.analyses[0];
  const buttons = c.analyses.map((a) => `<button type="button" class="selector-button" data-analysis="${esc(a.id)}" aria-pressed="${a.id === selected.id}">${esc(a.title)} <span class="mini-status">${esc(a.figureId)}</span></button>`).join("");
  const max = Math.max(...selected.mockData.map((point) => point.value));
  const valueText = (value) => selected.id === "correlation" ? `r = ${(value / 100).toFixed(2)}` : selected.id === "overview" ? value.toLocaleString() : `${value}%`;
  const mockFigure = selected.id === "overview"
    ? `<div class="mock-stat-grid">${selected.mockData.map((point) => `<div class="mock-stat"><span>${esc(point.label)}</span><strong>${esc(valueText(point.value))}</strong></div>`).join("")}</div>`
    : `<div class="mock-bar-list">${selected.mockData.map((point) => `<div class="mock-bar-row"><span class="mock-bar-label">${esc(point.label)}</span><span class="mock-bar-track"><i style="width:${Math.max(2, point.value / max * 100)}%"></i></span><strong>${esc(valueText(point.value))}</strong></div>`).join("")}</div>`;
  const mockTable = `<table class="mock-data-table"><thead><tr><th>項目 Item</th><th>示意值 Mock value</th></tr></thead><tbody>${selected.mockData.map((point) => `<tr><td>${esc(point.label)}</td><td>${esc(valueText(point.value))}</td></tr>`).join("")}</tbody></table>`;
  return `<div class="page">${banner(c)}${pageHeading("PHASE 02 / DATA UNDERSTANDING", "資料理解", "以下為合成描述性分析示意，用來預覽圖表與分析切換；不是原始資料計算結果。", "MOCK")}<section class="card"><div class="card-head"><div><p class="eyebrow">靜態分析示意 MOCK EDA · 案例圖表清單 CASE FIGURE LIST</p><h2>選擇分析視角 Select an analysis</h2></div>${badge("MOCK")}</div><div class="card-body"><div class="selector-row" role="group" aria-label="選擇分析 EDA analysis">${buttons}</div></div></section><div class="analysis-layout"><section class="card"><div class="card-head"><div><p class="eyebrow">目前視角 SELECTED · ${esc(selected.figureId)}</p><h2>${esc(selected.title)}</h2></div>${badge("MOCK")}</div><div class="card-body"><div class="mock-figure">${mockFigure}</div>${mockTable}<p class="stage-note">所有數值皆為合成 UI mock，非研究發現。 All values are synthetic UI fixtures, not research findings.</p></div></section><section class="card"><div class="card-head"><div><p class="eyebrow">分析註記 EVIDENCE NOTES</p><h2>說明與限制 Description and limits</h2></div></div><div class="card-body"><dl class="data-row"><dt>描述 Description</dt><dd>${esc(selected.description)}</dd></dl><dl class="data-row"><dt>示意觀察 Mock observation</dt><dd>${esc(selected.finding)}</dd></dl><dl class="data-row"><dt>限制 Limitations</dt><dd>${esc(selected.limitations)}</dd></dl><dl class="data-row"><dt>資料來源 Source</dt><dd>合成 UI fixture · Synthetic UI fixture</dd></dl></div></section></div>${footerNav([1,"業務理解"],[3,"資料準備"])}</div>`;
}
let phase3Data = null;
let phase3Loading = false;
let phase3LoadError = null;
const PHASE3_DATA_URL = `${WEB_BASE}/data/cases/ames-housing/phase-03/preparation.json`;
const PHASE3_UNIT_LABELS = {
  raw_columns: "原始欄位 Raw columns",
  pre_encoding_columns: "編碼前欄位 Pre-encoding columns",
  encoded_features: "編碼後特徵 Encoded features"
};

function loadPhase3Data() {
  if (phase3Loading || phase3Data || phase3LoadError) return;
  phase3Loading = true;
  fetch(PHASE3_DATA_URL)
    .then((response) => {
      if (!response.ok) throw new Error(`Static JSON request failed (${response.status})`);
      return response.json();
    })
    .then((data) => {
      if (data.case_id !== "ames-housing" || data.schema_version !== "1.0.0") {
        throw new Error("Static Phase 3 JSON has an unexpected case or schema version.");
      }
      phase3Data = data;
    })
    .catch((error) => {
      phase3LoadError = error instanceof Error ? error.message : "Unable to load Phase 3 data.";
    })
    .finally(() => {
      phase3Loading = false;
      if (["phase-3", "phase-4"].includes(state.route) && caseData().id === "ames-housing") render();
    });
}

function loadPhase5Package() {
  if (phase5PackageLoading || phase5PackageData || phase5PackageLoadError) return;
  phase5PackageLoading = true;
  Promise.all([
    fetch(`${PHASE5_PACKAGE_ROOT}/package.json`).then((response) => {
      if (!response.ok) throw new Error(`Case Package manifest request failed (${response.status})`);
      return response.json();
    }),
    fetch(`${PHASE5_PACKAGE_ROOT}/phases/phase-05/evaluations.json`).then((response) => {
      if (!response.ok) throw new Error(`Phase 5 evaluation index request failed (${response.status})`);
      return response.json();
    })
  ])
    .then(([manifest, index]) => {
      if (manifest.case_id !== "ames-housing" || index.case_id !== manifest.case_id || index.schema_version !== "1.0.0") {
        throw new Error("The formal Case Package has an unexpected case or schema version.");
      }
      if (manifest.phases?.phase5?.data_ref !== "phases/phase-05/evaluations.json" || !Array.isArray(index.evaluations)) {
        throw new Error("The Phase 5 package reference is missing or malformed.");
      }
      const evaluationIds = new Map();
      const configurations = new Map();
      for (const record of index.evaluations) {
        if (!record.evaluation_id || !record.configuration_id || evaluationIds.has(record.evaluation_id)) {
          throw new Error("The Phase 5 index has a missing or duplicate evaluation ID.");
        }
        evaluationIds.set(record.evaluation_id, record);
        if (!record.metrics || !["mae", "rmse", "r2"].every((key) => Number.isFinite(record.metrics[key]?.value))) {
          throw new Error("A Phase 5 evaluation has missing or invalid metric values.");
        }
        const pair = configurations.get(record.configuration_id) || [];
        pair.push(record);
        configurations.set(record.configuration_id, pair);
      }
      for (const [configurationId, records] of configurations) {
        const sources = records.map((record) => record.metric_source).sort().join("|");
        if (records.length !== 2 || sources !== "cv_fold_mean|pooled_oof") {
          throw new Error(`Configuration ${configurationId} is missing its paired evaluation sources.`);
        }
      }
      for (const record of index.evaluations) {
        if (!Array.isArray(record.linked_evaluation_ids) || record.linked_evaluation_ids.some((id) => evaluationIds.get(id)?.configuration_id !== record.configuration_id)) {
          throw new Error(`Evaluation ${record.evaluation_id} has an unresolved linked evaluation.`);
        }
      }
      phase5PackageData = { manifest, index, configurationIds: [...configurations.keys()].sort() };
    })
    .catch((error) => {
      phase5PackageLoadError = error instanceof Error ? error.message : "Unable to load the formal Phase 5 package.";
    })
    .finally(() => {
      phase5PackageLoading = false;
      if (state.route === "phase-5" && caseData().packageMode === "formal") render();
    });
}

function renderSegments(stage, featureTypes) {
  const total = stage.total;
  const colorsById = new Map(TYPES.map(([id, label, color]) => [id, { label, color }]));
  const dataTypes = featureTypes.map((item) => {
    const type = colorsById.get(item.type_id);
    return [item.type_id, type?.label || `${item.label} (${item.type_id})`, type?.color || "#ccc"];
  });
  const segments = Array.isArray(stage.segments) ? stage.segments : [];
  const segmentTotal = segments.reduce((sum, segment) => sum + segment.count, 0);
  const isMock = stage.distribution_status === "MOCK";
  const eligible = (stage.distribution_status === "VERIFIED" || isMock)
    && (stage.total_status === "VERIFIED" || isMock)
    && Number.isInteger(total)
    && total > 0
    && segments.length > 0
    && segments.every((segment) => Number.isInteger(segment.count) && segment.count >= 0 && dataTypes.some(([id]) => id === segment.type_id))
    && segmentTotal === total;
  if (!eligible) {
    return `<div class="stack-track is-unknown" role="img" aria-label="欄位類型分布 Feature type distribution · ${esc(statusLabel(stage.distribution_status))}">欄位類型分布 Feature type distribution · 百分比不可用 Percentages unavailable</div><div class="legend">${dataTypes.map(([, label, color]) => `<span class="legend-item"><i class="legend-dot" style="--dot:${color}"></i>${esc(label)}：未知 Unknown</span>`).join("")}</div>`;
  }
  const bars = segments.map((segment) => {
    const type = dataTypes.find(([id]) => id === segment.type_id);
    const percent = (segment.count / total) * 100;
    const shortLabel = type?.[1]?.split(" ")[0] || segment.type_id;
    return `<span class="stack-segment" style="width:${percent}%;background:${type?.[2] || "#ccc"}" title="${esc(type?.[1] || segment.type_id)} ${segment.count} / ${total} (${percent.toFixed(1)}%)"><span>${esc(shortLabel)}</span><span>${percent.toFixed(1)}%</span></span>`;
  }).join("");
  const legend = segments.map((segment) => {
    const type = dataTypes.find(([id]) => id === segment.type_id);
    return `<span class="legend-item"><i class="legend-dot" style="--dot:${type?.[2] || "#ccc"}"></i>${esc(type?.[1] || segment.type_id)}：${segment.count} · ${(segment.count / total * 100).toFixed(1)}%</span>`;
  }).join("");
  return `<div class="stack-track${isMock ? " is-mock" : ""}" role="img" aria-label="${esc(stage.label)}${isMock ? " · 合成示意 Synthetic UI mock" : ""}: ${segments.map((segment) => `${segment.type_id} ${segment.count}`).join(", ")}">${bars}</div><div class="legend">${legend}</div>${isMock ? `<p class="stage-note mock-data-note">合成 UI 示意 Synthetic UI mock · 非研究結果 Not research results</p>` : ""}`;
}

function renderPhase3() {
  const c = caseData();
  if (c.status === "PLANNED") return `<div class="page">${banner(c)}${pageHeading("PHASE 03 / DATA PREPARATION", "資料準備", "呈現原始、篩選、處理與編碼的特徵變化。", "PLANNED")}${plannedPanel()}${footerNav([2,"資料理解"],[4,"模型建立"])}</div>`;
  if (!phase3Data && !phase3LoadError) {
    loadPhase3Data();
    return `<div class="page">${banner(c)}${pageHeading("PHASE 03 / DATA PREPARATION", "資料準備", "從靜態案例 JSON 載入階段數值；分布未知時不繪製假比例。", "MOCK")}<section class="state-panel" role="status"><span class="state-icon" aria-hidden="true">…</span><h3>載入 Phase 3 靜態資料</h3><p>目前頁面不會保留其他案例的階段資料。</p></section></div>`;
  }
  if (phase3LoadError) return `<div class="page">${banner(c)}${pageHeading("PHASE 03 / DATA PREPARATION", "資料準備", "Phase 3 資料無法載入。", "ERROR")}<section class="state-panel" role="alert"><h3>Phase 3 JSON 載入失敗</h3><p>${esc(phase3LoadError)}</p></section>${footerNav([2,"資料理解"],[4,"模型建立"])}</div>`;
  if (phase3Data.case_id !== c.id) return `<div class="page">${banner(c)}${pageHeading("PHASE 03 / DATA PREPARATION", "資料準備", "沒有與目前案例相符的 Phase 3 資料。", "UNAVAILABLE")}${plannedPanel("目前沒有此案例的 Phase 3 JSON。")}${footerNav([2,"資料理解"],[4,"模型建立"])}</div>`;

  const data = phase3Data;
  const stages = data.stages.map((stage, index) => {
    const unit = PHASE3_UNIT_LABELS[stage.unit] || stage.unit;
    const note = stage.id === "raw"
      ? `${stage.total ?? "未知 Unknown"} 個原始候選預測欄位 (raw candidate predictor columns) 為來源回報；欄位類型分布 (feature type distribution) 是合成 UI 示意。`
      : stage.id === "encoded"
        ? `${stage.total ?? "未知 Unknown"} 個編碼後維度 (encoded dimensions) 為來源回報；類型分布為合成 UI 示意。擬合資料範圍 (fit population)、流程版本 (pipeline version) 與類型沿革 (type lineage) 尚不可用。`
        : "總數與類別計數皆為合成 UI 示意，並非根據研究資料推導；不代表已確認欄位排除或處理方式。";
    const treatmentAccordion = stage.id === "processed"
      ? `<details class="disclosure treatment-accordion"><summary>展開四種欄位類型處理方式 Expand four feature type treatments</summary><div class="treatment-list">${data.treatments.map((item) => { const type = TYPES.find(([id]) => id === item.type_id); return `<div class="treatment-item"><strong>${esc(type?.[1] || item.type_id)} · ${esc(item.operation_zh)} (${esc(item.operation_en)})</strong><span>${esc(item.description_zh)} ${esc(item.description_en)}</span><em>${esc(statusLabel(item.status))}</em></div>`; }).join("")}</div></details>`
      : "";
    const exclusions = stage.id === "filtered" && stage.exclusions?.length
      ? `<details class="disclosure"><summary>展開排除項目與原因 Excluded items and reasons</summary><div class="treatment-list">${stage.exclusions.map((item) => `<div class="treatment-item"><strong>${esc(item.category_zh)} (${esc(item.category_en)}) · ${item.count}</strong><span>${esc(item.reason_zh)} ${esc(item.reason_en)}</span><em>${esc(statusLabel(item.status))}</em></div>`).join("")}</div></details>`
      : "";
    const lineage = stage.id === "encoded"
      ? `<details class="disclosure"><summary>展開原始欄位至編碼後特徵對應 Raw-to-encoded feature mapping</summary><div class="treatment-list">${data.lineage.map((item) => { const type = TYPES.find(([id]) => id === item.type_id); return `<div class="treatment-item"><strong>${esc(type?.[1] || item.type_id)}</strong><span>${item.source_columns} 個來源欄位 Source columns → ${item.encoded_features} 個編碼後特徵 Encoded features</span><span>${esc(item.operation_zh)} (${esc(item.operation_en)})</span><em>${esc(statusLabel(item.status))}</em></div>`; }).join("")}</div></details>`
      : "";
    return `<section class="stage-card"><div class="stage-head"><div class="stage-title"><span class="index" aria-label="步驟 ${index + 1} Step ${index + 1}"><span>步驟 · STEP</span><b>0${index + 1}</b></span><h2>${esc(stage.label)}</h2></div><span class="stage-total">總數 Total: ${stage.total == null ? "未知 Unknown" : esc(stage.total)} ${esc(unit)} ${badge(stage.total_status)}</span></div>${renderSegments(stage, data.feature_types)}<p class="stage-note">${esc(note)}</p>${exclusions}${treatmentAccordion}${lineage}</section>`;
  }).join("");
  const split = data.split;
  const totalRows = split.source_labeled_rows;
  const splitReady = Number.isInteger(totalRows) && totalRows > 0
    && Number.isInteger(split.training_rows) && Number.isInteger(split.holdout_rows)
    && split.training_rows >= 0 && split.holdout_rows >= 0
    && split.training_rows + split.holdout_rows === totalRows;
  const splitContent = splitReady
    ? `<p class="body-copy">來源回報的資料切分 (data split)：${split.training_rows} / ${totalRows} 訓練集 (Training Set) · ${split.holdout_rows} / ${totalRows} 測試集 (Test Set；留出測試集 Holdout Test Set) · 隨機種子 (Random Seed) ${split.seed ?? "未知 UNKNOWN"}。比例依來源回報呈現，尚未驗證。</p><div class="row-split" role="img" aria-label="來源回報切分比例：訓練集 Training Set ${Math.round(split.training_rows / totalRows * 100)}%，測試集 Test Set ${Math.round(split.holdout_rows / totalRows * 100)}%"><span style="width:${split.training_rows / totalRows * 100}%">訓練集 Training Set · ${split.training_rows} 筆 rows · ${Math.round(split.training_rows / totalRows * 100)}%</span><span style="width:${split.holdout_rows / totalRows * 100}%">測試集 Test Set · ${split.holdout_rows} 筆 rows · ${Math.round(split.holdout_rows / totalRows * 100)}%</span></div><p class="stage-note">第 4 階段交叉驗證 (Cross-validation, CV) 僅使用訓練集；不把測試集當成第 4 階段結果。</p>`
    : `<div class="state-panel"><h3>資料不可用 UNAVAILABLE — 切分資料列數不一致 split row counts do not reconcile。</h3><p>來源列數完整且加總相符前，不顯示切分比例 No split proportion is drawn unless source counts are complete and sum to the labeled row total.</p></div>`;
  return `<div class="page">${banner(c)}${pageHeading("PHASE 03 / DATA PREPARATION", "資料準備", "四個特徵處理階段 (feature preparation stages)，接續獨立的資料列切分 (row split)。", data.status)}<div class="stage-list">${stages}<section class="card"><div class="card-head"><div><p class="eyebrow">資料集切分 Dataset split · 切分資料列，不是特徵 Rows, not features</p><h2>訓練集與測試集 Training and test sets</h2></div>${badge(split.status)}</div><div class="card-body">${splitContent}</div></section></div>${footerNav([2,"資料理解"],[4,"模型建立"])}</div>`;
}

function renderPhase4() {
  const c = caseData();
  if (c.status === "PLANNED") return `<div class="page">${banner(c)}${pageHeading("PHASE 04 / MODELING", "模型建立", "只呈現實際完成且可核對的模型實驗。", "PLANNED")}${plannedPanel()}${footerNav([3,"資料準備"],[5,"模型評估"])}</div>`;
  if (!phase3Data && !phase3LoadError) loadPhase3Data();
  const split = phase3Data?.case_id === c.id ? phase3Data.split : null;
  const splitReady = split && Number.isInteger(split.source_labeled_rows) && split.source_labeled_rows > 0
    && Number.isInteger(split.training_rows) && Number.isInteger(split.holdout_rows)
    && split.training_rows + split.holdout_rows === split.source_labeled_rows;
  const foldNames = ["Fold A", "Fold B", "Fold C"];
  const folds = Array.from({ length: 3 }, (_, iteration) => {
    const blocks = foldNames.map((foldName, foldIndex) => {
      const isValidation = foldIndex === iteration;
      const role = isValidation ? "Validation" : "Training";
      return `<span class="${isValidation ? "cv-valid" : "cv-train"}" style="width:33.333%">${foldName} · ${role}</span>`;
    }).join("");
    return `<div class="cv-row"><span class="cv-label">第 ${iteration + 1} 折 · CV iteration ${iteration + 1}</span><div class="cv-track" role="img" aria-label="CV iteration ${iteration + 1}: ${foldNames.map((name, index) => `${name} ${index === iteration ? "validation" : "training"}`).join(", ")}">${blocks}</div></div>`;
  }).join("");
  const splitReference = splitReady
    ? `<p class="body-copy">Phase 3 資料切分參照 Data split reference：${split.training_rows} / ${split.source_labeled_rows} 訓練集 Training Set · ${split.holdout_rows} / ${split.source_labeled_rows} 測試集 Test Set · 來源回報 Source-reported</p><div class="row-split" role="img" aria-label="與 Phase 3 相同的資料切分：訓練集 Training Set ${Math.round(split.training_rows / split.source_labeled_rows * 100)}%，測試集 Test Set ${Math.round(split.holdout_rows / split.source_labeled_rows * 100)}%"><span style="width:${split.training_rows / split.source_labeled_rows * 100}%">訓練集 Training Set · ${split.training_rows} 筆 rows · ${Math.round(split.training_rows / split.source_labeled_rows * 100)}%</span><span style="width:${split.holdout_rows / split.source_labeled_rows * 100}%">測試集 Test Set · ${split.holdout_rows} 筆 rows · ${Math.round(split.holdout_rows / split.source_labeled_rows * 100)}%</span></div><div class="cv-scope" style="grid-template-columns:${split.training_rows}fr ${split.holdout_rows}fr"><div class="cv-training-scope">${folds}</div><div class="cv-holdout-scope"><strong>測試集 Test Set</strong><span>不參與 CV<br>Excluded from CV</span></div></div>`
    : `<div class="state-panel"><h3>Phase 3 切分資料不可用 UNAVAILABLE</h3><p>無法載入或核對 Phase 3 的訓練集與測試集比例，因此不繪製比例圖，也不推定 CV 範圍。</p></div>`;
  const methodOptions = c.methods.map((m) => `<option value="${esc(m.id)}">${esc(m.label)}</option>`).join("");
  const perspectives = [["method_comparison","方法比較 Method comparison"],["selected_features","選取特徵 Selected features"],["feature_count_vs_cv","特徵數與 CV RMSE Feature count vs CV RMSE"]].map(([id,label]) => `<button class="selector-button" type="button" data-perspective="${id}" aria-pressed="${state.perspective === id}">${label}</button>`).join("");
  const runs = c.mockModelRuns;
  const selectedRun = runs.find((run) => run.id === state.phase4RunId) || runs[1];
  const runOptions = runs.map((run) => `<option value="${esc(run.id)}" ${run.id === selectedRun.id ? "selected" : ""}>${esc(run.id)} · ${esc(run.method)}</option>`).join("");
  const featureCurve = c.mockFeatureCurve;
  const maxError = Math.max(...featureCurve.map((point) => point.rmse));
  const mockPanel = state.perspective === "method_comparison"
    ? `<table class="mock-data-table"><thead><tr><th>示意方法 Mock method</th><th>特徵數 Features</th><th>RMSE (USD)</th><th>MAE (USD)</th><th>R²</th></tr></thead><tbody>${runs.map((run) => `<tr><td>${esc(run.method)}</td><td>${run.featureCount}</td><td>${run.rmse.toLocaleString()}</td><td>${run.mae.toLocaleString()}</td><td>${run.r2.toFixed(2)}</td></tr>`).join("")}</tbody></table>`
    : state.perspective === "selected_features"
      ? `<p class="body-copy">示意配置 Mock run ${selectedRun.id} · ${esc(selectedRun.method)} · ${selectedRun.featureCount} 個特徵 Features</p><div class="feature-chip-list">${selectedRun.selectedFeatures.map((feature) => `<span class="feature-chip">${esc(feature)}</span>`).join("")}</div>`
    : `<div class="mock-bar-list">${featureCurve.map((point) => { const scale = Math.round(point.rmse / maxError * 100); return `<div class="mock-bar-row"><span class="mock-bar-label">${point.features} 個特徵 Features</span><span class="mock-bar-track"><i style="width:${Math.max(4, scale)}%"></i></span><strong>RMSE ${point.rmse.toLocaleString()}</strong></div>`; }).join("")}</div>`;
  return `<div class="page">${banner(c)}${pageHeading("PHASE 04 / MODELING", "模型建立與特徵選擇", "以下模型與分數是合成 UI 示意，僅供檢視頁面功能，不代表實際實驗。", "MOCK")}<section class="card"><div class="card-head"><div><p class="eyebrow">01 · 三折交叉驗證 3-FOLD CROSS-VALIDATION</p><h2>訓練集專用 Training Set only</h2></div>${badge(c.cv.status)}</div><div class="cv-block"><p class="body-copy">交叉驗證 Cross-validation 使用 Phase 3 訓練集 Training Set：${splitReady ? split.training_rows : "—"} 筆來源回報資料列 source-reported rows · 折數 Fold count：${c.cv.foldCount} · 評估指標 Metric：均方根誤差 RMSE (root mean squared error)，越低越好。</p>${splitReference}<div class="legend"><span class="legend-item"><i class="legend-dot" style="--dot:#70b5e8"></i>訓練折 Training folds</span><span class="legend-item"><i class="legend-dot" style="--dot:#55d6c2"></i>驗證折輪替 Validation fold rotates</span><span class="legend-item"><i class="legend-dot" style="--dot:#f1b45b"></i>留出測試集 Holdout test set</span></div><p class="stage-note">示意圖 Schematic only · 每列顯示三個近似等寬資料折 (folds)。實際折數與流程設定未確認。右側測試集不參與 CV。</p><details class="disclosure"><summary>展開交叉驗證方法 Cross-validation methodology</summary><div class="disclosure-body">此處的模型比較分數是合成 UI mock。實際切分器、亂序、隨機種子、折內數量與資料隔離流程仍未知。</div></details></div></section><section class="card explorer"><div class="card-head"><div><p class="eyebrow">02 · 特徵選擇與模型瀏覽器 FEATURE SELECTION & MODEL EXPLORER</p><h2>切換示意研究視角 Choose a mock view</h2></div>${badge("MOCK")}</div><div class="card-body"><div class="selector-row" role="group" aria-label="研究視角 Research perspective">${perspectives}</div><div class="control-row"><label class="control">特徵選擇方法 Feature-selection method<select disabled><option>合成配置 Synthetic configuration</option>${methodOptions}</select></label><label class="control">示意執行 Mock run<select id="p4-run">${runOptions}</select></label></div><section class="mock-result-panel"><div class="mock-result-head"><strong>${state.perspective === "method_comparison" ? "方法比較 Method comparison" : state.perspective === "selected_features" ? "選取特徵 Selected features" : "特徵數與交叉驗證分數 Feature count vs cross-validation score"}</strong>${badge("MOCK")}</div>${mockPanel}</section><p class="stage-note">所有數值、特徵名稱及配置都是人工合成的 UI 示意；不能當成實際模型結果。 All metrics, features, and configurations are synthetic UI fixtures.</p><div class="button-row" style="margin-top:18px"><a class="button" href="#phase-5">查看 Phase 5 評估狀態 →</a><a class="button" href="#phase-6">查詢 Phase 6 模型就緒狀態 →</a></div></div></section>${footerNav([3,"資料準備"],[5,"模型評估"])}</div>`;
}
function renderPhase5Formal(c, packageData) {
  const { manifest, index, configurationIds } = packageData;
  const selectedConfigId = configurationIds.includes(state.phase5ConfigId) ? state.phase5ConfigId : configurationIds[0];
  const selected = index.evaluations.filter((record) => record.configuration_id === selectedConfigId);
  const cvMean = selected.find((record) => record.metric_source === "cv_fold_mean");
  const pooledOof = selected.find((record) => record.metric_source === "pooled_oof");
  const options = configurationIds.map((id, i) => `<option value="${esc(id)}" ${id === selectedConfigId ? "selected" : ""}>設定 Configuration ${String(i + 1).padStart(2, "0")} · ${esc(id.slice(0, 20))}…</option>`).join("");
  const metricDefinitions = [
    ["mae", "MAE", "平均絕對誤差", "Mean Absolute Error", "USD · 越低越好 Lower is better"],
    ["rmse", "RMSE", "均方根誤差", "Root Mean Squared Error", "USD · 越低越好 Lower is better"],
    ["r2", "R²", "決定係數", "Coefficient of Determination", "無單位 Dimensionless"]
  ];
  const formatMetric = (key, value) => key === "r2" ? Number(value).toFixed(4) : Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const sourceCard = (record, sourceLabel, sourceEn) => `<section class="card p5-source-card"><div class="card-head"><div><p class="eyebrow">${sourceLabel} · ${sourceEn}</p><h2>${sourceLabel}</h2></div>${badge(record.review_status)}</div><div class="card-body"><div class="metrics">${metricDefinitions.map(([key, acronym, labelZh, labelEn, note]) => { const metric = record.metrics[key]; return `<article class="metric-card"><div class="metric-name"><strong class="metric-acronym">${acronym}</strong><span class="metric-label">${labelZh}<small>${labelEn}</small></span></div><strong class="metric-value">${formatMetric(key, metric.value)}</strong><span class="metric-note">${badge(metric.status)} · ${note}</span></article>`; }).join("")}</div><details class="disclosure p5-id-details"><summary>查看追溯識別 Traceability IDs</summary><dl class="data-row"><dt>Evaluation ID</dt><dd><code>${esc(record.evaluation_id)}</code></dd></dl><dl class="data-row"><dt>Execution Run</dt><dd><code>${esc(record.execution_run_id)}</code></dd></dl><dl class="data-row"><dt>Linked Evaluation</dt><dd><code>${esc(record.linked_evaluation_ids?.[0])}</code></dd></dl></details></div></section>`;
  const phase5Path = `${PHASE5_PACKAGE_ROOT}/phases/phase-05/evaluations.json`;
  const packagePath = `${PHASE5_PACKAGE_ROOT}/package.json`;
  const figureState = [...new Set(selected.map((record) => record.asset_status))].join(" · ");
  return `<div class="page">${banner(c)}${pageHeading("PHASE 05 / EVALUATION", "模型評估", "此頁直接讀取正式 Case Package 的 Phase 5 索引；指標與索引審查狀態分開呈現。", index.status)}<section class="card"><div class="card-head"><div><p class="eyebrow">正式 CASE PACKAGE · ${esc(manifest.package_revision)}</p><h2>套件資料來源與評估設定 Package source & evaluation selection</h2></div>${badge(manifest.package_status)}</div><div class="card-body p5-package-grid"><div><dl class="data-row"><dt>Package ID</dt><dd><code>${esc(manifest.package_id)}</code></dd></dl><dl class="data-row"><dt>Package revision</dt><dd><code>${esc(manifest.package_revision)}</code></dd></dl><dl class="data-row"><dt>Phase 5 index</dt><dd>${index.evaluations.length} 筆 evaluations · ${configurationIds.length} 組 configurations</dd></dl><dl class="data-row"><dt>索引審查 Index review</dt><dd>${esc(index.status)} · ${esc(index.reason_code)} · ${esc(index.publication_review)}</dd></dl><div class="p5-package-links"><a class="text-link" href="${phase5Path}" target="_blank" rel="noreferrer">開啟 Phase 5 Evaluation JSON ↗</a><a class="text-link" href="${packagePath}" target="_blank" rel="noreferrer">開啟 Package Manifest ↗</a></div></div><div><label class="control" for="p5-config">設定 Configuration</label><select id="p5-config">${options}</select><p class="stage-note">套件未指定預設 Evaluation ID；目前顯示排序後第一組設定。The package has no default Evaluation ID; showing the first sorted configuration.</p><dl class="data-row"><dt>Configuration ID</dt><dd><code>${esc(selectedConfigId)}</code></dd></dl><dl class="data-row"><dt>Evaluation population</dt><dd>Development OOF · no holdout records in this index</dd></dl></div></div><p class="stage-note">目前案例選單中的 MOCK 仍是獨立預覽項目。這個正式套件選項只接入 Phase 5；其他 Phase 頁仍維持其原有預覽內容。</p></section><div class="p5-source-compare">${sourceCard(cvMean, "折均值交叉驗證", "CV fold mean")}${sourceCard(pooledOof, "OOF 合併計算", "Pooled OOF")}</div><section class="card p5-diagnostics"><div class="card-head"><div><p class="eyebrow">診斷圖 DIAGNOSTIC FIGURES</p><h2>目前沒有連結到這組評估的診斷圖</h2></div>${badge(figureState || "UNAVAILABLE")}</div><div class="card-body"><p class="body-copy">此設定的 Evaluation records 沒有圖表參照，asset status 為 ${esc(figureState || "UNAVAILABLE")}。套件內圖資標記為 PLANNED，尚未連結至這組評估，因此此處不以圖資或 MOCK 圖替代。</p><p class="stage-note">單項指標狀態依索引呈現；索引本身仍為 ${esc(index.status)} · ${esc(index.reason_code)}。</p></div></section>${footerNav([4,"返回模型建立"],[6,"模型就緒狀態"])}</div>`;
}

function renderPhase5() {
  const c = caseData();
  if (c.packageMode === "formal") {
    if (!PHASE5_PACKAGE_ROOT) return `<div class="page">${banner(c)}${pageHeading("PHASE 05 / EVALUATION", "模型評估", "正式 Case Package 尚未進入公開 release。", "PLANNED")}<section class="state-panel"><h3>目前沒有已發布的 Case Package</h3><p>正式資料保存在私有 staging；完成獨立審查與發布後，網站才會從不可變 release 路徑讀取。</p>${badge("PLANNED")}</section>${footerNav([4,"模型建立"],[6,"模型預測實驗室"])}</div>`;
    if (!phase5PackageData && !phase5PackageLoadError) loadPhase5Package();
    if (phase5PackageLoadError) return `<div class="page">${banner(c)}${pageHeading("PHASE 05 / EVALUATION", "模型評估", "正式 Case Package 無法載入。", "ERROR")}<section class="state-panel" role="alert"><h3>Phase 5 資料載入失敗</h3><p>${esc(phase5PackageLoadError)}</p></section>${footerNav([4,"模型建立"],[6,"模型預測實驗室"])}</div>`;
    if (!phase5PackageData) {
      loadPhase5Package();
      return `<div class="page">${banner(c)}${pageHeading("PHASE 05 / EVALUATION", "模型評估", "正在讀取正式 Case Package。", "PLANNED")}<section class="state-panel"><h3>載入 Phase 5 資料中 Loading package data…</h3><p>${esc(PHASE5_PACKAGE_ROOT)}</p></section>${footerNav([4,"模型建立"],[6,"模型預測實驗室"])}</div>`;
    }
    return renderPhase5Formal(c, phase5PackageData);
  }
  if (c.status === "PLANNED") return `<div class="page">${banner(c)}${pageHeading("PHASE 05 / EVALUATION", "模型評估", "只有符合指定評估母體並通過審核的結果才會顯示。", "PLANNED")}${plannedPanel()}${footerNav([4,"模型建立"],[6,"模型預測實驗室"])}</div>`;
  const figures = c.evaluation.figures.map(([id,label]) => `<button class="selector-button" type="button" data-p5-figure="${id}" aria-pressed="${state.phase5Figure === id}">${id} · ${label}</button>`).join("");
  const mock = c.evaluation.mock;
  const holdout = state.p5Population === "holdout";
  const metrics = holdout ? { mae: 23100, rmse: 33700, r2: 0.81 } : mock.metrics;
  const predictionPoints = holdout
    ? mock.predictions.map((point, i) => ({ ...point, predicted: point.predicted + (i % 2 === 0 ? 6000 : -5000) }))
    : mock.predictions;
  const residuals = predictionPoints.map((point) => point.actual - point.predicted);
  const minPrice = 80000;
  const maxPrice = 460000;
  const plotPoints = predictionPoints.map((point, i) => {
    const x = 60 + (point.predicted - minPrice) / (maxPrice - minPrice) * 560;
    const residual = point.actual - point.predicted;
    const y = state.phase5Figure === "FIG-P5-02" ? 155 - residual / 25000 * 110 : 280 - (point.actual - minPrice) / (maxPrice - minPrice) * 250;
    return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="6"/>`;
  }).join("");
  const histogram = holdout
    ? mock.histogram.map((bin, i) => ({ ...bin, value: [7, 16, 26, 31, 15, 5][i] }))
    : mock.histogram;
  const histogramBars = histogram.map((bin, i) => `<g><rect x="${70 + i * 88}" y="${270 - bin.value * 5}" width="56" height="${bin.value * 5}"/><text x="${98 + i * 88}" y="292" text-anchor="middle">${esc(bin.label)}</text><text x="${98 + i * 88}" y="${258 - bin.value * 5}">${bin.value}%</text></g>`).join("");
  const mockChart = state.phase5Figure === "FIG-P5-03"
    ? `<svg class="mock-svg" viewBox="0 0 680 330" role="img" aria-label="合成殘差分布直方圖 Synthetic residual distribution histogram"><line x1="50" y1="270" x2="640" y2="270"/><line x1="50" y1="40" x2="50" y2="270"/>${histogramBars}<text x="340" y="325" text-anchor="middle">殘差區間 Residual range</text></svg>`
    : `<svg class="mock-svg" viewBox="0 0 680 330" role="img" aria-label="合成診斷散佈圖 Synthetic diagnostic scatter plot"><line x1="60" y1="280" x2="630" y2="280"/><line x1="60" y1="35" x2="60" y2="280"/>${state.phase5Figure === "FIG-P5-02" ? `<line class="mock-zero-line" x1="60" y1="155" x2="630" y2="155"/>` : `<line class="mock-diagonal" x1="60" y1="280" x2="620" y2="35"/>`}${plotPoints}<text x="340" y="320" text-anchor="middle">預測售價 Predicted price</text><text transform="translate(18 165) rotate(-90)" text-anchor="middle">${state.phase5Figure === "FIG-P5-02" ? "殘差 Residual" : "實際售價 Actual price"}</text></svg>`;
  const metricCards = [
    ["MAE", "平均絕對誤差", "Mean Absolute Error", metrics.mae, "USD · 越低越好 Lower is better"],
    ["RMSE", "均方根誤差", "Root Mean Squared Error", metrics.rmse, "USD · 越低越好 Lower is better"],
    ["R²", "決定係數", "Coefficient of Determination", metrics.r2.toFixed(2), "無單位 Dimensionless"]
  ].map(([acronym, labelZh, labelEn, value, note]) => `<article class="metric-card"><div class="metric-name"><strong class="metric-acronym">${acronym}</strong><span class="metric-label">${labelZh}<small>${labelEn}</small></span></div><strong class="metric-value">${typeof value === "number" ? value.toLocaleString("en-US") : value}</strong><span class="metric-note">合成示意 MOCK · ${note}</span></article>`).join("");
  const chartTable = predictionPoints.map((point, i) => `<tr><td>${i + 1}</td><td>${point.actual.toLocaleString()}</td><td>${point.predicted.toLocaleString()}</td><td>${residuals[i].toLocaleString()}</td></tr>`).join("");
  return `<div class="page">${banner(c)}${pageHeading("PHASE 05 / MODEL EVALUATION", "模型評估", "以下指標與圖表為合成 UI 示意，只用來預覽評估頁面，不代表實際模型評估結果。", "MOCK")}<section class="card"><div class="card-head"><div><p class="eyebrow">01 · 評估範圍與識別 EVALUATION CONTEXT</p><h2>評估設定與身分 Evaluation setup and identity</h2></div>${badge("MOCK")}</div><div class="card-body grid two"><div><dl class="data-row"><dt>示意配置 Mock configuration</dt><dd>${esc(mock.configId)}</dd></dl><dl class="data-row"><dt>示意執行 Mock execution</dt><dd>${esc(mock.runId)}</dd></dl><dl class="data-row"><dt>示意評估 Mock evaluation</dt><dd>${esc(mock.evaluationId)}</dd></dl></div><div><label class="control">評估母體 Evaluation population<select id="p5-population"><option value="development_oof" ${!holdout ? "selected" : ""}>開發資料 OOF Development OOF</option><option value="holdout" ${holdout ? "selected" : ""}>測試集 Test set（留出集 Holdout）</option></select></label><p class="stage-note">母體切換會顯示不同的合成示意數值；無真實評估資料。Population switch changes mock values only.</p></div></div></section><div class="metrics" style="margin-top:18px">${metricCards}</div><section class="card explorer"><div class="card-head"><div><p class="eyebrow">03 · 核心診斷圖 Core diagnostics</p><h2>${esc(c.evaluation.figures.find(([id]) => id === state.phase5Figure)?.[1] || "Residual vs Predicted")}</h2></div>${badge("MOCK")}</div><div class="card-body"><div class="selector-row" role="group" aria-label="診斷圖選擇 Diagnostic figure">${figures}</div><div class="mock-figure" style="margin-top:16px">${mockChart}</div><table class="mock-data-table"><thead><tr><th>示意列 Mock row</th><th>實際值 Actual (USD)</th><th>預測值 Predicted (USD)</th><th>殘差 Residual (USD)</th></tr></thead><tbody>${chartTable}</tbody></table><p class="stage-note">六筆合成資料列 Synthetic rows · 僅供繪圖預覽，不是實際觀測值。</p></div></section><div class="grid two" style="margin-top:18px"><section class="card"><div class="card-head"><div><p class="eyebrow">04 · 信賴區間與預測區間 CONFIDENCE / PREDICTION INTERVAL</p><h2>合成區間示意 Mock interval illustration</h2></div>${badge("MOCK")}</div><div class="card-body"><dl class="data-row"><dt>示意方法 Mock method</dt><dd>${esc(mock.intervals.method)}</dd></dl><dl class="data-row"><dt>示意區間 Mock range</dt><dd>${mock.intervals.lower.toLocaleString()}–${mock.intervals.upper.toLocaleString()} USD</dd></dl><dl class="data-row"><dt>示意涵蓋率 Mock coverage</dt><dd>${Math.round(mock.intervals.coverage * 100)}%</dd></dl><p class="stage-note">此區間與涵蓋率均為合成值，不具統計推論效力。Synthetic values; no inferential claim.</p></div></section><section class="card"><div class="card-head"><div><p class="eyebrow">05 · 可追溯性 TRACEABILITY</p><h2>來源、方法與限制 Source, method, and limits</h2></div>${badge("MOCK")}</div><div class="card-body"><p class="body-copy">此頁評估 ID、樣本數、預測值與圖表都為合成 UI 資料；沒有連結到真實研究執行或已發布證據。</p><p class="stage-note">Evaluation identity, samples, predictions and figures are synthetic fixtures; no published evidence is linked.</p></div></section></div>${footerNav([4,"返回模型建立"],[6,"模型就緒狀態"])}</div>`;
}
function renderPhase6() {
  const c = caseData();
  if (c.status === "PLANNED") return `<div class="page">${banner(c)}${pageHeading("PHASE 06 / MODEL PREDICTION LAB", "房價預測實驗室", "單筆推論需要通過核准的模型、輸入 Schema 與已部署 API。", "PLANNED")}${plannedPanel(c.inference.message)}${footerNav([5,"模型評估"],null)}</div>`;
  const mock = c.mockInference;
  const neighborhoodOptions = AMES_NEIGHBORHOODS.map((value) => `<option value="${value}" ${value === state.phase6Values.neighborhood ? "selected" : ""}>${value}</option>`).join("");
  const qualityTicks = Array.from({ length: 10 }, (_, index) => `<span>${index + 1}</span>`).join("");
  const csv = state.phase6Csv;
  const csvPanel = csv ? `<div class="upload-zone p6-upload-zone"><div class="p6-csv-summary"><strong>${esc(csv.fileName)}</strong><span>${csv.rows.length.toLocaleString()} rows · ${csv.headers.length} columns</span></div><label class="control">更換 CSV 檔案 Choose another CSV<input id="p6-csv-file" type="file" accept=".csv,text/csv"></label><p class="stage-note" role="status">${esc(state.phase6CsvMessage)} 檔案只在此瀏覽器本機讀取，不會上傳或保存。</p><div class="control-row p6-csv-controls"><label class="control">選擇資料列 Select row<select id="p6-csv-row">${csv.rows.map((_, index) => `<option value="${index}" ${index === csv.selectedIndex ? "selected" : ""}>Row ${index + 1}</option>`).join("")}</select></label><div class="p6-map-status"><strong>欄位對應 Field mapping</strong><span>${["Neighborhood","OverallQual","BedroomAbvGr","GrLivArea"].filter((name) => csv.headers.includes(name)).length}/4 exact-name fields recognized</span><small>${["Neighborhood","OverallQual","BedroomAbvGr","GrLivArea"].map((name) => `${csv.headers.includes(name) ? "✓" : "○"} ${name}`).join(" · ")}</small></div></div><div class="csv-preview p6-csv-preview"><table><thead><tr><th>Row</th>${csv.headers.map((header) => `<th>${esc(header)}</th>`).join("")}</tr></thead><tbody>${csv.rows.slice(0,8).map((row,index)=>`<tr class="${index===csv.selectedIndex?"selected":""}"><td>${index+1}</td>${csv.headers.map((_,column)=>`<td>${esc(row[column]??"")}</td>`).join("")}</tr>`).join("")}</tbody></table></div><div class="button-row" style="margin-top:14px"><button type="button" class="button primary" data-action="phase6-use-csv-row" ${["Neighborhood","OverallQual","BedroomAbvGr","GrLivArea"].some((name) => csv.headers.includes(name)) ? "" : "disabled"}>將此列帶入手動欄位 Use row in manual form</button></div><p class="stage-note">僅依完全相符的欄名帶入，不猜測欄位；無正式模型，不能由 CSV 產生真實預測。</p></div>` : `<div class="upload-zone p6-upload-zone"><label class="control">選擇 CSV 檔案 Choose CSV file<input id="p6-csv-file" type="file" accept=".csv,text/csv"></label><p class="stage-note" role="status">${esc(state.phase6CsvMessage)} CSV stays in this browser only; no upload or persistence.</p></div>`;
  const result = state.phase6MockSubmitted
    ? `<div class="model-state mock-prediction-result"><p class="eyebrow">合成推論結果 SYNTHETIC MOCK PREDICTION</p><h2>${mock.estimate.toLocaleString()} ${esc(mock.unit)}</h2><p>預測售價 Estimate for ${esc(mock.target)} · 僅為固定示意值，不是由輸入欄位計算。</p><dl class="data-row"><dt>示意區間 Mock range</dt><dd>${mock.lower.toLocaleString()}–${mock.upper.toLocaleString()} ${esc(mock.unit)}</dd></dl><dl class="data-row"><dt>模型 Model</dt><dd>${esc(mock.modelId)}</dd></dl>${badge("MOCK")}</div>`
    : `<div class="state-panel"><span class="state-icon" aria-hidden="true">i</span><h3>尚未顯示示意結果 Mock preview not shown</h3><p>按下按鈕只會顯示預設合成值；不會執行推論。The button reveals a fixed mock value and does not run inference.</p>${badge("MOCK")}</div>`;
  return `<div class="page">${banner(c)}${pageHeading("PHASE 06 / MODEL PREDICTION LAB", "房價預測實驗室", "此頁展示推論介面的合成互動；沒有註冊模型或即時推論服務。Mock UI only: no registered model or live inference service.", "MOCK")}<section class="card"><div class="card-head"><div><p class="eyebrow">案例與模型脈絡 CASE / MODEL CONTEXT</p><h2>${esc(c.title)}</h2></div>${badge("MOCK")}</div><div class="card-body grid three"><dl class="data-row"><dt>預測目標 Target</dt><dd>${esc(c.target.label)} · ${esc(c.target.unit)}</dd></dl><dl class="data-row"><dt>示意執行 Mock run</dt><dd>${esc(mock.runId)}</dd></dl><dl class="data-row"><dt>示意模型 Mock model</dt><dd>${esc(mock.modelId)}</dd></dl></div></section><div class="two-panel phase6-panels" style="margin-top:18px"><section class="card"><div class="card-head"><div><p class="eyebrow">輸入欄位示意 MOCK INPUT SCHEMA</p><h2>住宅條件 Housing features</h2></div>${badge("MOCK")}</div><div class="card-body ${state.phase6InputMode === "csv" ? "phase6-csv-mode" : ""}"><p class="body-copy">欄位依 Phase 3 的資料型態分類，並使用相應控制方式。 Field controls follow the Phase 3 measurement types.</p><div class="mode-switch p6-mode-switch" role="group" aria-label="Input method"><button type="button" data-phase6-mode="manual" aria-pressed="${state.phase6InputMode === "manual"}">手動輸入 Manual entry</button><button type="button" data-phase6-mode="csv" aria-pressed="${state.phase6InputMode === "csv"}">CSV 上傳 CSV upload</button></div>${state.phase6InputMode === "csv" ? csvPanel : ""}<div class="p6-feature-grid"><article class="p6-feature-card"><span class="p6-type-tag nominal">名目 · NOMINAL</span><label class="p6-field-label" for="p6-neighborhood"><strong>住宅區位 Neighborhood</strong><span>25 個本機資料類別 · 類別選單 Categorical choice</span></label><select id="p6-neighborhood">${neighborhoodOptions}</select><p class="p6-field-note">區位名稱沒有大小順序，使用下拉選單。Nominal values have no rank order.</p></article><article class="p6-feature-card"><span class="p6-type-tag ordinal">次序 · ORDINAL</span><label class="p6-field-label" for="p6-overall-quality"><strong>房屋整體品質 OverallQual</strong><span>建材與裝修評級 · 有序尺度 Ordered scale</span></label><input id="p6-overall-quality" class="p6-range" type="range" min="1" max="10" step="1" value="${esc(state.phase6Values.quality)}" aria-label="Overall quality, scale 1 to 10"><div class="p6-scale-ticks" aria-hidden="true">${qualityTicks}</div><div class="p6-scale-labels"><span>1 · 非常差<br>Very Poor</span><output id="p6-quality-output" for="p6-overall-quality">${qualityScaleLabel(state.phase6Values.quality)}</output><span>10 · 極佳<br>Very Excellent</span></div><p class="p6-field-note">資料定義的 1–10 等級；拖動尺度可切換示意值。The range follows the source rating scale.</p></article><article class="p6-feature-card"><span class="p6-type-tag discrete">離散 · DISCRETE</span><label class="p6-field-label" for="p6-bedroom-count"><strong>地上臥室數 BedroomAbvGr</strong><span>地下室臥室不計 · 整數計數 Integer count</span></label><div class="p6-number-field"><input id="p6-bedroom-count" type="number" min="0" max="8" step="1" value="${esc(state.phase6Values.bedrooms)}"><span>間 bedrooms</span></div><p class="p6-field-note">本機資料觀察範圍：0–8 間。Observed range: 0–8.</p></article><article class="p6-feature-card"><span class="p6-type-tag continuous">連續 · CONTINUOUS</span><label class="p6-field-label" for="p6-living-area"><strong>地上居住面積 GrLivArea</strong><span>平方英尺 · 面積數值 Area in square feet</span></label><div class="p6-number-field"><input id="p6-living-area" type="number" min="334" max="5642" step="1" value="${esc(state.phase6Values.area)}"><span>sq ft</span></div><p class="p6-field-note">本機資料觀察範圍：334–5,642 平方英尺。Observed range: 334–5,642 sq ft.</p></article></div><p class="stage-note">欄位型態與可用類別／範圍依本機 1,460 筆訓練資料核對；預設值是介面示意，不是單一資料列，也不會輸入模型計算。Feature types and observed options/ranges were checked against the local 1,460-row training file; defaults are UI fixtures, not a record or model input.</p><div class="button-row" style="margin-top:14px"><button class="button primary" type="button" data-action="phase6-mock-preview">顯示示意預測 Show mock estimate</button></div></div></section><section class="card"><div class="card-head"><div><p class="eyebrow">預測結果 PREDICTION RESULT</p><h2>合成售價示意 Synthetic estimate</h2></div>${badge("MOCK")}</div><div class="card-body">${result}<p class="stage-note">不會訓練或載入模型、不會讀取輸入值計算，也不會呼叫 API。No model is loaded or trained, inputs are not computed, and no API is called.</p></div></section></div><section class="card" style="margin-top:18px"><div class="card-body"><p class="eyebrow">來源與限制 PROVENANCE & LIMITATIONS</p><p class="body-copy">Case ID: ${esc(c.id)} · 此頁的模型識別碼、輸入欄位、預測值及區間都是合成 UI mock，不能解讀為實際推論結果。</p><p class="stage-note">Model ID, input fields, prediction and interval are synthetic UI fixtures, not real inference output.</p><a class="text-link" href="#phase-5">查看 Phase 5 評估狀態 View Phase 5 →</a></div></section>${footerNav([5,"模型評估"],null)}</div>`;
}
function renderDashboardVerified() {
  const c = caseData();
  if (c.packageMode === "car") {
    const pkg = carPackage;
    if (!pkg) return `<div class="state-panel"><h3>載入中古車研究摘要中</h3><p>${esc(carPackageError || "正在驗證本機 Case Package。")}</p>${badge(carPackageError ? "ERROR" : "UNAVAILABLE")}</div>`;
    const phase4 = pkg.docs[4], winner = phase4.configurations.find((item) => item.configuration_id === phase4.default_configuration_id);
    const evaluations = pkg.docs[5].evaluations.filter((item) => item.configuration_id === winner?.configuration_id);
    const mean = evaluations.find((item) => item.metric_source === "cv_fold_mean");
    return `<div class="grid three"><article class="card"><div class="card-head"><div><p class="eyebrow">USED CAR CASE</p><h2>${esc(pkg.caseDoc.title)}</h2></div>${badge(pkg.manifest.package_status)}</div><div class="card-body"><p>${esc(pkg.caseDoc.source.label)} · ${esc(pkg.caseDoc.target.raw_field_id)}</p><p>Development ${Number(pkg.docs[4].cv.training_rows).toLocaleString()} rows · ${phase4.cv.fold_count}-fold</p></div></article><article class="card"><div class="card-head"><div><p class="eyebrow">CANDIDATE EXPLORATION</p><h2>${phase4.configurations.length} configurations</h2></div>${badge("PARTIAL")}</div><div class="card-body"><p>${phase4.configurations.filter((item) => item.status === "VERIFIED").length} completed · ${phase4.configurations.filter((item) => item.status === "ERROR").length} failed.</p><p>最佳候選僅代表已完成候選中的相對排序。</p></div></article><article class="card"><div class="card-head"><div><p class="eyebrow">DEVELOPMENT CV</p><h2>Mean-fold RMSE</h2></div>${badge("VERIFIED")}</div><div class="card-body"><p>${mean ? phase5FormatMetric(phase5MetricValue(mean, "rmse"), "rmse") : "—"} USD</p><p>該候選未優於 Dummy Baseline；預測能力有限。</p></div></article></div><div class="button-row" style="margin-top:18px">${PHASES.map(([n,,zh]) => `<a class="button" href="#phase-${n}">Phase ${n} · ${esc(zh)}</a>`).join("")}</div>`;
  }
  if (c.packageMode === "exploration") {
    const pkg = explorationPackage;
    if (!pkg) return `<div class="state-panel"><h3>載入 Model Exploration 摘要中</h3><p>${esc(explorationPackageError || "Waiting for the static Case Package.")}</p>${badge(explorationPackageError ? "ERROR" : "UNAVAILABLE")}</div>`;
    const p4 = pkg.docs[4], p5 = pkg.docs[5];
    const methodChart = p4.charts.find((item) => item.chart_id === "method-comparison");
    const points = explorationArtifact(pkg, methodChart.points_ref)?.points || [];
    const winners = p4.methods.map((method) => points.find((item) => item.method_id === method.method_id && item.method_winner)).filter(Boolean);
    return `<div class="grid three"><article class="card"><div class="card-head"><div><p class="eyebrow">FULL MODEL EXPLORATION</p><h2>${esc(pkg.caseDoc.title)}</h2></div>${badge(pkg.manifest.package_status)}</div><div class="card-body"><p>${esc(pkg.caseDoc.source.label)} · Target ${esc(pkg.caseDoc.target.raw_field_id)}</p><p>${p4.configurations.length} configurations · ${p4.configurations.filter((x)=>x.status === "VERIFIED").length} completed · ${p4.cv.fold_count}-fold Development CV</p></div></article><article class="card"><div class="card-head"><div><p class="eyebrow">METHOD COMPARISON</p><h2>${winners.length} methods with completed results</h2></div>${badge("VERIFIED")}</div><div class="card-body"><p>Fixed historical protocol · ${esc(p4.execution_runs[0].execution_run_id)}</p><p>Invalid configurations are retained with their recorded status and excluded from scores.</p></div></article><article class="card"><div class="card-head"><div><p class="eyebrow">DEVELOPMENT OOF</p><h2>Phase 5 metrics</h2></div>${badge(p5.publication_review)}</div><div class="card-body"><p>${p5.evaluations.length} bound evaluations across ${new Set(p5.evaluations.map((x)=>x.configuration_id)).size} configurations.</p><p>Publication review pending; no predictions or residual rows are public.</p></div></article></div><div class="button-row" style="margin-top:18px">${PHASES.map(([n,,zh]) => `<a class="button" href="#phase-${n}">Phase ${n} · ${esc(zh)}</a>`).join("")}</div>`;
  }
  if (c.packageMode === "reference") {
    const pkg = referencePackage;
    if (!pkg) return `<div class="state-panel"><h3>載入 Reference Baseline 摘要中</h3><p>${esc(referencePackageError || "Waiting for the static Case Package.")}</p>${badge(referencePackageError ? "ERROR" : "UNAVAILABLE")}</div>`;
    const caseDoc = pkg.caseDoc;
    const split = pkg.docs[3].split;
    const evaluationDoc = pkg.docs[5];
    const pooled = evaluationDoc.evaluations.find((item) => item.evaluation_id === evaluationDoc.default_evaluation_id);
    const metrics = pooled ? ["mae", "rmse", "r2"].map((key) => `<dl class="data-row"><dt>${key.toUpperCase()} · Development OOF</dt><dd>${Number(pooled.metrics[key].value).toLocaleString("en-US", {maximumFractionDigits: key === "r2" ? 8 : 6})}</dd></dl>`).join("") : "<p>OOF metrics unavailable.</p>";
    return `<div class="grid three"><article class="card"><div class="card-head"><div><p class="eyebrow">REFERENCE CASE</p><h2>${esc(caseDoc.title)}</h2></div>${badge(pkg.manifest.package_status)}</div><div class="card-body"><p>Source: ${esc(caseDoc.source.label)} · Target: ${esc(caseDoc.target.raw_field_id)}</p><p>Development rows: ${split.training_rows} · Encoded features: ${pkg.docs[3].stages.at(-1).total}</p></div></article><article class="card"><div class="card-head"><div><p class="eyebrow">FIXED MODEL</p><h2>${esc(pkg.docs[4].default_configuration_id)}</h2></div>${badge(pkg.docs[4].status)}</div><div class="card-body"><p>${esc(pkg.docs[4].cv.protocol_id)} · ${pkg.docs[4].cv.fold_count} folds · candidate search disabled</p></div></article><article class="card"><div class="card-head"><div><p class="eyebrow">EVALUATION</p><h2>Development OOF</h2></div>${badge(evaluationDoc.publication_review === "PENDING" ? "PLANNED" : evaluationDoc.status)}</div><div class="card-body">${metrics}<p class="stage-note">OOF metrics are calculated and independently artifact-audited; research publication review remains pending.</p></div></article></div><div class="button-row" style="margin-top:18px">${PHASES.map(([n,,zh]) => `<a class="button" href="#phase-${n}">Phase ${n} · ${esc(zh)}</a>`).join("")}</div>`;
  }
  if (c.status === "PLANNED") return `<div class="state-panel"><h3>此案例尚無可用研究摘要</h3><p>Verified Research 僅讀取同一 Case Package。此 planned case 沒有可以展示的指標或圖表。</p>${badge("PLANNED")}</div>`;
  return `<div class="grid three"><article class="card"><div class="card-head"><div><p class="eyebrow">DATASET OVERVIEW</p><h2>${esc(c.title)}</h2></div>${badge("MOCK")}</div><div class="card-body"><p class="body-copy">Source: ${esc(c.source)}<br>Target: ${esc(c.target.column)} · ${esc(c.target.unit)}</p><p class="stage-note">Package publication not approved. This is a fixture preview, not Verified Research.</p></div></article><article class="card"><div class="card-head"><div><p class="eyebrow">FEATURE SELECTION</p><h2>Methods & configuration</h2></div>${badge("UNAVAILABLE")}</div><div class="card-body"><p class="body-copy">${c.methods.length} method definitions in the sample contract; ${c.configurations.length} eligible configurations.</p><p class="stage-note">No selected features, stability/frequency summaries or comparable method result is available.</p></div></article><article class="card"><div class="card-head"><div><p class="eyebrow">METRICS</p><h2>MAE · RMSE · R²</h2></div>${badge("UNAVAILABLE")}</div><div class="card-body"><div class="metrics"><span class="metric-value">—</span><span class="metric-value">—</span><span class="metric-value">—</span></div><p class="stage-note">No approved metric source. Scores are not calculated in the browser.</p></div></article></div><section class="card" style="margin-top:18px"><div class="card-head"><div><p class="eyebrow">VISUALIZATION</p><h2>Prediction versus actual · uncertainty</h2></div>${badge("UNAVAILABLE")}</div><div class="card-body"><div class="state-panel"><h3>No approved evaluation figure</h3><p>Actual-versus-predicted and confidence/prediction interval figures remain unavailable until evidence and publication review are complete.</p></div><div class="grid two" style="margin-top:16px"><p class="stage-note">Provenance: ${esc(SOURCE)}</p><p class="stage-note">Limitations: sample package is MOCK; files[] is empty and publication is not approved.</p></div></div></section>`;
}
function customPanel() {
  const sourceControls = `<div class="selector-row" role="group" aria-label="Dataset input source"><button type="button" class="selector-button" data-custom-source="file" aria-pressed="${state.customSource === "file"}">CSV upload</button><button type="button" class="selector-button" data-custom-source="url" aria-pressed="${state.customSource === "url"}">Direct URL</button></div>`;
  const input = state.customSource === "file"
    ? `<label class="control">Choose CSV file<input id="csv-file" type="file" accept=".csv,text/csv"></label><p class="stage-note">Local-only preview reads at most the first 64 KB. File contents stay in this browser and are not uploaded or saved.</p>`
    : `<label class="control">HTTPS CSV URL<input id="csv-url" type="url" placeholder="https://example.org/data.csv" value="${esc(state.customUrl)}"></label><p class="stage-note">Prototype validates URL format only. It does not fetch remote URLs.</p>`;
  const preview = state.customHeaders.length ? `<div class="control-row"><label class="control">Target<select id="custom-target"><option value="">Select target…</option>${state.customHeaders.map(h=>`<option value="${esc(h)}" ${state.targetField === h ? "selected" : ""}>${esc(h)}</option>`).join("")}</select></label><label class="control">Features<select id="custom-features" multiple size="4" aria-label="Select feature columns">${state.customHeaders.filter(h=>h!==state.targetField).map(h=>`<option value="${esc(h)}" ${state.featureFields.includes(h) ? "selected" : ""}>${esc(h)}</option>`).join("")}</select></label></div><div class="csv-preview"><table><thead><tr>${state.customHeaders.map(h=>`<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${state.customRows.map(row=>`<tr>${state.customHeaders.map((_,i)=>`<td>${esc(row[i] ?? "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>` : `<div class="state-panel"><h3>${esc(state.csvMessage)}</h3><p>Load a small CSV preview to choose a target and features. No training or evaluation is available in this prototype.</p></div>`;
  const validation = state.customValidated ? `<p class="stage-note" role="status">${state.csvMessage}</p>` : "";
  return `<div class="two-panel"><section class="card"><div class="card-head"><div><p class="eyebrow">CUSTOM DATASET · BROWSER-LOCAL ONLY</p><h2>載入並檢視資料</h2></div>${badge("MOCK")}</div><div class="card-body">${sourceControls}<div class="upload-zone" style="margin-top:15px">${input}<p class="stage-note" role="status">${esc(state.csvMessage)}</p></div>${preview}<div class="button-row" style="margin-top:15px"><button type="button" class="button" data-action="validate-custom" ${state.customHeaders.length ? "" : "disabled"}>Validate</button><button type="button" class="button primary" disabled title="Custom Run is not authorized">Run · DISABLED</button></div>${validation}</div></section><section class="card"><div class="card-head"><div><p class="eyebrow">CUSTOM DATA STATE</p><h2>Upload ≠ research case</h2></div>${badge("UNAVAILABLE")}</div><div class="card-body"><p class="body-copy">Custom input is isolated from Verified Research. Selecting a local file only previews its header and first rows in this page; changing mode clears the other mode's content.</p><dl class="data-row"><dt>Training / Evaluate</dt><dd>DISABLED — not authorized</dd></dl><dl class="data-row"><dt>Network request</dt><dd>None. Direct URL is format-checked only.</dd></dl><dl class="data-row"><dt>Persisted data</dt><dd>None</dd></dl></div></section></div>`;
}
function renderDashboard() {
  const c = caseData();
  return `<div class="page">${banner(c)}${pageHeading("INTEGRATED REGRESSION ANALYSIS", "Dashboard", "獨立的分析工作區。Verified Research 與 Custom Dataset 互斥；兩種模式不共享研究結果。", c.status)}<div class="mode-switch" role="group" aria-label="Dashboard mode"><button type="button" data-dashboard-mode="verified" aria-pressed="${state.dashboardMode === "verified"}">Verified Research</button><button type="button" data-dashboard-mode="custom" aria-pressed="${state.dashboardMode === "custom"}">Custom Dataset</button></div><div style="margin-top:18px">${state.dashboardMode === "verified" ? renderDashboardVerified() : customPanel()}</div><div class="button-row" style="margin-top:22px"><a class="button" href="#phase-1">← Back to CRISP-DM Home</a></div></div>`;
}
function render() {
  if (!referencePackage && !referencePackageError && !referencePackageLoading) loadReferencePackage();
  if (!explorationPackage && !explorationPackageError && !explorationPackageLoading) loadExplorationPackage();
  if (!carPackage && !carPackageError && !carPackageLoading) loadCarPackage();
  updateShell();
  const phase = routePhase();
  if (state.route === "home") app.innerHTML = renderHome();
  else if (state.route === "dashboard") app.innerHTML = renderDashboard();
  else if (phase && caseData().packageMode === "reference") app.innerHTML = renderReferencePackagePhase(phase);
  else if (phase && caseData().packageMode === "exploration") app.innerHTML = renderExplorationPackagePhase(phase);
  else if (phase && caseData().packageMode === "car") app.innerHTML = renderCarPackagePhase(phase);
  else if (phase === 1) app.innerHTML = renderPhase1();
  else if (phase === 2) app.innerHTML = renderPhase2();
  else if (phase === 3) app.innerHTML = renderPhase3();
  else if (phase === 4) app.innerHTML = renderPhase4();
  else if (phase === 5) app.innerHTML = renderPhase5();
  else if (phase === 6) app.innerHTML = renderPhase6();
  else { state.route = "home"; app.innerHTML = renderHome(); }
}
function csvRows(text) {
  const rows = []; let row = []; let cell = ""; let quoted = false;
  for (let i=0;i<text.length;i++) {
    const char = text[i];
    if (char === '"' && quoted && text[i+1] === '"') { cell += '"'; i++; }
    else if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) { row.push(cell); cell = ""; }
    else if ((char === "\n" || char === "\r") && !quoted) { if (char === "\r" && text[i+1] === "\n") i++; row.push(cell); if (row.some(v=>v.trim())) rows.push(row); row = []; cell = ""; }
    else cell += char;
  }
  if (cell || row.length) { row.push(cell); if (row.some(v=>v.trim())) rows.push(row); }
  return rows;
}
function resetCustom() {
  state.customFile = null; state.customHeaders = []; state.customRows = []; state.customUrl = "";
  state.targetField = ""; state.featureFields = []; state.customValidated = false;
  state.csvMessage = "尚未載入資料。CSV 僅在此瀏覽器本機預覽，不會上傳。";
}
function routeFromHash() {
  const raw = location.hash.replace(/^#/, "") || "home";
  if (raw === "home") state.route = "home";
  else if (raw === "dashboard") state.route = "dashboard";
  else if (/^phase-[1-6]$/.test(raw)) state.route = raw;
  else state.route = "home";
  render();
}

caseSelect.addEventListener("change", () => {
  state.caseId = caseSelect.value;
  state.analysisId = CASES[state.caseId].analyses?.[0]?.id || "";
  state.referenceAnalysisId = state.caseId === CAR_CASE_ID ? (carPackage?.docs[2]?.default_analysis_id || "field-decisions") : "figure-field-decisions";
  state.referenceEvaluationId = "initb-development-e2e-20261028-02.development-oof.cv-mean";
  state.referenceFigureId = "FIG-P5-01";
  state.explorationP5Figure = "FIG-P5-01";
  state.explorationMode = "comparison";
  state.explorationPerspective = "selected_features";
  const selectedExplorationPackage = state.caseId === CAR_CASE_ID ? carPackage : explorationPackage;
  state.explorationConfigurationId = selectedExplorationPackage?.docs[4]?.default_configuration_id || "";
  state.explorationMethodId = selectedExplorationPackage?.docs[4]?.configurations.find((item) => item.configuration_id === state.explorationConfigurationId)?.method_id || "";
  state.phase5ConfigId = "";
  state.perspective = "method_comparison"; state.phase5Figure = "FIG-P5-02";
  state.p5Population = "development_oof"; state.phase6MockSubmitted = false; state.phase6InputMode = "manual"; state.phase6Csv = null; state.phase6Values = { neighborhood: "CollgCr", quality: "6", bedrooms: "3", area: "1800" }; resetCustom(); render();
});
window.addEventListener("hashchange", () => {
  routeFromHash();
  if (/^#phase-[1-6]$/.test(location.hash)) window.scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
});
app.addEventListener("click", (event) => {
  const target = event.target.closest("button[data-action],button[data-analysis],button[data-perspective],button[data-p5-figure],button[data-dashboard-mode],button[data-custom-source],button[data-phase6-mode],button[data-reference-analysis],button[data-reference-evaluation],button[data-reference-figure],button[data-exploration-p5-figure],button[data-exploration-mode],button[data-exploration-perspective],button[data-exploration-metric-source],button[data-exploration-open-method]");
  if (!target) return;
  if (target.dataset.referenceAnalysis) { state.referenceAnalysisId = target.dataset.referenceAnalysis; render(); }
  else if (target.dataset.explorationMode) { state.explorationMode = target.dataset.explorationMode; render(); }
  else if (target.dataset.explorationOpenMethod) {
    state.explorationMode = "explorer";
    state.explorationMethodId = target.dataset.explorationOpenMethod;
    const pkg = activeExplorationPackage();
    const config = pkg?.docs[4]?.configurations.find((item) => item.configuration_id === target.dataset.explorationOpenConfiguration)
      || (pkg ? explorationDefaultConfigForMethod(pkg, state.explorationMethodId) : null);
    state.explorationConfigurationId = config?.configuration_id || "";
    state.explorationPerspective = "selected_features";
    if (config?.status === "VERIFIED") loadExplorationConfigurationArtifacts(pkg, config).then(render).catch((error) => { if (caseData().packageMode === "car") carPackageError = error.message; else explorationPackageError = error.message; render(); });
    render();
  }
  else if (target.dataset.explorationPerspective) { state.explorationPerspective = target.dataset.explorationPerspective; render(); }
  else if (target.dataset.explorationP5Figure) { state.explorationP5Figure = target.dataset.explorationP5Figure; render(); }
  else if (target.dataset.explorationMetricSource) { state.explorationMetricSource = target.dataset.explorationMetricSource; render(); }
  else if (target.dataset.referenceEvaluation) { state.referenceEvaluationId = target.dataset.referenceEvaluation; state.referenceFigureId = "FIG-P5-02"; render(); }
  else if (target.dataset.referenceFigure) { state.referenceFigureId = target.dataset.referenceFigure; render(); }
  else if (target.dataset.phase6Mode) { state.phase6InputMode = target.dataset.phase6Mode; render(); }
  else if (target.dataset.action === "phase6-use-csv-row") {
    const csv = state.phase6Csv; const row = csv?.rows[csv.selectedIndex] || [];
    const value = (name) => { const index = csv?.headers.indexOf(name) ?? -1; return index < 0 ? null : row[index]?.trim() ?? ""; };
    const neighborhood = value("Neighborhood"); const quality = value("OverallQual"); const bedrooms = value("BedroomAbvGr"); const area = value("GrLivArea");
    if (neighborhood && AMES_NEIGHBORHOODS.includes(neighborhood)) state.phase6Values.neighborhood = neighborhood;
    if (quality && Number(quality) >= 1 && Number(quality) <= 10) state.phase6Values.quality = String(Number(quality));
    if (bedrooms !== null && bedrooms !== "" && Number.isInteger(Number(bedrooms)) && Number(bedrooms) >= 0 && Number(bedrooms) <= 8) state.phase6Values.bedrooms = String(Number(bedrooms));
    if (area && Number(area) >= 334 && Number(area) <= 5642) state.phase6Values.area = String(Number(area));
    state.phase6InputMode = "manual"; state.phase6MockSubmitted = false; render();
  }
  else if (target.dataset.analysis) { state.analysisId = target.dataset.analysis; render(); }
  else if (target.dataset.perspective) { state.perspective = target.dataset.perspective; render(); }
  else if (target.dataset.p5Figure) { state.phase5Figure = target.dataset.p5Figure; render(); }
  else if (target.dataset.action === "phase6-mock-preview") { state.phase6MockSubmitted = true; render(); }
  else if (target.dataset.dashboardMode) { state.dashboardMode = target.dataset.dashboardMode; resetCustom(); render(); }
  else if (target.dataset.customSource) { state.customSource = target.dataset.customSource; resetCustom(); render(); }
  else if (target.dataset.action === "validate-custom") {
    const valid = state.customHeaders.length > 0 && state.targetField && state.featureFields.length > 0 && !state.featureFields.includes(state.targetField);
    state.customValidated = true;
    state.csvMessage = valid ? "Validation passed for selected columns. Run remains disabled; no model was trained." : "Choose one target and at least one distinct feature before validation.";
    render();
  }
});
app.addEventListener("change", (event) => {
  if (event.target.id === "p6-csv-file") {
    const file = event.target.files?.[0]; if (!file) return;
    state.phase6Csv = null; state.phase6MockSubmitted = false;
    if (!file.name.toLowerCase().endsWith(".csv") || file.size === 0 || file.size > 20 * 1024 * 1024) { state.phase6CsvMessage = "請選擇非空且小於 20 MB 的 .csv 檔案。Choose a non-empty CSV under 20 MB."; render(); return; }
    const reader = new FileReader();
    reader.onload = () => {
      const parsed = csvRows(String(reader.result || "").replace(/^\uFEFF/, ""));
      if (parsed.length < 2 || !parsed[0].some((cell) => cell.trim())) { state.phase6CsvMessage = "CSV 需要標題列與至少一筆資料。CSV needs a header and at least one data row."; }
      else {
        const headers = parsed[0].map((cell,index) => cell.trim() || `Column ${index+1}`);
        if (new Set(headers).size !== headers.length) state.phase6CsvMessage = "欄名重複，請先整理 CSV 標題列。Duplicate column names; please make headers unique.";
        else { state.phase6Csv = { fileName: file.name, headers, rows: parsed.slice(1).map((row)=>headers.map((_,i)=>row[i]??"")), selectedIndex: 0 }; state.phase6CsvMessage = "CSV 已載入本機預覽。CSV loaded for local preview."; }
      }
      render();
    };
    reader.onerror = () => { state.phase6CsvMessage = "無法讀取此本機檔案。Unable to read local file."; render(); };
    reader.readAsText(file);
  } else if (event.target.id === "p6-csv-row") { if (state.phase6Csv) state.phase6Csv.selectedIndex = Number(event.target.value); render(); }
  else if (event.target.id === "csv-file") {
    const file = event.target.files?.[0]; if (!file) return;
    state.customFile = file.name; state.customHeaders = []; state.customRows = []; state.targetField = ""; state.featureFields = []; state.customValidated = false;
    if (!file.name.toLowerCase().endsWith(".csv") || file.size === 0) { state.csvMessage = "Please choose a non-empty .csv file."; render(); return; }
    const reader = new FileReader();
    reader.onload = () => {
      const rows = csvRows(String(reader.result || ""));
      if (rows.length < 2 || !rows[0].some(cell => cell.trim())) { state.csvMessage = "No header and sample rows could be read from this CSV preview."; }
      else { state.customHeaders = rows[0].map((cell, index) => cell.trim() || `Column ${index+1}`); state.customRows = rows.slice(1, 7).map(row => state.customHeaders.map((_,i)=>row[i] ?? "")); state.csvMessage = `Local preview ready · ${state.customHeaders.length} columns · first ${state.customRows.length} data rows. File is not uploaded.`; }
      render();
    };
    reader.onerror = () => { state.csvMessage = "Unable to read this local file."; render(); };
    reader.readAsText(file.slice(0, 65536));
  } else if (event.target.id === "custom-target") { state.targetField = event.target.value; state.featureFields = state.featureFields.filter(field => field !== state.targetField); state.customValidated = false; }
  else if (event.target.id === "custom-features") { state.featureFields = [...event.target.selectedOptions].map(option => option.value); state.customValidated = false; }
  else if (event.target.id === "csv-url") { state.customUrl = event.target.value; state.customValidated = false; }
  else if (["p6-neighborhood","p6-overall-quality","p6-bedroom-count","p6-living-area"].includes(event.target.id)) {
    const map = { "p6-neighborhood": "neighborhood", "p6-overall-quality": "quality", "p6-bedroom-count": "bedrooms", "p6-living-area": "area" };
    state.phase6Values[map[event.target.id]] = event.target.value;
  }
  else if (event.target.id === "p4-run") { state.phase4RunId = event.target.value; render(); }
  else if (event.target.id === "p5-population") { state.p5Population = event.target.value; render(); }
  else if (event.target.id === "p5-config") { state.phase5ConfigId = event.target.value; render(); }
  else if (event.target.id === "exploration-method") {
    state.explorationMethodId = event.target.value;
    const pkg = activeExplorationPackage();
    const config = pkg ? explorationDefaultConfigForMethod(pkg, state.explorationMethodId) : null;
    state.explorationConfigurationId = config?.configuration_id || "";
    if (config && config.status === "VERIFIED") loadExplorationConfigurationArtifacts(pkg, config).then(render).catch((error) => { if (caseData().packageMode === "car") carPackageError = error.message; else explorationPackageError = error.message; render(); });
    render();
  }
  else if (event.target.id === "exploration-config" || event.target.id === "exploration-p5-config") {
    state.explorationConfigurationId = event.target.value;
    const pkg = activeExplorationPackage();
    const config = pkg?.docs[4]?.configurations.find((item) => item.configuration_id === state.explorationConfigurationId);
    if (config) {
      state.explorationMethodId = config.method_id;
      if (config.status === "VERIFIED") loadExplorationConfigurationArtifacts(pkg, config).then(render).catch((error) => { if (caseData().packageMode === "car") carPackageError = error.message; else explorationPackageError = error.message; render(); });
    }
    render();
  }
});
app.addEventListener("input", (event) => {
  if (event.target.id === "csv-url") {
    state.customUrl = event.target.value; state.customValidated = false;
    const urlOk = /^https:\/\//i.test(state.customUrl);
    state.csvMessage = urlOk ? "HTTPS URL format accepted; remote loading is disabled in this prototype." : "Enter an HTTPS URL. Remote loading is disabled in this prototype.";
    const status = app.querySelector(".upload-zone [role=status]"); if (status) status.textContent = state.csvMessage;
  } else if (event.target.id === "p6-overall-quality") {
    const output = app.querySelector("#p6-quality-output");
    if (output) output.textContent = qualityScaleLabel(event.target.value);
  }
});

if (!location.hash) location.hash = "home";
routeFromHash();
