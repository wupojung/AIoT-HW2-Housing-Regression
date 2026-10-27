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
  ["nominal", "Nominal 名目", "#b9d6c4"],
  ["ordinal", "Ordinal 次序", "#cadba6"],
  ["discrete", "Discrete 離散", "#b9cedd"],
  ["continuous", "Continuous 連續", "#e8d39a"]
];
const CASES = {
  "ames-housing": {
    id: "ames-housing", title: "Ames Housing — MOCK UI Sample", status: "MOCK",
    source: "Kaggle House Prices", sourceUrl: "https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data",
    license: "PENDING", target: { column: "SalePrice", label: "售價", unit: "USD" },
    methodology: "mlr-feature-selection-v1", packageRevision: "sample-r1",
    sections: [
      { title: "研究問題", body: "示意：探索住宅條件與售價的關係。" },
      { title: "研究目標", body: "示意：展示多元線性迴歸與特徵選擇流程。" },
      { title: "限制", body: "本內容僅供 UI 渲染測試，不代表已驗證結果。" }
    ],
    analyses: [
      ["overview", "FIG-01", "資料集概覽"],
      ["missingness", "FIG-02", "缺失值分析"],
      ["saleprice", "FIG-03", "售價分布"],
      ["correlation", "FIG-06", "數值相關分析"]
    ].map(([id, figureId, title]) => ({ id, figureId, title, status: "UNAVAILABLE", imageRef: null, tableRef: null,
      description: "待綁定已核准圖資", finding: null,
      limitations: "圖資尚未通過此 Sample 的發布審查", provenanceRef: null })),
    stages: [
      { id: "raw", label: "原始候選欄位", unit: "原始欄位", total: 79, totalStatus: "SOURCE_REPORTED_NOT_VERIFIED", segments: [], distributionStatus: "UNAVAILABLE" },
      { id: "filtered", label: "欄位排除後", unit: "原始欄位", total: null, totalStatus: "UNAVAILABLE", segments: [], distributionStatus: "UNAVAILABLE" },
      { id: "processed", label: "資料處理後", unit: "編碼前欄位", total: null, totalStatus: "UNAVAILABLE", segments: [], distributionStatus: "UNAVAILABLE" },
      { id: "encoded", label: "編碼後", unit: "編碼特徵", total: 248, totalStatus: "SOURCE_REPORTED_NOT_VERIFIED", segments: [], distributionStatus: "UNAVAILABLE" }
    ],
    split: { source: 1460, training: 1168, holdout: 292, seed: 42, status: "SOURCE_REPORTED_NOT_VERIFIED", competitionTest: 1459 },
    cv: { trainingRows: 1168, foldCount: 3, protocolId: null, status: "SOURCE_REPORTED_NOT_VERIFIED" },
    methods: [
      { id: "pearson", label: "Pearson", parameters: [{ id: "top_k", label: "Top K", dataType: "integer" }] },
      { id: "lasso", label: "Lasso", parameters: [{ id: "alpha", label: "Alpha", dataType: "number" }] },
      { id: "elastic_net", label: "Elastic Net", parameters: [{ id: "alpha", label: "Alpha", dataType: "number" }, { id: "l1_ratio", label: "L1 Ratio", dataType: "number" }] }
    ],
    configurations: [],
    evaluation: { status: "UNAVAILABLE", reasonCode: "NO_APPROVED_EVALUATIONS", evaluations: [], figures: [
      ["FIG-P5-02", "Residual vs Predicted"], ["FIG-P5-01", "Actual vs Predicted"], ["FIG-P5-03", "Residual Distribution"]
    ], intervalF: "PENDING", intervalS: "UNAVAILABLE" },
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
  caseId: "ames-housing", route: "phase-1", analysisId: "overview", perspective: "method_comparison",
  phase5Figure: "FIG-P5-02", p5Population: "development_oof", p5DetailsOpen: false,
  dashboardMode: "verified", customSource: "file", customFile: null, customUrl: "", customHeaders: [], customRows: [],
  targetField: "", featureFields: [], csvMessage: "尚未載入資料。CSV 僅在此瀏覽器本機預覽，不會上傳。", customValidated: false
};
const app = document.querySelector("#app");
const phaseNav = document.querySelector("#phase-nav");
const caseSelect = document.querySelector("#case-select");

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}
function statusLabel(status) {
  const labels = { MOCK: "MOCK", UNAVAILABLE: "UNAVAILABLE", PLANNED: "PLANNED", VERIFIED: "VERIFIED", ERROR: "ERROR", SOURCE_REPORTED_NOT_VERIFIED: "SOURCE REPORTED · NOT VERIFIED" };
  return labels[status] || status || "UNKNOWN";
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
  phaseNav.hidden = !phase;
  phaseNav.innerHTML = PHASES.map(([n, en, zh]) => `<a class="phase-tab" href="#phase-${n}" ${phase === n ? 'aria-current="page"' : ""}><span class="num">0${n}</span><span>${esc(zh)}</span></a>`).join("");
  document.querySelector("[data-home-link]").setAttribute("aria-current", state.route === "phase-1" ? "page" : "false");
  document.querySelector("[data-dashboard-link]").setAttribute("aria-current", state.route === "dashboard" ? "page" : "false");
  caseSelect.innerHTML = Object.values(CASES).map((c) => `<option value="${esc(c.id)}" ${c.id === state.caseId ? "selected" : ""}>${esc(c.title)} · ${esc(c.status)}</option>`).join("");
}
function pageHeading(kicker, title, subtitle, status = caseData().status) {
  return `<div class="page-heading"><div><p class="kicker">${esc(kicker)}</p><h1>${esc(title)}</h1><p class="lede">${esc(subtitle)}</p></div><div class="page-meta">${badge(status)}</div></div>`;
}
function footerNav(prev, next) {
  const phase = routePhase();
  const samplePath = REF[`phase${phase}`];
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
function renderPhase1() {
  const c = caseData();
  const intro = `<section class="hero-layout"><div class="hero-card"><p class="kicker">NCHU AIoT 2026 · HOUSING REGRESSION LAB</p><h1>從研究問題，<br>走向可追溯的證據。</h1><p>以 CRISP-DM 六階段呈現住宅迴歸研究流程。所有頁面依資料來源狀態顯示內容，缺少審核資料時保留明確的 unavailable 狀態。</p><a class="button" href="#phase-2">開始瀏覽研究流程 →</a></div><div class="journey-card"><div><p class="eyebrow">CRISP-DM RESEARCH JOURNEY</p><h2>六個階段，<br>一段完整研究路徑。</h2><p class="body-copy">從案例脈絡、資料理解和準備，走到模型建立、評估與部署狀態。</p></div><div class="journey-line" aria-label="CRISP-DM 六階段">${PHASES.map((p) => `<span class="journey-step"><i></i>0${p[0]} ${esc(p[2])}</span>`).join("")}</div></div></section>`;
  if (c.status === "PLANNED") return `<div class="page">${intro}${banner(c)}${pageHeading("PHASE 01 / BUSINESS UNDERSTANDING", "業務理解", "案例脈絡、研究目標與預測標的。", "PLANNED")}${plannedPanel("尚未提供案例來源、研究問題或預測標的。")}${footerNav(null, [2, "資料理解"])}</div>`;
  const sections = c.sections.map((s) => `<article class="card"><div class="card-head"><div><p class="eyebrow">CASE NARRATIVE</p><h2>${esc(s.title)}</h2></div>${badge("MOCK")}</div><div class="card-body"><p class="body-copy">${esc(s.body)}</p></div></article>`).join("");
  const caseCard = `<article class="card"><div class="card-head"><div><p class="eyebrow">DATASET / CASE</p><h2>${esc(c.title)}</h2></div>${badge(c.status)}</div><div class="card-body"><dl class="data-row"><dt>Dataset</dt><dd>House Prices</dd></dl><dl class="data-row"><dt>Source</dt><dd>${esc(c.source)}</dd></dl><dl class="data-row"><dt>Source URL</dt><dd><a class="text-link" href="${esc(c.sourceUrl)}" target="_blank" rel="noreferrer">開啟官方資料來源 ↗</a></dd></dl><dl class="data-row"><dt>License review</dt><dd>${esc(c.license)}</dd></dl></div></article>`;
  const target = `<article class="card"><div class="card-head"><div><p class="eyebrow">PREDICTION TARGET</p><h2>預測標的</h2></div>${badge("MOCK")}</div><div class="card-body"><dl class="data-row"><dt>欄位</dt><dd>${esc(c.target.label)} (${esc(c.target.column)})</dd></dl><dl class="data-row"><dt>單位</dt><dd>${esc(c.target.unit)}</dd></dl><div class="method-ribbon"><strong>共享研究方法</strong><span>Multiple Linear Regression → Feature Selection → Evaluation<br>Methodology ID: ${esc(c.methodology)}</span></div></div></article>`;
  return `<div class="page">${intro}${banner(c)}${pageHeading("PHASE 01 / BUSINESS UNDERSTANDING", "業務理解", "研究案例介紹：資料來源、問題、研究目標與預測標的。", c.status)}<div class="grid three phase1-grid">${caseCard}${sections}${target}</div>${footerNav(null, [2, "資料理解"])}</div>`;
}
function renderPhase2() {
  const c = caseData();
  if (c.status === "PLANNED") return `<div class="page">${banner(c)}${pageHeading("PHASE 02 / DATA UNDERSTANDING", "資料理解", "瀏覽已產生並核准的靜態 EDA 證據。", "PLANNED")}${plannedPanel()}${footerNav([1,"業務理解"],[3,"資料準備"])}</div>`;
  const selected = c.analyses.find((a) => a.id === state.analysisId) || c.analyses[0];
  const buttons = c.analyses.map((a) => `<button type="button" class="selector-button" data-analysis="${esc(a.id)}" aria-pressed="${a.id === selected.id}">${esc(a.title)} <span class="mini-status">${esc(a.figureId)}</span></button>`).join("");
  const imageState = selected.imageRef ? `<img src="${esc(selected.imageRef)}" alt="${esc(selected.title)}">` : `<div class="state-panel"><span class="state-icon" aria-hidden="true">◌</span><h3>${esc(selected.figureId)} · ${esc(selected.title)}</h3><p>UNAVAILABLE — ${esc(selected.limitations)}. No figure or accessible table is included in this fixture.</p>${badge(selected.status)}</div>`;
  return `<div class="page">${banner(c)}${pageHeading("PHASE 02 / DATA UNDERSTANDING", "資料理解", "從已完成且公開的描述性分析中閱讀一項證據；本頁不執行即時 EDA。", "UNAVAILABLE")}<section class="card"><div class="card-head"><div><p class="eyebrow">AVAILABLE EDA ANALYSES · CASE FIXTURE LIST</p><h2>選擇一個分析視角</h2></div>${badge("UNAVAILABLE")}</div><div class="card-body"><div class="selector-row" role="group" aria-label="選擇 EDA 分析">${buttons}</div></div></section><div class="analysis-layout"><section class="card"><div class="card-head"><div><p class="eyebrow">SELECTED · ${esc(selected.figureId)}</p><h2>${esc(selected.title)}</h2></div>${badge(selected.status)}</div><div class="card-body"><div class="figure-frame" role="img" aria-label="${esc(selected.title)} 圖資目前不可用">${imageState}</div><p class="stage-note">Accessible table: ${selected.tableRef ? esc(selected.tableRef) : "UNAVAILABLE — no table fixture provided."}</p></div></section><section class="card"><div class="card-head"><div><p class="eyebrow">EVIDENCE NOTES</p><h2>分析說明</h2></div></div><div class="card-body"><dl class="data-row"><dt>描述</dt><dd>${esc(selected.description)}</dd></dl><dl class="data-row"><dt>觀察結果</dt><dd>${selected.finding ? esc(selected.finding) : "UNAVAILABLE — no finding is included in this sample."}</dd></dl><dl class="data-row"><dt>限制</dt><dd>${esc(selected.limitations)}</dd></dl><dl class="data-row"><dt>來源</dt><dd>${selected.provenanceRef ? esc(selected.provenanceRef) : "UNAVAILABLE — provenance reference not included."}</dd></dl></div></section></div>${footerNav([1,"業務理解"],[3,"資料準備"])}</div>`;
}
function renderSegments(stage) {
  const total = stage.total;
  const verified = stage.distributionStatus === "VERIFIED" && total > 0 && stage.segments.length > 0 && stage.segments.reduce((sum, segment) => sum + segment.count, 0) === total;
  if (!verified) return `<div class="stack-track is-unknown" role="img" aria-label="型態分布 ${esc(statusLabel(stage.distributionStatus))}">型態分布 ${esc(statusLabel(stage.distributionStatus))} · percentages not available</div><div class="legend">${TYPES.map(([, label, color]) => `<span class="legend-item"><i class="legend-dot" style="--dot:${color}"></i>${esc(label)}：未知</span>`).join("")}</div>`;
  const segments = stage.segments.map((s) => {
    const type = TYPES.find(([id]) => id === s.typeId); const percent = (s.count / total) * 100;
    return `<span class="stack-segment" style="width:${percent}%;background:${type?.[2] || "#ccc"}" title="${esc(type?.[1] || s.typeId)} ${s.count} / ${total} (${percent.toFixed(1)}%)"></span>`;
  }).join("");
  return `<div class="stack-track" role="img" aria-label="${esc(stage.label)}: ${stage.segments.map(s => `${s.typeId} ${s.count}`).join(", ")}">${segments}</div><div class="legend">${stage.segments.map((s) => { const t = TYPES.find(([id]) => id === s.typeId); return `<span class="legend-item"><i class="legend-dot" style="--dot:${t?.[2] || "#ccc"}"></i>${esc(t?.[1] || s.typeId)}：${s.count} · ${(s.count / total * 100).toFixed(1)}%</span>`; }).join("")}</div>`;
}
function renderPhase3() {
  const c = caseData();
  if (c.status === "PLANNED") return `<div class="page">${banner(c)}${pageHeading("PHASE 03 / DATA PREPARATION", "資料準備", "呈現原始、篩選、處理與編碼的特徵變化。", "PLANNED")}${plannedPanel()}${footerNav([2,"資料理解"],[4,"模型建立"])}</div>`;
  const stages = c.stages.map((s, i) => `<section class="stage-card"><div class="stage-head"><div class="stage-title"><span class="index">0${i + 1}</span><h2>${esc(s.label)}</h2></div><span class="stage-total">TOTAL: ${s.total == null ? "UNKNOWN" : esc(s.total)} ${esc(s.unit)} ${badge(s.totalStatus)}</span></div>${renderSegments(s)}<p class="stage-note">${s.id === "raw" ? "79 is a source-reported candidate predictor count; classification is pending audit." : s.id === "encoded" ? "248 is source-reported encoded dimensions; fit population, pipeline version and type lineage are unavailable." : "Retained feature total and category counts are unavailable; no zero-exclusion assumption is made."}</p>${s.id === "filtered" ? `<details class="disclosure"><summary>顯示排除欄位與原因</summary><div class="disclosure-body">Exclusion audit pending. No excluded-column list or verified zero count is available.</div></details>` : ""}${s.id === "processed" ? TYPES.map(([id,label]) => `<details class="disclosure"><summary>${esc(label)} · UNKNOWN</summary><div class="disclosure-body">No source-backed operation or field-level treatment is provided for this type.</div></details>`).join("") : ""}${s.id === "encoded" ? `<details class="disclosure"><summary>展開 raw-to-encoded feature mapping</summary><div class="disclosure-body">UNAVAILABLE — no approved lineage mapping is included.</div></details>` : ""}</section>`).join("");
  const split = c.split; const total = split.source;
  return `<div class="page">${banner(c)}${pageHeading("PHASE 03 / DATA PREPARATION", "資料準備", "四個相同量尺的特徵階段，接續一個獨立的資料列切分。分布未知時不繪製假比例。", "MOCK")}<div class="stage-list">${stages}<section class="card"><div class="card-head"><div><p class="eyebrow">DATASET PARTITION · ROWS, NOT FEATURES</p><h2>訓練集與保留測試集</h2></div>${badge(split.status)}</div><div class="card-body"><p class="body-copy">來源回報的切分：${split.training} / ${total} Training Set · ${split.holdout} / ${total} Holdout Test Set · Random Seed ${split.seed}。比例僅依來源回報值呈現，未驗證。</p><div class="row-split" role="img" aria-label="來源回報切分比例：訓練 80%，保留測試 20%"><span style="width:${split.training/total*100}%">Training Set · ${split.training} rows · 80%</span><span style="width:${split.holdout/total*100}%">Holdout · ${split.holdout} · 20%</span></div><p class="stage-note">Kaggle competition test (${split.competitionTest} unlabeled rows) is separate. Phase 4 CV uses only the Training Set; Holdout is not shown as a Phase 4 result.</p></div></section></div>${footerNav([2,"資料理解"],[4,"模型建立"])}</div>`;
}
function renderPhase4() {
  const c = caseData();
  if (c.status === "PLANNED") return `<div class="page">${banner(c)}${pageHeading("PHASE 04 / MODELING", "模型建立", "只呈現實際完成且可核對的模型實驗。", "PLANNED")}${plannedPanel()}${footerNav([3,"資料準備"],[5,"模型評估"])}</div>`;
  const folds = Array.from({ length: c.cv.foldCount }, (_, i) => { const validAt = i; return `<div class="cv-row"><span class="cv-label">Fold ${i+1}</span><div class="cv-track" role="img" aria-label="Fold ${i+1} 約三分之一 validation，三分之二 training"><span class="cv-valid" style="width:33.333%">Validation ~33.3%</span><span class="cv-train" style="width:66.667%">Training ~66.7%</span></div></div>`; }).join("");
  const methodOptions = c.methods.map((m) => `<option value="${esc(m.id)}">${esc(m.label)}</option>`).join("");
  const perspectives = [["method_comparison","Method Comparison"],["selected_features","Selected Features"],["feature_count_vs_cv","Feature Count vs CV RMSE"]].map(([id,label]) => `<button class="selector-button" type="button" data-perspective="${id}" aria-pressed="${state.perspective === id}">${label}</button>`).join("");
  const emptyMessages = {
    method_comparison: "No eligible configurations. Method comparison and CV RMSE values are unavailable.",
    selected_features: "No selected-feature artifact is available. Raw and encoded feature counts are not interchangeable.",
    feature_count_vs_cv: "No measured points are available. No interpolated curve or synthetic scores are shown."
  };
  return `<div class="page">${banner(c)}${pageHeading("PHASE 04 / MODELING", "模型建立與特徵選擇", "閱讀交叉驗證流程、實際方法與可用結果。選擇器只使用有效 configuration；本 fixture 沒有可用實驗。", "UNAVAILABLE")}<section class="card"><div class="card-head"><div><p class="eyebrow">01 · CROSS-VALIDATION PROTOCOL</p><h2>3-Fold CV · Training Set only</h2></div>${badge(c.cv.status)}</div><div class="cv-block"><p class="body-copy">Training Set: ${c.cv.trainingRows} source-reported rows · Fold count: ${c.cv.foldCount} (read only) · Primary metric: CV RMSE, lower is better when verified.</p>${folds}<div class="legend"><span class="legend-item"><i class="legend-dot" style="--dot:#d8e5ec"></i>Training folds</span><span class="legend-item"><i class="legend-dot" style="--dot:#b9d8c8"></i>Validation fold rotates</span></div><p class="stage-note">Schematic only; exact fold sizes and protocol ID are unknown. Holdout Test Set (292 source-reported rows) is not used here. Kaggle competition test is a separate population.</p><details class="disclosure"><summary>展開 CV methodology</summary><div class="disclosure-body">Fold count and training rows are source-reported only. Splitter, shuffle, seed, fold-level counts, fit isolation and evidence reference are UNKNOWN.</div></details></div></section><section class="card explorer"><div class="card-head"><div><p class="eyebrow">02 · FEATURE SELECTION & MODEL EXPLORER</p><h2>選擇一種研究視角</h2></div>${badge("UNAVAILABLE")}</div><div class="card-body"><div class="selector-row" role="group" aria-label="研究視角">${perspectives}</div><div class="control-row"><label class="control">Feature-selection method<select disabled><option>請先選擇可用的 configuration</option>${methodOptions}</select></label><label class="control">Valid configuration<select disabled><option>尚無可驗證配置</option></select></label></div><div class="state-panel"><span class="state-icon" aria-hidden="true">i</span><h3>${esc(emptyMessages[state.perspective] || emptyMessages.method_comparison)}</h3><p>Method catalog is a schema/sample reference, not proof that these methods were run. Configurations: ${c.configurations.length}. No scores or feature lists are fabricated.</p>${badge("UNAVAILABLE")}</div><details class="disclosure"><summary>展開實驗設定與研究限制</summary><div class="disclosure-body">A configuration is distinct from an execution run. Current sample has no execution runs, configurations, eligible parameter tuples, metrics or selected-feature artifacts.</div></details><div class="button-row" style="margin-top:18px"><a class="button" href="#phase-5">查看 Phase 5 評估狀態 →</a><a class="button" href="#phase-6">查詢 Phase 6 模型就緒狀態 →</a></div></div></section>${footerNav([3,"資料準備"],[5,"模型評估"])}</div>`;
}
function renderPhase5() {
  const c = caseData();
  if (c.status === "PLANNED") return `<div class="page">${banner(c)}${pageHeading("PHASE 05 / EVALUATION", "模型評估", "只有符合指定評估母體並通過審核的結果才會顯示。", "PLANNED")}${plannedPanel()}${footerNav([4,"模型建立"],[6,"模型預測實驗室"])}</div>`;
  const figures = c.evaluation.figures.map(([id,label]) => `<button class="selector-button" type="button" data-p5-figure="${id}" aria-pressed="${state.phase5Figure === id}">${id} · ${label}</button>`).join("");
  return `<div class="page">${banner(c)}${pageHeading("PHASE 05 / MODEL EVALUATION", "模型評估", "依指定 configuration 與評估母體呈現 MAE、RMSE、R²、診斷圖和區間證據。沒有核准結果時維持 unavailable。", c.evaluation.status)}<section class="card"><div class="card-head"><div><p class="eyebrow">01 · EVALUATION CONTEXT</p><h2>評估範圍與身分</h2></div>${badge(c.evaluation.status)}</div><div class="card-body grid two"><div><dl class="data-row"><dt>Configuration</dt><dd>UNKNOWN — source mapping pending</dd></dl><dl class="data-row"><dt>Execution</dt><dd>UNAVAILABLE</dd></dl><dl class="data-row"><dt>Evaluation ID</dt><dd>UNAVAILABLE</dd></dl></div><div><label class="control">Evaluation population<select id="p5-population"><option value="development_oof" ${state.p5Population === "development_oof" ? "selected" : ""}>Development OOF</option><option value="holdout" ${state.p5Population === "holdout" ? "selected" : ""}>Holdout aggregate</option></select></label><p class="stage-note">Population selector is a UI control only; no evaluation exists for either population.</p></div></div></section><div class="metrics" style="margin-top:18px">${[["MAE","USD · lower is better"],["RMSE","USD · lower is better"],["R²","dimensionless · not a percent"]].map(([name,note]) => `<article class="metric-card"><span class="metric-label">${name}</span><strong class="metric-value">—</strong><span class="metric-note">UNAVAILABLE · no approved metric source · ${note}</span></article>`).join("")}</div><section class="card explorer"><div class="card-head"><div><p class="eyebrow">03 · CORE DIAGNOSTICS</p><h2>${esc(c.evaluation.figures.find(([id]) => id === state.phase5Figure)?.[1] || "Residual vs Predicted")}</h2></div>${badge("UNAVAILABLE")}</div><div class="card-body"><div class="selector-row" role="group" aria-label="Evaluation figure">${figures}</div><div class="figure-frame" style="margin-top:16px"><div class="state-panel"><span class="state-icon" aria-hidden="true">◌</span><h3>${esc(state.phase5Figure)} · No approved figure</h3><p>UNAVAILABLE — an approved public-safe asset, digest, accessible table and matching evaluation provenance were not provided.</p></div></div></div></section><div class="grid two" style="margin-top:18px"><section class="card"><div class="card-head"><div><p class="eyebrow">04 · CONFIDENCE / PREDICTION INTERVAL</p><h2>區間證據</h2></div>${badge("UNAVAILABLE")}</div><div class="card-body"><dl class="data-row"><dt>INT-F feasibility</dt><dd>${esc(c.evaluation.intervalF)}</dd></dl><dl class="data-row"><dt>INT-S actual figure</dt><dd>${esc(c.evaluation.intervalS)} — formal CI/PI deliverable incomplete</dd></dl><p class="stage-note">No RMSE-derived interval or coverage claim is generated.</p></div></section><section class="card"><div class="card-head"><div><p class="eyebrow">05 · TRACEABILITY</p><h2>來源、方法與限制</h2></div></div><div class="card-body"><p class="body-copy">No evaluation IDs, sample sizes, fold summaries, predictions, or source evidence are included in this empty fixture.</p><details class="disclosure"><summary>展開來源與審查資訊</summary><div class="disclosure-body">Phase 5 schema: docs/ui-ux/case-package/phase-05/evaluation-index.schema.json. Review status: PENDING. No public release is present.</div></details></div></section></div>${footerNav([4,"返回模型建立"],[6,"模型就緒狀態"])}</div>`;
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
  if (state.route === "dashboard") app.innerHTML = renderDashboard();
  else if (phase === 1) app.innerHTML = renderPhase1();
  else if (phase === 2) app.innerHTML = renderPhase2();
  else if (phase === 3) app.innerHTML = renderPhase3();
  else if (phase === 4) app.innerHTML = renderPhase4();
  else if (phase === 5) app.innerHTML = renderPhase5();
  else if (phase === 6) app.innerHTML = renderPhase6();
  else { state.route = "phase-1"; app.innerHTML = renderPhase1(); }
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
  const raw = location.hash.replace(/^#/, "") || "phase-1";
  if (raw === "dashboard") state.route = "dashboard";
  else if (/^phase-[1-6]$/.test(raw)) state.route = raw;
  else state.route = "phase-1";
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
  else if (event.target.id === "p5-population") { state.p5Population = event.target.value; }
});
app.addEventListener("input", (event) => {
  if (event.target.id === "csv-url") {
    state.customUrl = event.target.value; state.customValidated = false;
    const urlOk = /^https:\/\//i.test(state.customUrl);
    state.csvMessage = urlOk ? "HTTPS URL format accepted; remote loading is disabled in this prototype." : "Enter an HTTPS URL. Remote loading is disabled in this prototype.";
    const status = app.querySelector(".upload-zone [role=status]"); if (status) status.textContent = state.csvMessage;
  }
});

if (!location.hash) location.hash = "phase-1";
routeFromHash();
