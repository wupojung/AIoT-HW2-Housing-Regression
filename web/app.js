const SOURCE = "PR #35 HEAD 8d2bc4405e08e1a1b982204984f681d90975956a";
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
  ["nominal", "名目 (Nominal)", "#b9d6c4"],
  ["ordinal", "次序 (Ordinal)", "#cadba6"],
  ["discrete", "離散 (Discrete)", "#b9cedd"],
  ["continuous", "連續 (Continuous)", "#e8d39a"]
];
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

const state = {
  caseId: "ames-housing", route: "home", analysisId: "overview", perspective: "method_comparison",
  phase4RunId: "MOCK-RUN-02",
  phase5Figure: "FIG-P5-02", p5Population: "development_oof", p5DetailsOpen: false,
  dashboardMode: "verified", customSource: "file", customFile: null, customUrl: "", customHeaders: [], customRows: [],
  targetField: "", featureFields: [], csvMessage: "尚未載入資料。CSV 僅在此瀏覽器本機預覽，不會上傳。", customValidated: false
};
const app = document.querySelector("#app");
const phaseNav = document.querySelector("#phase-nav");
const caseContext = document.querySelector("#case-context");
const caseSelect = document.querySelector("#case-select");

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}
function statusLabel(status) {
  const labels = { MOCK: "示意資料 MOCK", UNAVAILABLE: "無可用資料 UNAVAILABLE", PLANNED: "規劃中 PLANNED", VERIFIED: "已驗證 VERIFIED", ERROR: "錯誤 ERROR", SOURCE_REPORTED_NOT_VERIFIED: "來源回報・尚未驗證 SOURCE REPORTED · NOT VERIFIED" };
  return labels[status] || status || "未知 UNKNOWN";
}
function statusClass(status) {
  return ({ MOCK: "mock", UNAVAILABLE: "unavailable", PLANNED: "planned", VERIFIED: "verified", ERROR: "error", SOURCE_REPORTED_NOT_VERIFIED: "mock" })[status] || "unavailable";
}
function badge(status) { return `<span class="status ${statusClass(status)}">${esc(statusLabel(status))}</span>`; }
function caseData() { return CASES[state.caseId] || CASES["planned-case"]; }
function isPhaseRoute() { return state.route.startsWith("phase-"); }
function routePhase() { return isPhaseRoute() ? Number(state.route.slice(6)) || 1 : 0; }
function setRoute(route) { location.hash = route; }
function setPhase(phase) { setRoute(`phase-${phase}`); }
function banner(caseInfo = caseData()) {
  const reason = caseInfo.status === "MOCK"
    ? `UI fixture only · package revision ${caseInfo.packageRevision} · ${SOURCE}. These values are not approved research results.`
    : "Planned placeholder only · no research package, data, or model is available.";
  return `<div class="fixture-banner"><span><strong>${caseInfo.status === "MOCK" ? "Fixture preview" : "Planned case"}</strong> · ${esc(reason)}</span>${badge(caseInfo.status)}</div>`;
}
function updateShell() {
  const phase = routePhase();
  caseContext.hidden = !phase || state.route === "home" || state.route === "dashboard";
  phaseNav.hidden = !phase || state.route === "home" || state.route === "dashboard";
  phaseNav.innerHTML = PHASES.map(([n, en, zh]) => `<a class="phase-tab" href="#phase-${n}" ${phase === n ? 'aria-current="page"' : ""}><span class="num">0${n}</span><span class="phase-zh">${esc(zh)}</span><span class="phase-en">${esc(en)}</span></a>`).join("");
  document.querySelector("[data-home-link]").setAttribute("aria-current", state.route === "home" ? "page" : "false");
  document.querySelector("[data-crisp-link]").setAttribute("aria-current", phase ? "page" : "false");
  document.querySelector("[data-dashboard-link]").setAttribute("aria-current", state.route === "dashboard" ? "page" : "false");
  caseSelect.innerHTML = Object.values(CASES).map((c) => `<option value="${esc(c.id)}" ${c.id === state.caseId ? "selected" : ""}>${esc(c.title)} · ${esc(c.status)}</option>`).join("");
}
function pageHeading(kicker, title, subtitle, status = caseData().status) {
  return `<div class="page-heading"><div><p class="kicker">${esc(kicker)}</p><h1>${esc(title)}</h1><p class="lede">${esc(subtitle)}</p></div><div class="page-meta">${badge(status)}</div></div>`;
}
function footerNav(prev, next) {
  const phase = routePhase();
  const samplePath = phase === 3
    ? "web/data/cases/ames-housing/phase-03/preparation.json"
    : REF[`phase${phase}`];
  const schemaPath = phase === 5
    ? "docs/ui-ux/case-package/phase-05/evaluation-index.schema.json"
    : `docs/design/data-contracts/schemas/phase-0${phase}.schema.json`;
  const fileUrl = (path) => `https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/8d2bc4405e08e1a1b982204984f681d90975956a/${path}`;
  const source = `<div class="source-note"><span>Fixture / contract provenance · ${esc(SOURCE)}</span><a href="${fileUrl(samplePath)}" target="_blank" rel="noreferrer">Sample JSON ↗</a><a href="${fileUrl(schemaPath)}" target="_blank" rel="noreferrer">Schema ↗</a></div>`;
  return `${source}<nav class="phase-footer" aria-label="前後階段">${prev ? `<a class="button" href="#phase-${prev[0]}">← ${esc(prev[1])}</a>` : `<span></span>`}${next ? `<a class="button primary" href="#phase-${next[0]}">${esc(next[1])} →</a>` : `<span></span>`}</nav>`;
}
function plannedPanel(message = "此案例目前沒有可用的研究資料。") {
  return `<section class="state-panel"><span class="state-icon" aria-hidden="true">i</span><h3>此階段尚未提供資料</h3><p>${esc(message)}切換至此案例不會沿用 Ames 的文字、圖表或狀態。</p>${badge("PLANNED")}</section>`;
}
function renderHome() {
  const c = caseData();
  return `<div class="page">${banner(c)}<section class="home-hero"><div><p class="kicker">NCHU AIoT 2026 · HOUSING REGRESSION LAB</p><h1>從研究問題<br>走向可追溯的證據</h1><p>以清楚可追溯的方式呈現住宅迴歸研究。進入 CRISP-DM，從案例與研究問題開始。</p><a class="button" href="#phase-1">CRISP-DM →</a></div></section></div>`;
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
const PHASE3_DATA_URL = "/data/cases/ames-housing/phase-03/preparation.json";
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
      if (state.route === "phase-3" && state.caseId === "ames-housing") render();
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
    return `<section class="stage-card"><div class="stage-head"><div class="stage-title"><span class="index">0${index + 1}</span><h2>${esc(stage.label)}</h2></div><span class="stage-total">總數 Total: ${stage.total == null ? "未知 Unknown" : esc(stage.total)} ${esc(unit)} ${badge(stage.total_status)}</span></div>${renderSegments(stage, data.feature_types)}<p class="stage-note">${esc(note)}</p>${exclusions}${treatmentAccordion}${lineage}</section>`;
  }).join("");
  const split = data.split;
  const totalRows = split.source_labeled_rows;
  const splitReady = Number.isInteger(totalRows) && totalRows > 0
    && Number.isInteger(split.training_rows) && Number.isInteger(split.holdout_rows)
    && split.training_rows >= 0 && split.holdout_rows >= 0
    && split.training_rows + split.holdout_rows === totalRows;
  const splitContent = splitReady
    ? `<p class="body-copy">來源回報的資料切分 (data split)：${split.training_rows} / ${totalRows} 訓練集 (Training Set) · ${split.holdout_rows} / ${totalRows} 保留測試集 (Holdout Test Set) · 隨機種子 (Random Seed) ${split.seed ?? "未知 UNKNOWN"}。比例依來源回報呈現，尚未驗證。</p><div class="row-split" role="img" aria-label="來源回報切分比例：訓練集 Training Set ${Math.round(split.training_rows / totalRows * 100)}%，保留測試集 Holdout Test Set ${Math.round(split.holdout_rows / totalRows * 100)}%"><span style="width:${split.training_rows / totalRows * 100}%">訓練集 Training Set · ${split.training_rows} 筆 rows · ${Math.round(split.training_rows / totalRows * 100)}%</span><span style="width:${split.holdout_rows / totalRows * 100}%">保留測試 Holdout Test Set · ${split.holdout_rows} 筆 rows · ${Math.round(split.holdout_rows / totalRows * 100)}%</span></div><p class="stage-note">第 4 階段交叉驗證 (Cross-validation, CV) 僅使用訓練集；不把保留測試集當成第 4 階段結果。</p>`
    : `<div class="state-panel"><h3>資料不可用 UNAVAILABLE — 切分資料列數不一致 split row counts do not reconcile。</h3><p>來源列數完整且加總相符前，不顯示切分比例 No split proportion is drawn unless source counts are complete and sum to the labeled row total.</p></div>`;
  return `<div class="page">${banner(c)}${pageHeading("PHASE 03 / DATA PREPARATION", "資料準備", "四個特徵處理階段 (feature preparation stages)，接續獨立的資料列切分 (row split)。", data.status)}<div class="stage-list">${stages}<section class="card"><div class="card-head"><div><p class="eyebrow">資料集切分 DATASET PARTITION · 切分資料列，不是特徵 ROWS, NOT FEATURES</p><h2>訓練集與保留測試集 Training and holdout test sets</h2></div>${badge(split.status)}</div><div class="card-body">${splitContent}</div></section></div>${footerNav([2,"資料理解"],[4,"模型建立"])}</div>`;
}

function renderPhase4() {
  const c = caseData();
  if (c.status === "PLANNED") return `<div class="page">${banner(c)}${pageHeading("PHASE 04 / MODELING", "模型建立", "只呈現實際完成且可核對的模型實驗。", "PLANNED")}${plannedPanel()}${footerNav([3,"資料準備"],[5,"模型評估"])}</div>`;
  const foldNames = ["Fold A", "Fold B", "Fold C"];
  const folds = Array.from({ length: 3 }, (_, iteration) => {
    const blocks = foldNames.map((foldName, foldIndex) => {
      const isValidation = foldIndex === iteration;
      const role = isValidation ? "Validation" : "Training";
      return `<span class="${isValidation ? "cv-valid" : "cv-train"}" style="width:33.333%">${foldName} · ${role}</span>`;
    }).join("");
    return `<div class="cv-row"><span class="cv-label">CV iteration ${iteration + 1}</span><div class="cv-track" role="img" aria-label="CV iteration ${iteration + 1}: ${foldNames.map((name, index) => `${name} ${index === iteration ? "validation" : "training"}`).join(", ")}">${blocks}</div></div>`;
  }).join("");
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
  return `<div class="page">${banner(c)}${pageHeading("PHASE 04 / MODELING", "模型建立與特徵選擇", "以下模型與分數是合成 UI 示意，僅供檢視頁面功能，不代表實際實驗。", "MOCK")}<section class="card"><div class="card-head"><div><p class="eyebrow">01 · 三折交叉驗證 3-FOLD CROSS-VALIDATION</p><h2>訓練集專用 Training Set only</h2></div>${badge(c.cv.status)}</div><div class="cv-block"><p class="body-copy">訓練集 Training Set：${c.cv.trainingRows} 筆來源回報資料列 source-reported rows · 折數 Fold count：${c.cv.foldCount} · 評估指標 Metric：均方根誤差 RMSE (root mean squared error)，越低越好。</p>${folds}<div class="legend"><span class="legend-item"><i class="legend-dot" style="--dot:#d8e5ec"></i>訓練折 Training folds</span><span class="legend-item"><i class="legend-dot" style="--dot:#b9d8c8"></i>驗證折輪替 Validation fold rotates</span></div><p class="stage-note">示意圖 Schematic only · 每列顯示三個近似等寬資料折 (folds)。實際折數與流程設定未確認。保留測試集 Holdout Test Set (292 筆來源回報資料列) 不參與此交叉驗證。</p><details class="disclosure"><summary>展開交叉驗證方法 Cross-validation methodology</summary><div class="disclosure-body">此處的模型比較分數是合成 UI mock。實際切分器、亂序、隨機種子、折內數量與資料隔離流程仍未知。</div></details></div></section><section class="card explorer"><div class="card-head"><div><p class="eyebrow">02 · 特徵選擇與模型瀏覽器 FEATURE SELECTION & MODEL EXPLORER</p><h2>切換示意研究視角 Choose a mock view</h2></div>${badge("MOCK")}</div><div class="card-body"><div class="selector-row" role="group" aria-label="研究視角 Research perspective">${perspectives}</div><div class="control-row"><label class="control">特徵選擇方法 Feature-selection method<select disabled><option>合成配置 Synthetic configuration</option>${methodOptions}</select></label><label class="control">示意執行 Mock run<select id="p4-run">${runOptions}</select></label></div><section class="mock-result-panel"><div class="mock-result-head"><strong>${state.perspective === "method_comparison" ? "方法比較 Method comparison" : state.perspective === "selected_features" ? "選取特徵 Selected features" : "特徵數與交叉驗證分數 Feature count vs cross-validation score"}</strong>${badge("MOCK")}</div>${mockPanel}</section><p class="stage-note">所有數值、特徵名稱及配置都是人工合成的 UI 示意；不能當成實際模型結果。 All metrics, features, and configurations are synthetic UI fixtures.</p><div class="button-row" style="margin-top:18px"><a class="button" href="#phase-5">查看 Phase 5 評估狀態 →</a><a class="button" href="#phase-6">查詢 Phase 6 模型就緒狀態 →</a></div></div></section>${footerNav([3,"資料準備"],[5,"模型評估"])}</div>`;
}
function renderPhase5() {
  const c = caseData();
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
  const metricCards = [["MAE 平均絕對誤差", metrics.mae, "USD · 越低越好 Lower is better"], ["RMSE 均方根誤差", metrics.rmse, "USD · 越低越好 Lower is better"], ["R² 決定係數", metrics.r2.toFixed(2), "無單位 Dimensionless"]].map(([name, value, note]) => `<article class="metric-card"><span class="metric-label">${name}</span><strong class="metric-value">${typeof value === "number" ? value.toLocaleString() : value}</strong><span class="metric-note">合成示意 MOCK · ${note}</span></article>`).join("");
  const chartTable = predictionPoints.map((point, i) => `<tr><td>${i + 1}</td><td>${point.actual.toLocaleString()}</td><td>${point.predicted.toLocaleString()}</td><td>${residuals[i].toLocaleString()}</td></tr>`).join("");
  return `<div class="page">${banner(c)}${pageHeading("PHASE 05 / MODEL EVALUATION", "模型評估", "以下指標與圖表為合成 UI 示意，只用來預覽評估頁面，不代表實際模型評估結果。", "MOCK")}<section class="card"><div class="card-head"><div><p class="eyebrow">01 · 評估範圍與識別 EVALUATION CONTEXT</p><h2>評估設定與身分 Evaluation setup and identity</h2></div>${badge("MOCK")}</div><div class="card-body grid two"><div><dl class="data-row"><dt>示意配置 Mock configuration</dt><dd>${esc(mock.configId)}</dd></dl><dl class="data-row"><dt>示意執行 Mock execution</dt><dd>${esc(mock.runId)}</dd></dl><dl class="data-row"><dt>示意評估 Mock evaluation</dt><dd>${esc(mock.evaluationId)}</dd></dl></div><div><label class="control">評估母體 Evaluation population<select id="p5-population"><option value="development_oof" ${!holdout ? "selected" : ""}>開發資料 OOF Development OOF</option><option value="holdout" ${holdout ? "selected" : ""}>保留測試集 Holdout</option></select></label><p class="stage-note">母體切換會顯示不同的合成示意數值；無真實評估資料。Population switch changes mock values only.</p></div></div></section><div class="metrics" style="margin-top:18px">${metricCards}</div><section class="card explorer"><div class="card-head"><div><p class="eyebrow">03 · 核心診斷圖 Core diagnostics</p><h2>${esc(c.evaluation.figures.find(([id]) => id === state.phase5Figure)?.[1] || "Residual vs Predicted")}</h2></div>${badge("MOCK")}</div><div class="card-body"><div class="selector-row" role="group" aria-label="診斷圖選擇 Diagnostic figure">${figures}</div><div class="mock-figure" style="margin-top:16px">${mockChart}</div><table class="mock-data-table"><thead><tr><th>示意列 Mock row</th><th>實際值 Actual (USD)</th><th>預測值 Predicted (USD)</th><th>殘差 Residual (USD)</th></tr></thead><tbody>${chartTable}</tbody></table><p class="stage-note">六筆合成資料列 Synthetic rows · 僅供繪圖預覽，不是實際觀測值。</p></div></section><div class="grid two" style="margin-top:18px"><section class="card"><div class="card-head"><div><p class="eyebrow">04 · 信賴區間與預測區間 CONFIDENCE / PREDICTION INTERVAL</p><h2>合成區間示意 Mock interval illustration</h2></div>${badge("MOCK")}</div><div class="card-body"><dl class="data-row"><dt>示意方法 Mock method</dt><dd>${esc(mock.intervals.method)}</dd></dl><dl class="data-row"><dt>示意區間 Mock range</dt><dd>${mock.intervals.lower.toLocaleString()}–${mock.intervals.upper.toLocaleString()} USD</dd></dl><dl class="data-row"><dt>示意涵蓋率 Mock coverage</dt><dd>${Math.round(mock.intervals.coverage * 100)}%</dd></dl><p class="stage-note">此區間與涵蓋率均為合成值，不具統計推論效力。Synthetic values; no inferential claim.</p></div></section><section class="card"><div class="card-head"><div><p class="eyebrow">05 · 可追溯性 TRACEABILITY</p><h2>來源、方法與限制 Source, method, and limits</h2></div>${badge("MOCK")}</div><div class="card-body"><p class="body-copy">此頁評估 ID、樣本數、預測值與圖表都為合成 UI 資料；沒有連結到真實研究執行或已發布證據。</p><p class="stage-note">Evaluation identity, samples, predictions and figures are synthetic fixtures; no published evidence is linked.</p></div></section></div>${footerNav([4,"返回模型建立"],[6,"模型就緒狀態"])}</div>`;
}
function renderPhase6() {
  const c = caseData();
  if (c.status === "PLANNED") return `<div class="page">${banner(c)}${pageHeading("PHASE 06 / MODEL PREDICTION LAB", "房價預測實驗室", "單筆推論需要通過核准的模型、輸入 Schema 與已部署 API。", "PLANNED")}${plannedPanel(c.inference.message)}${footerNav([5,"模型評估"],null)}</div>`;
  return `<div class="page">${banner(c)}${pageHeading("PHASE 06 / MODEL PREDICTION LAB", "房價預測實驗室", "使用已註冊且核准的模型進行單筆推論。此 prototype 沒有 ready model、raw-input schema 或 inference API。", "UNAVAILABLE")}<section class="card"><div class="card-head"><div><p class="eyebrow">CASE / RUN CONTEXT</p><h2>${esc(c.title)}</h2></div>${badge("MOCK")}</div><div class="card-body grid three"><dl class="data-row"><dt>Target</dt><dd>${esc(c.target.label)} · ${esc(c.target.unit)}</dd></dl><dl class="data-row"><dt>Research run</dt><dd>UNAVAILABLE — no eligible configuration</dd></dl><dl class="data-row"><dt>Model selector</dt><dd><label class="control"><span class="sr-only">Registered model</span><select disabled><option>沒有核准的模型</option></select></label></dd></dl></div></section><div class="two-panel" style="margin-top:18px"><section class="card"><div class="card-head"><div><p class="eyebrow">MODEL-SPECIFIC RAW INPUT SCHEMA</p><h2>輸入住宅條件</h2></div>${badge("UNAVAILABLE")}</div><div class="card-body"><div class="state-panel"><span class="state-icon" aria-hidden="true">i</span><h3>目前不提供輸入欄位</h3><p>No approved registered model or model-specific input schema is available. The UI will not guess fields or request encoded features.</p></div><div class="button-row" style="margin-top:14px"><button class="button" type="button" disabled>Validate Inputs</button><button class="button primary" type="button" disabled>Predict</button></div></div></section><section class="card"><div class="card-head"><div><p class="eyebrow">PREDICTION RESULT</p><h2>預測結果</h2></div>${badge("UNAVAILABLE")}</div><div class="card-body"><div class="model-state"><p class="eyebrow">MODEL READINESS</p><h2>此模型尚未準備好</h2><p>${esc(c.inference.message)}</p><dl class="data-row"><dt>Readiness reason</dt><dd>${esc(c.inference.reasonCode)}</dd></dl><dl class="data-row"><dt>Prediction interval</dt><dd>UNAVAILABLE — no approved interval method</dd></dl><dl class="data-row"><dt>API status</dt><dd>API_NOT_DEPLOYED</dd></dl></div><p class="stage-note">研究 CV、部署模型和預測服務是不同狀態。此頁不會訓練模型或呼叫 API。</p><div class="button-row" style="margin-top:14px"><button class="button" type="button" disabled>選擇其他可用模型</button><a class="button primary" href="#phase-4">返回 Phase 4 Modeling →</a></div></div></section></div><section class="card" style="margin-top:18px"><div class="card-body"><p class="eyebrow">PROVENANCE & LIMITATIONS</p><p class="body-copy">Case ID: ${esc(c.id)} · Model registry: ${esc(c.inference.reasonCode)} · Model artifact, fitted pipeline, raw input schema, publication review, API deployment and QA are not available.</p><a class="text-link" href="#phase-5">查看 Phase 5 evaluation 狀態 →</a></div></section>${footerNav([5,"模型評估"],null)}</div>`;
}
function renderDashboardVerified() {
  const c = caseData();
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
  updateShell();
  const phase = routePhase();
  if (state.route === "home") app.innerHTML = renderHome();
  else if (state.route === "dashboard") app.innerHTML = renderDashboard();
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
  state.analysisId = CASES[state.caseId].analyses[0]?.id || "";
  state.perspective = "method_comparison"; state.phase5Figure = "FIG-P5-02";
  state.p5Population = "development_oof"; resetCustom(); render();
});
window.addEventListener("hashchange", routeFromHash);
app.addEventListener("click", (event) => {
  const target = event.target.closest("button[data-action],button[data-analysis],button[data-perspective],button[data-p5-figure],button[data-dashboard-mode],button[data-custom-source]");
  if (!target) return;
  if (target.dataset.analysis) { state.analysisId = target.dataset.analysis; render(); }
  else if (target.dataset.perspective) { state.perspective = target.dataset.perspective; render(); }
  else if (target.dataset.p5Figure) { state.phase5Figure = target.dataset.p5Figure; render(); }
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
  if (event.target.id === "csv-file") {
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
  else if (event.target.id === "p4-run") { state.phase4RunId = event.target.value; render(); }
  else if (event.target.id === "p5-population") { state.p5Population = event.target.value; render(); }
});
app.addEventListener("input", (event) => {
  if (event.target.id === "csv-url") {
    state.customUrl = event.target.value; state.customValidated = false;
    const urlOk = /^https:\/\//i.test(state.customUrl);
    state.csvMessage = urlOk ? "HTTPS URL format accepted; remote loading is disabled in this prototype." : "Enter an HTTPS URL. Remote loading is disabled in this prototype.";
    const status = app.querySelector(".upload-zone [role=status]"); if (status) status.textContent = state.csvMessage;
  }
});

if (!location.hash) location.hash = "home";
routeFromHash();
