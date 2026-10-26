"""Pure safe-control state transitions; no process action is performed."""

from __future__ import annotations

from enum import Enum


class ControlState(str, Enum):
    READY = "ready"
    RUNNING = "running"
    WARNING = "warning"
    FROZEN = "frozen"
    STOP_REQUESTED = "stop_requested"
    MONITOR_LOST = "monitor_lost"


class ControlEvent(str, Enum):
    START = "start"
    WARN = "warn"
    FREEZE = "freeze"
    REQUEST_STOP = "request_stop"
    MONITOR_MISSING = "monitor_missing"
    MONITOR_RESTORED = "monitor_restored"


class InvalidControlTransition(ValueError):
    """Raised when a state/event pair is outside the declared state machine."""


_TRANSITIONS: dict[tuple[ControlState, ControlEvent], ControlState] = {
    (ControlState.READY, ControlEvent.START): ControlState.RUNNING,
    (ControlState.RUNNING, ControlEvent.WARN): ControlState.WARNING,
    (ControlState.RUNNING, ControlEvent.FREEZE): ControlState.FROZEN,
    (ControlState.WARNING, ControlEvent.FREEZE): ControlState.FROZEN,
    (ControlState.RUNNING, ControlEvent.REQUEST_STOP): ControlState.STOP_REQUESTED,
    (ControlState.WARNING, ControlEvent.REQUEST_STOP): ControlState.STOP_REQUESTED,
    (ControlState.FROZEN, ControlEvent.REQUEST_STOP): ControlState.STOP_REQUESTED,
    (ControlState.MONITOR_LOST, ControlEvent.REQUEST_STOP): ControlState.STOP_REQUESTED,
    (ControlState.READY, ControlEvent.MONITOR_MISSING): ControlState.MONITOR_LOST,
    (ControlState.RUNNING, ControlEvent.MONITOR_MISSING): ControlState.MONITOR_LOST,
    (ControlState.WARNING, ControlEvent.MONITOR_MISSING): ControlState.MONITOR_LOST,
    (ControlState.FROZEN, ControlEvent.MONITOR_MISSING): ControlState.MONITOR_LOST,
    (ControlState.MONITOR_LOST, ControlEvent.MONITOR_RESTORED): ControlState.FROZEN,
}


def transition(state: ControlState, event: ControlEvent) -> ControlState:
    """Return the next state; stop requests do not claim process termination."""

    if not isinstance(state, ControlState) or not isinstance(event, ControlEvent):
        raise InvalidControlTransition("state and event must be declared enum values")
    try:
        return _TRANSITIONS[(state, event)]
    except KeyError as exc:
        raise InvalidControlTransition(f"invalid transition: {state.value} + {event.value}") from exc


def admission_is_open(state: ControlState) -> bool:
    """Only RUNNING admits work; warning, freeze, and unknown monitor close it."""

    return state is ControlState.RUNNING
