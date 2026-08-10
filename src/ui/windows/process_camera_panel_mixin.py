from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..styles import refresh_widget_styles


class ProcessCameraPanelMixin:
    """Execution-window camera controls aligned to the bound-camera workflow."""

    def _create_camera_controls_section(self) -> QWidget:
        section = QWidget()
        section.setObjectName("cameraControlsSection")
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.bound_camera_card = QFrame()
        self.bound_camera_card.setObjectName("cameraBindingCard")
        card_layout = QVBoxLayout(self.bound_camera_card)
        card_layout.setContentsMargins(12, 6, 12, 6)
        card_layout.setSpacing(2)

        self.bound_camera_title_label = QLabel("执行相机")
        self.bound_camera_title_label.setObjectName("cameraBindingTitle")
        card_layout.addWidget(self.bound_camera_title_label)

        self.bound_camera_summary_label = QLabel("正在读取绑定信息...")
        self.bound_camera_summary_label.setObjectName("cameraBindingSummary")
        self.bound_camera_summary_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        card_layout.addWidget(self.bound_camera_summary_label)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(6)
        self.bound_camera_status_badge = QLabel("未绑定")
        self.bound_camera_status_badge.setObjectName("cameraBindingStatusBadge")
        self.bound_camera_status_badge.setProperty("cameraState", "unbound")
        self.bound_camera_detail_label = QLabel("请先在相机管理页绑定相机")
        self.bound_camera_detail_label.setObjectName("cameraBindingDetail")
        status_row.addWidget(self.bound_camera_status_badge)
        status_row.addWidget(self.bound_camera_detail_label)
        status_row.addStretch(1)
        card_layout.addLayout(status_row)

        self.refresh_btn = QPushButton("刷新状态")
        self.refresh_btn.setObjectName("cameraRefreshButton")
        self.refresh_btn.setFixedHeight(36)
        self.refresh_btn.clicked.connect(self.refresh_camera_list)

        self.camera_toggle_btn = QPushButton("连接相机")
        self.camera_toggle_btn.setObjectName("cameraToggleButton")
        self.camera_toggle_btn.setFixedHeight(36)
        self.camera_toggle_btn.clicked.connect(self.toggle_camera)

        self.camera_manage_btn = QPushButton("相机管理")
        self.camera_manage_btn.setObjectName("cameraManageButton")
        self.camera_manage_btn.setFixedHeight(36)
        self.camera_manage_btn.clicked.connect(self.open_camera_management_page)

        layout.addWidget(self.bound_camera_card, 1)
        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.camera_toggle_btn)
        layout.addWidget(self.camera_manage_btn)

        self.refresh_camera_list(auto_start=True)
        return section

    def update_bound_camera_panel(
        self,
        summary: str,
        status_text: str,
        detail: str,
        *,
        action_enabled: bool,
        connected: bool,
    ) -> None:
        self.bound_camera_summary_label.setText(summary)
        self.bound_camera_detail_label.setText(detail)
        self.bound_camera_status_badge.setText(status_text)
        self.bound_camera_status_badge.setProperty(
            "cameraState", self._map_camera_state(status_text)
        )
        refresh_widget_styles(self.bound_camera_status_badge)

        self.camera_toggle_btn.setEnabled(action_enabled)
        self.camera_toggle_btn.setText("重新连接" if connected else "连接相机")

    def _map_camera_state(self, status_text: str) -> str:
        mapping = {
            "未绑定": "unbound",
            "离线": "offline",
            "使用中/不可访问": "busy",
            "空闲可连接": "ready",
            "已连接": "connected",
            "预览中": "connected",
            "连接中...": "connecting",
            "连接失败": "error",
        }
        return mapping.get(status_text, "ready")

    def open_camera_management_page(self) -> None:
        host = self.parentWidget()
        while host is not None and not hasattr(host, "switch_page"):
            host = host.parentWidget()

        if host is None:
            self.show_toast("未找到相机管理页面入口", False)
            return

        try:
            self.stop_camera_preview()
        except Exception:
            pass

        try:
            host.switch_page("camera")
            host.showNormal()
            host.raise_()
            host.activateWindow()
        except Exception as exc:
            self.show_toast(f"打开相机管理失败: {exc}", False)
            return

        self.close()
