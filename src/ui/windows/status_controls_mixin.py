from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QPainter
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QWidget

from ..styles import refresh_widget_styles


class StatusIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusIndicator")
        self.setFixedSize(20, 20)
        self._state = "idle"
        self._colors = {
            "idle": "#6b7280",
            "detecting": "#f59e0b",
            "ok": "#22c55e",
            "ng": "#ef4444",
            "error": "#ef4444",
        }

    def set_state(self, state: str):
        self._state = state
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color_hex = self._colors.get(self._state, "#6b7280")
        painter.setBrush(QBrush(QColor(color_hex)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 16, 16)
        painter.end()


class StatusControlsMixin:
    def _create_status_section(self) -> QWidget:
        section = QWidget()
        section.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        section.setFixedHeight(120)

        auto_active = getattr(self, "auto_detect_active", False)
        detecting = self.detection_status == "detecting"
        allowed = bool(getattr(self, "_has_detection_source", lambda: False)()) and not detecting
        btn_text = "检测中" if detecting else "开始检测"
        self.start_detection_btn = QPushButton(btn_text)
        self.start_detection_btn.setObjectName("startDetectionButton")
        self.start_detection_btn.setFixedSize(200, 120)
        try:
            self.start_detection_btn.setFont(self.custom_font)
        except Exception:
            pass
        self.start_detection_btn.setEnabled(allowed)
        self.start_detection_btn.setVisible(not auto_active)
        if allowed:
            try:
                self.start_detection_btn.clicked.connect(self.on_start_detection)
            except Exception:
                pass
        else:
            self._set_detection_button_tooltip(self.start_detection_btn)
        layout.addWidget(self.start_detection_btn)

        if bool(getattr(self, "has_final_check", lambda: False)()):
            self.final_check_btn = QPushButton("终检")
            self.final_check_btn.setObjectName("finalCheckButton")
            self.final_check_btn.setFixedSize(200, 120)
            try:
                self.final_check_btn.setFont(self.custom_font)
            except Exception:
                pass
            final_allowed = bool(getattr(self, "can_run_final_check", lambda: False)())
            self.final_check_btn.setEnabled(final_allowed)
            if final_allowed:
                try:
                    self.final_check_btn.clicked.connect(self.on_final_check_detection)
                except Exception:
                    pass
            else:
                self._set_detection_button_tooltip(self.final_check_btn)
            layout.addWidget(self.final_check_btn)

        auto_text = "停止自动" if auto_active else "自动检测"
        self.auto_detect_btn = QPushButton(auto_text)
        self.auto_detect_btn.setObjectName("autoDetectButton")
        self.auto_detect_btn.setCheckable(True)
        self.auto_detect_btn.setChecked(auto_active)
        self.auto_detect_btn.setFixedSize(200, 120)
        try:
            self.auto_detect_btn.setFont(self.custom_font)
        except Exception:
            pass
        auto_allowed = auto_active or allowed
        self.auto_detect_btn.setEnabled(auto_allowed)
        try:
            self.auto_detect_btn.clicked.connect(self.toggle_auto_detect)
        except Exception:
            pass
        layout.addWidget(self.auto_detect_btn)

        self.status_indicator = StatusIndicator(section)
        self.status_indicator.setVisible(auto_active)
        layout.addWidget(self.status_indicator)

        return section

    def _set_detection_button_tooltip(self, button: QPushButton) -> None:
        try:
            tooltip = "请先开启相机"
            if bool(getattr(self, "auto_detect_active", False)):
                tooltip = "自动检测中不可手工终检"
            elif bool(getattr(self, "_allows_mock_camera_bypass", lambda: False)()):
                tooltip = "MOCK CAM 已启用"
            button.setToolTip(tooltip)
        except Exception:
            pass

    def rebuild_status_section(self):
        old_section = self.status_section
        footer_layout = old_section.parent().layout()
        new_section = self._create_status_section()
        self.status_section = new_section
        footer_layout.replaceWidget(old_section, new_section)
        old_section.deleteLater()
        try:
            refresh_widget_styles(new_section)
        except Exception:
            pass
