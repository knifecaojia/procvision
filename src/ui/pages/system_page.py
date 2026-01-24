"""
System settings page for the industrial vision system.
"""

import logging
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpacerItem, QSizePolicy,
    QFileDialog, QCheckBox, QComboBox, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, QTimer, Signal

from ..styles import refresh_widget_styles, save_user_theme_preference

logger = logging.getLogger(__name__)


class SystemPage(QFrame):
    """System settings page implementation."""

    themeChanged = Signal(str)
    
    def __init__(self, parent=None, initial_theme: str = "dark"):
        super().__init__(parent)
        self.setObjectName("systemPage")
        self.current_theme = initial_theme if initial_theme in {"dark", "light"} else "dark"
        self._loading_settings = False
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Initialize the system page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("systemScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.viewport().setObjectName("systemScrollViewport")

        scroll_content = QWidget()
        scroll_content.setObjectName("systemScrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(20)
        
        # Header section
        header_frame = QFrame()
        header_frame.setObjectName("systemHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("系统设置")
        title_label.setObjectName("systemTitle")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        scroll_layout.addWidget(header_frame)

        general_frame = QFrame()
        general_frame.setObjectName("generalFrame")
        general_layout = QVBoxLayout(general_frame)
        general_layout.setContentsMargins(20, 20, 20, 20)
        general_layout.setSpacing(15)

        general_title = QLabel("基本配置")
        general_title.setObjectName("sectionTitle")

        auto_layout = QHBoxLayout()
        auto_label = QLabel("完成后自动开始下一产品检测:")
        auto_label.setObjectName("paramLabel")
        self.auto_start_next_checkbox = QCheckBox()
        self.auto_start_next_checkbox.setObjectName("paramCheckBox")
        auto_layout.addWidget(auto_label)
        auto_layout.addWidget(self.auto_start_next_checkbox)

        theme_layout = QHBoxLayout()
        theme_layout.setSpacing(10)
        theme_label = QLabel("主题模式（Light）:")
        theme_label.setObjectName("paramLabel")
        self.theme_label = theme_label
        self.theme_switch = QCheckBox()
        self.theme_switch.setObjectName("themeSwitch")
        self.theme_switch.setToolTip("切换浅色或深色主题")
        self.theme_switch.toggled.connect(self.on_theme_switch)
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_switch)
        theme_layout.addStretch()

        general_layout.addWidget(general_title)
        general_layout.addLayout(auto_layout)
        general_layout.addLayout(theme_layout)

        pos_layout = QHBoxLayout()
        pos_label = QLabel("检测结果提示位置:")
        pos_label.setObjectName("paramLabel")
        self.result_position_combo = QComboBox()
        self.result_position_combo.setObjectName("paramInput")
        self.result_position_combo.addItem("左上", "top_left")
        self.result_position_combo.addItem("正上", "top_center")
        self.result_position_combo.addItem("右上", "top_right")
        self.result_position_combo.addItem("左中", "center_left")
        self.result_position_combo.addItem("正中", "center")
        self.result_position_combo.addItem("右中", "center_right")
        self.result_position_combo.addItem("左下", "bottom_left")
        self.result_position_combo.addItem("正下", "bottom_center")
        self.result_position_combo.addItem("右下", "bottom_right")
        pos_layout.addWidget(pos_label)
        pos_layout.addWidget(self.result_position_combo)

        boxopt_layout = QHBoxLayout()
        ok_box_label = QLabel("OK绘制框线:")
        ok_box_label.setObjectName("paramLabel")
        self.draw_ok_checkbox = QCheckBox()
        self.draw_ok_checkbox.setObjectName("paramCheckBox")
        ng_box_label = QLabel("NG绘制框线:")
        ng_box_label.setObjectName("paramLabel")
        self.draw_ng_checkbox = QCheckBox()
        self.draw_ng_checkbox.setObjectName("paramCheckBox")
        boxopt_layout.addWidget(ok_box_label)
        boxopt_layout.addWidget(self.draw_ok_checkbox)
        boxopt_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum))
        boxopt_layout.addWidget(ng_box_label)
        boxopt_layout.addWidget(self.draw_ng_checkbox)

        general_layout.addLayout(pos_layout)
        general_layout.addLayout(boxopt_layout)

        scroll_layout.addWidget(general_frame)
        
        # Server configuration
        server_frame = QFrame()
        server_frame.setObjectName("serverFrame")
        
        server_layout = QVBoxLayout(server_frame)
        server_layout.setContentsMargins(20, 20, 20, 20)
        server_layout.setSpacing(15)
        
        server_title = QLabel("中心服务器配置")
        server_title.setObjectName("sectionTitle")
        
        # Server address
        addr_layout = QHBoxLayout()
        addr_label = QLabel("服务器地址:")
        addr_label.setObjectName("paramLabel")
        self.addr_input = QLineEdit("192.168.1.100")
        self.addr_input.setObjectName("paramInput")
        addr_layout.addWidget(addr_label)
        addr_layout.addWidget(self.addr_input)
        
        # Server port
        port_layout = QHBoxLayout()
        port_label = QLabel("服务器端口:")
        port_label.setObjectName("paramLabel")
        self.port_input = QLineEdit("8080")
        self.port_input.setObjectName("paramInput")
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        
        server_layout.addWidget(server_title)
        server_layout.addLayout(addr_layout)
        server_layout.addLayout(port_layout)
        
        scroll_layout.addWidget(server_frame)
        
        # Image storage configuration
        image_frame = QFrame()
        image_frame.setObjectName("imageFrame")
        
        image_layout = QVBoxLayout(image_frame)
        image_layout.setContentsMargins(20, 20, 20, 20)
        image_layout.setSpacing(15)
        
        image_title = QLabel("图像存储配置")
        image_title.setObjectName("sectionTitle")
        
        # Image save path
        img_path_layout = QHBoxLayout()
        img_path_label = QLabel("图像保存位置:")
        img_path_label.setObjectName("paramLabel")
        self.img_path_input = QLineEdit("C:\\VisionData\\Images")
        self.img_path_input.setObjectName("paramInput")
        # Removed fixed width to allow adaptive width
        self.img_browse_btn = QPushButton("浏览")
        self.img_browse_btn.setObjectName("browseButton")
        self.img_browse_btn.setFixedWidth(80)
        self.img_browse_btn.setFixedHeight(32)
        img_path_layout.addWidget(img_path_label)
        img_path_layout.addWidget(self.img_path_input)
        img_path_layout.addWidget(self.img_browse_btn)
        
        # Image retention days
        img_retention_layout = QHBoxLayout()
        img_retention_label = QLabel("图像保留时间（天）:")
        img_retention_label.setObjectName("paramLabel")
        self.img_retention_input = QLineEdit("30")
        self.img_retention_input.setObjectName("paramInput")
        img_retention_layout.addWidget(img_retention_label)
        img_retention_layout.addWidget(self.img_retention_input)
        
        image_layout.addWidget(image_title)
        image_layout.addLayout(img_path_layout)
        image_layout.addLayout(img_retention_layout)
        
        scroll_layout.addWidget(image_frame)
        
        # Log storage configuration
        log_frame = QFrame()
        log_frame.setObjectName("logFrame")
        
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(20, 20, 20, 20)
        log_layout.setSpacing(15)
        
        log_title = QLabel("日志存储配置")
        log_title.setObjectName("sectionTitle")
        
        # Log save path
        log_path_layout = QHBoxLayout()
        log_path_label = QLabel("日志保存位置:")
        log_path_label.setObjectName("paramLabel")
        self.log_path_input = QLineEdit("C:\\VisionData\\Logs")
        self.log_path_input.setObjectName("paramInput")
        # Removed fixed width to allow adaptive width
        self.log_browse_btn = QPushButton("浏览")
        self.log_browse_btn.setObjectName("browseButton")
        self.log_browse_btn.setFixedWidth(80)
        self.log_browse_btn.setFixedHeight(32)
        log_path_layout.addWidget(log_path_label)
        log_path_layout.addWidget(self.log_path_input)
        log_path_layout.addWidget(self.log_browse_btn)
        
        # Log retention days
        log_retention_layout = QHBoxLayout()
        log_retention_label = QLabel("日志保留时间（天）:")
        log_retention_label.setObjectName("paramLabel")
        self.log_retention_input = QLineEdit("90")
        self.log_retention_input.setObjectName("paramInput")
        log_retention_layout.addWidget(log_retention_label)
        log_retention_layout.addWidget(self.log_retention_input)
        
        log_layout.addWidget(log_title)
        log_layout.addLayout(log_path_layout)
        log_layout.addLayout(log_retention_layout)
        
        scroll_layout.addWidget(log_frame)
        
        # Save button - moved to bottom and adjusted width
        save_btn_layout = QHBoxLayout()
        save_btn_layout.addStretch()
        self.save_btn = QPushButton("保存配置")
        self.save_btn.setObjectName("saveButton")
        self.save_btn.setFixedHeight(40)
        self.save_btn.setFixedWidth(120)
        save_btn_layout.addWidget(self.save_btn)
        save_btn_layout.addStretch()
        
        scroll_layout.addLayout(save_btn_layout)
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)

        self.toast_container = QFrame()
        self.toast_container.setObjectName("toastContainer")
        toast_layout = QHBoxLayout(self.toast_container)
        toast_layout.setContentsMargins(0, 0, 0, 0)
        toast_layout.addStretch()
        self.toast_label = QLabel()
        self.toast_label.setObjectName("toastLabel")
        self.toast_label.setVisible(False)
        self.toast_label.setProperty("toastState", "success")
        toast_layout.addWidget(self.toast_label)
        toast_layout.addStretch()
        self.toast_container.setVisible(False)
        layout.addWidget(self.toast_container)

        self.img_browse_btn.clicked.connect(self.on_img_browse)
        self.log_browse_btn.clicked.connect(self.on_log_browse)
        self.save_btn.clicked.connect(self.save_settings)

    def on_img_browse(self):
        initial = self.img_path_input.text() or str(Path.cwd())
        path = QFileDialog.getExistingDirectory(self, "选择图像保存位置", initial)
        if path:
            self.img_path_input.setText(self.normalize_path_for_os(path))

    def on_log_browse(self):
        initial = self.log_path_input.text() or str(Path.cwd())
        path = QFileDialog.getExistingDirectory(self, "选择日志保存位置", initial)
        if path:
            self.log_path_input.setText(self.normalize_path_for_os(path))

    def config_path(self) -> Path:
        return Path.cwd() / "config.json"

    def load_settings(self):
        self._loading_settings = True
        try:
            p = self.config_path()
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                server = data.get("server", {})
                storage = data.get("storage", {})
                image = storage.get("image", {})
                log = storage.get("log", {})
                general = data.get("general", {})
                if "address" in server:
                    self.addr_input.setText(str(server.get("address", "")))
                if "port" in server:
                    self.port_input.setText(str(server.get("port", "")))
                if "path" in image:
                    self.img_path_input.setText(self.normalize_path_for_os(str(image.get("path", ""))))
                if "retention_days" in image:
                    self.img_retention_input.setText(str(image.get("retention_days", "")))
                if "path" in log:
                    self.log_path_input.setText(self.normalize_path_for_os(str(log.get("path", ""))))
                if "retention_days" in log:
                    self.log_retention_input.setText(str(log.get("retention_days", "")))
                self.auto_start_next_checkbox.setChecked(bool(general.get("auto_start_next", False)))
                rp = str(general.get("result_prompt_position", "center"))
                idx = 0
                for i in range(self.result_position_combo.count()):
                    if self.result_position_combo.itemData(i) == rp:
                        idx = i
                        break
                self.result_position_combo.setCurrentIndex(idx)
                self.draw_ok_checkbox.setChecked(bool(general.get("draw_boxes_ok", True)))
                self.draw_ng_checkbox.setChecked(bool(general.get("draw_boxes_ng", True)))
                theme_value = str(general.get("theme", self.current_theme)).lower()
                if theme_value not in {"dark", "light"}:
                    theme_value = self.current_theme
                self.current_theme = theme_value
                self.theme_switch.blockSignals(True)
                self.theme_switch.setChecked(self.current_theme == "light")
                self.theme_switch.blockSignals(False)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
        finally:
            self._loading_settings = False
            self.theme_switch.blockSignals(True)
            self.theme_switch.setChecked(self.current_theme == "light")
            self.theme_switch.blockSignals(False)
            self._update_theme_label()

    def save_settings(self):
        try:
            p = self.config_path()
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
            data.setdefault("server", {})
            data["server"]["address"] = self.addr_input.text().strip()
            try:
                data["server"]["port"] = int(self.port_input.text().strip())
            except ValueError:
                data["server"]["port"] = self.port_input.text().strip()
            data.setdefault("storage", {})
            data["storage"].setdefault("image", {})
            data["storage"]["image"]["path"] = self.normalize_path_for_os(self.img_path_input.text().strip())
            try:
                data["storage"]["image"]["retention_days"] = int(self.img_retention_input.text().strip())
            except ValueError:
                data["storage"]["image"]["retention_days"] = self.img_retention_input.text().strip()
            data["storage"].setdefault("log", {})
            data["storage"]["log"]["path"] = self.normalize_path_for_os(self.log_path_input.text().strip())
            try:
                data["storage"]["log"]["retention_days"] = int(self.log_retention_input.text().strip())
            except ValueError:
                data["storage"]["log"]["retention_days"] = self.log_retention_input.text().strip()
            data.setdefault("general", {})
            data["general"]["auto_start_next"] = bool(self.auto_start_next_checkbox.isChecked())
            try:
                sel_idx = self.result_position_combo.currentIndex()
                data["general"]["result_prompt_position"] = str(self.result_position_combo.itemData(sel_idx))
            except Exception:
                data["general"]["result_prompt_position"] = "center"
            data["general"]["draw_boxes_ok"] = bool(self.draw_ok_checkbox.isChecked())
            data["general"]["draw_boxes_ng"] = bool(self.draw_ng_checkbox.isChecked())
            data["general"]["theme"] = "light" if self.theme_switch.isChecked() else "dark"
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved: {p}")
            self.show_toast("保存成功", True)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            self.show_toast("保存失败", False)

    def normalize_path_for_os(self, path_str: str) -> str:
        if not path_str:
            return path_str
        import os as _os
        return _os.path.normpath(path_str)

    def show_toast(self, text: str, success: bool):
        if not hasattr(self, "toast_label"):
            return
        self.toast_label.setText(text)
        state = "success" if success else "error"
        self.toast_label.setProperty("toastState", state)
        refresh_widget_styles(self.toast_label)
        self.toast_label.setVisible(True)
        self.toast_container.setVisible(True)
        QTimer.singleShot(2000, self.hide_toast)

    def hide_toast(self):
        if hasattr(self, "toast_label"):
            self.toast_label.setVisible(False)
            self.toast_container.setVisible(False)

    def on_theme_switch(self, checked: bool):
        if self._loading_settings:
            return
        theme = "light" if checked else "dark"
        if theme == self.current_theme:
            return
        self.current_theme = theme
        try:
            save_user_theme_preference(theme, self.config_path())
        except Exception:
            logger.exception("Failed to persist theme preference")
        self.show_toast(f"主题已切换为 {'浅色' if theme == 'light' else '深色'}", True)
        self._update_theme_label()
        self.themeChanged.emit(theme)

    def _update_theme_label(self) -> None:
        if hasattr(self, "theme_label"):
            mode = "Light" if self.theme_switch.isChecked() else "Dark"
            self.theme_label.setText(f"主题模式（{mode}）:")
