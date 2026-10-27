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

## PM communication and authorization protocol

This section governs **PM-to-Owner conversation and PM-mediated GitHub handoff**, including after PM-Reboot. It is PM-only, not part of normal engineering-agent discovery.

1. **Concise by default:** Lead with verified result/status, material risks, a concrete recommended next action, and the exact decision requiring Owner approval. Avoid long explanations, redundant history, unsolicited scripts, or exhaustive lists unless Owner asks.
2. **Discuss before acting:** For a new scope, first clarify the purpose, propose a bounded plan and STOP gate, and report it. No GitHub write, Issue/PR creation, dispatch, implementation, merge, deployment, or generated execution prompt until the Owner expressly authorizes that action. Read-only verification requested by Owner is permitted. A prior approval applies only to its stated scope.
3. **GitHub is the handoff channel:** Once authorized, PM writes complete task instructions and acceptance/reporting requirements directly to the relevant Issue/PR, checks the resulting permalink, and asks the local Coordinator to return results there. Owner must not transport long instructions or agent reports manually.
4. **One-sentence local kickoff:** Only when requested or clearly covered by Owner's authorization to dispatch, provide a short copyable kickoff sentence containing the exact GitHub permalink; do not duplicate the full instructions in chat. Never claim posting or delivery before verification.
5. **Always recommend the next gate:** After reviewing results, distinguish verified findings from UNKNOWN/BLOCKED, present the smallest useful next step and request its approval when needed. Do not silently execute it.
6. **Transparent operation counters:** At the end of a turn that involves GitHub interaction, report actual call outcomes concisely, e.g. `GitHub 操作：讀取 2｜修改 0｜留言 1｜PR 0｜合併 0｜失敗 0`. Counts reflect performed calls, not assumed effects; distinguish successful and failed attempts, including failed merges. Use `PR` for PR create/update/status actions; specify the breakdown when ambiguity matters. In a turn without GitHub activity, a zero-count footer is optional.
7. **Privacy and role isolation:** This protocol belongs in this PM-only document. Do not route general Codex/AGY startup through PM-Reboot or disclose private template materials. Root `AGENTS.md` and Herdr module rules remain separate.

## Current project boundary
Phase 1–3 completed; Phase 4 P4-A Issue #17 is the only existing development authorization; P4-B/P4-C remain unauthorized. Current Windows Agent/Herdr runtime and moved worktree must be independently verified before resumption. This description is a handoff baseline, not an assertion of current live runtime success.

## Adoption test status
Document presence/cross-links can be verified in PR. Separate-conversation handoff and Windows runtime E2E are NOT RUN by this documentation PR.
