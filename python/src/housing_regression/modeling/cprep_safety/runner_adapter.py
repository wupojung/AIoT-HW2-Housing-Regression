"""Injectable bridge from supplied observations to cooperative run control.

This adapter accepts data values and an injected control object only. It never
queries the operating system, starts a worker, or signals a process.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from .budget import (
    AdmissionDecision,
    BudgetDecision,
    SafetyBudgetPolicy,
    decide_admission,
    evaluate_budget,
)
from .control import ControlState
from .monitor import (
    MonitorAssessment,
    MonitorSnapshot,
    PressureLevel,
    WorkerResources,
    assess_snapshot,
)
from .process_identity import ProcessIdentity, check_process_identity


class CooperativeRunnerControl(Protocol):
    """Narrow subset implemented by the current run-scoped control state."""

    def status_snapshot(self) -> Mapping[str, Any]: ...

    def admit_task(self, task_id: str) -> bool: ...

    def freeze(self) -> Mapping[str, Any]: ...

    def stop_all(self) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class AdapterResult:
    """Policy and cooperative-control outcome; contains no termination claim."""

    decision: BudgetDecision
    admitted: bool
    reason: str
    runner_action: str
    runner_state: str | None


class CPrepRunnerAdapter:
    """Convert supplied observations and gate one task through run control."""

    _KNOWN_RUNNER_STATES = frozenset(
        {"CREATED", "RUNNING", "FROZEN", "STOP_REQUESTED", "COMPLETED", "FAILED", "STOPPED"}
    )

    def __init__(
        self,
        *,
        control: CooperativeRunnerControl,
        run_id: str,
        authorized_worker_ids: frozenset[str],
        policy: SafetyBudgetPolicy,
    ) -> None:
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("Adapter requires a nonempty run_id")
        if (
            not isinstance(authorized_worker_ids, frozenset)
            or not authorized_worker_ids
            or any(not isinstance(item, str) or not item for item in authorized_worker_ids)
        ):
            raise ValueError("Adapter requires authorized worker IDs")
        if not isinstance(policy, SafetyBudgetPolicy):
            raise ValueError("Adapter requires a valid safety budget policy")
        self.control = control
        self.run_id = run_id
        self.authorized_worker_ids = authorized_worker_ids
        self.policy = policy

    def admit_task(
        self,
        *,
        task_id: str,
        resource_observation: Mapping[str, Any] | None,
        expected_identity: ProcessIdentity | None,
        identity_observation: Mapping[str, Any] | None,
        current_workers: int,
        requested_workers: int,
        now_monotonic: float,
        elapsed_seconds: float,
    ) -> AdapterResult:
        """Assess supplied values, then perform at most one cooperative gate call."""

        runner_state, status_reason, verified_run = self._runner_state()
        if not verified_run:
            return self._result(BudgetDecision.DENY, status_reason, "none", runner_state)
        if status_reason == "UNKNOWN_RUNNER_STATE":
            action = self._freeze_future_admissions()
            return self._result(BudgetDecision.DENY, status_reason, action, runner_state)
        if runner_state is ControlState.STOP_REQUESTED:
            action = self._record_stop_intent()
            return self._result(BudgetDecision.STOP_REQUEST, "STOP_ALREADY_REQUESTED", action, "STOP_REQUESTED")
        if runner_state is ControlState.FROZEN:
            action = self._freeze_future_admissions()
            return self._result(BudgetDecision.FREEZE, "ADMISSION_ALREADY_FROZEN", action, "FROZEN")
        if runner_state is not ControlState.RUNNING:
            return self._result(BudgetDecision.DENY, status_reason, "none", runner_state)

        try:
            snapshot = self._monitor_snapshot(resource_observation)
            assessment = assess_snapshot(
                snapshot,
                now_monotonic=now_monotonic,
                max_age_seconds=self.policy.max_snapshot_age_seconds,
            )
        except (TypeError, ValueError, OverflowError):
            assessment = MonitorAssessment(False, "INVALID_MONITOR_OBSERVATION", None, None, None)
        observed_identity = self._process_identity(identity_observation)
        identity_check = check_process_identity(
            expected_identity,
            observed_identity,
            authorized_run_id=self.run_id,
            authorized_worker_ids=self.authorized_worker_ids,
            now_monotonic=now_monotonic,
            max_age_seconds=self.policy.max_snapshot_age_seconds,
        )

        try:
            budget_decision = evaluate_budget(
                assessment,
                state=runner_state,
                elapsed_seconds=elapsed_seconds,
                policy=self.policy,
            )
            admission_decision = decide_admission(
                current_workers=current_workers,
                requested_workers=requested_workers,
                state=runner_state,
                assessment=assessment,
                elapsed_seconds=elapsed_seconds,
                policy=self.policy,
            )
        except (TypeError, ValueError, OverflowError):
            action = self._freeze_future_admissions()
            return self._result(BudgetDecision.DENY, "INVALID_POLICY_INPUT", action, "RUNNING")

        # A run-scoped freeze is safe for this verified run and closes future
        # admissions when either supplied observation is not trustworthy.
        if not assessment.valid:
            action = self._freeze_future_admissions()
            return self._result(BudgetDecision.DENY, assessment.reason or "INVALID_MONITOR", action, "RUNNING")
        if not identity_check.authorized:
            action = self._freeze_future_admissions()
            return self._result(BudgetDecision.DENY, identity_check.reason, action, "RUNNING")

        if budget_decision is BudgetDecision.STOP_REQUEST:
            action = self._record_stop_intent()
            return self._result(BudgetDecision.STOP_REQUEST, "STOP_REQUESTED_BY_BUDGET", action, "RUNNING")
        if budget_decision is BudgetDecision.FREEZE:
            action = self._freeze_future_admissions()
            return self._result(BudgetDecision.FREEZE, "BUDGET_FREEZE", action, "RUNNING")
        if budget_decision is BudgetDecision.DENY or not admission_decision.allowed:
            reason = admission_decision.reason if not admission_decision.allowed else "BUDGET_DENIED"
            return self._result(BudgetDecision.DENY, reason, "none", "RUNNING")

        try:
            admitted = self.control.admit_task(task_id)
        except Exception:
            action = self._freeze_future_admissions()
            return self._result(BudgetDecision.DENY, "RUNNER_ADMISSION_ERROR", action, "RUNNING")
        if not admitted:
            # The injected RunControlState owns the atomic admission boundary;
            # a concurrent freeze/stop wins without starting this task.
            return self._result(BudgetDecision.DENY, "ADMISSION_RACE_OR_ALREADY_CLOSED", "admit_task_rejected", "RUNNING")
        return self._result(BudgetDecision.ADMIT, "TASK_ADMITTED", "admit_task", "RUNNING", admitted=True)

    def _runner_state(self) -> tuple[ControlState | None, str, bool]:
        try:
            snapshot = self.control.status_snapshot()
        except Exception:
            return None, "RUNNER_STATUS_UNAVAILABLE", False
        if not isinstance(snapshot, Mapping):
            return None, "RUNNER_STATE_UNKNOWN", False
        if snapshot.get("run_id") != self.run_id:
            return None, "RUN_ID_MISMATCH", False

        status = snapshot.get("status")
        frozen = snapshot.get("frozen")
        stop_requested = snapshot.get("stop_requested")
        if (
            not isinstance(status, str)
            or status not in self._KNOWN_RUNNER_STATES
            or not isinstance(frozen, bool)
            or not isinstance(stop_requested, bool)
        ):
            return None, "UNKNOWN_RUNNER_STATE", True
        if stop_requested or status == "STOP_REQUESTED":
            return ControlState.STOP_REQUESTED, "", True
        if frozen or status == "FROZEN":
            return ControlState.FROZEN, "", True
        if status == "RUNNING":
            return ControlState.RUNNING, "", True
        return None, "RUNNER_NOT_RUNNING", True

    def _freeze_future_admissions(self) -> str:
        """Call only the cooperative admission freeze; never stop a worker."""

        try:
            snapshot = self.control.freeze()
        except Exception:
            return "freeze_unconfirmed"
        if (
            isinstance(snapshot, Mapping)
            and snapshot.get("run_id") == self.run_id
            and snapshot.get("frozen") is True
        ):
            return "freeze"
        return "freeze_unconfirmed"

    def _record_stop_intent(self) -> str:
        """Record run stop intent through the cooperative control interface."""

        try:
            snapshot = self.control.stop_all()
        except Exception:
            return "stop_intent_unconfirmed"
        if (
            isinstance(snapshot, Mapping)
            and snapshot.get("run_id") == self.run_id
            and snapshot.get("frozen") is True
            and snapshot.get("stop_requested") is True
        ):
            return "stop_intent_recorded"
        return "stop_intent_unconfirmed"

    @staticmethod
    def _monitor_snapshot(observation: Mapping[str, Any] | None) -> MonitorSnapshot | None:
        if not isinstance(observation, Mapping):
            return None
        raw_workers = observation.get("workers")
        if not isinstance(raw_workers, (list, tuple)):
            return None
        workers: list[WorkerResources] = []
        for item in raw_workers:
            if not isinstance(item, Mapping):
                return None
            workers.append(
                WorkerResources(
                    worker_id=item.get("worker_id"),
                    cpu_percent=item.get("cpu_percent"),
                    rss_bytes=item.get("rss_bytes"),
                    memory_bytes=item.get("memory_bytes"),
                )
            )
        try:
            pressure = PressureLevel(observation.get("pressure"))
        except (TypeError, ValueError):
            pressure = PressureLevel.UNKNOWN
        return MonitorSnapshot(
            observed_monotonic=observation.get("observed_monotonic"),
            heartbeat_monotonic=observation.get("heartbeat_monotonic"),
            host_cpu_percent=observation.get("host_cpu_percent"),
            host_memory_used_bytes=observation.get("host_memory_used_bytes"),
            host_memory_total_bytes=observation.get("host_memory_total_bytes"),
            host_swap_used_bytes=observation.get("host_swap_used_bytes"),
            pressure=pressure,
            workers=tuple(workers),
        )

    @staticmethod
    def _process_identity(observation: Mapping[str, Any] | None) -> ProcessIdentity | None:
        if not isinstance(observation, Mapping):
            return None
        return ProcessIdentity(
            pid=observation.get("pid"),
            ppid=observation.get("ppid"),
            creation_time_ns=observation.get("creation_time_ns"),
            run_id=observation.get("run_id"),
            worker_id=observation.get("worker_id"),
            observed_monotonic=observation.get("observed_monotonic"),
        )

    @staticmethod
    def _result(
        decision: BudgetDecision,
        reason: str,
        action: str,
        runner_state: str | None,
        *,
        admitted: bool = False,
    ) -> AdapterResult:
        return AdapterResult(decision, admitted, reason, action, runner_state)
