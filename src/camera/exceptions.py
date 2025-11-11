"""Custom exception types for the camera SDK abstraction layer."""


class CameraError(Exception):
    """Base error for camera related issues."""


class DiscoveryError(CameraError):
    """Raised when device discovery fails."""


class ConnectionError(CameraError):
    """Raised when connecting to a device fails."""


class StreamError(CameraError):
    """Raised when starting/stopping the stream fails."""


class ParameterError(CameraError):
    """Raised when parameter get/set operations fail."""
