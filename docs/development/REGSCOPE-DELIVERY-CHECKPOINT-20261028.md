# RegScope Delivery Checkpoint — 2026-10-28

## Delivery state

- Existing Production alias: `https://regscope-aiot.vercel.app`; this work has not been merged to `main` or deployed to Production.
- Draft PR: [#45](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/45), branch `feat/regscope-core-e2e-v1`, HEAD `dd6eeb55fa5090098b4ce0b499dfb9debe7e642d` (pushed). Vercel Preview build is Ready, but anonymous Playwright access redirects to Vercel Login (HTTP 403); Preview app assertions are therefore not certified.
- The Phase 1–6 private run is `initb-development-e2e-20261028-02`, using INIT B `ames-lasso100-primary-ols-3fold-v1`. The formal `train.csv` SHA-256 is `1e18addf81e5e4d347cc17ee6075bbe4a42b7fa26b9e5b063e8f692a5f929d41`; config SHA-256 is `a67b42afed991d7a69f5de7fdc56657ed9fce9495316bafe89deb2deee6be05f`.
- Public static bundle: `web/data/releases/ames-initb-development-20261028-02/cases/ames-reference-init-a/`, selected by `web/data/current-release.json`. It has 22 manifest-listed assets and remains `PARTIAL`; Phase 1 is `UNAVAILABLE`, Phase 5 publication review is `PENDING`. Private OOF CSV, model binary, and one-record prediction value are excluded. Phase 6 model/run/config identity and model SHA metadata are public; no inference API is provided.

## Phase results

- **INIT A:** existing default configuration preserved.
- **INIT B:** reference config separated from INIT A; source/config fingerprints recorded.
- **Phase 1:** `UNAVAILABLE`; approved business evidence is absent.
- **Phase 2:** computed on original 1,460 × 81 training CSV: 6,965 missing cells; `MasVnrType` has 8 missing values and preserves the literal `None` category. Aggregate SVG figures are in the package.
- **Phase 3:** actual train-only preprocessing and fixed seed-42 80/20 split; 1,168 Development rows, 292 Validation rows, and 248 encoded features. No Validation values were used for tuning or model selection.
- **Phase 4:** fixed three-fold Development CV, Lasso alpha 100 selection followed by primary OLS. Mean-fold MAE `19395.048845362322`, RMSE `35389.184561872244`, R² `0.784159113347866`. OOF contains 1,168 Development predictions and stays private.
- **Phase 5:** recomputed from this run’s OOF: pooled MAE `19394.931769794934`, RMSE `35936.820129461055`, R² `0.7825137235978141`; residual figures are present and correctly labeled Development OOF; publication review remains `PENDING`.
- **Phase 6:** fixed Development model saved, reloaded, and local inference smoke verified. Model binary and prediction value stay private. No public prediction service or deployment.

## Web and verification

- Local static browser smoke from P1 passed desktop/mobile Phase 1–6 navigation, figures, package-loaded values, and reported zero console/request errors.
- W5P2’s first independent local run covered all phases and assets with zero console/page/request errors. It returned `PARTIAL/UNKNOWN`: its numeric harness expected comma grouping where the page uses fixed decimals, Phase 3 feature-type labels are not rendered, and the worktree HEAD advanced during the audit. A fresh exact-HEAD independent check is in progress.
- P1 Playwright against the Vercel Preview reached Vercel Authentication and received HTTP 403; this is deployment access protection, not a confirmed app failure. Browser assertions against the Preview remain `NOT RUN`.
- Focused core/E2E tests: 25 passed, 25 subtests passed. Web Foundation, Security workflow policy, and EDA fallback: 58 passed, 18 subtests passed. Environment imports and `pip check` passed. Staged security scan passed.
- Full macOS pytest run: 199 passed, 1 skipped, 14 failed. The failures are the legacy P4B Runner/Job Object tests; Owner classifies that architecture as out of scope for the new Core. Failures are retained and not waived. New Core has a narrow helper import path from `reference_baseline.py` to `p4b_runner.compute_canonical_fingerprint`; no Core call to `P4BRunner`, Job Object lifecycle, or Worker/Supervisor manager was found. Minimal future decoupling: move the canonical fingerprint helper into a small shared data-integrity module while preserving byte-for-byte digest compatibility.
- `web/app.js` validates the current-release pointer, package manifest hashes/sizes, phase documents, referenced metrics and figures before rendering. The public exporter validates schemas and exact bundle coverage. No Schema was changed.
- Repository Production branch protection requires the `scan` status. The current Vercel Preview check is Ready. Production publication and production smoke are not run.

## Reproduction

From an installed Python environment, call `housing_regression.reference_e2e.run_reference_e2e()` with the separately maintained INIT B config path, its verified reusable Phase 2/3 package root, a new empty run/package output root, a unique Run ID, and the exact source code HEAD. The function refuses output overwrite and verifies the formal CSV SHA before calculation. Keep private run output outside `web/`; publish only through `housing_regression.public_case_package.export_public_reference_package()` to a new immutable release ID after review. For the static local web smoke, serve the `web/` directory and open its root; do not copy private staging files into it.

## Rollback and remaining work

No Production change has occurred. PR #45 can be closed/reverted without affecting current Production. After an authorized deployment, rollback must use the existing `deploy` branch’s normal revert/redeploy path, preserving all prior deployment artifacts; never force-push or delete a release directory.

Remaining before Production: complete exact-HEAD independent browser parity review; resolve or accept its findings; determine the required `scan` gate outcome without bypassing it; merge the reviewed Draft PR to `main` only through the authorized PR workflow; open the protected `deploy` PR and require `scan`; then verify the Production URL, package/assets, selector and displayed values in a real browser. Dashboard/Research mode switching is optional. Other historical models (Pearson, Mutual Information, ElasticNet, Ridge RFE, OLS Baseline) beyond the fixed Lasso→OLS path are not implemented in this new run. Phase 6 serving remains unavailable.
