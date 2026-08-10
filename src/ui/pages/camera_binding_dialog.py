"""Compact dialog for selecting a bound camera with project-aligned styling."""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.config import get_config
from src.camera.camera_service import CameraService
from src.camera.types import CameraInfo
from ..styles import load_user_theme_preference, resolve_theme_colors


class CameraBindingDialog(QDialog):
    """Styled camera picker dialog using a dropdown for friendlier interaction."""

    def __init__(
        self,
        camera_service: CameraService,
        cameras: List[CameraInfo],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.camera_service = camera_service
        self.cameras = cameras
        self.camera_combo: Optional[QComboBox] = None
        self.dialog_panel: Optional[QFrame] = None
        self.header_frame: Optional[QFrame] = None
        self.name_value_label: Optional[QLabel] = None
        self.model_value_label: Optional[QLabel] = None
        self.serial_value_label: Optional[QLabel] = None
        self.ip_value_label: Optional[QLabel] = None
        self.status_value_label: Optional[QLabel] = None
        self.confirm_button: Optional[QPushButton] = None
        self._drag_offset: Optional[QPoint] = None

        self.setWindowTitle("绑定相机")
        self.setModal(True)
        self.setMinimumSize(560, 260)
        self.resize(620, 320)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._build_ui()
        self._apply_theme()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(0)

        self.dialog_panel = QFrame()
        self.dialog_panel.setObjectName("dialogPanel")
        panel_layout = QVBoxLayout(self.dialog_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        root_layout.addWidget(self.dialog_panel)

        self.header_frame = QFrame()
        self.header_frame.setObjectName("dialogHeader")
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(20, 16, 20, 14)
        header_layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(10)

        title = QLabel("绑定相机")
        title.setObjectName("dialogTitle")
        header_row.addWidget(title)
        header_row.addStretch()

        close_button = QPushButton("×")
        close_button.setObjectName("dialogCloseButton")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setFixedSize(28, 28)
        close_button.clicked.connect(self.reject)
        header_row.addWidget(close_button)

        subtitle = QLabel("请选择要绑定到当前客户端的海康相机。系统会优先连接这台设备。")
        subtitle.setObjectName("dialogSubtitle")
        subtitle.setWordWrap(True)

        header_layout.addLayout(header_row)
        header_layout.addWidget(subtitle)
        panel_layout.addWidget(self.header_frame)

        body = QFrame()
        body.setObjectName("dialogBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(16, 16, 16, 16)
        body_layout.setSpacing(12)

        combo_label = QLabel("绑定到:")
        combo_label.setObjectName("fieldLabel")
        self.camera_combo = QComboBox()
        self.camera_combo.setObjectName("cameraBindingCombo")
        self.camera_combo.currentIndexChanged.connect(self._update_detail_panel)
        for index, camera in enumerate(self.cameras):
            self.camera_combo.addItem(self.camera_service.get_camera_display_label(camera), index)

        combo_row = QHBoxLayout()
        combo_row.setSpacing(12)
        combo_row.addWidget(combo_label)
        combo_row.addWidget(self.camera_combo, 1)
        body_layout.addLayout(combo_row)

        detail_frame = QFrame()
        detail_frame.setObjectName("generalFrame")
        detail_layout = QGridLayout(detail_frame)
        detail_layout.setContentsMargins(12, 12, 12, 12)
        detail_layout.setHorizontalSpacing(12)
        detail_layout.setVerticalSpacing(10)

        detail_pairs = [
            ("显示名称:", "name_value_label"),
            ("型号:", "model_value_label"),
            ("序列号:", "serial_value_label"),
            ("IP 地址:", "ip_value_label"),
            ("访问状态:", "status_value_label"),
        ]

        for row, (label_text, attr_name) in enumerate(detail_pairs):
            label = QLabel(label_text)
            label.setObjectName("fieldLabel")
            value = QLabel("-")
            value.setObjectName("fieldValue")
            value.setWordWrap(True)
            setattr(self, attr_name, value)
            detail_layout.addWidget(label, row, 0)
            detail_layout.addWidget(value, row, 1)

        body_layout.addWidget(detail_frame)

        panel_layout.addWidget(body, 1)

        footer = QHBoxLayout()
        footer.setContentsMargins(16, 0, 16, 16)
        footer.setSpacing(10)
        footer.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("dialogSecondaryButton")
        cancel_btn.clicked.connect(self.reject)

        self.confirm_button = QPushButton("确认绑定")
        self.confirm_button.setObjectName("dialogPrimaryButton")
        self.confirm_button.setEnabled(False)
        self.confirm_button.clicked.connect(self.accept)

        footer.addWidget(cancel_btn)
        footer.addWidget(self.confirm_button)
        panel_layout.addLayout(footer)

        if self.camera_combo.count() > 0:
            self.camera_combo.setCurrentIndex(0)
            self._update_detail_panel()

    def _apply_theme(self) -> None:
        config = get_config()
        theme_name = load_user_theme_preference()
        colors = resolve_theme_colors(theme_name, getattr(config.ui, "colors", {}))
        self.setStyleSheet(
            f"""
            QDialog {{
                background: transparent;
            }}
            #dialogPanel {{
                background-color: {colors['deep_graphite']};
                border: 1px solid {colors['dark_border']};
                border-radius: 12px;
            }}
            #dialogHeader {{
                background-color: {colors['deep_graphite']};
                border-bottom: 1px solid {colors['dark_border']};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}
            #dialogTitle {{
                color: {colors['arctic_white']};
                font-size: 22px;
                font-weight: 700;
            }}
            #dialogSubtitle {{
                color: {colors['cool_grey']};
                font-size: 13px;
            }}
            #dialogBody {{
                background-color: {colors['deep_graphite']};
            }}
            #generalFrame {{
                background-color: {colors['steel_grey']};
                border: 1px solid {colors['dark_border']};
                border-radius: 8px;
            }}
            QLabel#fieldLabel {{
                color: {colors['cool_grey']};
                font-size: 13px;
                min-width: 84px;
            }}
            QLabel#fieldValue {{
                color: {colors['arctic_white']};
                font-size: 13px;
                font-weight: 500;
            }}
            QComboBox#cameraBindingCombo {{
                background-color: {colors['steel_grey']};
                border: 1px solid {colors['dark_border']};
                border-radius: 6px;
                padding: 6px 28px 6px 10px;
                color: {colors['arctic_white']};
                font-size: 13px;
            }}
            QComboBox#cameraBindingCombo:focus {{
                border: 1px solid {colors['hover_orange']};
            }}
            QComboBox#cameraBindingCombo::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid {colors['dark_border']};
            }}
            QComboBox#cameraBindingCombo QAbstractItemView {{
                background-color: {colors['steel_grey']};
                border: 1px solid {colors['dark_border']};
                color: {colors['arctic_white']};
                selection-background-color: {colors['hover_orange']};
                selection-color: {colors['arctic_white']};
                outline: 0;
            }}
            QPushButton#dialogPrimaryButton {{
                background-color: {colors['hover_orange']};
                border: none;
                border-radius: 6px;
                color: {colors['arctic_white']};
                font-size: 14px;
                font-weight: 700;
                padding: 8px 18px;
                min-width: 96px;
            }}
            QPushButton#dialogPrimaryButton:hover {{
                background-color: {colors['amber']};
            }}
            QPushButton#dialogPrimaryButton:disabled {{
                background-color: {colors['steel_grey']};
                border: 1px solid {colors['dark_border']};
                color: {colors['cool_grey']};
            }}
            QPushButton#dialogSecondaryButton {{
                background-color: {colors['steel_grey']};
                border: 1px solid {colors['dark_border']};
                border-radius: 6px;
                color: {colors['arctic_white']};
                font-size: 14px;
                font-weight: 600;
                padding: 8px 18px;
                min-width: 88px;
            }}
            QPushButton#dialogSecondaryButton:hover {{
                border: 1px solid {colors['hover_orange']};
                color: {colors['hover_orange']};
            }}
            QPushButton#dialogCloseButton {{
                background: transparent;
                border: none;
                border-radius: 14px;
                color: {colors['cool_grey']};
                font-size: 18px;
                font-weight: 700;
            }}
            QPushButton#dialogCloseButton:hover {{
                background-color: {colors['steel_grey']};
                color: {colors['arctic_white']};
            }}
            """
        )

    def _update_detail_panel(self) -> None:
        if not self.camera_combo or not self.confirm_button:
            return

        index = self.camera_combo.currentIndex()
        has_selection = index >= 0
        self.confirm_button.setEnabled(has_selection)
        if not has_selection:
            for value_label in (
                self.name_value_label,
                self.model_value_label,
                self.serial_value_label,
                self.ip_value_label,
                self.status_value_label,
            ):
                if value_label:
                    value_label.setText("-")
            return

        camera = self.cameras[index]
        if self.name_value_label:
            self.name_value_label.setText(camera.name or "未命名相机")
        if self.model_value_label:
            self.model_value_label.setText(camera.model_name or "未知")
        if self.serial_value_label:
            self.serial_value_label.setText(camera.serial_number or "无序列号")
        if self.ip_value_label:
            self.ip_value_label.setText(camera.ip_address or "无IP")
        if self.status_value_label:
            self.status_value_label.setText(camera.access_status or "未知")

    def selected_camera(self) -> Optional[CameraInfo]:
        if not self.camera_combo:
            return None
        index = self.camera_combo.currentIndex()
        if index < 0:
            return None
        return self.cameras[index]

    def mousePressEvent(self, event) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.header_frame
            and self.header_frame.geometry().contains(event.position().toPoint())
        ):
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)
