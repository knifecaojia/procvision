"""
Process execution window for guided manufacturing operations.

Provides step-by-step visual guidance, inspection feedback, and process
navigation for operators performing assembly tasks.
"""

import logging
from typing import Optional, Dict, Any, List, Literal
from dataclasses import dataclass
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QProgressBar,
    QScrollArea, QGraphicsOpacityEffect, QComboBox, QStackedLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QImage
from PySide6.QtSvgWidgets import QSvgWidget

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
        self.order_number = process_data.get('name', 'ME-ASM-2024-001')
        self.operator_name = "张三"
        self.operator_station = "A01"
        self.network_status: Literal['online', 'offline'] = "online"
        self.total_steps = process_data.get('steps', 12)
        self.current_step_index = 0
        self.detection_status: DetectionStatus = "idle"
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

    def _initialize_steps(self) -> List[ProcessStep]:
        """Initialize process steps with sample data."""
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

        steps = []
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

        # Set window background
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                color: #ffffff;
                font-family: Arial;
            }
        """)

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

        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 8, 16, 8)
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

        # Center section: Progress
        center_section = self.create_progress_section()
        header_layout.addWidget(center_section)

        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setFixedHeight(32)
        separator2.setStyleSheet("background-color: #3a3a3a;")
        header_layout.addWidget(separator2)

        # Right section: Controls and status
        right_section = self.create_header_controls_section()
        header_layout.addWidget(right_section)

        # Separator
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.Shape.VLine)
        separator3.setFixedHeight(32)
        separator3.setStyleSheet("background-color: #3a3a3a;")
        header_layout.addWidget(separator3)

        # Camera controls section
        camera_section = self.create_camera_controls_section()
        header_layout.addWidget(camera_section)

        return header_frame

    def create_product_info_section(self) -> QWidget:
        """Create the left section with product SN and order number."""
        section = QWidget()
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Product SN
        sn_widget = self.create_info_item("📦", "产品 SN", self.product_sn)
        layout.addWidget(sn_widget)

        # Order number
        order_widget = self.create_info_item("📄", "订单号", self.order_number)
        layout.addWidget(order_widget)

        return section

    def create_info_item(self, icon: str, label: str, value: str) -> QWidget:
        """Create an info item with icon, label, and value."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 16px; color: #f97316;")
        layout.addWidget(icon_label)

        # Label and value
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)

        label_widget = QLabel(label)
        label_widget.setStyleSheet("font-size: 12px; color: #9ca3af;")

        value_widget = QLabel(value)
        value_widget.setStyleSheet("font-size: 14px; color: #ffffff;")

        text_layout.addWidget(label_widget)
        text_layout.addWidget(value_widget)

        layout.addLayout(text_layout)

        return widget

    def create_progress_section(self) -> QWidget:
        """Create the center section with step progress."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Progress text
        self.progress_label = QLabel(f"步骤: {self.current_step_index + 1} / {self.total_steps}")
        self.progress_label.setStyleSheet("font-size: 14px; color: #ffffff;")
        layout.addWidget(self.progress_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(self.total_steps)
        self.progress_bar.setValue(self.current_step_index + 1)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3a3a3a;
                border-radius: 3px;
                max-width: 300px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #f97316, stop:1 #fb923c);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        return section

    def create_header_controls_section(self) -> QWidget:
        """Create the right section with buttons and status."""
        section = QWidget()
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Return to task list button
        self.return_btn = QPushButton("← 返回任务列表")
        self.return_btn.setObjectName("returnButton")
        self.return_btn.setFixedHeight(32)
        self.return_btn.setStyleSheet("""
            QPushButton#returnButton {
                background-color: transparent;
                border: 1px solid #f97316;
                color: #f97316;
                border-radius: 4px;
                padding: 0 12px;
                font-size: 13px;
            }
            QPushButton#returnButton:hover {
                background-color: #f97316;
                color: #ffffff;
            }
        """)
        self.return_btn.clicked.connect(self.close)
        layout.addWidget(self.return_btn)

        # Product image button
        self.product_img_btn = QPushButton("🖼 产品实物图")
        self.product_img_btn.setObjectName("productImageButton")
        self.product_img_btn.setFixedHeight(32)
        self.product_img_btn.setStyleSheet("""
            QPushButton#productImageButton {
                background-color: #3b82f6;
                border: none;
                color: #ffffff;
                border-radius: 4px;
                padding: 0 12px;
                font-size: 13px;
            }
            QPushButton#productImageButton:hover {
                background-color: #2563eb;
            }
        """)
        layout.addWidget(self.product_img_btn)

        # Operator info
        operator_widget = QWidget()
        operator_layout = QHBoxLayout(operator_widget)
        operator_layout.setContentsMargins(0, 0, 0, 0)
        operator_layout.setSpacing(4)

        operator_icon = QLabel("👤")
        operator_icon.setStyleSheet("font-size: 16px; color: #9ca3af;")
        operator_layout.addWidget(operator_icon)

        operator_text = QLabel(f"{self.operator_name} ({self.operator_station})")
        operator_text.setStyleSheet("font-size: 14px; color: #ffffff;")
        operator_layout.addWidget(operator_text)

        layout.addWidget(operator_widget)

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
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Camera selection dropdown
        self.camera_combo = QComboBox()
        self.camera_combo.setObjectName("cameraCombo")
        self.camera_combo.setFixedHeight(32)
        self.camera_combo.setMinimumWidth(180)
        self.camera_combo.setStyleSheet("""
            QComboBox#cameraCombo {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 4px 8px;
                color: #ffffff;
                font-size: 13px;
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
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                selection-background-color: #f97316;
                color: #ffffff;
            }
        """)

        # Populate camera list
        self.refresh_camera_list()

        layout.addWidget(self.camera_combo)

        # Camera power toggle button
        self.camera_toggle_btn = QPushButton("📷 启动相机")
        self.camera_toggle_btn.setObjectName("cameraToggleButton")
        self.camera_toggle_btn.setFixedHeight(32)
        self.camera_toggle_btn.setCheckable(True)
        self.camera_toggle_btn.setStyleSheet("""
            QPushButton#cameraToggleButton {
                background-color: #22c55e;
                border: none;
                color: #ffffff;
                border-radius: 4px;
                padding: 0 12px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#cameraToggleButton:hover {
                background-color: #16a34a;
            }
            QPushButton#cameraToggleButton:checked {
                background-color: #ef4444;
            }
            QPushButton#cameraToggleButton:checked:hover {
                background-color: #dc2626;
            }
        """)
        self.camera_toggle_btn.clicked.connect(self.toggle_camera)

        layout.addWidget(self.camera_toggle_btn)

        # Refresh button
        refresh_btn = QPushButton("🔄")
        refresh_btn.setObjectName("cameraRefreshButton")
        refresh_btn.setFixedSize(32, 32)
        refresh_btn.setToolTip("刷新相机列表")
        refresh_btn.setStyleSheet("""
            QPushButton#cameraRefreshButton {
                background-color: #3b82f6;
                border: none;
                color: #ffffff;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton#cameraRefreshButton:hover {
                background-color: #2563eb;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_camera_list)

        layout.addWidget(refresh_btn)

        return section

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

        except Exception as e:
            logger.error(f"Failed to start camera preview: {e}")
            self.camera_toggle_btn.setChecked(False)
            if self.camera_service.current_camera:
                self.camera_service.disconnect_camera()

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

        except Exception as e:
            logger.error(f"Error stopping camera preview: {e}")

    def on_frame_ready(self, qimage: QImage):
        """Handle new frame from camera preview."""
        if not self.camera_active:
            return

        # Convert QImage to QPixmap and display
        pixmap = QPixmap.fromImage(qimage)
        if not pixmap.isNull():
            # Scale to fit while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.base_image_label.width(),
                self.base_image_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.base_image_label.setPixmap(scaled_pixmap)
            # Leave alignment set by stylesheet and do not override to top-left

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

        # Use QStackedLayout to overlay widgets in the same geometry
        stacked = QStackedLayout(container)
        stacked.setContentsMargins(0, 0, 0, 0)
        stacked.setStackingMode(QStackedLayout.StackingMode.StackAll)

        # Base layer: PCB image or camera feed
        self.base_image_label = QLabel()
        self.base_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.base_image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.base_image_label.setStyleSheet("""
            background-color: #0a0a0a;
            border: 1px solid #2a2a2a;
        """)

        # Initialize with neutral placeholder
        self.reset_camera_placeholder()

        stacked.addWidget(self.base_image_label)

        # Overlay layer: detection results
        self.overlay_widget = self.create_overlay_widget()
        stacked.addWidget(self.overlay_widget)

        return container

    def create_overlay_widget(self) -> QWidget:
        """Create the overlay widget for detection results."""
        overlay = QWidget()
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        overlay.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        overlay.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(overlay)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create overlays for detection results only
        self.pass_overlay = self.create_pass_overlay()
        self.fail_overlay = self.create_fail_overlay()

        # Stack overlays
        layout.addWidget(self.pass_overlay)
        layout.addWidget(self.fail_overlay)

        # Initially hide overlays
        self.update_overlay_visibility()

        return overlay

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
        self.pass_overlay.setVisible(is_pass)
        self.fail_overlay.setVisible(is_fail)

    def create_step_list_panel(self) -> QWidget:
        """Create the left sidebar with scrollable step list."""
        panel = QFrame()
        panel.setFixedWidth(288)
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
            font-size: 16px;
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
        """)

        # Container for step cards
        steps_container = QWidget()
        steps_layout = QVBoxLayout(steps_container)
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

        # Style based on status
        if step.status == 'current':
            card.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                              stop:0 rgba(249, 115, 22, 0.2),
                                              stop:1 rgba(251, 146, 60, 0.2));
                    border: 2px solid #f97316;
                    border-radius: 8px;
                    padding: 12px;
                }
            """)
        elif step.status == 'completed':
            card.setStyleSheet("""
                QFrame {
                    background-color: rgba(34, 197, 94, 0.1);
                    border: 2px solid rgba(34, 197, 94, 0.5);
                    border-radius: 8px;
                    padding: 12px;
                }
            """)
        else:  # pending
            card.setStyleSheet("""
                QFrame {
                    background-color: #252525;
                    border: 2px solid #3a3a3a;
                    border-radius: 8px;
                    padding: 12px;
                }
            """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Status icon
        icon_label = QLabel()
        if step.status == 'completed':
            icon_label.setText("✅")
            icon_label.setStyleSheet("font-size: 20px;")
        elif step.status == 'current':
            icon_label.setText("🔶")
            icon_label.setStyleSheet("font-size: 20px;")
        else:  # pending
            icon_label.setText("⚪")
            icon_label.setStyleSheet("font-size: 20px; color: #6b7280;")

        layout.addWidget(icon_label)

        # Text content
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        name_label = QLabel(step.name)
        if step.status == 'current':
            name_label.setStyleSheet("font-size: 14px; color: #fb923c; font-weight: bold;")
        elif step.status == 'completed':
            name_label.setStyleSheet("font-size: 14px; color: #22c55e;")
        else:
            name_label.setStyleSheet("font-size: 14px; color: #9ca3af;")

        desc_label = QLabel(step.description)
        if step.status == 'current':
            desc_label.setStyleSheet("font-size: 12px; color: #ffffff;")
        elif step.status == 'completed':
            desc_label.setStyleSheet("font-size: 12px; color: #d1d5db;")
        else:
            desc_label.setStyleSheet("font-size: 12px; color: #6b7280;")

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

        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(16, 12, 16, 12)
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

        # Label
        label = QLabel("当前操作")
        label.setStyleSheet("font-size: 14px; color: #9ca3af;")
        layout.addWidget(label)

        # Instruction text
        self.instruction_label = QLabel(self.current_instruction)
        self.instruction_label.setStyleSheet("font-size: 36px; color: #ffffff; font-weight: bold;")
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.instruction_label)

        return section

    def create_status_section(self) -> QWidget:
        """Create the right section with detection status indicator."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Status indicator based on detection_status
        if self.detection_status == "idle":
            # Idle state: gray circle + waiting text + start button
            indicator = QLabel("⚪")
            indicator.setStyleSheet("""
                font-size: 60px;
                color: #6b7280;
            """)
            indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)

            status_text = QLabel("等待检测")
            status_text.setStyleSheet("font-size: 24px; color: #9ca3af; font-weight: bold;")
            status_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.start_detection_btn = QPushButton("开始检测 (演示)")
            self.start_detection_btn.setObjectName("startDetectionButton")
            self.start_detection_btn.setFixedSize(140, 36)
            self.start_detection_btn.setStyleSheet("""
                QPushButton#startDetectionButton {
                    background-color: #f97316;
                    border: none;
                    color: #ffffff;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton#startDetectionButton:hover {
                    background-color: #ea580c;
                }
            """)
            self.start_detection_btn.clicked.connect(self.on_start_detection)

            layout.addWidget(indicator)
            layout.addWidget(status_text)
            layout.addWidget(self.start_detection_btn)

        elif self.detection_status == "pass":
            # Pass state: green circle with checkmark + PASS text
            indicator = QLabel("✅")
            indicator.setStyleSheet("""
                font-size: 60px;
                color: #22c55e;
            """)
            indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)

            status_text = QLabel("PASS")
            status_text.setStyleSheet("font-size: 32px; color: #22c55e; font-weight: bold;")
            status_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

            layout.addWidget(indicator)
            layout.addWidget(status_text)

        elif self.detection_status == "fail":
            # Fail state: red circle with alert + FAIL text (pulsing)
            indicator = QLabel("❌")
            indicator.setStyleSheet("""
                font-size: 60px;
                color: #ef4444;
            """)
            indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)

            status_text = QLabel("FAIL")
            status_text.setStyleSheet("font-size: 32px; color: #ef4444; font-weight: bold;")
            status_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

            layout.addWidget(indicator)
            layout.addWidget(status_text)

        return section

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
        if self.detection_status != 'idle':
            return

        logger.info("Starting detection simulation")
        self.detection_status = 'detecting'

        # Update UI
        self.update_overlay_visibility()
        self.rebuild_status_section()

        # Simulate detection with 1.5 second delay
        self.detection_timer = QTimer()
        self.detection_timer.setSingleShot(True)
        self.detection_timer.timeout.connect(self.on_detection_complete)
        self.detection_timer.start(1500)  # 1.5 seconds

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
            # Last step completed
            logger.info("All steps completed")
            self.set_step_status(self.current_step_index, 'completed')
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
            if step.status == 'current':
                card_widget.setStyleSheet("""
                    QFrame {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                  stop:0 rgba(249, 115, 22, 0.2),
                                                  stop:1 rgba(251, 146, 60, 0.2));
                        border: 2px solid #f97316;
                        border-radius: 8px;
                        padding: 12px;
                    }
                """)
            elif step.status == 'completed':
                card_widget.setStyleSheet("""
                    QFrame {
                        background-color: rgba(34, 197, 94, 0.1);
                        border: 2px solid rgba(34, 197, 94, 0.5);
                        border-radius: 8px;
                        padding: 12px;
                    }
                """)
            else:
                card_widget.setStyleSheet("""
                    QFrame {
                        background-color: #252525;
                        border: 2px solid #3a3a3a;
                        border-radius: 8px;
                        padding: 12px;
                    }
                    QFrame:hover {
                        border: 2px solid #6b7280;
                    }
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
        dialog.setFixedSize(400, 200)
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
        layout.setSpacing(20)

        # Success icon and message
        icon = QLabel("✅")
        icon.setStyleSheet("font-size: 64px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        message = QLabel("所有工艺步骤已完成!")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)

        summary = QLabel(f"工艺: {self.process_data.get('name')}\n完成步骤: {self.total_steps}/{self.total_steps}")
        summary.setStyleSheet("color: #9ca3af; font-size: 14px;")
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
