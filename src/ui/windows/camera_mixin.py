import logging
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class CameraConnectWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, service):
        super().__init__()
        self.service = service

    def run(self):
        try:
            success, _camera_info, message = self.service.connect_bound_camera(force_refresh=True)
            if not success:
                self.finished.emit(False, message or "连接绑定相机失败")
                return
            if not self.service.start_preview():
                try:
                    self.service.disconnect_camera()
                except Exception:
                    pass
                self.finished.emit(False, "预览启动失败")
                return
            self.finished.emit(True, "已连接绑定相机")
        except Exception as e:
            self.finished.emit(False, f"Connection error: {e}")


class CameraMixin:
    def refresh_camera_list(self, auto_start: bool = False):
        start_time = datetime.now()
        if not self.camera_service:
            self.update_bound_camera_panel(
                "无相机服务",
                "未绑定",
                "当前窗口未初始化相机服务",
                action_enabled=False,
                connected=False,
            )
            logger.info("Camera refresh took %.2fms (no service)", (datetime.now() - start_time).total_seconds() * 1000)
            return

        try:
            state = self.camera_service.get_bound_camera_runtime_state(force_refresh=False)
            self.update_bound_camera_panel(
                state["summary"],
                state["status_text"],
                state["detail"],
                action_enabled=bool(state["has_binding"]),
                connected=bool(state["connected"]),
            )
            if state["connected"] and state["streaming"] and not self.preview_worker:
                logger.info("Bound camera already streaming, attaching preview worker")
                self.start_camera_preview(force_reconnect=False)
            elif auto_start and state["has_binding"] and state["can_connect"]:
                logger.info("Auto-connecting bound camera for process execution")
                self.start_camera_preview(force_reconnect=False)

        except Exception as e:
            logger.error("Failed to discover cameras: %s", e)
            self.update_bound_camera_panel(
                "绑定相机状态获取失败",
                "连接失败",
                str(e),
                action_enabled=True,
                connected=False,
            )

        total_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info("Camera refresh total took %.2fms", total_time)

    def toggle_camera(self, _checked: bool = False):
        force_reconnect = bool(self.camera_active)
        if self.camera_service and self.camera_service.get_connected_camera():
            force_reconnect = True
        self.start_camera_preview(force_reconnect=force_reconnect)

    def start_camera_preview(self, force_reconnect: bool = False):
        if not self.camera_service:
            logger.warning("No camera service available")
            self.camera_toggle_btn.setEnabled(False)
            return

        state = self.camera_service.get_bound_camera_runtime_state(force_refresh=True)
        if not state["has_binding"]:
            self.show_toast("请先在相机管理页绑定相机", False)
            self.refresh_camera_list(auto_start=False)
            return

        camera_info = state["camera"]
        if not camera_info:
            self.show_toast("未发现已绑定相机，请检查设备是否在线", False)
            self.refresh_camera_list(auto_start=False)
            return

        if camera_info.accessible is False and not state["connected"]:
            self.show_toast("当前绑定相机正在使用中或不可访问", False)
            self.refresh_camera_list(auto_start=False)
            return

        current_device = self.camera_service.get_connected_camera()
        if current_device and state["connected"] and not force_reconnect:
            logger.info("Bound camera %s already connected, attaching preview", camera_info.name)
            if not self.camera_service.is_streaming() and not self.camera_service.start_preview():
                self.show_toast("启动相机预览失败", False)
                return
            self._start_preview_worker(current_device)
            return

        if force_reconnect and current_device:
            self.stop_camera_preview()

        self.camera_toggle_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.camera_toggle_btn.setText("连接中...")
        self.update_bound_camera_panel(
            state["summary"],
            "连接中...",
            state["detail"],
            action_enabled=False,
            connected=False,
        )

        self._connect_worker = CameraConnectWorker(self.camera_service)
        self._connect_worker.finished.connect(self._on_camera_connected)
        self._connect_worker.start()

    def _start_preview_worker(self, camera_device):
        try:
            from ..components.preview_worker import PreviewWorker
            if self.preview_worker:
                self.preview_worker.stop()
                self.preview_worker.wait(1000)
            self.preview_worker = PreviewWorker(camera_device)
            self.preview_worker.frame_ready.connect(self.on_frame_ready)
            self.preview_worker.error_occurred.connect(self.on_preview_error)
            self.preview_worker.start()

            self.camera_active = True
            self.camera_toggle_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.refresh_camera_list(auto_start=False)

            logger.info("Camera preview started for: %s", camera_device.info.name)
            try:
                self.rebuild_status_section()
            except Exception:
                pass

        except Exception as e:
            logger.error("Failed to initialize preview worker: %s", e)
            self.camera_toggle_btn.setText("连接相机")
            self.show_toast(f"预览启动失败: {e}", False)
            if self.preview_worker:
                self.preview_worker.stop()
                self.preview_worker = None

    def _on_camera_connected(self, success: bool, message: str):
        self._connect_worker = None
        if not success:
            self.camera_toggle_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            logger.error("Failed to start camera: %s", message)
            self.camera_toggle_btn.setText("连接相机")
            self.show_toast(f"相机启动失败: {message}", False)
            if self.camera_service.current_camera:
                try:
                    self.camera_service.disconnect_camera()
                except Exception:
                    pass
            self.refresh_camera_list(auto_start=False)
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
            self.camera_toggle_btn.setText("连接相机")
            self.reset_camera_placeholder()
            self.refresh_camera_list(auto_start=False)

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
            try:
                self.refresh_preview_annotation_overlay()
            except Exception:
                pass

    def on_preview_error(self, error_msg: str):
        logger.error("Preview error: %s", error_msg)
        self.stop_camera_preview()

    def reset_camera_placeholder(self):
        self.base_image_label.clear()
        self.base_image_label.setText("等待相机视频")
        self._set_video_state("placeholder")
        try:
            self.refresh_preview_annotation_overlay()
        except Exception:
            pass
