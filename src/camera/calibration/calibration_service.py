"""Camera calibration service for computing intrinsic parameters."""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
import cv2
from pathlib import Path

from .calibration_data import (
    CalibrationImage,
    CalibrationResult,
    ChessboardConfig,
    CameraNotConnectedException,
    InsufficientImagesException,
    CalibrationFailedException
)
from .chessboard_detector import detect_chessboard_corners

logger = logging.getLogger("camera.calibration")


class CalibrationService:
    """Service for managing camera calibration workflow.

    This service handles capturing calibration images, detecting chessboard
    corners, and computing camera intrinsic parameters using OpenCV.
    """

    def __init__(
        self,
        camera_service,
        min_images: int = 15,
        max_images: int = 30
    ):
        """Initialize calibration service.

        Args:
            camera_service: Camera service instance for accessing camera
            min_images: Minimum number of images required for calibration
            max_images: Maximum number of calibration images to store
        """
        self.camera_service = camera_service
        self.min_images = min_images
        self.max_images = max_images
        self.calibration_images: List[CalibrationImage] = []
        logger.info(f"CalibrationService initialized (min_images={min_images})")

    def capture_calibration_image(self, board_config: ChessboardConfig) -> bool:
        """Capture and validate current camera frame as calibration image.

        Args:
            board_config: Chessboard pattern configuration

        Returns:
            True if image was captured and corners detected, False otherwise

        Raises:
            CameraNotConnectedException: If camera is not connected
        """
        logger.debug("Attempting to capture calibration image")

        # Get current frame from camera
        frame_data = None
        if hasattr(self.camera_service, 'get_connected_camera'):
            camera = self.camera_service.get_connected_camera()
            if camera:
                frame_data = camera.get_frame(timeout_ms=1000)

        if frame_data is None or frame_data.image is None:
            logger.warning("No frame available from camera")
            raise CameraNotConnectedException("No frame available from camera")

        image = frame_data.image
        logger.debug(f"Captured frame with shape {image.shape}")

        # Detect chessboard corners
        success, corners = detect_chessboard_corners(
            image,
            board_config.board_size,
            refine=True
        )

        if not success:
            logger.debug("Chessboard corners not detected")
            return False

        # Store calibration image
        cal_image = CalibrationImage(
            timestamp=frame_data.timestamp,
            image_data=image,
            corners_detected=corners,
            board_size=board_config.board_size
        )

        self.calibration_images.append(cal_image)
        logger.info(f"Calibration image captured and stored. Total: {len(self.calibration_images)}")

        return True

    def calibrate(self, board_config: ChessboardConfig) -> CalibrationResult:
        """Execute camera calibration computation.

        Args:
            board_config: Chessboard pattern configuration

        Returns:
            CalibrationResult with computed camera parameters

        Raises:
            InsufficientImagesException: If not enough valid images
            CalibrationFailedException: If OpenCV calibration fails
        """
        logger.info(f"Starting calibration with {len(self.calibration_images)} images")

        # Validate minimum image count
        valid_images = [img for img in self.calibration_images
                       if img.corners_detected is not None]

        if len(valid_images) < self.min_images:
            raise InsufficientImagesException(
                current=len(valid_images),
                required=self.min_images
            )

        logger.info(f"Using {len(valid_images)} valid images for calibration")

        # Prepare object points (3D points in real world)
        objp = np.zeros((board_config.rows * board_config.cols, 3), np.float32)
        objp[:, :2] = np.mgrid[0:board_config.cols, 0:board_config.rows].T.reshape(-1, 2)
        objp *= board_config.square_size_mm  # Scale by square size

        # Arrays to store object points and image points
        obj_points = []  # 3D points in real world
        img_points = []  # 2D points in image plane

        # Collect points from all valid images
        for img in valid_images:
            if img.corners_detected is not None:
                obj_points.append(objp)
                img_points.append(img.corners_detected)

        # Get image resolution from first valid image
        if valid_images and valid_images[0].image_data is not None:
            height, width = valid_images[0].image_data.shape[:2]
            image_resolution = (width, height)
        else:
            image_resolution = (1920, 1080)  # Default fallback

        logger.debug(f"Image resolution: {image_resolution}")

        try:
            # Perform camera calibration
            ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
                obj_points,
                img_points,
                image_resolution,
                None,  # Initial camera matrix (None to compute from scratch)
                None,  # Initial distortion coeffs (None to compute from scratch)
                flags=0  # Default flags
            )

            logger.info(f"Calibration completed with reprojection error: {ret:.4f}")

            # Create calibration result object
            result = CalibrationResult(
                timestamp=datetime.now(),
                board_size=board_config.board_size,
                square_size_mm=board_config.square_size_mm,
                image_resolution=image_resolution,
                camera_matrix=camera_matrix,
                distortion_coeffs=dist_coeffs,
                reprojection_error=float(ret),
                total_images=len(self.calibration_images),
                valid_images=len(valid_images)
            )

            logger.debug(f"Camera matrix:\n{camera_matrix}")
            logger.debug(f"Distortion coefficients: {dist_coeffs.flatten()}")

            return result

        except Exception as e:
            logger.error(f"Camera calibration failed: {str(e)}", exc_info=True)
            raise CalibrationFailedException(
                message=f"OpenCV calibration failed: {str(e)}",
                original_error=e
            ) from e

    def get_progress(self) -> tuple[int, int]:
        """Get calibration progress (captured images, required images).

        Returns:
            Tuple of (captured_count, required_count)
        """
        valid_count = len([img for img in self.calibration_images
                          if img.corners_detected is not None])
        return valid_count, self.min_images

    def reset(self) -> None:
        """Clear all captured calibration images."""
        logger.info(f"Resetting calibration data (clearing {len(self.calibration_images)} images)")
        self.calibration_images.clear()

    def remove_image(self, index: int) -> bool:
        """Remove a specific calibration image by index.

        Args:
            index: Index of image to remove

        Returns:
            True if image was removed, False if index out of range
        """
        if 0 <= index < len(self.calibration_images):
            removed = self.calibration_images.pop(index)
            logger.info(f"Removed calibration image at index {index}")
            return True
        return False

    def get_images(self) -> list[CalibrationImage]:
        """Get all captured calibration images.

        Returns:
            List of CalibrationImage objects
        """
        return self.calibration_images.copy()
