# RegScope Case Package v1.0 — 資料包與前後端交換契約

> **唯一目的：定義「後端產生一包資料 → 驗證 → 核准發布 → 前端自動渲染」的完整交換格式。** Draft PR #35 現包含文件與一份混合狀態的 Case Package Sample：Phase 4 是來源報稱、尚未驗證的 Development aggregate，其餘階段維持 MOCK/UNAVAILABLE；整包仍未核准發布。這不授權模型運算、私有 OOF/Holdout 讀取、CLI/前端工程、Merge 或 Deploy。Phase 5 依 [Issue #37 §15](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/37) 對齊，但該 §15.4 是概念 JSON，**不是有效公開 fixture**。本文件是 v1.0 設計權威；碰到舊文件路徑/欄位不一致，以這份契約為提案準則，未核准部分交 Reviewer。

## 1. 精確的角色與發布模型

- 一個 Case Package 資料夾代表 **一個 case 在某個 `package_revision` 的不可變快照**。Case 在新資料、圖表或評估被核准時，產生下一個 revision；不覆寫舊版。
- **Backend Exporter**：從獲授權、可追溯的研究產物離線計算/整理，輸出所有前端所需的研究摘要 JSON、表格與批准圖資；前端不得重算 CV、特徵選擇、OOF 或 Holdout。
- **Package Validator**：核對 JSON Schema、實體路徑、每個檔案 SHA-256、交叉 ID、統計母體、型態與公開權限；未通過即不得發布。
- **Release Publisher**：把合格 Case 包複製到新的 immutable `release_id` 路徑，整批驗證後最後才切換網站索引。部署技術尚待工程審核，但**原子發布**是契約要求。
- **Frontend Case Renderer**：只讀 `package.json`、`case.json` 和 Manifest 指定資源。既有 Phase 1–6 UI 元件固定，JSON 決定內容、按鈕數、哪些圖可用；新增未知圖型或新互動必須先實作並版本升級。
- **Prediction Server**：與公開 Case 包完全分離，僅使用後端私有、核准且已載入的模型與 fitted pipeline；公開 Case 包至多包含可使用模型的*安全索引*，絕不可放 `joblib` 或使使用者 URL 直接載入模型。

## 2. 一個上傳資料包的標準目錄樹（每檔用途）

```text
case-package/                                   # 送至 STAGING 的一包；單一 case_id
├── package.json                                # 必備：入口、版本、各 Phase ref、files SHA 清單
├── case.json                                   # 必備：case_id / 名稱 / 問題 / target / 單位 / 語言
├── phases/
│   ├── phase-01/
│   │   └── content.json                        # Phase1 敘事：problem / objective / limits / source
│   ├── phase-02/
│   │   ├── analyses.json                       # Phase2 選單：分析 id/標題/說明/圖資/證據
│   │   └── figures/                            # 選用：經核准 SVG/PNG，單一 figure_id 對應一組
│   │       ├── fig-01.svg                      # 原圖：Dataset Overview（核准才可放）
│   │       └── fig-01.png                      # 同圖的 fallback（核准才可放）
│   ├── phase-03/
│   │   ├── preparation.json                    # 四段特徵型態與 80/20 split
│   │   └── feature-lineage.json                # 選用：raw→encoded 特徵對照與 fit scope
│   ├── phase-04/
│   │   ├── modeling.json                       # 真實 execution/config inventory、方法與可選參數
│   │   ├── configurations/                     # 選用：資料大時分拆；immutable ids
│   │   │   └── <configuration_id>/
│   │   │       ├── metadata.json               # method/track/params/protocol/fit scope
│   │   │       ├── fold-tasks.json              # fold task id/status/observed-K/row counts
│   │   │       ├── cv-metrics.json              # MAE/RMSE/R² fold mean、sample SD／適用性
│   │   │       └── selected-features.json      # 經公開審查之 encoded→raw lineage 表
│   │   └── charts/                             # 選用：比較曲線原始 tidy data 與圖資
│   │       └── <chart_id>.json                  # chart type/x/y/points/status/source/compatibility
│   ├── phase-05/
│   │   ├── evaluations.json                    # **唯一 Phase5 公開入口**：合法 evaluation 索引
│   │   ├── evaluations/                        # 選用：只在已核准時分拆
│   │   │   └── <evaluation_id>.json             # 同 population/metric_source 的評估記錄
│   │   └── figures/                            # 選用：FIG-P5-01/02/03/04 已核准圖/替代表
│   └── phase-06/
│       └── inference-catalog.json              # 模型 public-safe readiness / metadata only
└── assets/
    └── figure-manifest.json                    # 所有公開圖之元資料/SHA/大小/alt/table/source
```

**每個子目錄若無可發布資料，仍可保留該階段的有效 EMPTY/UNAVAILABLE JSON**，但是**不建立不存在的圖片或 configuration/evaluation 假紀錄**。深層 optional 檔案只有當 root manifest 真正參照且實體存在時才需建立。上面 `<...>` 是檔名位置符號，非真的檔名；真實路徑嚴禁穿越目錄（`../`）、跨 Case、跨 release 或帶 private 檔案絕對路徑。檔名大小寫需完全吻合；UTF-8 JSON、不允許註解。

### 2.1 公開網站路徑（原始包與發布路徑分離）

```text
PRIVATE (backoffice/staging)
  staging/<upload-id>/case-package/...
  local/research/<case-id>/...                    # 私有 source，永遠不是發布根目錄
  private-model-registry/<model-id>/...           # joblib / dependencies / pipeline 私有

PUBLIC (publisher 產生、URL，只讀)
  /data/current-release.json                     # 唯一可變指標，指向 release_id
  /data/releases/<release_id>/index.v1.json       # 整個 release 的 case 登錄清單
  /data/releases/<release_id>/cases/<case_id>/package.json
  /data/releases/<release_id>/cases/<case_id>/case.json
  /data/releases/<release_id>/cases/<case_id>/phases/...
```

公開前須經 Reviewer 與 Owner/授權發布流程；Case 上傳不等於核准研究、不等於部署 API。網站先取得 `current-release.json` 再將 `release_id` **pin 住整段頁面讀取**，全部 Phase/圖表從同一 release 解析；若刷新發現新版，先載入新 manifest、驗證後整體切換；失敗保留舊版並明確提示。快取 key 至少含 release_id/case_id/resource path；404、SHA 不符或版本不相容不得混用舊新資料。

## 3. 根目錄 `package.json` — 真正的唯一入口

**必填：** `package_schema_version`, `package_id`, `case_id`, `package_revision`, `package_status`, `publication`, `case_ref`, `phases`, `files`；`asset_manifest_ref` 可為 null。範例請直接打開 [sample/ames-housing/package.json](./sample/ames-housing/package.json)。

| 鍵名 | 型別／範圍 | 精確意義 |
|---|---|---|
| `package_schema_version` | semver string | 此 Package 文件格式，**不是**模型版本 |
| `package_id` | stable string | 此候選資料包身分；不可覆寫既有核准 revision |
| `case_id` | slug string | 所有子檔 `case_id` 必須一致 |
| `package_revision` | string | 某次資料快照版本；修改內容就需新 revision |
| `package_status` | `MOCK/PLANNED/UNAVAILABLE/VERIFIED` | 研究內容狀態，不能替代核准結果 |
| `publication` | object | `approved` boolean、`release_id` string|null、`review_status`；上傳時 false/null |
| `case_ref` | relative .json path | 指向同根 `case.json` |
| `phases` | object keyed `phase1..phase6` | 各物件 `status`, `data_ref`; 某 Phase 沒資產仍有資料狀態 |
| `asset_manifest_ref` | string|null | 本包所有圖檔共用索引 |
| `files` | array | **發布前必須非空且涵蓋所有檔案**：每項 `path,sha256,bytes,mime`；不含 `package.json` 自身以避免自我雜湊循環 |

**完整性規則：** 根 package manifest 的 `files[]` 覆蓋所有實體子檔（除自身），每個 SHA-256 與精確 bytes/MIME 實際一致；任何 `data_ref` 或 `image_ref` 必須命中 `files[]` 且存在。Ames Sample 現已封存 staging 檔案清單；雜湊只證明快照完整性，**不代表研究驗證、權利審查或發布核准**。任何 `files:[]` 仍是未封包 staging，不能通過 publisher gate。發布仍需獨立審查、來源/權利檢查和核准。這是刻意分清「可讀、可檢查的 staging package」與「可正式發布的完整包」。Validator 在 staging 可提供 `fixture_only` 模式，release mode 必須嚴格拒絕空雜湊清單。

## 4. `case.json` 與共同欄位詞彙

`case.json` 必含 `schema_version`, `case_id`, `title`, `case_status`, `methodology_id` (可 null), `source`, `target` (PLANNED 時可 null), `language`。Source 至少 `label,url,license_review`; target 為 `raw_field_id,label,unit,value_type`。顯示語言 `zh-Hant`，英文術語可並列；不能由 Case title 猜貨幣或把跨案例 RMSE 當同一排行榜。

**所有 Phase JSON 共通：** `schema_version`（單檔 schema 版本）、`case_id`（root 一致）、`status`（此檔的公開研究狀態）。正式 VERIFIED 數值/圖還需要安全來源 ID、source SHA、公開審核和 n/scope；未驗證數值一律標 `SOURCE_REPORTED_NOT_VERIFIED` 在欄位級 `*_status`，不得被實證圖表 renderer 使用。

**ID 層級（對齊 Phase 4 與 Issue #37）：** `case_id → execution_run_id → configuration_id → task_id/fold_index`；`configuration_id + evaluation_population + metric_source → evaluation_id`（須從來源驗證、不可憑字串臆造）；`final_fit_id` 僅在實際完整訓練產物存在時記錄；`model_id+model_version` 僅核准 registry 註冊後可用。舊 UX 把 method/params 當 `run_id` 的叫法作廢。32 configs 不等於 32 execution runs。

## 5. Phase 1–3 每個 JSON 的欄位語意

**`phases/phase-01/content.json`**：
- `sections[]` 是依順序顯示的文字卡，記錄 `section_id`（stable key）、`title`、`body`。來源連結與真正問題、研究價值與限制可由 exporter 填實證文案；不得由 UI 根據數字自行創作。此頁不需要圖。
- 無正文時 `status=UNAVAILABLE`，首頁仍可顯示 dataset 卡片與原因，不能顯示另一 case 的文字。

**`phases/phase-02/analyses.json`**：
- `analyses[]` 每一項代表**一個可以選取的 EDA 視角**；`id,figure_id,title,status,image_ref,table_ref,description,finding,limitations,provenance_ref`；`default_analysis_id` 必須指向陣列中存在的 id（或陣列為空時 null）。
- `image_ref` 是 **Case Package 內相對路徑**，例如 `phases/phase-02/figures/fig-01.svg`；僅 `status=VERIFIED` 且審查通過/檔案存在才可給圖。若 null，顯示相同主圖框的 UNAVAILABLE 說明，旁邊說明同步更新、不顯示上一張舊圖。
- Ames 已審查四類 FIG-01/02/03/06，但 Sample deliberately sets all `image_ref:null`，表示這包未包含已完成 URL/hash/licensing 核驗的原始圖；不由 UI 伪造圖片。

**`phases/phase-03/preparation.json`**：
- `feature_types[]`: `type_id,label`；合法 Nominal/Ordinal/Discrete/Continuous 等依 case 元資料定義，顏色前端依 stable type_id 一致顯示。
- `stages[]`: 嚴格順序 `raw,filtered,processed,encoded`（也就是原始候選→排除後→資料處理後→編碼後）。每筆 `id,label,unit,total,total_status,segments[],distribution_status`，已核准 segments 的 `type_id,count` 為非負整數且相加等於 total；前端只用 count/total 計算百分比，不信任手填百分比。
- **248** 必須有 `fit_population,pipeline_version,transformer_fit_id,split_id,source_artifact_sha256,lineage_ref` 等核對才可能 VERIFIED。Sample 248 是交接值 `SOURCE_REPORTED_NOT_VERIFIED`，四條比例圖類別未知時**整條顯示 UNAVAILABLE**，不能等分四種顏色。
- `treatments[]` 記錄真正採用的缺失值/類別處理，含 source evidence、fit scope；不能憑欄位類型自動假設 median 或 One-Hot。
- `split`: `source_labeled_rows,training_rows,holdout_rows,seed,status`，此為**資料列**的 80/20 長條（Ames 1168/292），與前面四條**特徵數**不同母體。不要把 Kaggle unlabeled competition test 1459 混入 Holdout。
- `feature-lineage.json` 為可選公開審核原始→編碼映射：`schema_version,case_id,pipeline_version,fit_population,source_artifact_sha256,mappings[]`；mappings 須標出 single/multi-source attribution、防止重覆計數，不足時保持 UNAVAILABLE。

## 6. Phase 4：execution/configuration/fold、圖表與折間 K

**`phases/phase-04/modeling.json`**：
- `cv`: `training_rows,fold_count,protocol_id,status`；真實 fold 由資料產物核實。**CV Folds=3** 與方法的 **Top K** 是不同控制/概念。
- `methods[]`: method_id/label/parameters[]；每個 `parameter_id,label,data_type` 為動態表單定義，0–N 個均可。
- `execution_runs[]`: 每個是**一次真實後端執行**，包含 `execution_run_id,source_manifest_sha256,status` 和關聯的 configurations。不可假造 per-method run。
- `configurations[]`: 一個 method+track+params+protocol 的完整組合；至少 `configuration_id,execution_run_id,method_id,track_id,params,protocol_id,status`，可補 metadata_ref/fold_tasks_ref/cv_metrics_ref/selected_features_ref。**前端選單只列真正可供該 view 的 configurations**，不能從 parameters options 笛卡兒積拼出不存在的組合。
- `default_configuration_id`: 只能指向確實存在且有來源、合格的配置；否則 null。
- `charts[]`: `chart_id,chart_type,points_ref,axes,comparison_protocol/status`。比對圖只放同一 protocol、metric scope、track 的可比 configs。未核准資料點不呈現。

**選用 `configurations/<id>/metadata.json`** 詳列 `requested_k` (fixed K or null)、`selected_k_by_fold`、`selected_k_summary`（observed K range 等）、`final_fit_selected_k`（獨立 Final Fit）、`fit_population`、`source_artifact_sha256`。Lasso α=100 報告過的 104/103/102 fold vs final 97 **不是同一個 X**；requested Top K 曲線不能硬混 observed K。Lasso 可用 alpha、Elastic Net 可用 alpha + l1_ratio facet，或標示 observed-K 而不要誤導。

**選用 `fold-tasks.json`** task_id/fold_index/status/train_rows/validation_rows/selected_encoded_k/provenance；96 tasks 是交接範圍，只有合法完成者才能產生可比較 CV。
**`cv-metrics.json`** 需 metric、target_unit、scope、fold_values、mean、sample_sd、fold_aggregation、n、status、source；fold mean/sample SD 與 pooled OOF 分開。
**`selected-features.json`** 僅真實可公開的 encoded_feature_id、raw_source_field_ids、rank/coef（無來源則 null）；排序不得暗示不存在的 ranking。
**`charts/*.json`** 存 tidy points/series、x_semantics (requested_k / alpha / observed-fold selected K)、y=CV RMSE、track/protocol；必須保留完整 configuration IDs，不平滑造點。擴展新圖型須 frontend schema 支援。

## 7. Phase 5：與 Issue #37 §15 嚴格相容（以本 package 契約為準）

**唯一公開入口 `phases/phase-05/evaluations.json`**。此檔為「已核准 evaluation 列表」，不是私有評估原始資料容器。**最重要：Issue §15.4 的 `evaluation_id:null` 是概念草稿，不是可加入 `evaluations[]` 的合法記錄**。真正缺 evidence 時寫 `evaluations:[]` 並標示 `status=UNAVAILABLE`、reason_code。Sample 已按此規則落地。

公開 Evaluation 每筆必須具備：
- **身分**：`evaluation_id,case_id,execution_run_id,configuration_id,final_fit_id|null,model_id|null,model_version|null`。JOIN case/config/eval 必須完整且同 release；private 未註冊模型不可自己造 model_id。
- **量測母體**：`evaluation_population` ∈ `development_oof|holdout|training_in_sample`、`prediction_origin`、`metric_source` ∈ `cv_fold_mean|pooled_oof|holdout_aggregate|training_in_sample`、`n`、`target{column,unit}`。**同一 Evaluation 不混 metric_source**。
- **指標**：`metrics.mae/rmse/r2` 各有 `value,status,reason_code,evidence_ref`。MAE/RMSE = target 單位；R² 無單位、可負、不是百分比。每個 missing 是 null，不填 0。
- **CV**：`fold_summary{fold_count,aggregation,sample_sd,fold_values_ref}`，fold mean / sample SD **不能冒充** pooled OOF score。
- **圖片**：`figures[]` 每個 `figure_id,status,asset_ref,sha256,evaluation_id,evaluation_population,configuration_id,prediction_origin,n,axes,residual_sign,alt,accessible_table_ref,limitations,publication_review`，只可引用與 Evaluation 同母體的合法已公開圖。**FIG-P5-01** Actual vs Predicted (x actual/y predicted/y=x)；**FIG-P5-02** Residual vs Predicted (x predicted/y actual−predicted/y=0，正殘差=低估)；**FIG-P5-03** Residual Distribution (bins、n、zero line)。Holdout 聚合數字不會自動產生逐列 Holdout 圖。
- **區間**：`interval.int_f` 表示方法 feasibility；`interval.int_s` 表示符合作業要求的真正 CI/PI 圖與解釋，彼此獨立，需 `status,reason_code`；INT-S 若完成還需 method/type/nominal_level/population/asset_ref/coverage_evidence。**INT-F PASS 不等於 HW2 完成**。
- **證據**：`evidence{source_artifact_sha256,source_ref,protocol_version,review_url}`、`asset_status`、`review_status`；研究驗證、公開核准、圖檔存在是三道不同關卡。

私人 Phase 5 原始產物 **不進此公開包**，維持 Issue #37 提案 `local/research/phase5/<gate_id>/artifacts/`：`evidence-inventory.json`, `gap-permission-matrix.json`, `evaluation-metrics.json`, `figure-manifest.json`, `evaluation-report.md`, `qa-report.json`, `checkpoint.json`。Exporter 需將已核准的指標和圖衍生為上述公開 projection。不能讓前端讀 `p4b_oof_predictions.csv` 或封存 Holdout。任何 source key path UNKNOWN，保持 UNKNOWN 直到獲准 audit。

## 8. Phase 6：模型索引與動態輸入 Schema

**`phases/phase-06/inference-catalog.json`**：
- `models[]` 只列具 public-safe registry 記錄的模型摘要。每項 `model_id,model_version,source_execution_run_id,source_configuration_id,model_status,input_schema_ref,readiness`。
- `readiness.predict_enabled` 只能由後端判定；**五段 gate** `artifact_exists`, `load_verified`, `raw_input_schema_validated`, `registered`, `api_deployed_and_qa_pass` 全 PASS，加授權發布才為 true；Mac/Windows 本地 joblib 存在不等於 READY。
- 如果沒有核准模型，`models:[]`, `status:UNAVAILABLE`, `readiness.reason_code:NO_APPROVED_MODEL`；前端呈現「此模型尚未準備好」，讓使用者選其他已核准模型或返回 Phase 4。
- 活的 `GET /api/cases/{case_id}/models` 查 public registry；`GET /api/models/{model_id}/input-schema?model_version=...` 查該 **特定模型** fitted pipeline 的 raw-input schema；`POST /api/predictions` 提交 `case_id,execution_run_id,configuration_id,model_id,model_version,schema_version,raw_inputs`。這些為**擬議端點，未部署**。沒有 API 時，靜態 inference catalog 只做 readiness 展示，**Predict 禁用**。
- Input schema 每項採 `raw_field_id,label,data_type,control,unit,required,min,max,allowed_values,missingness_kind,dependencies`；`data_type` = numerical/nominal/ordinal 等，不能讓使用者輸入 One-Hot 後的 248 或特定 Final Fit 的 97 encoded columns。Basic/Advanced 只有經安全可省略規則批准才允許。
- API 必須驗證當次 Model Registry 的 case/execution/config/model/version/input_schema 完全一致，拒絕 unknown category、非法 missingness、超界和未授權。返回已訓練 pipeline 的 prediction 和 request/provenance 或 typed error；變更 case/config/model/input 清除舊結果，忽略 stale reply。

## 9. `assets/figure-manifest.json` 與圖片輸出格式

**圖資索引每筆**：`figure_id,case_id,phase,source_configuration_id|null,source_evaluation_id|null,svg_ref|null,png_ref|null,width,height,alt,accessible_table_ref|null,source_evidence_ref,sha256_svg|null,sha256_png|null,publication_review,status`。引用的圖必須在 manifest、root `files[]`、物理檔案三方吻合；所有核准圖都附可讀的圖說與資料來源。
- **Phase 1**：文字，沒有圖。
- **Phase 2**：獨立審核 FIG-01/02/03/06，選一張顯示；SVG 優先、PNG fallback，長圖依內容，landscape 可採 SVG `viewBox 1200×675`、PNG 約 1600×900，相關矩陣不強迫裁成 16:9。
- **Phase 3**：四段 **100% stack bars 從 JSON 產生**，相同 type_id 固定同色；沒有分段 counts 時顯示 UNAVAILABLE 空圖框；80/20 split 顯示列數而非特徵數。
- **Phase 4**：3-fold training/validation 由 fold task JSON 產生三條橫條；真正 config 比較圖與 selected features table/point plots 從 JSON 渲染；可選匯出同來源 SVG/PNG。requested K vs alpha 不能混在同一 X 軸。
- **Phase 5**：FIG-P5-01/02/03/04 只依 Issue #37 的合法 source/population 產生；優先 residual FIG-P5-02，但缺圖時誠實 UNAVAILABLE。逐點資料即使轉成 PNG 也需 public-safety 許可。
- **Phase 6**：表單 + API 單筆預測，沒有必要要求靜態研究圖；單筆區間只有合法 interval model 且證據充分才有。
- 圖檔禁止 scripts/外部連結、私人路徑 metadata；字體採可用/嵌入禁止的安全設計，鍵盤及無障礙需 `alt` 或 aggregate table、legend、軸單位、母體、n、source。Frontend 不可根據圖片顏色擷取資料。

## 10. Sample 真正放在哪、如何測試

**現有可機器讀取的 11 個 JSON 檔**：
- [sample/ames-housing/package.json](./sample/ames-housing/package.json)；[case.json](./sample/ames-housing/case.json)
- [Phase1](./sample/ames-housing/phases/phase-01/content.json) · [Phase2](./sample/ames-housing/phases/phase-02/analyses.json) · [Phase3](./sample/ames-housing/phases/phase-03/preparation.json) · [Phase4](./sample/ames-housing/phases/phase-04/modeling.json) · [Phase5](./sample/ames-housing/phases/phase-05/evaluations.json) · [Phase6](./sample/ames-housing/phases/phase-06/inference-catalog.json) · [Figure manifest](./sample/ames-housing/assets/figure-manifest.json)
- [sample/planned-case/package.json](./sample/planned-case/package.json) · [case.json](./sample/planned-case/case.json)

**Sample package is `PLANNED`, never VERIFIED, and never approved for production.** Phase 4 contains 32 configurations and 96 fold-task records projected from a manifest-marked public summary; those records and the Final Fit metadata projection remain `SOURCE_REPORTED_NOT_VERIFIED`. Five fold tasks and two configurations are incomplete/invalid, not silently dropped. The Final Fit ID remains null because no independently reviewed source ID is available; the fitted binary and sensitive values are excluded. Phase 3 contains only source-reported totals/split counts with unavailable distributions; Phase 1 remains MOCK, Phases 2/5/6 remain unavailable. No Phase 5 result is inferred from Phase 4. The sealed `files[]` is an integrity manifest only. Publication remains false, and this sample must not be presented as verified research or a live deployable release.

### 10.1 Offline exporter contract (future permitted implementation)

Inputs: only Owner-authorized source allowlist, existing research manifest/config/task metadata, reviewed EDA/Phase5 assets, no implicit Holdout reads. Proposed command separation:
```text
inventory(case_id, allowed_sources)    # list file key paths/hashes without reading restricted rows
export(case_id, authorized_inputs)     # materialize JSON and approved figures to staging ONLY
seal(staging_package)                  # compute SHA-256 for every child except package.json
validate(staging_package, mode)        # schema+FK+numeric/scope+refs+hash+privacy/license
publish(sealed_package, approval)      # immutable release + atomic index pointer update
```
Each action idempotent, bounded IO, emits `coverage-report` and `checkpoint`; no training/resume/Final Fit side effects. If owner gate unknown, STOP. Source mapping table must name `source_artifact_sha256,source_json_path/csv_column,canonical_field,normalization,permission,review_status` and show UNKNOWN rather than invent.

### 10.2 Upload/publish acceptance checklist (fail-closed)

1. `package.json` schema/ID/revision valid; every referenced file exists and matches exact SHA+bytes/MIME; no unmanifested file, secret, joblib, private row CSV, path traversal or cross-case refs.
2. All JSON parse UTF-8; fields validate current JSON Schemas; `case_id` identical across files; no duplicate analysis/config/evaluation/figure IDs; wrong FK, mismatched target unit, source population, CV protocol, track or release FAIL.
3. Phase2 image refs resolve to approved figure manifest; broken one asset unavailable **in its own card**; Phase3 stage sums/count status legitimate; Phase4 config tuples source-backed; Phase5 evaluation_id nonnull and same source/eval; Phase6 model passes separate server registry gates.
4. Public-safety/rights/source evidence check; MOCK/PLANNED and no evidence never become VERIFIED merely because sample renders; real public projection only after independent QA/approver signoff.
5. Publish full immutable release and flip current pointer atomically; on missing asset/timeout/hash mismatch **no promotion**; preserve previous release and rollback path.
6. Frontend reads index, selects a case, renders available phase data, then a second PLANNED case without leaking prior Ames values; no stale async image/metric/prediction. Six navigation tabs retain their slots with proper EMPTY/UNAVAILABLE placeholders.

## 11. Canonical future extensions and explicit unknowns

Open technical followups: Draft 2020-12 JSON Schema files and real strict validator are **not yet implemented**; the Phase 4 sample maps the manifest-marked public summary and a restricted Final Fit metadata projection, while private details, raw task checkpoints, fitted binary internals, and Phase 5 OOF remain excluded. Public Phase2 current asset URLs/SHA/license, Phase3 248 fit scope, Phase5 legal figures and deployable models still need evidence. The Phase 4 sample is source-reported and structurally reviewed, not scientific verification or publication approval.

**Change policy**: backward-compatible optional field may add a minor schema version after review; deleting/renaming required keys, changing ID semantics or accepted status requires major version and a deterministic adapter, not silent drift. Every new Case Package must declare schema version and be rejected with actionable error if unsupported. This contract is the backbone of frontend/backend separation; **no research data is invented to make a demo appear complete**.


## Phase 5 normative child contract — v1.0

The precise fields, enums, figure/publication rules and static-read API for `phases/phase-05/evaluations.json` are defined **only** in [phase-05/PHASE-05-DATA-CONTRACT-v1.md](./phase-05/PHASE-05-DATA-CONTRACT-v1.md), with [JSON Schema](./phase-05/evaluation-index.schema.json) and [sample](./phase-05/sample/evaluations.json). Earlier prose in §7 is background; on conflicting shapes the child contract wins. This release requires exactly one `phases.phase5.data_ref` in the Case Package root. An empty evaluations array is valid and safer than the conceptual null-identified item from Issue #37 §15.4.

## F01–F12 Review freeze rules — canonical v1.2 (2026-10-27)

**P5-UI follow-up #6421939874:** ACCEPT F01–F12, with code-level release validation **DEFER / NOT_IMPLEMENTED** until authorization. This section is normative; resolve any old §3/§4 wording using the explicitly corrected replacements in their paragraphs; do not reintroduce a second source-mapping authority.

**Producer:** P5-A minimum only `evidence-inventory.json`, `gap-permission-matrix.json`, `checkpoint.json`. The **only** authoritative mapping is `evidence-inventory.json.source_key_mappings[]`; each row has `source_artifact_id,source_sha256,source_key_path_or_csv_column,canonical_destination_field,normalization_rule,read_permission,verification_status,reason_code`. Any optional derived map must contain `parent_inventory_sha256`, and never become a required source or competing truth.

**Linked evaluation A — exact UI lookup:** First resolve KPI evaluation by `case_id+execution_run_id+configuration_id+evaluation_population+metric_source=cv_fold_mean`. Follow **only** `linked_evaluation_ids[]`; each reference must resolve within the same case and pinned release. The linked evaluation must be `metric_source=pooled_oof`, `evaluation_population=development_oof`, same execution/config, protocol/version and approved evidence; it owns **its own** FIG-P5-01/02/03. Check reciprocal compatibility and explicit permission; do not require the KPI evaluation_id to equal the linked graph evaluation_id. If link missing, invalid, or not approved, graph is UNAVAILABLE. Holdout aggregate cannot borrow OOF graphs, directly or transitively. When a pooled OOF evaluation is selected, its own figures may display; never transfer figures between populations.

**Schema versus release validator:** JSON Schema 2020-12 checks nested types and local conditional values (and `date-time` only when FormatChecker/format assertion enabled). A **separate bundle validator** must check ID uniqueness, default IDs, link membership/type/protocol, target mapping, eligible figure scope, publication permission, file SHA/size/MIME, relative path traversal, same-release refs and license. See [VALIDATION-MATRIX.md](./VALIDATION-MATRIX.md). Bundle validator runtime: **NOT_IMPLEMENTED**, and therefore real release PASS cannot be claimed.

**Figure tokens and units:** FIG-P5-01 axes `x.field=actual`, `y.field=predicted`, `reference_line=y_equals_x`; FIG-P5-02 `x.field=predicted`, `y.field=actual_minus_predicted`, `reference_line=y_equals_0`; FIG-P5-03 `x.field=actual_minus_predicted`, `y.field=count`, `reference_line=x_equals_0`, `histogram.bin_count>=1`, `histogram.n=n` and verified bin edges. All target-valued axes have `unit=target.unit`, count is dimensionless `count`. Histogram and plot asset only after approved paired predictions and publication QA.

**Metrics/scope:** VERIFIED MAE/RMSE require finite number >=0 and nonempty evidence_ref. VERIFIED R² is finite, dimensionless and may be negative. UNAVAILABLE must be null with a reason. For `cv_fold_mean`, `metrics.*.value` is source-backed mean across explicitly scored folds and `fold_summary.sample_sd.{mae,rmse,r2}` separately stores per-metric sample SD with `ddof=1`; not a pooled OOF value. Pooled OOF must have its own evaluation ID and metrics; no implicit averaging or synthetic folds.

**Intervals:** `int_f.status=PASS` does **not** complete `int_s`; INT-S PASS requires reviewed method/type/level/population/figure asset/coverage evidence. Unavailable INT-S keeps the homework interval requirement outstanding. Historical Holdout 292 aggregate has no row-level plotting permission.

**Target join:** public P5 `target.column = case.json.target.raw_field_id`, `target.unit = case.json.target.unit`; source `case.json.target.value_type=number` is checked. The frontend never infers SalePrice/USD from case name, nor displays R² as a percentage.

**Render authority:** `ui.*` holds only ordering/labels/figure slot IDs, not availability status. An evaluation is eligible only if its own review/source evidence passes and its parent release is approved. Metric display requires own VERIFIED value/evidence; figure display additionally requires its own VERIFIED, APPROVED publication, asset_status AVAILABLE, case-root asset_ref + correct SHA + public allowlist. An EMPTY/PLANNED/MOCK/PENDING/REJECTED context never displays empirical data. A published EMPTY (evaluations:[]) is legitimate with `status=UNAVAILABLE` and reason, but must be sealed and approved at **package publication layer**.

**Lifecycle:** staging may have release_id/generated_at=null, PENDING, files=[]. Publication mode must require real pinned release_id, valid UTC timestamp, independent APPROVED review, sealed all-files manifest, digest and link integrity, no unauthorized private data and atomic release pointer switch. Schema validation alone is insufficient and does not authorize publication.
