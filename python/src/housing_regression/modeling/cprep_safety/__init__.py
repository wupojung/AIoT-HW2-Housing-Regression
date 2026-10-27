"""Pure safety-policy primitives for the C-Prep phase.

This package contains value objects and deterministic decisions only. It does
not inspect, start, signal, or terminate operating-system processes.
"""

from .budget import (
    AdmissionDecision,
    BudgetDecision,
    SafetyBudgetPolicy,
    decide_admission,
    evaluate_budget,
)
from .control import ControlEvent, ControlState, InvalidControlTransition, transition
from .monitor import (
    MonitorAssessment,
    MonitorSnapshot,
    PressureLevel,
    WorkerResources,
    assess_snapshot,
)
from .process_identity import (
    IdentityCheck,
    ProcessIdentity,
    check_process_identity,
)

__all__ = [
    "AdmissionDecision",
    "BudgetDecision",
    "ControlEvent",
    "ControlState",
    "IdentityCheck",
    "InvalidControlTransition",
    "MonitorAssessment",
    "MonitorSnapshot",
    "PressureLevel",
    "ProcessIdentity",
    "SafetyBudgetPolicy",
    "WorkerResources",
    "assess_snapshot",
    "check_process_identity",
    "decide_admission",
    "evaluate_budget",
    "transition",
]
