"""Preset manager for saving and loading camera parameter configurations."""

from __future__ import annotations

import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LOG = logging.getLogger("camera.preset")

EXPORT_VERSION = "1.0"
EXPORT_SOURCE = "Procvision Industrial Vision System"


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

    def list_camera_models(self, username: str) -> List[str]:
        """List all camera models that have presets for a user.

        Args:
            username: User name

        Returns:
            List of camera model names
        """
        user_dir = self.base_dir / username
        if not user_dir.exists():
            return []

        try:
            models = [d.name for d in user_dir.iterdir() if d.is_dir()]
            LOG.debug("Found %d camera models for user '%s'", len(models), username)
            return sorted(models)
        except Exception as exc:
            LOG.error("Failed to list camera models: %s", exc)
            return []

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

    def get_preset_metadata(self, preset_name: str, username: str, camera_model: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a preset without loading full data.

        Args:
            preset_name: Name of the preset
            username: User name
            camera_model: Camera model name

        Returns:
            Dict with metadata or None if not found
        """
        preset_path = self._get_preset_path(preset_name, username, camera_model)
        if not preset_path.exists():
            return None
        try:
            with preset_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "name": data.get("name"),
                "camera_model": data.get("camera_model"),
                "user_name": data.get("user_name"),
                "created_at": data.get("created_at"),
                "parameter_count": len(data.get("parameters", {}))
            }
        except Exception as exc:
            LOG.error("Failed to get preset metadata '%s': %s", preset_name, exc)
            return None

    def rename_preset(self, old_name: str, new_name: str, username: str, camera_model: str) -> bool:
        """Rename a preset file.

        Args:
            old_name: Current preset name
            new_name: New preset name
            username: User name
            camera_model: Camera model name

        Returns:
            True if renamed successfully, False otherwise
        """
        if old_name == new_name:
            return True

        old_path = self._get_preset_path(old_name, username, camera_model)
        new_path = self._get_preset_path(new_name, username, camera_model)

        if not old_path.exists():
            LOG.warning("Cannot rename preset '%s': file not found", old_name)
            return False

        if new_path.exists():
            LOG.warning("Cannot rename preset '%s' to '%s': target already exists", old_name, new_name)
            return False

        try:
            data = json.loads(old_path.read_text(encoding="utf-8"))
            data["name"] = new_name
            new_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            old_path.unlink()
            LOG.info("Renamed preset '%s' to '%s'", old_name, new_name)
            return True
        except Exception as exc:
            LOG.error("Failed to rename preset '%s': %s", old_name, exc)
            return False

    def export_preset(
        self,
        preset_name: str,
        username: str,
        camera_model: str,
        export_path: Path
    ) -> bool:
        """Export a single preset to a JSON file.

        Args:
            preset_name: Name of the preset to export
            username: User name
            camera_model: Camera model name
            export_path: Path to save the exported file

        Returns:
            True if exported successfully, False otherwise
        """
        preset_data = self.load_preset(preset_name, username, camera_model)
        if not preset_data:
            LOG.warning("Cannot export preset '%s': not found", preset_name)
            return False

        export_data = preset_data.copy()
        export_data["exported_at"] = datetime.now().isoformat()
        export_data["export_source"] = EXPORT_SOURCE
        export_data["version"] = EXPORT_VERSION

        try:
            export_path = Path(export_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            with export_path.open("w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            LOG.info("Exported preset '%s' to %s", preset_name, export_path)
            return True
        except Exception as exc:
            LOG.error("Failed to export preset '%s': %s", preset_name, exc)
            return False

    def import_preset(
        self,
        import_path: Path,
        username: str,
        camera_model: str,
        new_name: Optional[str] = None
    ) -> Optional[str]:
        """Import a preset from a JSON file.

        Args:
            import_path: Path to the JSON file to import
            username: User name to save the preset under
            camera_model: Camera model name
            new_name: Optional new name for the imported preset

        Returns:
            Name of the imported preset, or None if import failed
        """
        try:
            import_path = Path(import_path)
            with import_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            parameters = data.get("parameters")
            if not parameters or not isinstance(parameters, dict):
                LOG.warning("Invalid preset file '%s': no parameters found", import_path)
                return None

            preset_name = new_name or data.get("name", import_path.stem)
            preset_name = str(preset_name).strip()
            if not preset_name:
                preset_name = f"imported_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            preset_data = {
                "name": preset_name,
                "camera_model": camera_model,
                "user_name": username,
                "created_at": datetime.now().isoformat(),
                "parameters": parameters
            }

            preset_path = self._get_preset_path(preset_name, username, camera_model)
            with preset_path.open("w", encoding="utf-8") as f:
                json.dump(preset_data, f, indent=2, ensure_ascii=False)

            LOG.info("Imported preset '%s' from %s", preset_name, import_path)
            return preset_name
        except Exception as exc:
            LOG.error("Failed to import preset from '%s': %s", import_path, exc)
            return None

    def export_all_presets(
        self,
        username: str,
        camera_model: str,
        export_path: Path
    ) -> int:
        """Export all presets to a ZIP file.

        Args:
            username: User name
            camera_model: Camera model name
            export_path: Path to save the ZIP file

        Returns:
            Number of presets exported
        """
        preset_names = self.list_presets(username, camera_model)
        if not preset_names:
            LOG.warning("No presets to export")
            return 0

        export_path = Path(export_path)
        export_path.parent.mkdir(parents=True, exist_ok=True)

        exported_count = 0
        manifest = {
            "version": EXPORT_VERSION,
            "export_source": EXPORT_SOURCE,
            "exported_at": datetime.now().isoformat(),
            "camera_model": camera_model,
            "user_name": username,
            "preset_count": 0,
            "presets": []
        }

        try:
            with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for preset_name in preset_names:
                    preset_data = self.load_preset(preset_name, username, camera_model)
                    if not preset_data:
                        continue

                    safe_filename = self._make_safe_filename(preset_name)
                    file_in_zip = f"{safe_filename}.json"

                    export_data = preset_data.copy()
                    export_data["exported_at"] = manifest["exported_at"]
                    export_data["export_source"] = EXPORT_SOURCE
                    export_data["version"] = EXPORT_VERSION

                    zf.writestr(file_in_zip, json.dumps(export_data, indent=2, ensure_ascii=False))
                    manifest["presets"].append({"name": preset_name, "file": file_in_zip})
                    exported_count += 1

                manifest["preset_count"] = exported_count
                zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

            LOG.info("Exported %d presets to %s", exported_count, export_path)
            return exported_count
        except Exception as exc:
            LOG.error("Failed to export all presets: %s", exc)
            return 0

    def import_all_presets(
        self,
        import_path: Path,
        username: str,
        camera_model: str,
        overwrite: bool = False
    ) -> Tuple[int, List[str]]:
        """Import all presets from a ZIP file.

        Args:
            import_path: Path to the ZIP file
            username: User name to save presets under
            camera_model: Camera model name
            overwrite: If True, overwrite existing presets with same name

        Returns:
            Tuple of (number of imported presets, list of failed preset names)
        """
        import_path = Path(import_path)
        imported_count = 0
        failed_names: List[str] = []

        try:
            with zipfile.ZipFile(import_path, "r") as zf:
                manifest_data = None
                try:
                    manifest_json = zf.read("manifest.json")
                    manifest_data = json.loads(manifest_json)
                except KeyError:
                    pass

                preset_files = []
                if manifest_data and "presets" in manifest_data:
                    for entry in manifest_data["presets"]:
                        if "file" in entry:
                            preset_files.append((entry.get("name", ""), entry["file"]))
                else:
                    for name in zf.namelist():
                        if name.endswith(".json") and name != "manifest.json":
                            preset_files.append((Path(name).stem, name))

                for preset_name, file_name in preset_files:
                    try:
                        json_data = zf.read(file_name)
                        data = json.loads(json_data)

                        parameters = data.get("parameters")
                        if not parameters:
                            failed_names.append(preset_name)
                            continue

                        actual_name = data.get("name", preset_name) or preset_name
                        if not actual_name:
                            actual_name = Path(file_name).stem

                        if not overwrite and self.preset_exists(actual_name, username, camera_model):
                            failed_names.append(f"{actual_name} (已存在)")
                            continue

                        preset_data = {
                            "name": actual_name,
                            "camera_model": camera_model,
                            "user_name": username,
                            "created_at": data.get("created_at", datetime.now().isoformat()),
                            "parameters": parameters
                        }

                        preset_path = self._get_preset_path(actual_name, username, camera_model)
                        with preset_path.open("w", encoding="utf-8") as f:
                            json.dump(preset_data, f, indent=2, ensure_ascii=False)

                        imported_count += 1
                    except Exception as exc:
                        LOG.warning("Failed to import preset from '%s': %s", file_name, exc)
                        failed_names.append(preset_name)

            LOG.info("Imported %d presets from %s (%d failed)", imported_count, import_path, len(failed_names))
            return imported_count, failed_names
        except Exception as exc:
            LOG.error("Failed to import presets from '%s': %s", import_path, exc)
            return 0, ["读取ZIP文件失败"]

    def _make_safe_filename(self, name: str) -> str:
        """Convert a preset name to a safe filename.

        Args:
            name: Original preset name

        Returns:
            Safe filename without special characters
        """
        unsafe_chars = '<>:"/\\|?*'
        safe_name = name
        for char in unsafe_chars:
            safe_name = safe_name.replace(char, "_")
        return safe_name.strip() or "unnamed"
