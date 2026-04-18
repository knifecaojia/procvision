"""
Camera settings page for the industrial vision system with Hikvision camera integration.
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

 
from PySide6.QtCore import Qt, QSize, Slot, QTimer
from PySide6.QtGui import QIcon, QPixmap, QImage, QPainter
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QGridLayout, QSizePolicy,
    QToolButton, QMessageBox, QInputDialog, QScrollArea, QFormLayout,
    QListWidget, QListWidgetItem, QSpinBox, QDoubleSpinBox,
    QGroupBox, QProgressBar, QLayout
)

from PySide6.QtSvg import QSvgRenderer

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
from ..styles import refresh_widget_styles

logger = logging.getLogger("camera.ui")


class CameraPage(QFrame):
    """Camera settings page with live preview and parameter controls."""

    def __init__(self, camera_service: Optional[CameraService], parent=None, initial_theme: str = "dark"):
        super().__init__(parent)
        self.setObjectName("cameraPage")
        self.camera_service = camera_service
        self._service_warning_shown = False
        self.preview_worker: Optional[PreviewWorker] = None
        self.parameter_sliders = {}
        self.current_username = "admin"  # TODO: Get from session
        self.params_frame: Optional[QFrame] = None
        self.assets_dir = Path(__file__).resolve().parents[2] / "assets"
        self._latest_preview_frame: Optional[QImage] = None

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

        self.current_theme = initial_theme if initial_theme in {"dark", "light"} else "dark"
        self._control_buttons: list[tuple[QToolButton, str]] = []
        self._icon_cache: dict[tuple[str, str], QIcon] = {}

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
            self._update_status_label_state("unavailable")

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

    def _update_status_label_state(self, state: str) -> None:
        if self.status_value_label:
            self.status_value_label.setProperty("connectionState", state)
            refresh_widget_styles(self.status_value_label)

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

    def apply_theme(self, theme: str) -> None:
        if theme not in {"dark", "light"}:
            return
        if theme == self.current_theme:
            return
        self.current_theme = theme
        self._icon_cache.clear()
        self._refresh_control_icons()

    def _refresh_control_icons(self) -> None:
        for button, icon_name in self._control_buttons:
            self._set_button_icon(button, icon_name, force=True)

    def _set_button_icon(self, button: QToolButton, icon_name: str, force: bool = False) -> bool:
        if force:
            self._icon_cache.pop((icon_name, self.current_theme), None)
        icon = self._get_svg_icon(icon_name)
        if not icon:
            return False
        button.setIcon(icon)
        button.setIconSize(QSize(20, 20))
        button.setProperty("iconFallback", False)
        refresh_widget_styles(button)
        return True

    def _get_svg_icon(self, icon_name: str) -> Optional[QIcon]:
        key = (icon_name, self.current_theme)
        if key in self._icon_cache:
            return self._icon_cache[key]
        icon_path = self.assets_dir / icon_name
        if not icon_path.exists():
            return None
        try:
            svg_data = icon_path.read_text(encoding="utf-8")
        except OSError:
            return None
        color = self._icon_color_for_theme()
        svg_colored = svg_data.replace("currentColor", color)
        renderer = QSvgRenderer(bytearray(svg_colored, "utf-8"))
        if not renderer.isValid():
            return None
        size = QSize(20, 20)
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon = QIcon(pixmap)
        self._icon_cache[key] = icon
        return icon

    def _icon_color_for_theme(self) -> str:
        return "#F7F9FC" if self.current_theme == "dark" else "#1F2933"

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
            if icon_path.exists() and self._set_button_icon(button, icon_name):
                self._control_buttons.append((button, icon_name))
            else:
                button.setText(fallback_symbol)
                button.setProperty("iconFallback", "true")
                refresh_widget_styles(button)

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

        # Configuration management panel
        config_panel = self._create_config_management_panel()
        params_layout.addWidget(config_panel)

        # Scrollable parameters container
        scroll_area = QScrollArea()
        scroll_area.setObjectName("paramsScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.viewport().setObjectName("paramsScrollViewport")
        scroll_area.viewport().setAutoFillBackground(False)

        self.params_container = QFrame()
        self.params_container.setObjectName("paramsContainer")
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

    def _create_config_management_panel(self) -> QFrame:
        config_panel = QFrame()
        config_panel.setObjectName("configManagementPanel")
        config_layout = QVBoxLayout(config_panel)
        config_layout.setContentsMargins(5, 5, 5, 5)
        config_layout.setSpacing(8)

        config_title = QLabel("参数配置管理")
        config_title.setObjectName("sectionTitle")
        config_layout.addWidget(config_title)

        combo_row = QHBoxLayout()
        combo_row.setSpacing(8)

        combo_label = QLabel("选择配置:")
        combo_label.setObjectName("paramLabel")
        combo_row.addWidget(combo_label)

        self.config_combo = QComboBox()
        self.config_combo.setObjectName("configCombo")
        self.config_combo.setMinimumWidth(200)
        self.config_combo.currentTextChanged.connect(self._on_config_selected)
        combo_row.addWidget(self.config_combo)

        combo_row.addStretch()
        config_layout.addLayout(combo_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        load_btn = QPushButton("加载")
        load_btn.setToolTip("加载选中的配置到相机")
        load_btn.clicked.connect(self._on_load_selected_config)
        btn_row.addWidget(load_btn)

        save_btn = QPushButton("保存")
        save_btn.setToolTip("保存当前相机参数")
        save_btn.clicked.connect(self._on_save_config)
        btn_row.addWidget(save_btn)

        delete_btn = QPushButton("删除")
        delete_btn.setToolTip("删除选中的配置")
        delete_btn.clicked.connect(self.on_delete_preset)
        btn_row.addWidget(delete_btn)

        export_btn = QPushButton("导出")
        export_btn.setToolTip("导出选中配置为JSON")
        export_btn.clicked.connect(self.on_export_selected_preset)
        btn_row.addWidget(export_btn)

        import_btn = QPushButton("导入")
        import_btn.setToolTip("从JSON/ZIP导入配置")
        import_btn.clicked.connect(self.on_import_presets)
        btn_row.addWidget(import_btn)

        btn_row.addStretch()
        config_layout.addLayout(btn_row)

        self.refresh_config_combo()
        return config_panel

    def _on_save_config(self):
        if not self._require_service("保存配置"):
            return
        if not self.camera_service.get_connected_camera():
            QMessageBox.warning(self, "错误", "请先连接相机")
            return

        preset_name, ok = QInputDialog.getText(
            self, "保存配置", "请输入配置名称:"
        )

        if ok and preset_name:
            if self.camera_service.save_preset(preset_name, self.current_username):
                self.refresh_config_combo()
                self.refresh_presets()
                QMessageBox.information(self, "成功", f"配置 '{preset_name}' 已保存")
            else:
                QMessageBox.warning(self, "错误", "保存配置失败")

    def refresh_config_combo(self):
        if not hasattr(self, "config_combo") or not self.camera_service:
            return
        self.config_combo.clear()
        presets = self.camera_service.list_presets(self.current_username)
        self.config_combo.addItems(presets)

    def _on_config_selected(self, preset_name: str):
        pass

    def _on_load_selected_config(self):
        if not self._require_service("加载配置"):
            return
        if not self.camera_service.get_connected_camera():
            QMessageBox.warning(self, "错误", "请先连接相机")
            return

        preset_name = self.config_combo.currentText()
        if not preset_name:
            return

        success, failed_params = self.camera_service.apply_preset(preset_name, self.current_username)

        for key, slider in self.parameter_sliders.items():
            value = self.camera_service.get_parameter(key)
            if value is not None:
                slider.set_value(float(value))

        if success:
            QMessageBox.information(self, "成功", f"配置 '{preset_name}' 已加载")
        else:
            failed_str = "、".join(failed_params)
            QMessageBox.warning(
                self, "部分成功",
                f"配置 '{preset_name}' 已加载\n\n以下参数设置失败: {failed_str}\n(该相机可能不支持这些参数)"
            )

    @Slot()
    def on_export_selected_preset(self):
        if not self._require_service("导出配置"):
            return

        preset_name = self.config_combo.currentText()
        if not preset_name:
            QMessageBox.warning(self, "提示", "请先选择一个配置")
            return

        from PySide6.QtWidgets import QFileDialog
        default_path = Path.home() / "Downloads" / f"{preset_name}.json"
        export_path, _ = QFileDialog.getSaveFileName(
            self, "导出配置", str(default_path), "JSON文件 (*.json)"
        )
        if export_path:
            if self.camera_service.export_preset(preset_name, self.current_username, Path(export_path)):
                QMessageBox.information(self, "成功", f"配置已导出至:\n{export_path}")
            else:
                QMessageBox.warning(self, "错误", "导出失败")

    @Slot()
    def on_export_all_presets(self):
        if not self._require_service("导出全部配置"):
            return

        from PySide6.QtWidgets import QFileDialog
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = Path.home() / "Downloads" / f"camera_presets_{timestamp}.zip"
        export_path, _ = QFileDialog.getSaveFileName(
            self, "导出全部配置", str(default_path), "ZIP文件 (*.zip)"
        )
        if export_path:
            count = self.camera_service.export_all_presets(self.current_username, Path(export_path))
            if count > 0:
                QMessageBox.information(self, "成功", f"已导出 {count} 个配置至:\n{export_path}")
            else:
                QMessageBox.warning(self, "提示", "没有可导出的配置")

    @Slot()
    def on_import_presets(self):
        if not self._require_service("导入配置"):
            return

        from PySide6.QtWidgets import QFileDialog
        import_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置", "", "配置文件 (*.json *.zip)"
        )
        if not import_path:
            return

        import_path = Path(import_path)
        if import_path.suffix.lower() == ".zip":
            reply = QMessageBox.question(
                self, "批量导入",
                "是否覆盖同名配置?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            overwrite = reply == QMessageBox.StandardButton.Yes
            count, failed = self.camera_service.import_all_presets(
                import_path, self.current_username, overwrite
            )
            self.refresh_config_combo()
            self.refresh_presets()
            msg = f"成功导入 {count} 个配置"
            if failed:
                msg += f"\n失败: {len(failed)} 个"
            QMessageBox.information(self, "导入结果", msg)
        else:
            preset_name = self.camera_service.import_preset(import_path, self.current_username)
            if preset_name:
                self.refresh_config_combo()
                self.refresh_presets()
                QMessageBox.information(self, "成功", f"配置 '{preset_name}' 已导入")
            else:
                QMessageBox.warning(self, "错误", "导入失败")

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
        self.status_value_label.setProperty("connectionState", "disconnected")

        cam_fps_label = QLabel("实际帧率:")
        cam_fps_label.setObjectName("paramLabel")
        self.fps_value_label = QLabel("0 FPS")
        self.fps_value_label.setObjectName("paramValue")
        self.fps_value_label.setMinimumWidth(60)

        status_grid.addWidget(cam_model_label, 0, 0)
        status_grid.addWidget(self.model_value_label, 0, 1)
        status_grid.addWidget(cam_status_label, 0, 2)
        status_grid.addWidget(self.status_value_label, 0, 3)
        status_grid.addWidget(cam_fps_label, 1, 0)
        status_grid.addWidget(self.fps_value_label, 1, 1)

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
        if self._latest_preview_frame is None or self._latest_preview_frame.isNull():
            QMessageBox.information(self, "提示", "当前没有可用画面，请稍后再试。")
            return

        save_dir = self._resolve_image_save_dir()
        try:
            save_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.error("Failed to create image directory '%s': %s", save_dir, exc, exc_info=True)
            QMessageBox.warning(self, "错误", f"无法创建图像保存目录:\n{save_dir}")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        save_path = save_dir / f"{timestamp}.jpg"
        ok = self._latest_preview_frame.save(str(save_path), "JPEG", 85)
        if not ok:
            QMessageBox.warning(self, "错误", "截图保存失败")
            return

        QMessageBox.information(self, "成功", f"截图已保存:\n{save_path}")

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
        self._latest_preview_frame = image

        scaled_pixmap = QPixmap.fromImage(image).scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled_pixmap)

    def _resolve_image_save_dir(self) -> Path:
        default_dir = Path(r"C:\VisionData\Images")
        from src.core.paths import get_config_json_path
        cfg_path = get_config_json_path()
        try:
            if not cfg_path.exists():
                return default_dir
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            image_cfg = cfg.get("storage", {}).get("image", {})
            path_value = str(image_cfg.get("path") or "").strip()
            if path_value:
                return Path(path_value)
        except Exception as exc:
            logger.warning("Failed to load image storage path from %s: %s", cfg_path, exc)
        return default_dir

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
        preset_name = self.config_combo.currentText()
        if not preset_name:
            QMessageBox.warning(self, "提示", "请先选择一个配置")
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除配置 '{preset_name}' 吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.camera_service.delete_preset(preset_name, self.current_username):
                self.refresh_config_combo()
                self.refresh_presets()
                QMessageBox.information(self, "成功", f"配置 '{preset_name}' 已删除")
            else:
                QMessageBox.warning(self, "错误", "删除配置失败")

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
            self._update_status_label_state("connected")
            self._set_params_panel_visible(True)
        else:
            self.model_value_label.setText("未连接")
            self.status_value_label.setText("未连接")
            self._update_status_label_state("disconnected")
            self._set_params_panel_visible(False)

    def cleanup(self):
        """Cleanup resources."""
        self.on_stop_preview()
        if self.calibration_panel:
            self.calibration_panel.deactivate()
