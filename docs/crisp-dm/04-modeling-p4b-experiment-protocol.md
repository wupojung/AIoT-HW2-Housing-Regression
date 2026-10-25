# CRISP-DM Phase 4 — P4-B-A：特徵選擇與正則化實驗協定（Issue #21 / #22）

- **協定版本**：v1.0 (Draft Candidate - Under Review)
- **所屬任務**：Phase 4-B-A 特徵選擇與正則化比較實驗
- **關聯 Issue**：Issue #21（P4-B 特徵選擇規劃）、Issue #22（P4-B-A 協定凍結）
- **基準版本 (BASE SHA)**：`ee03a51978a0f615f39b656bee318946dcddd890`（已整併 P4-A 基準模型）
- **前次審查修訂點 (Amendment BASE)**：`81302acdec18c3513256916e4d2908cdbad42de9`
- **協定狀態**：Draft Candidate（A1 階段協定凍結審查草案；本協定目前處於審查修改階段，待通過 A1 Review Gate 審定前不代表正式批准；本階段僅制定規範與設計合約，嚴格禁止執行真實資料實驗、模型擬合、單元測試、基準測試、CI 觸發或 A2+ 實作）

---

## 1. 範圍、歷史對照與資料隔離邊界（Scope, Baseline & Data Boundaries）

1. **開發資料列數嚴格限制**：
   - 僅使用 Phase 3 外層 80/20 切分（固定 `seed=42`）劃分出之 **1,168 筆開發訓練列（Development Train Rows）**。
   - **292 筆封存保留集（Sealed Holdout Rows）** 於本階段維持密封狀態，串流讀檔時遇到對應行必須略過、不解析，嚴格禁止在 Phase 4 特徵選擇或超參數調校中窺探、計算或評估。
   - **1,459 筆 Kaggle 競賽測試集（Competition Test Rows）** 完全不開啟、不存取。
2. **歷史 P4-A 基準模型對照（Historical P4-A Baseline Context）**：
   - 依據專案既有成果文檔 [`04-modeling-p4a-ols-baseline.md`](04-modeling-p4a-ols-baseline.md)，P4-A 全特徵未懲罰最小範數 SVD OLS 基準模型在 1,168 筆開發集 5 折 CV 上之歷史表現為：
     - **驗證 RMSE 平均（樣本 SD）**：`36,855.78 (7,938.31)`
     - **驗證 R² 平均（樣本 SD）**：`0.763579 (0.079686)`
   - *明確邊界宣告*：上述數值僅作為本實驗之歷史比較對照背景（Historical Context），絕非 P4-B 之新量測數據；P4-A 之係數大小亦不代表特徵重要性。
3. **外層交叉驗證（Outer CV）規範**：
   - 採用標準 `sklearn.model_selection.KFold(n_splits=5, shuffle=True, random_state=42)`。
   - 折大小嚴格為 234 / 234 / 234 / 233 / 233 筆。
   - **外層折分配摘要來源與驗證性**：
     - 外層成員與折分配 SHA-256 摘要值為：`7c9f1d00eb74d8a281ba41ed47d5ebbdbffa0513b4bb778b70d1571735ad6463`。
     - **來源佐證（Provenance Verification）**：該摘要已在基準版本 `ee03a519` 之 P4-A 實作（`tests/modeling/test_p4a_ols_cv.py` 與 `docs/crisp-dm/04-modeling-p4a-ols-baseline.md`）中獲得獨立合成回歸測試與程式碼驗證，確認具備完整來源憑據（Verified Provenance）。
     - 本階段僅引用該既定摘要進行外層成員檢驗，絕不重新計算、變更折分配或存取已封存之資料集。
4. **授權開發資料集標準化指紋摘要合約（Canonical Dataset Fingerprint Specification）**：
   - 為在不洩漏或儲存逐列真實資料、私有識別碼的前題下，消除字元分隔歧義與型別碰撞（Collision-Safe Canonicalization），規範在後續 A2 階段由核可之載入器依以下合約計算標準化摘要（Canonical Dataset Digest）：
     - **列排序**：嚴格依原始訓練 CSV 中 1,168 筆授權開發列之原始出現順序（Source-Row Order）排列。
     - **欄位選取與固定順序**：排除 `Id` 與私有欄位；包含 79 個原始候選預測欄位（依欄位名稱 ASCII 字典序排序）及最後目標欄位 `SalePrice`（共 80 欄）。
     - **防碰撞型別與長度前綴序列化（Typed & Length-Prefixed Serialization）**：
       - 每列序列化為二進位串流，每個欄位編碼為：`[TypeTag: 1 byte][Length: 4 bytes big-endian unsigned int][Payload: Length bytes]`。
       - **型別標記（TypeTag）定義**：
         - `0x00` = `NULL`（缺失值/NaN；Length 為 0，Payload 為空）。
         - `0x01` = `STRING`（字串值；包括真值為空字串 `""`，Payload 為 UTF-8 正規化位元組，Length 為其位元組長度）。
         - `0x02` = `INT`（整數值；以標準十進位 ASCII 字串或 64 位元整數 Payload 表示）。
         - `0x03` = `FLOAT`（浮點數；規範化為 IEEE 754 雙精度 64 位元 big-endian 二進位位元組，或標準格式化十進位字串）。
       - 藉由明確區分 `0x00` (Null) 與 `0x01` (Empty string)，並採長度前綴而非單純符號分隔，徹底杜絕包含逗號、換行或引號時的字串切割碰撞。
     - **雜湊演算法**：對全體 1,168 筆序列化位元組串流計算 SHA-256。
     - **儲存邊界**：該指紋僅記錄於受 Git 忽略之私有中繼資料（`p4b_manifest.json`），公開輸出僅標註校驗狀態（如 `dataset_fingerprint_verified: true`）。A1 階段嚴禁計算或存取真實指紋。

---

## 2. 巢狀交叉驗證與特徵選擇架構（Nested CV Architecture）

為避免在特徵選擇與超參數調校過程中產生嚴重的選擇樂觀偏差（Selection Bias）與資訊洩漏（Information Leakage），本實驗嚴格採用**兩層巢狀交叉驗證（Nested Cross-Validation）**架構：

```
1,168 Development Rows
│
├── Outer 5-Fold CV (Outer Train: ~934 rows, Outer Val: ~234 rows)
│   │
│   ├── [內層 Inner Loop: 僅在當前折的 Outer Train 上進行]
│   │   ├── 凍結內層切分: KFold(n_splits=3, shuffle=True, random_state=1042)
│   │   │   (產生固定 3 組 Inner Train: ~623 rows / Inner Val: ~311 rows 分割清單)
│   │   │
│   │   ├── 每一折 (Inner Train, Inner Val)：
│   │   │   ├── 從原始資料列在 Inner Train 獨立執行 fit AmesDataPreparationPipeline
│   │   │   ├── transform Inner Train 與 Inner Val
│   │   │   ├── 【重要防洩漏合約】特徵選擇程序（Filter, SFS, RFE, Lasso, ElasticNet）
│   │   │   │   僅在 Inner Train 上依訓練集內部準則擬合並決定候選特徵路徑；
│   │   │   │   Inner Val 保持未受接觸，僅用於單次預測評分；
│   │   │   ├── 對各候選 K 或正則化超參數 alpha，以選定特徵在 Inner Train 擬合模型
│   │   │   └── 對 Inner Val 評估單次預測 RMSE，計算跨 3 個 Inner Val 的平均驗證 RMSE
│   │   │
│   │   └── 依內層平均驗證 RMSE 選出各軌道最佳超參數（最佳 K* 或正則化參數 alpha*）
│   │
│   └── [外層重新擬合與評估 Outer Refit & Evaluation]
│       ├── 在 Outer Train 全體（~934 rows）重新從原始列 fit 一個全新的外層前處理器
│       ├── 以決策之 K* 或 alpha*，在 Outer Train 上完全重新執行特徵選擇程序以取得特徵子集
│       ├── 重新在 Outer Train 擬合模型：
│       │   ├── Track A 重新擬合 SVD OLS
│       │   └── Track B 重新擬合原生正則化模型
│       ├── 對 Outer Val（~234 rows）執行單次 Transform 與【各自單次】模型預測：
│       │   ├── Track A 產生單次 Outer OOF 預測與泛化指標
│       │   └── Track B 產生單次 Outer OOF 預測與泛化指標
│       └── Outer Val 在兩軌道最終預測前絕不接觸，且預測結果絕不回饋至調校決策
```

### 具體隔離合約
1. **內層前處理禁止跨折預先擬合**：
   - 嚴格禁止在進入內層 3 折前於 Outer Train（約 934 筆）或全部 1,168 筆上預先 `fit` 前處理器（例如數值中位數、類別眾數、編碼水準或標準化尺度）。
   - 內層每一折（Inner Fold）必須各自從原始資料列開始，在該 Inner Train（約 623 筆）上獨立執行 `pipeline.fit()`，Inner Val（約 311 筆）僅能進行 `transform()`。
2. **超參數選擇與外層重新執行特徵選擇（Outer Refit via Re-Execution）**：
   - **禁止合併內層特徵集合**：內層 3 折之特徵選擇僅用於評估與決策最佳**超參數**（最佳特徵數 $K^*$ 或最佳正則化強度 $\alpha^*$），3 個內層折各自選出的特徵子集可能不同，**絕不進行特徵名稱聯集（Union）或將內層子集作為最終特徵集**。
   - **外層重選流程**：
     - 在 Outer Train（~934 筆）全體從原始資料重新 `fit` 一個全新的外層前處理器。
     - 以決策出的 $K^*$ 或 $\alpha^*$，在該 Outer Train 的特徵矩陣上**重新完整執行特徵選擇程序**。
     - 取得該 Outer Fold 專屬的外層選定特徵名稱集合。
     - Track A 擬合 SVD OLS，Track B 擬合原生模型，分別對 Outer Val 進行一次性預測產出 Outer OOF。兩軌道彼此完全獨立。

---

## 3. 折內動態候選特徵空間與 Phase 3 前處理行為對齊合約（Fold-Local Schema & Phase 3 Alignment）

1. **折內動態欄位空間**：
   - Phase 3 前處理管道（`AmesDataPreparationPipeline`）中的類別 One-Hot 編碼水準由各折訓練集動態學習。
   - 原始資料集具有 79 個候選預測變數（排除 `Id` 與目標變數 `SalePrice`），此 79 個原始欄位僅作為上游來源欄位定義（Source Column Mapping），並非最終模型空間。
   - 在 P4-A 的 5 折外層訓練中，觀察到的折內編碼後特徵數分別為 240, 241, 243, 248, 245。
   - **核心合約**：絕不強制固定編碼後欄位數為 248，亦不得在全體 1,168 筆上預先擬合全局特徵字典（Vocabulary）。所有候選特徵空間皆為該次訓練切分之**折內局部空間（Fold-Local Universe）**。
2. **Phase 3 前處理未知類別行為嚴格對齊（Strict Alignment with Phase 3 `handle_unknown='ignore'`）**：
   - 依據專案既有 Phase 3 管道實作（`python/src/housing_regression/data_prep/pipeline.py:84,404`），類別編碼器採用 `OneHotEncoder(handle_unknown='ignore')`：
     - 當驗證集（Inner Val 或 Outer Val）中出現該折訓練集未見過之新類別水準時，編碼器**自動輸出全 0 指示向量**，絕不產生額外的新欄位，亦不會拋出例外。
     - 折內選出之特徵欄位清單在該次擬合分區內完全自洽，**不存在跨折補 0 或人為剔除新欄位的操作**。
     - 跨折特徵穩定性分析時，以字串欄位名稱為統計依據，特徵選擇頻率的分母明確定義為外層折數 5（例如某欄位在外層 5 折中被選中 4 次，則頻率為 4/5 = 80%）。
3. **折內編碼維度硬上限合約（Enforced Dimension Ceiling & Fail-Closed Policy）**：
   - 為防止極端異常或編碼爆炸，本協定嚴格設定折內編碼特徵維度硬上限：
     $$D_{\text{ceiling}} = 300 \text{ 欄}$$
   - **防禦中斷機制（Fail-Closed Policy）**：在任何訓練分區執行完前處理後，若產生的特徵維度 $D_{\text{obs}} > D_{\text{ceiling}}$，**必須立即中止運行並拋出 `DimensionCeilingExceededError`**。嚴格禁止在背後靜默截斷或刪除特徵欄位。
4. **候選子集大小規範**：
   - 對於 Filter、Forward SFS 與 RFE，候選特徵數 $K$ 嚴格限定為集合：
     $$K \in \{2, 3, 5, 10, 20\}$$
   - 嚴格禁止評估未列入本合約之其他 $K$ 值。

---

## 4. 候選特徵選擇演算法與版本鎖定合約（Algorithm Contracts & Version Pinning）

### 4.1 環境與相依套件版本完全鎖定（Pinned Environment Contract）
依據專案根目錄 `requirements.in` 與 `requirements.lock`，本協定嚴格鎖定執行環境版本，並註記官方 API 依據：
- **Python**: 3.12 (依 lock 建置環境規範)
- **scikit-learn**: `1.9.1`
  - [`KFold`](https://scikit-learn.org/1.9/modules/generated/sklearn.model_selection.KFold.html)
  - [`StandardScaler`](https://scikit-learn.org/1.9/modules/generated/sklearn.preprocessing.StandardScaler.html)
  - [`OneHotEncoder`](https://scikit-learn.org/1.9/modules/generated/sklearn.preprocessing.OneHotEncoder.html)
  - [`Ridge`](https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.Ridge.html)
  - [`RFE`](https://scikit-learn.org/1.9/modules/generated/sklearn.feature_selection.RFE.html)
  - [`Lasso`](https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.Lasso.html)
  - [`ElasticNet`](https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.ElasticNet.html)
  - [`LassoCV`](https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.LassoCV.html)（官方 CV 介面參考）
  - [`ElasticNetCV`](https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.ElasticNetCV.html)（官方 CV 介面參考）
- **numpy**: `2.5.4`
  - [`numpy.linalg.lstsq`](https://numpy.org/doc/2.5/reference/generated/numpy.linalg.lstsq.html)
- **pandas**: `3.1.0`
- **scipy**: `1.18.1`
- 嚴格禁止使用 `>=`、`+` 或「預設未指定」之模糊版本與參數配置。

### 4.2 內層交叉驗證分割器凍結（Inner Splitter Freeze）
- 所有演算法在內層 3 折評估時，共用同一份由以下參數產生的內層分割清單：
  ```python
  inner_cv = KFold(n_splits=3, shuffle=True, random_state=1042)
  ```
- 內層分割在每次 Outer Fold 內部固定產生，確保所有候選方法、不同 $K$ 值及超參數網格皆在完全相同的樣本分組上評估。

### 4.3 濾窗法（Filter Method: Pearson Correlation |r|）
- **單一指標凍結**：嚴格鎖定使用 Pearson 相關係數絕對值 $|r|$：
  $$r(X_j, y) = \frac{\sum (X_{ij} - \bar{X}_j)(y_i - \bar{y})}{\sqrt{\sum (X_{ij} - \bar{X}_j)^2 \sum (y_i - \bar{y})^2}}$$
- **邊界與極端值處理**：
  - **常數欄位（$\sigma=0$）**：若特徵在訓練分區標準差為 0，強制賦予分數 $0.0$。
  - **非有限值（NaN/Inf）**：前處理異常產生之非有限值，強制賦予分數 $-1.0$。
- **平手決策（Tie-Breaking）**：
  - 若 $|r|$ 分數相同（容差 $10^{-9}$ 內），嚴格依照特徵名稱字串之 ASCII 字典順序（Lexicographical ascending order）升冪排列決策。
- **選取規則**：選取分數最高之前 $K \in \{2, 3, 5, 10, 20\}$ 個特徵。

### 4.4 循序向前選擇法防洩漏合約（Forward SFS: Training-Set Greedy Contract）
- **防止驗證集洩漏合約（Leakage-Safe Selection Flow）**：
  - 為杜絕使用內層驗證折來指導貪婪特徵挑選所帶來的二次選擇偏差，**SFS 的向前貪婪挑選程序必須且僅能在該分區之訓練集（Inner Train 或 Outer Train）內部完成**。
  - **貪婪加入準則**：從空集合開始，在訓練分區上擬合未懲罰 SVD OLS，每一步貪婪地將使**該訓練分區殘差平方和（Train RMSE）最小化**之單一特徵加入集合，逐步建構出包含 $K_{\max}=20$ 個特徵之固定序列路徑 $\langle f_1, f_2, \dots, f_{20} \rangle$。
  - **候選 $K$ 評估**：針對 $K \in \{2, 3, 5, 10, 20\}$，取前 $K$ 個特徵，在未受接觸之該折 Inner Val 上進行單次預測評估，計算驗證 RMSE。
  - **超參數選擇**：以 3 個 Inner Val 的平均驗證 RMSE 評估並選出最優之 $K^*$。
  - **外層重選**：在 Outer Train（~934 筆）全體上，重新完全依照上述「訓練集殘差最小化」向前挑選至 $K^*$ 個特徵，最後擬合 Track A 最終 OLS。
  - **平手決策**：若訓練集 RMSE 改善幅度在 $10^{-9}$ 內相同，優先挑選特徵名稱 ASCII 字典序最小之特徵。

### 4.5 遞迴特徵消除法（RFE: Recursive Feature Elimination）
- **基底估計器**：`sklearn.linear_model.Ridge(alpha=1.0, random_state=42, solver='auto')`。
- **特徵重要性評估**：回歸係數絕對值 $|\beta_j|$。
- **消除路徑**：在當前訓練分區上擬合 Ridge，每次剔除 $|\beta_j|$ 最小之 1 個特徵（`step=1`），由 $D_{\text{obs}}$ 步步剃除至 $K_{\min}=2$。
- **平手決策**：若係數絕對值相同（容差 $10^{-9}$ 內），優先淘汰特徵名稱字典順序較大者（保留字典序較小者）。

### 4.6 LassoCV 與 ElasticNetCV 之客製無洩漏適配器合約（Caller-Managed CV Adapter Contract）
- **設計決策與命名對齊說明（Interface Decision Trail）**：
  - 需求中指定比較之方法名稱為 **LassoCV** 與 **ElasticNetCV**。
  - **架構衝突與解決方案**：在 `scikit-learn 1.9.1` 中，若直接呼叫內建的 `LassoCV(cv=3)` 類別，該類別要求傳入已經 One-Hot 編碼與標準化後的全局特徵矩陣，這將導致內部驗證折受到全體前處理統計量之洩漏。此外，1.9.1 移除了 `n_alphas` 參數。
  - **正式凍結決策**：本協定將 LassoCV 與 ElasticNetCV 在系統內部具體實作為**「客製無洩漏交叉驗證適配器（Leakage-Safe Caller-Managed CV Adapter）」**。此適配器在外部保留 LassoCV / ElasticNetCV 之方法識別名稱與超參數調校語意，底層則透過嚴格折內擬合前處理管道驅動基礎 `Lasso` 與 `ElasticNet` 估計器進行網格搜尋，確保滿足資料隔離合約。此設計決策列入 A1 凍結記錄，提交 Review Gate 備查。
- **超參數網格設定**：
  - **Lasso $\alpha$ 網格**：預先註冊之幾何等比數列，固定 50 個點：
     $$\alpha \in \text{logspace}(\log_{10}(1000), \log_{10}(0.1), 50)$$
     *網格決策說明*：$[0.1, 1000]$ 為預先註冊之設計區間，涵蓋強正則化至弱正則化之平滑衰減路徑；A1 階段不預先探測資料（Uncertainty noted），若後續實驗顯示最優解觸及端點，將如實揭露邊界約束。
  - **ElasticNet 網格**：
     - `l1_ratio` $\in [0.1, 0.5, 0.7, 0.9, 0.95, 0.99]$（共 6 個值）。
     - $\alpha \in \text{logspace}(\log_{10}(1000), \log_{10}(0.1), 30)$（共 30 個點）。
  - 估計器收斂參數：`max_iter=5000`，`tol=1e-4`。

---

## 5. 特徵縮放與懲罰項可比性合約（Feature Scaling & Penalty Comparability）

1. **分區獨立縮放（Partition-Local Scaling）**：
   - 數值與序數特徵之標準化（`StandardScaler`）必須且僅能在**當前訓練分區（當前 Inner Train 或 Outer Train）** 上 `fit`，驗證分區僅進行 `transform`。
   - One-Hot 虛擬變數（0/1）初始保持未縮放（Unscaled 0/1）。
2. **懲罰項尺度不可比性限制宣告（Known Theoretical Limitation）**：
   - 當數值特徵標準化為單位方差（$\sigma=1$），而 One-Hot 欄位維持 $0/1$ 時，各特徵的尺度與經驗方差並不相同。此時 $L_1$ 或 $L_2$ 正則化施加於係數上時，對稀疏類別特徵與連續特徵的懲罰力道實質上不對稱。
   - 本協定將此列為「已知理論限制與不變設定」，在報告與成果中明確記錄，不進行人為隨意加權，以保持特徵工程管道之標準化與可追溯性。

---

## 6. 雙軌獨立評估策略與奇異值分解 OLS 規範（Two Independent Tracks & SVD OLS Specification）

本實驗評估兩條互相獨立的軌道，各自具有獨立的超參數選擇與外層重新擬合程序：

| 軌道 | 名稱 | 估計器與預測機制 | 評估目標與超參數選擇依據 |
|---|---|---|---|
| **Track A** | **Selected Features + OLS Refit** | 以選定之特徵子集（Filter/SFS/RFE 之 $K$，或 Lasso/ElasticNet 之非零特徵），**在訓練分區使用未懲罰 SVD OLS 重新擬合**。 | 評估特徵子集的**資訊代表性**與維度縮減效果。其超參數（$K^*$ 或 $\alpha^*_A$）**嚴格依據內層 SVD OLS Refit 驗證 RMSE 決定**。 |
| **Track B** | **End-to-End Native Regularized Model** | 直接使用正則化演算法（Lasso / ElasticNet）原生權重進行預測。 | 評估正則化演算法本身在**方差收縮與多重共線性抑制**下的預測能力。其超參數 $\alpha^*_B$ **嚴格依據內層原生正則化預測驗證 RMSE 決定**。 |

### 奇異值分解 OLS 數值規格（Deterministic SVD OLS Specification）
- **與 P4-A 求解器之一致性決策（Solver Specification Note）**：
  - 基準版本 `ee03a519` 之 P4-A 實作（`python/src/housing_regression/modeling/ols_cv.py:169`）調用 `np.linalg.lstsq(design, y, rcond=None)`。
  - **P4-B-A 凍結決策**：本協定在 Track A 重新擬合及 SFS 候選評估中，**統一切換至顯式設定 `rcond=None`（明確對齊 P4-A 既有行為）**，以保持跨階段最小範數解數值一致性。
- **數值診斷指標計算合約**：
  - 對設計矩陣 $X$ 進行奇異值分解 $S$。
  - **截斷閾值**：$\tau = \epsilon_{\text{mach}} \cdot \max(M, N) \cdot \max(S)$（對應 `rcond=None` 之內建閾值）。
  - **有效秩（Effective Rank）**：滿足 $s_i > \tau$ 之奇異值數量。
  - **零化度（Nullity）**：總欄數 - 有效秩。
  - **有效條件數（Effective Condition Number）**：$\max(S) / \min(\{s_i \in S \mid s_i > \tau\})$。若無非零奇異值則記為 null。

---

## 7. 內層選取準則、平手決策與樂觀偏差（Selection Criteria & Optimism）

1. **內層目標函數**：
   - 內層 3 折交叉驗證之平均驗證均方根誤差（Mean Validation RMSE）：
     $$\text{Score} = \frac{1}{3} \sum_{m=1}^3 \text{RMSE}_m$$
2. **確定性全序平手決策階層（Deterministic Total-Order Tie-Breaking）**：
   - 浮點數比較容差設為 $\epsilon = 10^{-9}$。
   - **平手決策嚴格在各 Track 內部獨立套用，全序規則（Total Order）定義如下**：
     - **Track A 內部確定性全序平手規則**：
       1. 優先選取特徵數較少者（Sparsity priority）。
       2. 若特徵數相同，依候選演算法順序：Filter $\to$ Forward SFS $\to$ RFE $\to$ Lasso $\to$ ElasticNet。
       3. 若同一演算法內仍平手，選取候選 $K$ 較小者（或 $\alpha$ 較大者；若 ElasticNet 則次選 `l1_ratio` 較大者）。
     - **Track B 內部確定性全序平手規則**：
       1. 若多個超參數之內層平均 RMSE 差異在 $\epsilon$ 內，依固定方法順序決策：**LassoCV 優先於 ElasticNetCV**。
       2. 在同一方法內部若仍平手，優先選取正則化強度較大者（較大之 $\alpha$）。
       3. 若 ElasticNetCV 且 $\alpha$ 相同，優先選取 `l1_ratio` 較大者（偏好更稀疏之 $L_1$ 懲罰）。
       4. 若仍平手，依候選網格產生之原初順序取最前者。
3. **無 1-SE 法則（No 1SE Rule）**：
   - 嚴格以內層驗證平均 RMSE 最小者勝出，不採用啟發式的 1 個標準誤差準則（1SE Rule）。
4. **外層排行榜選擇樂觀偏差警告（Outer Selection Optimism Warning）**：
   - 5 折外層 CV 排行榜之最優分數仍存在選擇樂觀偏差。Phase 5 封存保留集（292 筆 Holdout）必須持續維持密封狀態，作為獨立驗證屏障。

---

## 8. 巢狀交叉驗證原理與明確合成對照（Nested-CV Rationale & Qualitative Synthetic Demo）

### 8.1 為什麼必須採用巢狀交叉驗證？
若在同一層交叉驗證中同時進行特徵篩選與泛化評估，驗證折之資訊將外洩至特徵選擇決定中，使模型評估產生假性高分。

### 8.2 概念說明性合成程式碼對照（Conceptual Qualitative Demonstration）
以下程式碼僅供概念說明設計原理，明確標記為非實驗執行產物：

```python
# =========================================================================
# 【概念說明用合成程式碼：資訊洩漏 vs 巢狀隔離 (Conceptual Demo Only)】
# 本程式碼僅用於定義協定之防洩漏設計原理，嚴禁在 A1 階段執行或引用為實驗數據。
# 數值輸出受有限樣本隨機變異（Finite-sample variability）影響，非保證性實驗測量。
# =========================================================================
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold

# 假設環境：100 筆樣本，1,000 個獨立高斯雜訊特徵，y 亦為純隨機雜訊
np.random.seed(42)
X_synthetic = np.random.randn(100, 1000)
y_synthetic = np.random.randn(100)

# -------------------------------------------------------------------------
# [錯誤模式 Flawed Practice]: 全局篩選特徵後再切分 CV (資訊洩漏)
# -------------------------------------------------------------------------
corrs = np.abs([np.corrcoef(X_synthetic[:, j], y_synthetic)[0, 1] for j in range(1000)])
flawed_selected_idx = np.argsort(corrs)[-5:]

kf = KFold(n_splits=5, shuffle=True, random_state=42)
flawed_val_mse = []
for tr_idx, val_idx in kf.split(X_synthetic):
    reg = LinearRegression().fit(X_synthetic[tr_idx][:, flawed_selected_idx], y_synthetic[tr_idx])
    pred = reg.predict(X_synthetic[val_idx][:, flawed_selected_idx])
    flawed_val_mse.append(np.mean((pred - y_synthetic[val_idx]) ** 2))
# 理論推論預期：因納入與驗證集相關之雜訊特徵，驗證誤差常呈現偏低之選擇樂觀偏差。

# -------------------------------------------------------------------------
# [正確模式 Nested CV]: 嚴格於各折訓練集內部獨立篩選特徵
# -------------------------------------------------------------------------
nested_val_mse = []
for tr_idx, val_idx in kf.split(X_synthetic):
    tr_corrs = np.abs([np.corrcoef(X_synthetic[tr_idx, j], y_synthetic[tr_idx])[0, 1] for j in range(1000)])
    clean_selected_idx = np.argsort(tr_corrs)[-5:]

    reg = LinearRegression().fit(X_synthetic[tr_idx][:, clean_selected_idx], y_synthetic[tr_idx])
    pred = reg.predict(X_synthetic[val_idx][:, clean_selected_idx])
    nested_val_mse.append(np.mean((pred - y_synthetic[val_idx]) ** 2))
# 理論推論預期：驗證集隔離未洩漏，誤差如實反映雜訊本質（受有限樣本變異波動）。
```

---

## 9. 擬合預算、資源控制與防禦中斷機制（Fit Accounting, Resource Controls & Abort Policy）

### 9.1 擬合單位獨立會計定義（Dual Fit Unit Accounting）
- **估計器擬合單位（Estimator Fit Unit）**：定義為一個迴歸估計器（SVD OLS、Ridge、Lasso、ElasticNet）在指定樣本與特徵子集上完成一次參數計算。
- **前處理擬合單位（Preprocessor Fit Unit）**：定義為 `AmesDataPreparationPipeline.fit()` 在特定訓練分區上完成一次特徵工程轉換學習。
- **隔離與複用規則**：在同一訓練分區內部，已擬合完成的前處理特徵矩陣允許在該分區內的不同超參數候選模型間複用；**嚴格禁止跨不同訓練分區（跨 Inner Train、跨 Outer Train）複用前處理器**。

### 9.2 前處理擬合精確次數與硬上限
設外層折數 $M=5$，內層折數 $m=3$：
- 內層 3 折：每折於 Inner Train 執行 1 次 pipeline 擬合，共 $3$ 次。
- 外層重新擬合：於 Outer Train 全體執行 1 次 pipeline 擬合，共 $1$ 次。
- **單一外層折合計**：$3 + 1 = 4$ 次前處理擬合。
- **5 折外層總前處理擬合數**：$5 \times 4 = 20$ 次擬合（若各方法獨立隔離實例化則最多 $5 \text{ 方法} \times 20 = 100$ 次）。
- **前處理擬合硬上限（Preprocessor Fit Cap）**：設為 **$200$ 次擬合**，超過立即中斷。

### 9.3 估計器解析擬合上限精確計算（以硬維度上限 $D_{\text{ceiling}} = 300$ 計算）
設外層折數 $M=5$，內層折數 $m=3$，$D_{\text{ceiling}} = 300$，$K \in \{2, 3, 5, 10, 20\}$（$|K|=5$）：

1. **Filter (Pearson |r|)**：
   - 內層候選 $K$ 評估（Inner Train 擬合 OLS）：$5 \times 3 \times 5 = 75$ 次。
   - 外層重新評估與擬合：$5 \times 1 = 5$ 次。
   - **Filter 估計器擬合數**：$75 + 5 = 80$ 次。
2. **Forward SFS（訓練集貪婪挑選流）**：
   - 每次訓練路徑向前挑選 20 步精確擬合次數：$\sum_{k=1}^{20} (301 - k) = 5,810$ 次。
   - 內層 3 折挑選：$3 \times 5,810 = 17,430$ 次。
   - 外層重新在 Outer Train 挑選至 $K_{\max}=20$：$5,810$ 次。
   - 外層最終 OLS 擬合：$1$ 次。
   - **單一外層折合計**：$17,430 + 5,810 + 1 = 23,241$ 次。
   - **SFS 總擬合數上限（5 折外層）**：$5 \times 23,241 = 116,205$ 次。
3. **RFE (Ridge, step=1)**：
   - 從維度 300 步步剔除至 $K_{\min}=2$：$300 - 2 + 1 = 299$ 次 Ridge 擬合。
   - 內層 3 折消除擬合數：$3 \times 299 = 897$ 次。
   - 內層各候選 $K$ 之 Track A SVD OLS 評估：$3 \times 5 = 15$ 次。
   - 外層重新在 Outer Train 執行 Ridge 消除：$299$ 次 Ridge 擬合。
   - 外層以 $K^*$ 執行 Track A 最終 OLS 擬合：$1$ 次。
   - **單一外層折合計**：$897 + 15 + 299 + 1 = 1,212$ 次。
   - **RFE 總擬合數上限（5 折外層）**：$5 \times 1,212 = 6,060$ 次。
4. **LassoCV (50 alphas, 雙軌獨立評估)**：
   - 內層 3 折：$3 \times 50 = 150$ 次 Lasso 擬合 (Track B) + $3 \times 50 = 150$ 次 SVD OLS 擬合 (Track A)。
   - 外層重新擬合：共 3 次。
   - **單一外層折合計**：$150 + 150 + 3 = 303$ 次。
   - **LassoCV 總擬合數上限（5 折外層）**：$5 \times 303 = 1,515$ 次。
5. **ElasticNetCV (6 l1_ratios $\times$ 30 alphas = 180 組合, 雙軌獨立評估)**：
   - 內層 3 折：$3 \times 180 = 540$ 次 ElasticNet 擬合 (Track B) + $3 \times 540 = 540$ 次 SVD OLS 擬合 (Track A)。
   - 外層重新擬合：共 3 次。
   - **單一外層折合計**：$540 + 540 + 3 = 1,083$ 次。
   - **ElasticNetCV 總擬合數上限（5 折外層）**：$5 \times 1,083 = 5,415$ 次。

- **總理論分析估計器擬合次數**：
  $$\text{Total Estimator Fits} = 80 + 116,205 + 6,060 + 1,515 + 5,415 = 129,275 \text{ 次}$$
- **估計器擬合硬上限（Cumulative Estimator Fit Cap）**：
  $$\text{Cumulative Fit Cap} = 150,000 \text{ 次估計器擬合}$$

### 9.4 雙層資源閘門、A4 啟動校準包絡與中斷合約（Two-Tier Resource Gate & A4 Calibration Envelope）
- **雙層資源防禦機制（Two-Tier Resource Gate Architecture）**：
  - 為消除「限制未設定前不能跑 A4，但 A4 又未測量出限制」之循環相依，本協定嚴格確立雙層資源邊界：
    1. **第 1 層：A4 基準校準安全包絡（A4 Calibration Bootstrap Envelope）**：
       - A4 基準測試僅允許在專案經 Owner 事先核准之一組**明確、有限、正值、Fail-Closed 之校準防禦包絡**（例如微型基準測試單次呼叫秒數與記憶體上限）下啟動執行。
       - 在 Owner 審定該組 A4 啟動包絡設定檔前，A4 基準校準**不得啟動**。
       - A4 之任務即是在此啟動包絡的保護下，完成代表性子集微測量，並據此**量測、凍結並寫入正式執行之數值限制**（`max_wall_seconds` 與 `max_peak_memory_bytes`）。
    2. **第 2 層：正式執行資源閘門（Formal Execution Limits）**：
       - A2 完整測試與後續正式特徵選擇實驗，**在 A4 尚未實測並凍結正式數值限制前，嚴格處於 BLOCKED 狀態**。
       - 若設定檔限制為 null、未設定或正式執行超出該限制，Runner 必須立即中止（Fail-Closed）。
- **檢查點原子寫入與接續身份校驗合約（Checkpoint Resume Identity Contract）**：
  - 以「外層折 + 方法」為單位執行原子寫入（寫入 `.tmp` 檔並驗證 SHA-256 後替換）。
  - **拒絕接續驗證（Resume Refusal Checks）**：當 Runner 嘗試接續執行時，必須完整校驗以下身份條件，任一條件不符則**拒絕接續（Fail-Closed）並建立全新 Run ID**：
    1. 開發資料集標準化指紋摘要完全一致。
    2. Git Code HEAD Commit SHA 完全一致。
    3. 協定版本（`protocol_version: v1.0`）一致。
    4. 依賴套件版本（Python, scikit-learn, numpy, pandas, scipy）完全一致。
    5. 演算法超參數網格與外層/內層 KFold 分割種子完全一致。

---

## 10. 未來合成測試矩陣規劃（Planned Synthetic Test Matrix Specification）

本節為後續階段之測試合約設計規劃（純規格設計，**A1 階段嚴禁實作或執行測試**）：

| 測試案例 ID | 驗證目標 | 測試合約設計與斷言重點 | 隔離層級 |
|---|---|---|---|
| `TEST-P4B-01` | 外層折分一致性 | 驗證 5 折劃分之索引摘要完全符合既定 SHA-256 (`7c9f1d00...`)。 | 離線合成索引 |
| `TEST-P4B-02` | 前處理擬合邊界 Spy | 以 Mock/Spy 攔截器驗證 Preprocessor 絕未在 Inner Val 或 Outer Val 上呼叫 `fit()`。 | 合成虛擬資料 |
| `TEST-P4B-03` | Phase 3未知水準相容性 | 驗證驗證折中未見過之類別水準在 `handle_unknown='ignore'` 下正常產出全 0 向量，無新欄位產生。 | 合成異常類別 |
| `TEST-P4B-04` | 欄位維度超限防禦 | 合成生成超過 300 欄之矩陣，驗證系統必定拋出 `DimensionCeilingExceededError`。 | 邊界壓力測試 |
| `TEST-P4B-05` | 敏感欄位徹底排除 | 驗證特徵矩陣輸入中嚴格排除 `Id` 與 `SalePrice`，否則拋出 `SchemaError`。 | 輸入檢查測試 |
| `TEST-P4B-06` | 極端值與常數防禦 | 注入常數欄位（$\sigma=0$）與非有限值（NaN/Inf），驗證 Filter 與模型平手及降序處理。 | 數值穩定性 |
| `TEST-P4B-07` | 奇異值 SVD OLS 求解 | 在病態矩陣（多重共線性）下驗證最小範數解數值條件數與有效秩計算正確性（`rcond=None`）。 | 數值代數測試 |
| `TEST-P4B-08` | Track A 平手全序一致性 | 注入等效評分之合成特徵，驗證稀疏度優先、固定演算法順序與字典序規則能產生 100% 重現之解。 | 確定性測試 |
| `TEST-P4B-09` | 擬合預算硬上限中斷 | 透過計數器模擬超出 150,000 次估計器擬合，驗證立即觸發 `BudgetExceededError` 中止。 | 防禦熔斷測試 |
| `TEST-P4B-10` | 檢查點原子寫入與校驗 | 注入損毀之 `.tmp` 暫存檔，驗證 SHA-256 校驗失敗並防禦性中斷接續。 | I/O 安全測試 |
| `TEST-P4B-11` | 公開摘要去識別化 | 驗證 `p4b_public_summary.json` 不含任何逐列 OOF、真實標籤或本機敏感路徑。 | 隱私安全測試 |
| `TEST-P4B-12` | 候選 K 值範圍合約 | 驗證選擇器嚴格僅能輸出 $K \in \{2, 3, 5, 10, 20\}$ 之特徵集合，傳入非法 $K$ 拋出異常。 | 參數邊界測試 |
| `TEST-P4B-13` | SFS 訓練集獨立挑選 | 斷言驗證 SFS 貪婪挑選特徵過程僅依賴 Inner Train 殘差，Inner Val 保持未讀取。 | 演算法隔離測試 |
| `TEST-P4B-14` | 指紋防碰撞與重複穩定性 | 驗證型別標記與長度前綴序列化能精確區分 `[Null]` vs `[""]` 及逗號分割碰撞，且重複計算雜湊值 100% 一致。 | 資料完整性測試 |
| `TEST-P4B-15` | 檢查點身份不符拒絕接續 | 模擬變更套件版本或折分種子，驗證 Runner 必定拒絕接續中斷檔並拋出例外。 | 接續安全測試 |
| `TEST-P4B-16` | Track B 確定性全序平手 | 注入相同評分之 Lasso 與 ElasticNet 候選，驗證必定由 Lasso 優先，且同法依 $\alpha$ 降序決策。 | 確定性測試 |

---

## 11. 輸出綱要與產物安全合約（Output Schema & Artifact Boundaries）

所有產物使用純文字 JSON 與 CSV，嚴格禁止使用 SQLite。

### 11.1 私有與公開路徑隔離合約
- **私有產物路徑**：`local/research/phase4-p4b/<run-id>/`。
  - 寫入前執行 `git check-ignore` 驗證，未被忽略則拒絕寫入（Fail-Closed）。
  - 私有產物包含：
    1. `p4b_manifest.json`：包含所有輸出檔案清單、位元組大小、檔案 SHA-256 校驗摘要、以及開發資料集標準化指紋摘要。
    2. `p4b_oof_predictions.csv`：包含逐列 OOF 預測記錄（含 `Id`, `OuterFold`, `Track`, `ActualSalePrice`, `PredictedSalePrice`）。
    3. `p4b_private_details.json`：包含每折各方法選定之特徵名稱清單、特徵頻率表、秩、零化度、有效條件數、各階段耗時與擬合計數。
- **公開摘要產物**：`p4b_public_summary.json`。
  - **公開輸出中嚴格禁止包含任何逐列預測、真實房價或受保護本機路徑**。

### 11.2 產物校驗資訊清單綱要（Manifest Schema）

```json
{
  "_schema_notice": "THIS IS A SCHEMA SPECIFICATION ONLY. CONTAINS NO EXPERIMENTAL RESULTS.",
  "run_id": null,
  "created_at": null,
  "code_head_commit": null,
  "phase3_contract_version": null,
  "dataset_provenance": {
    "development_rows": 1168,
    "outer_fold_digest": "7c9f1d00eb74d8a281ba41ed47d5ebbdbffa0513b4bb778b70d1571735ad6463",
    "canonical_development_dataset_sha256": null
  },
  "file_inventory": [
    {
      "relative_path": "p4b_oof_predictions.csv",
      "sha256": null,
      "byte_size": null,
      "is_public": false
    },
    {
      "relative_path": "p4b_public_summary.json",
      "sha256": null,
      "byte_size": null,
      "is_public": true
    }
  ]
}
```

### 11.3 公開摘要結構綱要（Public Summary Schema，純綱要展示）

```json
{
  "_schema_notice": "THIS IS A SCHEMA SPECIFICATION ONLY. CONTAINS NO EXPERIMENTAL RESULTS.",
  "metadata": {
    "protocol_version": "v1.0",
    "issue_reference": "Issue #21 / Issue #22",
    "base_commit": "ee03a51978a0f615f39b656bee318946dcddd890",
    "historical_p4a_reference": {
      "outer_mean_rmse": 36855.78,
      "outer_std_rmse": 7938.31,
      "outer_mean_r2": 0.763579,
      "context_note": "Historical baseline from docs/crisp-dm/04-modeling-p4a-ols-baseline.md"
    },
    "run_id": null,
    "environment": {
      "python_version": "3.12",
      "sklearn_version": "1.9.1",
      "numpy_version": "2.5.4",
      "pandas_version": "3.1.0",
      "scipy_version": "1.18.1"
    },
    "data_boundary": {
      "development_rows": 1168,
      "outer_kfold": {"n_splits": 5, "shuffle": true, "random_state": 42},
      "inner_kfold": {"n_splits": 3, "shuffle": true, "random_state": 1042},
      "outer_fold_digest": "7c9f1d00eb74d8a281ba41ed47d5ebbdbffa0513b4bb778b70d1571735ad6463",
      "dataset_fingerprint_verified": true,
      "digest_provenance": "verified_in_p4a"
    }
  },
  "method_contract": {
    "filter_pearson": {"k_candidates": [2, 3, 5, 10, 20]},
    "forward_sfs": {"estimator": "SVD_OLS", "k_candidates": [2, 3, 5, 10, 20]},
    "rfe_ridge": {"estimator": "Ridge(alpha=1.0)", "k_candidates": [2, 3, 5, 10, 20]},
    "lasso_cv": {"alphas_count": 50, "inner_cv": 3, "adapter": "caller_managed_grid"},
    "elastic_net_cv": {"l1_ratios": [0.1, 0.5, 0.7, 0.9, 0.95, 0.99], "alphas_count": 30, "inner_cv": 3, "adapter": "caller_managed_grid"}
  },
  "per_outer_fold_results": [
    {
      "outer_fold": null,
      "method": null,
      "track": null,
      "selected_hyperparameter": null,
      "selected_feature_count": null,
      "selected_feature_names": [],
      "outer_val_rmse": null,
      "outer_val_r2": null,
      "numerical_diagnostics": {
        "rank": null,
        "nullity": null,
        "effective_condition_number": null
      },
      "fit_accounting": {
        "fold_estimator_fits": null,
        "fold_preprocessor_fits": null
      },
      "convergence_status": null
    }
  ],
  "aggregate_results": [
    {
      "method": null,
      "track": null,
      "mean_outer_rmse": null,
      "std_outer_rmse": null,
      "mean_outer_r2": null,
      "total_estimator_fits": null,
      "total_preprocessor_fits": null,
      "fit_cap_status": "within_budget"
    }
  ]
}
```

---

## 12. 停機條件與範圍邊界（Stop Conditions & Non-Goals）

- **非目標（Non-Goals）**：
  1. 不得執行任何真實 Ames 資料集讀取或特徵工程計算。
  2. 不得執行任何模型訓練、超參數搜尋或真實指標計算。
  3. 不得實作 A2（測試套件）、A3（Runner 程式碼）、A4（基準測量）或 B 階段之內容。
  4. 不得修改 `main` 分支或操作其他工作樹。
  5. 不得擅自進行工作樹清理或刪除分支。
- **停機條件（Stop Condition）**：
  - 本協定文檔（`docs/crisp-dm/04-modeling-p4b-experiment-protocol.md`）完成修訂並提交於 `feature/p4b-a1-protocol-issue-22` 分支後，執行 `git diff --check` 確認格式乾淨，寫入本機私有結果 handoff，隨即停機報告。
