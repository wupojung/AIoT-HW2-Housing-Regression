# CRISP-DM Phase 4 — P4-B-A：特徵選擇與正則化實驗協定（Issue #21 / #22）

- **協定版本**：v1.0 (Draft Candidate)
- **所屬任務**：Phase 4-B-A 特徵選擇與正則化比較實驗
- **關聯 Issue**：Issue #21（P4-B 特徵選擇規劃）、Issue #22（P4-B-A 協定凍結）
- **基準版本 (BASE SHA)**：`ee03a51978a0f615f39b656bee318946dcddd890`（已整併 P4-A 基準模型）
- **協定狀態**：Draft Candidate（A1 階段協定凍結草案；本階段僅制定規範，不執行真實資料實驗、模型擬合或 A2+ 實作）

---

## 1. 範圍與資料隔離邊界（Data Boundary & Partitioning）

1. **開發資料列數嚴格限制**：
   - 僅使用 Phase 3 外層 80/20 切分（固定 `seed=42`）劃分出之 **1,168 筆開發訓練列（Development Train Rows）**。
   - **292 筆封存保留集（Sealed Holdout Rows）** 於本階段維持密封狀態，串流讀檔時遇到對應行必須略過、不解析，嚴格禁止在 Phase 4 特徵選擇或超參數調校中窺探或評估。
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

為避免在特徵選擇與超參數調校過程中產生嚴重的選擇樂觀偏差（Selection Bias）與資訊洩漏（Information Leakage），本實驗嚴格採用**巢狀交叉驗證（Nested Cross-Validation）**架構：

```
1,168 Development Rows
│
├── Outer 5-Fold CV (Outer Train: ~934 rows, Outer Val: ~234 rows)
│   │
│   ├── [內層 Inner Loop: 僅在該折的 Outer Train 上進行]
│   │   ├── Inner 3-Fold CV (Inner Train: ~623 rows, Inner Val: ~311 rows)
│   │   ├── 各折 Inner Train 分別執行: 原始列 -> fit Preprocessing -> transform
│   │   ├── 各折 Inner Val 分別執行: transform (使用該 Inner Train fit 之前處理器)
│   │   ├── 特徵評估／篩選／模型調校並於 Inner Val 評估分數 (RMSE)
│   │   └── 依 3-fold 內層平均表現選出最佳特徵子集及超參數
│   │
│   └── [外層評估 Outer Evaluation]
│       ├── 以選定之特徵子集／超參數，在該 Outer Train 全體（~934 rows）重新擬合前處理與模型
│       ├── 對 Outer Val（~234 rows）執行單次 Transform 與單次預測
│       └── 記錄該折 Outer OOF 預測結果與泛化指標
```

### 具體隔離合約
1. **內層前處理禁止跨折預先擬合**：
   - 禁止在進入內層 3 折前於 Outer Train（934 筆）或全部 1,168 筆上預先 `fit` 前處理器（例如中位數、眾數或 One-Hot 編碼字典）。
   - 內層每一折（Inner Fold）必須各自從原始資料列開始，在該 Inner Train（約 623 筆）上獨立執行 `pipeline.fit()`，Inner Val（約 311 筆）僅能進行 `transform()`。
2. **決策與外層重新擬合（Refit）**：
   - 內層 3 折驗證僅用於「評估與決策」最佳特徵數 $K$ 或正則化超參數。
   - 選定超參數或特徵子集後，使用該外層訓練集（Outer Train, ~934 筆）重新 `fit` 一個全新的外層前處理器與模型。
   - 最後使用該外層訓練完成的模型，對該折的外層驗證集（Outer Val）進行一次性（Once and only once）預測，產生 Outer OOF 預測。

---

## 3. 折內候選特徵空間（Fold-Local Encoded Feature Universe）

1. **折內動態欄位空間**：
   - Phase 3 前處理管道（`AmesDataPreparationPipeline`）中的類別 One-Hot 編碼水準由各折訓練集動態學習。
   - 原始資料集具有 79 個候選預測變數（排除 `Id` 與目標變數 `SalePrice`），此 79 個原始欄位僅作為上游來源欄位定義（Source Column Mapping），並非最終模型空間。
   - 在 P4-A 的 5 折外層訓練中，觀察到的折內編碼後特徵數分別為 240, 241, 243, 248, 245（約 248 欄）。
   - **重要合約**：絕不強制固定編碼後欄位數為 248，亦不得在全體 1,168 筆上預先擬合全局特徵字典（Vocabulary）。所有候選特徵空間皆為該次訓練切分之**折內局部空間（Fold-Local Universe）**。
2. **候選子集大小規範**：
   - 對於需要明確指定特徵子集大小的篩選法（Filter）、循序向前選擇法（Forward SFS）與遞迴特徵消除法（RFE），候選特徵數 $K$ 嚴格限定為集合：
     $$K \in \{2, 3, 5, 10, 20\}$$
   - 嚴格禁止評估未列入本合約之其他 $K$ 值，以確保計算預算與可比性。

---

## 4. 候選特徵選擇演算法與正則化合約（Algorithm Contracts）

本實驗評估五種特徵選擇／正則化方法，各方法之數值行為、極端值處理與實作合約如下：

### 4.1 濾窗法（Filter Method: Pearson Correlation / Univariate F-regression）
- **演算法合約**：
  - 於訓練分區（Train Partition）計算各數值／編碼特徵與目標變數 $y$（`SalePrice`）之 Pearson 相關係數絕對值 $|r|$ 或一元線性迴歸 $F$-檢定統計量（二者在單變量線性關聯下排序一致）。
- **異常與邊界處理**：
  - **缺失值（Missing values）**：Phase 3 Pipeline 於編碼前已完成中位數／眾數填補，不應出現缺失值；若前處理後仍檢測到 NaN/Inf，必須立即報錯（Fail-Closed）。
  - **常數欄位（Constant features / Zero-variance）**：標準差為 0 之特徵，其相關係數未定義（0/0）。合約規定將常數特徵之分數設為 $0.0$，排序置於最末。
  - **非有限值（Non-finite）**：任何產生 NaN 或 Inf 之計算分數，強制設為 $-1.0$ 並排至最末。
- **特徵提取**：由高至低選取分數最高之前 $K \in \{2, 3, 5, 10, 20\}$ 個特徵。
- **平手決策（Tie-Breaking）**：若評分完全相同，依特徵欄位名稱之字典順序（Lexicographical order）升冪排列決策。

### 4.2 循序向前選擇法（Forward SFS: Sequential Feature Selector）
- **基底估計器**：未懲罰最小平方法 `LinearRegression()` 或 SVD OLS。
- **選擇方向與貪婪策略**：
  - 嚴格向前（Forward, `direction='forward'`）：從空集合開始，每一步貪婪地加入使內層 3 折交叉驗證平均 RMSE 最小化之特徵。
- **候選大小**：逐步選取直到特徵數達到預設 $K \in \{2, 3, 5, 10, 20\}$。
- **平手決策**：若多個候選特徵產生相同之平均 RMSE（在浮點容差 $10^{-9}$ 內），優先依特徵名稱字典順序最小者入選。

### 4.3 遞迴特徵消除法（RFE: Recursive Feature Elimination）
- **基底估計器**：`sklearn.linear_model.Ridge(alpha=1.0, random_state=42)`。
  - *採用 Ridge 之理由*：未懲罰 OLS 在高維多重共線性下可能產生極大或數值不穩定之係數；Ridge($\alpha=1.0$) 具備強凸性（Strict convexity），可提供數值穩定且具備可比性的係數權重。
- **特徵重要性評估依據**：回歸係數之絕對值 $|\beta_j|$。
- **淘汰步長（Elimination Step）**：每次剔除步長嚴格固定為 `step=1`（逐一剃除），以確保消除路徑之精確度。
- **平手決策**：若 $|\beta_j|$ 數值相同（容差 $10^{-9}$ 內），優先保留特徵名稱字典順序較小之欄位。

### 4.4 LassoCV（$L_1$ 正則化）
- **API 與套件版本**：`sklearn.linear_model.LassoCV`（依賴專案既有 `scikit-learn>=1.3`）。
- **參數設定**：
  - `cv=3`（內層 3 折）。
  - `n_alphas=100` 或預設幾何等比網格，`eps=1e-3`。
  - `random_state=42`。
  - `max_iter=5000`，`tol=1e-4`。
- **稀疏閾值與特徵抽取**：
  - 係數絕對值 $|\beta_j| \le 10^{-7}$ 判定為零係數；其餘非零特徵視為被選中之特徵。
- **收斂與極端處理**：
  - 若未於最大迭代次數內收斂（`ConvergenceWarning`），記錄收斂失敗標記（`converged=False`），不得無預警吞沒警訊。

### 4.5 ElasticNetCV（$L_1 + L_2$ 彈性網絡）
- **API 與套件版本**：`sklearn.linear_model.ElasticNetCV`。
- **參數設定**：
  - `l1_ratio=[0.1, 0.5, 0.7, 0.9, 0.95, 0.99]`。
  - `n_alphas=50`，`cv=3`。
  - `random_state=42`。
  - `max_iter=5000`，`tol=1e-4`。
- **非零特徵判斷與收斂**：
  - 閾值比照 $|\beta_j| > 10^{-7}$；若收斂超時同樣記錄收斂警告狀態。

---

## 5. 特徵縮放與懲罰項可比性合約（Feature Scaling & Penalty Comparability）

1. **分區獨立縮放（Partition-Local Scaling）**：
   - 數值與序數特徵之標準化（`StandardScaler`）必須且僅能在**當前訓練分區（當前 Inner Train 或 Outer Train）** 上 `fit`，驗證分區僅進行 `transform`。
   - One-Hot 虛擬變數（0/1）初始保持未縮放（Unscaled 0/1）。
2. **懲罰項尺度不可比性限制宣告（Known Limitation）**：
   - **核心理論限制**：當數值特徵具備單位方差（$\sigma=1$），而 One-Hot 欄位維持 $0/1$ 時，各特徵的尺度與經驗方差並不相同。此時 $L_1$ 或 $L_2$ 正則化施加於係數上時，對稀疏類別特徵與連續特徵的懲罰力道實質上不對稱。
   - **協定決策**：本協定將此列為「已知理論限制與不變設定」，在報告與成果中明確記錄，不進行人為的隨意加權，以保持特徵工程管道之標準化與可追溯性。

---

## 6. 雙軌評估策略（Two Distinct Evaluation Tracks）

為公平比較「純特徵篩選能力」與「正則化收縮估計能力」，本實驗劃分兩條獨立評估軌道：

| 軌道 | 名稱 | 估計器與預測機制 | 評估目標與本質 |
|---|---|---|---|
| **Track A** | **Selected Features + OLS Refit** | 以 Filter, SFS, RFE, LassoCV 或 ElasticNetCV 選出非零特徵子集後，**使用未懲罰普通最小平方法（Unpenalized SVD OLS）** 重新在 Outer Train 擬合並預測 Outer Val。 | 評估特徵子集的**資訊代表性**與維度縮減效果，排除正則化收縮帶來的有偏估計（Shrinkage Bias）。 |
| **Track B** | **End-to-End Native Regularized Model** | 直接使用調校最佳超參數之 **原生 Lasso / ElasticNet 模型權重** 進行預測。 | 評估正則化演算法本身在**方差收縮與多重共線性抑制**下的最終綜合預測能力。 |

> **禁止混淆宣告**：P4-A 基準模型為全特徵最小範數 SVD OLS 解，其係數並非特徵重要性；本協定中 Track A 與 Track B 嚴格區分，禁止將 P4-A 之係數大小拿來作為本實驗特徵排序之對照。

---

## 7. 內層選取準則、平手決策與樂觀偏差（Selection Criteria & Optimism）

1. **內層目標函數**：
   - 內層 3 折交叉驗證之平均驗證均方根誤差（Mean Validation RMSE）：
     $$\text{Score} = \frac{1}{3} \sum_{m=1}^3 \text{RMSE}_m$$
2. **數值容差與平手規則（Deterministic Tie-Breaking）**：
   - 浮點數比較容差設為 $\epsilon = 10^{-9}$。
   - 若候選設定之內層平均 RMSE 差異小於 $\epsilon$：
     1. **優先選擇特徵數較少者**（Occam's razor / Sparsity priority）。
     2. 若特徵數仍然相同，依固定演算法先後順序決策：Filter $\to$ Forward SFS $\to$ RFE $\to$ LassoCV $\to$ ElasticNetCV。
     3. 若仍平手，依候選 $K$ 值較小者優先。
3. **無 1-SE 法則（No 1SE Rule）**：
   - 嚴格以內層驗證平均 RMSE 最小者勝出，不採用啟發式的 1 個標準誤差準則（1SE Rule），以避免主觀任意性。
4. **外層排行榜選擇樂觀偏差警告（Outer Selection Optimism Warning）**：
   - 在 5 折外層 CV 評估各方法後，雖然可列出外層平均 RMSE 排行榜，但**在外層選擇排名第一的模型本身仍具有輕微的選擇樂觀偏差（Leaderboard Selection Optimism）**。
   - 因此，Phase 5 封存保留集（292 筆 Holdout）必須持續封存，作為最後最終確認泛化誤差之獨立屏障，絕不可在本協定外層選擇時動用。

---

## 8. 巢狀交叉驗證原理與反面教材（Nested-CV Rationale & Anti-Pattern）

### 8.1 為什麼必須採用巢狀交叉驗證？
若在同一層交叉驗證中同時進行「尋找最佳特徵／超參數」與「評估泛化誤差」，模型選擇的隨機波動會偏好在該驗證集上剛好表現極佳的特徵，導致嚴重的過度擬合與泛化估計過度樂觀。

### 8.2 明確合成反面教材（Synthetic Anti-Pattern Example）
考慮以下純雜訊特徵篩選的典型反例（明確標記為合成概念說明）：

```python
# -------------------------------------------------------------
# 【明確反面教材：資訊洩漏與假性高分 (Synthetic Anti-Pattern)】
# 假設 N=100 筆樣本，D=10,000 個與目標 y 完全無關的純常態隨機雜訊特徵
# -------------------------------------------------------------
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold

np.random.seed(42)
X_noise = np.random.randn(100, 10000)
y_noise = np.random.randn(100)  # y 完全是獨立雜訊，真實 R^2 應為 0

# 錯誤作法 (Information Leakage / Tuning Reuse):
# 1. 在全體 100 筆資料上計算與 y 的相關性，挑選出相關性最高的 5 個特徵
corrs = np.abs([np.corrcoef(X_noise[:, j], y_noise)[0, 1] for j in range(10000)])
top5_leaked = np.argsort(corrs)[-5:]

# 2. 在這 5 個「洩漏特徵」上跑 5-Fold CV
scores = []
kf = KFold(n_splits=5, shuffle=True, random_state=42)
for train_idx, val_idx in kf.split(X_noise):
    reg = LinearRegression().fit(X_noise[train_idx][:, top5_leaked], y_noise[train_idx])
    val_pred = reg.predict(X_noise[val_idx][:, top5_leaked])
    scores.append(np.mean((val_pred - y_noise[val_idx]) ** 2))

# 結果：驗證集會回報極高之 R^2（如 0.5 以上）與極低 MSE，造成「特徵高度有效」的假象！
# 正確的巢狀 CV 作法：在每一折 train_idx 內部才能進行 top5 特徵挑選，
# 驗證集 val_idx 上計算之 R^2 即會真實反映回歸到接近 0（純雜訊）。
```

### 8.3 巢狀交叉驗證的限制
- 巢狀 CV 計算量為單層 CV 的倍數（如 $5 \times 3 = 15$ 次內層擬合）。
- 巢狀 CV 提供的是「建模程序（Modeling Procedure）的泛化誤差估計」，而非單一固定的最終特徵子集（各外層折選出的特徵子集可能有些微差異）。

---

## 9. 擬合預算、資源控制與 Runner 設計規範（Runner Architecture & Controls）

1. **擬合次數精確會計（Fit Count Accounting）**：
   - 設外層折數 $M=5$，內層折數 $m=3$。
   - **Filter / RFE**：外層 5 折 $\times$ 內層 3 折 $= 15$ 次評估，外層重新擬合 5 次。
   - **Forward SFS**：步進貪婪選擇，$K=20$ 時約需評估數百次局部線性迴歸，必須記錄精確累計 fit 次數。
   - **LassoCV / ElasticNetCV**：由 sklearn 內部網格完成內層 3 折搜尋，再於外層執行 1 次最佳參數擬合。
2. **資源控制與防禦中斷機制**：
   - 所有運行以單次 Process 為原則，設定單折上限逾時（Timeout）與記憶體警戒線。
   - **合約約定**：具體單次完整執行耗時預算（Wall-clock time budget）與記憶體耗用上限，暫定為 A4 階段測量項目，不得作出未經驗證之時間保證承諾。
   - 實作中斷／恢復（Checkpoint & Resume）設計：以各外層 Fold 為單位儲存暫存 checkpoint，若遇中斷可自最後未完成折接續，避免無謂重跑。
3. **路徑與輸出隔離合約**：
   - **禁止使用 SQLite**：所有產物嚴格使用純文字 JSON、CSV 及選擇性 NPZ。
   - **私有產物固定路徑**：
     - 一律輸出至受 Git 忽略之路徑：`local/research/phase4-p4b/<run-id>/`。
     - 寫入前必須先透過 `git check-ignore` 驗證目標路徑是否被安全忽略；若未被忽略則立即中止（Fail-Closed）。
     - 包含私有檔案：`p4b_local_manifest.json`（含 SHA-256 校驗碼）、`p4b_local_details.json`、`p4b_oof_predictions.csv`（含逐列真實值與預測值）。
   - **公開產物邊界**：
     - 公開摘要：`p4b_public_summary.json`。
     - **公開輸出中嚴禁包含任何逐列預測（OOF rows）、真實房價、列索引或敏感路徑**；僅允許彙總性指標（平均 RMSE、標準差、被選中特徵頻率統計表）。

---

## 10. 輸出綱要與佐證索引規範（Output Schema & Evidence Index）

公開與私有產物之欄位結構與中繼資料合約定義如下：

```json
{
  "metadata": {
    "protocol_version": "v1.0",
    "issue_reference": "Issue #21 / Issue #22",
    "base_commit": "ee03a51978a0f615f39b656bee318946dcddd890",
    "run_id": "p4b-run-<timestamp>",
    "environment": {
      "python_version": "3.11+",
      "sklearn_version": "1.3+",
      "numpy_version": "1.24+"
    },
    "data_boundary": {
      "development_rows": 1168,
      "outer_kfold": {"n_splits": 5, "shuffle": true, "random_state": 42},
      "outer_fold_digest": "7c9f1d00eb74d8a281ba41ed47d5ebbdbffa0513b4bb778b70d1571735ad6463",
      "digest_provenance": "verified_in_p4a"
    }
  },
  "methods_evaluated": {
    "filter_pearson": {"k_candidates": [2, 3, 5, 10, 20]},
    "forward_sfs": {"estimator": "OLS", "k_candidates": [2, 3, 5, 10, 20]},
    "rfe_ridge": {"estimator": "Ridge(alpha=1.0)", "k_candidates": [2, 3, 5, 10, 20]},
    "lasso_cv": {"cv": 3, "selection_threshold": 1e-7},
    "elastic_net_cv": {"cv": 3, "l1_ratios": [0.1, 0.5, 0.7, 0.9, 0.95, 0.99]}
  },
  "aggregate_results": [
    {
      "method": "rfe_ridge",
      "track": "Track_A_OLS_Refit",
      "best_k": 10,
      "outer_mean_rmse": 0.0,
      "outer_std_rmse": 0.0,
      "outer_mean_r2": 0.0,
      "feature_selection_stability": {
        "most_frequent_features": [
          {"feature": "OverallQual", "selection_frequency": 5},
          {"feature": "GrLivArea", "selection_frequency": 5}
        ]
      },
      "fit_accounting": {
        "total_fits": 20,
        "mean_fold_duration_sec": 0.0
      },
      "convergence_status": "all_converged"
    }
  ]
}
```

---

## 11. 停機條件與範圍邊界（Stop Conditions & Non-Goals）

- **本階段非目標（Non-Goals）**：
  1. 不得執行任何真實 Ames 資料集讀取。
  2. 不得執行任何模型訓練、特徵篩選運算或真實評估。
  3. 不得實作 A2（測試套件）、A3（Runner 程式碼）、A4（基準測量）或 B 階段之內容。
  4. 不得修改 `main` 分支或其他工作樹。
  5. 不得擅自進行工作樹清理或刪除分支。
- **停機條件（Stop Condition）**：
  - 本協定文檔（`docs/crisp-dm/04-modeling-p4b-experiment-protocol.md`）撰寫完成並提交於指定工作樹（`C:\project\nchu\AIoT-HW2-Housing-Regression-p4b-a1`）之 `feature/p4b-a1-protocol-issue-22` 分支後，立即停止所有操作，發送單次完成報告等待進一步審查。
