# RegScope — Canonical Reconstruction Entry v1.0

**2026-10-26 | P6-A DOCS ONLY | PR #35 | No engineering/merge/deploy authorization.**

## Mandatory reading order (single entrypoint)

1. **THIS FILE** — page registry, canonical navigation, fixed states and conflict precedence.
2. [REGSCOPE-UX-SPEC.md](./REGSCOPE-UX-SPEC.md) — visual wireframes and control behavior. In that file the detailed Phase 1–3 supplement, Phase 4 detailed section and Phase 4↔6 supplement override abbreviated historical diagrams. Historic sketches are **SUPERSEDED / REFERENCE ONLY**. It is NOT correct to take the first occurrence of a phase as final.
3. [REGSCOPE-DATA-API-CONTRACT.md](./REGSCOPE-DATA-API-CONTRACT.md) — file inventory, data/visual/API contracts; for PM review corrections read [REGSCOPE-CONTRACT-REVIEW-DELTA.md](./REGSCOPE-CONTRACT-REVIEW-DELTA.md) FIRST. Where old examples disagree, DELTA wins.

Source reviews: [PM data review](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35#issuecomment-6420057913), [Independent cold-start reconstruction](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35#issuecomment-6420115156). **The earlier phase4 UI-facing `run_id` as one parameter tuple is superseded: canonical selection is `configuration_id`, upstream research `run_id` is `execution_run_id`.**

## Page registry — canonical routes are proposed, NOT existing router implementation

| page_id / proposed path | authoritative UX section | initial / no-data state | data needed | implementation status |
|---|---|---|---|---|
| home / `/` | detailed shared-shell section Phase 1–3 supplement | **Home loads Phase 1 directly**, not an extra marketing page | case index, Phase1 metadata | UX APPROVED DIRECTION; precise CSS TBD |
| phase1 / `/?phase=1` | supplement §B | read-only case text; UNAVAILABLE per missing item | case + phase1 | STRUCTURE DESIGNED |
| phase2 / `/?phase=2` | supplement §C plus earlier reviewed four-figure evidence | first eligible published analysis; else EMPTY | analyses[] + image URLs | STRUCTURE DESIGNED; full four-item export NOT READY |
| phase3 / `/?phase=3` | supplement §D | four vertically successive bars; if shares unknown show **blank labeled unavailable distribution track**, retain known audited total; bottom 80/20 | typed stages + lineage + split | STRUCTURE DESIGNED; shares NEED AUDIT |
| phase4 / `/?phase=4` | detailed Phase4 + Phase4↔6 supplement, **read DELTA identity fix** | fold bars and method explorer; no eligible configurations => disabled method/parameter controls + UNAVAILABLE result | execution/config/task catalog | STRUCTURE DESIGNED; source mappings NEED AUDIT |
| phase5 / `/?phase=5` | **NOT DESIGNED**; Issue [#37](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/37) governs future design | display **「模型評估頁面仍在設計／證據審核中」**; selected config shown as text; no metrics invented; link Phase4 | future approved evaluation manifest | **BLOCKED for faithful reconstruction** |
| phase6 / `/?phase=6` | Phase4↔6 supplement section Phase6 | no ready model => NOT READY notice + reason and return-to-Phase4 | configuration→registered model; bound input schema | STRUCTURE DESIGNED; LIVE PREDICTION BLOCKED |
| dashboard / `/dashboard` | dashboard BLOCKER 2 prior draft + dashboard state rules below | choose Verified Research / Custom Dataset; both **mutually exclusive** | approved static aggregates or CSV/URL validator | **PARTIAL DESIGN, NOT faithful reconstruction ready** |

**Route paths are proposed conventions**, not implementation verification. Navigation carries `case_id` and where available `execution_run_id+configuration_id` in router state/query; do not use a fabricated execution `run_id` for method combo. History back restores previously selected valid config; case switch clears incompatible selections and stale results.

## Canonical shell / 1920×1080 desktop (vertical scrolling allowed)

~~~text
+------------------------------------------------------------------------------------------------------+
| RegScope                                                     [Home/CRISP-DM]  [Dashboard]           |
| Study Dataset: [Ames Housing v]                                                                     |
| [01 Business] [02 Data] [03 Preparation] [04 Modeling] [05 Evaluation] [06 Deployment]  (ONE ROW)   |
+------------------------------------------------------------------------------------------------------+
| [PHASE HEADER + CASE-BOUND PRIMARY CONTENT]                                                        |
| [PHASE CONTENT vertically scrolling, no guessed charts]                                            |
| [< Previous Phase]                                                           [Next Phase >]         |
+------------------------------------------------------------------------------------------------------+
| Sources / evidence status / attribution  (when relevant)                                           |
+------------------------------------------------------------------------------------------------------+
~~~

Desktop single row means six steps never wrapped on two lines. Home starts Phase 1; Dashboard is an independent route. Prior project docs include historical alternate Home cards: **SUPERSEDED** when inconsistent. Exact max-width in px, heights, typography scale, logo spacing, color tokens, breakpoints: **DESIGN TBD, not an arbitrary acceptance gate**.

## Explicit no-data display fixtures (non-empirical, safe for cold-start reconstruction)

### Phase 2 — Four approved figure choices versus unavailable asset
~~~text
[Dataset Overview*] [Missingness] [SalePrice Distribution] [Numeric Correlations]
+----------------------------------------------+
| Selected: Dataset Overview   [VERIFIED if URL+rights passed]|
| [ONE approved image + accessible text/table] |
| Description / Finding / Limitation           |
+----------------------------------------------+
IF IMAGE MISSING: same space becomes [UNAVAILABLE: reviewed asset URL missing] [source]; no dummy chart.
~~~
The four labels correspond to previously reviewed FIG-01/02/03/06; published manifest still requires URLs/digest/alt/tables per record. Never publish four-item fabricated data just to populate controls.

### Phase 3 — absent category counts, real aggregate totals
~~~text
01 RAW  [Total reported 79]    [Distribution UNAVAILABLE — per-type counts not audited]
02 FILTERED [Total UNKNOWN]     [Distribution UNAVAILABLE] [Excluded fields audit pending v]
03 PROCESSED [Total UNKNOWN]    [Distribution UNAVAILABLE] [Treatment method accordions v]
04 ENCODED [Reported 248, fit-scope pending] [Distribution UNAVAILABLE] [Feature mapping v]
SPLIT [Training Set 80%, 1,168] [Holdout Test Set 20%, 292]   Seed=42
~~~
UNAVAILABLE means **do not draw a fake 100%-stacked equal-width bar**. Replace its horizontal chart track with neutral unavailable text in same container, preserving identical stage order, legend position and inter-stage arrows. When audited, replace track with category segments from JSON only.

### Phase 4 — no eligible configurations
~~~text
3-FOLD CV [3 three-segment training/validation bars] [Training Set 1168]
[Method Comparison*] [Selected Features] [Feature Count vs CV]
Method [none available — disabled]   Parameters [none — disabled]
+-------------------------------------------------+
| UNAVAILABLE — No approved configuration records |
| Review run/config/task evidence before results |
+-------------------------------------------------+
[View Evaluation — unavailable] [Use Model — unavailable]
~~~
When actual configs exist: Method Comparison uses **horizontal bar plot sorted ascending by compatible CV RMSE** (labels: configuration/method, x: CV RMSE in target unit; source and protocol), with accessible numbers table. Selected Features uses **scrollable table** columns: rank, encoded feature name, raw source field, measure/coef if available; pagination/detail mechanics TBD and should not invent rankings. Feature Count vs CV is **measured point plot**, x specified `requested_k` for fixed-K only; variable-K regularized models use separate alpha/l1_ratio view, NEVER observed/final K silently mixed. Any incompatible run or empty perspective displays UNAVAILABLE in same result region, not fake points.

### Phase 5 — cannot be reconstructed yet
~~~text
PHASE 05 / EVALUATION — DESIGN / EVIDENCE PENDING
Selected case: [case_id]; selected configuration: [configuration_id or none]
[UNAVAILABLE: Phase 5 visual design and evidence gate pending Issue #37]
[< Back to Phase 4]   [Proceed to Phase 6 (subject to model readiness)]
~~~
This is **a fallback status screen, NOT the approved Phase 5 final UI**. Never show Holdout RMSE/MAE/R², OOF figures or CI/PI as verified just because example values exist.

### Phase 6 — five canonical user-visible states
~~~text
NOT READY: [此模型尚未準備好] [reason: artifact/load/schema/registry/API gate] [Choose eligible model] [Return to Phase 4]
READY:     [MODEL verified selector] [Raw input form from model-specific schema] [Validate] [Predict]
INVALID:   [Same form with field-level error] [Predict disabled] [Correct inputs]
LOADING:   [Inputs snapshot] [Predict loading/disabled] [Result --] (ignore stale replies)
SUCCESS:   [Predicted target + unit] [model/version/request provenance] [new input invalidates old output]
API ERROR: [Result --] [safe reason and retry] [Return to Phase 4]
~~~
These are layout states, not claims of actual deployed models. The only supported current default is NOT READY until the five independent readiness gates pass.

### Dashboard — mutually exclusive, **provisional** layout states
~~~text
DASHBOARD / mode [Verified Research*] [Custom Dataset]
VERIFIED mode ONLY: [Case picker] [Approved run/config selector] [Dataset overview card]
                    [Feature selection result card] [Metrics evidence card]
                    [Prediction visual/interval only if verified] [Source/limitations]
                    Empty: [No approved aggregate data for selected case/config]
CUSTOM mode ONLY:   [CSV upload] OR [HTTP(S) URL input]
                    [Parse/Preview status with filename, rows, column names]
                    [Target single select] [Feature multi-select] [Validate]
                    [Run disabled — separate engineering/Owner gate]
                    [Field errors / unsupported size/URL/CORS explanation]
~~~
Opening mode = Verified Research by default. Switching modes clears prior source, selection, validation, metrics and stale results. Verified mode NEVER imports ad-hoc CSV. Custom mode NEVER promotes exploratory output to a reviewed run. **Precise card placement, dataset preview table row count, multi-select UX and source URL handling remain TBD** and the Dashboard is **not reconstruction PASS**.

## Next acceptance gate for a cold-start AI

A new agent must be able to state (a) each page's fixed panel order, (b) control effect/reset, (c) missing-data screen, (d) exactly which JSON supplies data, (e) what is unapproved. Stop rather than invent Phase 5 or functional Dashboard behavior. Do not infer that a static illustration with MOCK numeric values is evidence.

**No page other than actually reviewed evidence is empirically certified by these text fixtures.**