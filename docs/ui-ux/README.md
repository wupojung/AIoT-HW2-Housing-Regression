# RegScope — UI/UX specification entry point

The current source-backed UI baseline and terminology governance live in **[PR #63](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/63)** while that PR remains unmerged. After its authorized merge, follow:

- `REGSCOPE-PRODUCTION-UX-BASELINE.md` — source-backed navigation, per-phase presentation, UX state semantics, case transitions, responsive and accessibility notes.
- `REGSCOPE-SPEC-RECONCILIATION.md` — CURRENT/STALE/PROPOSED/UNKNOWN matrix and terminology audit.

**Do not treat missing documents on main as present.** PR #35 was **CLOSED/UNMERGED** and is only a historical reference. No Mock screenshots, proposed wireframes or experimental packages from that PR are production UI authority.

## Scope separation

- **UI/UX** owns the view: page structure, interaction, labels, accessible statuses and evidence disclosure.
- **Data contracts** own JSON Schema validation: [canonical Phase 1–6 schemas](../design/data-contracts/schemas/README.md). In particular, **Phase 5** moved from this directory to `docs/design/data-contracts/schemas/phase-05.schema.json`. Do **not** recreate a Phase 5 Schema under UI/UX.
- **CRISP-DM** owns methodology: [research documentation](../crisp-dm/README.md).
- **Case Package evidence** describes reviewed public artifacts; a UI badge cannot elevate a result's scientific status.

Naming decision: CRISP-DM Phase 6 remains **Deployment／部署**; the approved page-heading target is **模型預測與結果（Model Prediction & Results）**. This is a documentation naming decision, **not** proof that the deployed UI has changed or that a Prediction API exists.

Before publishing statements about live UI behavior, independently confirm Production branch/release and browser/HTTP evidence. Do not merge or deploy as part of a documentation move.
