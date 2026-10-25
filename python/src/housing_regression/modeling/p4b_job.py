"""Production Win32 Job Object lifecycle management with kill-on-close limits."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from typing import Optional

# Windows Job Object Constants
JobObjectExtendedLimitInformation = 9
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
JOB_OBJECT_LIMIT_JOB_MEMORY = 0x0200
DEFAULT_JOB_MEMORY_LIMIT_BYTES = 2 * 1024 * 1024 * 1024


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


def _get_kernel32():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryInformationJobObject.restype = wintypes.BOOL
    kernel32.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    return kernel32


def create_kill_on_close_job_object(memory_limit_bytes: int = DEFAULT_JOB_MEMORY_LIMIT_BYTES) -> int:
    """Create a kill-on-close Job Object with a finite aggregate commit limit."""
    if isinstance(memory_limit_bytes, bool) or not isinstance(memory_limit_bytes, int) or memory_limit_bytes <= 0:
        raise ValueError("Job Object memory limit must be a positive integer byte count.")
    if os.name != "nt":
        return 0
    kernel32 = _get_kernel32()
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise RuntimeError(f"Failed to create Job Object: Windows error {ctypes.get_last_error()}")

    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_JOB_MEMORY
    info.JobMemoryLimit = memory_limit_bytes
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
    """Assign a Windows process handle to a Job Object. Fails closed on error."""
    if os.name != "nt":
        return
    if not job_handle or not process_handle:
        raise RuntimeError("Failed to assign process to Job Object: invalid handle.")
    kernel32 = _get_kernel32()
    success = kernel32.AssignProcessToJobObject(job_handle, process_handle)
    if not success:
        raise RuntimeError(f"Failed to assign process to Job Object: Windows error {ctypes.get_last_error()}")


def close_job_object(job_handle: int) -> None:
    """Close a Windows Job Object handle (terminating all member processes if kill-on-close)."""
    if os.name != "nt" or not job_handle:
        return
    kernel32 = _get_kernel32()
    if not kernel32.CloseHandle(job_handle):
        raise RuntimeError(f"Failed to close Job Object: Windows error {ctypes.get_last_error()}")


def terminate_job_object(job_handle: int) -> None:
    """Terminate every process assigned to a Job Object, failing closed on error."""
    if os.name != "nt" or not job_handle:
        return
    kernel32 = _get_kernel32()
    if not kernel32.TerminateJobObject(job_handle, 1):
        raise RuntimeError(f"Failed to terminate Job Object: Windows error {ctypes.get_last_error()}")


def query_job_memory_limit(job_handle: int) -> tuple[int, int]:
    """Read back the enforced aggregate memory limit flags and byte count."""
    if os.name != "nt" or not job_handle:
        raise RuntimeError("Job Object memory query requires a valid Windows handle.")
    kernel32 = _get_kernel32()
    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    returned = wintypes.DWORD()
    success = kernel32.QueryInformationJobObject(
        job_handle,
        JobObjectExtendedLimitInformation,
        ctypes.byref(info),
        ctypes.sizeof(info),
        ctypes.byref(returned),
    )
    if not success:
        raise RuntimeError(f"Failed to query Job Object memory limit: Windows error {ctypes.get_last_error()}")
    return int(info.BasicLimitInformation.LimitFlags), int(info.JobMemoryLimit)
