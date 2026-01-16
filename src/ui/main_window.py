"""
Main application window for industrial vision system.

Provides the primary interface after successful login with
session management, user information, and application functionality.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

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
    QApplication,
    QMessageBox,
    QToolButton,
)
from PySide6.QtCore import Qt, QPoint, Signal, QSize, QFileSystemWatcher, QEvent, QTimer
from PySide6.QtGui import QFontDatabase, QFont

from .styles import (
    ThemeLoader,
    build_theme_variables,
    load_user_theme_preference,
    resolve_theme_colors,
)

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
    # Signal for cross-thread health state updates
    health_update_signal = Signal(bool, str)

    def __init__(self, session_manager: SessionManager, app=None, config: Optional[AppConfig] = None):
        """Initialize the main window."""
        super().__init__()
        self.session_manager = session_manager
        self.app = app  # Store app reference for shared services
        self.camera_service = getattr(app, "camera_service", None)
        self.config: AppConfig = config or get_config()
        self.app_display_name = "ProcVision"
        self.colors = self.config.ui.colors
        self.current_theme = load_user_theme_preference()
        self.theme_loader = ThemeLoader(theme_name=self.current_theme)
        self.stylesheet_path = self.theme_loader.stylesheet_path("main_window")
        self.stylesheet_watcher: Optional[QFileSystemWatcher] = None
        self.custom_font_family = "Arial"
        self.custom_font = QFont(self.custom_font_family)
        self._load_custom_font()
        self._time_labels = []
        self.time_label: Optional[QLabel] = None
        self.user_info_label: Optional[QLabel] = None
        self._time_timer: Optional[QTimer] = None
        
        self.init_ui()
        self.setProperty("maximized", "true" if self.isMaximized() else "false")
        self.setup_style()
        self.setup_connections()
        self.load_preferences()

        # Center window on screen
        self.center_window()

        # Set default page
        self.show_home_page()

        # Default to maximized window after login
        self.showMaximized()
        self.setProperty("maximized", "true")

        try:
            self.health_update_signal.connect(self._apply_health_update)
            self.session_manager.start_health_monitor(30, lambda online, ts: self.health_update_signal.emit(online, ts or ""))
        except Exception:
            logger.exception("Failed to start health monitor")

    def _load_custom_font(self):
        """Load Source Han Sans font for the main window and its widgets."""
        font_path = Path(__file__).resolve().parent.parent / "assets" / "SourceHanSansSC-Normal-2.otf"
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
        logger.info("Custom font applied to main window: %s", font_family)

    def _register_time_label(self, label: QLabel) -> None:
        """Track time labels so they can be updated together."""
        if label and label not in self._time_labels:
            self._time_labels.append(label)

    def _start_time_timer(self) -> None:
        """Start timer to refresh time display."""
        if hasattr(self, "_time_timer") and self._time_timer:
            return
        self._time_timer = QTimer(self)
        self._time_timer.setInterval(1000)
        self._time_timer.timeout.connect(self._update_time_display)
        self._time_timer.start()
        self._update_time_display()

    def _update_time_display(self) -> None:
        """Update all registered time labels with the current time."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for label in self._time_labels:
            label.setText(current_time)

    def on_theme_changed(self, theme: str) -> None:
        """Handle theme switch requests from settings."""
        self.set_theme(theme)

    def set_theme(self, theme: str) -> None:
        """Update the UI theme and reapply styles."""
        if theme not in {"dark", "light"}:
            logger.warning("Unsupported theme requested: %s", theme)
            return
        if theme == getattr(self, "current_theme", "dark"):
            return
        self.current_theme = theme
        self.theme_loader.set_theme(theme)
        try:
            self.stylesheet_path = self.theme_loader.stylesheet_path("main_window")
        except FileNotFoundError:
            logger.error("Theme '%s' is missing the main_window.qss file", theme)
            return
        if self.stylesheet_watcher:
            self.stylesheet_watcher.deleteLater()
            self.stylesheet_watcher = None
        self.reload_stylesheet()
        try:
            self.camera_page.apply_theme(theme)
        except Exception:
            logger.exception("Failed to apply theme on camera page")
        try:
            self.records_page.apply_theme(theme)
        except Exception:
            logger.exception("Failed to apply theme on records page")

    def init_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle(f"{self.app_display_name} v{self.config.app_version}")
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
        
        # Header with app info/user info/time
        header_bar = self.create_header_bar()
        main_layout.addWidget(header_bar)

        # Central stacked content area
        content_area = self.create_content_area()
        main_layout.addWidget(content_area, 1)

        # Bottom status bar
        self.status_bar = self.create_status_bar()
        main_layout.addWidget(self.status_bar)
        self._start_time_timer()

    def create_header_bar(self):
        """Create the top header with menu context, user info, and current time."""
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(64)

        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        # Left side - navigation menu (no ProcVision/version text)
        nav_container = self.create_navigation_bar()
        layout.addWidget(nav_container)
        layout.addStretch(1)

        # Right-aligned user info and time (simplified)
        username = "演示账号"
        if self.session_manager and self.session_manager.is_authenticated():
            name = None
            try:
                name = self.session_manager.get_username()
            except AttributeError:
                user = getattr(getattr(self.session_manager, "auth_state", None), "current_user", None)
                name = getattr(user, "username", None)
            if name:
                username = name

        self.user_info_label = QLabel(f"用户：{username}")
        self.user_info_label.setObjectName("userInfo")
        self.user_info_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.time_label = QLabel()
        self.time_label.setObjectName("timeInfo")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._register_time_label(self.time_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.addWidget(self.user_info_label)
        info_layout.addWidget(self.time_label)

        layout.addLayout(info_layout)

        # Enable window dragging
        title_bar.mousePressEvent = self.title_bar_mouse_press
        title_bar.mouseMoveEvent = self.title_bar_mouse_move
        title_bar.mouseReleaseEvent = self.title_bar_mouse_release

        return title_bar

    def create_navigation_bar(self) -> QWidget:
        """Create the horizontal navigation bar shown beneath the header."""
        nav_frame = QFrame()
        nav_frame.setObjectName("navBar")
        nav_frame.setFixedWidth(780)
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(20, 10, 20, 10)
        nav_layout.setSpacing(12)

        nav_items = [
            ("home", "主页"),
            ("system", "系统设置"),
            ("camera", "相机设置"),
            ("model", "算法管理"),
            ("process", "装配引导"),
            ("records", "工作记录"),
        ]

        self.nav_buttons = {}
        for item_id, label in nav_items:
            button = self.create_nav_button(item_id, label)
            nav_layout.addWidget(button)
            self.nav_buttons[item_id] = button

        self._debug_nav_button_state("init_top_nav")
        return nav_frame

    def create_nav_button(self, item_id: str, label: str) -> QPushButton:
        """Create a simplified navigation button for the top menu."""
        button = QPushButton(label)
        button.setObjectName("navButton")
        button.setCheckable(True)
        button.setFixedHeight(44)
        button.setMinimumWidth(110)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        button.setChecked(False)
        button.setProperty("selected", "false")
        button.clicked.connect(lambda checked, id=item_id: self.switch_page(id))
        return button

    def create_content_area(self) -> QWidget:
        """Create the central stacked content area with all pages."""
        content_frame = QFrame()
        content_frame.setObjectName("contentArea")

        layout = QVBoxLayout(content_frame)
        layout.setContentsMargins(20, 10, 20, 20)
        layout.setSpacing(16)

        # Stacked widget for different pages
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentStack")

        # Create pages using dynamic loading
        self.camera_page = CameraPage(camera_service=self.camera_service, initial_theme=self.current_theme)
        self.system_page = SystemPage(initial_theme=self.current_theme)
        self.model_page = ModelPage()
        self.process_page = ProcessPage(camera_service=self.camera_service)
        self.records_page = RecordsPage(initial_theme=self.current_theme)
        try:
            self.system_page.themeChanged.connect(self.on_theme_changed)
        except Exception:
            logger.exception("Failed to connect theme change signal")

        self.page_indices: dict[str, int] = {}
        page_definitions = [
            ("home", self.create_home_page()),
            ("process", self.process_page),
            ("camera", self.camera_page),
            ("model", self.model_page),
            ("records", self.records_page),
            ("system", self.system_page),
        ]

        for page_id, widget in page_definitions:
            self.content_stack.addWidget(widget)
            self.page_indices[page_id] = self.content_stack.count() - 1

        # Default to the home quick-action page
        if "home" in self.page_indices:
            self.content_stack.setCurrentIndex(self.page_indices["home"])

        layout.addWidget(self.content_stack)
        return content_frame

    def create_home_page(self) -> QWidget:
        """Create the default home page with two primary square actions."""
        home_widget = QWidget()
        home_widget.setObjectName("homePage")

        layout = QHBoxLayout(home_widget)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(40)

        layout.addStretch(1)
        assembly_button = self.create_home_action_button("装配", self.show_process_page)
        layout.addWidget(assembly_button)

        layout.addStretch(1)
        photo_button = self.create_home_action_button("拍照", lambda: self.switch_page("camera"))
        layout.addWidget(photo_button)
        layout.addStretch(1)

        return home_widget

    def create_home_action_button(self, label: str, callback: Callable[[], None]) -> QPushButton:
        """Create a square action button for the home page."""
        button = QPushButton(label)
        button.setObjectName("homeActionButton")
        button.setFixedSize(440, 440)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setProperty("homeAction", "true")
        button.clicked.connect(callback)
        return button

    def create_status_bar(self) -> QWidget:
        """Create the bottom status bar to show server connectivity info."""
        status_frame = QFrame()
        status_frame.setObjectName("statusBar")

        layout = QHBoxLayout(status_frame)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(16)

        self.connection_indicator = QLabel("●")
        self.connection_indicator.setObjectName("connectionIndicator")
        self.connection_indicator.setProperty("connectionState", "online")

        self.connection_label = QLabel("服务器已连接")
        self.connection_label.setObjectName("connectionLabel")

        version_info = QLabel(f"版本 {self.config.app_version}")
        version_info.setObjectName("versionInfo")

        self.sync_label = QLabel("最后同步：--:--:--")
        self.sync_label.setObjectName("syncLabel")

        layout.addWidget(self.connection_indicator)
        layout.addWidget(self.connection_label)
        layout.addSpacing(12)
        layout.addWidget(self.sync_label)
        layout.addStretch(1)
        layout.addWidget(version_info)

        return status_frame

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
        """Create assembly guidance and inspection page."""
        # This method is no longer needed as we're using dynamic page loading
        pass

    def create_records_page(self):
        """Create work records page."""
        # This method is no longer needed as we're using dynamic page loading
        pass

    def show_home_page(self):
        """Show the default home quick-action page."""
        if getattr(self, "content_stack", None):
            self.switch_page("home")

    def show_process_page(self):
        """Show the assembly guidance and inspection page."""
        if getattr(self, "content_stack", None):
            self.switch_page("process")

    def switch_page(self, page_id: str):
        """Switch to the specified page."""
        if getattr(self, "nav_buttons", None):
            for btn_id, button in self.nav_buttons.items():
                selected = btn_id == page_id
                button.setChecked(selected)
                button.setProperty("selected", "true" if selected else "false")
                button.style().unpolish(button)
                button.style().polish(button)

        fallback_index = 0
        if hasattr(self, "page_indices") and "home" in self.page_indices:
            fallback_index = self.page_indices["home"]

        page_index = self.page_indices.get(page_id, fallback_index) if hasattr(self, "page_indices") else fallback_index
        if hasattr(self, "content_stack"):
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
            stylesheet = self.theme_loader.load(
                "main_window",
                variables=self._build_stylesheet_variables(),
            )
        except FileNotFoundError:
            logger.error("Stylesheet file not found: %s", self.stylesheet_path)
            return
        self.setStyleSheet(stylesheet)

    def reload_stylesheet(self):
        """Public helper to reload styles, useful during development."""
        self.apply_stylesheet()
        if self.stylesheet_watcher and self.stylesheet_path.exists():
            watched_files = set(self.stylesheet_watcher.files())
            if str(self.stylesheet_path) not in watched_files:
                self.stylesheet_watcher.addPath(str(self.stylesheet_path))
        else:
            self._register_stylesheet_watcher()

    def _build_stylesheet_variables(self) -> dict[str, str]:
        """Prepare placeholder replacements for theme files."""
        font_family = getattr(self, "custom_font_family", "Arial") or "Arial"
        theme_colors = resolve_theme_colors(getattr(self, "current_theme", "dark"), self.colors)
        return build_theme_variables(theme_colors, font_family)

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
        # Future implementation: restore last open page, theme, etc.
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
        if self.session_manager and self.session_manager.is_authenticated() and self.user_info_label:
            name = None
            try:
                name = self.session_manager.get_username()
            except AttributeError:
                user = getattr(getattr(self.session_manager, "auth_state", None), "current_user", None)
                name = getattr(user, "username", None)
            if name:
                self.user_info_label.setText(f"用户：{name}")

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
            self.login_window = LoginWindow(self.session_manager, app_context=self.app)
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
            try:
                self.session_manager.stop_health_monitor()
            except Exception:
                pass
            
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

    def _apply_health_update(self, online: bool, ts_str: str):
        """Slot to apply health updates on the UI thread."""
        state = "online" if online else "offline"
        if hasattr(self, "connection_indicator") and self.connection_indicator:
            self.connection_indicator.setProperty("connectionState", state)
            self.connection_indicator.style().unpolish(self.connection_indicator)
            self.connection_indicator.style().polish(self.connection_indicator)
        if hasattr(self, "connection_label") and self.connection_label:
            self.connection_label.setText("服务器已连接" if online else "服务器未连接")
        if hasattr(self, "sync_label") and self.sync_label:
            self.sync_label.setText(f"最后同步：{ts_str or '--:--:--'}")
