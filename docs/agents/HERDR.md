# RegScope — Herdr communication and handoff rules

Scope: local development agents only. This document refines, but never overrides, root `AGENTS.md`, the assigned Issue, and explicit Owner approvals. Documentation adoption is NOT runtime installation or permission to contact panes.

## Entry and authority
- Read root `AGENTS.md`, the currently authorized GitHub Issue/PR and the minimum relevant task files before using Herdr.
- Verify installed CLI/version/help and native `herdr agent list` / `herdr agent get <verified-pane>` in the **current Windows runtime**. Never reuse old WSL paths or historic `w1:p1` labels as proof of identity.
- Base Herdr covers identity, one-shot native messaging, shared-file handoff and bounded diff-first review. It does **not** authorize recruiting or assigning peers. Team lifecycle is a separate, explicitly authorized extension: `docs/agents/HERDR-TEAMWORK.md`.
- Only designated, authorized roles may dispatch, push or comment; no messaging simply because another pane exists.

## One-shot native notification
- Sender first writes a private, ignored, receiver-accessible handoff with handoff ID, sender/receiver, verified worktree, Issue and authorization, BASE/HEAD, scope, tests and stop conditions. Include Team/Task IDs only when real and verified.
- Send one short `herdr agent prompt <verified-pane> "<handoff-ID> <path> <scope>"` using syntax supported by installed help. Do not include private datasets, secrets or transcript dumps.
- `agent_prompted` means delivery submitted, not receipt, acceptance or completion. Receipt ACK is optional; no ACK-of-ACK and no forced read or task launch.
- On ambiguity or timeout: one bounded supported diagnostic, record DELIVERY_UNKNOWN/ACK_PENDING as appropriate and stop. No blind resend, polling, timers or watchdogs.
- Receiver reads/accepts/works on handoff **only under its separate task authorization** and checks source freshness and scope before proceeding.

## Git and review evidence
- Handoff records repo, branch, worktree, immutable BASE/HEAD, changed files, `git diff --stat BASE HEAD`, focused tests, risks and uncommitted state. Compare only relevant diff first; broaden for evidenced dependencies/security risk.
- GitHub task reporting is conditional: a readable Issue URL does not grant comment permission. For an explicit task binding with reporting authorization, one designated reporter may post **once** on completion or BLOCKED; never startup/progress/ACK/heartbeat comments.
- When GitHub reporting is not explicitly permitted or confirmed, keep a private local handoff and visibly report `GitHub Support: LOCAL_ONLY`. Uncertain comment writes must not be blindly retried.
- No Herdr transport or Git operations from data-processing/modeling execution paths.
- No merge, deployment, worktree removal, or next task is implied by delivery, commit, review or this file.

## Runtime validation
Static doc checks are not proof of live Windows Herdr communication. Until Owner-authorized runtime verification completes, pane identities, worktree mapping and native messaging remain UNKNOWN / NOT RUN.
