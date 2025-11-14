"""PreviewWorker - QThread for camera frame acquisition."""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from PySide6 import QtCore, QtGui
import numpy as np
import cv2
import time

from src.camera.camera_device import CameraDevice
from src.camera.exceptions import CameraError
from src.camera.calibration import detect_chessboard_corners, draw_corners

LOG = logging.getLogger("camera.ui.preview")


class PreviewWorker(QtCore.QThread):
    """Worker thread for acquiring and processing camera frames."""

    frame_ready = QtCore.Signal(QtGui.QImage)
    stats_updated = QtCore.Signal(dict)
    error_occurred = QtCore.Signal(str)

    def __init__(self, camera: CameraDevice, parent: Optional[QtCore.QObject] = None) -> None:
        """Initialize preview worker.

        Args:
            camera: Camera device to acquire frames from
            parent: Parent QObject
        """
        super().__init__(parent)
        self._camera = camera
        self._running = False
        self._detect_enabled: bool = False
        self._board_size: Tuple[int, int] = (9, 6)
        self._downscale_height: int = 480
        self._interval_ms: int = 300
        self._last_overlay_time: float = 0.0
        LOG.debug("PreviewWorker initialized for camera: %s", camera.info.name)

    def run(self) -> None:
        """Main thread loop for frame acquisition."""
        self._running = True
        frame_count = 0
        LOG.info("Preview worker started")

        while self._running:
            try:
                frame = self._camera.get_frame(timeout_ms=1000)
            except CameraError as exc:
                error_msg = f"Frame acquisition error: {exc}"
                LOG.error(error_msg)
                self.error_occurred.emit(error_msg)
                self.stats_updated.emit({"error": str(exc)})
                self._running = False
                break
            except Exception as exc:
                error_msg = f"Unexpected error: {exc}"
                LOG.error(error_msg, exc_info=True)
                self.error_occurred.emit(error_msg)
                self._running = False
                break

            if frame is None:
                # Timeout, continue waiting
                continue

            try:
                image = frame.image  # RGB numpy array
                height, width, channels = image.shape
                bytes_per_line = channels * width

                if self._detect_enabled:
                    now = time.monotonic() * 1000.0
                    if now - self._last_overlay_time >= self._interval_ms:
                        self._last_overlay_time = now
                        try:
                            bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                            if height > self._downscale_height:
                                scale = self._downscale_height / height
                                small_h = self._downscale_height
                                small_w = int(width * scale)
                                bgr_small = cv2.resize(bgr, (small_w, small_h))
                            else:
                                bgr_small = bgr

                            success, corners = detect_chessboard_corners(bgr_small, self._board_size, refine=False)
                            if success and corners is not None:
                                overlay_small = draw_corners(bgr_small, self._board_size, corners, True)
                                overlay_rgb_small = cv2.cvtColor(overlay_small, cv2.COLOR_BGR2RGB)
                                overlay_rgb = cv2.resize(overlay_rgb_small, (width, height))
                                qt_image = QtGui.QImage(
                                    overlay_rgb.data,
                                    width,
                                    height,
                                    width * 3,
                                    QtGui.QImage.Format_RGB888
                                ).copy()
                            else:
                                qt_image = QtGui.QImage(
                                    image.data,
                                    width,
                                    height,
                                    bytes_per_line,
                                    QtGui.QImage.Format_RGB888
                                ).copy()
                        except Exception as exc:
                            LOG.error("Live detection overlay failed: %s", exc, exc_info=True)
                            qt_image = QtGui.QImage(
                                image.data,
                                width,
                                height,
                                bytes_per_line,
                                QtGui.QImage.Format_RGB888
                            ).copy()
                    else:
                        qt_image = QtGui.QImage(
                            image.data,
                            width,
                            height,
                            bytes_per_line,
                            QtGui.QImage.Format_RGB888
                        ).copy()
                else:
                    qt_image = QtGui.QImage(
                        image.data,
                        width,
                        height,
                        bytes_per_line,
                        QtGui.QImage.Format_RGB888
                    ).copy()

                self.frame_ready.emit(qt_image)

                # Emit statistics
                frame_count += 1
                stats = dict(frame.metadata)
                stats["frame_count"] = frame_count
                self.stats_updated.emit(stats)

            except Exception as exc:
                LOG.error("Error processing frame: %s", exc, exc_info=True)
                continue

        LOG.info("Preview worker stopped (frame_count=%d)", frame_count)

    def stop(self) -> None:
        """Stop the preview worker thread."""
        LOG.debug("Stopping preview worker...")
        self._running = False
        # Wait up to 2 seconds for thread to finish
        if not self.wait(2000):
            LOG.warning("Preview worker did not terminate promptly")
        LOG.debug("Preview worker stopped")

    @QtCore.Slot(bool, tuple)
    def configure_detection(self, enabled: bool, board_size: Tuple[int, int]) -> None:
        """Configure live chessboard detection overlay.

        Args:
            enabled: Whether to enable detection overlay
            board_size: Chessboard size (rows, cols)
        """
        self._detect_enabled = enabled
        self._board_size = board_size
        self._last_overlay_time = 0.0

    def set_detection_rate(self, interval_ms: int = 300, downscale_height: int = 480) -> None:
        """Adjust detection throttling and downscale settings."""
        self._interval_ms = max(50, int(interval_ms))
        self._downscale_height = max(120, int(downscale_height))
