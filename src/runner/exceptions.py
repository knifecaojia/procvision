class RunnerError(Exception):
    """Base class for all runner exceptions."""
    def __init__(self, message: str, error_code: str = "9999"):
        super().__init__(f"[{error_code}] {message}")
        self.message = message
        self.error_code = error_code

# Standard Error Codes (aligned with SDK)
class InvalidPidError(RunnerError):
    def __init__(self, message: str = "Invalid PID"):
        super().__init__(message, "1001")

class ImageLoadFailedError(RunnerError):
    def __init__(self, message: str = "Image load failed"):
        super().__init__(message, "1002")

class ModelNotFoundError(RunnerError):
    def __init__(self, message: str = "Model not found"):
        super().__init__(message, "1003")

class GpuOomError(RunnerError):
    def __init__(self, message: str = "GPU OOM"):
        super().__init__(message, "1004")

class TimeoutError(RunnerError):
    def __init__(self, message: str = "Timeout"):
        super().__init__(message, "1005")

class InvalidParamsError(RunnerError):
    def __init__(self, message: str = "Invalid params"):
        super().__init__(message, "1006")

class CoordinateInvalidError(RunnerError):
    def __init__(self, message: str = "Coordinate invalid"):
        super().__init__(message, "1007")

class UnknownError(RunnerError):
    def __init__(self, message: str = "Unknown error"):
        super().__init__(message, "9999")

# Package Management Error Codes (2xxx)
class InvalidZipError(RunnerError):
    def __init__(self, message: str = "Invalid ZIP"):
        super().__init__(message, "2001")

class ManifestMissingError(RunnerError):
    def __init__(self, message: str = "Manifest missing"):
        super().__init__(message, "2002")

class IncompatiblePythonError(RunnerError):
    def __init__(self, message: str = "Incompatible Python version"):
        super().__init__(message, "2003")

class WheelsMissingError(RunnerError):
    def __init__(self, message: str = "Wheels missing"):
        super().__init__(message, "2004")

class InstallFailedError(RunnerError):
    def __init__(self, message: str = "Install failed"):
        super().__init__(message, "2005")

class ActivationConflictError(RunnerError):
    def __init__(self, message: str = "Activation conflict"):
        super().__init__(message, "2006")

class UnsafeUninstallError(RunnerError):
    def __init__(self, message: str = "Unsafe uninstall"):
        super().__init__(message, "2007")
