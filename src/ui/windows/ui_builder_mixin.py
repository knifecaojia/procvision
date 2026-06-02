import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QProgressBar,
    QScrollArea, QComboBox, QSizePolicy, QFileDialog, QTextEdit,
)
from PySide6.QtCore import Qt, QObject, QEvent, QRect, QSize
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QTextCursor
from ..styles import refresh_widget_styles
from ..components.process_preview_annotation_overlay import ProcessPreviewAnnotationOverlay
logger = logging.getLogger(__name__)
StepStatus = Literal['completed', 'current', 'pending']
DetectionStatus = Literal['idle', 'detecting', 'pass', 'fail']
class OverlayWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setObjectName("processOverlay")
        self._boxes: List[QRect] = []
        self._labels: List[str] = []
        self._status: DetectionStatus = 'idle'
        self._draw_ok: bool = True
        self._draw_ng: bool = True
    def set_boxes(self, boxes: List[QRect]):
        self._boxes = boxes
        self.update()
    def set_labels(self, labels: List[str]):
        self._labels = labels or []
        self.update()
    def set_status(self, status: DetectionStatus):
        self._status = status
        self.update()
    def set_draw_options(self, draw_ok: bool, draw_ng: bool):
        self._draw_ok = bool(draw_ok)
        self._draw_ng = bool(draw_ng)
        self.update()
    def paintEvent(self, event):
        super().paintEvent(event)
        if self._status not in ('pass', 'fail'):
            return
        if self._status == 'pass' and not self._draw_ok:
            return
        if self._status == 'fail' and not self._draw_ng:
            return
        if not self._boxes:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._status == 'pass':
            pen_color = QColor(34, 197, 94, 200)
            fill_color = QColor(34, 197, 94, 60)
            label_bg = QColor(34, 197, 94, 220)
        else:
            pen_color = QColor(239, 68, 68, 200)
            fill_color = QColor(239, 68, 68, 60)
            label_bg = QColor(239, 68, 68, 220)
        painter.setPen(QPen(pen_color, 2))
        for i, r in enumerate(self._boxes):
            painter.fillRect(r, fill_color)
            painter.drawRect(r)
            text = self._labels[i] if i < len(self._labels) else ("NG" if self._status == 'fail' else "OK")
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            font = painter.font()
            font.setPixelSize(13)
            painter.setFont(font)
            fm = painter.fontMetrics()
            tw = max(38, fm.horizontalAdvance(text) + 12)
            th = max(20, fm.height() + 6)
            label_rect = QRect(r.topLeft().x(), r.topLeft().y() - th - 2, tw, th)
            painter.fillRect(label_rect, label_bg)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, text)
            painter.setPen(QPen(pen_color, 2))
        painter.end()
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
        from PySide6.QtGui import QPainter, QColor, QBrush
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color_hex = self._colors.get(self._state, "#6b7280")
        painter.setBrush(QBrush(QColor(color_hex)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 16, 16)
        painter.end()
class UIBuilderMixin:
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.create_header_bar())
        content_widget = self._create_content_area()
        main_layout.addWidget(content_widget, 1)
        main_layout.addWidget(self._create_footer_bar())
        self.setObjectName("processExecutionWindow")
        self.toast_container = QFrame(self)
        self.toast_container.setObjectName("toastOverlay")
        self.toast_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.toast_container.setFixedHeight(60)
        toast_layout = QHBoxLayout(self.toast_container)
        toast_layout.setContentsMargins(0, 0, 0, 0)
        toast_layout.addStretch()
        self.toast_label = QLabel()
        self.toast_label.setVisible(False)
        self.toast_label.setObjectName("toastLabel")
        self.toast_label.setProperty("toastState", "success")
        toast_layout.addWidget(self.toast_label)
        toast_layout.addStretch()
        self.toast_container.setVisible(False)
        try:
            self._position_toast()
        except Exception:
            pass

    def _set_toast_state(self, state: str) -> None:
        if hasattr(self, "toast_label") and self.toast_label:
            self.toast_label.setProperty("toastState", state)
            refresh_widget_styles(self.toast_label)

    def _set_video_state(self, state: str) -> None:
        if hasattr(self, "base_image_label") and self.base_image_label:
            self.base_image_label.setProperty("videoState", state)
            refresh_widget_styles(self.base_image_label)

    def _apply_step_card_state(self, card, status, name_label, desc_label):
        for w in (card, name_label, desc_label):
            if w:
                w.setProperty("stepStatus", status)
                refresh_widget_styles(w)

    def create_header_bar(self) -> QWidget:
        header_frame = QFrame()
        header_frame.setObjectName("headerBar")
        header_frame.setMinimumHeight(56)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(20)
        header_layout.addWidget(self._create_product_info_section())
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFixedHeight(32)
        sep1.setObjectName("headerSeparator")
        header_layout.addWidget(sep1)
        header_layout.addWidget(self._create_progress_section(), 1)
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFixedHeight(32)
        sep2.setObjectName("headerSeparator")
        header_layout.addWidget(sep2)
        header_layout.addWidget(self._create_header_controls_section())
        return header_frame

    def _create_product_info_section(self) -> QWidget:
        section = QWidget()
        section.setObjectName("productInfoSection")
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self._create_info_item("👤", "用户名", self.operator_name))
        layout.addWidget(self._create_info_item("📦", "任务编码", self.product_sn))
        layout.addWidget(self._create_info_item("🏷", "工艺/工序ID", self.order_number))
        algo_name = self.process_data.get('algorithm_name', self.process_data.get('name', ''))
        if algo_name:
            layout.addWidget(self._create_info_item("🧠", "算法", str(algo_name)))
        algo_ver = self.process_data.get('algorithm_version', self.process_data.get('version', ''))
        if algo_ver:
            layout.addWidget(self._create_info_item("🔖", "版本", str(algo_ver)))
        return section

    def _create_info_item(self, icon: str, label: str, value: str) -> QWidget:
        widget = QWidget()
        widget.setObjectName("infoItem")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        icon_label = QLabel(icon)
        icon_label.setObjectName("productInfoIcon")
        layout.addWidget(icon_label)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        label_widget = QLabel(label)
        label_widget.setObjectName("productInfoLabel")
        value_widget = QLabel(value)
        value_widget.setObjectName("productInfoValue")
        text_layout.addWidget(label_widget)
        text_layout.addWidget(value_widget)
        layout.addLayout(text_layout)
        return widget

    def _create_progress_section(self) -> QWidget:
        section = QWidget()
        section.setObjectName("progressSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.progress_label = QLabel(f"步骤: {self.current_step_index + 1} / {self.total_steps}")
        self.progress_label.setObjectName("progressLabel")
        layout.addWidget(self.progress_label)
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(self.total_steps)
        self.progress_bar.setValue(self.current_step_index + 1)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row_layout.addWidget(self.progress_bar, 1)
        section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addLayout(row_layout)
        return section

    def _create_header_controls_section(self) -> QWidget:
        section = QWidget()
        section.setObjectName("headerControlsSection")
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._create_camera_controls_section())
        self.layout_toggle_btn = QPushButton("🔀 分栏")
        self.layout_toggle_btn.setObjectName("layoutToggleButton")
        self.layout_toggle_btn.setFixedHeight(36)
        self.layout_toggle_btn.setCheckable(True)
        split_mode = getattr(self, "split_layout_mode", False)
        self.layout_toggle_btn.setChecked(split_mode)
        self.layout_toggle_btn.setText("🔀 单画面" if split_mode else "🔀 分栏")
        self.layout_toggle_btn.clicked.connect(lambda checked: self.toggle_layout_mode(checked))
        layout.addWidget(self.layout_toggle_btn)
        self.return_btn = QPushButton("← 返回任务列表")
        self.return_btn.setObjectName("returnButton")
        self.return_btn.setFixedHeight(36)
        self.return_btn.clicked.connect(self.close)
        layout.addWidget(self.return_btn)
        layout.addStretch(1)
        clock_widget = QWidget()
        clock_widget.setObjectName("clockWidget")
        clock_layout = QVBoxLayout(clock_widget)
        clock_layout.setContentsMargins(0, 0, 0, 0)
        clock_layout.setSpacing(0)
        from datetime import datetime
        self.date_label = QLabel(datetime.now().strftime("%Y-%m-%d"))
        self.date_label.setObjectName("dateLabel")
        self.time_label = QLabel(datetime.now().strftime("%H:%M:%S"))
        self.time_label.setObjectName("timeLabel")
        try:
            f = self._make_time_debug_filter()
            self.time_label.installEventFilter(f)
            self._time_debug_filter = f
        except Exception:
            pass
        clock_layout.addWidget(self.date_label)
        clock_layout.addWidget(self.time_label)
        layout.addWidget(clock_widget)
        from PySide6.QtCore import QTimer
        if not hasattr(self, "clock_timer"):
            self.clock_timer = QTimer(self)
            self.clock_timer.timeout.connect(self.update_current_time)
            self.clock_timer.start(1000)
        return section

    def _create_camera_controls_section(self) -> QWidget:
        section = QWidget()
        section.setObjectName("cameraControlsSection")
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.camera_combo = QComboBox()
        self.camera_combo.setObjectName("cameraCombo")
        self.camera_combo.setFixedHeight(36)
        self.camera_combo.setMinimumWidth(180)
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setObjectName("cameraRefreshButton")
        self.refresh_btn.setFixedSize(36, 36)
        self.refresh_btn.setToolTip("刷新相机列表")
        self.refresh_btn.clicked.connect(self.refresh_camera_list)
        self.camera_toggle_btn = QPushButton("📷 启动相机")
        self.camera_toggle_btn.setObjectName("cameraToggleButton")
        self.camera_toggle_btn.setFixedHeight(36)
        self.camera_toggle_btn.setCheckable(True)
        self.camera_toggle_btn.clicked.connect(self.toggle_camera)
        layout.addWidget(self.camera_combo)
        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.camera_toggle_btn)
        self.refresh_camera_list(auto_start=True)
        return section

    def _create_content_area(self) -> QWidget:
        content = QWidget()
        layout = QHBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.step_list_panel = self._create_step_list_panel()
        if getattr(self, "split_layout_mode", False):
            self.step_list_panel.setVisible(False)
        layout.addWidget(self.step_list_panel)
        self.visual_area = self.create_visual_area_container()
        layout.addWidget(self.visual_area, 1)
        self.preview_annotation_widget = ProcessPreviewAnnotationOverlay(self.base_image_label.parent())
        self.preview_annotation_widget.setVisible(False)
        self.preview_annotation_widget.setGeometry(self.base_image_label.geometry())
        self.overlay_widget = self._create_overlay_widget()
        self.overlay_widget.setParent(self.base_image_label.parent())
        self.overlay_widget.setVisible(False)
        self.overlay_widget.setGeometry(self.base_image_label.geometry())
        self.preview_annotation_widget.raise_()
        self.overlay_widget.raise_()
        self.reset_camera_placeholder()
        return content

    def _create_overlay_widget(self) -> QWidget:
        w = OverlayWidget()
        w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.pass_overlay = self._create_pass_overlay()
        self.fail_overlay = self._create_fail_overlay()
        self.pass_overlay.setParent(w)
        self.fail_overlay.setParent(w)
        w.setVisible(False)
        self.pass_overlay.setVisible(False)
        self.fail_overlay.setVisible(False)
        return w

    def _create_pass_overlay(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("passOverlay")
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QLabel("✅")
        icon.setObjectName("passOverlayIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text = QLabel("PASS")
        text.setObjectName("passOverlayText")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)
        layout.addWidget(text)
        close_btn = QPushButton("✕")
        close_btn.setObjectName("overlayCloseButton")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self._dismiss_overlay)
        close_btn.setParent(widget)
        widget._close_btn = close_btn
        return widget

    def _create_fail_overlay(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("failOverlay")
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        icon = QLabel("❌")
        icon.setObjectName("failOverlayIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text = QLabel("FAIL")
        text.setObjectName("failOverlayText")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_card = QFrame()
        error_card.setObjectName("failErrorCard")
        error_card.setMaximumWidth(400)
        error_layout = QVBoxLayout(error_card)
        error_layout.setSpacing(12)
        error_details = QLabel("未检测到元件或位置偏移超出容差范围")
        error_details.setObjectName("failErrorDetails")
        error_details.setWordWrap(True)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        self.retry_btn = QPushButton("重新检测")
        self.retry_btn.setObjectName("retryButton")
        self.retry_btn.setFixedHeight(36)
        self.skip_btn = QPushButton("跳过")
        self.skip_btn.setObjectName("skipButton")
        self.skip_btn.setFixedHeight(36)
        button_layout.addWidget(self.retry_btn)
        button_layout.addWidget(self.skip_btn)
        error_layout.addWidget(error_details)
        error_layout.addLayout(button_layout)
        layout.addWidget(icon)
        layout.addWidget(text)
        layout.addWidget(error_card)
        close_btn = QPushButton("✕")
        close_btn.setObjectName("overlayCloseButton")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self._dismiss_overlay)
        close_btn.setParent(widget)
        widget._close_btn = close_btn
        return widget

    def _create_step_list_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFixedWidth(368)
        panel.setObjectName("stepListPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QLabel("工艺步骤")
        header.setObjectName("stepListHeader")
        layout.addWidget(header)
        scroll_area = QScrollArea()
        scroll_area.setObjectName("stepListScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.viewport().setObjectName("stepListViewport")
        steps_container = QWidget()
        steps_container.setObjectName("stepsContainer")
        steps_layout = QVBoxLayout(steps_container)
        steps_layout.setContentsMargins(8, 8, 8, 8)
        steps_layout.setSpacing(8)
        self.step_card_widgets = []
        for step in self.steps:
            step_card = self._create_step_card(step)
            steps_layout.addWidget(step_card)
            self.step_card_widgets.append(step_card)
        steps_layout.addStretch()
        scroll_area.setWidget(steps_container)
        layout.addWidget(scroll_area)
        return panel

    def _create_step_card(self, step) -> QWidget:
        card = QFrame()
        card.setObjectName("stepCard")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setMinimumHeight(84)
        card.setProperty("stepStatus", step.status)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        name_label = QLabel(step.name)
        name_label.setObjectName("stepNameLabel")
        try:
            name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        except Exception:
            pass
        desc_label = QLabel(step.description)
        desc_label.setObjectName("stepDescLabel")
        try:
            desc_label.setWordWrap(True)
            desc_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        except Exception:
            pass
        text_layout.addWidget(name_label)
        text_layout.addWidget(desc_label)
        layout.addLayout(text_layout, 1)
        self._apply_step_card_state(card, step.status, name_label, desc_label)
        return card

    def _create_step_bar_card(self, step) -> QWidget:
        card = QFrame()
        card.setObjectName("stepBarCard")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setFixedWidth(130)
        card.setMinimumHeight(60)
        card.setProperty("stepStatus", step.status)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num_label = QLabel(f"{step.id + 1}")
        num_label.setObjectName("stepBarNumLabel")
        num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label = QLabel(step.name)
        name_label.setObjectName("stepBarNameLabel")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        try:
            name_label.setWordWrap(False)
        except Exception:
            pass
        layout.addWidget(num_label)
        layout.addWidget(name_label)
        self._apply_step_bar_card_state(card, step.status, num_label, name_label)
        return card

    def _apply_step_bar_card_state(self, card, status, num_label, name_label):
        for w in (card, num_label, name_label):
            if w:
                w.setProperty("stepStatus", status)
                refresh_widget_styles(w)

    def _create_footer_bar(self) -> QWidget:
        footer_frame = QFrame()
        footer_frame.setObjectName("footerBar")
        footer_frame.setFixedHeight(120)
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(16, 0, 16, 0)
        footer_layout.setSpacing(20)
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(self._create_instruction_section(), 1)
        self.status_section = self._create_status_section()
        footer_layout.addWidget(self.status_section)
        return footer_frame

    def _create_instruction_section(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction_label = QTextEdit()
        self.instruction_label.setObjectName("instructionLabel")
        try:
            self.instruction_label.setReadOnly(True)
            self.instruction_label.setAcceptRichText(False)
            self.instruction_label.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.instruction_label.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.instruction_label.setFrameShape(QFrame.Shape.NoFrame)
            self.instruction_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass
        self._set_instruction_text(self.current_instruction)
        layout.addWidget(self.instruction_label)
        return section

    def _create_status_section(self) -> QWidget:
        section = QWidget()
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        section.setFixedHeight(120)

        auto_active = getattr(self, "auto_detect_active", False)
        detecting = self.detection_status == "detecting"
        allowed = (self.camera_active or (self._last_qimage is not None)) and not detecting
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
            try:
                self.start_detection_btn.setToolTip("请先开启相机")
            except Exception:
                pass
        layout.addWidget(self.start_detection_btn)

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

    def _dismiss_overlay(self):
        self._overlay_dismissed = True
        pass_ov = getattr(self, 'pass_overlay', None)
        fail_ov = getattr(self, 'fail_overlay', None)
        if pass_ov is not None:
            pass_ov.setVisible(False)
        if fail_ov is not None:
            fail_ov.setVisible(False)
        if self.detection_status == 'fail':
            try:
                self._stop_ng_flash()
            except Exception:
                pass
            self.detection_status = 'idle'
            self.rebuild_status_section()

    def update_overlay_visibility(self):
        is_pass = self.detection_status == 'pass'
        is_fail = self.detection_status == 'fail'
        dismissed = getattr(self, '_overlay_dismissed', False)
        has_boxes = bool(getattr(self, 'detection_boxes', []))
        is_auto = bool(getattr(self, "auto_detect_active", False))
        overlay = getattr(self, 'overlay_widget', None)
        pass_ov = getattr(self, 'pass_overlay', None)
        fail_ov = getattr(self, 'fail_overlay', None)
        if overlay is not None:
            overlay.setVisible(((is_pass or is_fail) or (dismissed and has_boxes)) and not is_auto)
            try:
                overlay.set_status(self.detection_status)
                overlay.set_boxes(self.detection_boxes if not is_auto else [])
                overlay.set_labels((getattr(self, 'detection_labels', []) or []) if not is_auto else [])
                overlay.set_draw_options(bool(self.draw_boxes_ok), bool(self.draw_boxes_ng))
            except Exception:
                pass
        if not dismissed and not is_auto:
            if pass_ov is not None:
                pass_ov.setVisible(is_pass)
            if fail_ov is not None:
                fail_ov.setVisible(is_fail)
        else:
            if pass_ov is not None:
                pass_ov.setVisible(False)
            if fail_ov is not None:
                fail_ov.setVisible(False)
        try:
            if overlay is not None and overlay.isVisible():
                target = pass_ov if (is_pass and not dismissed) else (fail_ov if (is_fail and not dismissed) else None)
                if target is not None:
                    target.adjustSize()
                    sz = target.sizeHint()
                    g = self._compute_prompt_geometry(sz)
                    target.setGeometry(g)
                    cb = getattr(target, '_close_btn', None)
                    if cb is not None:
                        cb.raise_()
                        cb.move(target.width() - cb.width() - 4, 4)
                overlay.raise_()
        except Exception:
            pass

    def _compute_prompt_geometry(self, child_size: QSize) -> QRect:
        r = self.overlay_widget.rect() if hasattr(self, 'overlay_widget') and self.overlay_widget is not None else QRect(0, 0, 0, 0)
        w = max(1, min(child_size.width(), r.width()))
        h = max(1, min(child_size.height(), r.height()))
        m = 16
        pos = str(getattr(self, 'result_prompt_position', 'center'))
        positions = {
            'top_left': (m, m), 'top_center': ((r.width() - w) // 2, m),
            'top_right': (max(0, r.width() - w - m), m),
            'center_left': (m, (r.height() - h) // 2),
            'center': ((r.width() - w) // 2, (r.height() - h) // 2),
            'center_right': (max(0, r.width() - w - m), (r.height() - h) // 2),
            'bottom_left': (m, max(0, r.height() - h - m)),
            'bottom_center': ((r.width() - w) // 2, max(0, r.height() - h - m)),
            'bottom_right': (max(0, r.width() - w - m), max(0, r.height() - h - m)),
        }
        x, y = positions.get(pos, positions['center'])
        return QRect(x, y, w, h)

    def _align_overlay_geometry(self):
        try:
            if getattr(self, "preview_annotation_widget", None) and self.base_image_label:
                self.preview_annotation_widget.setGeometry(self.base_image_label.geometry())
            if self.overlay_widget and self.base_image_label:
                self.overlay_widget.setGeometry(self.base_image_label.geometry())
        except Exception:
            pass

    def _make_time_debug_filter(self):
        class _Time(QObject):
            def __init__(self, window):
                super().__init__()
                self._w = window
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.MouseButtonDblClick:
                    try:
                        self._w._on_debug_pick_image()
                    except Exception:
                        pass
                    return True
                return False
        return _Time(self)

    def _on_debug_pick_image(self):
        initial = str(Path.cwd())
        path, _ = QFileDialog.getOpenFileName(self, "选择调试图片", initial, "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            return
        qi = QImage(path)
        if qi.isNull():
            try:
                self.show_toast("图片加载失败", False)
            except Exception:
                pass
            return
        self._debug_image_path = path
        self._debug_input_enabled = True
        self._last_qimage = qi
        try:
            self._last_frame_size = qi.size()
        except Exception:
            self._last_frame_size = None
        pm = QPixmap.fromImage(qi)
        spm = pm.scaled(
            self.base_image_label.width(), self.base_image_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
        )
        try:
            self._last_display_size = spm.size()
        except Exception:
            self._last_display_size = None
        self.base_image_label.setPixmap(spm)
        self._set_video_state("active")
        self.detection_status = 'idle'
        try:
            self.rebuild_status_section()
        except Exception:
            pass

    def _set_instruction_text(self, text: str) -> None:
        try:
            w = getattr(self, "instruction_label", None)
            if w is None:
                return
            if isinstance(w, QTextEdit):
                try:
                    opt = w.document().defaultTextOption()
                    opt.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    w.document().setDefaultTextOption(opt)
                except Exception:
                    pass
                w.setPlainText(str(text or ""))
                try:
                    w.selectAll()
                    w.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    w.moveCursor(QTextCursor.MoveOperation.Start)
                except Exception:
                    pass
                return
            w.setText(str(text or ""))
        except Exception:
            pass

    def _position_toast(self):
        h = self.toast_container.height() if self.toast_container.height() > 0 else 60
        y = max(0, self.height() - h - 16)
        self.toast_container.setGeometry(0, y, self.width(), h)

    def _create_network_status(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        is_online = self.network_status == "online"
        icon = QLabel("📶" if is_online else "📵")
        icon.setObjectName("networkStatusIcon")
        icon.setProperty("networkState", "online" if is_online else "offline")
        text = QLabel("在线" if is_online else "离线")
        text.setObjectName("networkStatusText")
        text.setProperty("networkState", "online" if is_online else "offline")
        layout.addWidget(icon)
        layout.addWidget(text)
        return widget

    def rebuild_step_cards(self):
        for step, card_widget in zip(self.steps, self.step_card_widgets):
            name_label = card_widget.findChild(QLabel, "stepNameLabel")
            desc_label = card_widget.findChild(QLabel, "stepDescLabel")
            self._apply_step_card_state(card_widget, step.status, name_label, desc_label)

    def rebuild_step_bar_cards(self):
        cards = getattr(self, "step_bar_card_widgets", [])
        for step, card_widget in zip(self.steps, cards):
            num_label = card_widget.findChild(QLabel, "stepBarNumLabel")
            name_label = card_widget.findChild(QLabel, "stepBarNameLabel")
            self._apply_step_bar_card_state(card_widget, step.status, num_label, name_label)
        try:
            self._scroll_step_bar_to_current()
        except Exception:
            pass

    def rebuild_status_section(self):
        old_section = self.status_section
        footer_layout = old_section.parent().layout()
        new_section = self._create_status_section()
        self.status_section = new_section
        footer_layout.replaceWidget(old_section, new_section)
        old_section.deleteLater()
