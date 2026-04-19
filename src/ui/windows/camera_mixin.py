import logging
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class CameraConnectWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, service, camera_info):
        super().__init__()
        self.service = service
        self.info = camera_info

    def run(self):
        try:
            if not self.service.connect_camera(self.info):
                self.finished.emit(False, "Failed to connect to camera")
                return
            device = self.service.get_connected_camera()
            if not device:
                self.finished.emit(False, "No camera device retrieved after connection")
                return
            try:
                device.start_stream()
            except Exception as e:
                try:
                    self.service.disconnect_camera()
                except Exception:
                    pass
                self.finished.emit(False, f"Failed to start stream: {e}")
                return
            self.finished.emit(True, "Connected")
        except Exception as e:
            self.finished.emit(False, f"Connection error: {e}")


class CameraMixin:
    def refresh_camera_list(self, auto_start: bool = False):
        start_time = datetime.now()
        self.camera_combo.clear()
        self.available_cameras = []

        if not self.camera_service:
            self.camera_combo.addItem("无相机服务")
            self.camera_combo.setVisible(False)
            self.refresh_btn.setVisible(False)
            self.camera_toggle_btn.setVisible(False)
            logger.info("Camera refresh took %.2fms (no service)", (datetime.now() - start_time).total_seconds() * 1000)
            return

        try:
            cameras = self.camera_service.discover_cameras(force_refresh=False)
            self.available_cameras = cameras
            count = len(cameras)

            if cameras:
                for camera in cameras:
                    serial = camera.serial_number or "N/A"
                    self.camera_combo.addItem(f"{camera.name} ({serial})")
                logger.info("Found %d cameras", count)
            else:
                self.camera_combo.addItem("未发现相机")
                logger.warning("No cameras found")

            connected_device = self.camera_service.get_connected_camera()
            is_streaming = self.camera_service.is_streaming()

            if connected_device and is_streaming:
                logger.info("Camera already connected: %s, resuming preview", connected_device.info.name)
                index = -1
                for i, cam in enumerate(cameras):
                    if cam.id == connected_device.info.id:
                        index = i
                        break
                if index >= 0:
                    self.camera_combo.setCurrentIndex(index)

                if auto_start and count <= 1:
                    self.camera_combo.setVisible(False)
                    self.refresh_btn.setVisible(False)
                    self.camera_toggle_btn.setVisible(False)
                else:
                    self.camera_combo.setVisible(True)
                    self.refresh_btn.setVisible(True)
                    self.camera_toggle_btn.setVisible(True)

                self.start_camera_preview()
                return

            if auto_start:
                if count <= 1:
                    self.camera_combo.setVisible(False)
                    self.refresh_btn.setVisible(False)
                    if count == 1:
                        self.camera_toggle_btn.setVisible(False)
                        logger.info("Auto-starting single available camera")
                        self.camera_toggle_btn.setChecked(True)
                        self.start_camera_preview()
                    else:
                        self.camera_toggle_btn.setVisible(False)
                else:
                    self.camera_combo.setVisible(True)
                    self.refresh_btn.setVisible(True)
                    self.camera_toggle_btn.setVisible(True)
            else:
                if count > 1:
                    self.camera_combo.setVisible(True)
                    self.refresh_btn.setVisible(True)
                    self.camera_toggle_btn.setVisible(True)

        except Exception as e:
            logger.error("Failed to discover cameras: %s", e)
            self.camera_combo.addItem("相机发现失败")
            self.camera_combo.setVisible(True)
            self.refresh_btn.setVisible(True)
            self.camera_toggle_btn.setVisible(True)

        total_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info("Camera refresh total took %.2fms", total_time)

    def toggle_camera(self, checked: bool):
        if checked:
            self.start_camera_preview()
        else:
            self.stop_camera_preview()

    def start_camera_preview(self):
        if not self.camera_service:
            logger.warning("No camera service available")
            self.camera_toggle_btn.setChecked(False)
            return
        if not self.available_cameras:
            logger.warning("No cameras available")
            self.camera_toggle_btn.setChecked(False)
            return

        camera_index = self.camera_combo.currentIndex()
        if camera_index < 0 or camera_index >= len(self.available_cameras):
            logger.warning("Invalid camera selection")
            self.camera_toggle_btn.setChecked(False)
            return

        camera_info = self.available_cameras[camera_index]
        current_device = self.camera_service.get_connected_camera()
        if current_device and current_device.info.id == camera_info.id:
            logger.info("Camera %s already connected, attaching preview", camera_info.name)
            if not self.camera_service.is_streaming():
                self.camera_service.start_preview()
            self._start_preview_worker(current_device)
            return

        self.camera_toggle_btn.setEnabled(False)
        self.camera_combo.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.camera_toggle_btn.setText("连接中...")

        self._connect_worker = CameraConnectWorker(self.camera_service, camera_info)
        self._connect_worker.finished.connect(lambda success, msg: self._on_camera_connected(success, msg, camera_info))
        self._connect_worker.start()

    def _start_preview_worker(self, camera_device):
        try:
            from ..components.preview_worker import PreviewWorker
            self.preview_worker = PreviewWorker(camera_device)
            self.preview_worker.frame_ready.connect(self.on_frame_ready)
            self.preview_worker.error_occurred.connect(self.on_preview_error)
            self.preview_worker.start()

            self.camera_active = True
            self.camera_toggle_btn.setText("📷 停止相机")
            self.camera_toggle_btn.setChecked(True)
            self.camera_toggle_btn.setEnabled(True)
            self.camera_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)

            logger.info("Camera preview started for: %s", camera_device.info.name)
            try:
                self.rebuild_status_section()
            except Exception:
                pass

        except Exception as e:
            logger.error("Failed to initialize preview worker: %s", e)
            self.camera_toggle_btn.setChecked(False)
            self.camera_toggle_btn.setText("📷 启动相机")
            self.show_toast(f"预览启动失败: {e}", False)
            if self.preview_worker:
                self.preview_worker.stop()
                self.preview_worker = None

    def _on_camera_connected(self, success: bool, message: str, camera_info):
        self._connect_worker = None
        if not success:
            self.camera_toggle_btn.setEnabled(True)
            self.camera_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            logger.error("Failed to start camera: %s", message)
            self.camera_toggle_btn.setChecked(False)
            self.camera_toggle_btn.setText("📷 启动相机")
            self.show_toast(f"相机启动失败: {message}", False)
            if self.camera_service.current_camera:
                try:
                    self.camera_service.disconnect_camera()
                except Exception:
                    pass
            return
        try:
            camera_device = self.camera_service.get_connected_camera()
            self._start_preview_worker(camera_device)
        except Exception as e:
            logger.error("Error in _on_camera_connected: %s", e)
            self.camera_toggle_btn.setEnabled(True)

    def stop_camera_preview(self):
        try:
            if self.preview_worker:
                self.preview_worker.stop()
                self.preview_worker.wait(1000)
                self.preview_worker = None
            if self.camera_service and self.camera_service.current_camera:
                try:
                    self.camera_service.current_camera.stop_stream()
                except Exception:
                    pass
            try:
                self.camera_service.disconnect_camera()
            except Exception:
                pass

            self.camera_active = False
            self.camera_toggle_btn.setText("📷 启动相机")
            self.camera_toggle_btn.setChecked(False)
            self.reset_camera_placeholder()

            logger.info("Camera preview stopped")
            try:
                self.rebuild_status_section()
            except Exception:
                pass
        except Exception as e:
            logger.error("Error stopping camera preview: %s", e)

    def on_frame_ready(self, qimage: QImage):
        if not self.camera_active:
            return
        if getattr(self, "_debug_input_enabled", False):
            return
        pixmap = QPixmap.fromImage(qimage)
        if not pixmap.isNull():
            try:
                self._last_frame_size = qimage.size()
            except Exception:
                self._last_frame_size = None
            self._last_qimage = qimage
            scaled_pixmap = pixmap.scaled(
                self.base_image_label.width(),
                self.base_image_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            try:
                self._last_display_size = scaled_pixmap.size()
            except Exception:
                self._last_display_size = None
            self.base_image_label.setPixmap(scaled_pixmap)
            self._set_video_state("active")

    def on_preview_error(self, error_msg: str):
        logger.error("Preview error: %s", error_msg)
        self.stop_camera_preview()

    def reset_camera_placeholder(self):
        self.base_image_label.clear()
        self.base_image_label.setText("等待相机视频")
        self._set_video_state("placeholder")
