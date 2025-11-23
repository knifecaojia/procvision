"""Camera calibration dialog for intrinsic parameter calibration."""

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QSize
from PySide6.QtGui import QImage, QPixmap, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSpinBox, QDoubleSpinBox,
    QGroupBox, QFormLayout, QMessageBox, QProgressBar,
    QSplitter, QWidget, QFrame, QGridLayout
)

from src.camera.calibration import (
    CalibrationService,
    ChessboardConfig,
    CalibrationResult
)
from src.camera.camera_service import CameraService
from src.ui.components import PreviewWorker
from ..styles import refresh_widget_styles

logger = logging.getLogger("camera.ui.calibration")


class CameraCalibrationDialog(QDialog):
    """Dialog for camera intrinsic calibration using chessboard pattern."""

    def __init__(self, camera_service: CameraService, parent=None):
        """Initialize calibration dialog.

        Args:
            camera_service: Camera service for accessing camera frames
            parent: Parent widget
        """
        super().__init__(parent)
        self.camera_service = camera_service
        self.calibration_service: Optional[CalibrationService] = None
        self.preview_worker: Optional[PreviewWorker] = None
        self.preview_timer: Optional[QTimer] = None
        self.preview_image: Optional[np.ndarray] = None

        # Configuration
        self.board_config = ChessboardConfig(rows=9, cols=6, square_size_mm=20.0)

        # UI references
        self.preview_label: Optional[QLabel] = None
        self.image_list: Optional[QListWidget] = None
        self.rows_spinbox: Optional[QSpinBox] = None
        self.cols_spinbox: Optional[QSpinBox] = None
        self.square_size_spinbox: Optional[QDoubleSpinBox] = None
        self.capture_btn: Optional[QPushButton] = None
        self.calibrate_btn: Optional[QPushButton] = None
        self.clear_btn: Optional[QPushButton] = None
        self.progress_bar: Optional[QProgressBar] = None
        self.status_label: Optional[QLabel] = None

        self.init_ui()
        self.init_calib_service()

    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle("相机内参标定")
        self.setMinimumSize(1000, 700)
        self.setModal(True)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header
        header_label = QLabel("相机内参标定")
        header_label.setObjectName("dialogTitle")
        main_layout.addWidget(header_label)

        # Splitter for main content
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Settings and image list
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)

        # Right panel - Preview
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 1)  # Left panel
        splitter.setStretchFactor(1, 2)  # Right panel (preview larger)
        splitter.setSizes([300, 600])

        main_layout.addWidget(splitter)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        main_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("请调整棋盘格位置，点击【采集图像】")
        self.status_label.setObjectName("calibrationStatusLabel")
        self.status_label.setProperty("statusLevel", "info")
        main_layout.addWidget(self.status_label)

        # Initialize preview timer
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start(200)  # 200ms = 5 FPS

    def init_calib_service(self):
        """Initialize calibration service."""
        try:
            self.calibration_service = CalibrationService(
                self.camera_service,
                min_images=15,
                max_images=30
            )
            logger.info("Calibration service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize calibration service: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"初始化标定服务失败:\n{e}")

    def _set_status_level(self, level: str) -> None:
        if self.status_label:
            self.status_label.setProperty("statusLevel", level)
            refresh_widget_styles(self.status_label)

    def _create_left_panel(self) -> QWidget:
        """Create left panel with settings and image list."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Settings group
        settings_group = QGroupBox("棋盘格设置")
        settings_group.setObjectName("settingsGroup")
        settings_layout = QFormLayout()
        settings_layout.setSpacing(10)

        # Rows spinbox
        self.rows_spinbox = QSpinBox()
        self.rows_spinbox.setRange(4, 20)
        self.rows_spinbox.setValue(9)
        self.rows_spinbox.valueChanged.connect(self._on_board_params_changed)
        settings_layout.addRow("行数:", self.rows_spinbox)

        # Cols spinbox
        self.cols_spinbox = QSpinBox()
        self.cols_spinbox.setRange(4, 20)
        self.cols_spinbox.setValue(6)
        self.cols_spinbox.valueChanged.connect(self._on_board_params_changed)
        settings_layout.addRow("列数:", self.cols_spinbox)

        # Square size spinbox
        self.square_size_spinbox = QDoubleSpinBox()
        self.square_size_spinbox.setRange(1.0, 200.0)
        self.square_size_spinbox.setValue(20.0)
        self.square_size_spinbox.setSuffix(" mm")
        self.square_size_spinbox.valueChanged.connect(self._on_board_params_changed)
        settings_layout.addRow("方格大小:", self.square_size_spinbox)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Image list group
        image_list_group = QGroupBox("采集的图像")
        image_list_layout = QVBoxLayout()
        image_list_layout.setSpacing(5)

        # Progress label
        self.progress_label = QLabel("已采集: 0/15")
        image_list_layout.addWidget(self.progress_label)

        # Image list
        self.image_list = QListWidget()
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setIconSize(QSize(100, 100))
        self.image_list.setResizeMode(QListWidget.Adjust)
        self.image_list.setGridSize(QSize(110, 120))
        self.image_list.doubleClicked.connect(self._on_image_double_clicked)
        image_list_layout.addWidget(self.image_list)

        image_list_group.setLayout(image_list_layout)
        layout.addWidget(image_list_group)

        # Control buttons
        button_layout = QGridLayout()
        button_layout.setSpacing(10)

        self.capture_btn = QPushButton("采集图像")
        self.capture_btn.clicked.connect(self._on_capture_image)
        button_layout.addWidget(self.capture_btn, 0, 0)

        self.calibrate_btn = QPushButton("执行标定")
        self.calibrate_btn.setObjectName("calibrateButton")
        self.calibrate_btn.clicked.connect(self._on_calibrate)
        self.calibrate_btn.setEnabled(False)
        button_layout.addWidget(self.calibrate_btn, 0, 1)

        self.clear_btn = QPushButton("清除所有")
        self.clear_btn.clicked.connect(self._on_clear_all)
        button_layout.addWidget(self.clear_btn, 1, 0)

        layout.addLayout(button_layout)
        layout.addStretch()

        return panel

    def _create_right_panel(self) -> QWidget:
        """Create right panel with preview."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Preview label
        self.preview_label = QLabel()
        self.preview_label.setObjectName("calibrationPreview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(600, 450)

        layout.addWidget(self.preview_label)

        # Preview info
        info_label = QLabel("实时预览 (棋盘格检测)")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setObjectName("infoLabel")
        layout.addWidget(info_label)

        return panel

    @Slot()
    def _on_board_params_changed(self):
        """Update board configuration when parameters change."""
        try:
            self.board_config = ChessboardConfig(
                rows=self.rows_spinbox.value(),
                cols=self.cols_spinbox.value(),
                square_size_mm=self.square_size_spinbox.value()
            )
            logger.debug(f"Board config updated: {self.board_config.board_size}, "
                        f"square_size={self.board_config.square_size_mm}")
        except Exception as e:
            logger.warning(f"Invalid board parameters: {e}")

    @Slot()
    def _on_capture_image(self):
        """Handle capture image button click."""
        if not self.calibration_service:
            QMessageBox.warning(self, "错误", "标定服务未初始化")
            return

        self.status_label.setText("正在采集图像...")
        self._set_status_level("warning")

        try:
            # Capture calibration image
            success = self.calibration_service.capture_calibration_image(self.board_config)

            if success:
                self._update_image_list()
                self._update_progress()
                self.status_label.setText("✓ 采集成功")
                self._set_status_level("success")
                logger.info("Image captured successfully")
            else:
                self.status_label.setText("✗ 未检测到棋盘格，请调整位置")
                self._set_status_level("error")
                logger.warning("Chessboard not detected")

        except Exception as e:
            logger.error(f"Failed to capture image: {e}", exc_info=True)
            self.status_label.setText(f"✗ 采集失败: {str(e)}")
            self._set_status_level("error")
            QMessageBox.critical(self, "错误", f"图像采集失败:\n{e}")

    @Slot()
    def _on_calibrate(self):
        """Handle calibrate button click."""
        if not self.calibration_service:
            QMessageBox.warning(self, "错误", "标定服务未初始化")
            return

        # Confirm calibration
        captured, required = self.calibration_service.get_progress()
        reply = QMessageBox.question(
            self,
            "确认标定",
            f"将使用 {captured} 张图像执行标定计算，是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Show progress
        self._show_progress(True)
        self.status_label.setText("正在执行标定计算...")
        self._set_status_level("warning")

        # Disable controls
        self._set_controls_enabled(False)

        # Run calibration in background (using QTimer to avoid blocking)
        QTimer.singleShot(100, self._execute_calibration)

    def _execute_calibration(self):
        """Execute calibration computation."""
        try:
            result = self.calibration_service.calibrate(self.board_config)
            logger.info(f"Calibration completed with error: {result.reprojection_error:.4f}")

            # Save result
            camera = self.camera_service.get_connected_camera()
            if camera:
                camera_model = camera.info.model_name or "unknown"
                from src.camera.calibration import CalibrationStorage
                storage = CalibrationStorage()
                file_path = storage.save_calibration_result(result, camera_model)

                # Cleanup old files
                storage.cleanup_old_calibrations(camera_model, max_files=30)

            # Show result dialog
            self._show_calibration_result(result, file_path)

        except Exception as e:
            logger.error(f"Calibration failed: {e}", exc_info=True)
            self.status_label.setText(f"✗ 标定失败: {str(e)}")
            self._set_status_level("error")
            QMessageBox.critical(self, "标定失败", f"标定计算失败:\n{e}")

        finally:
            self._show_progress(False)
            self._set_controls_enabled(True)

    def _show_calibration_result(self, result: CalibrationResult, file_path: Path):
        """Show calibration result dialog."""
        # Format message
        message = f"""
<b>标定完成！</b><br><br>

<b>重投影误差:</b> {result.reprojection_error:.4f} 像素<br>
{"<font color='#3CC37A'>✓ 优秀 (&lt;0.5)</font>" if result.reprojection_error < 0.5
 else "<font color='#FF8C32'>✓ 良好 (&lt;1.0)</font>" if result.reprojection_error < 1.0
 else "<font color='#FFB347'>△ 一般 (&lt;2.0)</font>" if result.reprojection_error < 2.0
 else "<font color='#E85454'>✗ 较差 (≥2.0)</font>"}<br><br>

<b>有效图像:</b> {result.valid_images}/{result.total_images}<br>
<b>图像分辨率:</b> {result.image_resolution[0]}×{result.image_resolution[1]}<br>
<b>棋盘格:</b> {result.board_size[0]}×{result.board_size[1]}，方格大小: {result.square_size_mm}mm<br><br>

<b>存储路径:</b><br>
{file_path}<br>
"""

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("标定结果")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText("标定已完成")
        msg_box.setInformativeText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)

        # Add "Open Folder" button
        open_btn = msg_box.addButton("打开文件夹", QMessageBox.ActionRole)
        open_btn.clicked.connect(lambda: self._open_folder(file_path.parent))

        msg_box.exec()

        self.status_label.setText("✓ 标定完成")
        self._set_status_level("success")

    def _open_folder(self, folder_path: Path):
        """Open folder in file explorer."""
        import subprocess
        import platform
        import os

        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(str(folder_path))
            elif system == "Darwin":  # macOS
                subprocess.run(["open", str(folder_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(folder_path)])
        except Exception as e:
            logger.error(f"Failed to open folder: {e}")

    @Slot()
    def _on_clear_all(self):
        """Handle clear all button click."""
        if not self.calibration_service:
            return

        if self.calibration_service.get_progress()[0] == 0:
            return

        reply = QMessageBox.question(
            self,
            "确认清除",
            f"确定要清除所有 {len(self.calibration_service.get_images())} 张采集的图像吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.calibration_service.reset()
            self._update_image_list()
            self._update_progress()
            self.status_label.setText("已清除所有图像")
            self._set_status_level("info")

    @Slot()
    def update_preview(self):
        """Update preview image with corner detection."""
        if not self.camera_service or not self.preview_label:
            return

        try:
            camera = self.camera_service.get_connected_camera()
            if not camera:
                return

            frame_data = camera.get_frame(timeout_ms=100)
            if not frame_data or not frame_data.image:
                return

            image = frame_data.image
            self.preview_image = image.copy()

            # Detect corners on preview (fast, low resolution)
            # Resize for faster detection
            if image.shape[0] > 480:
                scale = 480 / image.shape[0]
                preview_h = 480
                preview_w = int(image.shape[1] * scale)
                preview_img = cv2.resize(image, (preview_w, preview_h))
            else:
                preview_img = image

            success, corners = detect_chessboard_corners(
                preview_img,
                self.board_config.board_size,
                refine=False  # Faster for preview
            )

            # Draw detection result
            if success:
                preview_img = cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB)
                cv2.drawChessboardCorners(
                    preview_img,
                    self.board_config.board_size,
                    corners,
                    True
                )
            else:
                preview_img = cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB)

            # Convert to Qt format
            height, width, channel = preview_img.shape
            bytes_per_line = 3 * width
            qt_image = QImage(preview_img.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)

            # Scale to fit label
            scaled_pixmap = pixmap.scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            self.preview_label.setPixmap(scaled_pixmap)

        except Exception as e:
            logger.debug(f"Preview update failed: {e}")

    def _update_image_list(self):
        """Update the image list widget with thumbnails."""
        if not self.image_list or not self.calibration_service:
            return

        self.image_list.clear()

        for idx, img in enumerate(self.calibration_service.get_images()):
            if img.image_data is not None:
                # Create thumbnail (100x100)
                thumb_h, thumb_w = 100, 100
                if img.image_data.shape[0] > thumb_h or img.image_data.shape[1] > thumb_w:
                    # Calculate scale to fit within thumbnail size
                    scale = min(thumb_h / img.image_data.shape[0],
                               thumb_w / img.image_data.shape[1])
                    thumb_img = cv2.resize(img.image_data, None, fx=scale, fy=scale)
                else:
                    thumb_img = img.image_data

                # Convert to RGB for Qt
                if len(thumb_img.shape) == 3:
                    thumb_img = cv2.cvtColor(thumb_img, cv2.COLOR_BGR2RGB)
                else:
                    thumb_img = cv2.cvtColor(thumb_img, cv2.COLOR_GRAY2RGB)

                # Create QImage and QPixmap
                height, width, channel = thumb_img.shape
                bytes_per_line = 3 * width
                qt_image = QImage(thumb_img.data, width, height, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)

                # Create list item
                item = QListWidgetItem()
                item.setIcon(QIcon(pixmap))
                item.setText(f"{idx + 1}")
                item.setTextAlignment(Qt.AlignCenter)
                item.setSizeHint(QSize(110, 120))

                self.image_list.addItem(item)

    def _update_progress(self):
        """Update progress label and buttons."""
        if not self.calibration_service:
            return

        captured, required = self.calibration_service.get_progress()
        self.progress_label.setText(f"已采集: {captured}/{required}")

        # Enable/disable calibrate button
        if captured >= required:
            self.calibrate_btn.setEnabled(True)
            if captured == required:
                self.status_label.setText("✓ 已采集足够图像，可以开始标定")
                self._set_status_level("success")
        else:
            self.calibrate_btn.setEnabled(False)

    def _on_image_double_clicked(self, index):
        """Handle image list double click (remove image)."""
        if not self.calibration_service:
            return

        idx = index.row()
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除第 {idx + 1} 张图像吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.calibration_service.remove_image(idx):
                self._update_image_list()
                self._update_progress()
                self.status_label.setText(f"已删除图像 {idx + 1}")
                self._set_status_level("warning")

    def _show_progress(self, show: bool):
        """Show/hide progress bar."""
        if self.progress_bar:
            self.progress_bar.setVisible(show)

    def _set_controls_enabled(self, enabled: bool):
        """Enable/disable dialog controls."""
        if self.capture_btn:
            self.capture_btn.setEnabled(enabled)
        if self.calibrate_btn:
            self.calibrate_btn.setEnabled(enabled and self.calibration_service.get_progress()[0] >= 15)
        if self.clear_btn:
            self.clear_btn.setEnabled(enabled)
        if self.rows_spinbox:
            self.rows_spinbox.setEnabled(enabled)
        if self.cols_spinbox:
            self.cols_spinbox.setEnabled(enabled)
        if self.square_size_spinbox:
            self.square_size_spinbox.setEnabled(enabled)

    def closeEvent(self, event):
        """Handle dialog close event."""
        if self.calibration_service:
            captured, _ = self.calibration_service.get_progress()
            if captured > 0:
                reply = QMessageBox.question(
                    self,
                    "确认关闭",
                    f"已采集 {captured} 张图像，是否放弃并关闭？",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply != QMessageBox.Yes:
                    event.ignore()
                    return

        # Cleanup
        if self.preview_timer:
            self.preview_timer.stop()

        event.accept()
