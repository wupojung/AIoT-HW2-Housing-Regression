# RegScope｜JSON Schemas 與 Sample 對照（設計交接入口）

**狀態：Phase 5 Data Contract v1.2 已設計核准；Phase 4 Data Contract v1.1 已加入配置 refs 與 samples；Phase 1/2/3 有結構契約與 MOCK/空態 samples；Phase 6 仍為 v1.0 提案。** 不因擁有 Schema 或 source-reported aggregate 而推定研究結果已驗證。

## 工作順序

1. [閱讀 Phase 1–6 JSON Contract](./PHASE-1-6-JSON-CONTRACT-v1.md)；先認識 Case root、ID、status、圖、來源與母體。
2. [Case Package Spec v1](../../ui-ux/case-package/CASE-PACKAGE-SPEC-v1.md)：整包如何封裝、編排 `package.json`、哪些資源是 public-safe。
3. 各 Phase 必須依下表**唯一 Schema** 產生資料，不要從 UI/UX 歷史文字猜欄位。
4. 共用 `docs/design/tools/validate_schema.py` 檢驗每份單檔，另由之後的 Bundle Validator 驗跨檔 ID/SHA/權限/Release。

| 畫面 | 必備 JSON（Case root relative） | Schema | 最低 Sample | 現有缺口 |
|---|---|---|---|---|
| Phase 1 Business Understanding | `phases/phase-01/content.json` | [01](./schemas/phase-01.schema.json) | [01](../../ui-ux/case-package/sample/ames-housing/phases/phase-01/content.json) | 已核准真實敘事／來源 |
| Phase 2 Data Understanding / EDA | `phases/phase-02/analyses.json` | [02](./schemas/phase-02.schema.json) | [02](../../ui-ux/case-package/sample/ames-housing/phases/phase-02/analyses.json) | 四幅核准圖的 public SHA/alt/table |
| Phase 3 Data Preparation | `phases/phase-03/preparation.json` | [03](./schemas/phase-03.schema.json) | [03](../../ui-ux/case-package/sample/ames-housing/phases/phase-03/preparation.json) | 細分段數／fit scope/feature lineage |
| Phase 4 Modeling | `phases/phase-04/modeling.json` | [04](./schemas/phase-04.schema.json) | [04](../../ui-ux/case-package/sample/ames-housing/phases/phase-04/modeling.json) | source-reported; config detail refs are optional in schema v1.1 |
| Phase 5 Evaluation | `phases/phase-05/evaluations.json` | [05](../../ui-ux/case-package/phase-05/evaluation-index.schema.json) | [05](../../ui-ux/case-package/phase-05/sample/evaluations.json) | **契約設計已核准**；實證/Bundle 待後續 Gate |
| Phase 6 Deployment/Prediction | `phases/phase-06/inference-catalog.json` | [06](./schemas/phase-06.schema.json) | [06](../../ui-ux/case-package/sample/ames-housing/phases/phase-06/inference-catalog.json) | valid registered model；預測 API 另案 |
| Dashboard Verified | **無額外新 JSON**；只讀選定 Case 上述已審核資料 | 不適用 | 不適用 | Dashboard 視覺版型／欄位綁定仍待獨立 Review |
| Dashboard Custom | **無研究 JSON**（未授權 Run/上傳） | 不適用 | 不適用 | 後續獨立授權，不能默認 API |

Phase-specific package guidance and validation matrices: [Phase 1](../../ui-ux/case-package/phase-01/), [Phase 2](../../ui-ux/case-package/phase-02/), [Phase 3](../../ui-ux/case-package/phase-03/), and [Phase 4](../../ui-ux/case-package/phase-04/). The canonical schemas remain in this shared schema directory; do not duplicate them in phase folders.

## 地端／CI 共用命令

```bash
python -m pip install "jsonschema[format]==4.26.0"
python docs/design/tools/validate_schema.py --schema docs/design/data-contracts/schemas/phase-03.schema.json docs/ui-ux/case-package/sample/ames-housing/phases/phase-03/preparation.json
```

Phase 1/2/4/6 只換 `--schema` 和資料路徑。完整的 Phase 5 MOCK 正反例仍用它原本的 `test_schema.py`。所有示例都是 staging-only；完整 `files[]` 雜湊不等於發布核准，`files:[]` 則表示未封包。

## 重要界線

- **Schema structural validation** 只確認單一 JSON 型別/欄位；不保證其他檔案的外鍵、重複 ID、`segments` counts sum、已驗證的 asset、圖的 SHA 或資料權限。
- **Phase 5 不回頭重做**：其 Data Contract／Schema 是已完成設計 Gate 的基準；上表以它為準。
- **版本變更**：修訂 Schema 不得靜默改 field，需同一 PR 更新 Sample、導覽索引、驗證腳本或 CI 與版本紀錄，避免明天 Producer 和 UI 使用兩種格式。
