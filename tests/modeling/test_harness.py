"""Bounded subprocess test execution harness for P4-B-A."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


def run_test_in_bounded_subprocess(
    test_module: str,
    test_case: str,
    timeout_seconds: float = 15.0,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess:
    """Run a specific test case in an isolated subprocess with hard kill on timeout."""
    python_exe = sys.executable
    cmd = [
        python_exe,
        "-m",
        "unittest",
        f"{test_module}.{test_case}",
        "-v",
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return proc
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(
            f"Test {test_module}.{test_case} exceeded bounded timeout {timeout_seconds}s and was terminated."
        ) from exc
