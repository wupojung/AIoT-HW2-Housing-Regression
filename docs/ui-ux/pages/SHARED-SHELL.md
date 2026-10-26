# Shared Shell / Home — Current UX

**Active proposal.** Desktop 1920×1080; case selector global; six phase tabs one horizontal row; Home starts Phase 1; Dashboard separate route. No frontend code authorization.

## P6-A Owner discussion supplement — Phase 1–3 detailed reconstruction contract (2026-10-26)

**Status: OWNER-DISCUSSED UX SPECIFICATION / DOCS ONLY.** This section records the latest Phase 1–3 decisions and is the **more specific controlling visual/interaction reference** where older generic Phase 1–3 ASCII sketches above differ. It does not supersede verified Phase 2 evidence, governance gates, the case/model registry safety requirements, or the unfinished Phase 4–6 designs. **No implementation, dataset processing, research rerun, publication, merge or deployment is authorized by this document.**

**How to reconstruct it:** This is a specification, not a screenshot. Draw controls and content in the relative order shown; labels in square brackets are actual controls only where the control catalog explicitly says so. A chart is a **single 100%-stacked horizontal bar** with dynamic segments, consistent category colors and labels, plus explicit numeric counts; four successive bars MUST read as a continuous feature-processing story. Desktop target **1920×1080**, vertically scrollable page. Exact component pixel measurements, type scales, colors and responsive breakpoints are **not Owner-approved**: do not mistake invented values for acceptance requirements. Use responsive widths within a centered desktop content panel; allow scrolling down rather than squeezing four stages into one screen.

### A. Shared shell and navigation — every Phase

~~~text
+--------------------------------------------------------------------------------------------------+
| RegScope                                                 Home / CRISP-DM    [Dashboard]          |
| Study dataset: [Ames Housing                                                 v]                 |
+--------------------------------------------------------------------------------------------------+
| [01 Business Understanding] [02 Data Understanding] [03 Data Preparation*]                     |
| [04 Modeling]             [05 Evaluation]       [06 Deployment]                                |
| NOTE: these six items occupy ONE horizontal desktop row; above is label wrapping in ASCII only.  |
+--------------------------------------------------------------------------------------------------+
| PHASE NN / [ENGLISH TITLE]                                                                        |
| [CASE-SPECIFIC SCROLLING CONTENT]                                                                 |
|                                                                                                  |
| [< Previous Phase]                                                         [Next Phase >]        |
+--------------------------------------------------------------------------------------------------+
~~~

**Global control contract**
1. **Research dataset selector**: one global control, not six phase-local selectors. Its displayed label comes from the current case \`title\`, with stable \`case_id\` used internally. Options are **documented cases only**; planned candidates may be disabled with a visible PLANNED explanation, never presented as completed runs. Selecting an eligible case replaces every phase's content, evidence, image paths, metrics, target/unit and available controls. Keep current phase number if supported; on unsupported phase show UNAVAILABLE/PLANNED rather than retaining the previous case's content. Clear previous case-specific selected EDA analysis and open details, and use the new case's default published item. Do not combine case data.
2. **Phase tabs 01–06**: each navigates to exactly one phase in the current case. The selected tab has active appearance and an accessible current-state label; other tabs stay individually keyboard-focusable if navigation is allowed. Click never changes case. On unsupported content show honest empty/unavailable explanation; tabs need not imply empirical completion. **Six in one horizontal desktop row**, regardless of the ASCII line-wrap used to explain them.
3. **Home**: opens the six-step research journey at Phase 1. **Dashboard**: separate secondary route, *not* an alternative dashboard panel under each phase. Keep prior dashboard-specific security and custom-data gate descriptions above; this supplement does not authorize the Dashboard Run action.
4. **Previous / Next**: navigate exactly one phase backward/forward within the same case. Hide or disable Previous at Phase 1, Next at Phase 6; never loop around. Keyboard Enter/Space activation, visible focus, meaningful labels. Case/phase navigation invalidates stale selected content and asynchronous results.
5. **State handling**: LOADING clears stale content; EMPTY, ERROR, PLANNED, MOCK, UNAVAILABLE, VERIFIED have meanings already defined above. Never turn UI examples or unreviewed local figures into verified case data. External source links must be safe, published URLs; no local machine paths.

### E. Acceptance checks for Phase 1–3 reconstruction
- [ ] On 1920×1080 desktop, all six CRISP-DM tabs appear in a **single** horizontal row; main panel vertically scrolls without forcing four Phase 3 bars onto one viewport.
- [ ] Global dataset picker drives all six phases; no per-phase dataset picker and no stale previous-case figure/copy.
- [ ] Phase 1 renders dataset provenance, case-specific Problem/Objective/Value, target/unit and shared methodology, without charts or images.
- [ ] Phase 2 analysis selector count equals the **approved/published** manifest length; each selection atomically swaps one image and its verified explanatory/evidence data; inaccessible/unapproved assets never appear as research.
- [ ] Phase 3 stages ①–④ each visibly have **the same** stacked horizontal type-distribution chart structure, legend, count, percent, known/unknown status, explanation BELOW bar and a directional connector.
- [ ] Stage ② preserves unchanged distribution **if** exclusion count verified 0; pending exclusion count is not displayed as zero.
- [ ] Stage ③ includes working independently collapsible treatment accordions; expand state doesn't alter the four bars; no fictional operations.
- [ ] Stage ④ encoded type segment widths may differ from Stages ①–③, especially due to **One-Hot expansion**; numeric encoded total 248 is distinctly not Phase 4 selected count 97.
- [ ] When distribution numbers are missing, UI displays **pending/unavailable** rather than any sample percentage, while retaining known audited total.
- [ ] Train–Test Split is the final separate 80/20 **row** bar, labels exact English names and row counts, never confuses Kaggle competition test or Phase 4 3-fold CV.
- [ ] Every control's inactive/loading/empty/unavailable state is accessible and truthful; all paths and percentages are validated and case-scoped.
- [ ] No engineering work or changes to substantive research/QA evidence are implied by this docs-only supplement.


---