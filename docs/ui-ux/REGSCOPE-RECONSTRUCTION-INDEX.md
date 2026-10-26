# RegScope — Canonical Reconstruction Entry v1.1

**Active directory entry. Draft P6-A docs only; not a frontend or empirical QA PASS.** All page designs live in `pages/`, no current UI spec depends on archived paragraphs.

## Read only these current resources

| Screen | Current page file | Status |
|---|---|---|
| Shared shell / Home | [pages/SHARED-SHELL.md](./pages/SHARED-SHELL.md) | DETAILED |
| Phase 1 | [pages/PHASE-01.md](./pages/PHASE-01.md) | DETAILED |
| Phase 2 | [pages/PHASE-02.md](./pages/PHASE-02.md) | DETAILED; assets not certified |
| Phase 3 | [pages/PHASE-03.md](./pages/PHASE-03.md) | DETAILED; category data pending |
| Phase 4 | [pages/PHASE-04.md](./pages/PHASE-04.md) | DETAILED; source IDs pending |
| Phase 5 | [pages/PHASE-05.md](./pages/PHASE-05.md) | **NEW PROPOSAL / REVIEW REQUIRED** |
| Phase 6 | [pages/PHASE-06.md](./pages/PHASE-06.md) | DETAILED; inference unavailable |
| Dashboard | [pages/DASHBOARD.md](./pages/DASHBOARD.md) | **PARTIAL**, further desktop design needed |

**Data identity and live API:** [REGSCOPE-CONTRACT-REVIEW-DELTA.md](./REGSCOPE-CONTRACT-REVIEW-DELTA.md) is authoritative for `execution_run_id`, `configuration_id`, `task_id`, `evaluation_id`, `model_id`, fold K semantics, status and endpoint names. [REGSCOPE-DATA-API-CONTRACT.md](./REGSCOPE-DATA-API-CONTRACT.md) contains the broader proposed asset inventory. Historic UX material is isolated under [archive](./archive/REGSCOPE-UX-SPEC-HISTORY-20261026.md); **DO NOT implement archived code or stale `run_id` assumptions**.

## Canonical initial state
```text
Route / → Phase 1 under default eligible case (Ames only if published case index approves).
One shared case selector → six Phase tabs (desktop: ONE ROW).
Dashboard is independent /dashboard mode.
Changing case clears configuration, metrics, evaluation, model and stale prediction.
Case-specific missing phases render UNAVAILABLE, not previous case's research.
```
Paths are proposed, not verified frontend routes. Nav to Phase 4 carries `case_id`; selecting a measured configuration resolves `configuration_id` within `execution_run_id`. Phase 5 and Phase 6 may receive these IDs; Phase 6 still requires a separate approved model registry entry before Predict is enabled.

## No-data page states (deterministic sketches)
```text
PHASE 2: [Four audited analyses only when actual public refs exist] → unavailable selected image stays in same area
PHASE 3: [raw 79 reported; distribution pending] ↓ [filtered unknown] ↓ [processed unknown] ↓
         [encoded 248 reported, fit-scope pending] ↓ [80% Training:1168][20% Holdout:292]
PHASE 4: [3 training/validation fold bars] [No eligible configurations → selector disabled] [CV result unavailable]
PHASE 5: [evaluation population & identity] [MAE --][RMSE --][R² --]
         [Residual graph unavailable] [Interval INT-F/INT-S unavailable]; see proposal
PHASE 6: [No approved model] [NOT READY, reason] [Choose another eligible model] [Return Phase 4]
DASHBOARD: Verified Research / Custom Dataset are MUTUALLY EXCLUSIVE; Custom Run disabled absent authorization.
```

For the exact response to all 15 second-round review findings, see [REGSCOPE-R2-REVIEW-TRACKER.md](./REGSCOPE-R2-REVIEW-TRACKER.md). This matrix identifies both amended artifacts and still-blocking evidence; it is not a PASS certificate.

## Cold-start independent review gates
- **Structural and navigation parity:** original Phase 1–4 and Phase 6 detailed sections retained as separate pages; no silent research claims.
- **Not yet achieved:** proposed design tokens and 1920×1080 images, fully developed Dashboard modes, syntactically valid JSON Schema and usable MOCK fixture loader, exact source-to-export key mapping, fully decided Phase 5 UX, independent blind screenshot/interaction QA.
- **R2 status:** [Independent Round 2 Review](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35#issuecomment-6420552696) remains PARTIAL. Page-file extraction resolves historical text volume, **not** R2-02 through R2-15 by itself.
- **No authorization** for reading restricted data, fitting/evaluation scripts, CLI, API, code build, merging or deploying.
