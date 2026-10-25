# RegScope — PM-only conversation handoff procedure

**Audience: Owner and current/incoming Project Manager only.** This is not a general engineering-agent entry point, CLI/pane restart guide, or Herdr/team lifecycle rule. Engineering agents must not be directed here during normal setup.

## Single durable journal
- Repository: `wupojung/AIoT-HW2-Housing-Regression`.
- Dedicated standing journal: https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/18 .
- One Issue per project, one **new standalone comment per Owner-authorized reboot**. Never create a branch/Issue per handoff.
- The first accepted checkpoint is https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/18#issuecomment-6392821795 . Future checkpoints link their immediate predecessor.

## Outgoing PM
1. Re-read primary GitHub evidence: branch SHA, Issue/PR head and status, current Owner approvals, last verified gates, tests, unresolved risks and known local-only unknowns.
2. Create one self-contained, public-safe checkpoint: project, date/PM, previous checkpoint, source watermarks, authorized/not authorized scope, phase/gate, completed proof, blockers, local recovery state as UNKNOWN when unverifiable, and next decision.
3. Publish only after explicit Owner reboot authorization; verify resulting comment is readable and return its **exact GitHub permalink**. No private template contents, raw Kaggle/NotebookLM assets, credentials or machine-sensitive paths in public journal. If write uncertain, do not blindly duplicate.
4. Corrections to prior checkpoints are new linked comments, not silent history rewrites.

## Incoming PM
1. Verify that the exact linked comment belongs to this repository and journal; independently compare current GitHub branch, Issues, PRs and approvals.
2. Mark each discrepancy MATCH / UPDATED / PARTIAL / UNKNOWN; recent verified sources take precedence over old prose.
3. Limit reverse-check of outgoing PM to material missing decisions/evidence. If unavailable, preserve uncertainty and request Owner acceptance.
4. Report acceptance and next permission gate. Reboot does **not** authorize dispatch, merge, deploy, cleanup or phase expansion.

## Current project boundary
Phase 1–3 completed; Phase 4 P4-A Issue #17 is the only existing development authorization; P4-B/P4-C remain unauthorized. Current Windows Agent/Herdr runtime and moved worktree must be independently verified before resumption. This description is a handoff baseline, not an assertion of current live runtime success.

## Adoption test status
Document presence/cross-links can be verified in PR. Separate-conversation handoff and Windows runtime E2E are NOT RUN by this documentation PR.
