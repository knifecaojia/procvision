"""Calibration storage for persisting and loading calibration results."""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .calibration_data import (
    CalibrationResult,
    InvalidCalibrationFileError,
    PermissionDeniedException
)

logger = logging.getLogger("camera.calibration.storage")


class CalibrationStorage:
    """Manages persistence and retrieval of camera calibration results."""

    def __init__(self, app_name: str = "SMART-VISION", storage_path: Optional[str] = None):
        """Initialize calibration storage.

        Args:
            app_name: Application name for directory naming
            storage_path: Custom storage path (None for system default)
        """
        self.app_name = app_name
        self.storage_path = storage_path

    def get_storage_path(self, camera_model: str, create: bool = False) -> Path:
        """Get the storage directory path for a camera model.

        Args:
            camera_model: Camera model name (e.g., "MV-CA050-10GM")
            create: Whether to create the directory if it doesn't exist

        Returns:
            Path object for the storage directory
        """
        if self.storage_path:
            base_path = Path(self.storage_path)
        else:
            # Use system-specific default paths
            import platform
            system = platform.system()

            if system == "Windows":
                base_path = Path("C:") / "ProgramData" / self.app_name / "calibration"
            elif system == "Linux":
                base_path = Path("/etc") / self.app_name.lower() / "calibration"
            elif system == "Darwin":  # macOS
                base_path = Path("/Library/Application Support") / self.app_name / "calibration"
            else:
                # Fallback to user data directory
                base_path = Path.home() / "." / self.app_name.lower() / "calibration"

        path = base_path / camera_model

        if create:
            path.mkdir(parents=True, exist_ok=True)

        return path

    def save_calibration_result(
        self,
        result: CalibrationResult,
        camera_model: str
    ) -> Path:
        """Save calibration result to root config.json."""
        timestamp = result.timestamp
        config_path = Path.cwd() / "config.json"

        try:
            payload: Dict[str, Any] = {
                "calibration_id": timestamp.strftime('%Y%m%d_%H%M%S'),
                "timestamp": timestamp.isoformat(),
                "camera_model": camera_model,
                "image_resolution": {
                    "width": result.image_resolution[0],
                    "height": result.image_resolution[1]
                },
                "board_size": {
                    "rows": result.board_size[0],
                    "cols": result.board_size[1]
                },
                "square_size_mm": result.square_size_mm,
                "camera_matrix": result.camera_matrix.tolist(),
                "distortion_coefficients": result.distortion_coeffs.flatten().tolist(),
                "reprojection_error": result.reprojection_error,
                "total_images": result.total_images,
                "valid_images": result.valid_images,
                "calibration_version": "1.0"
            }

            try:
                import cv2
                payload["opencv_version"] = cv2.__version__
            except Exception:
                payload["opencv_version"] = "unknown"

            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            else:
                cfg = {}

            cfg["calibration"] = payload

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)

            logger.info(f"Calibration result saved to {config_path}")
            return config_path

        except Exception as e:
            logger.error(f"Failed to save calibration: {e}", exc_info=True)
            raise

    def load_calibration_result(self, file_path: Path) -> CalibrationResult:
        """Load calibration result from JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            CalibrationResult object

        Raises:
            InvalidCalibrationFileError: If file is corrupted or has invalid format
        """
        logger.info(f"Loading calibration result from {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate required fields
            required_fields = [
                "timestamp", "camera_model", "image_resolution", "board_size",
                "square_size_mm", "camera_matrix", "distortion_coefficients",
                "reprojection_error", "total_images", "valid_images"
            ]

            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                raise InvalidCalibrationFileError(
                    str(file_path),
                    f"Missing required fields: {missing_fields}"
                )

            # Parse JSON and reconstruct arrays
            timestamp = datetime.fromisoformat(data["timestamp"])
            image_resolution = (
                data["image_resolution"]["width"],
                data["image_resolution"]["height"]
            )
            board_size = (
                data["board_size"]["rows"],
                data["board_size"]["cols"]
            )

            # Convert lists back to numpy arrays
            camera_matrix = np.array(data["camera_matrix"], dtype=np.float64)
            dist_coeffs = np.array(data["distortion_coefficients"], dtype=np.float64)

            result = CalibrationResult(
                timestamp=timestamp,
                board_size=board_size,
                square_size_mm=float(data["square_size_mm"]),
                image_resolution=image_resolution,
                camera_matrix=camera_matrix,
                distortion_coeffs=dist_coeffs,
                reprojection_error=float(data["reprojection_error"]),
                total_images=int(data["total_images"]),
                valid_images=int(data["valid_images"])
            )

            logger.info(f"Calibration result loaded successfully: {file_path}")
            return result

        except json.JSONDecodeError as e:
            raise InvalidCalibrationFileError(
                str(file_path),
                f"Invalid JSON format: {str(e)}"
            ) from e
        except Exception as e:
            raise InvalidCalibrationFileError(
                str(file_path),
                f"Error loading calibration: {str(e)}"
            ) from e

    def list_calibration_files(self, camera_model: str) -> List[Path]:
        """List all calibration files for a camera model.

        Args:
            camera_model: Camera model name

        Returns:
            List of file paths sorted by timestamp (newest first)
        """
        storage_dir = self.get_storage_path(camera_model)

        if not storage_dir.exists():
            return []

        # Find all JSON files
        json_files = list(storage_dir.glob("*_calibration.json"))

        # Sort by modification time (newest first)
        json_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        logger.debug(f"Found {len(json_files)} calibration files for {camera_model}")
        return json_files

    def load_latest_calibration(self, camera_model: str) -> Optional[CalibrationResult]:
        """Load the most recent calibration for a camera model.

        Args:
            camera_model: Camera model name

        Returns:
            CalibrationResult object or None if no calibrations exist
        """
        files = self.list_calibration_files(camera_model)

        if not files:
            logger.debug(f"No calibration files found for {camera_model}")
            return None

        # Load the most recent file (first in sorted list)
        latest_file = files[0]
        return self.load_calibration_result(latest_file)

    def cleanup_old_calibrations(self, camera_model: str, max_files: int = 30) -> int:
        """Remove old calibration files when exceeding limit.

        Args:
            camera_model: Camera model name
            max_files: Maximum number of files to keep (default: 30)

        Returns:
            Number of files removed
        """
        files = self.list_calibration_files(camera_model)

        if len(files) <= max_files:
            return 0

        # Remove oldest files (skip the first max_files)
        files_to_remove = files[max_files:]

        removed_count = 0
        for file_path in files_to_remove:
            try:
                file_path.unlink()
                removed_count += 1
                logger.info(f"Removed old calibration file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove {file_path}: {e}")

        logger.info(f"Cleaned up {removed_count} old calibration files for {camera_model}")
        return removed_count

    def delete_calibration(self, camera_model: str, timestamp: str) -> bool:
        """Delete a specific calibration file by timestamp.

        Args:
            camera_model: Camera model name
            timestamp: Timestamp in YYYYMMDD_HHMMSS format

        Returns:
            True if file was deleted, False otherwise
        """
        storage_dir = self.get_storage_path(camera_model)
        file_name = f"{timestamp}_calibration.json"
        file_path = storage_dir / file_name

        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Deleted calibration file: {file_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete {file_path}: {e}")

        return False
