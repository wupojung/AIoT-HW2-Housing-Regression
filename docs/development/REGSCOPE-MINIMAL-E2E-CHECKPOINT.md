# RegScope Core Minimal E2E Checkpoint

Date: 2026-10-28
Scope: fixed synthetic CSV through INIT, Phase 1–6 package generation, pinned schema and bundle validation, and loopback static HTTP smoke. No real research data or Holdout partition was used.

## Phase implementation status

| Stage | Implemented and exercised | State and limits |
|---|---|---|
| INIT | Creates and reloads validated YAML configuration; records source/config fingerprints and refuses unsafe edits or overwrites. | Existing Core exercised with the fixed fixture. INIT B / reference baseline remains a recorded future requirement only. |
| Phase 1 | Reads explicit synthetic business/source/rights evidence and emits schema-valid `content.json`; existing Core also supports honest UNAVAILABLE output. | **PARTIAL**: no real business or rights evidence was supplied. E2E content is labelled MOCK. |
| Phase 2 | Parses and profiles the fixture, applies fixed field decisions, emits aggregate `analyses.json` and two accessible SVGs. | **PARTIAL**: mock-labelled synthetic scope only. Prior formal reconciliation still has unresolved taxonomy, correlation, and PNG acceptance items; no research specification was changed here. |
| Phase 3 | Applies configured Phase 2 feature decisions, median/mode imputation, one-hot encoding, and emits typed preparation stages and treatment records. | **PARTIAL**: fixed synthetic fixture only; no train/validation split or general Ames pipeline was run. |
| Phase 4 | Fits a small Ridge model in memory from the encoded synthetic fixture and emits a MOCK run/configuration record. | **PARTIAL**: software path only; no real-data training, CV, research protocol, or model artifact. |
| Phase 5 | Computes synthetic in-sample MAE/RMSE/R² as an engineering exercise and emits the pinned evaluation-index shape with MOCK provenance. | **PARTIAL**: these values are not scientific evaluation or research results; no real evaluation, OOF, Holdout, intervals, or publication review. |
| Phase 6 | Exercises one in-memory prediction call; emits an UNAVAILABLE inference catalog with no model and prediction disabled. | **PARTIAL**: no deployable model, serving process, or real deployment. |

No Phase 1–6 document is presented as VERIFIED. There is no phase that is only a copied sample JSON: the synthetic CSV is parsed, transformed, fitted, and used for an in-memory prediction. Phase 6's package artifact remains honestly unavailable for deployment.

No phase is only an Adapter/Schema Exporter in this run: Phases 3–5 perform synthetic transformations/model/metric calculations, and Phase 6 exercises an in-memory prediction. The Phase 6 catalog itself is an honest schema-valid UNAVAILABLE export because there is no approved deployable model.

## Gates

- **Package E2E: PASS** — fixed fixture → INIT → Phase 1–6 execution/output → Case Package → all pinned Phase schemas, case IDs, file SHA/byte/MIME entries, figure refs, and exact bundle coverage validated.
- **Core implementation: PARTIAL** — see phase table; broad/research capabilities remain incomplete.
- **Real-data scientific reproduction: NOT RUN** — no formal training data, Phase 4 research training, Phase 5 scientific evaluation, or Holdout was accessed.
- **Local Web Smoke: PASS (loopback HTTP scope)** — HTTP 200 for the static app files, generated package JSON, six phase documents, figure manifest, and both SVGs from a server bound only to `127.0.0.1`. Browser rendering/interaction and loading this generated package through the Web application's case selector were **NOT RUN**; the current Web prototype uses its own fixed UI cases.

Focused verification on macOS: INIT, Phase 1–2, and E2E unittest suites, 17 tests passed. Pinned schema files were byte-for-byte compared with PR #35's pinned source commit. Synthetic-only execution record and generated package are retained under ignored `local/e2e-synthetic-20261028-r1/`.

## Research and scope limitations carried forward

- **FAIL → FIX → PARTIAL history:** formal reconciliation first failed because the CSV reader treated the legal category string `None` as missing; the Core now treats only empty cells and exact `NA` as missing, with regression coverage. The corrected missingness result was reconciled, while field taxonomy, correlation, and PNG acceptance remain **PARTIAL / unresolved** and were not changed to make this package pass.
- INIT A is unchanged. INIT B (Reference Baseline), based on accepted Phase 2/3 research definitions and Phase 4 protocol, is recorded as a future requirement and was not implemented.
- No real Phase 4 training, Phase 5 scientific evaluation, Phase 6 deployment, push/merge/deploy, or PR #35 schema modification was performed.

## Owner-authorized INIT B follow-up — 2026-10-28

This section supersedes the earlier “INIT B remains unimplemented / real-data scientific reproduction NOT RUN” status above. The earlier statement remains an accurate record of the synthetic E2E checkpoint at that time.

- **INIT A remains unchanged.** A separate `reference-config.yaml` implements INIT B Reference Baseline. It binds the authorized `train.csv` SHA-256, historical Run ID and historical Manifest/Public Summary/Final Model Metadata SHA-256 values. The validated INIT B config fingerprint is recorded in the ignored local run report.
- **Phase 1: UNAVAILABLE.** No complete, authoritative business question/source/rights sections were available to populate the Phase 1 contract without inventing research claims.
- **Phase 2: PARTIAL.** Formal Development profiling executed on the fixed train source. Existing formal reconciliation evidence confirms 1,460×81, 6,965 missing cells, `MasVnrType` missing 8 with literal `None` preserved, target bins, and missingness chart values. Remaining items: `LotShape`/`LandSlope` taxonomy conflict, historical `BsmtFinSF1` correlation discrepancy, and missing PNG assets. SVG assets are not counted as PNG acceptance.
- **Phase 3: COMPLETE for the fixed Reference Baseline path.** The new train-only pipeline produced 1,168×248 Development features and a 292-row transform-only validation partition. Source, Development data, train-index and fold digests match the named historical evidence; feature names and transformed matrices compare exactly with the legacy implementation used as a read-only reference.
- **Phase 4: PARTIAL.** The fixed Lasso α=100 → primary OLS computation ran over the three authorized Development folds with candidate search disabled. Per-fold selected feature counts and CV metrics match the historical public summary within absolute tolerances of 1e-5 SalePrice units for RMSE/MAE and 1e-9 for R². A final Development-only fit selected 97 features, matching historical metadata. No model file was saved.
- **Phase 5: NOT IMPLEMENTED.** No new scientific evaluation ran. Existing historical aggregate validation metrics were read for reference only; no validation rows or predictions were recomputed.
- **Phase 6: PARTIAL.** One in-memory training-population prediction smoke was finite; its value was discarded, no metrics were calculated, no model was persisted, and deployment remains unavailable.
- **Real-data Case Package: PARTIAL / bundle validation PASS.** The local package includes actual Phase 2/3/4 outputs and honest Phase 1/5/6 unavailable states. All six pinned phase schemas and bundle references/file hashes validate. It has two SVG charts and zero PNGs; it is not a publication release.
- **Local Web Smoke: PASS at loopback HTTP level only.** `/web/`, its JavaScript, and the package manifest return HTTP 200. Browser rendering and the UI case selector loading this new package were not tested; the prototype still uses fixed UI cases.
- **Historical auditor participation:** W5:P2 completed the read-only audit; its report, including the FAILED-run versus successful aggregate/finalization evidence conflict, is retained in ignored local evidence. No history was rewritten or reconciled by assumption.
- **INIT B Reference reproduction report and run outputs:** ignored under `local/reference-baseline-20261028/`. From this Worktree root, use `REGSCOPE_RUN_SUFFIX=r4 PYTHONPATH=python/src local/.venv/bin/python local/reference-baseline-20261028/run_real_e2e.py`; choose a new suffix for each run because existing evidence is never overwritten. Linux and Windows remain NOT TESTED.

No PR #35 schema, original dataset, historical run artifact, Phase 5 result, or deployable model was modified or published. The overall Real-data gate remains **PARTIAL** pending unresolved Phase 2 definitions/assets and Phase 5/6 work.
