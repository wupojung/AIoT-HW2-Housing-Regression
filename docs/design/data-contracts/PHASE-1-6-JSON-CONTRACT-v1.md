# RegScope｜Phase 1–6 與 Dashboard 靜態 JSON 契約總表（Design Baseline Proposal v1.0）

> **閱讀順序**：本文件 → [Case Package](../../ui-ux/case-package/CASE-PACKAGE-SPEC-v1.md) → 對應 Phase 的 [JSON Schema 與 Sample](./README.md)。Phase 5 是**已設計核准的獨立 Baseline**，詳細欄位以 [Phase 5 Data Contract v1.2](../../ui-ux/case-package/phase-05/PHASE-05-DATA-CONTRACT-v1.md) 為準，本文件不得修改它。其餘 Phase 目前為 **PROPOSED FOR PRODUCER REVIEW**，不可因建立 Schema 就聲稱 Research/Bundle/Release QA PASS。
>
> **無即時計算 API**：Phase 1–5、Dashboard Verified 靜態讀取 Case Package JSON/圖資；Phase 6 的靜態 `inference-catalog.json` 只負責顯示模型狀態。真正單筆推論才會在後續授權下使用獨立的 Phase 6 API。Dashboard Custom 資料上傳／訓練不是這一份靜態契約的功能，沒有授權就只能顯示 DISABLED。

## 1. 「data」的嚴格定義

| 名稱 | 精確意義 | 位置、權威與禁忌 |
|---|---|---|
| **Case data** | 某 Case 的公開安全研究**衍生結果**，包含敘述、統計摘要、figure references、model metadata；**不是 Kaggle 原始 CSV** | `cases/<case_id>/case.json`、`phases/*`；獨立於私有 source |
| **Source data** | 原始資料、row-level OOF、Holdout row、fit artifacts | 僅私有研究區，不得因 JSON 引用而公開 |
| **Manifest** | 列出合法檔案位置/版本/依賴的索引；不是結果本身 | `package.json`，且所有路徑 Case-root-relative |
| **Schema** | 描述單一 JSON 欄位型態、必填、枚舉等的 JSON Schema 2020-12 | `docs/design/data-contracts/schemas/*.schema.json`；**不是 payload** |
| **Sample/fixture** | 為測試 UI 與結構製作的明確 MOCK/UNAVAILABLE JSON，非已核准研究證據 | 既有 `docs/ui-ux/case-package/sample/`；禁止標 VERIFIED |
| **Figure asset** | 經審查的靜態 SVG/PNG 或統計替代表，不能由瀏覽器反向算研究結果 | `phases/phase-*/figures/` 並在 `assets/figure-manifest.json` 與 `files[]` 完整引用 |
| **Ready prediction service** | 經後端五項 readiness gate 核准的模型服務 | Phase 6 專屬，不是 Case Package 自動賦予 |
| **status** | 資料證據狀態（UNAVAILABLE/PLANNED/MOCK/VERIFIED/ERROR） | 與 Review approval、model readiness、schema parse PASS 彼此獨立 |
| **release_id** | 一次完整公開快照的不可變發布身分 | 與 package_revision、execution_run_id、evaluation_id 不可混用 |

## 2. 唯一標準目錄與入口

```text
case-package/
  package.json                               # root: phases.phase1..phase6.data_ref
  case.json                                  # case_id, title, source, target: {raw_field_id,label,unit,value_type}
  phases/
    phase-01/content.json                   # 文字段落與可查證來源
    phase-02/analyses.json                  # EDA analysis list, figure/table refs
    phase-02/figures/*                      # optional approved reviewed charts
    phase-03/preparation.json               # 四階段 feature distribution、split、treatments
    phase-03/feature-lineage.json           # optional source-backed raw→encoded mapping
    phase-04/modeling.json                  # execution/configuration/fold/protocol/catalog
    phase-04/configurations/*               # optional immutable detail by configuration
    phase-04/charts/*                       # optional approved chart data
    phase-05/evaluations.json               # Phase 5 已核准契約（不要自行換欄位）
    phase-05/figures/*                      # optional approved P5 diagnostic assets
    phase-06/inference-catalog.json         # static public-safe registered-model summary
  assets/figure-manifest.json               # optional public figures; [] means no approved assets
```

**Dashboard 不塞進每個 Case 的 Phase 目錄**：Verified Dashboard 是使用以上 Case JSON 做摘要呈現的**另一條頁面 route**；它的 view manifest 為設計層 `dashboard.view.json`（不代表要存每個 Case，避免複製真實數字），定義卡片佈局與固定 read-only selector。Custom 模式只需前端 UI 狀態，不得把尚未上傳的 CSV/URL 當研究資料加入 Case Package。

所有 JSON UTF-8、不允許 NaN/Infinity、字串化數字、前端擅自補數值。Schema 驗證**只驗單檔**；cross-file ID/sha/rights/release 仍屬未授權的 Bundle Validator 工程。JSON file path 只用相對 Case-root 的斜線 `/`，拒絕 `../`、絕對路徑、外部 URL 及跨 release JOIN。

## 3. 每個 JSON 的欄位契約、UI 綁定與 EMPTY 決策

### Phase 1 — `phases/phase-01/content.json`

根必填：`schema_version`, `case_id`, `status`, `sections[]`。每段：`section_id`（唯一穩定 key）、`title`、`body`（已審查公開安全純文字）。展示順序等於陣列順序；只做文字卡，不從空文字推測科學結論。根 `MOCK` 時加 MOCK 水印；`sections:[]` 時顯示「尚無經核准研究敘事」。所有來源/目標以 `case.json` 為唯一權威；`content.json` 可為各段提供後續 `source_ref`，但這是**選用且必須審核**的擴充欄位。

### Phase 2 — `phases/phase-02/analyses.json`（EDA）

根必填：`schema_version,case_id,status,default_analysis_id,analyses[]`。每分析必填 `id,figure_id,title,status,image_ref,table_ref,description,finding,limitations,provenance_ref`；允許 asset/table/finding/provenance nullable。已知的 FIG-01（總覽）、FIG-02（缺失值）、FIG-03（目標分布）、FIG-06（相關分析）在 Ames Sample 只有**選單資訊**，目前 `UNAVAILABLE` 不等於圖資已核准，UI 選中呈現同尺寸 unavailable 佔位。若分析項目非空，`default_analysis_id` 必須指向清單中一筆；空清單時 null。單次只顯示一個圖框，圖與 finding/source/table 同步替換；沒有圖不可保留上一張。圖資 VERIFIED 必須透過後續 Bundle 檢查 ref+hash+rights+alt+table、不可將 sample 的 title 當作已發布的實證圖。

### Phase 3 — `phases/phase-03/preparation.json`（資料準備）

必填 `schema_version,case_id,status,feature_types[],stages[],treatments[],split,lineage_ref`。四種 classification：`nominal/ordinal/discrete/continuous`；`feature_types[]` 每項 `type_id,label`。四個**按順序** `stages[]`：`raw,filtered,processed,encoded`；每筆 `id,label,unit,total,total_status,segments[],distribution_status`；`total` nullable，`unit` 僅 `raw_columns/pre_encoding_columns/encoded_features`，不同單位不可做相同分母百分比。每 segment 有 `type_id,count`，當 distribution VERIFIED，所有 count 必須非負且和等於 total、type_id 只能引用 feature_types。型態分布未知就 `segments:[],distribution_status:UNAVAILABLE`，**不得假畫四條等比色塊**。`treatments[]` 是經 source 審核的缺失值處理/資料轉換紀錄（Sample 可為空）；不可臆測 imputation 或泄露 fold row index。`split` 是**row count**、非 feature count：`source_labeled_rows,training_rows,holdout_rows,seed,status`，Ames 歷史交接 1460/1168/292 在 Sample 的 `status=SOURCE_REPORTED_NOT_VERIFIED`，不自動升 VERIFIED。`lineage_ref` 指向選用 `feature-lineage.json`，**248 encoded 的 fit_population/pipeline_version/source SHA 未證實前只能作 reported/unavailable**，不能推算 Phase6 raw input。

### Phase 4 — `phases/phase-04/modeling.json`（建模）

必填 `schema_version,case_id,status,cv,methods[],execution_runs[],configurations[],default_configuration_id,charts[]`。`cv{training_rows,fold_count,protocol_id,status}`、`methods[]` 每項 `method_id,label,parameters[]`，參數每項 `parameter_id,label,data_type`。只有**實際存在的配置**才可出現在 `configurations[]`：`configuration_id,execution_run_id,method_id,track_id,params,protocol_id,status`，metadata/fold/metrics/selected-feature refs 選用且必須可解參照。`execution_runs[]` 是多個 config 所屬的一次實驗執行，不得混作 method tuple。可變 K 不能作固定 Top-K 軸：fixed method 的 `requested_k` vs alpha/l1_ratio variable-method X 分開；selected fold K 與 final-fit K 是不同來源。`charts[]` 僅同 protocol/track/population 可比較。`execution_runs:[],configurations:[],default_configuration_id:null` 合法，UI 應顯示「尚無可驗證配置」，不得自動製造 Pearson/Lasso 榜單。

### Phase 5 — `phases/phase-05/evaluations.json`（模型評估）

**以已核准的 [Phase 5 Data Contract](../../ui-ux/case-package/phase-05/PHASE-05-DATA-CONTRACT-v1.md)＋[2020-12 Schema](../../ui-ux/case-package/phase-05/evaluation-index.schema.json) 為唯一權威**，不由本文件改寫。使用 `evaluation_id`、`linked_evaluation_ids[]`、母體、metric_source、MAE/RMSE/R²、三核心診斷圖與 INT-F/INT-S。OOF 圖不得冒充 Holdout。已有 [empty Sample](../../ui-ux/case-package/phase-05/sample/evaluations.json) 與 [nonempty MOCK](../../ui-ux/case-package/phase-05/sample/evaluations.nonempty.mock.json)。

### Phase 6 — `phases/phase-06/inference-catalog.json`（靜態模型清單）

必填 `schema_version,case_id,status,models[],readiness`。`readiness{predict_enabled:boolean,reason_code,message}`；`models[]` 若有真實登錄，欄位 `model_id,model_version,source_execution_run_id,source_configuration_id,model_status,input_schema_ref,readiness`，reference 及五個 readiness gate 由後端核實；不同 config 可以 0、1、N 個模型，不能從 Phase4 configs 自動憑空造 model_id。`models:[]` 與 disabled Predict 是合格空態。**Phase 6 的即時單筆預測是未來獨立 API/Model Registry 授權工作，絕不能讓此 JSON 觸發自動模型訓練或載入本地 joblib。**

### Shared Dashboard — 無新 Case Phase JSON

Verified 模式唯讀已有 Case Package `case.json` / Phase2–5 結果，並遵守每項 scope/unit/evidence；不可在前端重新計算研究統計。Custom 模式只保存使用者暫時 UI 輸入（CSV/URL 二擇一、target/features 草稿、錯誤訊息），不寫入已核准 Case Package；第一階段 `Run` disabled。若 Dashboard 之後需要獨立 published aggregate JSON，必須另做版本化 contract/Schema 和 owner review，**現在不創造不存在的結果 JSON 或即時 API**。

## 4. 跨頁的絕對一致性與明日工程交接

1. **Namespace**：`case_id` 全部吻合；`execution_run_id` 是研究執行、`configuration_id` 是方法/參數組合、`evaluation_id` 是評估觀測，`model_id` 是經核准的部署模型。任何單一過時 `run_id` 不作權威。
2. **Status**：`MOCK` 可渲染測試但要顯示水印；`UNAVAILABLE` 不得產生實測圖；`SOURCE_REPORTED_NOT_VERIFIED` 是欄位級來源報稱、非根 `VERIFIED`；`release_id` 不等於 `package_revision`。
3. **Assets**：FIG/JSON SHA+case-root refs 和公開權利需要實體驗證；Sample `files:[]` 只能作 staging。
4. **No fabricated numbers**：各 Phase 的缺欄填 null＋reason/status；不把示意值/交接值當真值，不把原始 row/OOF/holdout 對外公開。
5. **Readiness vs design**：Schema PASS 是單檔結構 PASS，不是 source、Bundle、模型訓練、API、Release PASS。
6. **Version control**：非 Phase5 新 Schema 提案皆 v1.0，實際下游 Producer 應先做 Schema/fixture/cross-Phase handshake，發現真正相容性缺口由 Owner/PM 核准升版；不能靜默改名或換 enum。
7. **No fake API**：純靜態頁面只從 pinned release 資料包讀已發布資源，不新增任何 `POST /api/evaluate`／Phase2 EDA API／Phase3 preprocessing API／Phase4 train API。

## 5. 還需要盤點什麼？（分層處理，不阻擋契約設計）

**短期資料契約 P0**：所有 Phase 各自最低正例/空態範例、Schema structural runtime、UI component→JSON field mapping 逐頁檢查、上層 sample 的 `files:[]` 是 staging 不可發布、來源真正 key path/fit scope **UNKNOWN** 的對照清單。後續工程才做 full Bundle Validator/atomic publication。Phase5 本輪設計已正式結案，不重新擴大驗收。

**來源資料另 Gate**：Phase2 FIG-01/02/03/06 正式圖與 SHA；Phase3 清洗前後欄位/每型態分類/encoder lineage + fit population；Phase4 real eligible configs/3-fold task/final fit mapping；Phase5 paired OOF、INT-S 等 Owner 授權；Phase6 validated fitted preprocessing、model registry/schema + deployed inference。缺來源時不可把 schema 設計當 data verified。

**明天的 Producer 交付規則：** 不得由模型或 UI 自行解讀欄位；以所屬 Schema 當唯一單檔檢查入口，使用共用 `docs/design/tools/validate_schema.py --schema ... input.json`。錯誤欄位、未知 ID、未核准圖或來源，**停止該筆資料發布**，可顯示 UNAVAILABLE，不使整個前端失效。
