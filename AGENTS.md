# RegScope — Agent collaboration and worktree policy

This repository is the NCHU AIoT 2026 HW2 Housing Regression Lab. This file is the standing operational policy for local Codex/AGY agents. Read the current Issue and actual Git state before work. **A specification is not permission to execute.** When instructions conflict, explicit newer Owner decisions take priority; report the conflict rather than guessing.

## Data and security boundary

- Keep real Kaggle CSVs, downloaded papers, private research, credentials, tokens, caches, local handoffs and generated unreviewed results in ignored `local/` or another verified ignored path. Never commit, paste into Issues/PRs, send to agents as prompt text, or publish raw rows, local paths containing secrets, or personal records.
- Use synthetic fixtures in tests. Before pushing or release, check staged/tracked content and public-facing output for prohibited data. Follow `docs/SECURITY_AND_DATA_POLICY.md`.
- **No automatic per-commit Python security scan.** `tools/security_scan.py` remains available manually. Security checks are mandatory, fail-closed gates before production/deploy updates, according to the actual GitHub settings and CI configuration; verify the real gate before claiming enforcement. Never bypass a failing required check.
- `main` is integration; `deploy` is production. No merge, production deployment, destructive migration, or public release without specific Owner authorization.
- EDA/modeling runtime must not invoke Git, Herdr, Codex, AGY or shell agent commands. Development, security and CI utilities may use Git when bounded and justified.

## Roles and authority

- **Coordinator (typically W1P1 / Codex):** intake, scoped planning, one-time dispatch, integration, first review, GitHub reporting and worktree inventory. The Coordinator alone may push after scope and data checks; pushing is not merging.
- **Implementer (typically W1P2 / AGY):** implement *one assigned bounded task* in its designated worktree; run focused tests; commit scoped changes; hand off and stop. Do not dispatch yourself, change agent governance, merge, deploy or launch recurring supervisors.
- **Independent QA (typically W1P3 / Codex):** review explicitly identified BASE..HEAD and evidence, using a separate read-only checkout/worktree when needed. Report PASS/BLOCKED and actionable defects. No implementation, merge or deploy unless separately authorized.
- These are roles, **not permanent pane identities**. Resolve actual identities once with `herdr agent list` when sessions start/change. Never assume a pane label identifies a person or process.

## Bounded task and incremental review

1. Read only the relevant GitHub Issue, acceptance criteria, current decisions and minimal required files. Verify branch/worktree state and record **BASE SHA**, objective, allowed files, non-goals, tests, time/effort boundary and **STOP condition** before dispatch.
2. Coordinator sends **one** scoped prompt to one idle, verified Implementer. Distinguish `delivered`, `accepted`, `running`, `committed`, `reviewed` and `merged`. Do not infer completion from prompt delivery.
3. Implementer reports **HEAD SHA**, `git diff --stat BASE HEAD`, changed files, test commands and results, known limitations, any uncommitted changes, worktree path, and next safe action. Stop at that boundary; do not keep hunting for follow-up tasks.
4. Coordinator reviews `git diff BASE HEAD` and relevant callers/tests only. For fixes, compare last reviewed HEAD to new HEAD, check unresolved findings, and avoid rescanning historical work without evidence. Independent QA checks exact same proposed revision after integration.
5. Record defects as file/line, reproduction, observed vs expected, severity and evidence. Do not invent failures, coverage numbers, performance root causes or success states.
6. Before merge, inspect cumulative PR diff, validate actual required checks, check data safety and ask for **specific Owner approval**. PR approval/test PASS does not authorize merging, deploy, Phase 3 or Issue closure.
7. GitHub Issue/PR comments hold durable decisions, SHA and concise evidence. Local ignored handoffs hold operational detail. Never require Owner to carry messages between agents.

## Herdr protocol — event driven, never monitoring

- Use installed-version help and `herdr agent list` to verify commands and identities; do not assume newer APIs are present. For a verified target, prefer a single `herdr agent prompt <agent-id> "<short status and handoff path>"` with relevant supported flags.
- A successful `agent_prompted` means **prompt delivered**, not read, approved or finished. Confirm the response once and wait for the other agent's **proactive completion message**; do not repeatedly inspect its pane or schedule retries.
- Git commit/diff is authoritative for code; shared local handoff Markdown is authoritative for task context; Herdr carries only brief notices with SHA/path/status. No long documents, secrets or raw data in prompts.
- **Forbidden:** Watchdog, `Schedule(15s)` or other recursive/short-interval scheduling, perpetual `agent wait`, polling panes/queues, agents monitoring each other, duplicate prompts after timeout, and agents automatically starting each other's new jobs.
- If delivery or status is ambiguous, take **one bounded snapshot** (agent list + short recent output if available), record UNKNOWN and stop/escalate. Lack of a historical Queue API alone is not a blocker. For Git timeout or D-state, take one bounded diagnostic, stop and report; no infinite retries.

## Worktree lifecycle and cleanup (mandatory)

**Goal: one accountable worktree per active task, not an accumulating pool of abandoned checkouts.**

### Inventory before assignment or agent restart

Coordinator records a single snapshot using bounded, read-only commands: `git worktree list --porcelain`, `git status --short` in the relevant checkouts, `git branch -vv`, and available PR/Issue references. Build a compact ledger with **path, branch, HEAD, agent/Issue, clean/dirty, active/idle/unknown, pushed/merged status, local-only commits, ignored assets, and proposed disposition**. Never assume that a directory is disposable merely because its pane has closed.

### Reuse before create

- Reuse an existing clean, idle task worktree when safe; create a new one only for actual isolation needs and an explicit assigned task. Avoid multiple worktrees on the same branch.
- Each Agent gets a designated writable checkout. QA reviews in read-only mode. Never reset, switch, stash, clean or overwrite another agent's worktree; never share write access to one checkout.
- For worktree creation, record path, branch, starting SHA, intended Owner/Issue and planned cleanup condition in the handoff.

### Safe cleanup after completed work

1. Coordinator collects the final SHA/handoff and confirms the task is complete, Issue/PR evidence persisted, and no Agent is still using the checkout. Ask each relevant Agent **once** for release of its worktree; do not poll.
2. Inspect `git status --porcelain`, local-only commits compared with upstream/base, untracked and ignored data, branch/PR merge status, and outstanding handoff dependencies. If any are unknown, dirty, unmerged, or contain unbacked-up evidence, **HOLD** with a reason.
3. Present a proposed **KEEP / REUSE / REMOVE / HOLD** ledger. Only **Owner-approved REMOVE** may delete a worktree or branch. Owner approval must identify the cleanup scope; it is not implied by authorizing development or a merge.
4. For an approved clean, unused and fully integrated checkout, use normal `git worktree remove <path>` (no `--force`); only after confirming it is gone may the Coordinator consider `git branch -d <branch>` for a merged, unused branch if separately covered by approval. `git worktree prune --dry-run` may be used to inspect stale metadata; ordinary prune only after checking that paths really no longer exist.
5. **Never** use `git worktree remove --force`, `git branch -D`, `git reset --hard`, `git clean -fdx`, recursive directory deletion or automatic bulk cleanup without a separate explicit, path-specific Owner authorization and a documented recovery plan. A clean worktree can still contain important ignored `local/` data.
6. Record removed paths, preserved refs/commits, command results, remaining worktrees and any HOLD items in the Issue/handoff. Do not delete ignored handoffs or datasets merely to make the inventory look clean.

### Worktree incident stop conditions

If worktree ownership is ambiguous, branch HEAD changed unexpectedly, a checkout is in use, D-state/Git I/O stalls, a safety ref is missing, or disk pressure could jeopardize preservation: **STOP cleanup**. Report known evidence; do not spin up a scavenger agent or retry indefinitely.

## Exact CLI runbook (WSL / Herdr 0.9.5)

Use the commands below **as written**. Lines containing `<PLACEHOLDER>` are templates, **not runnable commands**; first fill them with verified values. Never invent Herdr subcommands or a pane ID. These are manual, bounded steps, not polling scripts.

### 1. Identify agent and inspect state (read-only)

```bash
cd /mnt/d/project/nchu/aiot/AIoT-HW2-Housing-Regression
pwd
git rev-parse --show-toplevel
git status --short --branch
git rev-parse HEAD
herdr --version
herdr agent list
herdr agent --help
herdr agent prompt --help
herdr agent get --help
herdr agent read --help
```

If a documented option is not supported by the **installed** version, **stop and report the actual error**; do not guess another syntax. Pane identifiers such as `w1:p1` are illustrative until confirmed in the current `herdr agent list`. One check per session or after identity/permission changes; no recurring introspection.

### 2. One-time assignment and completion notice

Coordinator first writes a shared ignored handoff containing Issue, scope, BASE SHA, worktree, acceptance tests and STOP conditions. After confirming the target pane is idle and is the intended role, send **once**:

```bash
herdr agent get <VERIFIED_TARGET_ID>
herdr agent prompt <VERIFIED_TARGET_ID> "Issue #<N>: execute only the assigned scope in <SHARED_HANDOFF_ABSOLUTE_PATH>. BASE <SHA>. Commit, run bounded tests, report HEAD and stop. No merge/deploy or monitoring."
```

Check for `type: agent_prompted`. This means **delivered only**; not accepted, running, complete or approved. If delivery is ambiguous, **do not resend automatically**. For a single bounded manual diagnostic, **only if supported by installed CLI**, use:

```bash
herdr agent read <VERIFIED_TARGET_ID> --source recent-unwrapped --lines 20
```

Implementer/QA sends its **one** proactive completion report:

```bash
herdr agent prompt <VERIFIED_COORDINATOR_ID> "Issue #<N> STATUS PASS/BLOCKED; BASE <SHA>; HEAD <SHA>; tests <RESULT>; handoff <ABSOLUTE_PATH>; stopped. No merge/deploy."
```

Do **not** use `herdr notification show` for handoff. Do **not** run `herdr agent ... --wait` continuously or create timers, watchdogs, repeated `get/read/list` calls or retry loops.

### 3. Exact incremental review commands (read-only)

In the **designated checkout**, after obtaining actual SHA values from handoff:

```bash
git status --short --branch
git rev-parse HEAD
git diff --stat <VERIFIED_BASE_SHA> <VERIFIED_HEAD_SHA>
git diff --check <VERIFIED_BASE_SHA> <VERIFIED_HEAD_SHA>
git diff <VERIFIED_BASE_SHA> <VERIFIED_HEAD_SHA>
```

To review only a follow-up fix, replace BASE with **previously reviewed HEAD**, not the project genesis. Reviewers must not auto-approve newer commits or rerun all suites without a concrete requirement. Tests are explicit in the Issue; prefer focused synthetic tests with a bounded timeout, e.g.:

```bash
timeout --signal=TERM --kill-after=3s 45s python3 -m unittest discover -s tests/tools/eda -v
timeout --signal=TERM --kill-after=3s 45s python3 -m unittest tests.security.test_security_scan -v
```

Only run when the required Python environment is ready. A timeout or failed test is a reportable failure, **not** an invitation to recursively retry.

### 4. Worktree inventory: read-only first, every time

Run from the repo root. The first set does **not** modify branches, files or worktree registration:

```bash
git worktree list --porcelain
git branch -vv
git status --short --branch
git rev-parse HEAD
git worktree prune --dry-run
```

For **each reported actual worktree path**, inspect it individually (do **not** iterate blindly over stale paths). Replace the placeholder with the exact verified quoted path:

```bash
git -C "<VERIFIED_WORKTREE_PATH>" status --porcelain=v1 --untracked-files=all
git -C "<VERIFIED_WORKTREE_PATH>" rev-parse HEAD
git -C "<VERIFIED_WORKTREE_PATH>" branch --show-current
git -C "<VERIFIED_WORKTREE_PATH>" ls-files --others --ignored --exclude-standard
git -C "<VERIFIED_WORKTREE_PATH>" log --oneline --decorate -5
```

`ls-files --others --ignored` can be large; **summarize counts/paths only**, do not paste private names or data into public GitHub. Check local-only commits and branch integration after identifying the actual branch and comparison ref:

```bash
git log --oneline <VERIFIED_BASE_REF>..<VERIFIED_TASK_BRANCH>
git branch --merged <VERIFIED_BASE_REF>
```

**IMPORTANT:** `git branch --merged` and a clean status alone **do not** prove safe deletion; inspect ignored `local/`, handoffs, agent use and whether local commits exist. If in doubt, classify HOLD.

### 5. Creation and removal: explicit Owner approval gate

**Creation example, only if Coordinator has Owner-authorized task and verified unused path/branch:**

```bash
git worktree add -b <NEW_UNIQUE_TASK_BRANCH> "<APPROVED_NEW_WORKTREE_PATH>" <VERIFIED_BASE_REF>
git worktree list --porcelain
```

**Removal example, only after the Owner approves the *specific path* and Coordinator confirms it is clean, idle, integrated, has no important ignored/untracked data or unresolved handoffs:**

```bash
git -C "<OWNER_APPROVED_WORKTREE_PATH>" status --porcelain=v1 --untracked-files=all
git worktree remove "<OWNER_APPROVED_WORKTREE_PATH>"
git worktree list --porcelain
```

If removal fails, **STOP**. Never add `--force`. Optional branch deletion requires separately covered Owner scope and confirmed merge:

```bash
git branch -d <OWNER_APPROVED_MERGED_BRANCH>
```

Only if `git worktree prune --dry-run` revealed stale registration **and** the actual directory is verified gone, Coordinator may propose regular `git worktree prune` for Owner approval. Do not run cleanup automatically or batch over every listed path.

### 6. Status and incident reporting format

Use one compact report per boundary:

```text
Issue: #<N> | ROLE: Coordinator/Implementer/QA | HERDR: <VERIFIED_ID>
WORKTREE: <PATH> | BRANCH: <NAME> | BASE: <SHA> | HEAD: <SHA>
RESULT: PASS/BLOCKED/UNKNOWN | TESTS: <COMMAND AND OUTCOME>
WORKTREES: KEEP <...>; REUSE <...>; REMOVE-PROPOSED <...>; HOLD <...>
STOP REASON / OWNER ACTION: <ONE LINE>
```

No secrets, dataset rows, terminal session dumps or sensitive file contents in public Issue comments.

## Completion, knowledge transfer and final Owner merge gate

**Ordering is mandatory:** PM technical Review PASS → notify Owner → Coordinator-led agent closeout and knowledge preservation → authorized worktree cleanup → PM closeout verification → Owner's explicit final merge authorization → Coordinator merges → post-merge Issue confirmation. A technical PASS is **not** final merge approval.

1. **PM Review PASS / Owner notice.** PM tells Owner the reviewed exact PR HEAD, result and remaining risks and requests a **closeout assignment**. Do not immediately merge. Owner's authorization to perform closeout permits only the scope stated; it is not permission to delete unknown paths or merge.
2. **W1P1 closeout dispatch.** Coordinator checks `herdr agent list` once and sends one bounded task each to W1P2 (implementation and runtime handoff), W1P3 (independent QA and residual risks), and self (integration/worktree ownership). Each agent inventories **its own** assigned checkout, commits, changes, tests, unresolved defects, lessons learned, reproducible commands and next-stage recommendations. Each stops and sends a single Herdr summary with an ignored local handoff path. No agents monitor each other.
3. **Durable project handoff.** W1P1 consolidates project purpose, current CRISP-DM phase and gates, completed work, key decisions, PR/Issue/SHA links, code entrypoints and execution commands, actual test/CI evidence, data boundaries, outstanding defects, next authorized action and known agent/CLI failures into a concise **public-safe** GitHub Issue checkpoint or reviewed project document. This must be sufficient for fresh agents without reading old terminal sessions. Full private notes remain local; redact raw datasets, credentials, session history, personal paths and unreviewed artifacts. No automatically generated speculative root causes.
4. **Worktree pre-merge cleanup.** W1P1 creates a path-specific KEEP/REUSE/REMOVE/HOLD ledger and obtains **explicit Owner authorization for the named paths** (this is independent of final merge authorization). Before any removal, confirm that the clean checkout is idle/released, its changes are preserved in commits and reachable refs or remote PR head, no untracked/ignored work product will be lost, and any private handoffs needed later have been copied into a safe preserved ignored location. The integration/PR branch must remain reachable until final merge; removing a disposable checkout **must not delete its unmerged branch/ref**. Remove only approved safe worktrees using normal `git worktree remove` with no force. If a candidate is dirty, contains important ignored local data, is active, or has unverified commits, classify HOLD; report it as a **closeout exception** rather than deleting it. An Owner may approve retaining HOLD until after merge. Never delete the active Coordinator worktree while using it.
5. **Closeout evidence.** W1P1 posts final SHA, links, tests, lessons, worktree list before/after, successfully removed paths, protected refs, HOLD exceptions and the handoff location to the Issue/PR. Use `git worktree list --porcelain` for actual verification; do not claim worktrees were removed unless checked. No merge yet.
6. **PM closeout Review.** PM checks handoff completeness, safety and the specific cleanup evidence (or explicitly documented HOLD exceptions), and issues **CLOSEOUT PASS or BLOCKED**. If BLOCKED, resolve only the listed items; do not recursively repeat full reviews.
7. **Owner final merge authorization.** Only after PM issues CLOSEOUT PASS does the Owner approve the **specific PR and reviewed HEAD** for squash merge. W1P1 checks that HEAD and required checks are still current, then merges **once**, updates Issue with merge SHA and residual worktree/HOLD items, and stops. New commits after PM Review require targeted re-review before merge.

### Exact closeout commands (run only in Coordinator's designated checkout)

```bash
# Read-only: record PR integration state and worktree inventory
git status --short --branch
git rev-parse HEAD
git worktree list --porcelain
git branch -vv
git worktree prune --dry-run
```

For each **verified** released candidate, use the individual inspection commands in section 4. Do **not** bulk-clean. After Owner authorizes its exact path and all safety checks pass:

```bash
git worktree remove "<OWNER_APPROVED_SAFE_WORKTREE_PATH>"
git worktree list --porcelain
```

If worktree removal is unsafe or fails, **STOP and mark HOLD**, not `--force`. Only the Coordinator is allowed to perform cleanup. QA/Implementer provide release reports; they do not delete each other's worktrees.

### Final closeout report contract

```text
PR / Issue: <URLS> | Reviewed HEAD: <SHA> | PM technical review: PASS
Completed scope / acceptance / actual tests: <SHORT EVIDENCE>
Handoff: <PUBLIC-SAFE ISSUE LINK> | Private notes: <IGNORED PATH>
Agent lessons: <CONFIRMED / SUSPECTED / UNKNOWN; IMPROVEMENTS>
Worktrees BEFORE/AFTER: <COUNTS AND PATHS>
REMOVED: <EXACT OWNER-AUTHORIZED PATHS> | HOLD: <PATH AND REASON>
Remaining risks / next task: <SUMMARY> | PM CLOSEOUT: PASS/BLOCKED
Owner final squash merge approval: PENDING / AUTHORIZED for PR <N>, HEAD <SHA>
```

### Flow

```mermaid
flowchart TD
  A[Owner Issue authorization] --> B[W1P1 bounded dispatch via Herdr]
  B --> C[W1P2 implement and commit]
  C --> D[W1P1 incremental Review]
  D --> E[W1P3 independent QA]
  E --> F{PM technical Review PASS?}
  F -->|No| R[Targeted fixes and review]
  R --> D
  F -->|Yes| G[PM notifies Owner: ready for closeout]
  G --> H[W1P1 requests W1P2/W1P3 final inventories and handoffs]
  H --> I[Preserve project knowledge in Issue and local handoff]
  I --> J[Worktree ledger and Owner path-specific cleanup approval]
  J --> K[Coordinator safely removes approved idle worktrees]
  K --> L[Verify removal and document HOLD exceptions]
  L --> M{PM closeout Review PASS?}
  M -->|No| N[Resolve listed closeout gaps only]
  N --> M
  M -->|Yes| O[Owner authorizes final PR and HEAD squash merge]
  O --> P[Coordinator merges once, records merge SHA, closes stage]
```
