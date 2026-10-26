"""Mockable resource snapshots and fail-closed freshness assessment."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


class PressureLevel(str, Enum):
    """Caller-supplied pressure category; UNKNOWN is never treated as safe."""

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class WorkerResources:
    """One worker's measurements, using percent and byte units."""

    worker_id: str
    cpu_percent: float | None
    rss_bytes: int | None
    memory_bytes: int | None


@dataclass(frozen=True)
class MonitorSnapshot:
    """A supplied snapshot; timestamps are monotonic seconds, sizes are bytes."""

    observed_monotonic: float
    heartbeat_monotonic: float
    host_cpu_percent: float | None
    host_memory_used_bytes: int | None
    host_memory_total_bytes: int | None
    host_swap_used_bytes: int | None
    pressure: PressureLevel
    workers: tuple[WorkerResources, ...] = ()


@dataclass(frozen=True)
class MonitorAssessment:
    """Validated aggregate values, or an explicit fail-closed reason."""

    valid: bool
    reason: str | None
    age_seconds: float | None
    aggregate_worker_rss_bytes: int | None
    aggregate_worker_cpu_percent: float | None


def _valid_percent(value: float | None) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0 <= value <= 100
    )


def _valid_nonnegative_int(value: int | None) -> bool:
    return value is not None and not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def assess_snapshot(
    snapshot: MonitorSnapshot | None,
    *,
    now_monotonic: float,
    max_age_seconds: float,
) -> MonitorAssessment:
    """Validate freshness and required measurements without reading the host."""

    invalid = MonitorAssessment(False, "MISSING_SNAPSHOT", None, None, None)
    if snapshot is None:
        return invalid
    if (
        not _finite_number(now_monotonic)
        or not _finite_number(max_age_seconds)
        or max_age_seconds <= 0
    ):
        return MonitorAssessment(False, "INVALID_CLOCK_OR_FRESHNESS_POLICY", None, None, None)
    if (
        not _finite_number(snapshot.observed_monotonic)
        or not _finite_number(snapshot.heartbeat_monotonic)
        or snapshot.observed_monotonic > now_monotonic
        or snapshot.heartbeat_monotonic > now_monotonic
    ):
        return MonitorAssessment(False, "INVALID_MONOTONIC_TIMESTAMP", None, None, None)

    heartbeat_age = now_monotonic - snapshot.heartbeat_monotonic
    snapshot_age = now_monotonic - snapshot.observed_monotonic
    age = max(heartbeat_age, snapshot_age)
    if heartbeat_age > max_age_seconds or snapshot_age > max_age_seconds:
        return MonitorAssessment(False, "STALE_HEARTBEAT", age, None, None)
    if not _valid_percent(snapshot.host_cpu_percent):
        return MonitorAssessment(False, "MISSING_OR_INVALID_HOST_CPU", age, None, None)
    if not _valid_nonnegative_int(snapshot.host_memory_used_bytes):
        return MonitorAssessment(False, "MISSING_OR_INVALID_HOST_MEMORY_USED", age, None, None)
    if not _valid_nonnegative_int(snapshot.host_memory_total_bytes) or snapshot.host_memory_total_bytes == 0:
        return MonitorAssessment(False, "MISSING_OR_INVALID_HOST_MEMORY_TOTAL", age, None, None)
    if snapshot.host_memory_used_bytes > snapshot.host_memory_total_bytes:
        return MonitorAssessment(False, "HOST_MEMORY_EXCEEDS_TOTAL", age, None, None)
    if not _valid_nonnegative_int(snapshot.host_swap_used_bytes):
        return MonitorAssessment(False, "MISSING_OR_INVALID_HOST_SWAP", age, None, None)
    if not isinstance(snapshot.pressure, PressureLevel) or snapshot.pressure is PressureLevel.UNKNOWN:
        return MonitorAssessment(False, "UNKNOWN_MEMORY_PRESSURE", age, None, None)
    if not isinstance(snapshot.workers, tuple) or any(
        not isinstance(worker, WorkerResources) for worker in snapshot.workers
    ):
        return MonitorAssessment(False, "MISSING_OR_INVALID_WORKER_SNAPSHOT", age, None, None)

    worker_ids: set[str] = set()
    worker_rss = 0
    worker_cpu = 0.0
    for worker in snapshot.workers:
        if not isinstance(worker.worker_id, str) or not worker.worker_id.strip() or worker.worker_id in worker_ids:
            return MonitorAssessment(False, "MISSING_OR_DUPLICATE_WORKER_ID", age, None, None)
        worker_ids.add(worker.worker_id)
        if not _valid_percent(worker.cpu_percent):
            return MonitorAssessment(False, "MISSING_OR_INVALID_WORKER_CPU", age, None, None)
        if not _valid_nonnegative_int(worker.rss_bytes):
            return MonitorAssessment(False, "MISSING_OR_INVALID_WORKER_RSS", age, None, None)
        if not _valid_nonnegative_int(worker.memory_bytes):
            return MonitorAssessment(False, "MISSING_OR_INVALID_WORKER_MEMORY", age, None, None)
        worker_rss += worker.rss_bytes
        worker_cpu += worker.cpu_percent

    return MonitorAssessment(True, None, age, worker_rss, worker_cpu)
