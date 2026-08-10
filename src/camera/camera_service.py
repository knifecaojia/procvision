"""Camera service layer providing high-level API for camera operations."""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .binding_store import CameraBinding, CameraBindingStore
from .camera_identity import build_camera_display_label, get_camera_usage_status
from .camera_device import CameraDevice
from .camera_manager import CameraManager
from .preset_manager import PresetManager
from .types import CameraInfo, CameraParameter

LOG = logging.getLogger("camera.service")
DEFAULT_BINDING_SLOT = "default_camera"


class CameraService:
    """Service layer encapsulating all camera operations."""

    def __init__(
        self,
        sdk_path: Optional[Any] = None,
        presets_dir: Optional[Path] = None,
        bindings_path: Optional[Path] = None,
    ) -> None:
        """Initialize camera service.

        Args:
            sdk_path: Optional SDK installation path
            presets_dir: Directory for storing parameter presets
        """
        if sdk_path is not None and hasattr(sdk_path, "sdk_path"):
            camera_config = sdk_path
            sdk_path = getattr(camera_config, "sdk_path", None)
            if presets_dir is None:
                raw_presets_dir = getattr(camera_config, "presets_directory", None)
                if raw_presets_dir:
                    presets_dir = Path(str(raw_presets_dir))

        self.manager = CameraManager(sdk_path=sdk_path, logger=LOG)
        self.preset_manager = PresetManager(base_dir=presets_dir)
        self.binding_store = CameraBindingStore(
            file_path=bindings_path or self._default_bindings_path()
        )
        self.current_camera: Optional[CameraDevice] = None
        self._cached_cameras: List[CameraInfo] = []
        self._last_camera_model: Optional[str] = None
        LOG.info("CameraService initialized")

    @staticmethod
    def _default_bindings_path() -> Path:
        return Path(__file__).resolve().parents[2] / "config" / "camera_bindings.json"

    # Camera lifecycle ---------------------------------------------------------
    def discover_cameras(self, force_refresh: bool = False) -> List[CameraInfo]:
        """Discover all available cameras.
        
        Args:
            force_refresh: If True, ignore cache and force a new scan.

        Returns:
            List of discovered camera information objects
        """
        if not force_refresh and self._cached_cameras:
            LOG.info("Returning cached camera list (%d cameras)", len(self._cached_cameras))
            return self._cached_cameras

        try:
            cameras = self._deduplicate_cameras(self.manager.discover())
            decorated = self._decorate_cameras_with_binding(cameras)
            self._cached_cameras = decorated
            LOG.info("Discovered %d cameras", len(decorated))
            return decorated
        except Exception as exc:
            LOG.error("Camera discovery failed: %s", exc)
            raise

    def connect_camera(self, camera_info: CameraInfo) -> bool:
        """Connect to a camera.

        Args:
            camera_info: Camera to connect to

        Returns:
            True if connection successful, False otherwise
        """
        try:
            device = self.manager.connect(camera_info)
            self.current_camera = device
            self._last_camera_model = camera_info.model_name or "Unknown"
            LOG.info("Connected to camera: %s", camera_info.name)
            return True
        except Exception as exc:
            LOG.error("Failed to connect to camera %s: %s", camera_info.name, exc)
            return False

    def connect_bound_camera(
        self,
        slot_name: str = DEFAULT_BINDING_SLOT,
        force_refresh: bool = True,
    ) -> Tuple[bool, Optional[CameraInfo], str]:
        """Connect the locally bound camera for a slot."""
        binding = self.get_camera_binding(slot_name)
        if not binding:
            return False, None, "当前客户端尚未绑定相机"

        camera_info = self.get_bound_camera(slot_name=slot_name, force_refresh=force_refresh)
        if not camera_info:
            return False, None, "未找到已绑定相机，请检查相机是否在线"
        if camera_info.accessible is False:
            return False, camera_info, "目标相机已被占用或当前不可访问"

        success = self.connect_camera(camera_info)
        if not success:
            return False, camera_info, f"连接绑定相机失败：{camera_info.name}"
        return True, camera_info, ""

    def disconnect_camera(self) -> None:
        """Disconnect current camera."""
        if not self.current_camera:
            return

        try:
            camera_id = self.current_camera.info.id
            self.manager.disconnect(camera_id)
            LOG.info("Disconnected camera: %s", camera_id)
        except Exception as exc:
            LOG.warning("Error during disconnect: %s", exc)
        finally:
            self.current_camera = None

    def get_connected_camera(self) -> Optional[CameraDevice]:
        """Get currently connected camera device."""
        return self.current_camera

    def get_camera_binding(self, slot_name: str = DEFAULT_BINDING_SLOT) -> Optional[CameraBinding]:
        """Return the persistent binding for the current client slot."""
        return self.binding_store.get(slot_name)

    def bind_camera(
        self,
        camera_info: CameraInfo,
        slot_name: str = DEFAULT_BINDING_SLOT,
    ) -> CameraBinding:
        """Persist a camera binding for this client."""
        binding = CameraBinding.from_camera(slot_name, camera_info)
        self.binding_store.set(binding)
        self._cached_cameras = self._decorate_cameras_with_binding(self._cached_cameras)
        return binding

    def clear_camera_binding(self, slot_name: str = DEFAULT_BINDING_SLOT) -> None:
        """Remove a local camera binding."""
        self.binding_store.clear(slot_name)
        self._cached_cameras = self._decorate_cameras_with_binding(self._cached_cameras)

    def get_bound_camera(
        self,
        slot_name: str = DEFAULT_BINDING_SLOT,
        force_refresh: bool = True,
    ) -> Optional[CameraInfo]:
        """Resolve the currently bound camera from the latest discovery list."""
        binding = self.get_camera_binding(slot_name)
        if not binding:
            return None

        cameras = self.discover_cameras(force_refresh=force_refresh)
        for camera in cameras:
            if self._binding_matches_camera(binding, camera):
                return camera
        return None

    def get_camera_display_label(self, camera: CameraInfo) -> str:
        """Build a selection label for UI widgets."""
        is_bound = bool(camera.backend_data.get("is_bound"))
        return build_camera_display_label(camera, is_bound=is_bound)

    def get_binding_summary(self, slot_name: str = DEFAULT_BINDING_SLOT) -> str:
        """Return a one-line summary for the current binding."""
        binding = self.get_camera_binding(slot_name)
        if not binding:
            return "未绑定"

        ip_text = binding.expected_ip or "无IP"
        serial = binding.serial_number or "无序列号"
        name = binding.last_seen_name or binding.model_name or "未命名相机"
        return f"{name} | SN:{serial} | IP:{ip_text}"

    def get_bound_camera_runtime_state(
        self,
        slot_name: str = DEFAULT_BINDING_SLOT,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """Describe the bound camera for execution-oriented UIs."""
        binding = self.get_camera_binding(slot_name)
        if not binding:
            return {
                "has_binding": False,
                "camera": None,
                "summary": "未绑定",
                "detail": "请先在相机管理页绑定相机",
                "status_text": "未绑定",
                "connected": False,
                "streaming": False,
                "can_connect": False,
            }

        camera = self.get_bound_camera(slot_name=slot_name, force_refresh=force_refresh)
        connected_camera = self.get_connected_camera()
        connected = bool(
            camera
            and connected_camera
            and self._binding_matches_camera(binding, connected_camera.info)
        )
        streaming = bool(connected and self.is_streaming())

        if camera:
            summary = build_camera_display_label(camera, is_bound=True)
            detail = camera.model_name or camera.name or "海康相机"
            status_text = get_camera_usage_status(camera)
        else:
            summary = self.get_binding_summary(slot_name)
            detail = "当前未在局域网发现已绑定相机"
            status_text = "离线"

        if streaming:
            status_text = "预览中"
        elif connected:
            status_text = "已连接"

        return {
            "has_binding": True,
            "camera": camera,
            "summary": summary,
            "detail": detail,
            "status_text": status_text,
            "connected": connected,
            "streaming": streaming,
            "can_connect": bool(camera and camera.accessible is not False),
        }

    def _decorate_cameras_with_binding(self, cameras: List[CameraInfo]) -> List[CameraInfo]:
        binding = self.get_camera_binding()
        decorated: List[CameraInfo] = []
        for camera in cameras:
            metadata = dict(camera.backend_data)
            is_bound = bool(binding and self._binding_matches_camera(binding, camera))
            metadata["is_bound"] = is_bound
            metadata["display_label"] = build_camera_display_label(camera, is_bound=is_bound)
            decorated.append(replace(camera, backend_data=metadata))
        return decorated

    def _deduplicate_cameras(self, cameras: List[CameraInfo]) -> List[CameraInfo]:
        unique_by_id: Dict[str, CameraInfo] = {}
        for camera in cameras:
            existing = unique_by_id.get(camera.id)
            if existing is None:
                unique_by_id[camera.id] = camera
                continue

            preferred = existing
            if existing.accessible is not True and camera.accessible is True:
                preferred = camera
            elif not existing.ip_address and camera.ip_address:
                preferred = camera

            unique_by_id[camera.id] = preferred

        duplicate_count = len(cameras) - len(unique_by_id)
        if duplicate_count > 0:
            LOG.warning("Deduplicated %d duplicate camera entries during discovery", duplicate_count)
        return list(unique_by_id.values())

    @staticmethod
    def _binding_matches_camera(binding: CameraBinding, camera: CameraInfo) -> bool:
        if binding.serial_number and camera.serial_number:
            return binding.serial_number == camera.serial_number

        return (
            binding.transport == camera.transport.value
            and (binding.model_name or "") == (camera.model_name or "")
            and (binding.expected_ip or "") == (camera.ip_address or "")
        )

    # Parameter management -----------------------------------------------------
    def list_parameters(self) -> List[CameraParameter]:
        """List all available parameters for current camera.

        Returns:
            List of parameter metadata
        """
        if not self.current_camera:
            return []
        return list(self.current_camera.list_parameters())

    def get_all_parameters(self) -> Dict[str, Any]:
        """Get all parameter values from current camera.

        Returns:
            Dictionary mapping parameter keys to values
        """
        if not self.current_camera:
            return {}
        return self.current_camera.get_all_parameters()

    def get_parameter(self, key: str) -> Optional[Any]:
        """Get single parameter value.

        Args:
            key: Parameter key

        Returns:
            Parameter value or None if not available
        """
        if not self.current_camera:
            return None
        try:
            return self.current_camera.get_parameter(key)
        except Exception as exc:
            LOG.warning("Failed to get parameter %s: %s", key, exc)
            return None

    def set_parameter(self, key: str, value: Any) -> bool:
        """Set a parameter value.

        Args:
            key: Parameter key
            value: New value

        Returns:
            True if successful, False otherwise
        """
        if not self.current_camera:
            LOG.warning("No camera connected")
            return False

        try:
            param_def = None
            for param in self.current_camera.list_parameters():
                if param.key == key:
                    param_def = param
                    break

            if param_def:
                if param_def.value_type == int:
                    value = int(float(value))
                elif param_def.value_type == float:
                    value = float(value)
                if param_def.min_value is not None and value < param_def.min_value:
                    value = param_def.min_value
                if param_def.max_value is not None and value > param_def.max_value:
                    value = param_def.max_value

            self.current_camera.set_parameter(key, value)
            LOG.debug("Set parameter %s = %s", key, value)
            return True
        except Exception as exc:
            LOG.warning("Parameter %s not accessible on this camera: %s", key, exc)
            return False

    def get_parameter_range(self, key: str) -> Tuple[float, float]:
        """Get min/max range for a parameter.

        Args:
            key: Parameter key

        Returns:
            Tuple of (min_value, max_value)
        """
        if not self.current_camera:
            return (0.0, 0.0)

        for param in self.current_camera.list_parameters():
            if param.key == key:
                min_val = param.min_value if param.min_value is not None else 0.0
                max_val = param.max_value if param.max_value is not None else 100.0
                return (min_val, max_val)

        return (0.0, 0.0)

    # Preset management --------------------------------------------------------
    def save_preset(self, name: str, username: str) -> bool:
        """Save current parameters as a preset.

        Args:
            name: Preset name
            username: Current user name

        Returns:
            True if successful, False otherwise
        """
        if not self.current_camera:
            LOG.warning("No camera connected, cannot save preset")
            return False

        try:
            camera_model = self.current_camera.info.model_name or "Unknown"
            self._last_camera_model = camera_model
            parameters = self.get_all_parameters()

            self.preset_manager.save_preset(
                preset_name=name,
                username=username,
                camera_model=camera_model,
                parameters=parameters
            )
            LOG.info("Saved preset '%s' for user '%s'", name, username)
            return True
        except Exception as exc:
            LOG.error("Failed to save preset: %s", exc)
            return False

    def load_preset(self, name: str, username: str) -> Optional[Dict[str, Any]]:
        """Load a preset by name.

        Args:
            name: Preset name
            username: Current user name

        Returns:
            Dict of parameters or None if not found
        """
        if not self.current_camera:
            LOG.warning("No camera connected")
            return None

        try:
            camera_model = self.current_camera.info.model_name or "Unknown"
            preset_data = self.preset_manager.load_preset(
                preset_name=name,
                username=username,
                camera_model=camera_model
            )

            if preset_data:
                LOG.info("Loaded preset '%s' for user '%s'", name, username)
                return preset_data.get("parameters", {})
            return None
        except Exception as exc:
            LOG.error("Failed to load preset: %s", exc)
            return None

    def apply_preset(self, name: str, username: str) -> Tuple[bool, List[str]]:
        """Load and apply a preset to the current camera.

        Args:
            name: Preset name
            username: Current user name

        Returns:
            Tuple of (success, list of failed parameters)
        """
        parameters = self.load_preset(name, username)
        if not parameters:
            return False, ["配置不存在"]

        failed_params = []
        for key, value in parameters.items():
            if not self.set_parameter(key, value):
                failed_params.append(key)

        return len(failed_params) == 0, failed_params

    def list_presets(self, username: str, camera_model: Optional[str] = None) -> List[str]:
        """List all presets for current camera and user.

        Args:
            username: Current user name
            camera_model: Optional camera model override

        Returns:
            List of preset names
        """
        model = camera_model or self._last_camera_model
        if not model:
            models = self.preset_manager.list_camera_models(username)
            if models:
                self._last_camera_model = models[0]
                model = self._last_camera_model
            else:
                return []

        try:
            presets = self.preset_manager.list_presets(username, model)
            LOG.debug("Found %d presets for user '%s'", len(presets), username)
            return presets
        except Exception as exc:
            LOG.error("Failed to list presets: %s", exc)
            return []

    def delete_preset(self, name: str, username: str) -> bool:
        """Delete a preset.

        Args:
            name: Preset name
            username: Current user name

        Returns:
            True if successful, False otherwise
        """
        if not self.current_camera:
            return False

        try:
            camera_model = self.current_camera.info.model_name or "Unknown"
            self.preset_manager.delete_preset(name, username, camera_model)
            LOG.info("Deleted preset '%s' for user '%s'", name, username)
            return True
        except Exception as exc:
            LOG.error("Failed to delete preset: %s", exc)
            return False

    def rename_preset(self, old_name: str, new_name: str, username: str) -> bool:
        """Rename a preset.

        Args:
            old_name: Current preset name
            new_name: New preset name
            username: Current user name

        Returns:
            True if successful, False otherwise
        """
        if not self.current_camera:
            return False

        try:
            camera_model = self.current_camera.info.model_name or "Unknown"
            success = self.preset_manager.rename_preset(old_name, new_name, username, camera_model)
            if success:
                LOG.info("Renamed preset '%s' to '%s' for user '%s'", old_name, new_name, username)
            return success
        except Exception as exc:
            LOG.error("Failed to rename preset: %s", exc)
            return False

    def get_preset_info(self, name: str, username: str) -> Optional[Dict[str, Any]]:
        """Get preset metadata.

        Args:
            name: Preset name
            username: Current user name

        Returns:
            Dict with preset info or None if not found
        """
        if not self.current_camera:
            return None

        try:
            camera_model = self.current_camera.info.model_name or "Unknown"
            return self.preset_manager.get_preset_metadata(name, username, camera_model)
        except Exception as exc:
            LOG.error("Failed to get preset info: %s", exc)
            return None

    def export_preset(self, name: str, username: str, export_path: Path) -> bool:
        """Export a single preset to a JSON file.

        Args:
            name: Preset name
            username: Current user name
            export_path: Path to save the exported file

        Returns:
            True if successful, False otherwise
        """
        if not self.current_camera:
            return False

        try:
            camera_model = self.current_camera.info.model_name or "Unknown"
            success = self.preset_manager.export_preset(name, username, camera_model, export_path)
            if success:
                LOG.info("Exported preset '%s' to %s", name, export_path)
            return success
        except Exception as exc:
            LOG.error("Failed to export preset: %s", exc)
            return False

    def import_preset(self, import_path: Path, username: str, new_name: Optional[str] = None) -> Optional[str]:
        """Import a preset from a JSON file.

        Args:
            import_path: Path to the JSON file
            username: Current user name
            new_name: Optional new name for the imported preset

        Returns:
            Name of the imported preset, or None if failed
        """
        if not self.current_camera:
            return None

        try:
            camera_model = self.current_camera.info.model_name or "Unknown"
            preset_name = self.preset_manager.import_preset(
                import_path, username, camera_model, new_name
            )
            if preset_name:
                LOG.info("Imported preset '%s' from %s", preset_name, import_path)
            return preset_name
        except Exception as exc:
            LOG.error("Failed to import preset: %s", exc)
            return None

    def export_all_presets(self, username: str, export_path: Path) -> int:
        """Export all presets to a ZIP file.

        Args:
            username: Current user name
            export_path: Path to save the ZIP file

        Returns:
            Number of presets exported
        """
        if not self.current_camera:
            return 0

        try:
            camera_model = self.current_camera.info.model_name or "Unknown"
            count = self.preset_manager.export_all_presets(username, camera_model, export_path)
            LOG.info("Exported %d presets to %s", count, export_path)
            return count
        except Exception as exc:
            LOG.error("Failed to export all presets: %s", exc)
            return 0

    def import_all_presets(self, import_path: Path, username: str, overwrite: bool = False) -> Tuple[int, List[str]]:
        """Import all presets from a ZIP file.

        Args:
            import_path: Path to the ZIP file
            username: Current user name
            overwrite: If True, overwrite existing presets with same name

        Returns:
            Tuple of (number imported, list of failed names)
        """
        if not self.current_camera:
            return 0, ["相机未连接"]

        try:
            camera_model = self.current_camera.info.model_name or "Unknown"
            count, failed = self.preset_manager.import_all_presets(
                import_path, username, camera_model, overwrite
            )
            LOG.info("Imported %d presets from %s (%d failed)", count, import_path, len(failed))
            return count, failed
        except Exception as exc:
            LOG.error("Failed to import all presets: %s", exc)
            return 0, [str(exc)]

    # Stream control -----------------------------------------------------------
    def start_preview(self) -> bool:
        """Start camera preview stream.

        Returns:
            True if successful, False otherwise
        """
        if not self.current_camera:
            LOG.warning("No camera connected")
            return False

        try:
            self.current_camera.start_stream()
            LOG.info("Started preview stream")
            return True
        except Exception as exc:
            LOG.error("Failed to start preview: %s", exc)
            return False

    def stop_preview(self) -> None:
        """Stop camera preview stream."""
        if not self.current_camera:
            return

        try:
            self.current_camera.stop_stream()
            LOG.info("Stopped preview stream")
        except Exception as exc:
            LOG.warning("Error stopping preview: %s", exc)

    def is_streaming(self) -> bool:
        """Check if camera is currently streaming.

        Returns:
            True if streaming, False otherwise
        """
        if not self.current_camera:
            return False
        return self.current_camera._streaming

    # Cleanup ------------------------------------------------------------------
    def shutdown(self) -> None:
        """Shutdown service and release all resources."""
        self.stop_preview()
        self.disconnect_camera()
        self.manager.shutdown()
        LOG.info("CameraService shutdown complete")
