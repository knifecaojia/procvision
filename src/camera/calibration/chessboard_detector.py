"""Chessboard corner detection using OpenCV."""

import cv2
import numpy as np


def detect_chessboard_corners(
    image: np.ndarray,
    board_size: tuple[int, int],
    refine: bool = True
) -> tuple[bool, np.ndarray | None]:
    """Detect chessboard corners in an image.

    Args:
        image: Input image as numpy array (BGR or grayscale)
        board_size: Tuple of (rows, cols) for chessboard inner corners
        refine: Whether to refine corners to sub-pixel accuracy

    Returns:
        Tuple of (success, corners)
        - success: True if chessboard pattern was detected
        - corners: Numpy array of corner coordinates (N, 1, 2) or None
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Find chessboard corners
    flags = (
        cv2.CALIB_CB_ADAPTIVE_THRESH |
        cv2.CALIB_CB_NORMALIZE_IMAGE |
        cv2.CALIB_CB_FAST_CHECK
    )

    success, corners = cv2.findChessboardCorners(
        gray, board_size, None, flags
    )

    if success and refine:
        # Refine corners to sub-pixel accuracy
        criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            30,  # Max iterations
            0.001  # Epsilon
        )
        corners = cv2.cornerSubPix(
            gray, corners, (11, 11), (-1, -1), criteria
        )

    return success, corners


def draw_corners(
    image: np.ndarray,
    board_size: tuple[int, int],
    corners: np.ndarray,
    show_numbers: bool = True
) -> np.ndarray:
    """Draw detected chessboard corners on an image.

    Args:
        image: Input image
        board_size: Board size (rows, cols)
        corners: Detected corners array
        show_numbers: Whether to draw corner indices

    Returns:
        Image with corners drawn
    """
    # Make a copy to avoid modifying original
    output = image.copy()

    # Draw chessboard corners
    cv2.drawChessboardCorners(output, board_size, corners, True)

    if show_numbers:
        # Draw corner indices (for every 5th corner to avoid clutter)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.4
        color = (0, 255, 0)  # Green
        thickness = 1

        for i, corner in enumerate(corners):
            if i % 5 == 0:  # Show number every 5 corners
                x, y = corner[0]
                # Offset text to avoid overlapping corner marker
                cv2.putText(
                    output, str(i), (int(x) + 5, int(y) - 5),
                    font, font_scale, color, thickness
                )

    return output


def normalize_image_for_detection(image: np.ndarray) -> np.ndarray:
    """Normalize image to improve chessboard detection.

    Args:
        image: Input image

    Returns:
        Normalized grayscale image
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Apply adaptive histogram equalization
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    normalized = clahe.apply(gray)

    return normalized
