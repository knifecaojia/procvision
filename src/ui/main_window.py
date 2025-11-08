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
)
from PySide6.QtCore import Qt, QPoint, Signal, QSize
from PySide6.QtGui import QFontDatabase, QFont

try:
    from ..core.session import SessionManager
    from ..core.config import AppConfig, get_config
    # Import page classes
    from .pages.camera_page import CameraPage
    from .pages.system_page import SystemPage
    from .pages.model_page import ModelPage
    from .pages.process_page import ProcessPage
    from .pages.records_page import RecordsPage
except ImportError:
    # Handle when running as script
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.core.session import SessionManager  # type: ignore
    from src.core.config import AppConfig, get_config  # type: ignore
    # Import page classes
    from src.ui.pages.camera_page import CameraPage
    from src.ui.pages.system_page import SystemPage
    from src.ui.pages.model_page import ModelPage
    from src.ui.pages.process_page import ProcessPage
    from src.ui.pages.records_page import RecordsPage

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

        # Center window on screen
        self.center_window()

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

        # Create pages using dynamic loading
        self.camera_page = CameraPage()
        self.system_page = SystemPage()
        self.model_page = ModelPage()
        self.process_page = ProcessPage()  # 默认页面
        self.records_page = RecordsPage()

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
        # This method is no longer needed as we're using dynamic page loading
        pass

    def create_system_page(self):
        """Create system settings page."""
        # This method is no longer needed as we're using dynamic page loading
        pass

    def create_model_page(self):
        """Create model management page."""
        # This method is no longer needed as we're using dynamic page loading
        pass

    def create_process_page(self):
        """Create process information page."""
        # This method is no longer needed as we're using dynamic page loading
        pass

    def create_records_page(self):
        """Create work records page."""
        # This method is no longer needed as we're using dynamic page loading
        pass

    def show_process_page(self):
        """Show the process page by default during startup."""
        if getattr(self, "content_stack", None):
            self.switch_page("process")

    def switch_page(self, page_id: str):
        """Switch to the specified page."""
        # Reset all buttons
        for btn_id, button in self.nav_buttons.items():
            button.setProperty("selected", btn_id == page_id)
            button.style().unpolish(button)
            button.style().polish(button)
        
        # Switch to the appropriate page
        page_map = {
            "camera": 0,
            "system": 1,
            "model": 2,
            "process": 3,
            "records": 4
        }
        
        page_index = page_map.get(page_id, 3)  # Default to process page
        self.content_stack.setCurrentIndex(page_index)

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
                padding-bottom: 5px;
            }}

            #paramLabel {{
                color: {self.colors['cool_grey']};
                font-size: 13px;
                min-width: 100px;
                padding-right: 5px;
            }}

            #paramInput, #paramCombo {{
                background-color: {self.colors['deep_graphite']};
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                border-radius: 6px;
                padding: 6px;
                font-size: 13px;
                min-width: 100px;
            }}

            #paramInput:focus, #paramCombo:focus {{
                border: 1px solid {self.colors['hover_orange']};
            }}
            
            #paramValue {{
                color: {self.colors['arctic_white']};
                font-size: 13px;
                font-weight: normal;
                min-width: 60px;
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

            /* Model Card Styles */
            #modelCard {{
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                font-family: "{font_family}";
            }}

            #modelCard:hover {{
                border: 1px solid rgba(255, 165, 0, 0.5);
            }}

            #iconFrame {{
                background-color: #1a1a1a;
                border-radius: 20px;
            }}

            #iconFrame.opencv {{
                background-color: rgba(59, 130, 246, 0.1);
            }}

            #iconFrame.yolo {{
                background-color: rgba(168, 85, 247, 0.1);
            }}

            #iconLabel {{
                color: #ffffff;
                font-size: 18px;
            }}

            #iconFrame.opencv #iconLabel {{
                color: #60a5fa;
            }}

            #iconFrame.yolo #iconLabel {{
                color: #c084fc;
            }}

            #cardTitle {{
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
            }}

            #cardVersion {{
                color: #6b7280;
                font-size: 12px;
            }}

            #statusBadge {{
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
            }}

            #statusBadge.active {{
                background-color: rgba(34, 197, 94, 0.1);
                color: #4ade80;
                border: 1px solid rgba(34, 197, 94, 0.3);
            }}

            #statusBadge.inactive {{
                background-color: rgba(107, 114, 128, 0.1);
                color: #9ca3af;
                border: 1px solid rgba(107, 114, 128, 0.3);
            }}

            #descLabel {{
                color: #9ca3af;
                font-size: 14px;
            }}

            #infoFrame {{
                background-color: #1a1a1a;
                border-radius: 4px;
            }}

            #infoLabel {{
                color: #6b7280;
                font-size: 12px;
            }}

            #infoValue {{
                color: #ffffff;
                font-size: 14px;
            }}

            #viewButton {{
                background-color: transparent;
                border: 1px solid #3a3a3a;
                color: #9ca3af;
                border-radius: 6px;
                font-size: 13px;
            }}

            #viewButton:hover {{
                background-color: #2a2a2a;
                color: #ffffff;
            }}

            #updateButton {{
                background-color: #f97316;
                border: 1px solid #f97316;
                color: #ffffff;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }}

            #updateButton:hover {{
                background-color: #ea580c;
                border: 1px solid #ea580c;
            }}

            #deleteButton {{
                background-color: transparent;
                border: 1px solid rgba(239, 68, 68, 0.5);
                color: #f87171;
                border-radius: 6px;
                font-size: 13px;
            }}

            #deleteButton:hover {{
                background-color: rgba(239, 68, 68, 0.1);
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

    def center_window(self):
        """Center the window on the screen."""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())
        
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
