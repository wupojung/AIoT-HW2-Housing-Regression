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
- `agent_prompted` means delivery submitted, not receipt, acceptance or completion. Receipt ACK is optional for read-only notification only. **For any authorized engineering, resource-affecting or critical task, verify recipient identity and obtain explicit task-acceptance ACK before work starts**; `agent_prompted` never suffices. No ACK-of-ACK and no forced read or task launch.
- On ambiguity or timeout: one bounded supported diagnostic, record DELIVERY_UNKNOWN/ACK_PENDING as appropriate and stop. No blind resend, polling, timers or watchdogs.
- Receiver reads/accepts/works on handoff **only under its separate task authorization** and checks source freshness and scope before proceeding.

## Git and review evidence
- Handoff records repo, branch, worktree, immutable BASE/HEAD, changed files, `git diff --stat BASE HEAD`, focused tests, risks and uncommitted state. Compare only relevant diff first; broaden for evidenced dependencies/security risk.
- GitHub task reporting is conditional: a readable Issue URL does not grant comment permission. For an explicit task binding with reporting authorization, one designated reporter may post **once** on completion or BLOCKED; never startup/progress/ACK/heartbeat comments.
- When GitHub reporting is not explicitly permitted or confirmed, keep a private local handoff and visibly report `GitHub Support: LOCAL_ONLY`. Uncertain comment writes must not be blindly retried.
- No Herdr transport or Git operations from data-processing/modeling execution paths.
- No merge, deployment, worktree removal, or next task is implied by delivery, commit, review or this file.

## 三角色最小協作與異常停止（RegScope 專案）

- Coordinator 負責 Owner 任務授權與範圍、身分/Worktree 核對及唯一對外進度回報；Implementer 只做一項被接受的授權工作、留下交付 SHA/測試；Independent QA 對同一最終 SHA 及證據獨立驗收，不自行 Merge。
- 一份有界 Handoff → 明確接受 ACK（關鍵任務必須）→ 成果與限制 → 獨立 QA → 精簡 Checkpoint；收到投遞≠接受、完成或 Review PASS。失聯/逾時一次唯讀核查後標 UNKNOWN 並 STOP，嚴禁循環輪詢、猜測身分或擅自終止其他工作。
- 同一根因反覆 QA BLOCKED 時，Coordinator 停止無界修補並交 PM/Owner 判斷縮小範圍或中止。文件審查通過不代表模型、Worker 或跨平台 Supervisor 已實測安全。具體 Host 啟停只能依另外取得授權的工程工作指示。

## Runtime validation
Static doc checks are not proof of live Windows Herdr communication. Until Owner-authorized runtime verification completes, pane identities, worktree mapping and native messaging remain UNKNOWN / NOT RUN.
