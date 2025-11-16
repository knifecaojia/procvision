"""Preset manager for saving and loading camera parameter configurations."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

LOG = logging.getLogger("camera.preset")


class PresetManager:
    """Manages camera parameter presets with per-user and per-camera organization."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        """Initialize preset manager.

        Args:
            base_dir: Base directory for storing presets (defaults to data/camera_presets)
        """
        if base_dir is None:
            base_dir = Path("data/camera_presets")

        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        LOG.debug("PresetManager initialized with base_dir: %s", self.base_dir)

    def _get_preset_dir(self, username: str, camera_model: str) -> Path:
        """Get directory path for user and camera model presets.

        Args:
            username: User name
            camera_model: Camera model name

        Returns:
            Path to preset directory
        """
        preset_dir = self.base_dir / username / camera_model
        preset_dir.mkdir(parents=True, exist_ok=True)
        return preset_dir

    def _get_preset_path(self, preset_name: str, username: str, camera_model: str) -> Path:
        """Get full path to a preset file.

        Args:
            preset_name: Name of the preset
            username: User name
            camera_model: Camera model name

        Returns:
            Path to preset JSON file
        """
        preset_dir = self._get_preset_dir(username, camera_model)
        return preset_dir / f"{preset_name}.json"

    def save_preset(
        self,
        preset_name: str,
        username: str,
        camera_model: str,
        parameters: Dict[str, Any]
    ) -> Path:
        """Save camera parameters as a preset.

        Args:
            preset_name: Name for the preset
            username: Current user name
            camera_model: Camera model name
            parameters: Dictionary of parameter key-value pairs

        Returns:
            Path to saved preset file
        """
        preset_path = self._get_preset_path(preset_name, username, camera_model)

        preset_data = {
            "name": preset_name,
            "camera_model": camera_model,
            "user_name": username,
            "created_at": datetime.now().isoformat(),
            "parameters": parameters
        }

        try:
            with preset_path.open("w", encoding="utf-8") as f:
                json.dump(preset_data, f, indent=2, ensure_ascii=False)
            LOG.info("Saved preset '%s' to %s", preset_name, preset_path)
            return preset_path
        except Exception as exc:
            LOG.error("Failed to save preset '%s': %s", preset_name, exc)
            raise

    def load_preset(
        self,
        preset_name: str,
        username: str,
        camera_model: str
    ) -> Optional[Dict[str, Any]]:
        """Load a preset by name.

        Args:
            preset_name: Name of the preset
            username: User name
            camera_model: Camera model name

        Returns:
            Preset data dictionary or None if not found
        """
        preset_path = self._get_preset_path(preset_name, username, camera_model)

        if not preset_path.exists():
            LOG.warning("Preset '%s' not found at %s", preset_name, preset_path)
            return None

        try:
            with preset_path.open("r", encoding="utf-8") as f:
                preset_data = json.load(f)
            LOG.debug("Loaded preset '%s' from %s", preset_name, preset_path)
            return preset_data
        except Exception as exc:
            LOG.error("Failed to load preset '%s': %s", preset_name, exc)
            return None

    def list_presets(self, username: str, camera_model: str) -> List[str]:
        """List all available presets for a user and camera model.

        Args:
            username: User name
            camera_model: Camera model name

        Returns:
            List of preset names (without .json extension)
        """
        preset_dir = self._get_preset_dir(username, camera_model)

        if not preset_dir.exists():
            return []

        try:
            preset_files = list(preset_dir.glob("*.json"))
            preset_names = [f.stem for f in preset_files]
            LOG.debug("Found %d presets in %s", len(preset_names), preset_dir)
            return sorted(preset_names)
        except Exception as exc:
            LOG.error("Failed to list presets in %s: %s", preset_dir, exc)
            return []

    def delete_preset(self, preset_name: str, username: str, camera_model: str) -> bool:
        """Delete a preset.

        Args:
            preset_name: Name of the preset
            username: User name
            camera_model: Camera model name

        Returns:
            True if deleted successfully, False otherwise
        """
        preset_path = self._get_preset_path(preset_name, username, camera_model)

        if not preset_path.exists():
            LOG.warning("Cannot delete preset '%s': file not found", preset_name)
            return False

        try:
            preset_path.unlink()
            LOG.info("Deleted preset '%s' at %s", preset_name, preset_path)
            return True
        except Exception as exc:
            LOG.error("Failed to delete preset '%s': %s", preset_name, exc)
            return False

    def preset_exists(self, preset_name: str, username: str, camera_model: str) -> bool:
        """Check if a preset exists.

        Args:
            preset_name: Name of the preset
            username: User name
            camera_model: Camera model name

        Returns:
            True if preset exists, False otherwise
        """
        preset_path = self._get_preset_path(preset_name, username, camera_model)
        return preset_path.exists()
