# Phase 1 — Business Understanding

**Current detailed spec, docs-only.**

### B. Phase 1 — Business Understanding / 純文字研究案例介紹

**Goal:** explain why this case exists, what is being predicted, source, problem, objective, research value and shared methodology. NO dataset figures, EDA galleries, photos, prediction form, chart or benchmark metrics.

~~~text
+--------------------------------------------------------------------------------------------------+
| PHASE 01 / BUSINESS UNDERSTANDING                                                                 |
| 業務理解：本研究要解決什麼問題？                                                                  |
|                                                                                                  |
| +----------------------------------------------------------------------------------------------+ |
| | DATASET / CASE                                                                               | |
| | Ames Housing                                                                                 | |
| | Source: Kaggle                   Dataset: House Prices                                       | |
| | Source URL: [Open official dataset source ↗]                                                | |
| +----------------------------------------------------------------------------------------------+ |
| | BUSINESS CONTEXT                                                                             | |
| | Problem:   如何依據住宅條件估計住宅售價？                                                    | |
| | Objective: 探索住宅特徵與售價的關聯，並建立可解釋的預測基準。                                | |
| | Value:     作為住宅價格迴歸與特徵選擇的教學案例。                                             | |
| +----------------------------------------------------------------------------------------------+ |
| | PREDICTION TARGET                                                                            | |
| | Column: SalePrice                 Unit: USD                                                  | |
| +----------------------------------------------------------------------------------------------+ |
| | RESEARCH METHOD / SHARED METHODOLOGY                                                         | |
| | Multiple Linear Regression → Feature Selection → Evaluation                                | |
| | Methodology: mlr-feature-selection-v1                                                        | |
| +----------------------------------------------------------------------------------------------+ |
|                                                      [Next Phase: Data Understanding >]          |
+--------------------------------------------------------------------------------------------------+
~~~

**Per-element behavior:** Dataset/Case, Business Context and Target are read-only text from selected case metadata. Source link opens the exact permitted official source; it is not a data download or automatic import. Shared methodology is resolved through root \`methodology_id\`: if same methodology applies to different cases, don't copy boilerplate into every case's \`business_context\`. \`problem/objective/value\` MUST be genuinely specific to the selected case, not a universal "run MLR" description. If a case lacks an approved field, show \`UNAVAILABLE\` for that item; do not write Ames-specific text into another case. Next navigates Phase 2.

**Minimum phase 1 data structure** (illustrative contract; content shown is existing Ames case description):
~~~json
{
  "case_id": "ames-housing",
  "title": "Ames Housing",
  "methodology_id": "mlr-feature-selection-v1",
  "phase1": {
    "dataset": {
      "name": "House Prices",
      "source": "Kaggle",
      "url": "https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data"
    },
    "business_context": {
      "problem": "如何依據住宅條件估計住宅售價？",
      "objective": "探索住宅特徵與售價的關聯，並建立可解釋的預測基準。",
      "value": "作為住宅價格迴歸與特徵選擇的教學案例。"
    },
    "prediction_target": {"column": "SalePrice", "unit": "USD"}
  }
}
~~~