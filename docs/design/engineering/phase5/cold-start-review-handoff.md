# Phase 5 cold-start implementation handoff — review response

> **PROPOSED / DOCS ONLY / NOT IMPLEMENTED.** Applies to PR #38 review of 2026-10-27. No real dataset, Phase 4 private artifact, Holdout, model fit, release or deployment is authorized. Authority order: Issue #37 body + acceptance checklist → PR #35 Phase 5 v1.2 pinned at `8d2bc4405e08e1a1b982204984f681d90975956a` → existing Phase 4 protocol → this implementation handoff. This document cannot change the canonical schema.

## A. Golden fixture specification (synthetic-only)

**Canonical wire truth:** the complete PR #35 pinned [nonempty sample](https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/8d2bc4405e08e1a1b982204984f681d90975956a/docs/ui-ux/case-package/phase-05/sample/evaluations.nonempty.mock.json) is the baseline fixture for schema structure; copy that entire JSON when implementing `tests/phase5/fixtures/golden/expected-evaluations.json`, NOT the excerpts in this document. Check it against the pinned [evaluation-index.schema.json](https://github.com/wupojung/AIoT-HW2-Housing-Regression/blob/8d2bc4405e08e1a1b982204984f681d90975956a/docs/ui-ux/case-package/phase-05/evaluation-index.schema.json), using Draft 2020-12. This existing, complete sample has two mutually linked, distinct records: `synthetic-foldmean-01` / `cv_fold_mean`, and `synthetic-oof-01` / `pooled_oof`; `case_id=synthetic-evaluation-demo`, `status=MOCK`, `schema_version=1.0.0`, no empirical metrics, figures UNAVAILABLE and publication PENDING. Its 30 synthetic units are **placeholder metadata**, not a dataset or permission to generate numerical results.

The **first implementation golden test** is *copy-and-validate*, not a claimed executable exporter test: input = the pinned sample, expected byte-independent JSON object = that same pinned sample, output = `phases/phase-05/evaluations.json`, exit = 0 **for schema-validation-only**; compare parsed JSON, not formatting, assert exactly two evaluation IDs, reciprocal links, allowed metrics `mae/rmse/r2`, `fold_summary` on fold mean only, and three explicitly UNAVAILABLE figure slots on pooled OOF. No producer QA PASS, public rights or real evidence follows from this check. A `validate` CLI's manifest-based arguments in the main blueprint are proposed independently; do not treat the canonical output file as a Phase 4 input manifest.

**Separate deterministic numeric fixture** (future files `input-pairs.json` and `expected-metrics.json`; neither exists yet) contains three paired synthetic rows: `actual=[100,150,200]`, `predicted=[110,130,210]`, `target=SyntheticTarget`, `unit=synthetic_units`, `population=development_oof`, `prediction_origin=synthetic_fold_specific_models`, `configuration_id=synthetic-config-01`. Expected residuals = `[-10,20,-10]`; pooled MAE = `13.333333333333334`, RMSE = `sqrt(200)`, R² = `0.88` under the explicitly defined equations. This is a metrics-unit-test fixture, **not** enough fold membership to claim a `cv_fold_mean` record. For fold mean, use a *different* approved synthetic fixture with three independently specified nonconstant folds; verify each fold score and `ddof=1` sample SD. Never copy the pooled score into fold mean. If an exporter test is built, it must create a *separate full schema-valid expected output* using the pinned sample structure, with a reviewed exact mapping and without falsely presenting numeric test values as scientific evidence.

**Figure oracle** (numeric synthetic fixture only, no actual asset shipped): FIG-P5-01 x=`actual`, y=`predicted`, `y_equals_x`; FIG-P5-02 x=`predicted`, y=`actual_minus_predicted`, `y_equals_0`, includes both signs; FIG-P5-03 histogram of these three residuals, `x_equals_0`, explicitly fixed bin edges and n=3. Assertions inspect plotting data/metadata *before rendering*. In the complete schema-valid baseline all three figures remain UNAVAILABLE with null `asset_ref`/hash; no imaginary SVG, table, or released path. INT-F and INT-S are UNAVAILABLE, not PASS.

| Negative case | Setup | Expected operation-level outcome | Write boundary |
|---|---|---|---|
| Missing manifest required by proposed `preflight` | CLI arg absent | nonzero, `INVALID_INPUT`; exact integer exit code remains to be fixed in implementation spec | no package/index |
| Unauthorized real-data path | synthetic gate referencing a path outside isolated fixture root | nonzero `PATH_BLOCKED` or `NOT_AUTHORIZED`; exact integer exit code TBD | no read, no output promotion |
| Synthetic gate presented for real source | source digest/path does not match fixture allowlist | nonzero `NOT_AUTHORIZED`/`HASH_MISMATCH` | no real source read |
| Broken reciprocal evaluation link | mutate a copy of the full pinned sample | schema may pass; bundle/identity JOIN must fail nonzero `JOIN_BLOCKED` | no VERIFIED/promotion |
| Missing eligible evaluations with **valid authorized gate** | explicit empty permitted input | exit 0; validate PR #35 pinned complete *empty* sample shape, `UNAVAILABLE` | authorized private staging only |
| Unexpected missing real source | source listed in real gate is absent | nonzero `INVALID_INPUT`/stop; no auto-discovery | safe checkpoint only if allowlisted |

**Reproduction sequence for the future code PR:** (1) pin PR #35 HEAD/schema/sample hashes and interpreter in test report; (2) install only under separately approved synthetic-only code gate; (3) compare the full canonical pinned sample and empty sample to the pinned schema; (4) run numeric/oracle unit tests; (5) run negative isolation tests; (6) run end-to-end synthetic exporter test against a *new independently reviewed full golden output*, including manifest, gate, output, exact exit codes; (7) record executable command, stdout/stderr summary, hashes, platform, PASS/FAIL. All commands/test modules are **PROPOSED / NOT IMPLEMENTED**. **STOP:** do not claim an exporter end-to-end golden PASS from the existing sample alone. Numeric exit codes and full numeric exporter golden cannot be certified until the command contract and input adapter are implemented/reviewed.

## B. Small, verifiable engineering units

Each unit is a separate checkpoint; no unit may modify Phase 4 or PR #35. Dependencies below are hard blockers, not permission grants.

| Unit | Dependencies / gate | Input → owned output | STOP/failure | Minimum review evidence |
|---|---|---|---|---|
| E01 CLI/package entry | Owner synthetic-code gate | explicit argv, interpreter → registered `--help` and preflight/validate/export subcommands | missing package metadata, unpinned interpreter → STOP | clean checkout invocation + exact argv/exit |
| E02 synthetic manifest adapter | E01; synthetic-only | explicit fixture `--manifest` → typed normalized source identities | missing case/config/run/population/target or ambiguous join → `JOIN_BLOCKED` | mapping test + source fixture digest |
| E03 mode/gate/preflight | E01; synthetic gate for fixture only | explicit `--gate`, paths, mode → allow/deny decision | bad host/HEAD/path/SHA, mode escalation → DENY before source content read | deny-first tests; no reads/writes on disallowed path |
| E04 metrics/aggregation | E02,E03 | authorized aligned synthetic pairs/folds → MAE,RMSE,R² / fold mean + sample SD | nonfinite/missing fold; incompatible target/population → STOP or documented UNAVAILABLE | known-value tests, `ddof=1`, constant target |
| E05 figures | E02,E03,E04 | authorized synthetic pairs → figure data and accessibility metadata | absent rights/source, mixed origins → UNAVAILABLE (not fake PNG) | sign/reference lines/units + per-evaluation identity |
| E06 schema-valid exporter | E02–E05 | normalized mock records → full canonical `evaluations.json` in private staging | missing required field, unknown extra metric → `SCHEMA_FAIL` | validate full pinned schema and canonical complete golden |
| E07 staging/resume | E03,E06 | output + SHA + checkpoint → isolated atomic candidate | digest/gate/host/HEAD mismatch → STOP; never overwrite source | interruption, idempotence, symlink escape tests |
| E08 integration/review handoff | E01–E07 | complete synthetic-only fixture + audit log → reviewable checkpoint | producer self-PASS or pretend release → STOP | independent reviewer matrix, cross-OS bounded smoke |

**Track two separate lanes:** E01–E08 synthetic-only tooling may be requested under a future *code-only authorization*. **Real-data connector** (R01), Phase 4 source mapping/metadata audit (P5-A), real OOF figures/metrics (P5-B), actual interval evidence (INT-S), and public release (Phase 6) are distinct later gates. Synthetic unit PASS does not unblock real row reads. Each implementation ticket must contain explicit changed-file allowlist, authorized tests, environment, STOP rules and reviewer.

## C. Two non-interchangeable execution modes

| Property | `synthetic_fixture` development | `authorized_research` |
|---|---|---|
| Source | only checked-in, deliberately fake fixture under explicitly selected test fixture root | only Owner-authorized exact research artifacts |
| Gate record | scoped, explicitly labeled MOCK; literal allowlist of fixture IDs, paths, digests, operations | real gate with owner decision, host identity, OS/environment, repo HEAD, source SHA and exact paths |
| Host | Linux/macOS/Windows may differ; path containment and deny-first semantics must match | exact allowed host/machine and environment; no fallback |
| Outputs | isolated temp/staging root, permanently `MOCK`, never published/VERIFIED | permission-limited private staging; independent QA required |
| Forbidden | reading or scanning `local/`, Holdout, private data; carrying mock tokens into research run | bypassing preflight; dynamic scope widening, fitting/calibration without authorization |
| Negative test | pass a real-data path or expired/mismatched fixture hash: DENY **before read** | wrong host/HEAD/source SHA: DENY **before read** |

The mode must be an explicit proposed CLI argument or gate-record field, **with agreement required**; no implicit fallback from real to mock or vice versa. An environment variable by itself cannot elevate permission. Reject symlink escape, `..`, absolute/private references and case-root escape after canonicalization. Mock gate **cannot** authorize actual research data. Cross-OS smoke runs small fixtures only; it checks the same authorization semantics, path/UTF-8 behavior, canonical JSON and local mock static-URL resolution. It does not exercise Vercel or Phase 6 release verification.

## D. Real Phase 4 adapter dependency and blocker matrix

No row below asserts an existing formal Phase 4 JSON schema. A local path mention is *not* permission to read it. R = REQUIRED for the actual exported result; O = OPTIONAL; D = DERIVED only with authorized verified input; U = UNKNOWN until evidence/owner decision.

| Data/identity | Class | Owner / source to verify | Missing → action | Unlock condition |
|---|---|---|---|---|
| Case ID, target column and target unit/scale | R/U | Case Package owner + Phase 4 protocol/manifest | `JOIN_BLOCKED`; don't default to Ames USD blindly | accepted Case identity and target-scale mapping |
| `execution_run_id` | R/U | Phase 4 run-manifest owner | block; old `run_id` is not automatically equivalent | explicit audited 1:1 or 1:many mapping |
| `configuration_id`, model version, final fit ID | R/O/U depending on canonical nullability | Phase 4 config registry, selection record | block required identities; null optional slots with reason | evidence-linked mappings, no guessed config |
| `evaluation_id` | D | Phase 5 stable deterministic ID policy + reviewed Phase 4 identity | block collision/ambiguous join | documented construction and uniqueness test |
| Evaluation population, split, prediction origin | R/U | Phase 4 split manifest + OOF provenance | block mixed training/OOF/Holdout | population and split evidence, row membership verified under proper gate |
| Fold count, membership, per-fold metric values | R for `cv_fold_mean`, U | Phase 4 protocol, fold-level aggregate artifacts | no fold-mean metrics / UNAVAILABLE; never infer from pooled | approved source, fold denominator/count, `ddof=1` review |
| OOF aligned truth/prediction rows | R for new pooled/figure compute, U | Phase 4 row artifact owner | `UNAVAILABLE`; no implicit row read | P5-A PASS + exact P5-B row-data Owner gate |
| Metric source (`cv_fold_mean` vs `pooled_oof`) | R/D | Phase 4 aggregation provenance | `JOIN_BLOCKED` if mislabeled | evidence of computing method and distinct evaluation IDs |
| Source SHA-256 and artifact reference | R/U for evidence-backed publication | authorized artifact metadata owner | no VERIFIED/public status | independently checked digest and allowable sanitized reference |
| Fold protocol/version/platform/HEAD | R for provenance, U | Phase 4 protocol + run record | review blocked if uncertain | immutable reference/commit and verified metadata |
| Figure rights / accessibility asset references | O until approved, U | Owner/publication reviewer | figure UNAVAILABLE/PENDING, not fake | legitimate figure bytes, alt/table, rights and SHA |
| Holdout aggregate history | O/U, restricted | historical approved aggregated report | omit/UNAVAILABLE; no row retrieval | independent authorization specifically allowing quotation |
| CI/PI calibration and coverage | O/U pending INT-S | statistics reviewer and Owner | INT-F memo only; HW2 full-ready NO | separate method/data/compute approval |

**Review checkpoint template:** for each row save requirement status (`VERIFIED/DERIVABLE/NEEDS_AUTH/UNAVAILABLE/PROHIBITED`), concrete source locator or safe opaque ID, immutable digest if accessible, owner, permission ID, reviewer, verified date, precise missing field, STOP reason and requested decision. Never substitute `UNKNOWN` with a guessed Phase 4 filename/schema. P5-A permits *metadata inventory only after its own Owner gate*; P5-B permits real row data only after P5-A independent PASS and its own row gate.

## E. Cold-start review and acceptance trace

1. **Issue #37 checklist coverage:** map K06 checks to E01/E03 (clean checkout), E02/E06 (complete schema + two links), E04 (metrics/sign), E05 (zero line), E07/E08 (cross-OS/static references). G09 R01–R07 are the existing independent P5-A review handoff; they are not completed by this document.
2. **Empty workspace walkthrough:** reviewer starts at README → Issue #37 → pinned PR #35 schema/samples → this handoff → selects synthetic lane → makes E01 → E08 implementation tickets; stop at any unknown real source or missing Owner gate.
3. **Reverse contradiction test:** reject `evaluations.v1.json` and schema v1.1.0; reject MAPE/MedAE as canonical metrics; reject same ID for fold mean and pooled OOF; reject mock-as-VERIFIED, fake publication/release, fold SD from pooled data, synthetic gate on private source, leaked symlink, and producer self-approval.
4. **Evidence labels:** Documentation complete = design-only; synthetic schema test PASS = structure only; exporter integration PASS = synthetic functional proof only; independent P5-A PASS = metadata audit only; P5-B QA = authorized scientific evidence only; Phase 6 publication PASS = separate release review.

**Unresolved after this docs-only revision:** (i) real Phase 4 field/artifact mapping, (ii) reviewed full numerical exporter golden fixture and executable exit-code integers, (iii) Owner authorization of code/test scope, (iv) approved real row-source gate, (v) P5-A actual audit and independent QA, (vi) statistical interval evidence, and (vii) Phase 6 publication. None is silently promoted to PASS.
