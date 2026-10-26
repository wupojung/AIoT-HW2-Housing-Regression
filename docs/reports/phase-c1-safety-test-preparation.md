# Phase C1 Safety Test Preparation Report

**Status: PREPARATION ONLY — no C1 runtime test, Worker launch, process action, or Ames data access was performed.** This document defines a future single-Worker synthetic test plan. It does not claim OS containment or Worker safety PASS.

## 1. Host and Runner capability evidence

| Area | Evidence and current interpretation | C1 status |
|---|---|---|
| Windows containment | Historical Windows A2 evidence in [PR #25](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/25) records 27/27 bounded synthetic checks. The older Runner uses a Win32 Job Object with kill-on-close and a 2 GiB Job memory limit. This is historical Windows evidence for that implementation and SHA; it is not current C1 evidence or a cross-platform guarantee. | Historical PASS only; current C1 NOT RUN |
| macOS containment | No current C-Prep OS containment provider or C1 containment evidence is established. The Issue #26 retrospective records prior macOS design reviews, an old M4 Max Python/sklearn smoke, and an unexecuted launchd/Watchdog PoC; none proves current OS containment. | UNKNOWN / NOT VERIFIED |
| macOS non-Windows behavior | Existing P4B fold execution paths explicitly fail closed when `os.name != "nt"`, requiring Win32 Job Object isolation. Pure C-Prep policy and adapter values do not themselves provide macOS Runner support. | Fail-closed code path exists; no macOS live test performed |
| Real Worker launch/stop | PR #32 is a cooperative, injected safety-policy boundary. `CPrepRunnerAdapter` accepts supplied observations and a `CooperativeRunnerControl`; it does not query OS processes, launch a Worker, send a signal, or prove termination. | Current C-Prep real Worker E2E NOT VERIFIED |
| Host identity | No host/OS capability inspection was authorized or performed for this documentation task. | UNKNOWN |
| PID and ownership | `ProcessIdentity` represents PID, PPID, `creation_time_ns`, `run_id`, `worker_id`, and monotonic observation time. The pure checker denies stale/mismatched/unauthorized observations. An OS provider must obtain and freshly revalidate the observation before every future control request. | Value validation IMPLEMENTED; OS lookup/revalidation provider NOT IMPLEMENTED |
| CPU/RSS/memory/swap/pressure | `MonitorSnapshot` accepts caller supplied host CPU, host memory used/total, swap used, pressure, per-Worker CPU/RSS/memory, observed time and heartbeat time. Validation rejects absent, invalid, unknown or stale values. No live collector/provider is implemented or verified; the trustworthy OS source, sampling cadence, and scope are UNKNOWN. | Snapshot schema/validation IMPLEMENTED; live source NOT IMPLEMENTED |
| Timeout and heartbeat | Budget evaluation accepts elapsed seconds and a maximum runtime; snapshot freshness uses observed and heartbeat monotonic seconds. These are supplied values, not an enforced process deadline or an independent heartbeat detector. Default policy values are not current Host authorization. | Pure policy IMPLEMENTED; runtime enforcement/provider NOT VERIFIED |

The current PR #32 dependency watermark is **OPEN/Draft, HEAD `39625ffbac361c9b0a6947c146276ec8a76a2ce2`**, per the one-time Team C status in the task Handoff. Any later PR HEAD requires a new bounded verification before its status is repeated.

## 2. State, stop, and checkpoint semantics

- **`FREEZE`** closes future task admission for the identified run. It does not pause, interrupt, or terminate already admitted work.
- **`STOP_REQUEST`** freezes admission and records stop intent through the cooperative `stop_all` interface. It is not an OS kill, does not prove a Worker exited, and must not be reported as safe termination.
- **Monitoring loss or invalid identity** must deny new admission. A future integration may freeze the authorized run, but must not signal an unverified PID. Restoring monitoring is not automatic permission to resume or admit work.
- The existing P4B codebase has checkpoint/resume paths, but PR #32's adapter does not implement checkpointing or prove a resumed Worker is safe. For C1, checkpoint format, atomic publication, and resume validation must be verified against the exact Runner SHA. A resume is eligible only when run/task identity and code, data, configuration, and fold digests match; incomplete output must remain marked partial and must not be aggregated.
- A future recovery test must record checkpoint identity, digest comparison, atomic-write outcome, partial/completed state, resume decision, and final output digest. Mismatch, corruption, or unknown state means deny resume and STOP for review.

## 3. Proposed C1 single-Worker synthetic matrix

All cases are **design only**. For every row, “Gate B authorization” means a separate Owner approval naming the exact Host/OS and code SHA, one isolated synthetic Worker boundary, named operator, budget, commands, and recovery/STOP plan. No commands below were executed. Evidence fields are future fields, not collected results.

| Case | Host / Owner prerequisites | Synthetic input and operation proposal | Expected behavior | Future evidence fields | PASS / FAIL / BLOCKED criteria | STOP condition |
|---|---|---|---|---|---|---|
| C1-01 Normal completion | Gate B authorization; supported Host/OS and exact SHA; one Worker only | Tiny fixed synthetic task with unique run/task/worker IDs; request one admission, complete normally | Only the authorized task is admitted; final status and output are complete and digestable | Host/OS, SHA, run/task/worker IDs, input digest, status events, timestamps, output digest, unrelated-process baseline | PASS if admission and completion match the contract; FAIL on extra admission or inconsistent output; BLOCKED if identity/status cannot be observed | Stop if the target identity or output ownership is ambiguous |
| C1-02 WARNING / CRITICAL | Gate B authorization; approved pressure source or deterministic injected fixture; one Worker | Supply synthetic `WARNING`, then `CRITICAL`, while below stop RSS/time limits; request another task | Future admissions freeze; current Worker is not claimed stopped; no `stop_all`/OS signal is implied by pressure alone | Snapshot values/age, pressure level, policy result, admission attempts, control calls, Worker status | PASS if no new task enters and existing Worker is not misreported terminated; FAIL if admission proceeds or a kill is claimed; BLOCKED if pressure source is untrusted | Stop if pressure becomes unknown or actual Host impact exceeds authorized limit |
| C1-03 Missing / stale / lost monitoring | Gate B authorization; test source and watchdog/operator plan identified | Inject missing snapshot, stale heartbeat, stale observation, then bounded monitor-loss event; attempt admission | Fail closed; deny new admission and freeze the authorized run where supported; never act on an unknown PID | Snapshot/heartbeat timestamps, freshness threshold, deny reason, freeze result, operator alert/time | PASS if each invalid/lost case denies admission with explicit reason; FAIL if stale data admits; BLOCKED if monitor loss cannot be detected or evidenced | Stop immediately on real monitoring loss or inability to distinguish stale from fresh data |
| C1-04 RSS warning boundary (inclusive) | Gate B authorization; synthetic fixture first; live threshold only if separately authorized | Inject aggregate Worker RSS just below and exactly at configured warning threshold | Below threshold may continue if all other gates pass; at threshold returns `FREEZE` (inclusive); does not terminate Worker | Per-Worker and aggregate bytes, threshold bytes, decision, status/admission events | PASS if exact threshold freezes and below-threshold case follows policy; FAIL if equality is missed; BLOCKED if RSS provenance/units are unknown | Stop if observed aggregate exceeds authorized warning/stop ceiling or source is untrusted |
| C1-05 RSS stop boundary (inclusive) | Gate B authorization; synthetic fixture first; stop procedure explicitly approved | Inject aggregate RSS exactly at and above configured stop threshold | `STOP_REQUEST` is recorded before a pressure freeze; no OS termination is inferred; operator follows separately authorized stop procedure | Per-Worker and aggregate bytes, stop threshold, decision/reason, stop-intent acknowledgement, live exit verification if separately authorized | PASS if equality records stop intent and blocks admission; FAIL if admission continues or intent is called termination; BLOCKED if no safe stop observer exists | Stop at authorized stop threshold; do not improvise a signal or kill |
| C1-06 Timeout | Gate B authorization with finite wall-time and operator limits | Use a synthetic task with injected elapsed-time progression to just below and exactly at deadline | Before deadline may continue if all gates pass; at deadline records stop intent and closes admission; actual exit remains unverified until safely observed | Configured deadline, monotonic start/observation, elapsed values, decision, status and exit observation | PASS if deadline boundary is inclusive and no new admission occurs; FAIL if over-time task is admitted/reported complete; BLOCKED if the clock/deadline cannot be trusted | Stop at the approved deadline or earlier on system instability |
| C1-07 PID reuse / identity mismatch | Gate B authorization; OS identity provider and allowed identity fields reviewed | Inject reused PID with changed creation time, changed PPID, wrong run/worker, stale observation, and unauthorized owner | Deny control/admission; never signal the mismatched or unauthorized process | Expected/observed PID, PPID, creation time, run/worker owner, observation time/age, reason, attempted actions | PASS if every mismatch denies and performs no process action; FAIL if any mismatched target is controlled; BLOCKED if OS identity cannot be freshly re-read | Stop on any identity mismatch, stale read, missing owner, or unexpected process action |
| C1-08 Freeze / admission race | Gate B authorization; atomic admission behavior included in exact SHA review | Race one synthetic admission request against `FREEZE`; repeat with stop intent already recorded | Freeze wins for not-yet-admitted work; already admitted work remains running unless separately stopped; stop intent does not claim exit | Event ordering, lock/shared-flag observations, admission return, run state, Worker status | PASS if no task crosses a completed freeze boundary and result reflects actual admission; FAIL if a post-freeze task enters; BLOCKED if ordering is not observable | Stop if admission state is inconsistent or any unapproved task starts |
| C1-09 Interruption / checkpoint / resume | Gate B authorization; checkpoint path and integrity scheme approved; synthetic files only | Interrupt a synthetic task at a defined checkpoint; attempt resume with matching then mismatched SHA/config/digest | Matching checkpoint may resume only under explicit authorization; mismatch/corruption denies resume; partial output is not aggregated | Checkpoint manifest/digest, atomic-write evidence, run/task identity, source digests, interruption event, resume decision, output state | PASS if matching identity is preserved and mismatches fail closed; FAIL if corrupted/mismatched state resumes; BLOCKED if checkpoint integrity cannot be verified | Stop and preserve evidence on corruption, partial overwrite, or digest mismatch |
| C1-10 Unrelated-process isolation | Gate B authorization must identify unrelated-process observation method and zero-impact evidence; no broad process targeting | Record a safe synthetic baseline for unrelated Codex/Herdr/project processes; perform authorized lifecycle only on the named Worker; compare identities/state before and after | No unrelated process is signaled, stopped, or changed by the test; no broad `killall`, `pkill`, or group kill | Before/after process identity/status observations, exact target identity, operation log, unrelated-process comparison, operator record | PASS only if every unrelated process remains unaffected and target scope is exact; FAIL on any unrelated impact; BLOCKED if isolation cannot be proven | Stop immediately on any unexpected unrelated-process change or target ambiguity |

For every case, a missing prerequisite or untrustworthy observation is **BLOCKED**, not PASS. Any unapproved process action, wrong-target control, new admission after freeze/stop, or unrelated-process impact is **FAIL** and terminates the planned test sequence pending Owner review.

## 4. Evidence layers and current status

| Evidence layer | Current evidence | Status |
|---|---|---|
| Pure Mock | Team C's one-time status reports the isolated C-Prep suite **21/21 PASS** at PR #32 HEAD `39625ff…`. A prior 13/13 snapshot is superseded by this count. These fixtures do not prove live providers or OS action. | PASS for that isolated Mock suite only |
| Adapter Integration | The adapter and injected cooperative `RunControlState` mapping are IMPLEMENTED. Coordinator's bounded smoke of the actual `RunControlState` source covered normal admission, WARNING freeze, and CRITICAL plus RSS stop intent. Full adapter integration coverage against the real P4BRunner path is not established. | PARTIAL evidence; full Adapter Integration PASS NOT VERIFIED |
| OS Containment | Current C-Prep OS identity/resource providers and process actions are NOT IMPLEMENTED. Historical Windows A2 Job Object evidence is separate and platform/version scoped. | Current C-Prep OS Containment PASS NOT ESTABLISHED |
| Real Worker Safety | No C1 live Worker launch, freeze, stop, checkpoint/resume, or unrelated-process isolation test was performed. | NOT RUN; PASS NOT ESTABLISHED |
| Standard package/test discovery | Team C reports standard `unittest` discovery was blocked before test loading by missing `numpy`; standard package discovery remains unverified. | NOT VERIFIED |

These evidence layers are not interchangeable. Mock PASS is not Adapter Integration PASS, OS Containment PASS, or Real Worker Safety PASS.

## 5. Authorization gates

1. **C1 live single Worker:** requires a separate Owner authorization after the applicable implementation and Host are identified. This report authorizes design only.
2. **C2 two Workers:** requires C1 PASS plus separate Owner authorization. C1 PASS alone does not start C2.
3. **Further scaling:** only stepwise after each applicable review and authorization, up to four Workers at most. Four is a ceiling, not a target or automatic next step.
4. Any change to platform, SHA, Worker boundary, resource budget, monitoring method, or stop procedure requires a fresh authorization decision before live testing.

## 6. Team C interface dependencies and status

This section records the one-time Team C status for PR #32 HEAD `39625ffbac361c9b0a6947c146276ec8a76a2ce2`; it is not a new request to Team C.

| Interface | IMPLEMENTED | NOT IMPLEMENTED / NOT VERIFIED | Team B disposition |
|---|---|---|---|
| `MonitorSnapshot` | Supplied host/Worker CPU, memory/RSS, swap, pressure, observed/heartbeat monotonic seconds; pure assessment validates units, ranges, freshness and fails closed on missing/unknown/stale data. | Live OS metric provider and independent monitor-loss detection. Trustworthy source and sampling cadence. | Preserve interface; mark collector/provider fields UNKNOWN until verified. Any required schema change is PROPOSAL. |
| `ProcessIdentity` | PID, PPID, `creation_time_ns`, run/worker ownership and observed monotonic time; pure check denies stale observations and PID/creation/parent/ownership mismatches or unauthorized targets. | Actual OS PID lookup and fresh revalidation provider before control actions. | Require provider evidence for every future control request; otherwise BLOCKED. Interface changes are PROPOSAL. |
| Budget/admission | Budget policy and incremental admission decision; normal admission within budget, warning/critical freeze, inclusive RSS/time stop intent, invalid metrics denied; staged increase is one Worker at a time up to configured max. | Live metric enforcement and real Worker scheduling behavior. Default values do not authorize a Host run. | Use synthetic inputs in future C1; Owner must set actual thresholds and worker count. |
| Status/action mapping | Injected cooperative `RunControlState` API: `status_snapshot`, `admit_task`, `freeze`, `stop_all`; unknown/mismatched run or state denies. | OS process termination and end-to-end P4BRunner wiring. `FREEZE`/`STOP_REQUEST` are not termination. | Preserve semantics; require an integration/termination evidence layer before claiming runtime safety. |
| Mock seams | `CooperativeRunnerControl` injection and `FakeRunControl` exist; isolated C-Prep suite reported 21/21 PASS. | Real Host providers and full P4BRunner end-to-end are not verified. | Report Mock result only at the verified PR SHA. |
| Package discovery | Isolated suite can run with its explicit source path according to Team C's status. | Standard `unittest` discovery was blocked before test loading by missing `numpy`; package discovery remains unverified. | Do not claim standard discovery PASS; resolve and verify under a separately authorized validation task. |

## 7. Owner Gate B authorization checklist

Before any live C1 Worker test, the Owner authorization should name or attach:

- [ ] Exact Host, OS/version, architecture, and relevant capability evidence.
- [ ] Exact code SHA, branch/worktree identity, and allowed file/runtime scope.
- [ ] One Worker identity and process boundary: run/task/worker IDs, PID/PPID/creation identity source, ownership rule, and fresh revalidation method.
- [ ] Synthetic input definition and proof that Ames Development, sealed Holdout, and Competition Test are not accessed.
- [ ] Exact commands or controlled invocation, expected outputs, evidence locations, and who may execute each operation.
- [ ] CPU, RAM/RSS, swap/pressure, wall-time and heartbeat limits, units, threshold inclusivity, and trusted measurement sources.
- [ ] Named live supervision, monitoring-loss response, recovery/checkpoint policy, bounded stop plan, and explicit actions that remain prohibited.
- [ ] OS identity/resource provider and the evidence that it targets only the authorized Worker.
- [ ] Before/after evidence for zero impact to unrelated Codex, Herdr, and project processes.
- [ ] Nex/QA gate and exact criteria required before C1 can be called PASS.
- [ ] Explicit list of unimplemented and unverified items, including live providers, full P4BRunner integration, standard package discovery, and any platform-specific containment gap.

Until those items are resolved and separately authorized, C1 remains **PREPARATION ONLY / NOT RUN**. No report section establishes runtime PASS, and no Ames dataset split was accessed for this task.
