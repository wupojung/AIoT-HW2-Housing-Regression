# Phase 3 — Data Preparation

**Current detailed spec, docs-only.** 248 dimensions fit-scope pending independent audit; UNKNOWN distribution must not be invented.

### D. Phase 3 — Data Preparation / 四張連續、同規格的特徵變化圖

**Owner's critical visual intent:** teach a **continuous feature-transformation journey**, not four unrelated widgets. **ALL FOUR stages have the SAME stacked horizontal quantitative visualization** with category ordering and colors held stable. Descriptions go BELOW the bar. Stage ③ additionally has an expandable methods accordion. Stage ④ must show that categories can change width/absolute count following One-Hot/other encoding; it MUST NOT mechanically reuse Stage ①'s percentages. Train–Test Split is an independent fifth **closing** bar below the four feature stages.

**Vocabulary hierarchy:** Categorical → Nominal (unordered), Ordinal (ordered). Numerical → Discrete (countable), Continuous (measured). These are **common examples, not a forced exhaustive schema**: each case can have 1, 2, 3, 4 or additional supported types, such as Other/Datetime/Text where actually present. Display only actual classified types. **Preferred visible order** for comparability: Nominal, Ordinal, Discrete, Continuous, then other explicitly documented types. This intentionally puts Categorical before Numerical so that Nominal → One-Hot contribution can be traced. Type classification must use the **dataset dictionary + approved preprocessing policy**, NOT automatically infer "any integer = discrete" or silently assign ambiguous numeric codes. An Ordinal source column may be processed differently by a particular pipeline; display *actual* transformation rather than pretending the category dictates it.

**Percent/count rules and critical denominator discipline**
- Each stage's bar is **100% stacked** over that stage's **own total columns/features**. Within a stage, segment width = that category's count / that stage total. Show count \`n\` and percent \`n/total × 100%\` together via segment label (if readable) and fixed legend immediately beneath. No denominator mixing or sum-by-rounded-percent bugs.
- Persistent same color assignment by **type id** in all four bars, and persistent order. Accessibility: labels text/legend, not color-only. If a 1–3% segment is too narrow for text, put the exact count/percent in the legend; do not hide the segment or pretend it is zero. Empty categories are omitted in the stage but legend can explicitly report zero when needed for stage comparison.
- **Counts matter at least as much as percentages**: show the stage's total prominently at upper right, plus per-type raw counts, and a change note relative to preceding stage. Percentages are relative and MUST NOT imply absolute growth by themselves. In stage ④, reclassification after encoding must be traceable to source type, even though actual encoded matrix entries are numeric: plot segments by **ORIGINAL source-feature type / transformation lineage**, otherwise all encoded columns would trivially appear Numerical and defeat the purpose.
- Stages ①–③ count **source/retained feature columns at their respective stage**, unless independently documented feature creation happens at stage ③; then show its actual unit and a recorded mapping. Stage ④ counts **encoded model-input dimensions**; labeling changes to \`encoded features\`, and the source→encoded mapping explains expanded counts. Never label all four as the same measurement without this unit change.
- If no original predictor is excluded, Stage ② repeats **exactly** Stage ①'s category counts and percent, explicitly "0 excluded"; do not fake a minor reduction. If Stage ③ only imputes/fills without adding/removing fields, it repeats Stage ②'s counts/percent with a note that values changed, **not** feature dimension.
- Unknown count is **UNKNOWN/待核對**, never 0. Don't calculate percent from missing counts. A segment distribution is not independently VERIFIED until per-type values and classification are audited. **Do not use sample 35/20/15/30% in a published Ames chart**: those were UI mock numbers, not empirical results.

**Actual Ames evidence available for design:** 79 source candidate predictors (not counting \`Id\` or \`SalePrice\`), **248 model-matrix encoded columns from Phase 3**, original Kaggle labeled train 1,460 rows. Number of original excluded columns and per-type counts are **UNKNOWN pending actual pipeline/dictionary audit**. **97 selected encoded columns** belongs to a specific Phase 4 selection fit and must NOT replace 248 in Phase 3. Phase 3 and Phase 4 selection metrics must not be conflated.

~~~text
+------------------------------------------------------------------------------------------------------------------+
| PHASE 03 / DATA PREPARATION                                                                                      |
| 資料準備：79 個原始候選欄位，如何變成模型使用的 248 個編碼後特徵？                                                |
| Note: numbers 79 and 248 are Ames documented totals; per-type values below are placeholders awaiting evidence.   |
|                                                                                                                  |
| ① ORIGINAL FEATURE DISTRIBUTION                         TOTAL: 79 raw candidate columns                          |
| +--------------------------------------------------------------------------------------------------------------+ |
| | +------------------- 100% stacked category bar ---------------------------------------------+                | |
| | | [Nominal share ?] [Ordinal share ?] [Discrete share ?] [Continuous share ?] [Other?]       |                | |
| | +-------------------------------------------------------------------------------------------+                | |
| | LEGEND  Nominal: ? cols / ?%   Ordinal: ? cols / ?%   Discrete: ? cols / ?%  Continuous: ? cols / ?%           | |
| | Original candidate predictors exclude target and identifier. Classification: PENDING AUDIT.                   | |
| +--------------------------------------------------------------------------------------------------------------+ |
|                                                  ↓                                                               |
| ② FILTERED FEATURE DISTRIBUTION                         TOTAL: UNKNOWN retained raw columns                      |
| +--------------------------------------------------------------------------------------------------------------+ |
| | +------------------- SAME 100% stacked category bar ----------------------------------------+                | |
| | | [Nominal share ?] [Ordinal share ?] [Discrete share ?] [Continuous share ?] [Other?]       |                | |
| | +-------------------------------------------------------------------------------------------+                | |
| | LEGEND  each retained type: ? cols / ?%       EXCLUDED: UNKNOWN  RETAINED: UNKNOWN                           | |
| | [Show excluded columns and reasons v]                                                                         | |
| | If zero exclusions, repeat Stage ① exactly and print EXCLUDED 0.                                              | |
| +--------------------------------------------------------------------------------------------------------------+ |
|                                                  ↓                                                               |
| ③ PROCESSED FEATURE DISTRIBUTION                        TOTAL: UNKNOWN columns after value processing           |
| +--------------------------------------------------------------------------------------------------------------+ |
| | +------------------- SAME 100% stacked category bar ----------------------------------------+                | |
| | | [Nominal share ?] [Ordinal share ?] [Discrete share ?] [Continuous share ?] [Other?]       |                | |
| | +-------------------------------------------------------------------------------------------+                | |
| | LEGEND  each processed type: ? cols / ?%    Show count delta and non-dimensional value treatments             | |
| | HOW THE DATA WERE PROCESSED (expandable accordion immediately below the bar)                                  | |
| | [Nominal  | processing methods | click to expand v]                                                           | |
| | [Ordinal  | processing methods | click to expand v]                                                           | |
| | [Discrete | processing methods | click to expand v]                                                           | |
| | [Continuous | processing methods | click to expand v]                                                         | |
| | [Other, only if present | click to expand v]                                                                  | |
| +--------------------------------------------------------------------------------------------------------------+ |
|                                                  ↓                                                               |
| ④ FINAL ENCODED FEATURE DISTRIBUTION                    TOTAL: 248 ENCODED FEATURES                              |
| +--------------------------------------------------------------------------------------------------------------+ |
| | +------------------- SAME 100% stacked category bar ----------------------------------------+                | |
| | | [Nominal EXPANDED WIDTH ?] [Ordinal ?] [Discrete ?] [Continuous ?] [Other?]                |                | |
| | +-------------------------------------------------------------------------------------------+                | |
| | LEGEND  each ORIGINAL TYPE's contributed encoded cols: ? / ?%      Σ = 248                                    | |
| | One-Hot Encoding: raw source columns → several encoded columns (actual mapping pending audit).                | |
| | [Expand raw-to-encoded feature mapping v]                                                                      | |
| +--------------------------------------------------------------------------------------------------------------+ |
|                                                                                                                  |
| DATASET PARTITION / TRAIN–TEST SPLIT (different unit: ROWS, not feature columns)                                 |
| +--------------------------------------------------------------------------------------------------------------+ |
| | [-------------------- 80% Development Set (Training) ---------------------][20% Holdout Test Set]              | |
| |     Development: 1,168 labeled rows                                      Holdout: 292 labeled rows            | |
| | Labeled Kaggle train: 1,460 rows; Random Seed: 42. Kaggle Competition Test: 1,459 unlabeled rows SEPARATE.    | |
| | 3-Fold Cross-Validation: explained in Phase 4, on Development ONLY; Holdout not part of CV.                   | |
| +--------------------------------------------------------------------------------------------------------------+ |
| [< Previous Phase: Data Understanding]                                                [Next Phase: Modeling >]   |
+------------------------------------------------------------------------------------------------------------------+
~~~

**A note on ASCII bar characters:** question-mark segment widths in the diagram are *unknown* rather than an actual 20/30% chart. Implementation must compute widths from approved JSON data, including unknown/loading/empty states. In contrast, the 80:20 ROW split has known verified counts and may be drawn proportionally. When a case has only one type, that type fills 100%; with two, three or four types the count and widths follow the manifest. The four chart sections should be stacked **vertically on a scrollable page**, with visible sequence connectors, not four separate phase navigation pages or a carousel.

#### Phase 3 interactive control catalog (each actual button and its result)
| Control | Location and label | Trigger | State transition and content | Guard/disabled handling |
|---|---|---|---|---|
| Global dataset picker | Shared header, \`Study dataset: [title v]\` | select case | changes all stages' dataset, resets open disclosures, data and labels | planned case disabled or truthful incomplete case |
| Phase 01–06 tabs | Shared row | click tab | navigates selected phase; persists case | no invented result for unsupported phase |
| Exclusions disclosure | Under Stage ② \`Show excluded columns and reasons v\` | click | toggles visible list of \`raw_column_name\`, \`type\`, \`exclusion_reason\`, \`stage\`, \`evidence_ref\`; no navigation | UNKNOWN count => message "Exclusion audit pending", not fabricated zero; zero verified => "No raw columns excluded" |
| Nominal accordion | Stage ③ \`Nominal v\` | click | toggles only Nominal's actual treatment list, affected fields, missingness policy, transformation status, evidence | no confirmed method => UNKNOWN, not default One-Hot |
| Ordinal accordion | Stage ③ \`Ordinal v\` | click | toggles only Ordinal's documented ordering, imputation, encoding/identity pass-through, exact fields and evidence | unsupported subtype omitted; never invent category order |
| Discrete accordion | Stage ③ \`Discrete v\` | click | toggles numeric discrete missingness, scaling/retention/transform actually applied and evidence | not every integer raw column is discrete |
| Continuous accordion | Stage ③ \`Continuous v\` | click | toggles numeric continuous imputation/transformation actually applied and evidence | do not claim scaling/log transformation without observed pipeline |
| Other accordion | Stage ③ \`[type] v\` | click | only for a present and documented case type, shows recorded treatment and evidence | absent type should not generate a dead control |
| Raw→Encoded mapping disclosure | Stage ④ \`Expand raw-to-encoded feature mapping v\` | click | toggles searchable/scrollable list of input raw field, source type, encoder/operation, generated encoded feature IDs/count, source revision | unavailable mapping => UNAVAILABLE reason, NOT invented per-type numbers |
| Previous Phase | Footer \`< Previous Phase\` | click | Phase 2, same case | Phase 1 only disabled/hidden globally |
| Next Phase | Footer \`Next Phase >\` | click | Phase 4, same case | Phase 6 only disabled/hidden globally |

**Accordion mechanics:** all Stage ③ type panels **default collapsed** and may be open simultaneously; clicking its header toggles only that panel, without modifying bars or collapsing other panels. Disclosure headers are keyboard accessible with focus/expanded state; no added accordions for non-existent types. Each body is explanatory prose, not a second unrelated chart. Show **APPLIED / NOT_APPLIED / NOT_APPLICABLE / UNKNOWN** for each *actual documented operation* where needed. Do not use a bulky separate generic "research integrity" panel (Owner explicitly rejected it).

**Pipeline placement and scientific accuracy:**
1. Stage ① identifies raw candidate **predictor columns**, excludes \`Id\` and \`SalePrice\` from that 79; original CSV's 81 columns include those two. Its percentage denominator = classified candidate predictor count.
2. Stage ② records explicit column exclusion policies and approved reasons. **Feature selection by model/CV is NOT Stage ②**; that is Phase 4. Report both excluded and retained counts; distinguish 0 vs pending audit.
3. Stage ③ explains structural absence, genuine missing imputation, extra missingness indicators, categorical/numeric transformations, and each applicable \`APPLIED\` state. Clarify that **imputation changes values, not automatically number of columns**; missing-indicator creation *can* increase dimension, and the step where new columns are created must be assigned to a unique transformation stage in the manifest.
4. Stage ④ is the **actual encoded model input matrix**, type lineage by source type. One-Hot may expand Nominal source columns into many indicators; other methods can preserve or add columns, too. The encoded contributions by source type **must sum to exactly 248 for this Ames run**; when mapping is incomplete, the aggregate verified 248 may display but category shares must be UNKNOWN, not a fake stacked bar.
5. Source type/encoder is **not one-to-one by definition**: One-Hot is commonly applied to Nominal, Ordinal Encoding to Ordinal, but only the **actual fitted pipeline** decides; never label all Ordinal values One-Hot or all Nominal values as one numeric output without evidence.
6. The Kaggle 1,459-row competition test is separate from the internally split 1,460 labeled rows; do not call it Holdout. The 292 **Holdout Test Set** is sealed relative to selection/tuning. Phase 4 conducts **3-Fold Cross-Validation inside the 1,168-row Development Set**; Phase 5 holds final independently approved Holdout evaluation.
7. Train-fitted preprocessing and CV fold safety must be explained accurately. A Phase 3 transformed feature dimension is not proof that encoders/imputers were fitted on the entire labeled dataset or before CV; distinguish reported artifacts from CV-fold fit procedure using versioned evidence. No leakage claims without checking their actual provenance.

**Recommended per-case Phase 3 JSON manifest** (schema design, not generated research; UNKNOWN fields represented as null/status, sample type entries omitted until audited):
~~~json
{
  "phase3": {
    "distribution_units": {
      "raw": "raw_columns",
      "filtered": "raw_columns",
      "processed": "pre_encoding_columns",
      "encoded": "encoded_features"
    },
    "stages": [
      {
        "id": "raw",
        "title": "原始特徵型態分布",
        "total": 79,
        "status": "VERIFIED",
        "types": [],
        "evidence_ref": "SOURCE_AUDIT_REFERENCE"
      },
      {
        "id": "filtered",
        "title": "篩選後特徵型態分布",
        "total": null,
        "status": "UNAVAILABLE",
        "types": [],
        "excluded_columns": [],
        "excluded_count": null,
        "evidence_ref": null
      },
      {
        "id": "processed",
        "title": "資料處理後的特徵分布",
        "total": null,
        "status": "UNAVAILABLE",
        "types": [],
        "evidence_ref": null
      },
      {
        "id": "encoded",
        "title": "最終編碼特徵分布",
        "total": 248,
        "status": "VERIFIED",
        "types": [],
        "feature_mapping_ref": null,
        "evidence_ref": "PHASE3_QUALITY_REPORT_REFERENCE"
      }
    ],
    "processing_details": [],
    "split": {
      "source_labeled_rows": 1460,
      "development_rows": 1168,
      "holdout_rows": 292,
      "development_ratio": 0.8,
      "holdout_ratio": 0.2,
      "random_seed": 42,
      "competition_test_rows": 1459
    }
  }
}
~~~
**Contract invariants for future generation:** \`types[]\` is a dynamic array of \`{type_id, label, count, proportion, evidence_ref}\` (plus stable \`color_key\` or centrally mapped color). If \`status=VERIFIED\` for **distribution completeness**, counts are nonnegative integers and sum to \`total\`, and proportions derive from counts (do not trust independently supplied rounded text); the Stage ④ lineage contributions sum to encoded total; raw + excluded/retained reconciliation must hold for verified filtering. An aggregate known total **may coexist with unavailable subtype distribution** (don't use the stage-level VERIFIED flag to imply all its child bars are verified). Therefore the application should model **separate \`total_status\` and \`distribution_status\`** in the final production contract, or supply equivalent per-field provenance. In the illustrative JSON above, an empty \`types\` list with a verified total means **distribution unavailable**, not "zero types". No actual per-type counts are recorded in this document. Stage ③ \`processing_details[]\` entries require type/operation ID, status, fields, handling rules, stage, evidence and optional change in dimension; a categorical label is **not** sufficient evidence of a performed transform. The backend ETL/preprocessing audit will populate this later, after authorization.