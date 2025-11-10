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
from PySide6.QtCore import Qt, QPoint, Signal, QSize, QFileSystemWatcher, QEvent
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
        self.stylesheet_path = Path(__file__).resolve().parent / "styles" / "main_window.qss"
        self.stylesheet_watcher: Optional[QFileSystemWatcher] = None
        
        # Load custom font
        font_path = os.path.join(os.path.dirname(__file__), "..", "assets", "SourceHanSansSC-Normal-2.otf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            self.custom_font = QFont(font_family)
        else:
            self.custom_font = QFont()
        
        self.init_ui()
        self.setProperty("maximized", "true" if self.isMaximized() else "false")
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

        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(user_info)
        center_layout.addStretch()

        layout.addLayout(left_layout)
        layout.addLayout(center_layout)

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
        """Create custom title bar with user info."""
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

        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(user_info)
        center_layout.addStretch()

        layout.addLayout(left_layout)
        layout.addLayout(center_layout)

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
        self._debug_nav_button_state("init_left_panel")
        parent.addWidget(left_frame)

    def create_nav_button(self, item_id, cn_name, en_name):
        """Create a navigation button."""
        button = QPushButton()
        button.setObjectName(f"navButton_{item_id}")
        button.setFixedHeight(60)
        
        # Set default selected button to "process"
        is_default = item_id == "process"
        initial_state = "true" if is_default else "false"
        button.setProperty("selected", initial_state)
        
        # Create layout for button content
        layout = QHBoxLayout(button)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(15)
        
        # Icon placeholder (in a real app, you would use actual icons)
        icon_label = QLabel("■")  # Placeholder icon
        icon_label.setObjectName("navIcon")
        icon_label.setProperty("selected", initial_state)
        
        # Text layout
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        name_label = QLabel(cn_name)
        name_label.setObjectName("navName")
        name_label.setProperty("selected", initial_state)
        
        desc_label = QLabel(en_name)
        desc_label.setObjectName("navDesc")
        desc_label.setProperty("selected", initial_state)
        
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
            selection_state = "true" if btn_id == page_id else "false"
            button.setProperty("selected", selection_state)
            button.style().unpolish(button)
            button.style().polish(button)

            for child_name in ("navIcon", "navName", "navDesc"):
                label = button.findChild(QLabel, child_name)
                if label is not None:
                    label.setProperty("selected", selection_state)
                    label.style().unpolish(label)
                    label.style().polish(label)
        
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
        self._debug_nav_button_state(f"switch_to_{page_id}")

    def _debug_nav_button_state(self, context: str):
        """Log current navigation button selection state for diagnostics."""
        if not getattr(self, "nav_buttons", None):
            return

        state_snapshot = {
            btn_id: button.property("selected")
            for btn_id, button in self.nav_buttons.items()
        }
        logger.info("Nav button state [%s]: %s", context, state_snapshot)

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
        """Apply styles to the main window from an external QSS file."""
        self.apply_stylesheet()
        self._register_stylesheet_watcher()

    def apply_stylesheet(self):
        """Load stylesheet template and apply runtime variables."""
        try:
            template = self.stylesheet_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.error("Stylesheet file not found: %s", self.stylesheet_path)
            return

        stylesheet = self._inject_stylesheet_variables(template)
        self.setStyleSheet(stylesheet)

    def reload_stylesheet(self):
        """Public helper to reload styles, useful during development."""
        self.apply_stylesheet()
        if self.stylesheet_watcher and self.stylesheet_path.exists():
            watched_files = set(self.stylesheet_watcher.files())
            if str(self.stylesheet_path) not in watched_files:
                self.stylesheet_watcher.addPath(str(self.stylesheet_path))

    def _inject_stylesheet_variables(self, template: str) -> str:
        """Replace placeholder tokens with values from config and fonts."""
        replacements = {f"@{name}": value for name, value in self.colors.items()}
        font_family = self.custom_font.family() or "Arial"
        replacements["@font_family"] = font_family

        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)
        return template

    def _register_stylesheet_watcher(self):
        """Watch the stylesheet for changes to enable live reload."""
        if self.stylesheet_watcher or not self.stylesheet_path.exists():
            return

        self.stylesheet_watcher = QFileSystemWatcher([str(self.stylesheet_path)])
        self.stylesheet_watcher.fileChanged.connect(self.reload_stylesheet)

    def setup_connections(self):
        """Setup signal connections."""
        pass

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

    def changeEvent(self, event):
        """Track window state changes to update style-sheet bindings."""
        if event.type() == QEvent.Type.WindowStateChange:
            self.setProperty("maximized", "true" if self.isMaximized() else "false")
            self.style().unpolish(self)
            self.style().polish(self)
        super().changeEvent(event)
