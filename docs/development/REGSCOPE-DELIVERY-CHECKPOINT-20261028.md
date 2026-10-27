# RegScope Production Delivery Checkpoint — 2026-10-28

## Live deployment

- Production site: https://regscope-aiot.vercel.app
- Vercel deployment: `regscope-1vyd1u1ki-wupojung-8919s-projects.vercel.app`, state `READY`.
- Production branch: `deploy`; current commit `b483ae28ab7ca96d92079aabea676f2865cbb0b4`.
- PR #45 integrated the Core/Web work to `main` at `b6675725b161d46409cedd222dbf67fcb8cbeb5d`.
- CI split PR #47 merged to `main` at `d3ad1a5986f27069450217c2e395bcc2fb3ba09f`.
- PR #46 deployed `main` to `deploy` at `b483ae28ab7ca96d92079aabea676f2865cbb0b4`.
- The required `scan` and Vercel checks passed before the deploy merge. No branch-protection bypass was used.

## Real-data run and package

- Run ID: `initb-development-e2e-20261028-02`.
- INIT B configuration: `ames-lasso100-primary-ols-3fold-v1`.
- Formal `train.csv` SHA-256: `1e18addf81e5e4d347cc17ee6075bbe4a42b7fa26b9e5b063e8f692a5f929d41`.
- INIT B config SHA-256: `a67b42afed991d7a69f5de7fdc56657ed9fce9495316bafe89deb2deee6be05f`.
- Public package: `web/data/releases/ames-initb-development-20261028-02/cases/ames-reference-init-a/`, selected by `web/data/current-release.json`. It contains 22 manifest-listed files. Row-level OOF CSV, model binary, and one-record prediction value remain private.
- Package status is `PARTIAL`: Phase 1 is `UNAVAILABLE` because approved business evidence is absent; Phase 5 publication review remains `PENDING` and is labeled on the website. Owner confirmed this pending review does not block displaying the validated Development evaluation.

## Phase results

- **Phase 1:** `UNAVAILABLE`; no business/source evidence was fabricated.
- **Phase 2:** actual EDA on 1,460 × 81 training data; missing count 6,965; `MasVnrType` missing count 8; literal `None` remains a valid category. Two aggregate SVGs are served.
- **Phase 3:** actual train-only preprocessing; seed 42, 80/20 split, 1,168 Development / 292 Validation, 248 encoded features. Validation was not used for tuning or model selection.
- **Phase 4:** fixed historical Development configuration, three-fold CV, Lasso alpha 100 selection followed by primary OLS. Mean-fold MAE `19395.048845362322`, RMSE `35389.184561872244`, R² `0.784159113347866`. OOF covers the 1,168 Development rows and is not public.
- **Phase 5:** recomputed from this run’s OOF. Pooled MAE `19394.931769794934`, RMSE `35936.820129461055`, R² `0.7825137235978141`. Residual diagnostics and three PNG charts are available with Development OOF and publication-pending labels.
- **Phase 6:** fixed Development model was saved, reloaded, and locally smoke-predicted. The public package exposes model/run/config identity and digest metadata only; it contains no model binary or prediction value. No inference API is available.

## Verification evidence

- Required GitHub `scan`: **PASS**. It ran the tracked security scan, environment smoke check, and project tests excluding only the legacy `tests/modeling/test_p4b_runner.py` file: 191 passed, 1 skipped, 122 subtests passed.
- CI-only PR #47 preserves old P4B tests in a separate Windows job. That job ran 39 tests and reported 9 failures from stale synthetic-runner API expectations and an existing injected-write assertion; its JUnit artifact was uploaded. The old test file and expectations were not removed or modified. These legacy failures are not the required `scan` context and did not bypass branch protection.
- Focused Core/E2E tests: 25 passed, 25 subtests passed. Web/Security-policy/EDA focused tests: 58 passed, 18 subtests passed. Tracked security scan, environment smoke, `pip check`, JavaScript syntax, and `git diff --check` passed.
- W5P2 independent local Chromium QA: 35/35 PASS; public package integrity/privacy: 12/12 PASS. Report and JSON remain in ignored local evidence.
- Production Playwright smoke on https://regscope-aiot.vercel.app: desktop case selection, Phase 1–6, Phase 2 SVGs, Phase 5 PNGs, displayed data checks, dashboard route, and mobile layout all passed. Console errors, HTTP errors, and failed requests: **0**. Browser JSON: `local/w5-browser-test/result-production-b483ae2.json`.
- The Vercel Preview was protected by login, so anonymous Preview assertions were not run. The Production site was tested directly after deployment.

## Reproduction and rollback

Call `housing_regression.reference_e2e.run_reference_e2e()` with the verified INIT B config, its source-bound reusable Phase 2/3 package, a new empty output directory, unique Run ID, and exact code HEAD. It verifies the formal CSV SHA and refuses overwrite. Keep private run artifacts outside `web/`; export only a new validated package with `housing_regression.public_case_package.export_public_reference_package()`.

Production was previously at `c29c0eb8a055dbf90ef6a4f66266d7f2ccc41971`. If rollback is needed, use Vercel’s prior READY deployment or revert the release through a normal PR to `deploy`; do not force-push or bypass checks.

## Remaining scope

The live site serves the fixed Lasso→OLS Reference Baseline. Additional Pearson, Mutual Information, ElasticNet, Ridge RFE, and standalone OLS Baseline tracks are not part of this run. Phase 6 remains local-only with no public serving API. Phase 1 and Phase 5 publication/research approval statuses remain as stated above.
