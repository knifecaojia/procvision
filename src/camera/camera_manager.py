from __future__ import annotations

import logging
from dataclasses import replace
from typing import Dict, List, Optional

from .backend import CameraBackend
from .camera_device import CameraDevice
from .exceptions import ConnectionError, DiscoveryError
from .types import CameraInfo

LOG = logging.getLogger(__name__)


class CameraManager:
    """High level manager responsible for discovery and lifecycle operations."""

    def __init__(
        self,
        sdk_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._logger = logger or LOG
        self._backends: Dict[str, CameraBackend] = {}
        self._active_devices: Dict[str, CameraDevice] = {}

        self._try_register_hikvision_backend(sdk_path)

    # ------------------------------------------------------------------
    def _try_register_hikvision_backend(self, sdk_path: Optional[str]) -> None:
        try:
            from .hikvision_backend import HikvisionBackend
        except ImportError as exc:
            self._logger.debug(
                "Hikvision backend import failed: %s. No mock fallback.", exc
            )
            return

        try:
            backend = HikvisionBackend(sdk_path=sdk_path)
            self._backends[backend.name] = backend
            self._logger.debug("Successfully registered Hikvision backend")
        except RuntimeError as exc:
            self._logger.warning("Hikvision backend unavailable: %s", exc)
            return

    # ------------------------------------------------------------------
    def discover(self) -> List[CameraInfo]:
        cameras: List[CameraInfo] = []
        for name, backend in self._backends.items():
            try:
                for info in backend.discover():
                    metadata = dict(info.backend_data)
                    metadata.setdefault("backend", name)
                    cameras.append(replace(info, backend_data=metadata))
            except Exception as exc:
                self._logger.error("Discovery failed for backend %s: %s", name, exc)
                raise DiscoveryError(str(exc)) from exc
        return cameras

    # ------------------------------------------------------------------
    def connect(self, camera_info: CameraInfo) -> CameraDevice:
        backend_name = camera_info.backend_data.get("backend")
        if backend_name is None or backend_name not in self._backends:
            raise ConnectionError(f"Unknown backend for camera {camera_info.id}")

        backend = self._backends[backend_name]

        existing = self._active_devices.get(camera_info.id)
        if existing:
            self._logger.debug("Camera %s already connected", camera_info.id)
            return existing

        try:
            backend_device = backend.connect(camera_info)
        except Exception as exc:
            raise ConnectionError(f"Failed to connect to {camera_info.id}: {exc}") from exc

        camera_device = CameraDevice(backend_device)
        self._active_devices[camera_info.id] = camera_device
        return camera_device

    # ------------------------------------------------------------------
    def disconnect(self, camera_id: str) -> None:
        device = self._active_devices.pop(camera_id, None)
        if not device:
            return

        backend_name = device.info.backend_data.get("backend")
        backend = self._backends.get(backend_name) if backend_name else None

        try:
            device.close()
            if backend:
                backend.disconnect(device.backend_device)
        except Exception as exc:
            self._logger.warning("Error while disconnecting %s: %s", camera_id, exc)

    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        for camera_id in list(self._active_devices.keys()):
            self.disconnect(camera_id)
        for backend in self._backends.values():
            shutdown_func = getattr(backend, "shutdown", None)
            if callable(shutdown_func):
                try:
                    shutdown_func()
                except Exception as exc:
                    self._logger.debug("Backend %s shutdown warning: %s", backend.name, exc)
