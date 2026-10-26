"""Pure identity comparisons for a caller-supplied process observation.

No operating-system lookup is implemented here. A future integration must
revalidate identity before each control request and pass the observation in.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    ppid: int
    creation_time_ns: int
    run_id: str
    worker_id: str


@dataclass(frozen=True)
class IdentityCheck:
    authorized: bool
    reason: str


def check_process_identity(
    expected: ProcessIdentity | None,
    observed: ProcessIdentity | None,
    *,
    authorized_run_id: str,
    authorized_worker_ids: frozenset[str],
) -> IdentityCheck:
    """Fail closed on missing, reused, stale, or unowned process identity."""

    if expected is None or observed is None:
        return IdentityCheck(False, "IDENTITY_MISSING")
    if not _valid_identity_fields(expected):
        return IdentityCheck(False, "EXPECTED_IDENTITY_INVALID")
    if not _valid_identity_fields(observed):
        return IdentityCheck(False, "OBSERVED_IDENTITY_INVALID")
    if not expected.run_id or not expected.worker_id or not observed.run_id or not observed.worker_id:
        return IdentityCheck(False, "IDENTITY_OWNERSHIP_MISSING")
    if expected.run_id != authorized_run_id or expected.worker_id not in authorized_worker_ids:
        return IdentityCheck(False, "TARGET_NOT_AUTHORIZED")
    if observed.run_id != authorized_run_id or observed.worker_id not in authorized_worker_ids:
        return IdentityCheck(False, "OBSERVED_OWNER_NOT_AUTHORIZED")
    if observed.pid != expected.pid:
        return IdentityCheck(False, "PID_MISMATCH")
    if observed.creation_time_ns != expected.creation_time_ns:
        return IdentityCheck(False, "CREATION_IDENTITY_MISMATCH")
    if observed.ppid != expected.ppid:
        return IdentityCheck(False, "PARENT_IDENTITY_MISMATCH")
    if observed.run_id != expected.run_id or observed.worker_id != expected.worker_id:
        return IdentityCheck(False, "WORKER_OWNERSHIP_MISMATCH")
    return IdentityCheck(True, "IDENTITY_VERIFIED")


def _valid_identity_fields(identity: ProcessIdentity) -> bool:
    numeric_fields = (identity.pid, identity.ppid, identity.creation_time_ns)
    return (
        all(isinstance(value, int) and not isinstance(value, bool) for value in numeric_fields)
        and isinstance(identity.run_id, str)
        and isinstance(identity.worker_id, str)
        and identity.pid > 0
        and identity.ppid >= 0
        and identity.creation_time_ns > 0
    )
