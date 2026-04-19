import ctypes
from ctypes import wintypes
import sys
import logging

logger = logging.getLogger(__name__)

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

ERROR_ALREADY_EXISTS = 183

kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
kernel32.ReleaseMutex.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

MB_OK = 0x00000000
MB_ICONWARNING = 0x00000030
MB_SETFOREGROUND = 0x00010000
MB_TOPMOST = 0x00040000


class SingleInstanceError(Exception):
    pass


class SingleInstance:
    def __init__(self, app_name: str):
        self._mutex_name = f"Global\\{app_name}-SingleInstance"
        self._handle = None

    def try_lock(self) -> bool:
        self._handle = kernel32.CreateMutexW(None, False, self._mutex_name)
        if not self._handle:
            logger.error("CreateMutex failed: handle is null")
            return False
        last_error = ctypes.GetLastError()
        if last_error == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(self._handle)
            self._handle = None
            return False
        return True

    def release(self):
        if self._handle:
            kernel32.ReleaseMutex(self._handle)
            kernel32.CloseHandle(self._handle)
            self._handle = None

    def is_running(self) -> bool:
        return not self.try_lock()

    def __enter__(self):
        if not self.try_lock():
            raise SingleInstanceError(
                f"Application is already running (mutex: {self._mutex_name})"
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


def show_already_running_message(app_title: str = "SMART-VISION"):
    user32.MessageBoxW(
        None,
        "程序已经在运行中，不允许重复启动。\n\n如需重新启动，请先关闭已运行的实例。",
        f"{app_title} - 提示",
        MB_OK | MB_ICONWARNING | MB_SETFOREGROUND | MB_TOPMOST,
    )


def enforce_single_instance(app_name: str = "SMART-VISION", app_title: str = "SMART-VISION"):
    lock = SingleInstance(app_name)
    if not lock.try_lock():
        show_already_running_message(app_title)
        sys.exit(0)
    return lock
