"""Data structures for camera calibration."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

import numpy as np


class CameraNotConnectedException(Exception):
    """Raised when camera is not connected during calibration."""

    def __init__(self, message: str = "Camera is not connected"):
        super().__init__(message)


class InsufficientImagesException(Exception):
    """Raised when insufficient calibration images are available."""

    def __init__(self, current: int, required: int):
        message = f"Insufficient calibration images: have {current}, require {required}"
        super().__init__(message)
        self.current = current
        self.required = required


class CalibrationFailedException(Exception):
    """Raised when OpenCV calibration algorithm fails."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class PermissionDeniedException(Exception):
    """Raised when insufficient permissions to access calibration storage."""

    def __init__(self, path: str, original_error: Optional[Exception] = None):
        message = f"Permission denied accessing calibration storage at {path}"
        super().__init__(message)
        self.path = path
        self.original_error = original_error


class InvalidCalibrationFileError(Exception):
    """Raised when calibration file is corrupted or has invalid format."""

    def __init__(self, file_path: str, reason: str):
        message = f"Invalid calibration file {file_path}: {reason}"
        super().__init__(message)
        self.file_path = file_path
        self.reason = reason


@dataclass
class CalibrationImage:
    """Single calibration image with detected corners.

    Attributes:
        timestamp: Time when the image was captured
        image_data: Original image as numpy array (BGR or grayscale)
        corners_detected: Detected chessboard corners as numpy array (N, 1, 2)
                         None if corners were not detected
        board_size: Tuple of (rows, cols) for the chessboard pattern
    """
    timestamp: datetime
    image_data: np.ndarray
    corners_detected: Optional[np.ndarray]
    board_size: Tuple[int, int]


@dataclass
class CalibrationResult:
    """Result of camera calibration computation.

    Attributes:
        timestamp: Time when calibration was performed
        board_size: Chessboard pattern size (rows, cols)
        square_size_mm: Physical size of each chessboard square in millimeters
        image_resolution: Image resolution (width, height)
        camera_matrix: 3x3 intrinsic camera matrix K
        distortion_coeffs: Distortion coefficients (k1, k2, p1, p2, k3, [k4, k5, k6])
        reprojection_error: RMS reprojection error in pixels
        total_images: Total number of captured images
        valid_images: Number of valid images used in calibration
    """
    timestamp: datetime
    board_size: Tuple[int, int]
    square_size_mm: float
    image_resolution: Tuple[int, int]
    camera_matrix: np.ndarray
    distortion_coeffs: np.ndarray
    reprojection_error: float
    total_images: int
    valid_images: int


@dataclass
class ChessboardConfig:
    """Configuration for chessboard pattern used in calibration.

    Attributes:
        rows: Number of inner corner rows (typically 7-9)
        cols: Number of inner corner columns (typically 5-6)
        square_size_mm: Physical size of each square in millimeters
    """
    rows: int
    cols: int
    square_size_mm: float

    def __post_init__(self):
        """Validate chessboard parameters."""
        if not 4 <= self.rows <= 20:
            raise ValueError(f"Rows must be between 4 and 20, got {self.rows}")
        if not 4 <= self.cols <= 20:
            raise ValueError(f"Cols must be between 4 and 20, got {self.cols}")
        if not 1.0 <= self.square_size_mm <= 200.0:
            raise ValueError(f"Square size must be between 1.0 and 200.0 mm, got {self.square_size_mm}")

    @property
    def board_size(self) -> Tuple[int, int]:
        """Get board size as (rows, cols) tuple."""
        return (self.rows, self.cols)
