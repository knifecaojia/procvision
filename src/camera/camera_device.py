from __future__ import annotations

import threading
from typing import Dict, Iterable, Optional

import numpy as np

from .backend import BackendDevice, FrameData
from .exceptions import CameraError, ParameterError, StreamError
from .types import CameraInfo, CameraParameter


class CameraDevice:
    """High-level wrapper exposing a backend device to the application."""

    def __init__(self, backend_device: BackendDevice) -> None:
        self._device = backend_device
        self._lock = threading.RLock()
        self._streaming = False

    @property
    def info(self) -> CameraInfo:
        return self._device.info

    @property
    def backend_device(self) -> BackendDevice:
        return self._device

    # ------------------------------------------------------------------
    def list_parameters(self) -> Iterable[CameraParameter]:
        return self._device.list_parameters()

    def get_parameter(self, key: str) -> object:
        with self._lock:
            return self._device.get_parameter(key)

    def set_parameter(self, key: str, value: object) -> None:
        with self._lock:
            self._device.set_parameter(key, value)

    def get_all_parameters(self) -> Dict[str, object]:
        return {param.key: self.get_parameter(param.key) for param in self.list_parameters()}

    # ------------------------------------------------------------------
    def start_stream(self) -> None:
        with self._lock:
            self._device.start_stream()
            self._streaming = True

    def stop_stream(self) -> None:
        with self._lock:
            self._device.stop_stream()
            self._streaming = False

    def get_frame(self, timeout_ms: int = 1000) -> Optional[FrameData]:
        with self._lock:
            return self._device.get_frame(timeout_ms)

    def close(self) -> None:
        with self._lock:
            if self._streaming:
                try:
                    self._device.stop_stream()
                except StreamError:
                    pass
            self._device.close()

    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, object]:
        """Serialize basic info for persistence."""
        data = {
            "id": self.info.id,
            "name": self.info.name,
            "transport": self.info.transport.value,
            "serial_number": self.info.serial_number,
            "ip_address": self.info.ip_address,
            "manufacturer": self.info.manufacturer,
            "model_name": self.info.model_name,
            "parameters": self.get_all_parameters(),
        }
        return data
