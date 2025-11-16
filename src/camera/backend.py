from __future__ import annotations

import abc
from typing import Dict, Iterable, List, Optional

from .exceptions import CameraError
from .types import CameraInfo, CameraParameter


class BackendDevice(abc.ABC):
    """Backend-specific device implementation."""

    info: CameraInfo

    def __init__(self, info: CameraInfo):
        self.info = info

    # Lifecycle ----------------------------------------------------------
    def open(self) -> None:
        """Hook executed after the device has been created."""

    def close(self) -> None:
        """Release device resources."""

    # Parameter management -----------------------------------------------
    @abc.abstractmethod
    def list_parameters(self) -> Iterable[CameraParameter]:
        """Return parameter metadata."""

    @abc.abstractmethod
    def get_parameter(self, key: str) -> object:
        """Return the current value for a parameter."""

    @abc.abstractmethod
    def set_parameter(self, key: str, value: object) -> None:
        """Update a parameter value."""

    # Streaming ----------------------------------------------------------
    @abc.abstractmethod
    def start_stream(self) -> None:
        """Start providing frames."""

    @abc.abstractmethod
    def stop_stream(self) -> None:
        """Stop providing frames."""

    @abc.abstractmethod
    def get_frame(self, timeout_ms: int = 1000) -> Optional["FrameData"]:
        """Fetch the next frame. Returns None on timeout."""

    def __enter__(self) -> "BackendDevice":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class CameraBackend(abc.ABC):
    """Abstract base class for backend providers."""

    name: str = "BaseBackend"

    @abc.abstractmethod
    def discover(self) -> List[CameraInfo]:
        """Return all currently available cameras."""

    @abc.abstractmethod
    def connect(self, info: CameraInfo) -> BackendDevice:
        """Connect to a discovered camera."""

    def disconnect(self, device: BackendDevice) -> None:
        """Disconnect device. Default implementation calls close."""
        try:
            device.close()
        except CameraError:
            raise
        except Exception as exc:
            raise CameraError(f"Failed to disconnect {device.info.id}: {exc}") from exc


class FrameData(dict):
    """Simple mapping object carrying frame data and metadata."""

    image: "np.ndarray"
    metadata: Dict[str, object]

    def __init__(self, image, **metadata):
        super().__init__(image=image, metadata=metadata)

    @property
    def image(self):
        return self["image"]

    @property
    def metadata(self) -> Dict[str, object]:
        return self["metadata"]
