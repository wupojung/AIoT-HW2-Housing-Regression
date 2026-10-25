# CRISP-DM Phase 4 — P4-B-A：特徵選擇與正則化實驗協定（Issue #21 / #22）

- **協定版本**：v1.0 (Draft Candidate - Amended)
- **所屬任務**：Phase 4-B-A 特徵選擇與正則化比較實驗
- **關聯 Issue**：Issue #21（P4-B 特徵選擇規劃）、Issue #22（P4-B-A 協定凍結）
- **基準版本 (BASE SHA)**：`ee03a51978a0f615f39b656bee318946dcddd890`（已整併 P4-A 基準模型）
- **前次審查提交 (Reviewed Candidate HEAD)**：`5c335e47d8b97cd340f55070aa0492bdcca2978e`
- **協定狀態**：Draft Candidate（A1 階段協定凍結草案修訂版；本階段僅制定規範與設計合約，嚴格禁止執行真實資料實驗、模型擬合、單元測試、基準測試、CI 觸發或 A2+ 實作）

---

## 1. 範圍與資料隔離邊界（Data Boundary & Partitioning）

1. **開發資料列數嚴格限制**：
   - 僅使用 Phase 3 外層 80/20 切分（固定 `seed=42`）劃分出之 **1,168 筆開發訓練列（Development Train Rows）**。
   - **292 筆封存保留集（Sealed Holdout Rows）** 於本階段維持密封狀態，串流讀檔時遇到對應行必須略過、不解析，嚴格禁止在 Phase 4 特徵選擇或超參數調校中窺探、計算或評估。
   - **1,459 筆 Kaggle 競賽測試集（Competition Test Rows）** 完全不開啟、不存取。
2. **外層交叉驗證（Outer CV）規範**：
   - 採用標準 `sklearn.model_selection.KFold(n_splits=5, shuffle=True, random_state=42)`。
   - 折大小嚴格為 234 / 234 / 234 / 233 / 233 筆。
   - **外層折分配摘要來源與驗證性**：
     - 外層成員與折分配 SHA-256 摘要值為：`7c9f1d00eb74d8a281ba41ed47d5ebbdbffa0513b4bb778b70d1571735ad6463`。
     - **來源佐證（Provenance Verification）**：該摘要已在基準版本 `ee03a519` 之 P4-A 實作（`tests/modeling/test_p4a_ols_cv.py` 與 `docs/crisp-dm/04-modeling-p4a-ols-baseline.md`）中獲得獨立合成回歸測試與程式碼驗證，確認具備完整來源憑據（Verified Provenance）。
     - 本階段僅引用該既定摘要進行外層成員檢驗，絕不重新計算、變更折分配或存取已封存之資料集。

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
│   │   ├── 各候選方法／候選超參數共用同一組內層 3 折分割清單：
│   │   │   ├── 每一折 Inner Train: 從原始列獨立執行 fit AmesDataPreparationPipeline
│   │   │   ├── 每一折 Inner Val: 僅以該 Inner Train fit 之前處理器執行 transform
│   │   │   └── 在 Inner Val 評估 RMSE，計算 3 折平均驗證 RMSE
│   │   │
│   │   └── 依內層平均 RMSE 與確定性平手規則選定最佳特徵子集名稱集合 S* 或最佳超參數 α*
│   │
│   └── [外層評估 Outer Evaluation]
│       ├── 在 Outer Train 全體（~934 rows）重新從原始列 fit 一個全新的前處理器
│       ├── 依名稱集合 S* 投影特徵（或依 α* 配置原生正則化估計器），重新 fit 模型
│       ├── 對 Outer Val（~234 rows）執行單次 Transform 與單次預測
│       └── 記錄該折 Outer OOF 預測結果與泛化指標
```

### 具體隔離合約
1. **內層前處理禁止跨折預先擬合**：
   - 嚴格禁止在進入內層 3 折前於 Outer Train（約 934 筆）或全部 1,168 筆上預先 `fit` 前處理器（例如數值中位數、類別眾數、編碼水準或標準化尺度）。
   - 內層每一折（Inner Fold）必須各自從原始資料列開始，在該 Inner Train（約 623 筆）上獨立執行 `pipeline.fit()`，Inner Val（約 311 筆）僅能進行 `transform()`。
2. **決策與外層重新擬合（Refit）**：
   - 內層 3 折驗證僅用於「評估與決策」最佳特徵數 $K$、最佳特徵名稱集合 $S^*$ 或正則化超參數 $\alpha^*$。
   - 選定後，使用該外層訓練集（Outer Train, ~934 筆）重新 `fit` 一個全新的外層前處理器與模型。
   - 最後使用該外層訓練完成的模型，對該折的外層驗證集（Outer Val）進行一次性（Once and only once）預測，產生 Outer OOF 預測。

---

## 3. 折內動態候選特徵空間與名稱對齊合約（Fold-Local Feature Identity & Schema Alignment）

1. **折內動態欄位空間**：
   - Phase 3 前處理管道（`AmesDataPreparationPipeline`）中的類別 One-Hot 編碼水準由各折訓練集動態學習。
   - 原始資料集具有 79 個候選預測變數（排除 `Id` 與目標變數 `SalePrice`），此 79 個原始欄位僅作為上游來源欄位定義（Source Column Mapping），並非最終模型空間。
   - 在 P4-A 的 5 折外層訓練中，觀察到的折內編碼後特徵數分別為 240, 241, 243, 248, 245（約 248 欄）。
   - **核心合約**：絕不強制固定編碼後欄位數為 248，亦不得在全體 1,168 筆上預先擬合全局特徵字典（Vocabulary）。所有候選特徵空間皆為該次訓練切分之**折內局部空間（Fold-Local Universe）**。
2. **跨折名稱對齊與缺欄／新欄確定性合約（Name-Based Alignment Contract）**：
   - **特徵唯一識別碼（Feature Identity）**：所有特徵以「名稱字串（Column Name）」作為唯一比對識別依據（例如 `Neighborhood_NAmes`、`OverallQual`）。
   - **內層評估對齊規則**：
     - 當評估某特徵名稱 $f$ 於內層 3 折之表現時，若特徵 $f$ 在某折 Inner Train 中因該訓練分區未出現該類別水準而**不存在（Absent）**，則該特徵在該折的 Inner Val 投影中定義為全 0 常數欄（因該類別指示為 0）。
     - 於濾窗法或係數排序時，若某特徵未出現在該折 Inner Train，該折賦予其評分為 $0.0$（排序最末）。
   - **外層重新擬合（Outer Refit）對齊規則**：
     - 內層選出之最佳特徵集合 $S^*$ 為一組字串集合（如 `{'OverallQual', 'GrLivArea', 'GarageCars'}`）。
     - 在 Outer Train 重新擬合前處理管道後，產出當前 Outer Train 的特徵字典 $V_{\text{outer}}$。
     - **存在性檢查（Presence Check）**：若 $S^*$ 中之某特徵 $f \in S^*$ 在 $V_{\text{outer}}$ 中存在，則正常選取該欄位；若 $f \notin V_{\text{outer}}$（極罕見情況：內層出現但外層訓練未產生該編碼水準），則外層訓練矩陣中該欄以全 0 向量補齊，以保持選定集合維度與模型契約一致。
     - 若 Outer Train 前處理產生了 $S^*$ 以外之新編碼水準（New Unseen Level），則該新欄位直接被忽略淘汰，不進入外層模型擬合。
3. **候選子集大小規範**：
   - 對於 Filter、Forward SFS 與 RFE，候選特徵數 $K$ 嚴格限定為集合：
     $$K \in \{2, 3, 5, 10, 20\}$$
   - 嚴格禁止評估未列入本合約之其他 $K$ 值。

---

## 4. 候選特徵選擇演算法與正則化合約（Algorithm Contracts & Pinned Versions）

### 4.1 環境與相依套件版本完全鎖定（Pinned Environment Contract）
依據專案根目錄 `requirements.in` 與 `requirements.lock`，本協定嚴格鎖定執行環境版本：
- **Python**: 3.12 (依 lock 建置環境規範)
- **scikit-learn**: `1.9.1`（官方文檔：[scikit-learn 1.9 API](https://scikit-learn.org/stable/)）
- **numpy**: `2.5.4`
- **pandas**: `3.1.0`
- **scipy**: `1.18.1`
- 嚴格禁止使用 `>=`、`+` 或「預設未指定（or default）」之模糊版本與參數配置。

### 4.2 內層交叉驗證分割器凍結（Inner Splitter Freeze）
- 所有演算法在內層 3 折評估時，共用同一份由以下參數產生的內層分割清單：
  ```python
  inner_cv = KFold(n_splits=3, shuffle=True, random_state=1042)
  ```
- 內層分割在每次 Outer Fold 內部固定產生，確保所有候選方法、不同 $K$ 值及超參數網格皆在完全相同的樣本分組上評估，杜絕方法間因分折不同產生的比較噪聲。

### 4.3 濾窗法（Filter Method: Pearson Correlation |r|）
- **單一指標凍結**：嚴格鎖定使用 Pearson 相關係數絕對值 $|r|$，不採用 F-檢定（兩者在單變量線性關聯下排序等價，凍結單一計算公式以確保可追溯性）：
  $$r(X_j, y) = \frac{\sum (X_{ij} - \bar{X}_j)(y_i - \bar{y})}{\sqrt{\sum (X_{ij} - \bar{X}_j)^2 \sum (y_i - \bar{y})^2}}$$
- **邊界與極端值處理**：
  - **常數欄位（$\sigma=0$）**：若特徵在訓練分區標準差為 0，其相關係數未定義，強制賦予分數 $0.0$。
  - **非有限值（NaN/Inf）**：前處理異常產生之非有限值，強制賦予分數 $-1.0$。
- **平手決策（Tie-Breaking）**：
  - 若 $|r|$ 分數相同（容差 $10^{-9}$ 內），嚴格依照特徵名稱字串之 ASCII 字典順序（Lexicographical ascending order）升冪排列決策。
- **選取規則**：選取分數最高之前 $K \in \{2, 3, 5, 10, 20\}$ 個特徵。

### 4.4 循序向前選擇法（Forward SFS: Sequential Feature Selector）
- **基底估計器**：嚴格鎖定使用帶 SVD 奇異值分解之未懲罰普通最小平方法（SVD OLS，比照 P4-A 實作 `numpy.linalg.lstsq(rcond=1e-15)`），不使用標準 `LinearRegression()` 避免共線性下數值發散。
- **搜尋方向**：嚴格向前（Forward），從空集合開始，每一步貪婪地將使內層 3 折平均驗證 RMSE 最小之單一特徵加入集合。
- **候選大小**：逐步選取至 $K \in \{2, 3, 5, 10, 20\}$。
- **平手決策**：若多個特徵加入後之內層平均 RMSE 差異在 $10^{-9}$ 內，優先依特徵名稱字典順序最小者入選。

### 4.5 遞迴特徵消除法（RFE: Recursive Feature Elimination）
- **基底估計器**：`sklearn.linear_model.Ridge(alpha=1.0, random_state=42, solver='auto')`。
  - *採用 Ridge 之理由*：未懲罰 OLS 在高維多重共線性下解不唯一；Ridge 具備強凸性（Strict convexity），可提供穩定之係數重要性排序。
- **特徵重要性評估**：回歸係數絕對值 $|\beta_j|$。
- **消除步長**：嚴格固定每次剔除 1 個特徵（`step=1`）。
- **平手決策**：若係數絕對值相同（容差 $10^{-9}$ 內），優先淘汰特徵名稱字典順序較大者（即保留字典序較小者）。

### 4.6 Lasso 與 ElasticNet 正則化超參數調校與無洩漏合約（Leakage-Safe Penalized CV Contract）
在 `scikit-learn 1.9.1` 中，`LassoCV` 與 `ElasticNetCV` 之 `n_alphas` 參數已移除，必須明確給定 `alphas` 陣列或使用固定網格。更重要的是，為徹底防止內部驗證折的前處理洩漏，**嚴格禁止直接對預先轉換後的特徵矩陣呼叫內建 CV 估計器**。本協定制定以下無洩漏流程合約：

1. **超參數網格完全凍結（Pinned Hyperparameter Grids）**：
   - **Lasso $\alpha$ 網格**：幾何等比數列，固定 50 個點：
     $$\alpha \in \text{logspace}(\log_{10}(1000), \log_{10}(0.1), 50)$$
   - **ElasticNet 網格**：
     - `l1_ratio` $\in [0.1, 0.5, 0.7, 0.9, 0.95, 0.99]$（共 6 個值）。
     - $\alpha \in \text{logspace}(\log_{10}(1000), \log_{10}(0.1), 30)$（共 30 個點）。
   - 估計器收斂參數：`max_iter=5000`，`tol=1e-4`。
2. **無洩漏估計器流程（Leakage-Safe Estimator Flow）**：
   - **步驟 1（內層評估）**：
     - 對於內層 3 折分割清單中的每一組 $(\text{Train}_{\text{inner}}, \text{Val}_{\text{inner}})$：
       1. 僅在原始資料 $\text{Train}_{\text{inner}}$ 上執行 `pipeline.fit()`。
       2. 以該 pipeline 對 $\text{Train}_{\text{inner}}$ 與 $\text{Val}_{\text{inner}}$ 分別執行 `transform()`。
       3. 對於候選網格中的每一個超參數組合（$\alpha$ 或 $(\alpha, \text{l1\_ratio})$），在轉換後的 $\text{Train}_{\text{inner}}$ 擬合 `Lasso` 或 `ElasticNet`，並在 $\text{Val}_{\text{inner}}$ 計算 RMSE。
   - **步驟 2（超參數決策）**：
     - 計算各候選超參數在內層 3 折驗證集上的平均 RMSE。
     - 選出平均 RMSE 最小之最佳超參數 $\alpha^*$（或 $(\alpha^*, \text{l1\_ratio}^*)$）。若平手（容差 $10^{-9}$），優先選取較大之 $\alpha$（更稀疏／強正則化），次選較大之 `l1_ratio`。
   - **步驟 3（外層重新擬合 Outer Refit）**：
     - 在 Outer Train 全體（~934 筆原始資料）重新 `fit` 一個全新的 `AmesDataPreparationPipeline` 並執行 `transform()`。
     - 以最佳超參數配置模型，在該 Outer Train 全特徵矩陣上擬合最終模型。
     - 對 Outer Val 執行單次 `transform()` 與單次預測，記錄 Outer OOF。
3. **稀疏閾值與特徵抽取**：
   - 係數絕對值 $|\beta_j| \le 10^{-7}$ 判定為零；其餘為選中之非零特徵。
   - 若發生 `ConvergenceWarning`，記錄 `converged=False` 旗標於輸出中繼資料。

---

## 5. 特徵縮放與懲罰項可比性合約（Feature Scaling & Penalty Comparability）

1. **分區獨立縮放（Partition-Local Scaling）**：
   - 數值與序數特徵之標準化（`StandardScaler`）必須且僅能在**當前訓練分區（當前 Inner Train 或 Outer Train）** 上 `fit`，驗證分區僅進行 `transform`。
   - One-Hot 虛擬變數（0/1）初始保持未縮放（Unscaled 0/1）。
2. **懲罰項尺度不可比性限制宣告（Known Theoretical Limitation）**：
   - **核心理論限制**：當數值特徵標準化為單位方差（$\sigma=1$），而 One-Hot 欄位維持 $0/1$ 時，各特徵的尺度與經驗方差並不相同。此時 $L_1$ 或 $L_2$ 正則化施加於係數上時，對稀疏類別特徵與連續特徵的懲罰力道實質上不對稱。
   - **協定決策**：本協定將此列為「已知理論限制與不變設定」，在報告與成果中明確記錄，不進行人為的隨意加權，以保持特徵工程管道之標準化與可追溯性。

---

## 6. 雙軌評估策略與奇異值分解 OLS 規範（Two Tracks & Rank-Deficient SVD OLS）

本實驗評估兩條獨立軌道：

| 軌道 | 名稱 | 估計器與預測機制 | 評估目標與本質 |
|---|---|---|---|
| **Track A** | **Selected Features + OLS Refit** | 以 Filter, SFS, RFE, Lasso 或 ElasticNet 選出非零特徵子集名稱 $S^*$ 後，**使用未懲罰 SVD OLS** 重新在 Outer Train 擬合並預測 Outer Val。 | 評估特徵子集的**資訊代表性**與維度縮減效果，排除正則化收縮帶來的有偏估計（Shrinkage Bias）。 |
| **Track B** | **End-to-End Native Regularized Model** | 直接使用調校最佳超參數之 **原生 Lasso / ElasticNet 模型權重** 進行預測。 | 評估正則化演算法本身在**方差收縮與多重共線性抑制**下的最終綜合預測能力。 |

### 奇異值分解 OLS 數值規格（Deterministic SVD OLS Specification）
- 於 Track A 重新擬合以及 SFS 候選評估時，若選出之特徵子集存在線性相依（Rank Deficient）：
  - 統一採用 `numpy.linalg.lstsq(X, y, rcond=1e-15)` 計算最小範數最小平方解。
  - 計算奇異值數值截斷：$\sigma_i > \text{rcond} \cdot \max(\sigma)$ 者計入有效秩（Effective Rank）。
  - 記錄數值診斷指標：矩陣有效秩（Rank）、零化度（Nullity = 欄數 - 秩）、有效條件數（Effective Condition Number $\sigma_{\max} / \sigma_{\min,\text{positive}}$）。
- **禁止混淆宣告**：P4-A 基準模型為全特徵最小範數解，其係數並非特徵重要性；禁止將 P4-A 係數大小作為特徵選擇排序依據。

---

## 7. 內層選取準則、平手決策與樂觀偏差（Selection Criteria & Optimism）

1. **內層目標函數**：
   - 內層 3 折交叉驗證之平均驗證均方根誤差（Mean Validation RMSE）：
     $$\text{Score} = \frac{1}{3} \sum_{m=1}^3 \text{RMSE}_m$$
2. **數值容差與確定性平手規則（Deterministic Tie-Breaking Hierarchy）**：
   - 浮點數比較容差設為 $\epsilon = 10^{-9}$。
   - 若候選設定之內層平均 RMSE 差異小於 $\epsilon$：
     1. **優先選擇特徵數較少者**（Occam's razor / Sparsity priority）。
     2. 若特徵數仍然相同，依固定演算法先後順序決策：Filter $\to$ Forward SFS $\to$ RFE $\to$ Lasso $\to$ ElasticNet。
     3. 若仍平手，依候選 $K$ 值較小者優先。
3. **無 1-SE 法則（No 1SE Rule）**：
   - 嚴格以內層驗證平均 RMSE 最小者勝出，不採用啟發式的 1 個標準誤差準則（1SE Rule），以避免主觀任意性。
4. **外層排行榜選擇樂觀偏差警告（Outer Selection Optimism Warning）**：
   - 在 5 折外層 CV 評估各方法後，在外層選出排名第一的方法與超參數組合，其外層 CV 平均表現仍具有微小之選擇樂觀偏差（Leaderboard Selection Optimism）。
   - 因此，Phase 5 封存保留集（292 筆 Holdout）必須持續維持密封狀態，作為最後評估最終模型泛化誤差的獨立隔離集。

---

## 8. 巢狀交叉驗證原理與明確合成對照（Nested-CV Rationale & Synthetic Demonstration）

### 8.1 為什麼必須採用巢狀交叉驗證？
若在同一層交叉驗證中同時進行特徵篩選與泛化評估（例如：在包含驗證折的資料集上先挑選相關特徵），驗證集資訊已洩漏至特徵選擇決策中，導致模型評估高度樂觀。

### 8.2 概念說明性合成程式碼對照（Conceptual Synthetic Demonstration）
以下程式碼僅供概念說明設計原理，明確標記為非實驗執行產物：

```python
# =========================================================================
# 【概念說明用合成程式碼：資訊洩漏 vs 巢狀隔離 (Conceptual Synthetic Demo)】
# 本程式碼僅用於定義協定之防洩漏設計原理，嚴禁在 A1 階段執行或引用為實驗數據。
# =========================================================================
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold

# 假設環境：100 筆樣本，1,000 個獨立高斯雜訊特徵，y 亦為純隨機雜訊（真實 R^2 = 0）
np.random.seed(42)
X_synthetic = np.random.randn(100, 1000)
y_synthetic = np.random.randn(100)

# -------------------------------------------------------------------------
# [錯誤模式 Flawed Practice]: 全局篩選特徵後再切分 CV (資訊洩漏)
# -------------------------------------------------------------------------
# 在全體 100 筆上計算相關性並挑出前 5 個特徵（洩漏了全體 y 的資訊）
corrs = np.abs([np.corrcoef(X_synthetic[:, j], y_synthetic)[0, 1] for j in range(1000)])
flawed_selected_idx = np.argsort(corrs)[-5:]

kf = KFold(n_splits=5, shuffle=True, random_state=42)
flawed_val_mse = []
for tr_idx, val_idx in kf.split(X_synthetic):
    reg = LinearRegression().fit(X_synthetic[tr_idx][:, flawed_selected_idx], y_synthetic[tr_idx])
    pred = reg.predict(X_synthetic[val_idx][:, flawed_selected_idx])
    flawed_val_mse.append(np.mean((pred - y_synthetic[val_idx]) ** 2))
# 理論推論：驗證誤差顯著偏低，產生「純雜訊特徵能良好預測 y」的虛假假象。

# -------------------------------------------------------------------------
# [正確模式 Nested CV]: 嚴格於各折訓練集內部獨立篩選特徵
# -------------------------------------------------------------------------
nested_val_mse = []
for tr_idx, val_idx in kf.split(X_synthetic):
    # 僅使用 tr_idx 計算相關性並挑選特徵
    tr_corrs = np.abs([np.corrcoef(X_synthetic[tr_idx, j], y_synthetic[tr_idx])[0, 1] for j in range(1000)])
    clean_selected_idx = np.argsort(tr_corrs)[-5:]

    reg = LinearRegression().fit(X_synthetic[tr_idx][:, clean_selected_idx], y_synthetic[tr_idx])
    pred = reg.predict(X_synthetic[val_idx][:, clean_selected_idx])
    nested_val_mse.append(np.mean((pred - y_synthetic[val_idx]) ** 2))
# 理論推論：驗證誤差忠實反映無預測能力（MSE 回歸常態雜訊期望變異數）。
```

---

## 9. 擬合預算、分析性上限與防禦中斷機制（Fit Accounting & Analytical Upper Bounds）

### 9.1 擬合單位定義（Counted Unit Definition）
- **1 個「擬合單位（Fit Unit）」**：定義為一個回歸估計器在指定特徵子集與樣本子集上完成一次完整的參數擬合計算（例如一次 `LinearRegression.fit()`、`Ridge.fit()` 或 `Lasso.fit()`）。

### 9.2 各方法解析擬合上限公式（Per-Method Analytical Upper Bounds）
設外層折數 $M=5$，內層折數 $m=3$，折內候選特徵數上限 $D_{\max} \approx 250$，$K \in \{2, 3, 5, 10, 20\}$：

1. **Filter (Pearson |r|)**：
   - 特徵評分僅為統計量計算（不計為估計器 fit）。
   - 內層評估：5 個候選 $K$ 值 $\times$ 3 個內層折 $= 15$ 次擬合。
   - 外層重新擬合：5 外層折 $\times 1$ 次 (Track A) $= 5$ 次擬合。
   - **Filter 總擬合數上限**：$M \times (m \cdot |K| + 1) = 5 \times (3 \times 5 + 1) = 80$ 次。
2. **Forward SFS**：
   - 每步評估未選入特徵於內層 3 折之表現。至 $K=20$ 時：
     $$\text{Fits per fold} = 3 \times \sum_{k=1}^{20} (D_{\max} - k + 1) \approx 3 \times 20 \times 240 \approx 14,400 \text{ 次}$$
   - 外層重新擬合：5 次。
   - **SFS 總擬合數上限**：$5 \times 14,400 + 5 \approx 72,005$ 次。
3. **RFE (Ridge, step=1)**：
   - 從 $D_{\max}$ 逐步剃除至 $K_{\min}=2$，剃除次數約 $248$ 步。
   - 內層評估：3 折 $\times 248 \approx 744$ 次擬合。
   - 外層重新擬合：5 次。
   - **RFE 總擬合數上限**：$5 \times 744 + 5 \approx 3,725$ 次。
4. **Lasso (50 alphas)**：
   - 內層評估：3 折 $\times 50 \text{ alphas} = 150$ 次擬合。
   - 外層重新擬合：Track A (OLS Refit) 1 次 + Track B (Native Lasso) 1 次 $= 2$ 次。
   - **Lasso 總擬合數上限**：$5 \times (150 + 2) = 760$ 次。
5. **ElasticNet (6 l1_ratios $\times$ 30 alphas = 180 組合)**：
   - 內層評估：3 折 $\times 180 = 540$ 次擬合。
   - 外層重新擬合：Track A 1 次 + Track B 1 次 $= 2$ 次。
   - **ElasticNet 總擬合數上限**：$5 \times (540 + 2) = 2,710$ 次。

### 9.3 累計硬上限與防禦中斷機制（Cumulative Hard Cap & Abort Triggers）
- **A1 協定預先設定硬擬合上限（Provisional Hard Fit Cap）**：
  $$\text{Cumulative Fit Cap} = 100,000 \text{ 次擬合}$$
  （總理論需求約 $80 + 72,005 + 3,725 + 760 + 2,710 \approx 79,280$ 次，設定 100,000 次作為確定性防禦邊界）。
- **異常中斷觸發（Abort Trigger）**：
  - 若累計擬合次數達到 100,000 次而尚未完成，Runner 必須立即中止（Fail-Closed），拋出 `BudgetExceededError`。
  - 若在單一內層折內連續發生 3 次數值發散或未收斂警告，立即中斷該方法並標記失敗。
- **檢查點機制（Checkpoint & Resume）**：
  - 以「外層折（Outer Fold）+ 方法」為原子單位寫入暫存檔案至私有路徑。中斷重啟時驗證 SHA-256 即可接續，避免重複計算。
- **資源測量宣告**：
  - **嚴格禁止在本協定捏造具體執行秒數或記憶體耗用數據**。實際牆上時間（Wall-clock time）與記憶體峰值由後續 **A4 基準測量階段** 進行實證測量，本階段僅規範分析性擬合次數與硬防禦上限。

---

## 10. 輸出綱要與產物安全合約（Output Schema & Artifact Boundaries）

所有產物使用純文字 JSON 與 CSV，嚴格禁止使用 SQLite。

### 10.1 私有與公開路徑隔離合約
- **私有產物路徑**：`local/research/phase4-p4b/<run-id>/`。
  - 寫入前執行 `git check-ignore` 驗證，未被忽略則拒絕寫入（Fail-Closed）。
  - 私有產物包含逐列 OOF 預測（含 `Id`, `Actual`, `Predicted`）與折內完整特徵字典。
- **公開摘要產物**：`p4b_public_summary.json`。
  - **公開輸出中嚴格禁止包含任何逐列預測、真實房價或受保護路徑**。

### 10.2 結構綱要範例（純綱要展示，所有數值為 null / placeholder）

```json
{
  "_schema_notice": "THIS IS A SCHEMA SPECIFICATION ONLY. CONTAINS NO EXPERIMENTAL RESULTS.",
  "metadata": {
    "protocol_version": "v1.0",
    "issue_reference": "Issue #21 / Issue #22",
    "base_commit": "ee03a51978a0f615f39b656bee318946dcddd890",
    "run_id": null,
    "environment": {
      "python_version": "3.12",
      "sklearn_version": "1.9.1",
      "numpy_version": "2.5.4"
    },
    "data_boundary": {
      "development_rows": 1168,
      "outer_kfold": {"n_splits": 5, "shuffle": true, "random_state": 42},
      "outer_fold_digest": "7c9f1d00eb74d8a281ba41ed47d5ebbdbffa0513b4bb778b70d1571735ad6463",
      "digest_provenance": "verified_in_p4a"
    }
  },
  "method_contract": {
    "filter_pearson": {"k_candidates": [2, 3, 5, 10, 20]},
    "forward_sfs": {"estimator": "SVD_OLS", "k_candidates": [2, 3, 5, 10, 20]},
    "rfe_ridge": {"estimator": "Ridge(alpha=1.0)", "k_candidates": [2, 3, 5, 10, 20]},
    "lasso": {"alphas_count": 50, "inner_cv": 3},
    "elastic_net": {"l1_ratios": [0.1, 0.5, 0.7, 0.9, 0.95, 0.99], "alphas_count": 30, "inner_cv": 3}
  },
  "aggregate_results": [
    {
      "method": null,
      "track": null,
      "best_k_or_alpha": null,
      "outer_mean_rmse": null,
      "outer_std_rmse": null,
      "outer_mean_r2": null,
      "feature_selection_stability": {
        "most_frequent_features": []
      },
      "fit_accounting": {
        "actual_fits": null,
        "fit_cap_status": null
      },
      "convergence_status": null
    }
  ]
}
```

---

## 11. 停機條件與範圍邊界（Stop Conditions & Non-Goals）

- **非目標（Non-Goals）**：
  1. 不得執行任何真實 Ames 資料集讀取或特徵工程計算。
  2. 不得執行任何模型訓練、超參數搜尋或真實指標計算。
  3. 不得實作 A2（測試套件）、A3（Runner 程式碼）、A4（基準測量）或 B 階段之內容。
  4. 不得修改 `main` 分支或操作其他工作樹。
  5. 不得擅自進行工作樹清理或刪除分支。
- **停機條件（Stop Condition）**：
  - 本協定文檔（`docs/crisp-dm/04-modeling-p4b-experiment-protocol.md`）完成修訂並提交於 `feature/p4b-a1-protocol-issue-22` 分支後，執行 `git diff --check` 確認格式乾淨，寫入本機私有結果 handoff，隨即停機報告。
