# RegScope — Current UI/UX Specification Index v1.0

> **CURRENT NORMATIVE ENTRY (2026-10-26), docs-only Draft PR #35.** The old cumulative spec is archived. No engineering, data access, merge or deploy authorized.

## Required reading sequence

1. [REGSCOPE-RECONSTRUCTION-INDEX.md](./REGSCOPE-RECONSTRUCTION-INDEX.md) — current page registry, statuses and reconstruction guidance.
2. [pages/SHARED-SHELL.md](./pages/SHARED-SHELL.md) — shared shell / Home.
3. Read **only the applicable page** from the directory below.
4. [REGSCOPE-CONTRACT-REVIEW-DELTA.md](./REGSCOPE-CONTRACT-REVIEW-DELTA.md) — canonical identities, K distinction, API naming and release approval. Old identity/API examples extracted verbatim into page specs are **REFERENCE ONLY where inconsistent**.
5. [REGSCOPE-DATA-API-CONTRACT.md](./REGSCOPE-DATA-API-CONTRACT.md) — complete research artifact/export inventory and proposed contracts; the reviewed delta controls discrepancies.

## One page, one file

| Page | Current spec | Status |
|---|---|---|
| Shared Shell / Home | [pages/SHARED-SHELL.md](./pages/SHARED-SHELL.md) | DETAILED DRAFT |
| Phase 1 | [pages/PHASE-01.md](./pages/PHASE-01.md) | DETAILED DRAFT |
| Phase 2 | [pages/PHASE-02.md](./pages/PHASE-02.md) | DETAILED DRAFT; assets need audit |
| Phase 3 | [pages/PHASE-03.md](./pages/PHASE-03.md) | DETAILED DRAFT; type lineage incomplete |
| Phase 4 | [pages/PHASE-04.md](./pages/PHASE-04.md) | DETAILED DRAFT; real config IDs pending audit |
| Phase 5 | [pages/PHASE-05.md](./pages/PHASE-05.md) | **NEW PROPOSAL, NOT APPROVED**; Issue #37 controls |
| Phase 6 | [pages/PHASE-06.md](./pages/PHASE-06.md) | DETAILED DRAFT; live inference not ready |
| Dashboard | [pages/DASHBOARD.md](./pages/DASHBOARD.md) | **PARTIAL DESIGN**, requires full mode-specific UX |

## Historical vs normative boundary

Prior composite content is preserved verbatim in [archive/REGSCOPE-UX-SPEC-HISTORY-20261026.md](./archive/REGSCOPE-UX-SPEC-HISTORY-20261026.md): **ARCHIVE / NOT A SOURCE FOR IMPLEMENTATION**. Each extracted page is current for its own visual structure, but its verbatim historical `run_id` per parameter-combination, K-axis, and old API snippets are **superseded** by the canonical data contract. See [PR #35 independent R2 review](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/35#issuecomment-6420552696) for the still-open issues.

## Scope and blockers

**Completed now:** organization into separate page documents, preserving prior owners' decisions, standalone draft Phase 5 visualization and stable entrypoint.

**NOT completed or certified:** renderable screenshot parity, uniform pixel/token design system, complete Dashboard modes, runnable schema-valid fixture package and real source key-path audit. `Phase 5` has a proposal only; no approved final UI/data. Frontend P6-B is **NOT AUTHORIZED**. No historical synthetic example is published empirical truth.

**Next acceptance:** fresh agent reconstructs each page from this index and canonical page file, and PM/Nex record a **per-page** PASS/PARTIAL/BLOCKED with evidence. Never interpret file existence as implementation-ready acceptance.
