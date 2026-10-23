# Phase 1 NotebookLM Research Synthesis

**Project:** NCHU AIoT 2026 HW2 Housing Regression

**Related work:** [Epic #4](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/4) · [Issue #5](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/5)

**Attribution:** Human-reviewed synthesis of Owner-provided `RegScope_Research_Report.md` generated with NotebookLM. The private original remains in ignored `local/`; this file contains only reviewed claims and source links.

**Evidence boundary:** Literature and documentation synthesis only. No project CSV was profiled and no Python model or metric was run.

## NotebookLM 摘要

NotebookLM 報告將 Ames Housing 定位為適合迴歸教學的歷史住宅交易資料，並整理了多種類型的房屋與地段特徵。De Cock 的資料描述涵蓋 Ames 於 2006–2010 年的 2,930 筆銷售紀錄；Kaggle 競賽則以 `SalePrice` 為預測目標，應視為需另行核對版本與欄位的競賽資料。報告也強調，特徵選擇、缺失值處理與其他學得的前處理必須留在訓練資料及交叉驗證流程內，以降低資料洩漏風險。OLS 預測可分別呈現條件平均值與新觀測的不確定性。報告列出的 R²、離群點處理建議及其他數字尚未作為本專案證據；須在來源定位並完成 Python 驗證後再討論。[1][2][3][4][5][6]

## 引用來源對照

| 綜述主張 | 來源 | 核對狀態 |
|---|---|---|
| Ames 原始教學資料描述 2006–2010 年、2,930 筆觀察及多種解釋變數 | [De Cock (2011), Journal of Statistics Education](https://doi.org/10.1080/10691898.2011.11889627) | 已與公開文章摘要核對；欄位數不直接套用到 Kaggle 子集 |
| Kaggle 任務以房屋特徵預測 `SalePrice`；Issue #5 記載約 79 個原始候選 predictor，`Id` 不作普通 predictor | [Kaggle competition overview/data page](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/overview), [Issue #5](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/5) | 任務目標與專案定義已核對；下載版本、樣本數及欄位仍待 Phase 2 核實 |
| Feature Selection 有多種方法，需依模型與資料條件選擇 | [scikit-learn Feature Selection](https://scikit-learn.org/stable/modules/feature_selection.html) | 方法概述已核對；沒有 RegScope 方法比較結果 |
| 預處理及特徵選擇不得利用 holdout/test 資料 fit；Pipeline 有助降低洩漏 | [scikit-learn Common Pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) | 文件方法建議已核對；不是本專案實驗結果 |
| OLS 可產生平均預測及新觀測 prediction results/intervals | [statsmodels `OLSResults.get_prediction`](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_prediction.html) | API 能力已核對；本專案尚未擬合模型或計算區間 |

## 證據分類與 Phase 1 用法

### 文獻／文件證據

- Ames 教學來源說明其歷史地區、期間、樣本及豐富特徵背景。[1]
- Kaggle 任務提供 `SalePrice` 預測脈絡；必須區分競賽版與 De Cock 原始資料。[2]
- Feature Selection 與資料洩漏風險可支持「在相同驗證設計中比較可解釋基準與選擇方法」的研究問題。[3][4]
- OLS prediction API 可支持 Phase 5 規劃明確標示 confidence interval 或 prediction interval 的圖表。[5]

### 研究推論

- MLR 可作為教學 baseline，因為可檢視係數與模型限制；這是研究設計理由，不表示 MLR 會勝過其他方法，也不是因果結論。
- 單一城市、歷史交易資料的結論不能直接外推至台灣或目前市場；需其他資料與研究設計才可評估可轉移性。

### 待 Python 實證（後續 Issue，不在 Phase 1 完成）

- 目標轉換、特徵選擇、合成面積變數或極端觀察對驗證結果的影響。
- 實際 RMSE、MAE、R²、特徵排名、殘差型態及區間覆蓋率。
- Kaggle 實際資料的樣本數、欄位、缺失模式與資料字典對照。

NotebookLM 原報告提及的 R² 約 0.80、0.92、`GrLivArea > 4000` 離群點建議及異質變異結論，因原報告未提供逐段 URL／頁碼／表圖定位，本綜述不將其當成已核實結論或 RegScope 成績。六個表格項目涵蓋八個匯入項目：Kaggle Overview/Data 是兩個來源，A–Z 指引 PDF/DOCX 是同一指引的兩種檔案格式。A–Z 另列為 `writing-guidelines`，不作學術證據。完整來源索引與核查紀錄留在 Owner 的 ignored `local/`。

## 非研究證據：寫作指引

**A2Z outline example**（教師提供，版本日期 2020-03-05；PDF 與 DOCX 兩種格式，僅地端保存）。分類：`writing-guidelines`。用途為協助研究報告／論文章節安排、寫作方法及格式檢查。它不是原始研究證據，也不能取代學術文獻引用；若內容與已核准研究規格不同，須列出差異並交 PM 決定，不直接覆蓋研究設計。原始檔案不公開。

## Phase 1 對照

本摘要支持 Issue #5 的研究背景、研究問題、資料版本限制、Data Leakage 風險與未來區間視覺化成功標準。它不完成 EDA、資料準備、模型訓練或評估。Phase 1 Gate 仍由 PM 審查決定。

## References

1. De Cock (2011), [Ames, Iowa: Alternative to the Boston Housing Data as an End of Semester Regression Project](https://doi.org/10.1080/10691898.2011.11889627).
2. Kaggle, [House Prices — Advanced Regression Techniques](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/overview); project-specific requirements in [Issue #5](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/5).
3. scikit-learn developers, [Feature selection](https://scikit-learn.org/stable/modules/feature_selection.html).
4. scikit-learn developers, [Common pitfalls and recommended practices](https://scikit-learn.org/stable/common_pitfalls.html).
5. statsmodels developers, [`OLSResults.get_prediction`](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_prediction.html).
6. Project requirements: [Epic #4](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/4), [Issue #5](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/5).
