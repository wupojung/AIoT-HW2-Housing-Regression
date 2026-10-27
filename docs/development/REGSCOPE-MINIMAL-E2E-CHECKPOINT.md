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
