# Phase 5 — Evaluation / 模型評估

> **DRAFT DESIGN / NOT OWNER-APPROVED / NO EMPIRICAL RESULTS AUTHORIZED.** Based on [Issue #37](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/37). This file is the canonical Phase 5 **proposed** page, not a claim that the Phase 5 design/evidence gate has passed. No OOF/Holdout private access, calculation, fit, graph release or API work permitted. See [contract delta](../REGSCOPE-CONTRACT-REVIEW-DELTA.md) for `execution_run_id`, `configuration_id`, `evaluation_id` relationships.

## Purpose
Compare a **specific audited configuration** only within its specified evaluation population. Metrics MAE/RMSE/R² with units, scope, aggregation and publication QA. Three figure slots FIG-P5-01 Actual vs Predicted, FIG-P5-02 Residual vs Predicted (primary priority), FIG-P5-03 Residual Distribution; separate FIG-P5-04 interval feasibility **INT-F** from actual deliverable **INT-S**.

## Desktop ASCII Wireframe — proposal 1920×1080, scrolling

```text
+---------------------------------------------------------------------------------------------------------------+
| RegScope       Study Dataset: [Ames Housing v]             [Home / CRISP-DM] [Dashboard]                        |
| [01 Business] [02 Data] [03 Preparation] [04 Modeling] [05 Evaluation*] [06 Deployment] (ONE ROW)            |
+---------------------------------------------------------------------------------------------------------------+
| PHASE 05 — MODEL EVALUATION                                                                                   |
| 模型評估：本次模型在哪個資料母體上評估？結果與限制是什麼？                                                     |
|                                                                                                               |
| ① EVALUATION CONTEXT                                                                                         |
| +-----------------------------------------------------------------------------------------------------------+ |
| | Configuration: [actual approved configuration v or unavailable]  Execution: [execution_run_id]            | |
| | [Development OOF*] [Holdout aggregate only, if approved] [Training only if available]                     | |
| | Evaluation ID: [id / unavailable] | n: [source n] | Prediction origin: [fold models / final-fit]          | |
| | Method, track, protocol, model/version (when applicable), source evidence                                  | |
| +-----------------------------------------------------------------------------------------------------------+ |
|                                                                                                               |
| ② CORE METRICS — one evaluation + one metric source, no mixing                                               |
| +-------------------------------+ +-------------------------------+ +-----------------------------------+ |
| | MAE (lower better)            | | RMSE (lower better)           | | R² (higher better)                | |
| | [value USD / UNAVAILABLE]     | | [value USD / UNAVAILABLE]     | | [score / UNAVAILABLE]             | |
| | [n / aggregation / source]    | | [n / aggregation / source]    | | [dimensionless, not accuracy %]   | |
| +-------------------------------+ +-------------------------------+ +-----------------------------------+ |
| [Expand fold mean/sample SD vs pooled OOF details v]                                                          |
|                                                                                                               |
| ③ CORE DIAGNOSTICS — ONE FIGURE selected at a time                                                              |
| [FIG-P5-02 Residual vs Predicted *] [FIG-P5-01 Actual vs Predicted] [FIG-P5-03 Residual Distribution]          |
| +-----------------------------------------------------------------------------------------------------------+ |
| | Figure title / scope / n / unit / status / evidence link                                                    | |
| | [ONE approved figure, preserve axes and accessible statistical alternative table]                         | |
| | [If unavailable: SAME figure container reads "No approved figure / exact blocker"]                          | |
| | Finding / interpretation / limitations / provenance                                                        | |
| +-----------------------------------------------------------------------------------------------------------+ |
|                                                                                                               |
| ④ CONFIDENCE / PREDICTION INTERVAL                                                                            |
| +-----------------------------------------------------------------------------------------------------------+ |
| | FIG-P5-04  [INT-F: feasibility status] [INT-S: actual figure status]                                        | |
| | [Approved interval figure ONLY IF lawful method/evidence] else [UNAVAILABLE + next Gate]                     | |
| | Interval type, level, assumptions, model-selection caveat, source                                            | |
| +-----------------------------------------------------------------------------------------------------------+ |
|                                                                                                               |
| ⑤ INTERPRETATION & TRACEABILITY                                                                                |
| +-----------------------------------------------------------------------------------------------------------+ |
| | Training/CV vs Development OOF vs sealed Holdout distinctions; model limitations; cross-OS caveats         | |
| | [Expand methods, sources, status and review evidence v]                                                      | |
| +-----------------------------------------------------------------------------------------------------------+ |
| [< Back to Phase 4 with same configuration]                            [Phase 6: model readiness check >]      |
+---------------------------------------------------------------------------------------------------------------+
```

## Control rules
- **Global case** clears current configuration, population, evaluation, figures, metrics and stale requests.
- **Configuration select** lists only correctly mapped actual configurations; selection refreshes all Phase 5 panels atomically. No source mapping → disabled with reason.
- **Population tabs** are constrained to published evaluated populations, not cross-run comparisons. `development_oof` differs from `holdout`, `training_in_sample`. Holdout **aggregate** permits eligible metrics but NEVER implies point scatter without a separate Owner authorization.
- **Metric detail** accordion shows true fold-mean and sample SD if audited; pooled OOF separately named. Hide missing SD rather than zero.
- **Three figure selector** updates exactly ONE chart, its alt/table, caveats/source. FIG-P5-02 is default priority but unavailable state remains honest. Actual-vs-predicted X=actual, Y=predicted, y=x; Residual X=predicted, Y=actual−predicted, y=0; Residual histogram defined bins and n. No row-level restricted data in browser.
- **Interval** requires separate `INT-F` feasibility and `INT-S` actual appropriate CI/PI chart. UNAVAILABLE feasibility is not successful homework submission; don't fabricate RMSE-based bands.
- **Back Phase 4** carries case+execution+configuration; **Next Phase 6** carries the same context for *registry lookup*, not fabricated `model_id`.
- All states `LOADING/EMPTY/MOCK/UNAVAILABLE/ERROR/VERIFIED` are cell/figure-specific. Clear stale values on navigation. `VERIFIED` is evidence status, not inference readiness.

## Exact empty-state example (current safe default)
```text
PHASE 05 / MODEL EVALUATION
Selected configuration: [UNKNOWN — source mapping pending]
Population: [Development OOF]  Evaluation: [UNAVAILABLE]
[MAE --] [RMSE --] [R² --]
[FIG-P5-02 Residual vs Predicted: UNAVAILABLE — audited published asset not provided]
[FIG-P5-01] [FIG-P5-03]  (same evidence requirement)
[INT-F pending] [INT-S unavailable — homework interval requirement not satisfied]
[< Phase4] [Phase6 registry lookup >]
```

## Data contract / dynamic fields
`case_id,execution_run_id,configuration_id,evaluation_id,model_id|null,evaluation_population,prediction_origin,metric_source,n,target{column,unit},metrics{mae,rmse,r2},fold_summary{fold_values_ref,mean,sample_sd,aggregation},figures[{figure_id,asset_ref,status,axes,source_digest,alt,accessible_table_ref}],interval{int_f,int_s,method,type,nominal_level},publication_review,evidence_ref`. All exact metrics/images require verified source, population and rights; no values inferred from Issue handoff. [Issue #37](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/37) controls future scientific/governance changes, not this unapproved UI suggestion.

## Review checklist
- [ ] Owner/Nex decide layout and prioritize residual graph.
- [ ] Valid case/config/evaluation joins; CV fold-mean/pooled OOF/Holdout independently labeled.
- [ ] Actual published figure URL and per-figure provenance, alt and aggregation QA.
- [ ] Holdout row-level never accessed via Phase 5 UI contract.
- [ ] INT-F memo status separated from INT-S actual interval fulfillment.
- [ ] Unavailable state usable before any Phase 5 empirical publication.
- [ ] This draft stays docs-only and is NOT implicitly an Issue #37 execution gate.
