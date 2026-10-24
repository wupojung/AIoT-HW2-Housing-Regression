# CRISP-DM Phase 3: Data Preparation (Ames Housing Regression)

- **Phase status:** IMPLEMENTATION_COMPLETED (Phase 3 Reproducible Data Preparation Pipeline implemented and verified by internal test suite; Independent QA PASS; PM Review PENDING; Milestone Checkpoint PENDING)
- **Task ID:** Issue #15 (Epic #4)
- **Implementation Worktree:** `AIoT-HW2-Housing-Regression-issue15-phase3` (isolated Phase 3 worktree)
- **Branch:** `feature/phase3-data-preparation-issue-15`
- **BASE Commit:** `fe287cb7b0dc759c7f1a5519cd662690625df584`
- **Author / Role:** `w1:p2` (Implementer / Antigravity)
- **Coordination Handoff:** `local/handoff/issue-15-phase3-coordination-2026-10-24.md` (primary checkout untracked handoff)

---

## 執行摘要 (Executive Summary)

本文件記載 Ames 房價迴歸專案在 CRISP-DM 第三階段（資料準備，Data Preparation）之實作成果與實證紀錄。本階段依據 Phase 2 資料理解產出之 81 項原始欄位清冊（包含 79 個預測變數、1 個外部識別碼 `Id` 與 1 個目標變數 `SalePrice`）與領域字典，建立了一套具備嚴格防資料洩漏（Leakage-Free）、可完全重現、支援自訂路徑的訓練配適與轉換管線（Train-Fit / Transform-Only Pipeline）。所有預處理參數（中位數、眾數、名義類別水準）皆 100% 僅由訓練分割集學習，並保留所有 61 筆標的變數 IQR 異常值候選供後續階段檢定。

### 1. 資料集規模與切分架構 `[Verified / 已驗證]`
- **標籤資料切分**：僅從具備標籤的 1,460 筆 `train.csv` 中，使用固定亂數種子 `random_state = 42` 進行 80/20 的內部切分，精確劃分為 **1,168 筆訓練集（Train Partition）** 與 **292 筆內部驗證集（Validation Partition）**。兩者索引集合互斥（交集為 0），確保劃分無重疊。
- **競賽測試集隔離**：Kaggle 官方提供的 1,459 筆 `test.csv` 嚴格定義為純轉換資料（Transform-Only Data）。本階段未將測試集納入任何參數配適計算，徹底隔離資料洩漏風險。
- **識別碼與標的變數隔離**：`Id` 欄位純化為外部追蹤 metadata，徹底排除於預測矩陣 $X$ 之外；目標變數 `SalePrice` 獨立分離為目標向量 $y$，不在特徵空間中殘留。

### 2. 結構性缺失與補值策略 `[Verified / 已驗證]`
- **15 個物理結構性缺失之專門處理**：依據 Phase 2 資料理解，對於 14 個類別型設施缺失（如 `Alley`, `PoolQC`, `Fence`, `MiscFeature`, `FireplaceQu`, `GarageType`, `GarageFinish`, `GarageQual`, `GarageCond`, `BsmtQual`, `BsmtCond`, `BsmtExposure`, `BsmtFinType1`, `BsmtFinType2`）分別指派專屬哨兵值 `'None'` 或序數階級 `0`；對於 1 個數值型結構缺失 `GarageYrBlt`，指派結構哨兵數值 `0.0`，並同步建立 `HasGarage` 等 7 項實體存在指示特徵（Structural Indicators）。
- **非結構性未知遺漏精確補值與區隔**：
  - **數值欄位**：以訓練集之中位數（Median）填補（如 `LotFrontage` 補以 70.0）。
  - **名義欄位**：以訓練集之眾數（Mode）填補（如 `Electrical` 補以 `'SBrkr'`、測試集缺失之 `MSZoning` 補以 `'RL'`、`Utilities` 補以 `'AllPub'`）。
  - **有序欄位**：非結構性缺漏（如測試集出現之 `KitchenQual`, `Functional`）以訓練集映射整數等級之 **中位數（Median of Training-Mapped Integer Scores）** 填補，而非字面眾數，確保等級空間中心性。
  - **磚石飾面（`MasVnrType` 與 `MasVnrArea`）之特殊處置**：雖然訓練集之眾數與中位數恰為 `'None'` 與 `0.0`，但其本質為非結構性之未記錄遺漏。管線除了以訓練統計量補值外，額外建立專屬指示變數 `MasVnrType_is_missing` 與 `MasVnrArea_is_missing`，使「真實無飾面（None/0）」與「未記錄遺漏（補值為 None/0）」在特徵矩陣中完全可區隔。轉換後所有分割集之缺失值皆降至 0（100% 完整）。

### 3. 特徵分類與編碼轉換 `[Verified / 已驗證]`
- **特徵維度擴展**：原始 79 個預測變數經重構為：
  - **35 個連續與離散數值特徵**（Numeric Continuous & Discrete Features）。
  - **7 個實體設施存在指示特徵**（`HasGarage`, `HasBasement`, `HasFireplace`, `HasPool`, `HasFence`, `HasAlley`, `HasMiscFeature`）。
  - **2 個非結構性缺失指示特徵**（`MasVnrType_is_missing`, `MasVnrArea_is_missing`）。
  - **19 個有序特徵**（Ordinal Features，依據字典層級嚴格對應為整數等級 0 至 8）。
  - **25 個名義類別特徵**（Nominal Features，採 One-Hot 編碼，包含依規範將 `MSSubClass` 視為名義類別），共展開出 **185 個二元 Dummy 特徵**。
  - **最終編碼特徵總數為 248 個**（35 + 7 + 2 + 19 + 185 = 248）。
- **未知類別容錯防護（Unknown Category Handling）**：名義類別 One-Hot 編碼採用 `handle_unknown='ignore'` 原則。當驗證集出現訓練集未見之名義類別（共 1 次未見水準觀測）或測試集出現罕見類別（共 1 次未見水準觀測）時，管線自動將該特徵所有 Dummy 設為 0，絕不拋出例外亦不改變欄位數量與排列，並忠實記錄於地端中繼摘要檔中。

### 4. 異常值候選與資料治理邊界 `[Assumed / 假設]`
- **61 筆 IQR 異常值候選全數保留**：在 Phase 2 所標記之 61 筆 `SalePrice` 邊際 IQR 離群候選（精確值：下圍欄 $3,937.50，上圍欄 $340,037.50；四捨五入整數表示為 $4,000 與 $340,000），在本階段資料準備中 **100% 完整保留，無任何刪除、截斷（Winsorization）或過濾**。保留原因在於高價房屋代表合理的真實市場交易樣態，其離群特質屬於 Phase 4 應評估是否採用對數轉換（Log Transformation）或強健迴歸之重要實證對象。
- **資料治理承諾**：所有逐筆資料與轉換後的特徵矩陣僅保留於主 checkout ignored 之 `local/` 本地目錄，嚴禁將未去識別化或高維逐筆數據提交至公共 Git 版本庫。

### 5. Phase 4 候選假設與建模待辦 (Candidate Hypotheses) `[Open / 待檢定]`
- **假說 H1（標的對數轉換）**：對標的變數進行對數轉換 $\log(1 + y)$ 是否能有效緩解高房價離群值對普通最小平方（OLS）殘差常態性之負面影響？
- **假說 H2（有序特徵編碼比較）**：將 19 個有序特徵視為整數等級（Ordinal Integer Rank）與展開為 One-Hot Dummy，在正則化線性迴歸（Ridge/Lasso）與非線性梯度提升樹（GBDT）上之預測誤差差異為何？
- **假說 H3（高基數與稀疏性篩選）**：在展開的 185 個 One-Hot 特徵中，極端低頻類別（例如僅出現 1 次之材料）是否會導致多重共線性或高方差過擬合？ Phase 4 是否應導入方差閾值過濾或 L1 正則化進行特徵篩選？

---

## 1. 資料準備目標與階段邊界 (Objectives & Boundary Gates)

### 1.1 階段目標
本階段（Phase 3 Data Preparation）專注於建置可重用、抗資料洩漏的特徵工程與資料清理管線，產出結構化特徵矩陣與對應的元資料映射清冊，為 Phase 4 建模提供標準化輸入。

### 1.2 嚴格邊界守則 (Boundary Invariants)
依據專案治理守則與派工指令，Phase 3 必須恪遵以下不可逾越之邊界：
- **禁止任何模型訓練**：不得呼叫任何監督式迴歸模型（如 LinearRegression, Ridge, Lasso, RandomForest, XGBoost 等）進行擬合。
- **禁止監督式特徵選取**：不得依據目標變數關聯度、相關係數或特徵重要性進行特徵刪除或排名。
- **禁止指標評估與比較**：不得計算 RMSE、MAE 或 $R^2$ 等預測評估指標。
- **禁止 Kaggle 競賽提交**：不得產生或提交競賽預測結果檔至 Kaggle。
- **禁止部署與 Phase 2 重跑**：不得觸發線上部署，不得重新執行 Phase 2 描述性統計或重生 174 張圖表。

---

## 2. 資料集分割與防漏機制 (Dataset Splitting & Leakage Prevention)

### 2.1 原始資料來源雜湊校驗 `[Verified / 已驗證]`
所有輸入資料均來自於專案主 checkout ignored 之 `local/datasets/` 目錄，各輸入檔案之 SHA-256 數位簽章與規模如下表所示：

| 檔案名稱 | SHA-256 雜湊值 (Digest) | 檔案大小 (Bytes) | 總筆數 (Rows) | 原始欄位數 (Cols) |
|---|---|---|---|---|
| `train.csv` | `1e18addf81e5e4d347cc17ee6075bbe4a42b7fa26b9e5b063e8f692a5f929d41` | 460,676 | 1,460 | 81 |
| `test.csv` | `8fdd3d829d4d986b58f845c9553b225e67dd8383624d90fb6ca1d4bed5798c1e` | 451,405 | 1,459 | 80 |
| `sample_submission.csv` | `f19e99699b925aa3085c8d2ae43c62f15fbcd35e4a953b98025f8392c3ffa807` | 31,939 | 1,459 | 2 |
| `data_description.txt` | `356a4670aa688afa8ba44b1365b633fbbac2dae535fe4638532630607d64070d` | 13,370 | - | - |

### 2.2 80/20 固定種子分割架構 `[Verified / 已驗證]`
- **切分原則**：僅對 1,460 筆具備標籤的 `train.csv` 進行切分。
- **隨機種子**：固定使用 `random_state = 42`，以獨立的亂數生成器產生隨機排列（Permutation）。
- **切分統計**：
  - **訓練集（Train Partition）**：1,168 筆（80.00%）。
  - **驗證集（Validation Partition）**：292 筆（20.00%）。
  - **競賽測試集（Competition Test）**：1,459 筆（維持原樣，Transform-Only）。
- **防漏驗證**：訓練集與驗證集之索引交集為空集合，且聯集精確涵蓋 1,460 筆資料。

### 2.3 參數學習隔離機制 `[Verified / 已驗證]`
為防止任何型式的資訊外洩（Data Leakage），預處理管線的 `fit()` 函式 **僅接收 1,168 筆訓練集**：
1. 數值欄位的中位數（Median）僅自訓練集計算。
2. 類別欄位的眾數（Mode）與已知類別水準（Active Categories）僅自訓練集統計。
3. 驗證集與競賽測試集一律透過 `transform()` 函式進行處理，絕無參數回饋或再次配適。

---

## 3. 物理結構性缺失與未知遺漏處理 (Structural Absence vs Genuine Missingness)

### 3.1 15 個物理結構性缺失欄位處理 `[Verified / 已驗證]`
在 Ames 資料集中，許多欄位之字面值 `"NA"` 代表該房屋不具備特定設施，此為領域結構特徵而非觀測遺漏。管線依據資料字典進行結構化重構：

| 設施範疇 | 涉及欄位名稱 | 變數型態 | 處理方法與指派數值 |
|---|---|---|---|
| **巷道通聯** | `Alley` | 名義類別 | 指派專屬類別哨兵值 `'None'`（展開為 `Alley_None` Dummy） |
| **游泳池** | `PoolQC` | 有序類別 | 映射為序數等級 `0`（代表無泳池，相對於 Fa=1, TA=2, Gd=3, Ex=4） |
| **圍欄設施** | `Fence` | 有序類別 | 映射為序數等級 `0`（代表無圍欄，相對於 MnWw=1, GdWo=2, MnPrv=3, GdPrv=4） |
| **雜項設施** | `MiscFeature` | 名義類別 | 指派專屬類別哨兵值 `'None'`（展開為 `MiscFeature_None` Dummy） |
| **壁爐品質** | `FireplaceQu` | 有序類別 | 映射為序數等級 `0`（代表無壁爐，相對於 Po=1, Fa=2, TA=3, Gd=4, Ex=5） |
| **車庫設施 (5項)** | `GarageType` | 名義類別 | 指派專屬類別哨兵值 `'None'` |
| | `GarageFinish` | 有序類別 | 映射為序數等級 `0`（代表無車庫，相對於 Unf=1, RFn=2, Fin=3） |
| | `GarageQual` | 有序類別 | 映射為序數等級 `0`（代表無車庫，相對於 Po=1, Fa=2, TA=3, Gd=4, Ex=5） |
| | `GarageCond` | 有序類別 | 映射為序數等級 `0`（代表無車庫，相對於 Po=1, Fa=2, TA=3, Gd=4, Ex=5） |
| | `GarageYrBlt` | 數值年份 | 當無車庫時指派數值哨兵 `0.0`，並結合 `HasGarage` 二元指示特徵標示 |
| **地下室設施 (5項)** | `BsmtQual` | 有序類別 | 映射為序數等級 `0`（代表無地下室，相對於 Po=1, Fa=2, TA=3, Gd=4, Ex=5） |
| | `BsmtCond` | 有序類別 | 映射為序數等級 `0`（代表無地下室，相對於 Po=1, Fa=2, TA=3, Gd=4, Ex=5） |
| | `BsmtExposure` | 有序類別 | 映射為序數等級 `0`（代表無地下室，相對於 No=1, Mn=2, Av=3, Gd=4） |
| | `BsmtFinType1` | 有序類別 | 映射為序數等級 `0`（代表無地下室，相對於 Unf=1, LwQ=2, Rec=3, BLQ=4, ALQ=5, GLQ=6） |
| | `BsmtFinType2` | 有序類別 | 映射為序數等級 `0`（代表無地下室，相對於 Unf=1, LwQ=2, Rec=3, BLQ=4, ALQ=5, GLQ=6） |

### 3.2 物理存在指示特徵 (Structural Presence Indicators) `[Verified / 已驗證]`
為了提供線性與樹狀模型明確的物理設施具備信號，管線建構了 7 個二元指示變數：
1. `HasGarage`：當具備有效車庫類型時為 `1.0`，無車庫為 `0.0`。
2. `HasBasement`：當具備有效地下室品質且面積大於 0 時為 `1.0`，無地下室為 `0.0`。
3. `HasFireplace`：當壁爐數量大於 0 或具備壁爐品質評價時為 `1.0`，否則為 `0.0`。
4. `HasPool`：當泳池面積大於 0 或具備泳池品質評價時為 `1.0`，否則為 `0.0`。
5. `HasFence`：具備圍欄評價時為 `1.0`，否則為 `0.0`。
6. `HasAlley`：具備巷道通聯時為 `1.0`，否則為 `0.0`。
7. `HasMiscFeature`：具備雜項設施時為 `1.0`，否則為 `0.0`。

### 3.3 非結構性未知遺漏補值與結果驗證 `[Verified / 已驗證]`
對於非屬結構性特徵之未記錄/非結構性遺漏，全數採用訓練集配適之統計量：
- **數值欄位**：以訓練集連續/計數數值之 **中位數（Median）** 填補（如 `LotFrontage` 補以 70.0、`MasVnrArea` 補以 0.0、測試集零星缺漏之地下室與車庫面積補以 0.0）。
- **名義欄位**：以訓練集類別之 **眾數（Mode）** 填補（如 `Electrical` 補以 `'SBrkr'`、`MSZoning` 補以 `'RL'`、`Utilities` 補以 `'AllPub'`、`Exterior1st` 與 `Exterior2nd` 補以 `'VinylSd'`、`SaleType` 補以 `'WD'`）。
- **有序欄位**：非結構性缺漏（如測試集出現之 `KitchenQual`, `Functional`）以訓練集映射整數等級之 **中位數（Median of Training-Mapped Integer Scores）** 填補（如 `KitchenQual` 補以 3 即 TA，`Functional` 補以 8 即 Typ），而非字面眾數，確保等級空間之統計中心性。
- **磚石飾面（`MasVnrType` 與 `MasVnrArea`）顯式缺失指標**：因訓練集之眾數與中位數恰為 `'None'` 與 `0.0`，為防止未記錄/非結構性遺漏與真實無飾面設施相混淆，管線建立專屬之二元指示變數 `MasVnrType_is_missing` 與 `MasVnrArea_is_missing`，使兩者在特徵空間中具備嚴格可區隔性。
- **轉換後完整性**：訓練集、驗證集與測試集在轉換後的 248 個特徵中，**NaN 總數均為 0**（100% 完整無遺漏）。

---

## 4. 特徵編碼與維度轉換 (Feature Categorization & Encodings)

### 4.1 原始 79 個預測變數之重構分類 `[Verified / 已驗證]`
依據資料字典定義與派工要求，79 個原始預測變數分為三類：

1. **數值型特徵（35 項）**：
   - 包含連續尺度與離散計數特徵：`LotFrontage`, `LotArea`, `OverallQual`, `OverallCond`, `YearBuilt`, `YearRemodAdd`, `MasVnrArea`, `BsmtFinSF1`, `BsmtFinSF2`, `BsmtUnfSF`, `TotalBsmtSF`, `1stFlrSF`, `2ndFlrSF`, `LowQualFinSF`, `GrLivArea`, `BsmtFullBath`, `BsmtHalfBath`, `FullBath`, `HalfBath`, `BedroomAbvGr`, `KitchenAbvGr`, `TotRmsAbvGrd`, `Fireplaces`, `GarageYrBlt`, `GarageCars`, `GarageArea`, `WoodDeckSF`, `OpenPorchSF`, `EnclosedPorch`, `3SsnPorch`, `ScreenPorch`, `PoolArea`, `MiscVal`, `MoSold`, `YrSold`。
2. **有序型特徵（19 項）**：
   - 具備語意等級順序之文字特徵，依字典映射為整數等級：`ExterQual`, `ExterCond`, `BsmtQual`, `BsmtCond`, `BsmtExposure`, `BsmtFinType1`, `BsmtFinType2`, `HeatingQC`, `KitchenQual`, `Functional`, `FireplaceQu`, `GarageFinish`, `GarageQual`, `GarageCond`, `PavedDrive`, `PoolQC`, `Fence`, `LotShape`, `LandSlope`。
3. **名義型特徵（25 項）**：
   - 無等級順序之分類標籤，採用 One-Hot 編碼展開。特別是 `MSSubClass`，依據指示視為名義代碼而非連續整數：`MSSubClass`, `MSZoning`, `Street`, `Alley`, `LandContour`, `Utilities`, `LotConfig`, `Neighborhood`, `Condition1`, `Condition2`, `BldgType`, `HouseStyle`, `RoofStyle`, `RoofMatl`, `Exterior1st`, `Exterior2nd`, `MasVnrType`, `Foundation`, `Heating`, `CentralAir`, `Electrical`, `GarageType`, `MiscFeature`, `SaleType`, `SaleCondition`。

### 4.2 特徵維度展開清冊 `[Verified / 已驗證]`
特徵轉換後的維度組成如下表所示：

| 特徵群組 | 特徵數量 | 說明 |
|---|---|---|
| 連續與離散數值特徵 | 35 | 保留原始尺度，缺失以訓練集配適中位數填補 |
| 物理存在指示變數 | 7 | 二元實體標記（`HasGarage` ~ `HasMiscFeature`） |
| 非結構性缺失指示變數 | 2 | 二元缺失標記（`MasVnrType_is_missing`, `MasVnrArea_is_missing`） |
| 有序等級數值特徵 | 19 | 依據資料字典序號映射為整數（0 ~ 8） |
| 名義類別 One-Hot Dummy | 185 | 由 25 個名義欄位依訓練集 1,168 筆中觀察到的水準展開 |
| **總編碼特徵數量** | **248** | **三分割集特徵數量與排列順序完全一致** |

### 4.3 未知類別容錯防護機制 (Unknown Category Handling) `[Verified / 已驗證]`
在真實預測環境中，測試資料常包含訓練階段未見之罕見類別。本管線實作 `handle_unknown='ignore'` 防護：
- 當遇見未知類別時，該欄位所對應的所有訓練 One-Hot Dummy 一律設為 `0.0`。
- 管線不拋出例外，維持特徵矩陣之維度固定為 248 欄。
- 實證觀測之未知類別事件（僅保留分割集層級安全匯總計數，精確類別值僅記錄於地端 ignored 產物中）：
  - **驗證集**：觀測到 1 次未見名義類別事件（One-Hot Dummy 安全設為全 0）。
  - **競賽測試集**：觀測到 1 次未見名義類別事件（One-Hot Dummy 安全設為全 0）。
- 上述未知類別事件之精確欄位與水準皆安全隔離追蹤於本地 ignored 之 `prep_profile.json` 與品質報告中。

---

## 5. 異常值候選與標的隔離 (Target Isolation & 61 IQR Candidates)

### 5.1 識別碼與標的變數隔離 `[Verified / 已驗證]`
- **識別碼 (`Id`)**：完整保留於 `TransformResult.ids` 中，用於後續提交檔之關聯比對，嚴格自特徵矩陣 $X$ 剔除。
- **目標變數 (`SalePrice`)**：僅於具備標籤之資料集產出於 `TransformResult.y`，競賽測試集之 `y` 為 `None`。

### 5.2 61 筆 SalePrice IQR 異常值候選處置 `[Verified & Assumed]`
在 Phase 2 資料理解階段，透過 Tukey 四分位距準則（$IQR = Q_3 - Q_1 = \$214,000 - \$129,975 = \$84,025$）標記出 61 筆離群候選值（精確下界 $\$3,937.50$，精確上界 $\$340,037.50$；四捨五入整數表示為 $\$4,000$ 與 $\$340,000$）。

本階段資料準備針對此 61 筆候選之決策與執行如下：
1. **100% 完整保留**：在 1,168 筆訓練集與 292 筆驗證集之目標向量 $y$ 中，61 筆異常值全數在位，未執行任何刪除、截斷或替換。
2. **決策依據**：
   - 經領域分析，該 61 筆高價物件主要座落於高價社區（如 StoneBr, NridgHt, NoRidge），其建坪、品質均屬頂級，為真實市場反映而非資料登錄錯誤。
   - 隨意剔除高房價極端值將導致模型在預測高端市場時嚴重低估（產生向下的系統性偏差）。
   - Phase 3 屬於資料準備階段，不可進行任何模型評估或假設性剪裁；該異常值對於迴歸殘差的影響，應由 Phase 4 透過目標變數對數轉換與強健迴歸模型進行實證檢定。

---

## 6. 特徵映射與地端研究產物 (Feature Mapping & Artifacts)

### 6.1 產出目錄與清單 `[Verified / 已驗證]`
所有資料準備之中繼結構與元資料均儲存於主 checkout ignored 目錄：
`<local-root>/research/phase3-data-prep/`（預設為專案主 checkout 之 `local/research/phase3-data-prep/`）

| 產物檔案名稱 | 內容摘要與用途 | 資料治理屬性 |
|---|---|---|
| `prep_profile.json` | 記錄資料雜湊、種子、分割統計、前後缺失率、未知類別事件與特徵維度清冊 | 結構化元資料（JSON） |
| `feature_mapping.json` | 原始 79 個變數對應至 248 個特徵之完整映射、補值中位數、眾數與類別表 | 結構化特徵字典（JSON） |
| `feature_manifest.csv` | 248 個特徵之索引、特徵名、原始欄位來源、編碼型態與補值策略清冊 | 欄位清單（CSV） |
| `quality_report.md` | 本地研究記錄與品質檢驗摘要報告 | 人類可讀文件（Markdown） |

### 6.2 資料邊界承諾 `[Verified / 已驗證]`
依據專案 [Security and Data Policy](../../docs/SECURITY_AND_DATA_POLICY.md)，**嚴禁將轉換後的逐筆特徵陣列（Row-level Array/CSV）提交至 Git**。僅提交代碼、單元測試、本技術文件與必要之安全度量清冊。

---

## 7. 研究限制與 Phase 4 候選假設 (Limitations & Phase 4 Hypotheses)

### 7.1 本階段研究限制與陳述邊界 `[Verified & Assumed]`
1. **尺度未標準化**：本管線保留了連續數值變數的原始物理尺度（如平方英尺、年份），尚未執行 Z-score 標準化或 Min-Max 縮放。這是為了使非線性樹狀模型（如 LightGBM, Random Forest）能保有最佳可解釋性；線性模型若需要特徵縮放，應於 Phase 4 建模管線中透過 `StandardScaler` 串接。
2. **未進行特徵交互作用衍生**：本階段僅執行基礎清洗、結構性缺失拆解與標準編碼，未引入領域複合特徵（例如 `TotalSF = 1stFlrSF + 2ndFlrSF + TotalBsmtSF` 或 `AgeAtSale = YrSold - YearBuilt`）。此類工程衍生特徵將作為 Phase 4 的候選假設進行控制實驗。
3. **無監督式篩選**：展開的 185 個 One-Hot 特徵中包含極度稀疏的欄位，本階段刻意不做篩除，以維持資料集特徵完整度。

### 7.2 Phase 4 建模待辦與候選假設 (Candidate Hypotheses) `[Assumed / 待檢定假說]`

| 假說編號 | 假說內容 (Hypothesis Statement) | 預期檢定方法 (Evaluation Strategy) | 狀態 |
|---|---|---|---|
| **H1** | 對標的變數 `SalePrice` 進行對數轉換 $\log(1 + y)$，能顯著改善線性模型之殘差常態性與同質變異性，降低驗證集 RMSLE。 | 在 292 筆驗證集上比較原始尺度迴歸與對數尺度迴歸之 RMSLE。 | `[Assumed / 待檢定]` |
| **H2** | 19 個有序特徵採用「整數等級編碼（Ordinal Integer）」相較於「One-Hot 展開」，能大幅降低參數維度並減少共線性，提升線性迴歸之泛化表現。 | 比較兩種編碼方案在 Ridge/Lasso 交叉驗證下的誤差與係數穩定度。 | `[Assumed / 待檢定]` |
| **H3** | 引入建築年齡（`YrSold - YearBuilt`）與總樓地板面積（`TotalSF`）等領域合成特徵，將具備高於單一原始特徵的特徵重要性與解釋力。 | 透過樹狀模型之特徵重要性（Feature Importance）與消融實驗（Ablation Study）驗證。 | `[Assumed / 待檢定]` |
| **H4** | 針對 185 個 One-Hot 稀疏特徵採用方差閾值篩除（Variance Threshold）或 L1 正則化懲罰，能有效防止模型在測試集產生過擬合。 | 檢驗不同正則化強度 $\alpha$ 下驗證集誤差之收斂曲線。 | `[Assumed / 待檢定]` |
