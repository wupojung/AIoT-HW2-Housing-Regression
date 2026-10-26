# RegScope P4-B｜五種特徵選取與三折交叉驗證研究協定 v2.0（R3 Nex Delta 修訂）

> 狀態：**文件候選規格，待獨立 QA 與 Owner Merge 授權後生效**。本文件不代表程式已完成、資源限制已實測、或可讀取 Holdout。依據 [Recovery #28 v4](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/28)、Epic #4、#21–#23。舊 5×3 Nested CV／Forward SFS 規格由 Git 歷史保存，**此版於合併後才正式取代其未來執行契約**。

## 1. 研究問題、數據與不可變界線

- 比較 Pearson、Mutual Information、Lasso、ElasticNet、Ridge RFE 對房價迴歸的選取效果、穩定性、預測誤差與計算成本。**不增加 F-test、Forward SFS 或 Group Lasso**。
- Ames/Kaggle 有標記資料 1,460 列，維持 Phase 3 seed=42 的 80/20 原始分割：**1,168 Development / 292 sealed Holdout**。另外 1,459 列未標記 Competition Test；P4-B 一律不得載入/解析 Holdout 的特徵與標籤、不得訪問 Competition Test，也不得對其選模。
- 模型輸入排除 `Id`、`SalePrice`；`SalePrice` 只作為目標。原始預測候選約 79 欄，老師「≥14」的原始 rubric 尚未確認，暫按 Owner 解讀記為候選原始欄位而不是選後 K；正式交件前須核對來源，不阻擋安全的 Development 規格工作。
- 不改 Phase 3 的 missingness、structural absence、ordinal/nominal 意義和數據分割程式。P4-A 歷史 5-fold OLS RMSE 36,855.78、R² .763579 **保留為歷史，不能與下述三折直接排序**。

## 2. 三折 CV 與避免資料洩漏

1. 以 **同一份已核實的 1,168 列 Development 排序**產生 `KFold(n_splits=3,shuffle=True,random_state=42)`；固定儲存 fold membership digest、實際各折行數、資料指紋、Git SHA 與 Python/sklearn/numpy 版本。行數預期為 390/389/389；實作必須從確定的開發資料順序重算並驗證，不重用舊 5-fold digest。
2. 每個 `method × config × fold` 均從**原始 training rows**建新的 Phase 3 前處理器，僅使用該 fold train 做 imputation、encoding、scaling、selection、estimator fit；validation 僅 `transform/predict/score`。One-hot vocab 可隨 fold 改變。**嚴禁事先於整份 Development fit encoder/scaler/selectKBest 再 CV。**
3. 每個預先登記的候選配置在相同三折評分。**Pearson／MI／Ridge RFE 僅有 selected→OLS 主軌；Lasso／ElasticNet 的 primary track 明訂為 selected→OLS**，以其三折 `mean(RMSE)` 選定各方法之 alpha／l1_ratio，然後才比較五種方法的共同 OLS 主軌。**Native Lasso／ElasticNet 僅是 diagnostic secondary track：套用 primary 選中的同一組超參數，在同一三折分開報 native 預測分數，不能用 native 分數另選參數或取代 primary winner。** 以主軌 `mean(RMSE)` 越小越好為主要選擇目標；差異 ≤ `1e-8` 時依「選中 encoded 數較少→候選順序→方法順序」決勝。附 mean/sample SD RMSE、MAE、R²；每折 RMSE 先分別計算，不能先合併全部 OOF 再誤稱 mean-fold RMSE。
4. **不使用在整份 Development 預先 fit preprocessing 後的 `LassoCV` / `ElasticNetCV` 內建 CV。** 使用對每折 training rows 重建完整 pipeline 的明確有限 grid 候選。沒有第二層 inner-CV；最佳三折分數受選擇樂觀偏差影響，報告必須註明 `Development CV selection score; not independent generalization`。
5. 各方法設定凍結於 Development 評分前；不得看結果之後改 alpha/grid/K/tie 再假裝同一輪預先註冊。真正需要改規格則開**新 Run ID 與明示 amendment**。最後依已鎖定的 method/config 在**全 1,168 Development** 重新 fit，保留版本與選中欄位。僅在 Phase 5 Owner 另授權後開 **292 Holdout 一次**，絕不把 Holdout 作調參回饋。
6. **同折 OLS baseline**：在完全相同 3-fold、training-only Phase 3 preprocessing 上，用所有該 fold encoded 欄位及截距進行 `numpy.linalg.lstsq`（與 P4-A 一致的 SVD 最小範數策略），記錄秩、nullity、condition、tolerance。其三折輸出是**新的**研究數據，不得先填寫歷史 P4-A 數字。

## 3. 特徵單位、五方法及固定有界候選

**選取單位決議（本文件提議採用）：** 一個 feature = 一個**該折轉換後 encoded column**。K grid = **[2,3,5,10,20]** 僅用於 Pearson / MI / Ridge RFE。Lasso/ElasticNet 以非零 encoded 係數數為自然選取數，**不強制 K**。每折記錄 `encoded_name → raw_source_column` 及不同的 raw-variable 數。例如原始類別 `Neighborhood` 分成八個 one-hot，是**1 raw field / 8 encoded fields**，不能以編碼後數目宣稱符合教師原始特徵規則。若某折有效 encoded 數少於 K，該候選標 `INVALID`，不可默默縮小 K。

### 原始來源與衍生指標的正式歸屬（Nex Delta #2）

選中每個 encoded 欄位都必須記錄 `encoding_type`、`is_derived`、`raw_source_columns: list[str]`（可多個）、`provenance_status`。**不得僅相信現有 `feature_manifest.source_column` 字串**：目前 Phase 3 對 `Has*` 使用 `ind.replace("Has","")`，其中 `HasGarage→Garage` 不是原始 CSV 欄名。以 `constants.py` 的 79 原始輸入欄位白名單驗證每個來源；未知、無法證實或指向非輸入欄者標 `UNRESOLVED`，**不得計入 raw count 或將之宣稱為新的原始特徵**，並阻擋發布完整的原始特徵來源統計。

**由 Phase 3 `pipeline.py` 的衍生公式確認的結構指標對應（文件規格，不修改來源程式）：**

| 衍生 encoded 欄位 | 實際原始輸入來源 |
|---|---|
| `HasGarage` | `GarageType` |
| `HasBasement` | `BsmtQual`, `TotalBsmtSF` |
| `HasFireplace` | `Fireplaces`, `FireplaceQu` |
| `HasPool` | `PoolArea`, `PoolQC` |
| `HasFence` | `Fence` |
| `HasAlley` | `Alley` |
| `HasMiscFeature` | `MiscFeature` |

`MasVnrType_is_missing`／`MasVnrArea_is_missing` 分別源自 `MasVnrType`／`MasVnrArea`；其他 ordinary one-hot、numeric、ordinal 的來源應從 Phase 3 manifest 對照真實欄位驗證。**raw_count = 所有已選 encoded 欄位之 `raw_source_columns` 的唯一聯集數量**，多輸入衍生指標可能貢獻 2 個已存在的 raw input，衍生本身貢獻 **0 個新的 raw input**。若報告「原始特徵選取頻率」，多輸入欄位只表示*參與衍生計算*，不得冒稱模型直接獨立選了所有上游欄位；須另外列 `direct_raw_sources` 與 `derived_dependencies`。老師「≥14」的 eligible 候選數仍只以原始 79 欄為基礎。

**R4 合成契約必測：** ① `HasGarage` 必須歸屬 `GarageType` 而非 `Garage`；② `HasBasement` 必須對應兩個真實來源且 unique union 不重複計數；③ 來源含未知標籤時 fail-closed、不得多算；④ 每折 one-hot 所屬 raw 欄正確；⑤ 開發集資料／CV 及選取輸出不可包含 `Id`／`SalePrice`。所有 synthetic tests **NOT RUN**，需取得後續工程授權才測試。

**共用前處理：** 沿用 Phase 3；針對需按係數大小比較的 Lasso/ElasticNet/Ridge RFE，對該折 training transformation **所有非二元連續／序位 encoded 欄**再用 `StandardScaler` fit/transform，one-hot indicators 保持 0/1，相關的懲罰與重要性差異作為明示限制。Pearson/MI 基於該折 training encoded 資料評分。有限/NaN 常數欄不能無聲略過，必須記 `score_invalid`，確保每一候選可以安全選 K。

| 方法 | 特徵選取訓練規格 | 固定候選／異常處理 | 預測評分 |
|---|---|---|---|
| **Pearson** | Training 上各 encoded 欄與 `SalePrice` 的 Pearson r，依 `abs(r)` 降冪 | K=[2,3,5,10,20]；零變異／非有限 r 記錄並置於最後（不可勝過有效分數），tie 依 encoded 欄名稱字典序 | 選中欄 → 帶截距 OLS |
| **Mutual Information** | `mutual_info_regression`，`random_state=42`，`n_neighbors=3` | K 同上；已辨識 one-hot 0/1 indicator 的 `discrete_features=True`，其餘 False；不能一律指定 `'auto'`。NaN/失敗與同分規則明記，seed 固定 | 選中欄 → OLS |
| **Lasso** | `sklearn.linear_model.Lasso`，`max_iter=10000, tol=1e-4, selection='cyclic'`，折內 scaled training | `alpha` grid **[0.1,1.0,10.0,100.0]**（SalePrice 原單位）；`abs(coef)>1e-8` 視非零；全部零則 `EMPTY_SELECTION`，不得虛構 OLS | **兩條分開報告**：選中→OLS、native Lasso |
| **ElasticNet** | `ElasticNet(max_iter=10000,tol=1e-4,selection='cyclic')` | `alpha` 同上；`l1_ratio=[0.2,0.5,0.8]`；非零判定同上；收斂警告、全部零不得算選特徵 OLS 有效 | 選中→OLS 和 native ElasticNet |
| **Ridge RFE** | training-scaled `Ridge(alpha=1.0)` 作 `RFE` base estimator，按 `abs(coef_)` 排除，`step=0.2` | K 同上；同分時用穩定輸入欄名排序建立的欄序，scikit-learn RFE 對完全 ties 的行為需以 synthetic 固定驗證 | 選中→OLS |

**雙軌有效性（Nex Delta #1）：** Lasso／ElasticNet 各候選的 `selected→OLS` 是唯一 tuning 與五方法 winner selection 依據。若該候選在任何折出現 `EMPTY_SELECTION`、未收斂、nonfinite、OLS 失敗或其它 invalid，該候選 **INVALID、不可參與主軌選優**；但仍保留 native 的可計算診斷結果並明示 `secondary_only`，不得以 native 成績救回 invalid primary 配置。若某方法所有候選皆 INVALID，該方法為 `METHOD_BLOCKED`，不得默默借用其它軌／其它方法補勝者；必須以新明示 amendment 與 Run ID 重新評審。本次所有方法的最終報告將 `selection_primary_cv_rmse` 與 `native_diagnostic_cv_rmse` 分列，native track 不另設獨立 winner。\n\n**模型細節：** OLS 用訓練設計矩陣與 intercept 求解，可容忍 rank deficiency 但必須紀錄條件數、nullity；選取後 OLS 與 native penalty score 絕不混成單一排名。若 selection 出現零有效特徵、nonfinite y/pred、convergence warning、無足夠特徵或 library API 不相容，該 task 記 `FAILED/INVALID` 並阻擋依其結果選 Winner；不應在後續折無聲替換演算法。完整所有方法至少列 selection-only 統一 OLS 比較，native Lasso/ElasticNet 另列；報告 one-hot 相依、相關性不等於因果、penalty scaling 與 non-nested selection optimism。

**候選成本上界（概念最小 fit 次數，不含 RFE 內部消去 fit）：** Pearson 5×3=15；MI 15；Lasso 4×3=12（+選後 OLS）；ElasticNet 4×3×3=36（+選後 OLS）；Ridge RFE 5×3=15 **RFE 呼叫但每次含多次 Ridge fits**；baseline 3。若算力不符預算，先 STOP 並回報有界結果；不得換回 SFS 或擅自打開 Holdout。

## 4. 結果、品質驗收與版本記錄

最小 schema：`run_id,task_id,method,track,fold,seed,git_sha,package_versions,data_digest,fold_digest,config_hash,encoded_count,raw_count,selected_encoded_names,selected_raw_sources,raw_source_columns,encoding_type,is_derived,provenance_status,derived_dependencies,primary_track,primary_valid,rank_or_score,coef_or_importance,rmse,mae,r2,ols_rank,ols_nullity,duration_seconds,fit_count,warning,status`。全量保留的中間預測和實體 CSV 僅存 ignored 私有工作區；只將經隱私審查的 aggregate tables/charts 送上 GitHub。

- **重現性**：K/alpha/grid/seed/版本/digest 完整；按方法候選折次保存結果；輸出 unique `task_id`，以 temp→完成檔原子寫入；僅 `COMPLETED` 且 digest 匹配者可進 aggregate。
- **特徵穩定性**：同方法及選中 K/config，依 encoded names 與 raw source 分別計算被選取折數 0–3、比例與每折名單；各折 schema 不同須說明。
- **資料隔離**：合成資料測試檢驗 fold-train-only transform/selection、Id/target 不入 X、validation 不 fit、292 Holdout/competition-test 零讀取、CV config 不洩漏。
- **數據與認證**：本 PR 為**文件審查**，所有 synthetic、模型分數、macOS safety 都 `NOT RUN`；未來在獨立授權後以測試/Run SHA 補實測證據。

## 5. 最多四 Worker 的最小安全執行契約（僅設計，非已運作）

Owner 方向為最多 4 個前景 Python 計算 Worker、兩個有人值守的終端（Monitor A、Stop B）；不是四個 Agent。**禁用 nested multiprocessing/Worker 和 `n_jobs>1`；限制 BLAS/OpenMP 各 1 thread。** 一個協調 Launcher 對每 Worker 指派唯一 task；不得多 Worker 寫同一結果。詳細可執行工具依 #22 後續工程授權建立；本文件只凍結 R4 前測試契約：

1. **身份和隔離：** `run_id/task_id` 唯一、Git/data/config/fold digest，記錄 PID、PPID、process creation identity、argv、owner/status，stop 前重核實，對未知 PID 不能發訊號。
2. **最小 control CLI 合約：** 必須提供**真實可複製**的 `status --run-id`、`freeze --run-id`、`stop-all --run-id`。前者核對所有本 Run Workers/子程序的各別 RSS 及 aggregate RSS、missing identity 必為 UNKNOWN；freeze 原子禁止再領新 task；stop-all 先 freeze→cooperative/TERM→有界等待→重查身份→必要時僅對確認程序 KILL→核對存活/殘留及狀態。**CLI 名稱及實作尚不存在，此處只是 acceptance interface**。
3. **監看與 STOP：** 需指派人工值班者、兩個已準備好的終端；每約 **3 秒**更新 worker-scope RSS（KiB；`sum(RSS_KiB)/1024/1024` GiB），另看 macOS Memory Pressure、Swap、互動延遲。暫定 **20 GiB WARNING（freeze）/24 GiB STOP（精準 stop-all）**；為人工觀測觸發、**非硬 RAM cap**，RSS 共享頁可能重複計算；只要系統異常即使不足 20 GiB 也 STOP。監看者離開、Terminal/SSH 失效時停止新派工；身份不明則停止派工上報，不能盲目 kill。
4. **預檢必測：** 在任何正式 Ames 計算前，以小型 synthetic 模擬四 Worker 的 unique IDs、身份重驗、RSS 合計、20/24 threshold 演練、freeze、TERM/必要時 KILL、部分 CSV 與原子輸出、輸出恢復、重複 run_id、Worker crash、lost-monitor、超時、unrelated-process unaffected。**預檢 PASS 及 Owner 另授權，才可執行四 Worker**。
5. **故障與結果**：故障先 freeze 整批 admission，已完成 checkpoints 保留，故障 task `PARTIAL/FAILED`；如果安全/記憶體未知則精準 stop remaining identified in-flight；重跑僅在 SHA/digest 一致且得到明確授權。不得 `killall python`、寬廣 `pkill`、盲目 group kill，或影響別的研究程序。

**有界預算（R2 提議初始固定上限；R4 可在新授權下更改）：** Pearson 2m、MI 5m、Lasso 10m、ElasticNet 15m、Ridge RFE 30m，總體 90m（含 10m 校準）。屬計劃上限，不是實測 throughput／系統提供的自動 enforce；到限人工 freeze/stop 並保留 PARTIAL。若單方法涉及成本過高，只呈報限制及 STOP，不能自動擴張預算。沒有將 #26 launchd/Watchdog/Supervisor 設計納入本研究必要前置。

## 6. R2 文件 Gate 與後續授權

- **文件 PR**：只修訂 ADR、protocol、索引、必要的 RegScope Agent 三角色協作規則。嚴禁修改模型程式、Runner、測試、部署、私有材料。
- **R3 Review**：審查 5 方法/每折 training-only、欄位計數、同折基準、CV bias、封存 Holdout、安全預檢標記 NOT RUN、公開資訊最小化；以**精確 PR HEAD SHA**核對。
- **後續**：Owner 另授權 Merge → 更新原 #21/#22/#23 指向新規格 → Owner 另授權 #22 工程/合成預檢與 #23 Development 實驗 → Phase 5 一次 Holdout → Phase 6 網站/交件。R2/R3 PASS **不是模型或 Worker 可以立即開跑的許可**。
