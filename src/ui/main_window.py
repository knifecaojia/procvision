"""
Main application window for industrial vision system.

Provides the primary interface after successful login with
session management, user information, and application functionality.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QStackedWidget,
    QSizePolicy,
    QComboBox,
    QLineEdit,
    QGridLayout,
    QSplitter,
    QApplication,
    QMessageBox,
    QToolButton,
    QStyle,
)
from PySide6.QtCore import Qt, QPoint, Signal, QSize
from PySide6.QtGui import QFontDatabase, QFont

try:
    from ..core.session import SessionManager
    from ..core.config import AppConfig, get_config
except ImportError:
    # Handle when running as script
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.core.session import SessionManager  # type: ignore
    from src.core.config import AppConfig, get_config  # type: ignore

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window for the industrial vision system.

    Displays the primary interface after successful authentication
    with user information, camera status, and application controls.
    """

    # Signal emitted when user requests logout
    logout_requested = Signal()

    def __init__(self, session_manager: SessionManager, config: Optional[AppConfig] = None):
        """Initialize the main window."""
        super().__init__()
        self.session_manager = session_manager
        self.config: AppConfig = config or get_config()
        self.colors = self.config.ui.colors
        
        # Load custom font
        font_path = os.path.join(os.path.dirname(__file__), "..", "assets", "SourceHanSansSC-Normal-2.otf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            self.custom_font = QFont(font_family)
        else:
            self.custom_font = QFont()
        
        self.init_ui()
        self.setup_style()
        self.setup_connections()
        self.load_preferences()
        
        # Set default page
        self.show_process_page()

    def init_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle(f"{self.config.app_title} v{self.config.app_version}")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumWidth(1000)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Main central widget
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Custom title bar
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(60)

        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(15)

        # Left side - App info
        title_label = QLabel(self.config.app_title)
        title_label.setObjectName("titleBarLabel")

        version_label = QLabel(f"v{self.config.app_version}")
        version_label.setObjectName("titleVersion")

        left_layout = QHBoxLayout()
        left_layout.addWidget(title_label)
        left_layout.addWidget(version_label)
        left_layout.addStretch()

        # Center - User info (简化用户信息显示)
        user_info = QLabel("User: Demo User | Workstation: WS-001 | ID: 001 | 2024-11-07 14:30")
        user_info.setObjectName("userInfo")
        user_info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Right side - Window controls
        self.min_button = QPushButton("−")
        self.min_button.setObjectName("windowButton")
        self.min_button.setFixedSize(30, 20)
        
        self.max_button = QPushButton("□")
        self.max_button.setObjectName("windowButton")
        self.max_button.setFixedSize(30, 20)

        self.close_button = QPushButton("×")
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(30, 20)

        right_layout = QHBoxLayout()
        right_layout.addWidget(user_info)
        right_layout.addStretch()
        right_layout.addWidget(self.min_button)
        right_layout.addWidget(self.max_button)
        right_layout.addWidget(self.close_button)

        layout.addLayout(left_layout)
        layout.addLayout(right_layout)

        # Enable window dragging
        title_bar.mousePressEvent = self.title_bar_mouse_press
        title_bar.mouseMoveEvent = self.title_bar_mouse_move
        title_bar.mouseReleaseEvent = self.title_bar_mouse_release

        main_layout.addWidget(title_bar)

        # Main content area with splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setObjectName("mainSplitter")
        
        # Create left navigation panel
        self.create_left_panel(self.splitter)
        
        # Create right content area
        self.create_right_content_area(self.splitter)
        
        main_layout.addWidget(self.splitter)

    def create_title_bar(self):
        """Create custom title bar with user info and window controls."""
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(60)

        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(15)

        # Left side - App info
        title_label = QLabel(self.config.app_title)
        title_label.setObjectName("titleBarLabel")

        version_label = QLabel(f"v{self.config.app_version}")
        version_label.setObjectName("titleVersion")

        left_layout = QHBoxLayout()
        left_layout.addWidget(title_label)
        left_layout.addWidget(version_label)
        left_layout.addStretch()

        # Center - User info (简化用户信息显示)
        user_info = QLabel("User: Demo User | Workstation: WS-001")
        user_info.setObjectName("userInfo")
        user_info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Right side - Window controls
        self.min_button = QPushButton("−")
        self.min_button.setObjectName("windowButton")
        self.min_button.setFixedSize(30, 20)
        
        self.max_button = QPushButton("□")
        self.max_button.setObjectName("windowButton")
        self.max_button.setFixedSize(30, 20)

        self.close_button = QPushButton("×")
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(30, 20)

        right_layout = QHBoxLayout()
        right_layout.addWidget(user_info)
        right_layout.addStretch()
        right_layout.addWidget(self.min_button)
        right_layout.addWidget(self.max_button)
        right_layout.addWidget(self.close_button)

        layout.addLayout(left_layout)
        layout.addLayout(right_layout)

        # Enable window dragging
        title_bar.mousePressEvent = self.title_bar_mouse_press
        title_bar.mouseMoveEvent = self.title_bar_mouse_move
        title_bar.mouseReleaseEvent = self.title_bar_mouse_release

        return title_bar

    def create_left_panel(self, parent):
        """Create left navigation panel."""
        left_frame = QFrame()
        left_frame.setObjectName("leftPanel")
        left_frame.setMinimumWidth(250)  # 使用最小宽度而不是固定宽度
        left_frame.setMaximumWidth(350)   # 设置最大宽度

        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Navigation menu
        nav_frame = QFrame()
        nav_frame.setObjectName("navFrame")
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(0, 20, 0, 20)
        nav_layout.setSpacing(5)

        # Navigation items
        self.nav_buttons = {}
        nav_items = [
            ("camera", "相机设置", "Camera Settings"),
            ("system", "系统设置", "System Settings"),
            ("model", "模型管理", "Model Management"),
            ("process", "工艺信息", "Process Information"),
            ("records", "工作记录", "Work Records")
        ]

        for item_id, cn_name, en_name in nav_items:
            button = self.create_nav_button(item_id, cn_name, en_name)
            nav_layout.addWidget(button)
            self.nav_buttons[item_id] = button

        nav_layout.addStretch()

        # Status info at bottom
        status_frame = QFrame()
        status_frame.setObjectName("statusFrame")
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(20, 15, 20, 15)

        # Connection status
        connection_layout = QHBoxLayout()
        connection_layout.setContentsMargins(0, 0, 0, 0)
        
        wifi_icon = QLabel("●")
        wifi_icon.setObjectName("wifiIcon")
        wifi_label = QLabel("Connected")
        wifi_label.setObjectName("wifiLabel")
        
        version_info = QLabel(f"v{self.config.app_version}")
        version_info.setObjectName("versionInfo")
        
        connection_layout.addWidget(wifi_icon)
        connection_layout.addWidget(wifi_label)
        connection_layout.addStretch()
        connection_layout.addWidget(version_info)
        
        status_layout.addLayout(connection_layout)
        
        # Last sync time
        sync_label = QLabel("Last sync: --:--:--")
        sync_label.setObjectName("syncLabel")
        status_layout.addWidget(sync_label)
        self.sync_label = sync_label

        left_layout.addWidget(nav_frame)
        left_layout.addWidget(status_frame)
        parent.addWidget(left_frame)

    def create_nav_button(self, item_id, cn_name, en_name):
        """Create a navigation button."""
        button = QPushButton()
        button.setObjectName(f"navButton_{item_id}")
        button.setFixedHeight(60)
        
        # Set default selected button to "process"
        if item_id == "process":
            button.setProperty("selected", True)
        
        # Create layout for button content
        layout = QHBoxLayout(button)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(15)
        
        # Icon placeholder (in a real app, you would use actual icons)
        icon_label = QLabel("■")  # Placeholder icon
        icon_label.setObjectName("navIcon")
        
        # Text layout
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        name_label = QLabel(cn_name)
        name_label.setObjectName("navName")
        
        desc_label = QLabel(en_name)
        desc_label.setObjectName("navDesc")
        
        text_layout.addWidget(name_label)
        text_layout.addWidget(desc_label)
        
        layout.addWidget(icon_label)
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # Connect button click
        button.clicked.connect(lambda checked, id=item_id: self.switch_page(id))
        
        return button

    def create_right_content_area(self, parent):
        """Create right content area with stacked widgets for different pages."""
        right_frame = QFrame()
        right_frame.setObjectName("rightPanel")

        layout = QVBoxLayout(right_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Stacked widget for different pages
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentStack")

        # Create pages
        self.camera_page = self.create_camera_page()
        self.system_page = self.create_system_page()
        self.model_page = self.create_model_page()
        self.process_page = self.create_process_page()  # 默认页面
        self.records_page = self.create_records_page()

        # Add pages to stack
        self.content_stack.addWidget(self.camera_page)
        self.content_stack.addWidget(self.system_page)
        self.content_stack.addWidget(self.model_page)
        self.content_stack.addWidget(self.process_page)
        self.content_stack.addWidget(self.records_page)

        # Set default page to process page (index 3)
        self.content_stack.setCurrentIndex(3)

        layout.addWidget(self.content_stack)
        parent.addWidget(right_frame)

    def create_camera_page(self):
        """Create camera settings page."""
        page = QFrame()
        page.setObjectName("cameraPage")
        
        layout = QVBoxLayout(page)
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
        
        # Upper section - Split into left (preview) and right (parameters)
        upper_splitter = QSplitter(Qt.Orientation.Horizontal)
        upper_splitter.setObjectName("cameraUpperSplitter")
        
        # Left side - Camera preview
        preview_container = QFrame()
        preview_container.setObjectName("previewContainer")
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(12)

        toolbar = QFrame()
        toolbar.setObjectName("previewToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(12)

        control_specs = [
            ("connect", "连接相机", "SP_DialogApplyButton"),
            ("disconnect", "断开连接", "SP_DialogCancelButton"),
            ("startPreview", "开始预览", "SP_MediaPlay"),
            ("stopPreview", "停止预览", "SP_MediaStop"),
            ("screenshot", "截图", "SP_DialogSaveButton"),
            ("record", "录像", "SP_DriveDVDIcon"),
        ]

        for control_id, tooltip, icon_name in control_specs:
            button = QToolButton()
            button.setObjectName("previewToolButton")
            button.setToolTip(tooltip)
            button.setProperty("controlId", control_id)
            pixmap_enum = getattr(QStyle.StandardPixmap, icon_name, QStyle.StandardPixmap.SP_FileIcon)
            if not hasattr(QStyle.StandardPixmap, icon_name):
                logger.debug("Standard icon %s not found, using default file icon", icon_name)
            button.setIcon(self.style().standardIcon(pixmap_enum))
            button.setIconSize(QSize(24, 24))
            button.setAutoRaise(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            toolbar_layout.addWidget(button)

        toolbar_layout.addStretch()
        preview_layout.addWidget(toolbar)
        
        preview_frame = QFrame()
        preview_frame.setObjectName("previewFrame")
        preview_frame.setMinimumSize(480, 360)
        preview_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        preview_inner_layout = QVBoxLayout(preview_frame)
        preview_inner_layout.setContentsMargins(0, 0, 0, 0)
        
        preview_label = QLabel("相机预览区域")
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_label.setObjectName("previewLabel")
        preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        preview_inner_layout.addWidget(preview_label)
        
        preview_layout.addWidget(preview_frame, 1)
        preview_layout.addStretch()
        
        # Right side - Camera parameters
        params_frame = QFrame()
        params_frame.setObjectName("paramsFrame")
        
        params_layout = QVBoxLayout(params_frame)
        params_layout.setContentsMargins(20, 20, 20, 20)
        params_layout.setSpacing(15)
        
        params_title = QLabel("相机参数")
        params_title.setObjectName("paramsTitle")
        
        # Exposure time
        exposure_layout = QHBoxLayout()
        exposure_label = QLabel("曝光时间 (μs):")
        exposure_label.setObjectName("paramLabel")
        exposure_input = QLineEdit("5000")
        exposure_input.setObjectName("paramInput")
        exposure_layout.addWidget(exposure_label)
        exposure_layout.addWidget(exposure_input)
        exposure_layout.addStretch()
        
        # Gain
        gain_layout = QHBoxLayout()
        gain_label = QLabel("增益:")
        gain_label.setObjectName("paramLabel")
        gain_input = QLineEdit("1.0")
        gain_input.setObjectName("paramInput")
        gain_layout.addWidget(gain_label)
        gain_layout.addWidget(gain_input)
        gain_layout.addStretch()
        
        # Resolution
        resolution_layout = QHBoxLayout()
        resolution_label = QLabel("分辨率:")
        resolution_label.setObjectName("paramLabel")
        resolution_combo = QComboBox()
        resolution_combo.addItems(["1920 × 1080", "1280 × 720", "640 × 480"])
        resolution_combo.setObjectName("paramCombo")
        resolution_layout.addWidget(resolution_label)
        resolution_layout.addWidget(resolution_combo)
        resolution_layout.addStretch()
        
        # FPS
        fps_layout = QHBoxLayout()
        fps_label = QLabel("帧率 (FPS):")
        fps_label.setObjectName("paramLabel")
        fps_input = QLineEdit("30")
        fps_input.setObjectName("paramInput")
        fps_layout.addWidget(fps_label)
        fps_layout.addWidget(fps_input)
        fps_layout.addStretch()
        
        # Apply button
        apply_btn = QPushButton("应用参数")
        apply_btn.setObjectName("applyButton")
        apply_btn.setFixedHeight(40)
        
        params_layout.addWidget(params_title)
        params_layout.addLayout(exposure_layout)
        params_layout.addLayout(gain_layout)
        params_layout.addLayout(resolution_layout)
        params_layout.addLayout(fps_layout)
        params_layout.addWidget(apply_btn)
        params_layout.addStretch()
        
        upper_splitter.addWidget(preview_container)
        upper_splitter.addWidget(params_frame)
        upper_splitter.setStretchFactor(0, 3)
        upper_splitter.setStretchFactor(1, 2)
        upper_splitter.setSizes([600, 360])
        
        layout.addWidget(upper_splitter)
        
        # Lower section - Camera connection and status
        lower_frame = QFrame()
        lower_frame.setObjectName("lowerFrame")
        
        lower_layout = QVBoxLayout(lower_frame)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.setSpacing(15)
        
        # Camera status info
        status_frame = QFrame()
        status_frame.setObjectName("statusFrame")
        
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(20, 20, 20, 20)
        status_layout.setSpacing(10)
        
        status_title = QLabel("相机状态")
        status_title.setObjectName("paramsTitle")
        
        # Status details
        status_grid = QGridLayout()
        status_grid.setSpacing(10)
        
        cam_model_label = QLabel("相机型号:")
        cam_model_label.setObjectName("paramLabel")
        cam_model_value = QLabel("MV-CE060-10GM")
        cam_model_value.setObjectName("paramValue")
        
        cam_status_label = QLabel("连接状态:")
        cam_status_label.setObjectName("paramLabel")
        cam_status_value = QLabel("未连接")
        cam_status_value.setObjectName("paramValue")
        
        cam_temp_label = QLabel("温度:")
        cam_temp_label.setObjectName("paramLabel")
        cam_temp_value = QLabel("38.5°C")
        cam_temp_value.setObjectName("paramValue")
        
        cam_fps_label = QLabel("实际帧率:")
        cam_fps_label.setObjectName("paramLabel")
        cam_fps_value = QLabel("0 FPS")
        cam_fps_value.setObjectName("paramValue")
        
        status_grid.addWidget(cam_model_label, 0, 0)
        status_grid.addWidget(cam_model_value, 0, 1)
        status_grid.addWidget(cam_status_label, 0, 2)
        status_grid.addWidget(cam_status_value, 0, 3)
        status_grid.addWidget(cam_temp_label, 1, 0)
        status_grid.addWidget(cam_temp_value, 1, 1)
        status_grid.addWidget(cam_fps_label, 1, 2)
        status_grid.addWidget(cam_fps_value, 1, 3)
        
        status_layout.addWidget(status_title)
        status_layout.addLayout(status_grid)
        
        lower_layout.addWidget(status_frame)
        
        layout.addWidget(lower_frame)
        layout.addStretch()
        
        return page

    def create_system_page(self):
        """Create system settings page."""
        page = QFrame()
        page.setObjectName("systemPage")
        
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header section
        header_frame = QFrame()
        header_frame.setObjectName("systemHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("系统设置")
        title_label.setObjectName("systemTitle")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
        
        # Save button
        save_btn = QPushButton("保存配置")
        save_btn.setObjectName("saveButton")
        save_btn.setFixedHeight(40)
        
        layout.addWidget(save_btn)
        
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
        addr_input = QLineEdit("192.168.1.100")
        addr_input.setObjectName("paramInput")
        addr_layout.addWidget(addr_label)
        addr_layout.addWidget(addr_input)
        
        # Server port
        port_layout = QHBoxLayout()
        port_label = QLabel("服务器端口:")
        port_label.setObjectName("paramLabel")
        port_input = QLineEdit("8080")
        port_input.setObjectName("paramInput")
        port_layout.addWidget(port_label)
        port_layout.addWidget(port_input)
        
        server_layout.addWidget(server_title)
        server_layout.addLayout(addr_layout)
        server_layout.addLayout(port_layout)
        
        layout.addWidget(server_frame)
        
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
        img_path_input = QLineEdit("C:\\VisionData\\Images")
        img_path_input.setObjectName("paramInput")
        img_browse_btn = QPushButton("浏览")
        img_browse_btn.setObjectName("browseButton")
        img_path_layout.addWidget(img_path_label)
        img_path_layout.addWidget(img_path_input)
        img_path_layout.addWidget(img_browse_btn)
        
        # Image retention days
        img_retention_layout = QHBoxLayout()
        img_retention_label = QLabel("图像保留时间（天）:")
        img_retention_label.setObjectName("paramLabel")
        img_retention_input = QLineEdit("30")
        img_retention_input.setObjectName("paramInput")
        img_retention_layout.addWidget(img_retention_label)
        img_retention_layout.addWidget(img_retention_input)
        
        image_layout.addWidget(image_title)
        image_layout.addLayout(img_path_layout)
        image_layout.addLayout(img_retention_layout)
        
        layout.addWidget(image_frame)
        
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
        log_path_input = QLineEdit("C:\\VisionData\\Logs")
        log_path_input.setObjectName("paramInput")
        log_browse_btn = QPushButton("浏览")
        log_browse_btn.setObjectName("browseButton")
        log_path_layout.addWidget(log_path_label)
        log_path_layout.addWidget(log_path_input)
        log_path_layout.addWidget(log_browse_btn)
        
        # Log retention days
        log_retention_layout = QHBoxLayout()
        log_retention_label = QLabel("日志保留时间（天）:")
        log_retention_label.setObjectName("paramLabel")
        log_retention_input = QLineEdit("90")
        log_retention_input.setObjectName("paramInput")
        log_retention_layout.addWidget(log_retention_label)
        log_retention_layout.addWidget(log_retention_input)
        
        log_layout.addWidget(log_title)
        log_layout.addLayout(log_path_layout)
        log_layout.addLayout(log_retention_layout)
        
        layout.addWidget(log_frame)
        layout.addStretch()
        
        return page

    def create_model_page(self):
        """Create model management page."""
        page = QFrame()
        page.setObjectName("modelPage")
        
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header section
        header_frame = QFrame()
        header_frame.setObjectName("modelHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("模型管理")
        title_label.setObjectName("modelTitle")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        download_btn = QPushButton("从服务器下载")
        download_btn.setObjectName("downloadButton")
        download_btn.setFixedHeight(40)
        
        upload_btn = QPushButton("上传模型")
        upload_btn.setObjectName("uploadButton")
        upload_btn.setFixedHeight(40)
        
        button_layout.addWidget(download_btn)
        button_layout.addWidget(upload_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Model table
        table_frame = QFrame()
        table_frame.setObjectName("tableFrame")
        
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a simple table-like structure using QLabels for demonstration
        # In a real application, you would use QTableWidget or QTableView
        headers_frame = QFrame()
        headers_frame.setObjectName("headersFrame")
        headers_layout = QHBoxLayout(headers_frame)
        headers_layout.setContentsMargins(10, 5, 10, 5)
        
        name_header = QLabel("模型名称")
        name_header.setObjectName("tableHeader")
        type_header = QLabel("类型")
        type_header.setObjectName("tableHeader")
        version_header = QLabel("版本")
        version_header.setObjectName("tableHeader")
        size_header = QLabel("大小")
        size_header.setObjectName("tableHeader")
        updated_header = QLabel("更新时间")
        updated_header.setObjectName("tableHeader")
        action_header = QLabel("操作")
        action_header.setObjectName("tableHeader")
        
        headers_layout.addWidget(name_header)
        headers_layout.addWidget(type_header)
        headers_layout.addWidget(version_header)
        headers_layout.addWidget(size_header)
        headers_layout.addWidget(updated_header)
        headers_layout.addWidget(action_header)
        
        table_layout.addWidget(headers_frame)
        
        # Sample model rows
        models = [
            {"name": "Edge Detection Standard", "type": "OpenCV", "version": "v2.1.0", "size": "1.2 MB", "updated": "2024-11-05"},
            {"name": "Component Position Check", "type": "OpenCV", "version": "v1.8.3", "size": "850 KB", "updated": "2024-11-01"},
            {"name": "PCB Defect Detection", "type": "YOLO", "version": "v5.0.2", "size": "45.6 MB", "updated": "2024-11-03"},
            {"name": "Screw Detection", "type": "YOLO", "version": "v3.2.1", "size": "28.3 MB", "updated": "2024-10-28"},
            {"name": "QR Code Reader", "type": "OpenCV", "version": "v1.5.0", "size": "600 KB", "updated": "2024-10-25"}
        ]
        
        for model in models:
            row_frame = QFrame()
            row_frame.setObjectName("rowFrame")
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(10, 5, 10, 5)
            
            name_label = QLabel(model["name"])
            name_label.setObjectName("tableCell")
            type_label = QLabel(model["type"])
            type_label.setObjectName("tableCell")
            version_label = QLabel(model["version"])
            version_label.setObjectName("tableCell")
            size_label = QLabel(model["size"])
            size_label.setObjectName("tableCell")
            updated_label = QLabel(model["updated"])
            updated_label.setObjectName("tableCell")
            
            action_layout = QHBoxLayout()
            action_layout.setSpacing(5)
            view_btn = QPushButton("查看")
            view_btn.setObjectName("tableButton")
            update_btn = QPushButton("更新")
            update_btn.setObjectName("tableButton")
            delete_btn = QPushButton("删除")
            delete_btn.setObjectName("deleteButton")
            
            action_layout.addWidget(view_btn)
            action_layout.addWidget(update_btn)
            action_layout.addWidget(delete_btn)
            
            row_layout.addWidget(name_label)
            row_layout.addWidget(type_label)
            row_layout.addWidget(version_label)
            row_layout.addWidget(size_label)
            row_layout.addWidget(updated_label)
            
            action_widget = QWidget()
            action_widget.setLayout(action_layout)
            row_layout.addWidget(action_widget)
            
            table_layout.addWidget(row_frame)
        
        table_layout.addStretch()
        layout.addWidget(table_frame)
        layout.addStretch()
        
        return page

    def create_records_page(self):
        """Create work records page."""
        page = QFrame()
        page.setObjectName("recordsPage")
        
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header section
        header_frame = QFrame()
        header_frame.setObjectName("recordsHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("工作记录")
        title_label.setObjectName("recordsTitle")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        date_btn = QPushButton("选择日期")
        date_btn.setObjectName("dateButton")
        date_btn.setFixedHeight(40)
        
        export_btn = QPushButton("导出报表")
        export_btn.setObjectName("exportButton")
        export_btn.setFixedHeight(40)
        
        button_layout.addWidget(date_btn)
        button_layout.addWidget(export_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Records table
        table_frame = QFrame()
        table_frame.setObjectName("tableFrame")
        
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        # Table headers
        headers_frame = QFrame()
        headers_frame.setObjectName("headersFrame")
        headers_layout = QHBoxLayout(headers_frame)
        headers_layout.setContentsMargins(10, 5, 10, 5)
        
        record_id_header = QLabel("记录编号")
        record_id_header.setObjectName("tableHeader")
        product_sn_header = QLabel("产品SN")
        product_sn_header.setObjectName("tableHeader")
        process_header = QLabel("工艺名称")
        process_header.setObjectName("tableHeader")
        operator_header = QLabel("操作员")
        operator_header.setObjectName("tableHeader")
        workstation_header = QLabel("工位")
        workstation_header.setObjectName("tableHeader")
        duration_header = QLabel("耗时")
        duration_header.setObjectName("tableHeader")
        status_header = QLabel("状态")
        status_header.setObjectName("tableHeader")
        action_header = QLabel("操作")
        action_header.setObjectName("tableHeader")
        
        headers_layout.addWidget(record_id_header)
        headers_layout.addWidget(product_sn_header)
        headers_layout.addWidget(process_header)
        headers_layout.addWidget(operator_header)
        headers_layout.addWidget(workstation_header)
        headers_layout.addWidget(duration_header)
        headers_layout.addWidget(status_header)
        headers_layout.addWidget(action_header)
        
        table_layout.addWidget(headers_frame)
        
        # Sample records
        records = [
            {
                "record_id": "REC-2024110701234",
                "product_sn": "SN20241107001",
                "process": "机械底座装配工艺",
                "operator": "张三",
                "workstation": "A01",
                "duration": "13min 22s",
                "status": "OK"
            },
            {
                "record_id": "REC-2024110701235",
                "product_sn": "SN20241107002",
                "process": "主控板PCB装配工艺",
                "operator": "李四",
                "workstation": "B02",
                "duration": "12min 15s",
                "status": "NG"
            },
            {
                "record_id": "REC-2024110701236",
                "product_sn": "SN20241107003",
                "process": "标准包装工艺流程",
                "operator": "王五",
                "workstation": "C01",
                "duration": "7min 18s",
                "status": "条件通过"
            },
            {
                "record_id": "REC-2024110701237",
                "product_sn": "SN20241107004",
                "process": "机械底座装配工艺",
                "operator": "张三",
                "workstation": "A01",
                "duration": "12min 35s",
                "status": "OK"
            },
            {
                "record_id": "REC-2024110701238",
                "product_sn": "SN20241107005",
                "process": "接口板PCB装配工艺",
                "operator": "赵六",
                "workstation": "B03",
                "duration": "8min 45s",
                "status": "OK"
            }
        ]
        
        for record in records:
            row_frame = QFrame()
            row_frame.setObjectName("rowFrame")
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(10, 5, 10, 5)
            
            record_id_label = QLabel(record["record_id"])
            record_id_label.setObjectName("tableCell")
            product_sn_label = QLabel(record["product_sn"])
            product_sn_label.setObjectName("tableCell")
            process_label = QLabel(record["process"])
            process_label.setObjectName("tableCell")
            operator_label = QLabel(record["operator"])
            operator_label.setObjectName("tableCell")
            workstation_label = QLabel(record["workstation"])
            workstation_label.setObjectName("tableCell")
            duration_label = QLabel(record["duration"])
            duration_label.setObjectName("tableCell")
            
            # Status with color coding
            status_label = QLabel(record["status"])
            status_label.setObjectName("statusLabel")
            if record["status"] == "OK":
                status_label.setStyleSheet("color: #3CC37A; font-weight: bold;")
            elif record["status"] == "NG":
                status_label.setStyleSheet("color: #E85454; font-weight: bold;")
            else:  # 条件通过
                status_label.setStyleSheet("color: #FFB347; font-weight: bold;")
            
            # Action button
            detail_btn = QPushButton("详情")
            detail_btn.setObjectName("tableButton")
            
            row_layout.addWidget(record_id_label)
            row_layout.addWidget(product_sn_label)
            row_layout.addWidget(process_label)
            row_layout.addWidget(operator_label)
            row_layout.addWidget(workstation_label)
            row_layout.addWidget(duration_label)
            row_layout.addWidget(status_label)
            row_layout.addWidget(detail_btn)
            
            table_layout.addWidget(row_frame)
        
        table_layout.addStretch()
        layout.addWidget(table_frame)
        layout.addStretch()
        
        return page

    def create_process_page(self):
        """Create process information page."""
        page = QFrame()
        page.setObjectName("processPage")
        
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header section
        header_frame = QFrame()
        header_frame.setObjectName("processHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("工艺信息")
        title_label.setObjectName("processTitle")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        sync_btn = QPushButton("从服务器同步")
        sync_btn.setObjectName("syncButton")
        sync_btn.setFixedHeight(40)
        
        create_btn = QPushButton("创建工艺")
        create_btn.setObjectName("createButton")
        create_btn.setFixedHeight(40)
        
        button_layout.addWidget(sync_btn)
        button_layout.addWidget(create_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Process cards
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(15)
        
        # Sample processes
        processes = [
            {
                "id": "ME-ASM-2024-001",
                "title": "机械底座装配工艺",
                "type": "机械安装",
                "version": "v3.2",
                "steps": 12,
                "models": ["Edge Detection Standard", "Screw Detection"],
                "status": "已发布",
                "updated": "2024-11-05"
            },
            {
                "id": "PCB-ASM-2024-015",
                "title": "主控板PCB装配工艺",
                "type": "PCB安装",
                "version": "v2.8",
                "steps": 8,
                "models": ["PCB Defect Detection", "Component Position Check"],
                "status": "已发布",
                "updated": "2024-11-03"
            },
            {
                "id": "PKG-STD-2024-003",
                "title": "标准包装工艺流程",
                "type": "包装",
                "version": "v1.5",
                "steps": 5,
                "models": ["QR Code Reader", "Assembly Classification"],
                "status": "已发布",
                "updated": "2024-10-28"
            }
        ]
        
        for process in processes:
            card_frame = QFrame()
            card_frame.setObjectName("cardFrame")
            
            card_layout = QVBoxLayout(card_frame)
            card_layout.setContentsMargins(20, 20, 20, 20)
            card_layout.setSpacing(15)
            
            # Card header
            card_header_layout = QHBoxLayout()
            card_title = QLabel(process["title"])
            card_title.setObjectName("cardTitle")
            
            card_type = QLabel(process["type"])
            card_type.setObjectName("cardType")
            
            card_status = QLabel(process["status"])
            card_status.setObjectName("cardStatus")
            
            card_header_layout.addWidget(card_title)
            card_header_layout.addStretch()
            card_header_layout.addWidget(card_type)
            card_header_layout.addWidget(card_status)
            
            # Card details
            details_layout = QHBoxLayout()
            
            id_label = QLabel(f"编号: {process['id']}")
            id_label.setObjectName("detailLabel")
            
            version_label = QLabel(f"版本: {process['version']}")
            version_label.setObjectName("detailLabel")
            
            steps_label = QLabel(f"工艺步骤: {process['steps']} 步")
            steps_label.setObjectName("detailLabel")
            
            updated_label = QLabel(f"更新时间: {process['updated']}")
            updated_label.setObjectName("detailLabel")
            
            details_layout.addWidget(id_label)
            details_layout.addWidget(version_label)
            details_layout.addWidget(steps_label)
            details_layout.addWidget(updated_label)
            
            # Models
            models_label = QLabel("关联模型:")
            models_label.setObjectName("modelsLabel")
            
            models_layout = QHBoxLayout()
            for model in process["models"]:
                model_tag = QLabel(model)
                model_tag.setObjectName("modelTag")
                models_layout.addWidget(model_tag)
            models_layout.addStretch()
            
            # Action buttons
            action_layout = QHBoxLayout()
            action_layout.setSpacing(10)
            
            view_btn = QPushButton("查看详情")
            view_btn.setObjectName("viewButton")
            view_btn.setFixedHeight(35)
            
            start_btn = QPushButton("启动工艺")
            start_btn.setObjectName("startButton")
            start_btn.setFixedHeight(35)
            
            edit_btn = QPushButton("编辑")
            edit_btn.setObjectName("editButton")
            edit_btn.setFixedHeight(35)
            
            action_layout.addWidget(view_btn)
            action_layout.addWidget(start_btn)
            action_layout.addWidget(edit_btn)
            action_layout.addStretch()
            
            card_layout.addLayout(card_header_layout)
            card_layout.addLayout(details_layout)
            card_layout.addWidget(models_label)
            card_layout.addLayout(models_layout)
            card_layout.addLayout(action_layout)
            
            cards_layout.addWidget(card_frame)
        
        layout.addLayout(cards_layout)
        layout.addStretch()
        
        return page

    def show_process_page(self):
        """Show the process page by default during startup."""
        if getattr(self, "content_stack", None):
            self.switch_page("process")

    def switch_page(self, page_id):
        """Switch to the specified page."""
        # Update button states
        for btn_id, button in self.nav_buttons.items():
            if btn_id == page_id:
                button.setProperty("selected", True)
            else:
                button.setProperty("selected", False)
            # Force style update
            button.style().unpolish(button)
            button.style().polish(button)
        
        # Switch content
        page_map = {
            "camera": 0,
            "system": 1,
            "model": 2,
            "process": 3,
            "records": 4
        }
        
        if page_id in page_map:
            self.content_stack.setCurrentIndex(page_map[page_id])

    def title_bar_mouse_press(self, event):
        """Handle mouse press on title bar for window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def title_bar_mouse_move(self, event):
        """Handle mouse move on title bar for window dragging."""
        if event.buttons() & Qt.MouseButton.LeftButton and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def title_bar_mouse_release(self, event):
        """Handle mouse release on title bar."""
        self.drag_pos = None
        event.accept()

    def setup_style(self):
        """Apply styles to the main window."""
        # 获取自定义字体族
        font_family = self.custom_font.family() if self.custom_font.family() else "Arial"
        
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.colors['deep_graphite']};
                border-radius: 10px;
                font-family: "{font_family}";
            }}

            /* 当窗口最大化时移除圆角 */
            QMainWindow[maximized="true"] {{
                border-radius: 0px;
            }}

            #centralWidget {{
                background-color: {self.colors['deep_graphite']};
                border-radius: 10px;
                font-family: "{font_family}";
            }}

            QMainWindow[maximized="true"] #centralWidget {{
                border-radius: 0px;
            }}

            #titleBar {{
                background-color: {self.colors['deep_graphite']};
                border-bottom: 1px solid {self.colors['dark_border']};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}

            QMainWindow[maximized="true"] #titleBar {{
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }}

            #titleBarLabel {{
                color: {self.colors['arctic_white']};
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 1px;
            }}

            #titleVersion {{
                color: {self.colors['cool_grey']};
                font-size: 12px;
                text-transform: uppercase;
            }}

            #userInfo {{
                color: {self.colors['arctic_white']};
                font-size: 16px;  /* 增大字体 */
                font-weight: normal;
            }}

            #windowButton {{
                background-color: transparent;
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                font-weight: bold;
                border-radius: 3px;
            }}

            #windowButton:hover {{
                border: 1px solid {self.colors['hover_orange']};
                color: {self.colors['hover_orange']};
            }}

            #closeButton {{
                background-color: transparent;
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                font-weight: bold;
                border-radius: 3px;
            }}

            #closeButton:hover {{
                background-color: {self.colors['error_red']};
                border: 1px solid {self.colors['error_red']};
            }}

            #mainSplitter {{
                background-color: {self.colors['deep_graphite']};
                border-radius: 10px;
            }}

            QMainWindow[maximized="true"] #mainSplitter {{
                border-radius: 0px;
            }}

            #mainSplitter::handle {{
                background-color: transparent;
            }}

            #leftPanel {{
                background-color: {self.colors['steel_grey']};
                border-right: 1px solid {self.colors['dark_border']};
                border-bottom-left-radius: 10px;
                font-family: "{font_family}";
            }}

            QMainWindow[maximized="true"] #leftPanel {{
                border-bottom-left-radius: 0px;
            }}

            #navFrame {{
                background-color: {self.colors['steel_grey']};
            }}

            #navButton_camera, #navButton_system, #navButton_model, 
            #navButton_process, #navButton_records {{
                background-color: transparent;
                border: none;
                text-align: left;
                padding: 10px 20px;
            }}

            #navButton_camera:hover, #navButton_system:hover, #navButton_model:hover, 
            #navButton_process:hover, #navButton_records:hover {{
                background-color: #2a2a2a;
            }}

            #navButton_camera[selected="true"], #navButton_system[selected="true"], 
            #navButton_model[selected="true"], #navButton_process[selected="true"], 
            #navButton_records[selected="true"] {{
                background-color: {self.colors['hover_orange']};
            }}

            #navIcon {{
                color: {self.colors['cool_grey']};
                font-size: 16px;
            }}

            #navButton_camera[selected="true"] #navIcon,
            #navButton_system[selected="true"] #navIcon,
            #navButton_model[selected="true"] #navIcon,
            #navButton_process[selected="true"] #navIcon,
            #navButton_records[selected="true"] #navIcon {{
                color: {self.colors['arctic_white']};
            }}

            #navName {{
                color: {self.colors['cool_grey']};
                font-size: 14px;
                font-weight: normal;
            }}

            #navButton_camera[selected="true"] #navName,
            #navButton_system[selected="true"] #navName,
            #navButton_model[selected="true"] #navName,
            #navButton_process[selected="true"] #navName,
            #navButton_records[selected="true"] #navName {{
                color: {self.colors['arctic_white']};
                font-weight: bold;
            }}

            #navDesc {{
                color: {self.colors['cool_grey']};
                font-size: 10px;
                text-transform: uppercase;
            }}

            #navButton_camera[selected="true"] #navDesc,
            #navButton_system[selected="true"] #navDesc,
            #navButton_model[selected="true"] #navDesc,
            #navButton_process[selected="true"] #navDesc,
            #navButton_records[selected="true"] #navDesc {{
                color: #ffdbb8;
            }}

            #statusFrame {{
                background-color: {self.colors['deep_graphite']};
                border-top: 1px solid {self.colors['dark_border']};
            }}

            #wifiIcon {{
                color: {self.colors['success_green']};
                font-size: 10px;
            }}

            #wifiLabel {{
                color: {self.colors['success_green']};
                font-size: 12px;
            }}

            #versionInfo {{
                color: {self.colors['cool_grey']};
                font-size: 12px;
            }}

            #syncLabel {{
                color: {self.colors['cool_grey']};
                font-size: 10px;
                margin-top: 5px;
            }}

            #rightPanel {{
                background-color: {self.colors['deep_graphite']};
                border-bottom-right-radius: 10px;
            }}

            QMainWindow[maximized="true"] #rightPanel {{
                border-bottom-right-radius: 0px;
            }}

            #contentStack {{
                background-color: {self.colors['deep_graphite']};
            }}

            #cameraPage, #systemPage, #modelPage, #processPage, #recordsPage {{
                background-color: {self.colors['deep_graphite']};
                font-family: "{font_family}";
            }}

            #pageLabel {{
                color: {self.colors['arctic_white']};
                font-size: 18px;
                font-weight: bold;
            }}

            #processHeader, #cameraHeader, #systemHeader, #modelHeader, #recordsHeader {{
                background-color: transparent;
            }}

            #cameraTitle, #systemTitle, #modelTitle, #processTitle, #recordsTitle {{
                color: {self.colors['arctic_white']};
                font-size: 24px;
                font-weight: bold;
            }}

            /* Camera Page Styles */
            #applyButton {{
                background-color: {self.colors['steel_grey']};
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }}

            #applyButton:hover {{
                background-color: {self.colors['hover_orange']};
                border: 1px solid {self.colors['hover_orange']};
            }}

            #previewToolbar {{
                background-color: {self.colors['steel_grey']};
                border: 1px solid {self.colors['dark_border']};
                border-radius: 8px;
                padding: 10px 14px;
            }}

            QToolButton#previewToolButton {{
                color: {self.colors['arctic_white']};
                border: 1px solid transparent;
                padding: 8px;
                border-radius: 6px;
            }}

            QToolButton#previewToolButton:hover {{
                border: 1px solid {self.colors['hover_orange']};
                color: {self.colors['hover_orange']};
            }}

            #previewFrame {{
                background-color: #000000;
                border: 2px solid {self.colors['dark_border']};
                border-radius: 6px;
            }}

            #previewLabel {{
                color: {self.colors['cool_grey']};
                font-size: 16px;
            }}

            #paramsFrame, #serverFrame, #imageFrame, #logFrame, #statusFrame {{
                background-color: {self.colors['steel_grey']};
                border: 1px solid {self.colors['dark_border']};
                border-radius: 8px;
            }}

            #paramsTitle, #sectionTitle {{
                color: {self.colors['arctic_white']};
                font-size: 18px;
                font-weight: bold;
                border-bottom: 1px solid {self.colors['dark_border']};
                padding-bottom: 10px;
            }}

            #paramLabel {{
                color: {self.colors['cool_grey']};
                font-size: 14px;
                min-width: 150px;
            }}

            #paramInput, #paramCombo {{
                background-color: {self.colors['deep_graphite']};
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                min-width: 120px;
            }}

            #paramInput:focus, #paramCombo:focus {{
                border: 1px solid {self.colors['hover_orange']};
            }}
            
            #paramValue {{
                color: {self.colors['arctic_white']};
                font-size: 14px;
            }}

            /* System Page Styles */
            #saveButton, #browseButton {{
                background-color: {self.colors['hover_orange']};
                border: none;
                color: {self.colors['arctic_white']};
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }}

            #saveButton:hover, #browseButton:hover {{
                background-color: #e07a28;
            }}

            /* Model Page Styles */
            #downloadButton, #uploadButton {{
                background-color: {self.colors['steel_grey']};
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }}

            #downloadButton:hover {{
                background-color: {self.colors['hover_orange']};
                border: 1px solid {self.colors['hover_orange']};
            }}

            #uploadButton:hover {{
                background-color: {self.colors['hover_orange']};
                border: 1px solid {self.colors['hover_orange']};
            }}

            #tableFrame {{
                background-color: {self.colors['steel_grey']};
                border: 1px solid {self.colors['dark_border']};
                border-radius: 8px;
            }}

            #headersFrame {{
                background-color: {self.colors['deep_graphite']};
                border-bottom: 1px solid {self.colors['dark_border']};
            }}

            #tableHeader {{
                color: {self.colors['cool_grey']};
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }}

            #rowFrame {{
                background-color: {self.colors['deep_graphite']};
                border-bottom: 1px solid {self.colors['dark_border']};
            }}

            #tableCell {{
                color: {self.colors['arctic_white']};
                font-size: 13px;
                min-width: 120px;
            }}

            #tableButton {{
                background-color: transparent;
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                border-radius: 4px;
                font-size: 12px;
                padding: 5px 10px;
                min-width: 60px;
            }}

            #tableButton:hover {{
                border: 1px solid {self.colors['hover_orange']};
                color: {self.colors['hover_orange']};
            }}

            #deleteButton {{
                background-color: transparent;
                border: 1px solid #E85454;
                color: #E85454;
                border-radius: 4px;
                font-size: 12px;
                padding: 5px 10px;
                min-width: 60px;
            }}

            #deleteButton:hover {{
                background-color: #E85454;
                color: {self.colors['arctic_white']};
            }}

            /* Process Page Styles */
            #syncButton, #createButton {{
                background-color: {self.colors['steel_grey']};
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }}

            #syncButton:hover, #createButton:hover {{
                background-color: {self.colors['hover_orange']};
                border: 1px solid {self.colors['hover_orange']};
            }}

            #cardFrame {{
                background-color: {self.colors['steel_grey']};
                border: 1px solid {self.colors['dark_border']};
                border-radius: 8px;
            }}

            #cardTitle {{
                color: {self.colors['arctic_white']};
                font-size: 16px;
                font-weight: bold;
            }}

            #cardType {{
                background-color: #1a1d23;
                color: #8C92A0;
                border: 1px solid #242831;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 12px;
            }}

            #cardStatus {{
                background-color: #3CC37A;
                color: #1a1d23;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 12px;
                font-weight: bold;
            }}

            #detailLabel, #modelsLabel {{
                color: {self.colors['cool_grey']};
                font-size: 13px;
            }}

            #modelTag {{
                background-color: {self.colors['deep_graphite']};
                color: {self.colors['arctic_white']};
                border: 1px solid {self.colors['dark_border']};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 12px;
                margin-right: 5px;
            }}

            #viewButton, #editButton {{
                background-color: transparent;
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                border-radius: 6px;
                font-size: 13px;
            }}

            #viewButton:hover, #editButton:hover {{
                border: 1px solid {self.colors['hover_orange']};
                color: {self.colors['hover_orange']};
            }}

            #startButton {{
                background-color: {self.colors['hover_orange']};
                border: none;
                color: {self.colors['arctic_white']};
                border-radius: 6px;
                font-size: 13px;
            }}

            #startButton:hover {{
                background-color: #e07a28;
            }}

            /* Records Page Styles */
            #dateButton, #exportButton {{
                background-color: {self.colors['steel_grey']};
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }}

            #dateButton:hover, #exportButton:hover {{
                background-color: {self.colors['hover_orange']};
                border: 1px solid {self.colors['hover_orange']};
            }}

            #statusLabel {{
                font-weight: bold;
                min-width: 80px;
            }}
        """)

    def setup_connections(self):
        """Setup signal connections."""
        self.min_button.clicked.connect(self.showMinimized)
        self.max_button.clicked.connect(self.toggle_maximize)
        self.close_button.clicked.connect(self.close)

    def load_preferences(self) -> None:
        """Placeholder for loading persisted UI preferences."""
        # Future implementation: restore splitter sizes, last open page, etc.
        pass
        
    def toggle_maximize(self):
        """Toggle window maximize state."""
        if self.isMaximized():
            self.showNormal()
            self.max_button.setText("□")
            self.setProperty("maximized", False)
        else:
            self.showMaximized()
            self.max_button.setText("❐")
            self.setProperty("maximized", True)
        
        # 更新样式以反映最大化状态
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def update_user_info(self):
        """Update user information display."""
        # Placeholder for user info update
        pass

    def check_session_status(self):
        """Check and update session status."""
        # Placeholder for session status check
        pass

    def handle_session_expiry(self):
        """Handle session expiration."""
        logger.warning("Session expired, redirecting to login")
        self.navigate_to_login()

    def navigate_to_login(self):
        """Navigate back to login window."""
        try:
            # Hide main window
            self.hide()

            # Show login window
            from .login_window import LoginWindow
            self.login_window = LoginWindow(self.session_manager)
            self.login_window.show()

        except Exception as e:
            logger.error(f"Failed to navigate to login: {e}")
            QMessageBox.critical(self, "Navigation Error", "Failed to return to login screen")

    def closeEvent(self, event):
        """Handle window close event with proper cleanup and confirmation."""
        try:
            # Stop session monitoring timer
            if hasattr(self, 'session_timer'):
                self.session_timer.stop()
            
            # Perform any necessary cleanup
            logger.info("Shutting down main window")
            
            # Accept the close event
            super().closeEvent(event)
            
        except Exception as e:
            logger.error(f"Error during window close: {e}")
            # Still allow window to close even if cleanup fails
            super().closeEvent(event)

    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)
        # 如果需要在窗口大小变化时执行特定操作，可以在这里添加代码
