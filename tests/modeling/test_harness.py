"""Bounded subprocess test execution harness for P4-B-A with Windows Job Object kill-on-close."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import unittest
from ctypes import wintypes
from pathlib import Path

# Windows Job Object Win32 Constants & Structures
JobObjectExtendedLimitInformation = 9
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
        ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryLimit", ctypes.c_size_t),
        ("PeakJobMemoryLimit", ctypes.c_size_t),
    ]


def create_kill_on_close_job_object() -> int:
    """Create a Windows Job Object configured with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE."""
    if os.name != "nt":
        return 0
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise RuntimeError(f"Failed to create Job Object: Windows error {ctypes.get_last_error()}")

    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    success = kernel32.SetInformationJobObject(
        job,
        JobObjectExtendedLimitInformation,
        ctypes.byref(info),
        ctypes.sizeof(info),
    )
    if not success:
        kernel32.CloseHandle(job)
        raise RuntimeError(f"Failed to set Job Object info: Windows error {ctypes.get_last_error()}")
    return job


def assign_process_to_job(job_handle: int, process_handle: int) -> None:
    """Assign a Windows process handle to a Job Object."""
    if os.name != "nt" or not job_handle:
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    success = kernel32.AssignProcessToJobObject(job_handle, process_handle)
    if not success:
        raise RuntimeError(f"Failed to assign process to Job Object: Windows error {ctypes.get_last_error()}")


def close_job_object(job_handle: int) -> None:
    """Close a Windows Job Object handle (terminating all member processes if kill-on-close)."""
    if os.name != "nt" or not job_handle:
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle(job_handle)


def run_test_in_bounded_subprocess(
    test_module: str,
    test_case: str,
    timeout_seconds: float = 30.0,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess:
    """Run a specific test case in an isolated subprocess with hard kill on timeout via Job Object."""
    python_exe = sys.executable
    cmd = [
        python_exe,
        "-m",
        "unittest",
        f"{test_module}.{test_case}",
        "-v",
    ]

    job_handle = create_kill_on_close_job_object() if os.name == "nt" else 0

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if job_handle:
            # On Windows, proc._handle is the process handle
            try:
                assign_process_to_job(job_handle, proc._handle)
            except Exception as exc:
                proc.kill()
                raise RuntimeError(f"Job Object assignment failed: {exc}") from exc

        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=proc.returncode,
                stdout=stdout,
                stderr=stderr,
            )
        except subprocess.TimeoutExpired as exc:
            proc.kill()
            if job_handle:
                close_job_object(job_handle)
                job_handle = 0
            stdout, stderr = proc.communicate()
            raise TimeoutError(
                f"Test {test_module}.{test_case} exceeded bounded timeout {timeout_seconds}s and was terminated.\n"
                f"Stdout: {stdout}\nStderr: {stderr}"
            ) from exc

    finally:
        if job_handle:
            close_job_object(job_handle)
