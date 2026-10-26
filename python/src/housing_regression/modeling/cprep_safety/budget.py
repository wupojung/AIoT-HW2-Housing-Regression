"""Configurable safety budgets and pure admission decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .control import ControlState, admission_is_open
from .monitor import MonitorAssessment, PressureLevel


@dataclass(frozen=True)
class SafetyBudgetPolicy:
    """Byte-based thresholds and finite runtime/admission limits.

    The default 20/24 GiB figures are policy thresholds only. They are not an
    operating-system memory cap or a claim about the current host.
    """

    warning_aggregate_rss_bytes: int = 20 * 1024**3
    stop_aggregate_rss_bytes: int = 24 * 1024**3
    max_runtime_seconds: float = 90 * 60
    max_snapshot_age_seconds: float = 10.0
    max_workers: int = 4

    def __post_init__(self) -> None:
        if (
            isinstance(self.warning_aggregate_rss_bytes, bool)
            or isinstance(self.stop_aggregate_rss_bytes, bool)
            or not isinstance(self.warning_aggregate_rss_bytes, int)
            or not isinstance(self.stop_aggregate_rss_bytes, int)
            or self.warning_aggregate_rss_bytes < 0
            or self.stop_aggregate_rss_bytes <= self.warning_aggregate_rss_bytes
        ):
            raise ValueError("RSS thresholds must be nonnegative and stop must exceed warning")
        if (
            isinstance(self.max_runtime_seconds, bool)
            or not isinstance(self.max_runtime_seconds, (int, float))
            or not math.isfinite(self.max_runtime_seconds)
            or self.max_runtime_seconds <= 0
        ):
            raise ValueError("max_runtime_seconds must be finite and positive")
        if (
            isinstance(self.max_snapshot_age_seconds, bool)
            or not isinstance(self.max_snapshot_age_seconds, (int, float))
            or not math.isfinite(self.max_snapshot_age_seconds)
            or self.max_snapshot_age_seconds <= 0
        ):
            raise ValueError("max_snapshot_age_seconds must be finite and positive")
        if (
            isinstance(self.max_workers, bool)
            or not isinstance(self.max_workers, int)
            or not 1 <= self.max_workers <= 4
        ):
            raise ValueError("max_workers must be between one and four")


class BudgetDecision(str, Enum):
    ADMIT = "admit"
    FREEZE = "freeze"
    STOP_REQUEST = "stop_request"
    DENY = "deny"


@dataclass(frozen=True)
class AdmissionDecision:
    allowed: bool
    reason: str


def evaluate_budget(
    assessment: MonitorAssessment,
    *,
    state: ControlState,
    elapsed_seconds: float,
    policy: SafetyBudgetPolicy,
) -> BudgetDecision:
    """Return a recommendation only; never changes controller/process state."""

    if isinstance(elapsed_seconds, bool) or not isinstance(elapsed_seconds, (int, float)):
        return BudgetDecision.DENY
    if not math.isfinite(elapsed_seconds) or elapsed_seconds < 0:
        return BudgetDecision.DENY
    if state is ControlState.STOP_REQUESTED:
        return BudgetDecision.STOP_REQUEST
    if (
        not assessment.valid
        or assessment.aggregate_worker_rss_bytes is None
        or isinstance(assessment.aggregate_worker_rss_bytes, bool)
        or not isinstance(assessment.aggregate_worker_rss_bytes, int)
        or assessment.aggregate_worker_rss_bytes < 0
    ):
        return BudgetDecision.DENY
    if (
        assessment.age_seconds is None
        or isinstance(assessment.age_seconds, bool)
        or not isinstance(assessment.age_seconds, (int, float))
        or not math.isfinite(assessment.age_seconds)
        or assessment.age_seconds < 0
        or assessment.age_seconds > policy.max_snapshot_age_seconds
    ):
        return BudgetDecision.DENY
    if not isinstance(assessment.pressure, PressureLevel) or assessment.pressure is PressureLevel.UNKNOWN:
        return BudgetDecision.DENY
    # A WARNING freezes worker admission; CRITICAL does the same even below
    # the RSS thresholds. Neither decision claims that a running worker stopped.
    if assessment.pressure in (PressureLevel.WARNING, PressureLevel.CRITICAL):
        return BudgetDecision.FREEZE
    if elapsed_seconds >= policy.max_runtime_seconds:
        return BudgetDecision.STOP_REQUEST
    if assessment.aggregate_worker_rss_bytes >= policy.stop_aggregate_rss_bytes:
        return BudgetDecision.STOP_REQUEST
    if assessment.aggregate_worker_rss_bytes >= policy.warning_aggregate_rss_bytes:
        return BudgetDecision.FREEZE
    if not admission_is_open(state):
        return BudgetDecision.DENY
    return BudgetDecision.ADMIT


def decide_admission(
    *,
    current_workers: int,
    requested_workers: int,
    state: ControlState,
    assessment: MonitorAssessment,
    elapsed_seconds: float,
    policy: SafetyBudgetPolicy,
) -> AdmissionDecision:
    """Authorize exactly one staged count increase; never starts a worker."""

    if (
        isinstance(current_workers, bool)
        or isinstance(requested_workers, bool)
        or not isinstance(current_workers, int)
        or not isinstance(requested_workers, int)
    ):
        return AdmissionDecision(False, "INVALID_WORKER_COUNT")
    if not 0 <= current_workers <= policy.max_workers or not 0 <= requested_workers <= policy.max_workers:
        return AdmissionDecision(False, "WORKER_LIMIT_EXCEEDED")
    if requested_workers != current_workers + 1:
        return AdmissionDecision(False, "ADMISSION_MUST_INCREASE_BY_ONE")
    budget = evaluate_budget(
        assessment,
        state=state,
        elapsed_seconds=elapsed_seconds,
        policy=policy,
    )
    if budget is not BudgetDecision.ADMIT:
        return AdmissionDecision(False, budget.value.upper())
    return AdmissionDecision(True, "NEXT_STAGE_ALLOWED")
