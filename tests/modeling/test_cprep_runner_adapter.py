"""Synthetic contract tests for the injectable C-Prep Runner adapter."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "python" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from housing_regression.modeling.cprep_safety.budget import BudgetDecision, SafetyBudgetPolicy
from housing_regression.modeling.cprep_safety.control import ControlState
from housing_regression.modeling.cprep_safety.monitor import PressureLevel
from housing_regression.modeling.cprep_safety.process_identity import ProcessIdentity
from housing_regression.modeling.cprep_safety.runner_adapter import CPrepRunnerAdapter


class FakeRunControl:
    """In-memory stand-in matching only the cooperative RunControlState API."""

    def __init__(self, *, run_id="run-a", status="RUNNING", frozen=False, stop_requested=False):
        self.run_id = run_id
        self.status = status
        self.frozen = frozen
        self.stop_requested = stop_requested
        self.calls = []
        self.admitted_tasks = []
        self.reject_next_admission = False

    def status_snapshot(self):
        self.calls.append("status_snapshot")
        return {
            "run_id": self.run_id,
            "status": self.status,
            "frozen": self.frozen,
            "stop_requested": self.stop_requested,
        }

    def admit_task(self, task_id):
        self.calls.append("admit_task")
        if self.reject_next_admission:
            self.reject_next_admission = False
            self.status = "FROZEN"
            self.frozen = True
            return False
        if self.frozen or self.stop_requested:
            return False
        self.admitted_tasks.append(task_id)
        return True

    def freeze(self):
        self.calls.append("freeze")
        self.frozen = True
        if self.status not in {"COMPLETED", "FAILED", "STOPPED"}:
            self.status = "FROZEN"
        return self.status_snapshot()

    def stop_all(self):
        self.calls.append("stop_all")
        self.frozen = True
        self.stop_requested = True
        if self.status not in {"COMPLETED", "FAILED", "STOPPED"}:
            self.status = "STOP_REQUESTED"
        return self.status_snapshot()


class RunnerAdapterTests(unittest.TestCase):
    NOW = 100.0

    def setUp(self):
        self.policy = SafetyBudgetPolicy(
            warning_aggregate_rss_bytes=200,
            stop_aggregate_rss_bytes=300,
            max_runtime_seconds=100.0,
            max_snapshot_age_seconds=5.0,
            max_workers=4,
        )
        self.expected_identity = ProcessIdentity(51, 8, 700, "run-a", "worker-1", 90.0)

    def resource_observation(self, *, pressure=PressureLevel.NORMAL, rss_bytes=100, **overrides):
        observation = {
            "observed_monotonic": 99.0,
            "heartbeat_monotonic": 99.0,
            "host_cpu_percent": 15.0,
            "host_memory_used_bytes": 500,
            "host_memory_total_bytes": 1000,
            "host_swap_used_bytes": 10,
            "pressure": pressure,
            "workers": [
                {
                    "worker_id": "worker-1",
                    "cpu_percent": 10.0,
                    "rss_bytes": rss_bytes,
                    "memory_bytes": rss_bytes,
                }
            ],
        }
        observation.update(overrides)
        return observation

    def identity_observation(self, **overrides):
        observation = {
            "pid": 51,
            "ppid": 8,
            "creation_time_ns": 700,
            "run_id": "run-a",
            "worker_id": "worker-1",
            "observed_monotonic": 99.5,
        }
        observation.update(overrides)
        return observation

    def adapter(self, control):
        return CPrepRunnerAdapter(
            control=control,
            run_id="run-a",
            authorized_worker_ids=frozenset({"worker-1"}),
            policy=self.policy,
        )

    def attempt(self, control, *, resources=Ellipsis, identity=Ellipsis, elapsed=1.0, current=0, requested=1):
        return self.adapter(control).admit_task(
            task_id="task-1",
            resource_observation=self.resource_observation() if resources is Ellipsis else resources,
            expected_identity=self.expected_identity,
            identity_observation=self.identity_observation() if identity is Ellipsis else identity,
            current_workers=current,
            requested_workers=requested,
            now_monotonic=self.NOW,
            elapsed_seconds=elapsed,
        )

    def test_normal_admission_uses_injected_policy_and_control(self):
        control = FakeRunControl()
        result = self.attempt(control)
        self.assertEqual(result.decision, BudgetDecision.ADMIT)
        self.assertTrue(result.admitted)
        self.assertEqual(result.runner_action, "admit_task")
        self.assertEqual(control.admitted_tasks, ["task-1"])
        self.assertEqual(control.calls, ["status_snapshot", "admit_task"])

    def test_warning_and_critical_only_freeze_future_admission(self):
        for pressure in (PressureLevel.WARNING, PressureLevel.CRITICAL):
            with self.subTest(pressure=pressure):
                control = FakeRunControl()
                result = self.attempt(
                    control,
                    resources=self.resource_observation(pressure=pressure, rss_bytes=10),
                    current=1,
                    requested=2,
                )
                self.assertEqual(result.decision, BudgetDecision.FREEZE)
                self.assertFalse(result.admitted)
                self.assertEqual(result.runner_action, "freeze")
                self.assertTrue(control.frozen)
                self.assertFalse(control.stop_requested)
                self.assertEqual(control.admitted_tasks, [])
                self.assertNotIn("stop_all", control.calls)

    def test_warning_and_critical_stop_boundaries_precede_freeze(self):
        cases = (
            (300, 1.0, BudgetDecision.STOP_REQUEST),
            (301, 1.0, BudgetDecision.STOP_REQUEST),
            (10, 100.0, BudgetDecision.STOP_REQUEST),
            (10, 99.0, BudgetDecision.FREEZE),
        )
        for pressure in (PressureLevel.WARNING, PressureLevel.CRITICAL):
            for rss_bytes, elapsed, expected in cases:
                with self.subTest(pressure=pressure, rss_bytes=rss_bytes, elapsed=elapsed):
                    control = FakeRunControl()
                    result = self.attempt(
                        control,
                        resources=self.resource_observation(pressure=pressure, rss_bytes=rss_bytes),
                        elapsed=elapsed,
                        current=1,
                        requested=2,
                    )
                    self.assertEqual(result.decision, expected)
                    self.assertFalse(result.admitted)
                    self.assertEqual(result.runner_action, "stop_intent_recorded" if expected is BudgetDecision.STOP_REQUEST else "freeze")
                    self.assertEqual(control.admitted_tasks, [])
                    if expected is BudgetDecision.STOP_REQUEST:
                        self.assertTrue(control.stop_requested)
                        self.assertTrue(control.frozen)
                        self.assertIn("stop_all", control.calls)
                    else:
                        self.assertTrue(control.frozen)
                        self.assertFalse(control.stop_requested)
                        self.assertNotIn("stop_all", control.calls)
                    self.assertFalse(hasattr(result, "worker_terminated"))

    def test_missing_and_stale_monitor_fail_closed(self):
        stale = self.resource_observation(observed_monotonic=90.0, heartbeat_monotonic=99.0)
        invalid_values = (
            ("nan", self.resource_observation(host_cpu_percent=float("nan"))),
            ("oversized_number", self.resource_observation(host_cpu_percent=10**1000)),
        )
        for name, resources in (("missing", None), ("stale", stale), *invalid_values):
            with self.subTest(resources=name):
                control = FakeRunControl()
                result = self.attempt(control, resources=resources)
                self.assertEqual(result.decision, BudgetDecision.DENY)
                self.assertFalse(result.admitted)
                self.assertIn("freeze", control.calls)
                self.assertEqual(control.admitted_tasks, [])

    def test_pid_reuse_identity_mismatch_stale_and_unauthorized_fail_closed(self):
        identities = (
            None,
            self.identity_observation(creation_time_ns=701),  # PID reuse
            self.identity_observation(pid=52),
            self.identity_observation(ppid=9),
            self.identity_observation(observed_monotonic=90.0),  # stale observation
            self.identity_observation(observed_monotonic=float("nan")),
            self.identity_observation(worker_id="worker-2"),  # unauthorized owner
            self.identity_observation(run_id="run-b"),
            None,
        )
        for identity in identities:
            with self.subTest(identity=identity):
                control = FakeRunControl()
                result = self.attempt(control, identity=identity)
                self.assertEqual(result.decision, BudgetDecision.DENY)
                self.assertFalse(result.admitted)
                self.assertIn("freeze", control.calls)
                self.assertEqual(control.admitted_tasks, [])

    def test_run_mismatch_and_unknown_runner_state_fail_closed(self):
        mismatched = FakeRunControl(run_id="run-b")
        mismatch_result = self.attempt(mismatched)
        self.assertEqual(mismatch_result.decision, BudgetDecision.DENY)
        self.assertEqual(mismatch_result.reason, "RUN_ID_MISMATCH")
        self.assertEqual(mismatched.calls, ["status_snapshot"])

        unknown = FakeRunControl(status="UNRECOGNIZED")
        unknown_result = self.attempt(unknown)
        self.assertEqual(unknown_result.decision, BudgetDecision.DENY)
        self.assertEqual(unknown_result.reason, "UNKNOWN_RUNNER_STATE")
        self.assertTrue(unknown.frozen)
        self.assertEqual(unknown.admitted_tasks, [])

    def test_existing_frozen_or_stop_requested_state_cannot_admit(self):
        frozen = FakeRunControl(status="FROZEN", frozen=True)
        frozen_result = self.attempt(frozen)
        self.assertEqual(frozen_result.decision, BudgetDecision.FREEZE)
        self.assertFalse(frozen_result.admitted)
        self.assertNotIn("admit_task", frozen.calls)

        stopping = FakeRunControl(status="STOP_REQUESTED", frozen=True, stop_requested=True)
        stop_result = self.attempt(stopping)
        self.assertEqual(stop_result.decision, BudgetDecision.STOP_REQUEST)
        self.assertFalse(stop_result.admitted)
        self.assertNotIn("admit_task", stopping.calls)

    def test_atomic_admission_rejection_wins_race(self):
        control = FakeRunControl()
        control.reject_next_admission = True
        result = self.attempt(control)
        self.assertEqual(result.decision, BudgetDecision.DENY)
        self.assertFalse(result.admitted)
        self.assertEqual(result.reason, "ADMISSION_RACE_OR_ALREADY_CLOSED")
        self.assertEqual(control.calls, ["status_snapshot", "admit_task"])
        self.assertEqual(control.admitted_tasks, [])


if __name__ == "__main__":
    unittest.main()
