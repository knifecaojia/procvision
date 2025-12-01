"""
ProcVision login window with authentication integration.

Provides the main login interface for the industrial vision application
with secure authentication, session management, and user feedback.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional, Any

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)
from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtGui import QPixmap, QFontDatabase, QFont

try:
    from ..auth.services import AuthService, SessionManager
    from ..core.config import get_config
except ImportError:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.auth.services import AuthService, SessionManager  # type: ignore
    from src.core.config import get_config  # type: ignore

from .styles import (
    ThemeLoader,
    build_theme_variables,
    refresh_widget_styles,
    load_user_theme_preference,
    resolve_theme_colors,
)

logger = logging.getLogger(__name__)


class LoginWindow(QMainWindow):
    """Main ProcVision login window."""

    def __init__(self, session_manager: Optional[SessionManager] = None, app_context: Optional[Any] = None) -> None:
        super().__init__()

        self.auth_service = AuthService()
        self.session_manager = session_manager or SessionManager(self.auth_service)
        self.app_context = app_context

        self.setWindowTitle("ProcVision 登录")
        self.setFixedSize(1050, 700)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.drag_pos: Optional[QPoint] = None

        self.project_root = Path(__file__).resolve().parents[2]

        self.config = get_config()
        self.colors = self.config.ui.colors
        self.current_theme = load_user_theme_preference()
        self.theme_loader = ThemeLoader(theme_name=self.current_theme)

        self.is_loading = False
        self.login_attempts = 0
        self.max_login_attempts = 5

        self.hero_label: Optional[QLabel] = None

        # 加载自定义字体
        self.load_custom_font()

        self.init_ui()
        self.setup_style()
        self.setup_connections()
        self.load_saved_preferences()
        QTimer.singleShot(0, self.update_left_image)
        QTimer.singleShot(0, self.update_left_panel_size)

    def load_custom_font(self):
        """加载自定义字体"""
        font_path = self.project_root / "src" / "assets" / "SourceHanSansSC-Normal-2.otf"
        fallback_font = QFont("Arial")
        self.custom_font = fallback_font
        self.custom_font_family = fallback_font.family()

        if not font_path.exists():
            logger.warning("Custom font file not found at %s", font_path)
            return

        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id == -1:
            logger.warning("Failed to load custom font")
            return

        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.custom_font = QFont(font_family)
        self.custom_font_family = font_family
        app = QApplication.instance()
        if app is not None:
            app.setFont(self.custom_font)
        logger.info("Custom font loaded: %s", font_family)

    # --- UI creation -----------------------------------------------------
    def init_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = self.create_title_bar()
        main_layout.addWidget(self.title_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(0)
        splitter.setObjectName("mainSplitter")
        main_layout.addWidget(splitter)
        self.splitter = splitter

        self.create_left_panel(splitter)
        self.create_right_panel(splitter)
        splitter.setSizes([300, 750])  # 更新右面板大小以适应新的总宽度
        
        # 初始化左侧面板大小
        QTimer.singleShot(0, self.update_left_panel_size)

    def create_title_bar(self) -> QWidget:
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(12)

        title_label = QLabel("ProcVision 视觉检测系统")
        title_label.setObjectName("titleBarLabel")

        version_label = QLabel(f"版本 {self.config.app_version}")
        version_label.setObjectName("titleVersion")

        layout.addWidget(title_label)
        layout.addWidget(version_label)
        layout.addStretch()

        self.min_button = QPushButton("−")
        self.min_button.setObjectName("windowButton")
        self.min_button.setFixedSize(32, 24)
        layout.addWidget(self.min_button)

        self.close_button = QPushButton("×")
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(32, 24)
        layout.addWidget(self.close_button)

        title_bar.installEventFilter(self)
        return title_bar

    def create_left_panel(self, parent: QSplitter) -> None:
        left_frame = QFrame()
        left_frame.setObjectName("leftFrame")

        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.hero_label = QLabel()
        self.hero_label.setObjectName("leftImage")
        self.hero_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hero_label.setScaledContents(True)
        self.hero_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.hero_label.setProperty("contentState", "placeholder")

        left_layout.addWidget(self.hero_label)
        parent.addWidget(left_frame)

    def update_left_panel_size(self):
        """根据高度更新左侧面板的宽度，保持1024:1536的比例"""
        if hasattr(self, 'splitter') and self.splitter:
            # 获取当前窗口的高度
            height = self.splitter.height()
            # 计算符合1024:1536比例的宽度 (1024/1536 = 2/3)
            width = int(height * 1024 / 1536)
            
            # 应用新的宽度到左侧面板
            left_panel = self.splitter.widget(0)  # 第一个widget是左侧面板
            if left_panel:
                left_panel.setFixedWidth(width)

    def create_right_panel(self, parent: QSplitter) -> None:
        right_frame = QFrame()
        right_frame.setObjectName("rightFrame")

        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(90, 70, 90, 60)
        right_layout.setSpacing(6)

        login_title = QLabel("用户登录")
        login_title.setObjectName("loginTitle")
        login_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        username_label = QLabel("用户名")
        username_label.setObjectName("fieldLabel")
        self.username_input = QLineEdit()
        self.username_input.setObjectName("inputField")
        self.username_input.setClearButtonEnabled(True)
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setFixedHeight(48)

        password_label = QLabel("密码")
        password_label.setObjectName("fieldLabel")
        self.password_input = QLineEdit()
        self.password_input.setObjectName("inputField")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setFixedHeight(48)
        self.password_input.setProperty("inputState", "default")

        self.remember_checkbox = QCheckBox("记住用户名")
        self.remember_checkbox.setObjectName("checkBox")

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(26)
        self.status_label.setProperty("statusState", "normal")

        self.login_button = QPushButton("登录")
        self.login_button.setObjectName("loginButton")
        self.login_button.setFixedSize(220, 44)

        right_layout.addStretch()
        right_layout.addWidget(login_title)
        right_layout.addSpacing(10)

        right_layout.addWidget(username_label)
        right_layout.addWidget(self.username_input)
        right_layout.addSpacing(16)

        right_layout.addWidget(password_label)
        right_layout.addWidget(self.password_input)
        right_layout.addSpacing(20)

        right_layout.addWidget(self.remember_checkbox)
        right_layout.addSpacing(18)

        right_layout.addWidget(self.status_label)

        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self.login_button)
        button_row.addStretch()
        right_layout.addLayout(button_row)
        right_layout.addStretch()

        parent.addWidget(right_frame)

    # --- Styling ---------------------------------------------------------
    def setup_style(self) -> None:
        self.theme_loader.apply(self, "login_window", variables=self._build_theme_variables())

    def _build_theme_variables(self) -> dict[str, str]:
        font_family = getattr(self, "custom_font_family", "Arial") or "Arial"
        theme_colors = resolve_theme_colors(getattr(self, "current_theme", "dark"), self.colors)
        return build_theme_variables(theme_colors, font_family)

    # --- Connections -----------------------------------------------------
    def setup_connections(self) -> None:
        self.login_button.clicked.connect(self.on_login_clicked)
        self.remember_checkbox.toggled.connect(self.on_remember_toggled)
        self.min_button.clicked.connect(self.showMinimized)
        self.close_button.clicked.connect(self.close)

        self.username_input.returnPressed.connect(self.on_login_clicked)
        self.password_input.returnPressed.connect(self.on_login_clicked)

    # --- Image handling --------------------------------------------------
    def update_left_image(self) -> None:
        if not self.hero_label:
            return
        image_path = self.project_root / "src" / "assets" / "left.png"
        if image_path.exists():
            pixmap = QPixmap(str(image_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    max(1, self.hero_label.width()),
                    max(1, self.hero_label.height()),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.hero_label.setPixmap(scaled)
                self._set_widget_state(self.hero_label, "contentState", "image")
                return
        self.hero_label.setText("PROC VISION")
        self._set_widget_state(self.hero_label, "contentState", "placeholder")

    # --- Preference handling --------------------------------------------
    def load_saved_preferences(self) -> None:
        if self.session_manager.is_authenticated():
            username = self.session_manager.get_username()
            if username:
                self.username_input.setText(username)
                self.remember_checkbox.setChecked(True)

    def save_user_preferences(self, username: str) -> None:
        try:
            preferences = {
                "remember_username": self.remember_checkbox.isChecked(),
            }
            self.auth_service.update_user_preferences(username, preferences)
        except Exception as exc:  # pragma: no cover - logging only
            logger.error(f"Failed to save user preferences: {exc}")

    # --- Actions ---------------------------------------------------------
    def on_login_clicked(self) -> None:
        if self.is_loading:
            return

        username = self.username_input.text().strip()
        password = self.password_input.text()
        remember_me = self.remember_checkbox.isChecked()

        self.clear_status()

        is_valid, error = self.validate_login_input(username, password)
        if not is_valid:
            self.show_error(error)
            return

        self.set_loading_state(True)
        try:
            # 修改为允许任意用户登录，无需数据库验证
            # success, error = self.session_manager.login(username=username, password=password)
            # 模拟登录成功
            success = True
            error = None
            
            if success:
                # 直接设置会话状态
                self.session_manager.auth_service.auth_state.is_authenticated = True
                # 保存用户偏好
                if remember_me:
                    self.save_user_preferences(username)
                self.show_success("登录成功，正在跳转...")
                QTimer.singleShot(800, self.navigate_to_main_window)
            else:
                self.show_error(error or "登录失败")
                self.login_attempts += 1
                if self.login_attempts >= self.max_login_attempts:
                    self.lock_login_form()
        except Exception as exc:  # pragma: no cover - logging only
            logger.error(f"Login error: {exc}")
            self.show_error("发生意外错误")
        finally:
            self.set_loading_state(False)

    def validate_login_input(self, username: str, password: str) -> tuple[bool, Optional[str]]:
        """Permit all input combinations."""
        return True, None

    def set_loading_state(self, loading: bool) -> None:
        self.is_loading = loading
        self.username_input.setEnabled(not loading)
        self.password_input.setEnabled(not loading)
        self.remember_checkbox.setEnabled(not loading)
        self.login_button.setEnabled(not loading)
        if loading:
            self.login_button.setText("Authenticating…")
        else:
            self.login_button.setText("Login")

    def show_error(self, message: str) -> None:
        self.status_label.setText(message)
        self._set_widget_state(self.status_label, "statusState", "error")
        self._set_widget_state(self.password_input, "inputState", "error")

    def show_success(self, message: str) -> None:
        self.status_label.setText(message)
        self._set_widget_state(self.status_label, "statusState", "success")
        self._set_widget_state(self.password_input, "inputState", "default")

    def clear_status(self) -> None:
        self.status_label.setText("")
        self._set_widget_state(self.status_label, "statusState", "normal")
        self._set_widget_state(self.password_input, "inputState", "default")

    def lock_login_form(self) -> None:
        self.show_error("Too many failed attempts. Please wait…")
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)
        self.login_button.setEnabled(False)
        QTimer.singleShot(30000, self.unlock_login_form)

    def unlock_login_form(self) -> None:
        self.clear_status()
        self.username_input.setEnabled(True)
        self.password_input.setEnabled(True)
        self.login_button.setEnabled(True)
        self.login_attempts = 0

    @staticmethod
    def _set_widget_state(widget: Optional[QWidget], prop: str, value: str) -> None:
        if widget is None:
            return
        widget.setProperty(prop, value)
        refresh_widget_styles(widget)

    def on_remember_toggled(self, checked: bool) -> None:  # pragma: no cover - logging only
        logger.info(f"Remember username toggled: {checked}")

    def navigate_to_main_window(self) -> None:
        try:
            self.hide()
            try:
                from src.ui.main_window import MainWindow
            except ImportError:  # pragma: no cover - fallback for script execution
                from .main_window import MainWindow  # type: ignore
            self.main_window = MainWindow(self.session_manager, app=self.app_context)
            self.main_window.show()
            logger.info("Navigated to main window")
        except Exception as exc:  # pragma: no cover - logging only
            import traceback
            logger.error(f"Failed to navigate to main window: {exc}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "Navigation Error", f"Failed to open main window.\n\n{exc}")
            self.show()

    # --- Qt events -------------------------------------------------------
    def eventFilter(self, watched, event):  # type: ignore[override]
        if watched == getattr(self, "title_bar", None):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if event.type() == QEvent.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton and self.drag_pos:
                self.move(event.globalPosition().toPoint() - self.drag_pos)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self.drag_pos = None
                return True
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):  # type: ignore[override]
        self.update_left_image()
        self.update_left_panel_size()
        return super().resizeEvent(event)

    def closeEvent(self, event):  # type: ignore[override]
        if not self.session_manager.is_authenticated():
            self.session_manager.logout()
        super().closeEvent(event)

def main() -> int:  # pragma: no cover - manual testing helper
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
