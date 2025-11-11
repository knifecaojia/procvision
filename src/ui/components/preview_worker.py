"""PreviewWorker - QThread for camera frame acquisition."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6 import QtCore, QtGui

from src.camera.camera_device import CameraDevice
from src.camera.exceptions import CameraError

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
                break
            except Exception as exc:
                error_msg = f"Unexpected error: {exc}"
                LOG.error(error_msg, exc_info=True)
                self.error_occurred.emit(error_msg)
                break

            if frame is None:
                # Timeout, continue waiting
                continue

            try:
                # Convert numpy array to QImage
                image = frame.image
                height, width, channels = image.shape
                bytes_per_line = channels * width

                # Create QImage from frame data
                qt_image = QtGui.QImage(
                    image.data,
                    width,
                    height,
                    bytes_per_line,
                    QtGui.QImage.Format_RGB888
                ).copy()  # Important: copy to avoid data corruption

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
        self.wait(2000)
        LOG.debug("Preview worker stopped")
