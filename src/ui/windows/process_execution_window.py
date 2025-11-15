"""
Process execution window for guided manufacturing operations.

Provides step-by-step visual guidance, inspection feedback, and process
navigation for operators performing assembly tasks.
"""

import logging
from typing import Optional, Dict, Any, List, Literal
from pathlib import Path
from dataclasses import dataclass
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QProgressBar,
    QScrollArea, QGraphicsOpacityEffect, QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QObject, QEvent
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QImage, QResizeEvent, QPainterPath, QFontDatabase, QFont
from PySide6.QtCore import QRect
from PySide6.QtSvgWidgets import QSvgWidget
from datetime import datetime
import numpy as np
import importlib.util
import sys
import json

logger = logging.getLogger(__name__)

# Type definitions
StepStatus = Literal['completed', 'current', 'pending']
DetectionStatus = Literal['idle', 'detecting', 'pass', 'fail']


@dataclass
class ProcessStep:
    """Data class for a process step."""
    id: int
    name: str
    description: str
    status: StepStatus = 'pending'


class OverlayWidget(QWidget):
    """Overlay for detection drawings and pass/fail cards."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: transparent;")
        self._boxes: List[QRect] = []
        self._status: DetectionStatus = 'idle'

    def set_boxes(self, boxes: List[QRect]):
        self._boxes = boxes
        self.update()

    def set_status(self, status: DetectionStatus):
        self._status = status
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._status not in ('pass', 'fail') or not self._boxes:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Determine color based on detection status
        if self._status == 'pass':
            pen_color = QColor(34, 197, 94, 200)  # green with alpha
            fill_color = QColor(34, 197, 94, 60)
            label_bg = QColor(34, 197, 94, 220)
        else:
            pen_color = QColor(239, 68, 68, 200)  # red with alpha
            fill_color = QColor(239, 68, 68, 60)
            label_bg = QColor(239, 68, 68, 220)

        pen = QPen(pen_color, 2)
        painter.setPen(pen)

        for r in self._boxes:
            painter.fillRect(r, fill_color)
            painter.drawRect(r)

            # draw simple label at top-left
            label_rect = QRect(r.topLeft().x(), r.topLeft().y() - 22, 38, 20)
            painter.fillRect(label_rect, label_bg)
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, "NG" if self._status == 'fail' else "OK")

        painter.end()

class ProcessExecutionWindow(QWidget):
    """
    Main window for process execution with visual guidance.

    This window provides operators with:
    - Step-by-step process navigation
    - Visual guidance overlays
    - Real-time inspection feedback
    - Product and operator information display
    """

    # Signal emitted when window is closed
    closed = Signal()

    def __init__(self, process_data: Dict[str, Any], parent: Optional[QWidget] = None, camera_service=None):
        """
        Initialize the process execution window.

        Args:
            process_data: Dictionary containing process metadata including:
                - id: Process ID
                - name: Process name (e.g., "ME-ASM-2024-001")
                - title: Process title
                - version: Process version
                - steps: Number of steps
                - type: Process type
            parent: Parent widget
        """
        super().__init__(parent)
        self.process_data = process_data
        self.camera_service = camera_service

        # Camera state
        self.preview_worker = None
        self.camera_active = False
        self.available_cameras = []

        # State management
        self.product_sn = "SN-2025-VM-00123"
        self.order_number = process_data.get('pid', process_data.get('name', 'ME-ASM-2024-001'))
        self.operator_name = "张三"
        self.operator_station = "A01"
        self.network_status: Literal['online', 'offline'] = "online"
        self.total_steps = len(process_data.get('steps_detail', [])) or process_data.get('steps', 12)
        self.current_step_index = 0
        self.detection_status: DetectionStatus = "idle"
        self.is_simulated = self._is_simulated_process()
        self._last_qimage: Optional[QImage] = None
        self._last_display_size = None
        self.detection_boxes: List[QRect] = []
        self.auto_start_next = self._read_auto_start_next_setting()
        # Overlay-related attributes (initialized early to avoid AttributeError)
        self.overlay_widget: Optional[QWidget] = None
        self.pass_overlay: Optional[QWidget] = None
        self.fail_overlay: Optional[QWidget] = None
        # Custom font (align with MainWindow): load and apply
        self.custom_font_family = "Arial"
        self.custom_font = QFont(self.custom_font_family)
        self._load_custom_font()
        # Initialize process steps
        self.steps: List[ProcessStep] = self._initialize_steps()
        self.current_instruction = self.steps[0].description if self.steps else "No steps available"

        # Set window properties
        self.setWindowTitle(f"工艺执行 - {process_data.get('name', '')}")
        self.setMinimumSize(1280, 720)
        self.resize(1800, 900)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowSystemMenuHint |
            Qt.WindowType.WindowMinMaxButtonsHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        # Set modal behavior
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Timers for detection workflow
        self.detection_timer: Optional[QTimer] = None
        self.advance_timer: Optional[QTimer] = None

        # Initialize UI
        self.init_ui()

        # Connect signals
        self.setup_connections()

        # Default to maximized window state (preserves native controls)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

        # Initialize with a neutral placeholder before any camera starts
        self.reset_camera_placeholder()

        logger.info(f"ProcessExecutionWindow initialized for process: {process_data.get('name')}")

        # Align overlay geometry with base video label once widget tree is ready
        QTimer.singleShot(0, self._align_overlay_geometry)

    def _load_custom_font(self) -> None:
        """Load custom font from assets and apply to this window (same as MainWindow)."""
        try:
            font_path = Path(__file__).resolve().parents[2] / "assets" / "SourceHanSansSC-Normal-2.otf"
        except Exception:
            font_path = Path("src/assets/SourceHanSansSC-Normal-2.otf").resolve()

        if not font_path.exists():
            logger.warning("Custom font file not found: %s", font_path)
            self.setFont(self.custom_font)
            return

        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id == -1:
            logger.warning("Failed to load custom font from: %s", font_path)
            self.setFont(self.custom_font)
            return

        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.custom_font = QFont(font_family)
        self.custom_font_family = font_family
        self.setFont(self.custom_font)
        logger.info("Custom font applied to ProcessExecutionWindow: %s", font_family)

    def _initialize_steps(self) -> List[ProcessStep]:
        """Initialize process steps from provided JSON (steps_detail) or fallback."""
        provided = self.process_data.get('steps_detail')
        steps: List[ProcessStep] = []
        if isinstance(provided, list) and provided:
            for i, item in enumerate(provided):
                step_number = item.get('step_number', i + 1)
                step_name = item.get('step_name', f"步骤 {step_number}")
                operation_guide = item.get('operation_guide', step_name)
                status: StepStatus = 'current' if i == 0 else 'pending'
                steps.append(ProcessStep(
                    id=i,
                    name=(step_name if step_name else f"步骤 {step_number}"),
                    description=operation_guide,
                    status=status
                ))
            return steps

        step_templates = [
            ("步骤 1", "安装电容 C101"),
            ("步骤 2", "安装电容 C102"),
            ("步骤 3", "安装电容 C103"),
            ("步骤 4", "安装电阻 R101"),
            ("步骤 5", "安装电阻 R102"),
            ("步骤 6", "安装电阻 R103"),
            ("步骤 7", "安装芯片 U101"),
            ("步骤 8", "安装连接器 J101"),
            ("步骤 9", "安装连接器 J102"),
            ("步骤 10", "焊接检查"),
            ("步骤 11", "电气测试"),
            ("步骤 12", "最终检验"),
        ]
        for i, (name, description) in enumerate(step_templates[: self.total_steps]):
            status: StepStatus = 'current' if i == 0 else 'pending'
            steps.append(ProcessStep(
                id=i,
                name=name,
                description=description,
                status=status
            ))
        return steps

    def get_current_step(self) -> Optional[ProcessStep]:
        """Get the current step."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def set_step_status(self, step_id: int, status: StepStatus):
        """Update the status of a specific step."""
        if 0 <= step_id < len(self.steps):
            self.steps[step_id].status = status
            logger.debug(f"Step {step_id} status updated to: {status}")

    def init_ui(self):
        """Initialize the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar
        header_widget = self.create_header_bar()
        main_layout.addWidget(header_widget)

        # Content area with step list and visual guidance
        content_widget = self.create_content_area()
        main_layout.addWidget(content_widget, 1)

        # Footer
        footer_widget = self.create_footer_bar()
        main_layout.addWidget(footer_widget)

        # Set window background and unify font family (scoped to this window only)
        self.setObjectName("processExecutionWindow")
        self.setStyleSheet(f"""
            QWidget#processExecutionWindow {{
                background-color: #1a1a1a;
                color: #ffffff;
                font-family: {self.custom_font_family};
            }}
        """)

        self.toast_container = QFrame(self)
        self.toast_container.setObjectName("toastOverlay")
        self.toast_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.toast_container.setStyleSheet("background-color: transparent;")
        self.toast_container.setFixedHeight(60)
        toast_layout = QHBoxLayout(self.toast_container)
        toast_layout.setContentsMargins(0, 0, 0, 0)
        toast_layout.addStretch()
        self.toast_label = QLabel()
        self.toast_label.setVisible(False)
        self.toast_label.setStyleSheet("padding:8px 12px; border-radius:16px; background-color:#3CC37A; color:#FFFFFF;")
        toast_layout.addWidget(self.toast_label)
        toast_layout.addStretch()
        self.toast_container.setVisible(False)
        try:
            self._position_toast()
        except Exception:
            pass

    def create_header_bar(self) -> QWidget:
        """Create the top header bar with product info, progress, and controls."""
        header_frame = QFrame()
        header_frame.setObjectName("headerBar")
        header_frame.setStyleSheet("""
            QFrame#headerBar {
                background-color: #252525;
                border-bottom: 1px solid #3a3a3a;
            }
        """)
        # 顶部整体高度适当增加
        header_frame.setMinimumHeight(56)

        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(20)

        # Left section: Product info
        left_section = self.create_product_info_section()
        header_layout.addWidget(left_section)

        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setFixedHeight(32)
        separator1.setStyleSheet("background-color: #3a3a3a;")
        header_layout.addWidget(separator1)

        # Center section: Progress（自适应填充宽度）
        center_section = self.create_progress_section()
        header_layout.addWidget(center_section, 1)

        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setFixedHeight(32)
        separator2.setStyleSheet("background-color: #3a3a3a;")
        header_layout.addWidget(separator2)

        # Right section: Controls 最右侧（包含相机/时钟/返回）
        right_section = self.create_header_controls_section()
        header_layout.addWidget(right_section)

        return header_frame

    def create_product_info_section(self) -> QWidget:
        """Create the left section with product SN, PID, and algorithm info."""
        section = QWidget()
        section.setObjectName("productInfoSection")
        section.setStyleSheet("""
            QWidget#productInfoSection {
                background-color: #252525;
            }
        """)
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Username（最左）
        username_widget = self.create_info_item("👤", "用户名", self.operator_name)
        layout.addWidget(username_widget)

        # Workstation
        station_widget = self.create_info_item("🛠", "工作站", self.operator_station)
        layout.addWidget(station_widget)

        # Product SN
        sn_widget = self.create_info_item("📦", "产品 SN", self.product_sn)
        layout.addWidget(sn_widget)

        # PID
        pid_widget = self.create_info_item("🏷", "PID", self.order_number)
        layout.addWidget(pid_widget)

        # Algorithm name
        algo_name = self.process_data.get('algorithm_name', self.process_data.get('name', ''))
        if algo_name:
            layout.addWidget(self.create_info_item("🧠", "算法", str(algo_name)))

        # Algorithm version
        algo_ver = self.process_data.get('algorithm_version', self.process_data.get('version', ''))
        if algo_ver:
            layout.addWidget(self.create_info_item("🔖", "版本", str(algo_ver)))

        return section

    def create_info_item(self, icon: str, label: str, value: str) -> QWidget:
        """Create an info item with icon, label, and value."""
        widget = QWidget()
        widget.setObjectName("infoItem")
        widget.setStyleSheet("""
            QWidget#infoItem {
                background-color: #252525;
            }
        """)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 19px; color: #f97316;")
        layout.addWidget(icon_label)

        # Label and value
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)

        label_widget = QLabel(label)
        label_widget.setStyleSheet("font-size: 14px; color: #9ca3af;")

        value_widget = QLabel(value)
        value_widget.setStyleSheet("font-size: 17px; color: #ffffff;")

        text_layout.addWidget(label_widget)
        text_layout.addWidget(value_widget)

        layout.addLayout(text_layout)

        return widget

    def create_progress_section(self) -> QWidget:
        """Create the center section with step progress."""
        section = QWidget()
        section.setObjectName("progressSection")
        section.setStyleSheet("""
            QWidget#progressSection {
                background-color: #252525;
            }
        """)
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Progress text
        self.progress_label = QLabel(f"步骤: {self.current_step_index + 1} / {self.total_steps}")
        self.progress_label.setStyleSheet("font-size: 16px; color: #ffffff;")
        layout.addWidget(self.progress_label)

        # Progress bar row
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(self.total_steps)
        self.progress_bar.setValue(self.current_step_index + 1)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e1e1e;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #f97316, stop:1 #fb923c);
                border-radius: 3px;
            }
        """)
        # 让进度条按可用空间自适应填充宽度
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row_layout.addWidget(self.progress_bar, 1)

        section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addLayout(row_layout)

        return section

    def create_header_controls_section(self) -> QWidget:
        """Create the right section with buttons and status."""
        section = QWidget()
        section.setObjectName("headerControlsSection")
        section.setStyleSheet("""
            QWidget#headerControlsSection {
                background-color: #252525;
            }
        """)
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        # Product image button（靠右组最前）
        self.product_img_btn = QPushButton("🖼 产品实物图")
        self.product_img_btn.setObjectName("productImageButton")
        self.product_img_btn.setFixedHeight(36)
        self.product_img_btn.setStyleSheet("""
            QPushButton#productImageButton {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                color: #ffffff;
                border-radius: 4px;
                padding: 0 14px;
                font-size: 16px;
            }
            QPushButton#productImageButton:hover {
                border: 1px solid #f97316;
            }
        """)
        layout.addWidget(self.product_img_btn)

        # 相机控件内联：列表、刷新、启动
        camera_section = self.create_camera_controls_section()
        layout.addWidget(camera_section)

        # Return to task list button（最右）
        self.return_btn = QPushButton("← 返回任务列表")
        self.return_btn.setObjectName("returnButton")
        self.return_btn.setFixedHeight(36)
        self.return_btn.setStyleSheet("""
            QPushButton#returnButton {
                background-color: #252525;
                border: 1px solid #f97316;
                color: #f97316;
                border-radius: 4px;
                padding: 0 14px;
                font-size: 16px;
            }
            QPushButton#returnButton:hover {
                background-color: #f97316;
                color: #ffffff;
            }
        """)
        self.return_btn.clicked.connect(self.close)
        layout.addWidget(self.return_btn)

        # 将时间放在最右侧，两行显示日期和时间
        layout.addStretch(1)
        clock_widget = QWidget()
        clock_widget.setObjectName("clockWidget")
        clock_layout = QVBoxLayout(clock_widget)
        clock_layout.setContentsMargins(0, 0, 0, 0)
        clock_layout.setSpacing(0)

        self.date_label = QLabel(datetime.now().strftime("%Y-%m-%d"))
        self.date_label.setObjectName("dateLabel")
        self.date_label.setStyleSheet("font-size: 14px; color: #22c55e;")

        self.time_label = QLabel(datetime.now().strftime("%H:%M:%S"))
        self.time_label.setObjectName("timeLabel")
        self.time_label.setStyleSheet("font-size: 18px; color: #22c55e;")

        clock_layout.addWidget(self.date_label)
        clock_layout.addWidget(self.time_label)
        layout.addWidget(clock_widget)

        # 时钟每秒刷新
        if not hasattr(self, "clock_timer"):
            self.clock_timer = QTimer(self)
            self.clock_timer.timeout.connect(self.update_current_time)
            self.clock_timer.start(1000)

        # Network status (hidden for this build)
        # self.network_widget = self.create_network_status()
        # layout.addWidget(self.network_widget)

        return section

    def create_network_status(self) -> QWidget:
        """Create network status indicator."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if self.network_status == "online":
            icon = QLabel("📶")
            icon.setStyleSheet("font-size: 16px; color: #22c55e;")
            text = QLabel("在线")
            text.setStyleSheet("font-size: 14px; color: #22c55e;")
        else:
            icon = QLabel("📵")
            icon.setStyleSheet("font-size: 16px; color: #ef4444;")
            text = QLabel("离线")
            text.setStyleSheet("font-size: 14px; color: #ef4444;")

        layout.addWidget(icon)
        layout.addWidget(text)

        return widget

    def create_camera_controls_section(self) -> QWidget:
        """Create the camera controls section with selection and power toggle."""
        section = QWidget()
        section.setObjectName("cameraControlsSection")
        section.setStyleSheet("""
            QWidget#cameraControlsSection {
                background-color: #252525;
            }
        """)
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Camera selection dropdown
        self.camera_combo = QComboBox()
        self.camera_combo.setObjectName("cameraCombo")
        self.camera_combo.setFixedHeight(36)
        self.camera_combo.setMinimumWidth(180)
        self.camera_combo.setStyleSheet("""
            QComboBox#cameraCombo {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 4px 8px;
                color: #ffffff;
                font-size: 16px;
            }
            QComboBox#cameraCombo:hover {
                border: 1px solid #f97316;
            }
            QComboBox#cameraCombo::drop-down {
                border: none;
            }
            QComboBox#cameraCombo::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #9ca3af;
                margin-right: 6px;
            }
            QComboBox QAbstractItemView {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                selection-background-color: #f97316;
                color: #ffffff;
            }
        """)

        # Populate camera list
        self.refresh_camera_list()

        layout.addWidget(self.camera_combo)

        # Refresh button（与父容器同色背景）
        refresh_btn = QPushButton("🔄")
        refresh_btn.setObjectName("cameraRefreshButton")
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.setToolTip("刷新相机列表")
        refresh_btn.setStyleSheet("""
            QPushButton#cameraRefreshButton {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                color: #ffffff;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton#cameraRefreshButton:hover {
                border: 1px solid #f97316;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_camera_list)

        layout.addWidget(refresh_btn)

        # Camera power toggle button（统一高度与字体）
        self.camera_toggle_btn = QPushButton("📷 启动相机")
        self.camera_toggle_btn.setObjectName("cameraToggleButton")
        self.camera_toggle_btn.setFixedHeight(36)
        self.camera_toggle_btn.setCheckable(True)
        self.camera_toggle_btn.setStyleSheet("""
            QPushButton#cameraToggleButton {
                background-color: #252525;
                border: 1px solid #22c55e;
                color: #22c55e;
                border-radius: 4px;
                padding: 0 14px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton#cameraToggleButton:hover {
                border: 1px solid #16a34a;
            }
            QPushButton#cameraToggleButton:checked {
                background-color: #252525;
                border: 1px solid #ef4444;
                color: #ef4444;
            }
            QPushButton#cameraToggleButton:checked:hover {
                border: 1px solid #dc2626;
            }
        """)
        self.camera_toggle_btn.clicked.connect(self.toggle_camera)

        layout.addWidget(self.camera_toggle_btn)

        return section

    def update_current_time(self):
        """Update the date and time labels in header bar."""
        now = datetime.now()
        if hasattr(self, "time_label") and self.time_label:
            self.time_label.setText(now.strftime("%H:%M:%S"))
        if hasattr(self, "date_label") and self.date_label:
            self.date_label.setText(now.strftime("%Y-%m-%d"))

    def refresh_camera_list(self):
        """Refresh the list of available cameras."""
        self.camera_combo.clear()
        self.available_cameras = []

        if not self.camera_service:
            self.camera_combo.addItem("无相机服务")
            return

        try:
            cameras = self.camera_service.discover_cameras()
            self.available_cameras = cameras

            if cameras:
                for camera in cameras:
                    serial = camera.serial_number or "N/A"
                    self.camera_combo.addItem(f"{camera.name} ({serial})")
                logger.info(f"Found {len(cameras)} cameras")
            else:
                self.camera_combo.addItem("未发现相机")
                logger.warning("No cameras found")

        except Exception as e:
            logger.error(f"Failed to discover cameras: {e}")
            self.camera_combo.addItem("相机发现失败")

    def toggle_camera(self, checked: bool):
        """Toggle camera preview on/off."""
        if checked:
            self.start_camera_preview()
        else:
            self.stop_camera_preview()

    def start_camera_preview(self):
        """Start camera preview."""
        if not self.camera_service:
            logger.warning("No camera service available")
            self.camera_toggle_btn.setChecked(False)
            return

        if not self.available_cameras:
            logger.warning("No cameras available")
            self.camera_toggle_btn.setChecked(False)
            return

        # Get selected camera index
        camera_index = self.camera_combo.currentIndex()
        if camera_index < 0 or camera_index >= len(self.available_cameras):
            logger.warning("Invalid camera selection")
            self.camera_toggle_btn.setChecked(False)
            return

        camera_info = self.available_cameras[camera_index]

        try:
            # Connect to camera
            if not self.camera_service.connect_camera(camera_info):
                logger.error("Failed to connect to camera")
                self.camera_toggle_btn.setChecked(False)
                return

            # Get camera device
            camera_device = self.camera_service.get_connected_camera()
            if not camera_device:
                logger.error("No camera device after connection")
                self.camera_toggle_btn.setChecked(False)
                return

            # Start streaming
            camera_device.start_stream()

            # Create and start preview worker
            from ..components.preview_worker import PreviewWorker
            self.preview_worker = PreviewWorker(camera_device)
            self.preview_worker.frame_ready.connect(self.on_frame_ready)
            self.preview_worker.error_occurred.connect(self.on_preview_error)
            self.preview_worker.start()

            self.camera_active = True
            self.camera_toggle_btn.setText("📷 停止相机")

            logger.info(f"Camera preview started: {camera_info.name}")
            try:
                self.rebuild_status_section()
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Failed to start camera preview: {e}")
            self.camera_toggle_btn.setChecked(False)
            if self.camera_service.current_camera:
                self.camera_service.disconnect_camera()
            try:
                self.rebuild_status_section()
            except Exception:
                pass

    def stop_camera_preview(self):
        """Stop camera preview."""
        try:
            # Stop preview worker
            if self.preview_worker:
                self.preview_worker.stop()
                self.preview_worker.wait(1000)  # Wait max 1 second
                self.preview_worker = None

            # Stop streaming and disconnect
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
            self.camera_toggle_btn.setText("📷 启动相机")
            self.camera_toggle_btn.setChecked(False)

            # Show neutral placeholder after stopping camera
            self.reset_camera_placeholder()

            logger.info("Camera preview stopped")
            try:
                self.rebuild_status_section()
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error stopping camera preview: {e}")

    def on_frame_ready(self, qimage: QImage):
        if not self.camera_active:
            return

        pixmap = QPixmap.fromImage(qimage)
        if not pixmap.isNull():
            try:
                self._last_frame_size = qimage.size()  # type: ignore[attr-defined]
            except Exception:
                self._last_frame_size = None
            self._last_qimage = qimage
            scaled_pixmap = pixmap.scaled(
                self.base_image_label.width(),
                self.base_image_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            try:
                self._last_display_size = scaled_pixmap.size()
            except Exception:
                self._last_display_size = None
            self.base_image_label.setPixmap(scaled_pixmap)

    def on_preview_error(self, error_msg: str):
        """Handle preview worker error."""
        logger.error(f"Preview error: {error_msg}")
        self.stop_camera_preview()

    def reset_camera_placeholder(self):
        """Show a neutral placeholder before the camera preview starts."""
        self.base_image_label.clear()
        self.base_image_label.setText("等待相机视频")
        # Ensure consistent styling: dark background and muted text
        self.base_image_label.setStyleSheet("""
            background-color: #0a0a0a;
            color: #6b7280;
            font-size: 18px;
            qproperty-alignment: AlignCenter;
        """)

    def _qimage_to_numpy(self, qimage: QImage):
        qi = qimage.convertToFormat(QImage.Format.Format_RGB888)
        w = qi.width()
        h = qi.height()
        bpl = qi.bytesPerLine()
        mv = qi.bits()
        buf = mv.tobytes()
        arr = np.frombuffer(buf, dtype=np.uint8)
        arr = arr.reshape(h, bpl)
        arr = arr[:, : w * 3]
        arr = arr.reshape(h, w, 3)
        return arr[:, :, ::-1].copy()

    def _ng_regions_to_rects(self, regions: List[Dict[str, Any]]) -> List[QRect]:
        rects: List[QRect] = []
        try:
            lw = self.base_image_label.width()
            lh = self.base_image_label.height()
            ow = self._last_frame_size.width() if self._last_frame_size else lw
            oh = self._last_frame_size.height() if self._last_frame_size else lh
            dw = self._last_display_size.width() if self._last_display_size else lw
            dh = self._last_display_size.height() if self._last_display_size else lh
            sx = dw / float(ow) if ow else 1.0
            sy = dh / float(oh) if oh else 1.0
            ox = int((lw - dw) / 2)
            oy = int((lh - dh) / 2)
            for r in regions:
                x1, y1, x2, y2 = r.get('box_coords', [0, 0, 0, 0])
                x = ox + int(x1 * sx)
                y = oy + int(y1 * sy)
                w = int((x2 - x1) * sx)
                h = int((y2 - y1) * sy)
                rects.append(QRect(x, y, max(1, w), max(1, h)))
        except Exception:
            pass
        return rects

    def create_content_area(self) -> QWidget:
        """Create the main content area with step list and visual guidance."""
        content = QWidget()
        layout = QHBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left: Step list panel
        step_panel = self.create_step_list_panel()
        layout.addWidget(step_panel)

        # Right: Visual guidance area
        self.visual_area = self.create_visual_guidance_area()
        layout.addWidget(self.visual_area, 1)

        return content

    def create_visual_guidance_area(self) -> QWidget:
        """Create the central visual guidance area with camera/PCB display and overlays."""
        # Main container
        container = QFrame()
        container.setObjectName("visualGuidanceArea")
        container.setStyleSheet("""
            QFrame#visualGuidanceArea {
                background-color: #1a1a1a;
            }
        """)

        # Replace StackAll with single layout where overlay is a sibling overlay of base label
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # Base layer: PCB image or camera feed
        self.base_image_label = QLabel()
        self.base_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.base_image_label.setMinimumSize(720, 480)
        self.base_image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.base_image_label.setStyleSheet("""
            background-color: #0a0a0a;
            border: 1px solid #2a2a2a;
        """)

        # Initialize with neutral placeholder
        self.reset_camera_placeholder()

        layout.addWidget(self.base_image_label)

        # Overlay layer: sibling overlay (geometry synced via event filter)
        self.overlay_widget = self.create_overlay_widget()
        # 将叠加层置为与视频区域同一父级，并初始隐藏
        self.overlay_widget.setParent(container)
        self.overlay_widget.setVisible(False)
        # 初始几何与层级
        self.overlay_widget.setGeometry(self.base_image_label.geometry())
        self.overlay_widget.raise_()
        # 同步叠加层几何：同时处理 Resize 和 Move
        self.base_image_label.installEventFilter(self._make_overlay_sync())

        return container

    def _align_overlay_geometry(self):
        """Explicitly align overlay geometry to base video label."""
        try:
            if self.overlay_widget and self.base_image_label:
                self.overlay_widget.setGeometry(self.base_image_label.geometry())
        except Exception:
            pass

    def _make_overlay_sync(self):
        """Factory an event filter to sync overlay geometry with base label"""
        class _Sync(QObject):
            def __init__(self, overlay):
                super().__init__()
                self._overlay = overlay
            def eventFilter(self, obj, event):
                if event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
                    # 保持叠加层与视频区域完全对齐
                    self._overlay.setGeometry(obj.geometry())
                    # 同步子控件尺寸以充满叠加层
                    try:
                        parent = self._overlay
                        for child in parent.children():
                            if isinstance(child, QWidget):
                                child.setGeometry(parent.rect())
                    except Exception:
                        pass
                return False
        return _Sync(self.overlay_widget)

    def create_overlay_widget(self) -> QWidget:
        """Create overlay for detection drawings and pass/fail cards"""
        w = OverlayWidget()
        # 叠加层不改变布局尺寸，仅覆盖视频区域
        w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        w.setStyleSheet("background-color: transparent;")

        self.pass_overlay = self.create_pass_overlay()
        self.fail_overlay = self.create_fail_overlay()
        self.pass_overlay.setParent(w)
        self.fail_overlay.setParent(w)
        # 初始状态均为隐藏，避免在尚未完成父子绑定时触发可见性更新
        w.setVisible(False)
        self.pass_overlay.setVisible(False)
        self.fail_overlay.setVisible(False)
        return w

    def create_guidance_overlay(self) -> QWidget:
        """Create the orange guidance box overlay."""
        widget = QWidget()
        widget.setObjectName("guidanceOverlay")

        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Guidance box container
        box_container = QFrame()
        box_container.setFixedSize(250, 180)
        box_container.setStyleSheet("""
            QFrame {
                background-color: rgba(249, 115, 22, 0.1);
                border: 3px solid #f97316;
                border-radius: 8px;
            }
        """)

        box_layout = QVBoxLayout(box_container)
        box_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        box_layout.setContentsMargins(0, 0, 0, 0)

        # Label above the box
        label = QLabel("安装位置")
        label.setStyleSheet("""
            background-color: #f97316;
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
            padding: 4px 12px;
            border-radius: 4px;
            margin-top: -20px;
        """)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(label)

        layout.addWidget(box_container)

        return widget

    def create_crosshair_overlay(self) -> QWidget:
        """Create the center crosshair overlay."""
        widget = QWidget()
        widget.setObjectName("crosshairOverlay")

        # We'll draw crosshair in paintEvent
        class CrosshairWidget(QWidget):
            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)

                # Set pen for crosshair
                pen = QPen(QColor(249, 115, 22, 100))  # Orange with 40% opacity
                pen.setWidth(1)
                painter.setPen(pen)

                # Get widget dimensions
                width = self.width()
                height = self.height()

                # Draw horizontal line (75% of width)
                h_start = int(width * 0.125)
                h_end = int(width * 0.875)
                painter.drawLine(h_start, height // 2, h_end, height // 2)

                # Draw vertical line (75% of height)
                v_start = int(height * 0.125)
                v_end = int(height * 0.875)
                painter.drawLine(width // 2, v_start, width // 2, v_end)

        crosshair = CrosshairWidget()
        crosshair.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(crosshair)

        return widget

    def create_pass_overlay(self) -> QWidget:
        """Create the PASS detection result overlay."""
        widget = QWidget()
        widget.setObjectName("passOverlay")
        widget.setStyleSheet("""
            background-color: transparent;
        """)

        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Large checkmark icon
        icon = QLabel("✅")
        icon.setStyleSheet("""
            font-size: 96px;
            color: #ffffff;
            background: rgba(34, 197, 94, 0.7);
            padding: 16px;
            border-radius: 12px;
        """)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # PASS text
        text = QLabel("PASS")
        text.setStyleSheet("""
            font-size: 72px;
            color: #ffffff;
            font-weight: bold;
            background: rgba(34, 197, 94, 0.7);
            padding: 16px 24px;
            border-radius: 12px;
        """)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(text)

        return widget

    def create_fail_overlay(self) -> QWidget:
        """Create the FAIL detection result overlay with error card."""
        widget = QWidget()
        widget.setObjectName("failOverlay")
        widget.setStyleSheet("""
            background-color: transparent;
        """)

        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # Large alert icon
        icon = QLabel("❌")
        icon.setStyleSheet("""
            font-size: 96px;
            color: #ffffff;
            background: rgba(239, 68, 68, 0.8);
            padding: 16px;
            border-radius: 12px;
        """)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # FAIL text
        text = QLabel("FAIL")
        text.setStyleSheet("""
            font-size: 72px;
            color: #ffffff;
            font-weight: bold;
            background: rgba(239, 68, 68, 0.8);
            padding: 16px 24px;
            border-radius: 12px;
        """)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Error card
        error_card = QFrame()
        error_card.setMaximumWidth(400)
        error_card.setStyleSheet("""
            QFrame {
                background: rgba(25, 25, 25, 0.85);
                border: 1px solid rgba(239, 68, 68, 0.7);
                border-radius: 10px;
                padding: 16px;
            }
        """)

        error_layout = QVBoxLayout(error_card)
        error_layout.setSpacing(12)

        # Error title
        error_title = QLabel("检测到缺陷")
        error_title.setStyleSheet("""
            color: #fecaca;
            font-size: 16px;
            font-weight: bold;
        """)

        # Error details
        error_details = QLabel("未检测到元件或位置偏移超出容差范围")
        error_details.setStyleSheet("""
            color: #fecaca;
            font-size: 14px;
        """)
        error_details.setWordWrap(True)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.retry_btn = QPushButton("重新检测")
        self.retry_btn.setObjectName("retryButton")
        self.retry_btn.setFixedHeight(36)
        self.retry_btn.setStyleSheet("""
            QPushButton#retryButton {
                background-color: #ef4444;
                border: none;
                color: #ffffff;
                border-radius: 4px;
                padding: 0 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#retryButton:hover {
                background-color: #dc2626;
            }
        """)

        self.skip_btn = QPushButton("跳过")
        self.skip_btn.setObjectName("skipButton")
        self.skip_btn.setFixedHeight(36)
        self.skip_btn.setStyleSheet("""
            QPushButton#skipButton {
                background-color: transparent;
                border: 1px solid #ef4444;
                color: #ef4444;
                border-radius: 4px;
                padding: 0 16px;
                font-size: 14px;
            }
            QPushButton#skipButton:hover {
                background-color: rgba(239, 68, 68, 0.1);
            }
        """)

        button_layout.addWidget(self.retry_btn)
        button_layout.addWidget(self.skip_btn)

        error_layout.addWidget(error_title)
        error_layout.addWidget(error_details)
        error_layout.addLayout(button_layout)

        layout.addWidget(icon)
        layout.addWidget(text)
        layout.addWidget(error_card)

        return widget

    def update_overlay_visibility(self):
        """Update visibility of overlays based on detection status."""
        # Show overlays only for pass/fail results
        is_pass = self.detection_status == 'pass'
        is_fail = self.detection_status == 'fail'
        # 顶层叠加层显示与隐藏（属性存在时才处理）
        overlay = getattr(self, 'overlay_widget', None)
        pass_ov = getattr(self, 'pass_overlay', None)
        fail_ov = getattr(self, 'fail_overlay', None)
        if overlay is not None:
            overlay.setVisible(is_pass or is_fail)
            try:
                overlay.set_status(self.detection_status)
                overlay.set_boxes(self.detection_boxes or [])
            except Exception:
                pass
        if pass_ov is not None:
            pass_ov.setVisible(is_pass)
        if fail_ov is not None:
            fail_ov.setVisible(is_fail)
        # 确保充满覆盖区域并位于顶层
        try:
            if overlay is not None and overlay.isVisible():
                if pass_ov is not None:
                    pass_ov.setGeometry(overlay.rect())
                if fail_ov is not None:
                    fail_ov.setGeometry(overlay.rect())
                overlay.raise_()
        except Exception:
            pass

    def create_step_list_panel(self) -> QWidget:
        """Create the left sidebar with scrollable step list."""
        panel = QFrame()
        panel.setFixedWidth(368)
        panel.setObjectName("stepListPanel")
        panel.setStyleSheet("""
            QFrame#stepListPanel {
                background-color: #1e1e1e;
                border-right: 1px solid #3a3a3a;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QLabel("工艺步骤")
        header.setStyleSheet("""
            background-color: #1e1e1e;
            color: #ffffff;
            font-size: 24px;
            font-weight: bold;
            padding: 12px;
            border-bottom: 1px solid #3a3a3a;
        """)
        layout.addWidget(header)

        # Scroll area for step cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: none;
            }
            QScrollArea > QWidget {
                background-color: #1e1e1e;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #1e1e1e;
            }
        """)

        # Container for step cards
        steps_container = QWidget()
        steps_container.setObjectName("stepsContainer")
        steps_container.setStyleSheet("""
            QWidget#stepsContainer {
                background-color: #1e1e1e;
            }
        """)
        steps_layout = QVBoxLayout(steps_container)
        # 使用外框样式，适当留出内边距与间距，避免“线框叠加”的拥挤感
        steps_layout.setContentsMargins(8, 8, 8, 8)
        steps_layout.setSpacing(8)

        # Create step cards
        self.step_card_widgets = []
        for step in self.steps:
            step_card = self.create_step_card(step)
            steps_layout.addWidget(step_card)
            self.step_card_widgets.append(step_card)

        steps_layout.addStretch()

        scroll_area.setWidget(steps_container)
        layout.addWidget(scroll_area)

        return panel

    def create_step_card(self, step: ProcessStep) -> QWidget:
        """Create a single step card widget."""
        card = QFrame()
        card.setObjectName(f"stepCard_{step.id}")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        # 增加最小高度以适配放大后的字体，避免内容垂直被裁剪
        card.setMinimumHeight(84)

        # Style based on status
        if step.status == 'current':
            card.setStyleSheet(f"""
                QFrame#stepCard_{step.id} {{
                    background-color: #262626;
                    border: 1px solid #f97316; /* ≤2px 外框，仅作用于当前卡片 */
                    border-radius: 8px;
                    padding: 10px 12px;
                }}
            """)
        elif step.status == 'completed':
            card.setStyleSheet(f"""
                QFrame#stepCard_{step.id} {{
                    background-color: #1e1e1e;
                    border: 1px solid rgba(34, 197, 94, 0.5); /* ≤2px 外框，仅作用于当前卡片 */
                    border-radius: 8px;
                    padding: 10px 12px;
                }}
            """)
        else:  # pending
            card.setStyleSheet(f"""
                QFrame#stepCard_{step.id} {{
                    background-color: #1e1e1e;
                    border: 1px solid #2a2a2a; /* ≤2px 外框，仅作用于当前卡片 */
                    border-radius: 8px;
                    padding: 10px 12px;
                }}
            """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Text content
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        name_label = QLabel(step.name)
        if step.status == 'current':
            name_label.setStyleSheet("font-size: 26px; color: #fb923c; font-weight: bold;")
        elif step.status == 'completed':
            name_label.setStyleSheet("font-size: 26px; color: #22c55e;")
        else:
            name_label.setStyleSheet("font-size: 26px; color: #9ca3af;")
        # 允许根据内容自适应高度
        try:
            name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        except Exception:
            pass

        desc_label = QLabel(step.description)
        if step.status == 'current':
            desc_label.setStyleSheet("font-size: 21px; color: #ffffff;")
        elif step.status == 'completed':
            desc_label.setStyleSheet("font-size: 21px; color: #d1d5db;")
        else:
            desc_label.setStyleSheet("font-size: 21px; color: #6b7280;")
        # 开启自动换行，避免文本被裁剪；允许根据内容自适应高度
        try:
            desc_label.setWordWrap(True)
            desc_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        except Exception:
            pass

        text_layout.addWidget(name_label)
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)

        return card

    def create_footer_bar(self) -> QWidget:
        """Create the bottom footer with current instruction and detection status."""
        footer_frame = QFrame()
        footer_frame.setObjectName("footerBar")
        footer_frame.setStyleSheet("""
            QFrame#footerBar {
                background-color: #252525;
                border-top: 1px solid #3a3a3a;
            }
        """)
        # 固定底部高度以避免状态更新时影响主内容区域尺寸
        footer_frame.setFixedHeight(120)

        footer_layout = QHBoxLayout(footer_frame)
        # 去掉上下边距，确保 120x120 的按钮不会被裁剪
        footer_layout.setContentsMargins(16, 0, 16, 0)
        footer_layout.setSpacing(20)
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Left section: Current instruction
        instruction_section = self.create_instruction_section()
        footer_layout.addWidget(instruction_section, 1)

        # Right section: Detection status
        self.status_section = self.create_status_section()
        footer_layout.addWidget(self.status_section)

        return footer_frame

    def create_instruction_section(self) -> QWidget:
        """Create the left section with current operation instruction."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Instruction text
        self.instruction_label = QLabel(self.current_instruction)
        self.instruction_label.setStyleSheet("font-size: 36px; color: #f97316; font-weight: bold;")
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.instruction_label)

        return section

    def create_status_section(self) -> QWidget:
        """Create the right section with detection status indicator.

        Footer shows only the start button when idle/pass/fail, and a simple
        text "检测中…" when detecting. No large icons are displayed here;
        PASS/FAIL are presented only on the video overlay.
        """
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 固定状态区宽度与按钮一致，确保左侧内容能撑满剩余空间
        section.setFixedWidth(250)
        section.setFixedHeight(120)

        # 统一使用一个按钮；检测中时仅改文案并禁用，不显示任何“检测中”标签
        detecting = self.detection_status == "detecting"
        allowed = self.camera_active and not detecting
        btn_text = "检测中" if detecting else "开始检测"
        self.start_detection_btn = QPushButton(btn_text)
        self.start_detection_btn.setObjectName("startDetectionButton")
        # 方形按钮，尺寸与底部信息栏高度一致
        self.start_detection_btn.setFixedSize(250, 120)
        self.start_detection_btn.setStyleSheet(f"""
            QPushButton#startDetectionButton {{
                background-color: #f97316;
                border: none;
                color: #ffffff;
                border-radius: 4px;
                font-size: 24px;
                font-weight: 700;
                font-family: {self.custom_font_family};
                padding: 0px;
            }}
            QPushButton#startDetectionButton:hover {{
                background-color: #ea580c;
            }}
            QPushButton#startDetectionButton:disabled {{
                background-color: #3a3a3a;
                color: #9ca3af;
            }}
        """)
        # Ensure button uses the loaded custom font
        try:
            self.start_detection_btn.setFont(self.custom_font)
        except Exception:
            pass
        self.start_detection_btn.setEnabled(allowed)
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

        return section

    def on_stop_detection(self):
        """Stop simulated detection early (bound to small stop button)."""
        if self.detection_timer and self.detection_timer.isActive():
            self.detection_timer.stop()
        self.detection_status = 'idle'
        self.update_overlay_visibility()
        self.rebuild_status_section()

    def setup_connections(self):
        """Setup signal connections for buttons and timers."""
        # Connect retry and skip buttons (created in FAIL overlay)
        self.retry_btn.clicked.connect(self.on_retry_detection)
        self.skip_btn.clicked.connect(self.on_skip_step)

        # Start detection button will be connected in create_status_section
        # but we need to recreate it when status changes
        pass

    def on_start_detection(self):
        """Handle start detection button click."""
        if self.detection_status != 'idle' or not self.camera_active:
            return

        if self.is_simulated:
            logger.info("Starting detection simulation")
            self.detection_status = 'detecting'
            self.update_overlay_visibility()
            self.rebuild_status_section()
            self.detection_timer = QTimer()
            self.detection_timer.setSingleShot(True)
            self.detection_timer.timeout.connect(self.on_detection_complete)
            self.detection_timer.start(1500)
            return

        if self._last_qimage is None:
            logger.warning("No camera frame available for external detection")
            return

        self.detection_status = 'detecting'
        self.update_overlay_visibility()
        self.rebuild_status_section()

        try:
            img = self._qimage_to_numpy(self._last_qimage)
            idx = self.current_step_index
            sd = self.process_data.get('steps_detail', [])
            step_number = sd[idx].get('step_number', idx + 1) if isinstance(sd, list) and idx < len(sd) else (idx + 1)
            pid = self.process_data.get('pid', None)
            base_dir = Path(__file__).resolve().parents[3] / "3rd" / "assembly_direction_checker"
            sys.path.insert(0, str(base_dir))
            inner_dir = base_dir / "assembly_direction_checker"
            if inner_dir.exists():
                sys.path.insert(0, str(inner_dir))
            original_src = sys.modules.get("src")
            try:
                if original_src is not None:
                    del sys.modules["src"]
                spec = importlib.util.spec_from_file_location("main_findal", str(base_dir / "main_findal.py"))
                module = importlib.util.module_from_spec(spec)
                assert spec is not None and spec.loader is not None
                spec.loader.exec_module(module)
                result = module.execute_step(img, step_number, pid=pid)
            finally:
                if original_src is not None:
                    sys.modules["src"] = original_src
            status = str(result.get('status', '')).upper()
            if status == 'OK':
                self.detection_boxes = []
                self.detection_status = 'pass'
                self.update_overlay_visibility()
                self.rebuild_status_section()
                self.advance_timer = QTimer()
                self.advance_timer.setSingleShot(True)
                self.advance_timer.timeout.connect(self.advance_to_next_step)
                self.advance_timer.start(2000)
            else:
                ng_regions = result.get('ng_regions', [])
                self.detection_boxes = self._ng_regions_to_rects(ng_regions)
                self.detection_status = 'fail'
                self.update_overlay_visibility()
                self.rebuild_status_section()
        except Exception as e:
            logger.error(f"External detection failed: {e}")
            self.detection_status = 'fail'
            self.detection_boxes = []
            self.update_overlay_visibility()
            self.rebuild_status_section()

    def on_detection_complete(self):
        """Handle detection completion with simulated result."""
        import random

        # 70% chance of PASS, 30% chance of FAIL
        passed = random.random() < 0.7

        if passed:
            logger.info("Detection PASSED")
            self.detection_status = 'pass'
            self.update_overlay_visibility()
            self.rebuild_status_section()

            # Auto-advance after 2 seconds
            self.advance_timer = QTimer()
            self.advance_timer.setSingleShot(True)
            self.advance_timer.timeout.connect(self.advance_to_next_step)
            self.advance_timer.start(2000)  # 2 seconds
        else:
            logger.info("Detection FAILED")
            self.detection_status = 'fail'
            self.update_overlay_visibility()
            self.rebuild_status_section()

    def advance_to_next_step(self):
        """Advance to the next process step."""
        if self.current_step_index >= len(self.steps) - 1:
            logger.info("All steps completed")
            self.set_step_status(self.current_step_index, 'completed')
            if getattr(self, 'auto_start_next', False):
                self.reset_for_next_product()
                try:
                    self.show_toast("已自动开始下一产品工艺检测", True)
                except Exception:
                    pass
            else:
                self.show_completion_dialog()
            return

        # Mark current step as completed
        self.set_step_status(self.current_step_index, 'completed')

        # Move to next step
        self.current_step_index += 1
        self.set_step_status(self.current_step_index, 'current')

        # Update UI
        self.current_instruction = self.steps[self.current_step_index].description
        self.instruction_label.setText(self.current_instruction)
        self.detection_status = 'idle'

        # Update progress
        self.progress_label.setText(f"步骤: {self.current_step_index + 1} / {self.total_steps}")
        self.progress_bar.setValue(self.current_step_index + 1)

        # Rebuild step cards to reflect new status
        self.rebuild_step_cards()

        # Update overlays
        self.update_overlay_visibility()
        self.rebuild_status_section()

        logger.info(f"Advanced to step {self.current_step_index + 1}")

    def show_toast(self, text: str, success: bool = True):
        if not hasattr(self, "toast_label"):
            return
        self.toast_label.setText(text)
        if success:
            self.toast_label.setStyleSheet("padding:8px 12px; border-radius:16px; background-color:#3CC37A; color:#FFFFFF;")
        else:
            self.toast_label.setStyleSheet("padding:8px 12px; border-radius:16px; background-color:#E85454; color:#FFFFFF;")
        self.toast_label.setVisible(True)
        self.toast_container.setVisible(True)
        try:
            self._position_toast()
        except Exception:
            pass
        QTimer.singleShot(2000, self.hide_toast)

    def hide_toast(self):
        if hasattr(self, "toast_label"):
            self.toast_label.setVisible(False)
            self.toast_container.setVisible(False)

    def _position_toast(self):
        h = self.toast_container.height() if self.toast_container.height() > 0 else 60
        y = max(0, self.height() - h - 16)
        self.toast_container.setGeometry(0, y, self.width(), h)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        try:
            if hasattr(self, 'toast_container') and self.toast_container.isVisible():
                self._position_toast()
        except Exception:
            pass

    def _is_simulated_process(self) -> bool:
        name = str(self.process_data.get('algorithm_name', self.process_data.get('name', '')))
        pid = str(self.process_data.get('pid', ''))
        return ('模拟' in name) or pid.startswith('SIM-')

    def _read_auto_start_next_setting(self) -> bool:
        try:
            p = Path.cwd() / "config.json"
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                general = data.get("general", {})
                return bool(general.get("auto_start_next", False))
        except Exception:
            pass
        return False

    def on_retry_detection(self):
        """Handle retry detection button click (from FAIL overlay)."""
        logger.info("Retrying detection")
        self.detection_status = 'idle'
        self.update_overlay_visibility()
        self.rebuild_status_section()

    def on_skip_step(self):
        """Handle skip step button click (from FAIL overlay)."""
        logger.info(f"Skipping step {self.current_step_index + 1}")
        # Mark as current but could add 'skipped' flag if needed
        self.advance_to_next_step()

    def rebuild_step_cards(self):
        """Rebuild step cards to reflect updated statuses."""
        # This is a simplified version - in production you'd update existing widgets
        # For now, just update the card styles by recreating them
        for i, (step, card_widget) in enumerate(zip(self.steps, self.step_card_widgets)):
            # Update styling based on new status
            obj_name = card_widget.objectName()
            if step.status == 'current':
                card_widget.setStyleSheet(f"""
                    QFrame#{obj_name} {{
                        background-color: #262626;
                        border: 1px solid #f97316; /* ≤2px 外框，仅作用于该卡片 */
                        border-radius: 8px;
                        padding: 10px 12px;
                    }}
                """)
            elif step.status == 'completed':
                card_widget.setStyleSheet(f"""
                    QFrame#{obj_name} {{
                        background-color: #1e1e1e;
                        border: 1px solid rgba(34, 197, 94, 0.5); /* ≤2px 外框，仅作用于该卡片 */
                        border-radius: 8px;
                        padding: 10px 12px;
                    }}
                """)
            else:
                card_widget.setStyleSheet(f"""
                    QFrame#{obj_name} {{
                        background-color: #1e1e1e;
                        border: 1px solid #2a2a2a; /* ≤2px 外框，仅作用于该卡片 */
                        border-radius: 8px;
                        padding: 10px 12px;
                    }}
                """)

    def rebuild_status_section(self):
        """Rebuild the status section in footer based on current detection status."""
        # Remove old status section
        old_section = self.status_section
        footer_layout = old_section.parent().layout()

        # Create new status section
        new_section = self.create_status_section()
        self.status_section = new_section

        # Replace in layout
        footer_layout.replaceWidget(old_section, new_section)
        old_section.deleteLater()

    def show_completion_dialog(self):
        """Show task completion dialog."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("任务完成")
        dialog.setFixedSize(520, 360)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #252525;
            }
            QLabel {
                color: #ffffff;
                font-size: 16px;
            }
            QPushButton {
                background-color: #22c55e;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(20)

        # Success icon and message
        icon = QLabel("✅")
        icon.setStyleSheet("font-size: 64px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        message = QLabel("所有工艺步骤已完成!")
        try:
            message.setWordWrap(True)
        except Exception:
            pass
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)

        summary = QLabel(f"工艺: {self.process_data.get('name')}\n完成步骤: {self.total_steps}/{self.total_steps}")
        summary.setStyleSheet("color: #9ca3af; font-size: 14px;")
        try:
            summary.setWordWrap(True)
        except Exception:
            pass
        summary.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Buttons
        button_box = QDialogButtonBox()
        next_btn = QPushButton("开始下一个产品")
        return_btn = QPushButton("返回任务列表")

        button_box.addButton(next_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton(return_btn, QDialogButtonBox.ButtonRole.RejectRole)

        next_btn.clicked.connect(dialog.accept)
        return_btn.clicked.connect(dialog.reject)

        layout.addWidget(icon)
        layout.addWidget(message)
        layout.addWidget(summary)
        layout.addWidget(button_box)

        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            # Reset to first step for next product
            logger.info("Starting next product")
            self.reset_for_next_product()
        else:
            # Return to task list
            logger.info("Returning to task list")
            self.close()

    def reset_for_next_product(self):
        """Reset the window for the next product."""
        # Reset all steps to pending except first (current)
        for i, step in enumerate(self.steps):
            if i == 0:
                step.status = 'current'
            else:
                step.status = 'pending'

        # Reset state
        self.current_step_index = 0
        self.detection_status = 'idle'
        self.current_instruction = self.steps[0].description

        # Update UI
        self.instruction_label.setText(self.current_instruction)
        self.progress_label.setText(f"步骤: 1 / {self.total_steps}")
        self.progress_bar.setValue(1)

        # Rebuild step cards and status
        self.rebuild_step_cards()
        self.update_overlay_visibility()
        self.rebuild_status_section()

        logger.info("Reset for next product")

    def closeEvent(self, event):
        """Handle window close event."""
        # Stop camera if active
        if self.camera_active:
            self.stop_camera_preview()

        # Clean up timers
        if self.detection_timer:
            self.detection_timer.stop()
        if self.advance_timer:
            self.advance_timer.stop()

        logger.info("ProcessExecutionWindow closing")
        self.closed.emit()
        super().closeEvent(event)

    def show_centered(self):
        """Show the window maximized by default, centering as fallback."""
        self.showMaximized()
        self.raise_()
        self.activateWindow()

        if self.isMaximized():
            return

        self.show()
        screen = self.screen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)
