# RegScope W5 Overnight Checkpoint — 2026-10-28

## Current state

- Worktree: `AIoT-HW2-Housing-Regression-regscope-core-e2e`, branch `feat/regscope-core-e2e-v1`.
- PR: [#45](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/45), Draft. The earlier three local commits were pushed after Owner clarified that isolated Vercel Preview is acceptable. Vercel reported `target=preview`; no production alias was created. Verify the remote PR head after this checkpoint commit is pushed.
- No merge, production deploy, schema change, Holdout access, or history rewrite.
- INIT A remains intact. INIT B is a separate reference-baseline configuration.

## Backup

- Verified local backup: `local/worktree-archive/overnight-20261028-01/`.
- The selected local INIT B config/package/reconciliation/audit evidence and prior E2E evidence were copied without changing originals; raw CSV and model binaries were excluded.
- Per-file SHA-256 and byte counts are in `backup-manifest.json`; Git bundle `regscope-core.bundle` verified with `git bundle verify` (SHA-256 `b8b3458ed1ba7138b6860335ac2b030015cfc165d4ea9aada058e32c1567c50d`).

## INIT B and historical reconciliation

- Source package: ignored local R3 output `local/reference-baseline-20261028/runs/ames-reference-package-r3/`; package status `PARTIAL`.
- Phase 2: formal train.csv aggregates and two SVGs retained. Prior reconciliation restores missing count 6,965 and MasVnrType missing 8 while preserving literal `None` category. Open differences remain: LotShape/LandSlope Phase 2 vs Phase 3 taxonomy, historical BsmtFinSF1 correlation rounding/evidence, and PNG acceptance (R3 contains SVG only).
- Phase 3: new INIT B transform reproduced historical Development split/matrix; 1,168 training rows, 292 validation rows, 248 features. No 292-row partition was used in this overnight task.
- Phase 4: fixed Lasso alpha 100 selection → primary OLS, three folds, seed 42; search disabled. Fold mean RMSE 35,389.184562, MAE 19,395.048845, R² 0.78415911, matching the prior reconciliation within its recorded numerical tolerance. Historical runner status contradiction remains unresolved.
- P2 read-only audit: `local/phase4-reconciliation-20261028/W5-OVERNIGHT-AUDIT.md`. It confirms the audited historical run has three completed fold aggregates but `predictions_included=false`, no package-bound OOF file, and Phase 5 UNAVAILABLE. Therefore no OOF metric recomputation or new Phase 5 evaluation was performed.
- Phase 6 remains UNAVAILABLE in the Case Package. Prior INIT B evidence records only a one-row in-memory engineering inference smoke; no persisted/approved serving model or deployment exists.

## Web integration

- Added loopback-only INIT B package selection in `web/app.js`. It loads the ignored R3 package, checks package identity, safe relative references, phase document SHA/byte counts, Phase 4 CV metrics SHA/byte count, and SVG SHA/byte counts before rendering.
- Browser smoke exercised the visible case selector and Phases 1–6. Phase 2 loaded both manifest-bound SVGs (natural width 760); Phase 3 displayed 79 input columns, 248 encoded features, split 1,168/292 and seed 42; Phase 4 displayed bound fold metrics; Phase 1/5/6 displayed UNAVAILABLE. Browser console errors and failed requests: zero.
- Browser evidence and runner are ignored under `local/w5-browser-test/`; browser binary is ignored under `local/w5-browser-browsers/`. No private package was copied into `web/`.
- This is a loopback consumer smoke, not a public release test or production-site integration.

## Gates and remaining work

| Gate | Result | Evidence / limitation |
|---|---|---|
| Backup integrity | PASS | Per-file manifest and Git bundle verification |
| Safe PR sync | PASS for prior HEAD | Remote PR #45 matched `7726be05d26670db597a28176ca1cf3444ad7a60`; Vercel target was Preview. This checkpoint commit still requires sync/remote recheck. |
| Package/schema/bundle | PASS (prior R3) | Existing local R3 validator report; no schema modified |
| Local Web browser smoke | PASS | `local/w5-browser-test/result.json`; Chromium, no console/page/request errors |
| Phase 5 Development evaluation | NOT RUN / BLOCKED | No OOF rows/artifact are package-bound; fold aggregates alone cannot create pooled OOF metrics |
| Phase 6 model-serving | NOT RUN | No approved persisted inference model/catalog; no API or deployment |
| Production deployment | NOT RUN | Not authorized |

To repeat the browser check from the worktree root: start `python3 -m http.server 8765 --bind 127.0.0.1`, then run `PLAYWRIGHT_BROWSERS_PATH=local/w5-browser-browsers node local/w5-browser-test/smoke.cjs`. The script verifies browser-visible values and SVG rendering; local package data remains ignored.

## Safety note

The root checkout's pre-existing untracked `.DS_Store` files and all other worktrees were left untouched. Do not remove worktrees or ignored evidence without a separate explicit cleanup authorization.
