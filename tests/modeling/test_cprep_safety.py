"""Pure Mock tests for Issue #30 C-PREP-02 safety foundations."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "python" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from housing_regression.modeling.cprep_safety.budget import (
    BudgetDecision,
    SafetyBudgetPolicy,
    decide_admission,
    evaluate_budget,
)
from housing_regression.modeling.cprep_safety.control import (
    ControlEvent,
    ControlState,
    InvalidControlTransition,
    admission_is_open,
    transition,
)
from housing_regression.modeling.cprep_safety.monitor import (
    MonitorAssessment,
    MonitorSnapshot,
    PressureLevel,
    WorkerResources,
    assess_snapshot,
)
from housing_regression.modeling.cprep_safety.process_identity import (
    ProcessIdentity,
    check_process_identity,
)


class MonitorTests(unittest.TestCase):
    def snapshot(self, **overrides):
        values = {
            "observed_monotonic": 10.0,
            "heartbeat_monotonic": 10.0,
            "host_cpu_percent": 30.0,
            "host_memory_used_bytes": 500,
            "host_memory_total_bytes": 1000,
            "host_swap_used_bytes": 20,
            "pressure": PressureLevel.NORMAL,
            "workers": (
                WorkerResources("w1", 10.0, 100, 120),
                WorkerResources("w2", 15.0, 200, 220),
            ),
        }
        values.update(overrides)
        return MonitorSnapshot(**values)

    def test_aggregates_worker_rss_and_cpu_with_explicit_units(self):
        result = assess_snapshot(self.snapshot(), now_monotonic=12.0, max_age_seconds=5.0)
        self.assertTrue(result.valid)
        self.assertEqual(result.aggregate_worker_rss_bytes, 300)
        self.assertEqual(result.aggregate_worker_cpu_percent, 25.0)
        self.assertEqual(result.age_seconds, 2.0)

    def test_missing_stale_unknown_or_invalid_monitor_data_fails_closed(self):
        self.assertEqual(
            assess_snapshot(None, now_monotonic=12.0, max_age_seconds=5.0).reason,
            "MISSING_SNAPSHOT",
        )
        stale = assess_snapshot(
            self.snapshot(heartbeat_monotonic=1.0), now_monotonic=12.0, max_age_seconds=5.0
        )
        self.assertEqual(stale.reason, "STALE_HEARTBEAT")
        stale_snapshot = assess_snapshot(
            self.snapshot(observed_monotonic=1.0), now_monotonic=12.0, max_age_seconds=5.0
        )
        self.assertEqual(stale_snapshot.reason, "STALE_HEARTBEAT")
        unknown = assess_snapshot(
            self.snapshot(pressure=PressureLevel.UNKNOWN), now_monotonic=12.0, max_age_seconds=5.0
        )
        self.assertEqual(unknown.reason, "UNKNOWN_MEMORY_PRESSURE")
        missing_worker_rss = assess_snapshot(
            self.snapshot(workers=(WorkerResources("w1", 10.0, None, 100),)),
            now_monotonic=12.0,
            max_age_seconds=5.0,
        )
        self.assertEqual(missing_worker_rss.reason, "MISSING_OR_INVALID_WORKER_RSS")
        future = assess_snapshot(
            self.snapshot(heartbeat_monotonic=13.0), now_monotonic=12.0, max_age_seconds=5.0
        )
        self.assertEqual(future.reason, "INVALID_MONOTONIC_TIMESTAMP")


class ProcessIdentityTests(unittest.TestCase):
    def setUp(self):
        self.expected = ProcessIdentity(42, 7, 1000, "run-a", "worker-1", 50.0)
        self.authorized = frozenset({"worker-1"})
        self.now_monotonic = 100.0

    def identity(self, *, pid=42, ppid=7, created=1000, run="run-a", worker="worker-1", observed_at=100.0):
        return ProcessIdentity(pid, ppid, created, run, worker, observed_at)

    def check(self, observed, expected=None, run_id="run-a", workers=None, now=None, max_age=5.0):
        return check_process_identity(
            expected or self.expected,
            observed,
            authorized_run_id=run_id,
            authorized_worker_ids=workers or self.authorized,
            now_monotonic=self.now_monotonic if now is None else now,
            max_age_seconds=max_age,
        )

    def test_fresh_identity_is_authorized_including_budget_boundary(self):
        self.assertTrue(self.check(self.identity()).authorized)
        boundary = self.identity(observed_at=95.0)
        self.assertTrue(self.check(boundary).authorized)

    def test_stale_missing_invalid_and_clock_skew_observations_are_denied(self):
        stale = self.identity(observed_at=94.9)
        self.assertEqual(self.check(stale).reason, "OBSERVATION_STALE")
        self.assertEqual(self.check(self.identity(observed_at=None)).reason, "OBSERVATION_TIME_MISSING")
        self.assertEqual(self.check(self.identity(observed_at=float("nan"))).reason, "OBSERVATION_TIME_INVALID")
        self.assertEqual(self.check(self.identity(observed_at=float("inf"))).reason, "OBSERVATION_TIME_INVALID")
        self.assertEqual(self.check(self.identity(observed_at="bad")).reason, "OBSERVATION_TIME_INVALID")
        self.assertEqual(self.check(self.identity(observed_at=100.1)).reason, "OBSERVATION_TIME_IN_FUTURE")
        self.assertEqual(self.check(self.identity(), now=float("nan")).reason, "INVALID_FRESHNESS_POLICY")
        self.assertEqual(self.check(self.identity(), max_age=0).reason, "INVALID_FRESHNESS_POLICY")
        self.assertEqual(
            self.check(self.identity(), expected=self.identity(observed_at=None)).reason,
            "EXPECTED_OBSERVATION_TIME_MISSING",
        )

    def test_pid_reuse_mismatch_and_missing_identity_are_denied(self):
        reused = self.identity(created=1001)
        self.assertEqual(self.check(reused).reason, "CREATION_IDENTITY_MISMATCH")
        wrong_pid = self.identity(pid=43)
        self.assertEqual(self.check(wrong_pid).reason, "PID_MISMATCH")
        self.assertEqual(self.check(None).reason, "IDENTITY_MISSING")

    def test_unowned_run_or_worker_is_denied(self):
        fresh = self.identity()
        self.assertEqual(self.check(fresh, run_id="run-b").reason, "TARGET_NOT_AUTHORIZED")
        stranger = self.identity(worker="worker-2")
        self.assertEqual(self.check(stranger).reason, "OBSERVED_OWNER_NOT_AUTHORIZED")


class ControlTests(unittest.TestCase):
    def test_normal_freeze_stop_and_lost_monitor_transitions(self):
        state = transition(ControlState.READY, ControlEvent.START)
        self.assertEqual(state, ControlState.RUNNING)
        state = transition(state, ControlEvent.WARN)
        self.assertEqual(state, ControlState.WARNING)
        self.assertFalse(admission_is_open(state))
        state = transition(state, ControlEvent.FREEZE)
        self.assertEqual(state, ControlState.FROZEN)
        state = transition(state, ControlEvent.REQUEST_STOP)
        self.assertEqual(state, ControlState.STOP_REQUESTED)
        self.assertEqual(transition(ControlState.RUNNING, ControlEvent.MONITOR_MISSING), ControlState.MONITOR_LOST)
        self.assertEqual(
            transition(ControlState.MONITOR_LOST, ControlEvent.MONITOR_RESTORED), ControlState.FROZEN
        )
        self.assertEqual(transition(ControlState.FROZEN, ControlEvent.REQUEST_STOP), ControlState.STOP_REQUESTED)

    def test_illegal_transitions_are_rejected(self):
        with self.assertRaises(InvalidControlTransition):
            transition(ControlState.READY, ControlEvent.REQUEST_STOP)
        with self.assertRaises(InvalidControlTransition):
            transition(ControlState.STOP_REQUESTED, ControlEvent.MONITOR_RESTORED)


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.policy = SafetyBudgetPolicy(
            warning_aggregate_rss_bytes=200,
            stop_aggregate_rss_bytes=300,
            max_runtime_seconds=100.0,
            max_snapshot_age_seconds=5.0,
            max_workers=4,
        )
        self.good = MonitorAssessment(True, None, 1.0, 100, 20.0, PressureLevel.NORMAL)

    def test_budget_warning_stop_timeout_and_unknown_monitor(self):
        self.assertEqual(
            evaluate_budget(self.good, state=ControlState.RUNNING, elapsed_seconds=1.0, policy=self.policy),
            BudgetDecision.ADMIT,
        )
        warning = MonitorAssessment(True, None, 1.0, 200, 20.0, PressureLevel.NORMAL)
        self.assertEqual(
            evaluate_budget(warning, state=ControlState.RUNNING, elapsed_seconds=1.0, policy=self.policy),
            BudgetDecision.FREEZE,
        )
        stopped = MonitorAssessment(True, None, 1.0, 300, 20.0, PressureLevel.NORMAL)
        self.assertEqual(
            evaluate_budget(stopped, state=ControlState.RUNNING, elapsed_seconds=1.0, policy=self.policy),
            BudgetDecision.STOP_REQUEST,
        )
        self.assertEqual(
            evaluate_budget(self.good, state=ControlState.RUNNING, elapsed_seconds=100.0, policy=self.policy),
            BudgetDecision.STOP_REQUEST,
        )
        unknown = MonitorAssessment(False, "LOST", None, None, None, None)
        self.assertEqual(
            evaluate_budget(unknown, state=ControlState.RUNNING, elapsed_seconds=1.0, policy=self.policy),
            BudgetDecision.DENY,
        )

    def test_admission_is_incremental_bounded_and_fail_closed(self):
        decision = decide_admission(
            current_workers=0,
            requested_workers=1,
            state=ControlState.RUNNING,
            assessment=self.good,
            elapsed_seconds=1.0,
            policy=self.policy,
        )
        self.assertTrue(decision.allowed)
        for current, requested, reason in (
            (0, 2, "ADMISSION_MUST_INCREASE_BY_ONE"),
            (3, 5, "WORKER_LIMIT_EXCEEDED"),
        ):
            result = decide_admission(
                current_workers=current,
                requested_workers=requested,
                state=ControlState.RUNNING,
                assessment=self.good,
                elapsed_seconds=1.0,
                policy=self.policy,
            )
            self.assertFalse(result.allowed)
            self.assertEqual(result.reason, reason)
        frozen = decide_admission(
            current_workers=1,
            requested_workers=2,
            state=ControlState.FROZEN,
            assessment=self.good,
            elapsed_seconds=1.0,
            policy=self.policy,
        )
        self.assertFalse(frozen.allowed)

    def test_pressure_reaches_budget_and_blocks_expansion_conservatively(self):
        for pressure, expected_decision in (
            (PressureLevel.WARNING, BudgetDecision.FREEZE),
            (PressureLevel.CRITICAL, BudgetDecision.FREEZE),
        ):
            snapshot = MonitorSnapshot(
                10.0,
                10.0,
                1.0,
                100,
                1000,
                0,
                pressure,
                (WorkerResources("w1", 1.0, 10, 10),),
            )
            assessment = assess_snapshot(snapshot, now_monotonic=10.0, max_age_seconds=2.0)
            self.assertTrue(assessment.valid)
            self.assertEqual(assessment.pressure, pressure)
            self.assertEqual(
                evaluate_budget(
                    assessment,
                    state=ControlState.RUNNING,
                    elapsed_seconds=1.0,
                    policy=self.policy,
                ),
                expected_decision,
            )
            admission = decide_admission(
                current_workers=1,
                requested_workers=2,
                state=ControlState.RUNNING,
                assessment=assessment,
                elapsed_seconds=1.0,
                policy=self.policy,
            )
            self.assertFalse(admission.allowed)
            self.assertEqual(admission.reason, "FREEZE")

        for pressure in (None, PressureLevel.UNKNOWN, "critical"):
            assessment = MonitorAssessment(True, None, 1.0, 10, 1.0, pressure)
            self.assertEqual(
                evaluate_budget(
                    assessment,
                    state=ControlState.RUNNING,
                    elapsed_seconds=1.0,
                    policy=self.policy,
                ),
                BudgetDecision.DENY,
            )

    def test_pressure_thresholds_are_inclusive_and_missing_metrics_deny(self):
        at_warning = MonitorAssessment(True, None, 1.0, 200, 1.0, PressureLevel.NORMAL)
        at_stop = MonitorAssessment(True, None, 1.0, 300, 1.0, PressureLevel.NORMAL)
        self.assertEqual(
            evaluate_budget(at_warning, state=ControlState.RUNNING, elapsed_seconds=1.0, policy=self.policy),
            BudgetDecision.FREEZE,
        )
        self.assertEqual(
            evaluate_budget(at_stop, state=ControlState.RUNNING, elapsed_seconds=1.0, policy=self.policy),
            BudgetDecision.STOP_REQUEST,
        )

        stale = assess_snapshot(
            MonitorSnapshot(1.0, 1.0, 10.0, 10, 100, 0, PressureLevel.NORMAL),
            now_monotonic=10.0,
            max_age_seconds=2.0,
        )
        missing = assess_snapshot(None, now_monotonic=10.0, max_age_seconds=2.0)
        invalid_pressure = assess_snapshot(
            MonitorSnapshot(10.0, 10.0, 10.0, 10, 100, 0, "not-a-level"),
            now_monotonic=10.0,
            max_age_seconds=2.0,
        )
        invalid_units = assess_snapshot(
            MonitorSnapshot(
                10.0,
                10.0,
                10.0,
                10,
                100,
                0,
                PressureLevel.NORMAL,
                (WorkerResources("w1", 1.0, 1.5, 2),),
            ),
            now_monotonic=10.0,
            max_age_seconds=2.0,
        )
        for assessment in (stale, missing, invalid_pressure, invalid_units):
            self.assertEqual(
                evaluate_budget(
                    assessment,
                    state=ControlState.RUNNING,
                    elapsed_seconds=1.0,
                    policy=self.policy,
                ),
                BudgetDecision.DENY,
            )


if __name__ == "__main__":
    unittest.main()
