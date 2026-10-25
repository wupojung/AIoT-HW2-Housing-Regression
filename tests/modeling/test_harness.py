"""Bounded subprocess test execution harness for P4-B-A with Windows Job Object kill-on-close."""

from __future__ import annotations

import os
import math
import subprocess
import sys
from pathlib import Path

from housing_regression.modeling.p4b_job import (
    assign_process_to_job,
    close_job_object,
    create_kill_on_close_job_object,
)


def run_test_in_bounded_subprocess(
    test_module: str,
    test_case: str,
    timeout_seconds: float = 30.0,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess:
    """Run a specific test case in an isolated subprocess with hard kill on timeout via Job Object."""
    if isinstance(timeout_seconds, bool) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0 or timeout_seconds > 30:
        raise ValueError("Acceptance test timeout must be finite, positive, and at most 30 seconds.")
    if os.name != "nt":
        raise RuntimeError("FAIL_CLOSED: bounded acceptance tests require a Windows Job Object.")
    unittest_args = [f"{test_module}.{test_case}", "-v"]
    script = (
        "import runpy,sys; sys.stdin.readline(); "
        f"sys.argv=['unittest', {unittest_args[0]!r}, '-v']; "
        "runpy.run_module('unittest', run_name='__main__')"
    )
    cmd = [sys.executable, "-c", script]
    job_handle = create_kill_on_close_job_object()
    proc = None

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if job_handle:
            # On Windows, proc._handle is the process handle
            try:
                assign_process_to_job(job_handle, proc._handle)
            except Exception:
                proc.kill()
                proc.communicate(timeout=2.0)
                close_job_object(job_handle)
                job_handle = 0
                raise RuntimeError("FAIL_CLOSED: Job Object assignment failed.") from None

        # The child blocks on stdin until it is safely inside the kill-on-close Job.
        assert proc.stdin is not None
        proc.stdin.write("\n")
        proc.stdin.flush()
        proc.stdin.close()

        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=proc.returncode,
                stdout=stdout,
                stderr=stderr,
            )
        except subprocess.TimeoutExpired as exc:
            if job_handle:
                close_job_object(job_handle)
                job_handle = 0
            proc.kill()
            stdout, stderr = proc.communicate(timeout=2.0)
            raise TimeoutError(
                f"Test {test_module}.{test_case} exceeded bounded timeout {timeout_seconds}s and was terminated.\n"
                f"Stdout: {stdout}\nStderr: {stderr}"
            ) from exc

    finally:
        try:
            if job_handle:
                close_job_object(job_handle)
        finally:
            if proc is not None and proc.poll() is None:
                proc.kill()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    raise RuntimeError("FAIL_CLOSED: bounded child cleanup could not be verified.") from None
