"""Inline camera calibration panel for the camera settings page."""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional

import cv2
from PySide6.QtCore import Qt, QTimer, QSize, Slot
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QDoubleSpinBox,
    QGroupBox,
    QFormLayout,
    QMessageBox,
    QProgressBar,
)

from src.camera.camera_service import CameraService
from src.camera.calibration import (
    CalibrationResult,
    CalibrationService,
    CalibrationStorage,
    ChessboardConfig,
)

logger = logging.getLogger("camera.ui.calibration_panel")


class CameraCalibrationPanel(QFrame):
    """Inline panel that hosts camera calibration workflow."""

    def __init__(self, camera_service: CameraService, parent=None):
        super().__init__(parent)
        self.camera_service = camera_service
        self.calibration_service: Optional[CalibrationService] = None
        self.board_config = ChessboardConfig(rows=9, cols=6, square_size_mm=25.0)

        # UI references
        self.image_list: Optional[QListWidget] = None
        self.rows_spinbox: Optional[QSpinBox] = None
        self.cols_spinbox: Optional[QSpinBox] = None
        self.square_size_spinbox: Optional[QDoubleSpinBox] = None
        self.capture_btn: Optional[QPushButton] = None
        self.calibrate_btn: Optional[QPushButton] = None
        self.clear_btn: Optional[QPushButton] = None
        self.progress_bar: Optional[QProgressBar] = None
        self.status_label: Optional[QLabel] = None
        self.progress_label: Optional[QLabel] = None

        self.setObjectName("cameraCalibrationPanel")
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("""
            #cameraCalibrationPanel QLabel,
            #cameraCalibrationPanel QGroupBox,
            #cameraCalibrationPanel QListWidget,
            #cameraCalibrationPanel QPushButton,
            #cameraCalibrationPanel QSpinBox,
            #cameraCalibrationPanel QDoubleSpinBox {
                color: #E6EAF3;
            }

            #cameraCalibrationPanel QListWidget#calibrationImageList {
                border: 1px solid #2F3744;
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.03);
                padding: 6px;
            }

            #cameraCalibrationPanel QPushButton#calibrationActionButton {
                background-color: #2F3A4D;
                border: 1px solid #3F4B61;
                border-radius: 6px;
                color: #E6EAF3;
                padding: 8px 12px;
            }

            #cameraCalibrationPanel QPushButton#calibrationActionButton:hover:enabled {
                background-color: #3C4961;
            }

            #cameraCalibrationPanel QPushButton#calibrationActionButton:disabled {
                background-color: #1F2633;
                border-color: #2B3345;
                color: #6A7284;
            }
        """)

        self._init_ui()
        self.setVisible(False)

    def _init_ui(self):
        """Build the inline panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header
        title_label = QLabel("相机标定")
        title_label.setObjectName("paramsTitle")
        layout.addWidget(title_label)

        description_label = QLabel("采集棋盘格图像来计算相机内参。")
        description_label.setObjectName("paramLabel")
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        # Chessboard settings
        settings_group = QGroupBox("棋盘格设置")
        settings_group.setObjectName("paramsGroup")
        settings_layout = QFormLayout(settings_group)
        settings_layout.setSpacing(6)

        self.rows_spinbox = QSpinBox()
        self.rows_spinbox.setRange(4, 20)
        self.rows_spinbox.setValue(self.board_config.rows)
        self.rows_spinbox.valueChanged.connect(self._on_board_params_changed)
        settings_layout.addRow("行数:", self.rows_spinbox)

        self.cols_spinbox = QSpinBox()
        self.cols_spinbox.setRange(4, 20)
        self.cols_spinbox.setValue(self.board_config.cols)
        self.cols_spinbox.valueChanged.connect(self._on_board_params_changed)
        settings_layout.addRow("列数:", self.cols_spinbox)

        self.square_size_spinbox = QDoubleSpinBox()
        self.square_size_spinbox.setRange(1.0, 200.0)
        self.square_size_spinbox.setValue(self.board_config.square_size_mm)
        self.square_size_spinbox.setSuffix(" mm")
        self.square_size_spinbox.valueChanged.connect(self._on_board_params_changed)
        settings_layout.addRow("方格大小:", self.square_size_spinbox)

        layout.addWidget(settings_group)

        # Capture progress + list
        self.progress_label = QLabel("已采集: 0/15")
        self.progress_label.setObjectName("paramLabel")
        layout.addWidget(self.progress_label)

        self.image_list = QListWidget()
        self.image_list.setObjectName("calibrationImageList")
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setResizeMode(QListWidget.Adjust)
        self.image_list.setIconSize(QSize(90, 90))
        self.image_list.setGridSize(QSize(100, 110))
        self.image_list.setMinimumHeight(140)
        self.image_list.doubleClicked.connect(self._on_image_double_clicked)
        layout.addWidget(self.image_list)

        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        self.capture_btn = QPushButton("采集图像")
        self.capture_btn.setObjectName("calibrationActionButton")
        self.capture_btn.clicked.connect(self._on_capture_image)
        controls_layout.addWidget(self.capture_btn)

        self.calibrate_btn = QPushButton("执行标定")
        self.calibrate_btn.setObjectName("calibrationActionButton")
        self.calibrate_btn.clicked.connect(self._on_calibrate)
        self.calibrate_btn.setEnabled(False)
        controls_layout.addWidget(self.calibrate_btn)

        self.clear_btn = QPushButton("清除所有")
        self.clear_btn.setObjectName("calibrationActionButton")
        self.clear_btn.clicked.connect(self._on_clear_all)
        controls_layout.addWidget(self.clear_btn)

        layout.addLayout(controls_layout)

        # Progress bar + status
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("请调整棋盘格位置，点击【采集图像】")
        self.status_label.setObjectName("paramLabel")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def activate(self):
        """Show the panel and ensure services are running."""
        if not self.camera_service:
            QMessageBox.warning(self, "错误", "标定服务未初始化")
            return False

        if not self.calibration_service:
            try:
                self.calibration_service = CalibrationService(
                    self.camera_service,
                    min_images=15,
                    max_images=30,
                )
                logger.info("Calibration service initialized in panel")
            except Exception as exc:
                QMessageBox.critical(self, "错误", f"初始化标定服务失败:\n{exc}")
                return False

        self._update_image_list()
        self._update_progress()
        self._set_status("请调整棋盘格位置，点击【采集图像】", "#8C92A0")
        self.setVisible(True)
        return True

    def deactivate(self):
        """Hide panel and stop timers."""
        self.setVisible(False)

    def reset_workflow(self):
        """Reset captured images and UI state."""
        if self.calibration_service:
            self.calibration_service.reset()
        self._update_image_list()
        self._update_progress()
        self._set_status("已清除所有采集的图像", "#8C92A0")

    @Slot()
    def _on_board_params_changed(self):
        """Update board configuration from spin boxes."""
        if not (self.rows_spinbox and self.cols_spinbox and self.square_size_spinbox):
            return
        try:
            self.board_config = ChessboardConfig(
                rows=self.rows_spinbox.value(),
                cols=self.cols_spinbox.value(),
                square_size_mm=self.square_size_spinbox.value(),
            )
            logger.debug("Board config updated: %s", self.board_config)
        except Exception as exc:
            logger.warning("Invalid board parameters: %s", exc)

    @Slot()
    def _on_capture_image(self):
        """Capture calibration image."""
        if not self.calibration_service:
            QMessageBox.warning(self, "错误", "标定服务未初始化")
            return

        self._set_status("正在采集图像...", "#FF8C32")

        try:
            success = self.calibration_service.capture_calibration_image(self.board_config)
            if success:
                self._update_image_list()
                self._update_progress()
                self._set_status("✓ 采集成功", "#3CC37A")
            else:
                self._set_status("✗ 未检测到棋盘格，请调整位置", "#E85454")
        except Exception as exc:
            logger.error("Failed to capture image: %s", exc, exc_info=True)
            self._set_status(f"✗ 采集失败: {exc}", "#E85454")
            QMessageBox.critical(self, "错误", f"图像采集失败:\n{exc}")

    @Slot()
    def _on_calibrate(self):
        """Execute calibration process."""
        if not self.calibration_service:
            QMessageBox.warning(self, "错误", "标定服务未初始化")
            return

        captured, required = self.calibration_service.get_progress()
        if captured < required:
            QMessageBox.warning(self, "提示", f"至少需要 {required} 张有效图像")
            return

        reply = QMessageBox.question(
            self,
            "确认标定",
            f"将使用 {captured} 张图像执行标定计算，是否继续？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._show_progress(True)
        self._set_controls_enabled(False)
        self._set_status("正在执行标定计算...", "#FF8C32")

        QTimer.singleShot(100, self._execute_calibration)

    def _execute_calibration(self):
        """Run calibration and show result."""
        try:
            result = self.calibration_service.calibrate(self.board_config)
            logger.info("Calibration completed, error=%.4f", result.reprojection_error)

            camera = self.camera_service.get_connected_camera()
            file_path: Optional[Path] = None
            if camera:
                storage = CalibrationStorage()
                camera_model = camera.info.model_name or "unknown"
                file_path = storage.save_calibration_result(result, camera_model)
                storage.cleanup_old_calibrations(camera_model, max_files=30)

            self._show_calibration_result(result, file_path)
            self._set_status("✓ 标定完成", "#3CC37A")
        except Exception as exc:
            logger.error("Calibration failed: %s", exc, exc_info=True)
            self._set_status(f"✗ 标定失败: {exc}", "#E85454")
            QMessageBox.critical(self, "标定失败", f"标定计算失败:\n{exc}")
        finally:
            self._show_progress(False)
            self._set_controls_enabled(True)

    def _show_calibration_result(self, result: CalibrationResult, file_path: Optional[Path]):
        """Display calibration summary."""
        message = (
            f"<b>标定完成！</b><br><br>"
            f"<b>重投影误差:</b> {result.reprojection_error:.4f} 像素<br>"
            f"<b>有效图像:</b> {result.valid_images}/{result.total_images}<br>"
            f"<b>图像分辨率:</b> {result.image_resolution[0]}×{result.image_resolution[1]}<br>"
            f"<b>棋盘格:</b> {result.board_size[0]}×{result.board_size[1]}"
            f"，方格大小: {result.square_size_mm}mm<br><br>"
        )

        if file_path:
            message += f"<b>存储路径:</b><br>{file_path}<br>"

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("标定结果")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText("标定已完成")
        msg_box.setInformativeText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)

        if file_path:
            open_btn = msg_box.addButton("打开文件夹", QMessageBox.ActionRole)
            open_btn.clicked.connect(lambda: self._open_folder(file_path.parent))

        msg_box.exec()

    def _open_folder(self, folder_path: Path):
        """Open folder containing calibration results."""
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(str(folder_path))
            elif system == "Darwin":
                subprocess.run(["open", str(folder_path)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder_path)], check=False)
        except Exception as exc:
            logger.error("Failed to open folder: %s", exc)

    @Slot()
    def _on_clear_all(self):
        """Clear captured images."""
        if not self.calibration_service:
            return
        captured, _ = self.calibration_service.get_progress()
        if captured == 0:
            return

        reply = QMessageBox.question(
            self,
            "确认清除",
            f"确定要清除所有 {captured} 张采集的图像吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.reset_workflow()

    def _update_image_list(self):
        """Refresh thumbnails list."""
        if not (self.image_list and self.calibration_service):
            return

        self.image_list.clear()
        for idx, image in enumerate(self.calibration_service.get_images()):
            img_data = image.image_data
            if img_data is None:
                continue

            thumb_img = img_data
            max_side = 90
            if img_data.shape[0] > max_side or img_data.shape[1] > max_side:
                scale = min(max_side / img_data.shape[0], max_side / img_data.shape[1])
                thumb_img = cv2.resize(img_data, None, fx=scale, fy=scale)

            if len(thumb_img.shape) == 3:
                thumb_img = cv2.cvtColor(thumb_img, cv2.COLOR_BGR2RGB)
            else:
                thumb_img = cv2.cvtColor(thumb_img, cv2.COLOR_GRAY2RGB)

            height, width, channel = thumb_img.shape
            bytes_per_line = 3 * width
            qt_image = QImage(thumb_img.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)

            item = QListWidgetItem()
            item.setIcon(QIcon(pixmap))
            item.setText(f"{idx + 1}")
            item.setTextAlignment(Qt.AlignCenter)
            item.setSizeHint(QSize(100, 110))
            self.image_list.addItem(item)

    def _update_progress(self):
        """Update capture progress and button availability."""
        if not (self.progress_label and self.calibration_service):
            return

        captured, required = self.calibration_service.get_progress()
        self.progress_label.setText(f"已采集: {captured}/{required}")

        ready = captured >= required
        self.calibrate_btn.setEnabled(ready)
        if ready and captured == required:
            self._set_status("✓ 已采集足够图像，可以开始标定", "#3CC37A")

    @Slot(object)
    def _on_image_double_clicked(self, index):
        """Remove selected image."""
        if not self.calibration_service or not index or not index.isValid():
            return

        idx = index.row()
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除第 {idx + 1} 张图像吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if self.calibration_service.remove_image(idx):
                self._update_image_list()
                self._update_progress()
                self._set_status(f"已删除图像 {idx + 1}", "#FF8C32")

    def _show_progress(self, show: bool):
        """Display or hide spinner style progress."""
        if self.progress_bar:
            self.progress_bar.setVisible(show)

    def _set_controls_enabled(self, enabled: bool):
        """Toggle capture/calibration controls."""
        for widget in (self.capture_btn, self.clear_btn, self.rows_spinbox,
                       self.cols_spinbox, self.square_size_spinbox):
            if widget:
                widget.setEnabled(enabled)

        if self.calibration_service:
            captured, required = self.calibration_service.get_progress()
            self.calibrate_btn.setEnabled(enabled and captured >= required)
        else:
            self.calibrate_btn.setEnabled(False)

    def _set_status(self, message: str, color: str):
        """Update status banner text."""
        if self.status_label:
            self.status_label.setText(message)
            self.status_label.setStyleSheet(f"color: {color}; padding: 6px;")
