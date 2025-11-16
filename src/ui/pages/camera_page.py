"""
Camera settings page for the industrial vision system with Hikvision camera integration.
"""

import logging
from pathlib import Path
from typing import Optional

 
from PySide6.QtCore import Qt, QSize, Slot, QTimer
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QGridLayout, QSizePolicy,
    QToolButton, QMessageBox, QInputDialog, QScrollArea, QFormLayout,
    QListWidget, QListWidgetItem, QSpinBox, QDoubleSpinBox,
    QGroupBox, QProgressBar, QLayout
)

from src.camera.camera_service import CameraService
from src.camera.types import CameraInfo
from src.camera.calibration import (
    CalibrationService,
    ChessboardConfig,
    CalibrationResult,
    CalibrationStorage
)
from src.ui.components import SliderField, PreviewWorker
from .camera_calibration_panel import CameraCalibrationPanel

logger = logging.getLogger("camera.ui")


class CameraPage(QFrame):
    """Camera settings page with live preview and parameter controls."""

    def __init__(self, camera_service: Optional[CameraService], parent=None):
        super().__init__(parent)
        self.setObjectName("cameraPage")
        self.camera_service = camera_service
        self._service_warning_shown = False
        self.preview_worker: Optional[PreviewWorker] = None
        self.parameter_sliders = {}
        self.current_username = "admin"  # TODO: Get from session
        self.params_frame: Optional[QFrame] = None
        self.assets_dir = Path(__file__).resolve().parents[2] / "assets"

        # UI references
        self.preview_label: Optional[QLabel] = None
        self.model_value_label: Optional[QLabel] = None
        self.status_value_label: Optional[QLabel] = None
        self.temp_value_label: Optional[QLabel] = None
        self.fps_value_label: Optional[QLabel] = None
        self.preset_combo: Optional[QComboBox] = None
        self.params_container: Optional[QFrame] = None
        self.param_controls_holder: Optional[QFrame] = None
        self.param_controls_layout: Optional[QVBoxLayout] = None
        self.calibration_panel_container: Optional[QFrame] = None
        self.calibration_panel: Optional[CameraCalibrationPanel] = None
        self.calibration_panel_visible = False
        self.calibration_live_detect_enabled: bool = False
        self._last_overlay_time: float = 0.0
        self._overlay_interval_ms: int = 300

        # Control buttons
        self.connect_btn: Optional[QToolButton] = None
        self.disconnect_btn: Optional[QToolButton] = None
        self.start_preview_btn: Optional[QToolButton] = None
        self.stop_preview_btn: Optional[QToolButton] = None
        self.screenshot_btn: Optional[QToolButton] = None

        self.init_ui()
        self.update_connection_state()

    def init_ui(self):
        """Initialize the camera page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header section
        header_frame = QFrame()
        header_frame.setObjectName("cameraHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("相机设置")
        title_label.setObjectName("cameraTitle")

        header_layout.addWidget(title_label)
        header_layout.addStretch()

        layout.addWidget(header_frame)

        # Main content - Vertical layout dividing top and bottom sections
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # Top section - Horizontal layout with preview on left and parameters on right
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)

        # Left side - Camera preview and controls
        preview_frame = self._create_preview_section()

        # Right side - Camera parameters
        params_frame = self._create_parameters_section()

        top_layout.addWidget(preview_frame)
        top_layout.addWidget(params_frame)

        # Bottom section - Camera status info
        status_frame = self._create_status_section()

        main_layout.addLayout(top_layout)
        main_layout.addWidget(status_frame)

        layout.addLayout(main_layout)

    def _require_service(self, action: str) -> bool:
        """Ensure camera service exists before doing work."""
        if self.camera_service:
            return True

        message = (
            "当前未初始化相机服务，相关功能已禁用。\n请通过完整应用启动或联系管理员。"
            if not self._service_warning_shown
            else f"无法{action}，相机服务未初始化。"
        )
        self._service_warning_shown = True

        QMessageBox.warning(
            self,
            "相机服务不可用",
            message,
        )
        logger.warning("Camera service unavailable for action: %s", action)
        return False

    def _apply_service_unavailable_state(self):
        """Disable interactive controls when camera service is missing."""
        for button in (self.connect_btn, self.disconnect_btn, self.start_preview_btn, self.stop_preview_btn, self.screenshot_btn, self.calibrate_btn):
            if button:
                button.setEnabled(False)
        if self.calibrate_btn:
            self._set_calibrate_button_checked(False)

        if self.preview_label:
            self.preview_label.setText("相机服务不可用\n请通过完整应用启动")

        if self.model_value_label:
            self.model_value_label.setText("不可用")

        if self.status_value_label:
            self.status_value_label.setText("服务不可用")
            self.status_value_label.setStyleSheet("color: #8C92A0;")

        if self.temp_value_label:
            self.temp_value_label.setText("--")

        if self.fps_value_label:
            self.fps_value_label.setText("0 FPS")
        self._set_params_panel_visible(False)

    def _set_params_panel_visible(self, visible: bool):
        """Show or hide the parameter panel."""
        if self.params_frame:
            self.params_frame.setVisible(visible)
        if not visible:
            self._hide_calibration_panel()

    def _clear_layout(self, layout: QLayout):
        """Remove all child widgets/layouts from the given layout."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget:
                widget.deleteLater()
            if child_layout:
                self._clear_layout(child_layout)

    def _ensure_calibration_panel(self) -> Optional[CameraCalibrationPanel]:
        """Create calibration panel widget if needed."""
        if not self.camera_service:
            return None

        if not self.calibration_panel:
            self.calibration_panel = CameraCalibrationPanel(self.camera_service, self)
            if self.calibration_panel_container and self.calibration_panel_container.layout():
                self.calibration_panel_container.layout().addWidget(self.calibration_panel)
            if self.calibration_panel.live_detect_checkbox:
                try:
                    self.calibration_panel.live_detect_checkbox.toggled.connect(
                        self._on_live_detect_state_changed
                    )
                except Exception:
                    # Fallback for environments lacking toggled
                    self.calibration_panel.live_detect_checkbox.stateChanged.connect(
                        lambda state: self._on_live_detect_state_changed(state == Qt.Checked)
                    )
            try:
                if self.calibration_panel.rows_spinbox:
                    self.calibration_panel.rows_spinbox.valueChanged.connect(lambda _: self._apply_detection_config())
                if self.calibration_panel.cols_spinbox:
                    self.calibration_panel.cols_spinbox.valueChanged.connect(lambda _: self._apply_detection_config())
            except Exception:
                pass
            self.calibration_live_detect_enabled = (
                self.calibration_panel.live_detect_checkbox.isChecked()
                if self.calibration_panel.live_detect_checkbox else False
            )

        return self.calibration_panel

    def _hide_calibration_panel(self):
        """Hide calibration panel and stop its activity."""
        if self.calibration_panel:
            self.calibration_panel.deactivate()
        self.calibration_panel_visible = False
        if self.calibration_panel_container:
            self.calibration_panel_container.setVisible(False)
        self._set_calibrate_button_checked(False)
        self.calibration_live_detect_enabled = False
        self._apply_detection_config()

    def _set_calibrate_button_checked(self, checked: bool):
        """Helper to update calibrate button state without triggering callbacks."""
        if self.calibrate_btn:
            self.calibrate_btn.blockSignals(True)
            self.calibrate_btn.setChecked(checked)
            self.calibrate_btn.blockSignals(False)

    def _create_preview_section(self) -> QFrame:
        """Create the preview section with controls and preview area."""
        preview_frame = QFrame()
        preview_frame.setObjectName("previewFrame")
        preview_frame.setMinimumWidth(560)
        preview_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(10)

        # Camera control toolbar
        controls_frame = QFrame()
        controls_frame.setObjectName("previewToolbar")
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(8, 0, 8, 0)
        controls_layout.setSpacing(2)
        controls_frame.setFixedHeight(45)

        control_specs = [
            ("connect", "连接相机", "connect.svg", "⦿", self.on_connect_camera),
            ("disconnect", "断开连接", "disconnect.svg", "⦸", self.on_disconnect_camera),
            ("startPreview", "开始预览", "preview.svg", "▶", self.on_start_preview),
            ("stopPreview", "停止预览", "stop.svg", "■", self.on_stop_preview),
            ("screenshot", "截图", "snapshot.svg", "⎙", self.on_screenshot),
            ("calibrate", "相机标定", "calibrate.svg", "📐", self.on_calibrate_camera),
        ]

        for control_id, tooltip, icon_name, fallback_symbol, callback in control_specs:
            button = QToolButton()
            button.setObjectName("previewToolButton")
            button.setProperty("controlId", control_id)
            button.setToolTip(tooltip)
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedSize(32, 32)
            if control_id == "calibrate":
                button.setCheckable(True)
            button.clicked.connect(callback)

            icon_path = self.assets_dir / icon_name
            if icon_path.exists():
                button.setIcon(QIcon(str(icon_path)))
                button.setIconSize(QSize(20, 20))
            else:
                button.setText(fallback_symbol)
                button.setStyleSheet("font-size: 24px;")

            controls_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)

            # Store button references
            if control_id == "connect":
                self.connect_btn = button
            elif control_id == "disconnect":
                self.disconnect_btn = button
            elif control_id == "startPreview":
                self.start_preview_btn = button
            elif control_id == "stopPreview":
                self.stop_preview_btn = button
            elif control_id == "screenshot":
                self.screenshot_btn = button
            elif control_id == "calibrate":
                self.calibrate_btn = button

        controls_layout.addStretch()

        # Camera preview area
        self.preview_label = QLabel("相机预览区域\n请先连接相机")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_label.setScaledContents(False)

        preview_layout.addWidget(controls_frame)
        preview_layout.addWidget(self.preview_label)

        return preview_frame

    def _create_parameters_section(self) -> QFrame:
        """Create the parameters section with sliders and presets."""
        params_frame = QFrame()
        params_frame.setObjectName("paramsFrame")
        params_frame.setFixedWidth(400)
        self.params_frame = params_frame

        params_layout = QVBoxLayout(params_frame)
        params_layout.setContentsMargins(20, 20, 20, 20)
        params_layout.setSpacing(15)

        # Parameters title
        params_title = QLabel("相机参数")
        params_title.setObjectName("paramsTitle")
        params_layout.addWidget(params_title)

        # Scrollable parameters container
        scroll_area = QScrollArea()
        scroll_area.setObjectName("paramsScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #1F232B;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #8C92A0;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #FF8C32;
            }
        """)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.viewport().setStyleSheet("background: transparent;")
        scroll_area.viewport().setAutoFillBackground(False)

        self.params_container = QFrame()
        self.params_container.setObjectName("paramsContainer")
        self.params_container.setStyleSheet("background: transparent;")
        self.params_container.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        container_layout = QVBoxLayout(self.params_container)
        container_layout.setContentsMargins(0, 0, 0, 10)
        container_layout.setSpacing(15)

        self.param_controls_holder = QFrame()
        self.param_controls_holder.setObjectName("paramControlsHolder")
        self.param_controls_layout = QVBoxLayout(self.param_controls_holder)
        self.param_controls_layout.setContentsMargins(0, 0, 0, 0)
        self.param_controls_layout.setSpacing(15)
        container_layout.addWidget(self.param_controls_holder)

        self.calibration_panel_container = QFrame()
        self.calibration_panel_container.setObjectName("calibrationPanelContainer")
        self.calibration_panel_container.setVisible(False)
        calib_layout = QVBoxLayout(self.calibration_panel_container)
        calib_layout.setContentsMargins(0, 0, 0, 0)
        calib_layout.setSpacing(10)

        container_layout.addWidget(self.calibration_panel_container)
        container_layout.addStretch()

        scroll_area.setWidget(self.params_container)

        params_layout.addWidget(scroll_area)

        return params_frame

    def _create_status_section(self) -> QFrame:
        """Create the status section showing camera info."""
        status_frame = QFrame()
        status_frame.setObjectName("statusFrame")
        status_frame.setFixedHeight(110)

        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(15, 10, 15, 10)
        status_layout.setSpacing(8)

        status_title = QLabel("相机状态")
        status_title.setObjectName("paramsTitle")
        status_title.setFixedHeight(25)

        # Status details
        status_grid = QGridLayout()
        status_grid.setSpacing(10)
        status_grid.setContentsMargins(0, 0, 0, 0)

        cam_model_label = QLabel("相机型号:")
        cam_model_label.setObjectName("paramLabel")
        self.model_value_label = QLabel("未连接")
        self.model_value_label.setObjectName("paramValue")
        self.model_value_label.setMinimumWidth(120)

        cam_status_label = QLabel("连接状态:")
        cam_status_label.setObjectName("paramLabel")
        self.status_value_label = QLabel("未连接")
        self.status_value_label.setObjectName("paramValue")
        self.status_value_label.setMinimumWidth(80)

        cam_temp_label = QLabel("温度:")
        cam_temp_label.setObjectName("paramLabel")
        self.temp_value_label = QLabel("--")
        self.temp_value_label.setObjectName("paramValue")
        self.temp_value_label.setMinimumWidth(60)

        cam_fps_label = QLabel("实际帧率:")
        cam_fps_label.setObjectName("paramLabel")
        self.fps_value_label = QLabel("0 FPS")
        self.fps_value_label.setObjectName("paramValue")
        self.fps_value_label.setMinimumWidth(60)

        status_grid.addWidget(cam_model_label, 0, 0)
        status_grid.addWidget(self.model_value_label, 0, 1)
        status_grid.addWidget(cam_status_label, 0, 2)
        status_grid.addWidget(self.status_value_label, 0, 3)
        status_grid.addWidget(cam_temp_label, 1, 0)
        status_grid.addWidget(self.temp_value_label, 1, 1)
        status_grid.addWidget(cam_fps_label, 1, 2)
        status_grid.addWidget(self.fps_value_label, 1, 3)

        status_layout.addWidget(status_title)
        status_layout.addLayout(status_grid)
        status_layout.addStretch()

        return status_frame

    def rebuild_parameter_controls(self):
        """Rebuild parameter controls based on connected camera."""
        if not self.param_controls_layout:
            if not self.param_controls_holder:
                return
            self.param_controls_layout = QVBoxLayout(self.param_controls_holder)
            self.param_controls_layout.setContentsMargins(0, 0, 0, 0)
            self.param_controls_layout.setSpacing(15)

        controls_layout = self.param_controls_layout
        if not controls_layout:
            return

        # Clear existing widgets
        self._clear_layout(controls_layout)

        self.parameter_sliders.clear()

        if not self.camera_service:
            label = QLabel("相机服务未初始化，参数设置不可用")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setObjectName("paramLabel")
            controls_layout.addWidget(label)
            controls_layout.addStretch()
            return

        # Get parameters from camera
        parameters = self.camera_service.list_parameters()
        if not parameters:
            label = QLabel("无可用参数")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setObjectName("paramLabel")
            controls_layout.addWidget(label)
            controls_layout.addStretch()
            return

        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(0, 0, 0, 0)

        for param in parameters:
            if param.read_only:
                continue

            label = QLabel(param.display_name + ":")
            label.setObjectName("paramLabel")

            # Create slider for this parameter
            min_val = param.min_value if param.min_value is not None else 0.0
            max_val = param.max_value if param.max_value is not None else 100.0
            step = param.step if param.step is not None else 1.0
            decimals = 2 if param.value_type == float else 0

            if param.unit and "s" in param.unit.lower():
                decimals = 0

            slider = SliderField(min_val, max_val, step, decimals)

            # Get current value
            current_value = self.camera_service.get_parameter(param.key)
            if current_value is not None:
                slider.set_value(float(current_value))

            # Connect to parameter change handler
            slider.value_changed.connect(
                lambda val, key=param.key: self.on_parameter_changed(key, val)
            )

            self.parameter_sliders[param.key] = slider

            # Add to form
            form_layout.addRow(label, slider)

        # Add form layout to container
        controls_layout.addLayout(form_layout)
        controls_layout.addStretch()

    @Slot()
    def on_connect_camera(self):
        """Handle camera connection."""
        if not self._require_service("连接相机"):
            return
        try:
            # Discover cameras
            cameras = self.camera_service.discover_cameras()

            if not cameras:
                QMessageBox.warning(self, "错误", "未发现相机\n请检查相机连接和SDK安装")
                return

            # For now, connect to first camera
            # TODO: Show selection dialog if multiple cameras
            camera_info = cameras[0]

            if self.camera_service.connect_camera(camera_info):
                logger.info("Connected to camera: %s", camera_info.name)
                self.update_connection_state()
                self.rebuild_parameter_controls()
                self.refresh_presets()
                QMessageBox.information(self, "成功", f"已连接到相机: {camera_info.name}")
            else:
                QMessageBox.warning(self, "错误", "连接相机失败")
        except Exception as exc:
            logger.error("Camera connection error: %s", exc, exc_info=True)
            QMessageBox.critical(self, "错误", f"连接相机时发生错误:\n{exc}")

    @Slot()
    def on_disconnect_camera(self):
        """Handle camera disconnection."""
        if not self._require_service("断开相机"):
            self.on_stop_preview()
            return
        try:
            self.on_stop_preview()
            self.camera_service.disconnect_camera()
            self.update_connection_state()
            self.rebuild_parameter_controls()
            self.preview_label.setText("相机预览区域\n请先连接相机")
            logger.info("Camera disconnected")
        except Exception as exc:
            logger.error("Camera disconnection error: %s", exc, exc_info=True)

    @Slot()
    def on_start_preview(self):
        """Start camera preview."""
        if self.preview_worker is not None:
            return  # Already running

        if not self._require_service("开启预览"):
            return

        camera = self.camera_service.get_connected_camera()
        if not camera:
            QMessageBox.warning(self, "错误", "请先连接相机")
            return

        try:
            # Start camera stream
            if not self.camera_service.start_preview():
                QMessageBox.warning(self, "错误", "启动预览失败")
                return

            # Create and start preview worker
            self.preview_worker = PreviewWorker(camera)
            self.preview_worker.frame_ready.connect(self.on_frame_ready)
            self.preview_worker.stats_updated.connect(self.on_stats_updated)
            self.preview_worker.error_occurred.connect(self.on_preview_error)
            self.preview_worker.start()

            # Apply live detection configuration to worker
            self._apply_detection_config()

            self.update_connection_state()
            logger.info("Preview started")
        except Exception as exc:
            logger.error("Preview start error: %s", exc, exc_info=True)
            QMessageBox.critical(self, "错误", f"启动预览失败:\n{exc}")

    @Slot()
    def on_stop_preview(self):
        """Stop camera preview."""
        if self.preview_worker is None:
            return

        try:
            self.preview_worker.stop()
            self.preview_worker = None
            if self.camera_service:
                self.camera_service.stop_preview()
            self.update_connection_state()
            self.fps_value_label.setText("0 FPS")
            logger.info("Preview stopped")
        except Exception as exc:
            logger.error("Preview stop error: %s", exc, exc_info=True)

    @Slot()
    def on_screenshot(self):
        """Take a screenshot."""
        if not self.camera_service or not self.camera_service.is_streaming():
            QMessageBox.information(self, "提示", "截图仅在预览进行时可用，请先开始预览。")
            return
        # TODO: Implement screenshot functionality
        QMessageBox.information(self, "提示", "截图功能开发中")

    @Slot()
    def on_calibrate_camera(self):
        """Toggle inline camera calibration panel."""
        toggle_on = True
        if self.calibrate_btn and self.calibrate_btn.isCheckable():
            toggle_on = self.calibrate_btn.isChecked()

        if not toggle_on:
            self._hide_calibration_panel()
            return

        if not self._require_service("打开标定面板"):
            self._set_calibrate_button_checked(False)
            return

        try:
            camera = self.camera_service.get_connected_camera()
            if not camera:
                QMessageBox.warning(self, "错误", "请先连接相机")
                self._set_calibrate_button_checked(False)
                return

            if not self.camera_service.is_streaming():
                self.on_start_preview()

            panel = self._ensure_calibration_panel()
            if not panel:
                QMessageBox.warning(self, "错误", "初始化标定面板失败")
                self._set_calibrate_button_checked(False)
                return

            if panel.activate():
                self.calibration_panel_visible = True
                if self.calibration_panel_container:
                    self.calibration_panel_container.setVisible(True)
                self._apply_detection_config()
            else:
                QMessageBox.warning(self, "错误", "标定面板不可用")
                self._set_calibrate_button_checked(False)

        except Exception as exc:
            logger.error("Calibration dialog error: %s", exc, exc_info=True)
            self._set_calibrate_button_checked(False)
            QMessageBox.critical(self, "错误", f"无法打开标定面板:\n{exc}")

    @Slot(object)
    def on_frame_ready(self, image):
        """Handle new frame from preview worker."""
        if not self.preview_label:
            return

        scaled_pixmap = QPixmap.fromImage(image).scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled_pixmap)

    @Slot(dict)
    def on_stats_updated(self, stats):
        """Handle statistics update from preview worker."""
        # Update FPS if available
        if "frame_count" in stats:
            # Simple FPS calculation (just for display)
            # For accurate FPS, need timestamp tracking
            self.fps_value_label.setText(f"{stats.get('frame_count', 0) % 60} FPS")

    @Slot(str)
    def on_preview_error(self, error_msg):
        """Handle preview error."""
        logger.error("Preview error: %s", error_msg)
        self.on_stop_preview()
        QMessageBox.critical(self, "预览错误", error_msg)

    def _on_live_detect_state_changed(self, enabled: bool):
        self.calibration_live_detect_enabled = enabled
        self._apply_detection_config()

    def _apply_detection_config(self):
        try:
            if not self.preview_worker:
                return
            board_size = (9, 6)
            if self.calibration_panel:
                board_size = self.calibration_panel.board_config.board_size
            self.preview_worker.configure_detection(self.calibration_live_detect_enabled, board_size)
            self.preview_worker.set_detection_rate(interval_ms=300, downscale_height=480)
        except Exception as exc:
            logger.error("Failed to apply detection config: %s", exc, exc_info=True)

    def on_parameter_changed(self, key: str, value: float):
        """Handle parameter value change."""
        if not self._require_service("调整参数"):
            return
        try:
            if self.camera_service.set_parameter(key, value):
                logger.debug("Parameter %s set to %s", key, value)
            else:
                logger.warning("Failed to set parameter %s", key)
                # Revert slider to current value
                current_value = self.camera_service.get_parameter(key)
                if current_value is not None and key in self.parameter_sliders:
                    self.parameter_sliders[key].set_value(float(current_value))
        except Exception as exc:
            logger.error("Parameter change error: %s", exc, exc_info=True)

    @Slot()
    def on_save_preset(self):
        """Save current parameters as preset."""
        if not self._require_service("保存预设"):
            return
        if not self.camera_service.get_connected_camera():
            QMessageBox.warning(self, "错误", "请先连接相机")
            return

        preset_name, ok = QInputDialog.getText(
            self, "保存预设", "请输入预设名称:"
        )

        if ok and preset_name:
            if self.camera_service.save_preset(preset_name, self.current_username):
                self.refresh_presets()
                QMessageBox.information(self, "成功", f"预设 '{preset_name}' 已保存")
            else:
                QMessageBox.warning(self, "错误", "保存预设失败")

    @Slot()
    def on_load_preset(self):
        """Load selected preset."""
        if not self._require_service("加载预设"):
            return
        if not self.camera_service.get_connected_camera():
            QMessageBox.warning(self, "错误", "请先连接相机")
            return

        preset_name = self.preset_combo.currentText()
        if not preset_name:
            return

        if self.camera_service.apply_preset(preset_name, self.current_username):
            # Update all sliders with new values
            for key, slider in self.parameter_sliders.items():
                value = self.camera_service.get_parameter(key)
                if value is not None:
                    slider.set_value(float(value))
            QMessageBox.information(self, "成功", f"预设 '{preset_name}' 已加载")
        else:
            QMessageBox.warning(self, "错误", "加载预设失败")

    @Slot()
    def on_delete_preset(self):
        """Delete selected preset."""
        if not self._require_service("删除预设"):
            return
        preset_name = self.preset_combo.currentText()
        if not preset_name:
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除预设 '{preset_name}' 吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.camera_service.delete_preset(preset_name, self.current_username):
                self.refresh_presets()
                QMessageBox.information(self, "成功", f"预设 '{preset_name}' 已删除")
            else:
                QMessageBox.warning(self, "错误", "删除预设失败")

    def refresh_presets(self):
        """Refresh preset list."""
        if not self.preset_combo or not self.camera_service:
            return

        self.preset_combo.clear()
        presets = self.camera_service.list_presets(self.current_username)
        self.preset_combo.addItems(presets)

    def update_connection_state(self):
        """Update UI based on connection state."""
        if not self.camera_service:
            self._apply_service_unavailable_state()
            return

        camera = self.camera_service.get_connected_camera()
        is_connected = camera is not None
        is_streaming = self.camera_service.is_streaming()

        # Update buttons
        if self.connect_btn:
            self.connect_btn.setEnabled(not is_connected)
        if self.disconnect_btn:
            self.disconnect_btn.setEnabled(is_connected)
        if self.start_preview_btn:
            self.start_preview_btn.setEnabled(is_connected and not is_streaming)
        if self.stop_preview_btn:
            self.stop_preview_btn.setEnabled(is_streaming)
        if self.screenshot_btn:
            self.screenshot_btn.setEnabled(is_streaming)
        if self.calibrate_btn:
            self.calibrate_btn.setEnabled(is_connected)

        # Update status labels
        if is_connected:
            self.model_value_label.setText(camera.info.model_name or "未知")
            self.status_value_label.setText("已连接")
            self.status_value_label.setStyleSheet("color: #3CC37A;")
            self._set_params_panel_visible(True)
        else:
            self.model_value_label.setText("未连接")
            self.status_value_label.setText("未连接")
            self.status_value_label.setStyleSheet("color: #8C92A0;")
            self._set_params_panel_visible(False)

    def cleanup(self):
        """Cleanup resources."""
        self.on_stop_preview()
        if self.calibration_panel:
            self.calibration_panel.deactivate()
