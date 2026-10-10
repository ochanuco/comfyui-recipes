"""Windows power: console idle time, the keep-awake request and S3 sleep."""

from __future__ import annotations

import ctypes
import functools
from collections.abc import Iterator
from contextlib import contextmanager

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
ERROR_NOT_ALL_ASSIGNED = 1300

# Byte offsets into SYSTEM_POWER_CAPABILITIES, whose leading fields are BOOLEANs.
SYSTEM_S3 = 5
HIBER_FILE_PRESENT = 8


class _LastInputInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint32), ("dwTime", ctypes.c_uint32)]


class _Luid(ctypes.Structure):
    _fields_ = [("LowPart", ctypes.c_uint32), ("HighPart", ctypes.c_int32)]


class _TokenPrivileges(ctypes.Structure):
    _fields_ = [("PrivilegeCount", ctypes.c_uint32), ("Luid", _Luid),
                ("Attributes", ctypes.c_uint32)]


@functools.cache
def _api():
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    powrprof = ctypes.WinDLL("powrprof", use_last_error=True)

    kernel32.GetTickCount.restype = wintypes.DWORD
    kernel32.GetTickCount.argtypes = []
    kernel32.SetThreadExecutionState.restype = wintypes.DWORD
    kernel32.SetThreadExecutionState.argtypes = [wintypes.DWORD]
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    user32.GetLastInputInfo.restype = wintypes.BOOL
    user32.GetLastInputInfo.argtypes = [ctypes.POINTER(_LastInputInfo)]
    advapi32.OpenProcessToken.restype = wintypes.BOOL
    advapi32.OpenProcessToken.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi32.LookupPrivilegeValueW.restype = wintypes.BOOL
    advapi32.LookupPrivilegeValueW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.POINTER(_Luid)]
    advapi32.AdjustTokenPrivileges.restype = wintypes.BOOL
    advapi32.AdjustTokenPrivileges.argtypes = [
        wintypes.HANDLE, wintypes.BOOL, ctypes.POINTER(_TokenPrivileges),
        wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p]
    powrprof.GetPwrCapabilities.restype = wintypes.BOOLEAN
    powrprof.GetPwrCapabilities.argtypes = [ctypes.c_void_p]
    powrprof.SetSuspendState.restype = wintypes.BOOLEAN
    powrprof.SetSuspendState.argtypes = [
        wintypes.BOOLEAN, wintypes.BOOLEAN, wintypes.BOOLEAN]
    return kernel32, user32, advapi32, powrprof


def _failure(call: str) -> OSError:
    code = ctypes.get_last_error()
    return OSError(code, f"{call} failed: {ctypes.FormatError(code)}")


def input_idle_seconds() -> float:
    """Seconds since the last keyboard or mouse input in this session."""
    kernel32, user32, _, _ = _api()
    info = _LastInputInfo(ctypes.sizeof(_LastInputInfo), 0)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        raise _failure("GetLastInputInfo")
    return ((kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000


@contextmanager
def keep_awake() -> Iterator[None]:
    """Hold off idle sleep for the calling thread until the block exits."""
    kernel32 = _api()[0]
    kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    try:
        yield
    finally:
        kernel32.SetThreadExecutionState(ES_CONTINUOUS)


def _enable_shutdown_privilege() -> None:
    from ctypes import wintypes

    kernel32, _, advapi32, _ = _api()
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(),
                                     TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                     ctypes.byref(token)):
        raise _failure("OpenProcessToken")
    try:
        luid = _Luid()
        if not advapi32.LookupPrivilegeValueW(None, "SeShutdownPrivilege",
                                              ctypes.byref(luid)):
            raise _failure("LookupPrivilegeValueW")
        privileges = _TokenPrivileges(1, luid, SE_PRIVILEGE_ENABLED)
        if not advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(privileges),
                                              0, None, None):
            raise _failure("AdjustTokenPrivileges")
        if ctypes.get_last_error() == ERROR_NOT_ALL_ASSIGNED:
            raise _failure("AdjustTokenPrivileges")
    finally:
        kernel32.CloseHandle(token)


def sleep_capability() -> tuple[bool, bool]:
    """(S3 sleep is available, a hibernation file is present)."""
    powrprof = _api()[3]
    capabilities = (ctypes.c_ubyte * 128)()
    if not powrprof.GetPwrCapabilities(capabilities):
        raise _failure("GetPwrCapabilities")
    return bool(capabilities[SYSTEM_S3]), bool(capabilities[HIBER_FILE_PRESENT])


def suspend() -> None:
    """Enter S3 sleep and return once the host has woken.

    Refuses while a hibernation file exists: with one, the sleep can end up
    as hibernation, which Wake-on-LAN does not reliably bring back.
    """
    s3, hibernation = sleep_capability()
    if not s3:
        raise SystemExit("S3 sleep is not available on this host")
    if hibernation:
        raise SystemExit("hibernation is enabled; run `powercfg /hibernate off`")
    _enable_shutdown_privilege()
    if not _api()[3].SetSuspendState(False, False, False):
        raise _failure("SetSuspendState")
