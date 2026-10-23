# CRISP-DM Phase 1 — Business Understanding

**Project:** NCHU AIoT 2026 HW2 Housing Regression

**Parent Epic:** [#4 — HW2 Regression Research](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/4)

**Work item:** [#5 — Business Understanding](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/5)

**Phase status:** Draft for PM review. This document defines the problem and evidence plan; it does not authorize Phase 2 or claim empirical results.

## 1. Executive Summary

本研究以 Kaggle「House Prices — Advanced Regression Techniques」作為教學基準，探討如何使用 Multiple Linear Regression (MLR) 解釋 Ames, Iowa 房屋資料中的特徵與 `SalePrice` 的關係，並比較 Feature Selection 對可解釋性及預測表現評估的影響。專案首先建立可重現、可審查的線性迴歸基準流程；結果僅適用於後續確認版本的 Kaggle/Ames 資料，不是台灣房價估價系統，也不支援信貸、交易或政策決策。

CRISP-DM Phase 1 的交付是明確研究問題、驗證方式、限制、風險、作業追溯及 Phase 2 入場條件。尚未進行 EDA、資料清理、建模、NotebookLM 分析或效能評估；任何模型數字與特徵效果都須待後續有證據後才能提出。

## 2. Business Problem

**Verified Fact — 專案範圍：**Epic #4 與 Issue #5 指定 Kaggle House Prices/Ames Housing、目標 `SalePrice`、Multiple Linear Regression、Feature Selection、模型評估與含信賴區間或預測區間的預測圖作為 HW2 研究要求。[1][2]

**Verified Fact — 研究脈絡：**De Cock 描述的 Ames 資料是 Iowa 州 Ames 市 2006–2010 年住宅銷售資料；論文摘要列有 2,930 筆觀察及多種類型的解釋變數。[3] Kaggle 競賽則把任務設定為依住宅特徵預測 SalePrice。[4]

**Business Problem：**學習者需要一套有來源、有明確限制且能重現的分析流程，理解住宅屬性如何與歷史銷售價格相關，並以可解釋的線性基準檢視預測誤差及不確定性。這是一項教育與方法比較問題，不是目前實際部署中的估價需求。

本研究不把模型關聯解釋為特徵造成價格變化的因果效果。Kaggle/Ames 的地區、年代、樣本選取與欄位定義均限制外推；尤其不能據此宣稱可直接預測台灣房價。

## 3. Research Questions

1. 在資料取得、版本及欄位經 Phase 2 核實後，MLR 如何表達至少 14 個原始房屋預測特徵與 `SalePrice` 的條件關聯？
2. 哪些原始特徵在預先定義且無資料洩漏的 Feature Selection 流程中保留？不同選擇方法下，特徵集合及係數解讀有何差異？
3. 經相同切分與驗證程序評估時，Feature Selection 對 MLR 的 RMSE、MAE、R² 及特徵可解釋性有何影響？
4. 模型的實際預測與誤差如何呈現？信賴區間或預測區間各表示何種不確定性，在哪些模型假設下才可解讀？
5. 研究結論在哪些 Ames 資料條件下成立，哪些地區、年代、族群或交易情境不在證據支持範圍內？

以上問題是待研究問題，並非已知答案或實驗結果。

## 4. Stakeholders & Use Cases

| Stakeholder | 使用情境 | 可提供的價值與限制 |
|---|---|---|
| NCHU AIoT 課程教師／助教 | 檢視是否依作業要求完成 CRISP-DM、迴歸、特徵選擇與評估 | 以可追溯文件、程式及結果審查學習成果；教師原始 rubric 尚待取得核對 |
| 修課學生／研究小組 | 學習資料來源、MLR 假設、特徵選擇、驗證及不確定性解讀 | 建立可重現的研究習慣；不得把模型輸出當作因果結論 |
| 同儕／GitHub 與 RegScope 讀者 | 理解研究問題、方法、證據及限制 | 只能閱讀經審查可公開的程式、metadata、摘要和展示內容 |
| 後續 Phase 2–5 實作者 | 依定義取得資料、檢查品質、準備分析並評估模型 | Phase 1 定義評估方向；不預先指定未有證據的模型效能門檻 |

**禁止用途：**本專案不是專業鑑價服務、貸款核准依據、個人房屋交易建議，也不是供台灣房市直接使用的估價工具。

## 5. Business Objectives

- 以 Ames/Kaggle 案例完成一個可審查的住宅價格迴歸教學研究。
- 讓學習者能說明 MLR 的係數、假設、適用範圍與限制，而不把統計關聯說成因果。
- 透過 Feature Selection 練習以資料內證據比較候選變數；不預設特徵選擇必然提高預測分數。
- 以訓練／驗證流程、誤差指標及區間圖建立對預測不確定性的正確認識。
- 依 CRISP-DM 六階段留下研究問題、資料來源、方法、決策、結果及交付證據。

## 6. Data Mining Goals

Phase 2 取得並核對獲准使用的 Kaggle 資料後，後續建模工作的規劃目標如下：

1. 將 `SalePrice` 作為連續目標變數；`Id` 是記錄識別／提交對應欄位，不作為普通房屋預測特徵。[2][4]
2. 依該次實際取得的資料與 data dictionary 核實原始特徵欄位。Epic/Issue 記載約 79 個候選預測特徵；Issue #5 要求至少 14 個**原始**預測特徵，不設 39 個特徵上限。Phase 2 應確認可用特徵數；後續報告需分清原始欄位與類別編碼後欄數。[1][2]
3. 建立可解釋的 MLR baseline，並與明確說明的 Feature Selection 方案比較；候選方法、前處理及模型設定待 Phase 2/3 依資料特性決定。
4. 先定義資料切分與交叉驗證策略；所有需由資料估計的處理及特徵選擇，須只在各訓練折 fit，避免驗證或測試資料洩漏。[5][6]
5. 在具體模型與驗證資料建立後，報告 RMSE、MAE 及 R²，並提供實際與預測值圖。至少一種區間視覺化須清楚標示為**平均反應的 confidence interval** 或**個別新觀測的 prediction interval**，並解釋涵義與假設。[7]
6. 所有分數、圖、入選特徵及診斷結論均需由可重現程式實際產生；不得以競賽排行榜、文件範例或 NotebookLM 回答代替本專案實驗。

**指標差異：**Epic/Issue 要求報告 RMSE、MAE、R²；Kaggle 競賽頁標示的排行榜指標是 Root Mean Squared Logarithmic Error (RMSLE)。兩者目的與尺度不同。是否另計 RMSLE、主要報告尺度及與作業 rubric 的對應，需於 Phase 2 前由 PM/教師確認；本文件不以 Kaggle 排行榜門檻替代課程成功標準。[2]

## 7. Success Criteria

成功標準採可驗證證據，不設定無來源的 RMSE/MAE/R² 數值門檻，也不預先承諾 Feature Selection 必定改善模型。

| Criterion | Evidence planned | Gate |
|---|---|---|
| 可重現流程 | 固定資料版本／檔案雜湊、程式版本、分割與交叉驗證設定、種子及執行紀錄 | Phase 2–5 |
| 可解釋 MLR baseline | 以至少 14 個可核實的原始預測欄位作為候選輸入；說明欄位轉換、類別編碼、係數意義與模型假設 | Phase 2–4 |
| Feature Selection 學習目標 | 記錄方法、選擇依據、選中欄位與不穩定性；與 baseline 以相同驗證設計比較 | Phase 3–5 |
| 公平且可解讀的模型評估 | 在明確保留的驗證／測試程序上計算 RMSE、MAE、R²；說明其尺度、比較對象及限制 | Phase 4–5 |
| 預測與不確定性視覺化 | 實際值對預測值圖及至少一種明確標為 confidence interval 或 prediction interval 的圖；圖表附資料子集、模型與區間解釋 | Phase 5 |
| 作業與研究完整性 | 完成六階段追溯；NotebookLM 摘要僅在 Owner 提供實際 NotebookLM 分析後引用，且繁體中文摘要至少 100 字；ChatGPT PDF 與 GitHub/Web 交付留下證據 | 全 Epic；各項依矩陣 gate |

PM/教師若要求數值通過門檻，應提供正式標準後再納入評分，不在此自行創造。

## 8. Assumptions & Constraints

### 8.1 Verified Facts

- Epic #4 與 Issue #5 是本工作單的要求來源；它們將目標指定為 `SalePrice`、要求 MLR、Feature Selection、RMSE/MAE/R²、預測圖及 CI/PI，並記錄至少 14 個原始候選特徵與不設 39 個上限。[1]
- De Cock 論文摘要描述 Ames 2006–2010 年房屋銷售、2,930 筆觀察，以及名目、序位、離散與連續類型的解釋變數。[3]
- Kaggle 資料需透過競賽頁取得；頁面存取與參賽規則可能要求登入／接受條款。尚未在本 Phase 1 驗證任何本機 CSV 的版本或內容。[4]
- scikit-learn 指出測試資料不得參與 fit；含特徵選擇的前處理應限制在訓練資料，Pipeline 可協助避免洩漏。[5][6]
- statsmodels OLS prediction API 可產生平均預測及新觀測預測結果／區間；這是套件能力，不代表本專案已建立模型或計算區間。[7]

### 8.2 Research Assumptions

- 教學研究會以每筆房屋銷售紀錄為分析單位，預測其記錄的歷史 `SalePrice`。
- MLR 作為教學基準，是為了練習條件關聯、係數與假設解讀；其簡單性不保證預測最佳。
- 在資料字典和缺失狀況確認後，類別特徵可採合適編碼，連續／離散特徵可依需要轉換；具體方案不在 Phase 1 定案。
- 評估結果僅說明選定資料版本及驗證切分下的表現，不直接代表未來交易或其他市場的預測效能。

### 8.3 Constraints

- 資料地理與年代受 Ames, Iowa 及該 Kaggle 資料版本限制；原始論文描述 2006–2010，競賽版本的實際範圍與其相同程度待 Phase 2 以來源及 data dictionary 確認。[3][4]
- Kaggle 下載與使用須遵守當時適用的競賽規則與授權；不得繞過登入或存取控制。原始 CSV、研究 PDF、NotebookLM 私人資料及憑證只存於忽略的 `local/`。[8]
- 目前沒有教師原始 HW2 rubric 文件；Issue/Epic 的記錄可作專案追溯，但不能冒稱已逐字核實教師正式條文。
- 不宣稱資料代表美國全體住宅，更不外推至台灣；歷史資料不保證反映目前市場。

## 9. Risks & Limitations

| Risk | Potential effect | Planned response |
|---|---|---|
| 單一城市與歷史期間 | 地理、年代、利率及市場制度限制外部效度 | 報告限制，避免泛化；需要新地區／期間資料才能主張可轉移性 |
| 樣本及選擇偏差 | 有成交紀錄的物件不一定代表未成交、未上市或全體住宅 | Phase 2 檢查資料涵蓋範圍與抽樣脈絡；在報告標示未知處 |
| 欄位語意與缺失值誤讀 | 將結構性「不適用」誤作一般缺失，可能改變模型含義 | 以該版 data dictionary 解讀；處理決策記錄於 Phase 3 |
| 高維度、共線性或非線性 | OLS 係數不穩定、區間變寬或系統性預測誤差 | Phase 2/4 做診斷；比較選擇／變換方案，不把線性假設視為已成立 |
| Data Leakage | 驗證分數過度樂觀 | 先切分；特徵篩選及所有學得的前處理放入 CV 訓練流程。[5][6] |
| 多重比較與 Feature Selection 不穩定 | 反覆嘗試使表現高估；選中特徵依切分改變 | 記錄嘗試，使用適當 CV/保留集；將穩定性與解釋限制納入討論 |
| 關聯被誤稱因果 | 教學結果被用作錯誤政策或個人決策 | 使用關聯語言，明示觀察性資料及未識別的混雜因素 |
| 區間假設不符合 | CI/PI 可能未達名目涵蓋或解讀錯誤 | 標示區間類型與模型假設；評估其覆蓋需後續資料驗證，不能只憑圖宣稱校準 |
| 授權或敏感內容外洩 | 違反資料／來源限制 | 私有原始資料留 `local/`；公開前執行 Security Scan 與人工檢視。[8] |

## 10. HW2 Requirements Traceability

下列要求取自 Parent Epic #4 與 Issue #5；因教師原始 rubric 未附在 repo，對應狀態不代表已獲教師最終確認。[1]

| HW2 requirement | Phase 1 decision / planned evidence | Planned phase / status |
|---|---|---|
| Kaggle House Prices 迴歸資料、目標 SalePrice | 指定 Kaggle/Ames，`SalePrice` 為連續 target；Phase 2 記錄資料版本、來源與 data dictionary | P1 定義；P2 驗證來源及欄位 |
| 至少 14 個原始預測特徵；不設 39 特徵上限 | Phase 2 核實至少 14 個可用原始 predictor；後續模型以至少 14 個原始欄位作候選輸入，另報編碼後欄數。是否要求「最終選中」也至少 14 個待教師確認 | P2 核實；P3–P5 留證；無 39 上限 |
| Multiple Linear Regression | 建立 MLR baseline，說明係數與假設 | P4 Modeling |
| Feature Selection | 比較有明確方法與無洩漏評估的候選特徵集合；不保證改善效能 | P3 Preparation / P4 Modeling / P5 Evaluation |
| Model Evaluation | 報告 RMSE、MAE、R²、驗證設計、比較基準及限制；不預造門檻 | P4–P5 |
| 預測圖及 Confidence Interval 或 Prediction Interval | 提供 actual-vs-predicted 圖及一種明確標示區間的結果圖，附解讀與假設 | P5 Evaluation |
| CRISP-DM 六階段 | 建立六階段 issue / PR / artifact 追溯；Phase 1 只完成本文件 | Epic 全程；P1 文件定義後續交付 |
| NotebookLM 研究及至少 100 字繁體中文摘要 | Owner 手動匯入已授權來源；取得 NotebookLM 原始回答與引用後，保存標註來源的 100 字以上摘要。未取得前標記待辦，不以 GPT 內容代替 | 全 Epic 後續；NotebookLM 尚未產出 |
| 區分 ChatGPT 與 NotebookLM 產出 | 分別標示作者／工具及引用；NotebookLM 摘要只能在實際取得後標記 | 研究報告與提交包 |
| ChatGPT 對話 PDF 匯出 | 匯出相關對話作為提交證據；私人 PDF 留在 `local/`，未審查不得公開 | 最終提交準備 |
| GitHub 與 Web 交付 | GitHub PR、程式與公開安全文件；Web/RegScope 展示僅放經審查內容，Phase 1 PR 不觸發 Production | 全 Epic；Phase 6 交付 |
| Optional bonus：切換兩個迴歸問題（+1） | 非核心要求，不納入 Phase 1 成功 gate；需確認作業 rubric 與範圍後另立決策 | Optional / 待確認 |
| Optional bonus：使用者自行輸入 Dataset（+2） | 非核心要求；實作前需定義檔案安全、欄位驗證及推論限制，不在本 Issue 範圍 | Optional / 待確認 |
| 「10+」特徵或其他未提供正式條文的限制 | Epic 要求不要在無原文證據時自行編碼此限制 | 待 PM/教師提供 rubric 核對 |

## 11. Phase 2 Entry Criteria

Phase 2 尚未開始。進入 Data Understanding 前，需由 PM 審查 Phase 1 文件，並完成以下條件：

- **資料存取與權限：**Owner 以允許方式取得 Kaggle 檔案並確認適用條款；原始 CSV 留在 ignored `local/datasets/`，不傳入 Git、Web build 或公開測試資料。
- **來源與版本：**記錄官方來源 URL、取得日期、資料版本／競賽版本及原始檔 SHA-256；不公開原始資料或敏感 metadata。
- **Data Dictionary：**保存並核對 Kaggle data description；明確核對 `SalePrice`、識別欄 `Id`、欄位數及至少 14 個原始 predictor，並區分 Kaggle 子集與 De Cock 論文所述原始資料。
- **Profiling Plan：**在真實獲准資料上規劃 row/column counts、型別、缺失模式、重複／識別欄、目標分布、類別基數與基本範圍檢查；此清單是未來計畫，不是本文件已完成的 EDA。
- **分析計畫：**PM/教師確認至少 14 個特徵的解讀（候選可用或最終使用）、RMSE/MAE/R² 的報告尺度，以及 Kaggle RMSLE 是否需要另行報告。
- **工具與安全：**固定 Python 套件環境及可重現分析入口；測試用合成資料，不複製真實 Kaggle row；掃描 public artifacts，確認原始資料仍在 local。

Phase 2 entry evidence should include a source/provenance record, a data dictionary mapping, a real-data profiling report with public-safe aggregate results, and documented open questions. PM must explicitly accept Phase 1 before the team treats the Phase 2 gate as passed.

## 12. Open Questions

1. 教師原始 HW2 rubric 的正式文件在哪裡？「至少 14 個原始特徵」要求可用候選欄位、baseline 實際輸入，還是 Feature Selection 後的最終欄位？
2. 教師是否要求「10+」特徵、特定 RMSE/MAE/R² 門檻、特定資料切分或模型規格？目前無原文，不設為 gate。
3. Kaggle 競賽版實際欄位、樣本與 De Cock 論文原始 2,930 筆資料如何對應？須待獲准資料與 data dictionary 核實。
4. 作業是否要求 Kaggle 的 RMSLE，或以一般尺度 RMSE/MAE/R² 為主？是否同時報告需確認。
5. CI/PI 的指定類型、信賴水準、圖表格式與是否要求覆蓋率檢查，是否由教師另有規範？
6. NotebookLM 可使用的來源授權及 Owner 匯入後可引用的回答，目前有哪些已確認紀錄？在取得 NotebookLM 原文與 citations 前不填寫歸屬於 NotebookLM 的摘要。
7. Web 交付要求的公開內容、交付網址與截止時間，是否有 Issue #4 以外的正式 rubric？

## 13. Phase 1 Review Gate

本文件提出可審查的研究問題、無任意效能門檻的成功標準、scope/limitations、風險、作業追溯及 Phase 2 入場證據。文件完成不等於 Phase 1 Gate PASS；須由 PM 審查本 PR 並決定是否接受未決問題及准許 Phase 2 開始。W1P1 不自行宣告 Gate 通過。

## 14. References

1. Project work records: [Epic #4](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/4), [Issue #5](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/5). 教師原始 rubric 尚未附入 repo。
2. Kaggle, [House Prices — Advanced Regression Techniques: Overview](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/overview) and [Data page / data description](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data). Access/download and current dataset contents must be verified at Phase 2.
3. De Cock, D. (2011). [Ames, Iowa: Alternative to the Boston Housing Data as an End of Semester Regression Project](https://doi.org/10.1080/10691898.2011.11889627). *Journal of Statistics Education*, 19(3). Public article abstract supports the 2006–2010, 2,930-observation description.
4. Kaggle, [House Prices — Advanced Regression Techniques](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/overview). The overview identifies the sale-price prediction task; the associated competition metric is RMSLE. Use the official page and the versioned data description to verify exact assignment data fields.
5. scikit-learn developers, [Common pitfalls and recommended practices](https://scikit-learn.org/stable/common_pitfalls.html), especially data leakage and training-only fitting of learned transformations.
6. scikit-learn developers, [Feature selection](https://scikit-learn.org/stable/modules/feature_selection.html). Available methods are candidates for later controlled comparison, not evidence of project performance.
7. statsmodels developers, [`OLSResults.get_prediction`](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_prediction.html). API reference for prediction results and interval-related methods; no project model has been fit.
8. Repository [Security and Data Policy](../SECURITY_AND_DATA_POLICY.md): raw data, PDFs, private NotebookLM materials and credentials remain in ignored `local/`.

IBM, [CRISP-DM View](https://www.ibm.com/docs/en/spss-modeler/saas?topic=projects-crisp-dm-view). IBM describes the six phases and notes Business Understanding as requirements/goals work, not model analysis.
