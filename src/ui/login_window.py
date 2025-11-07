"""
ProcVision login window with authentication integration.

Provides the main login interface for the industrial vision application
with secure authentication, session management, and user feedback.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
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
from PySide6.QtGui import QPixmap

try:
    from ..auth.services import AuthService, SessionManager
    from ..core.config import get_config
except ImportError:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.auth.services import AuthService, SessionManager  # type: ignore
    from src.core.config import get_config  # type: ignore


logger = logging.getLogger(__name__)


class LoginWindow(QMainWindow):
    """Main ProcVision login window."""

    def __init__(self, session_manager: Optional[SessionManager] = None) -> None:
        super().__init__()

        self.auth_service = AuthService()
        self.session_manager = session_manager or SessionManager(self.auth_service)

        self.setWindowTitle("ProcVision Login")
        self.setFixedSize(1200, 700)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.drag_pos: Optional[QPoint] = None

        self.project_root = Path(__file__).resolve().parents[2]

        self.config = get_config()
        self.colors = self.config.ui.colors

        self.is_loading = False
        self.login_attempts = 0
        self.max_login_attempts = 5

        self.hero_label: Optional[QLabel] = None

        self.init_ui()
        self.setup_style()
        self.setup_connections()
        self.load_saved_preferences()
        QTimer.singleShot(0, self.update_left_image)

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
        splitter.setSizes([540, 660])

    def create_title_bar(self) -> QWidget:
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(12)

        title_label = QLabel("ProcVision")
        title_label.setObjectName("titleBarLabel")

        version_label = QLabel(f"v{self.config.app_version}")
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

        left_layout.addWidget(self.hero_label)
        parent.addWidget(left_frame)

    def create_right_panel(self, parent: QSplitter) -> None:
        right_frame = QFrame()
        right_frame.setObjectName("rightFrame")

        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(90, 70, 90, 60)
        right_layout.setSpacing(28)

        brand_title = QLabel("ProcVision")
        brand_title.setObjectName("brandTitle")
        brand_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        login_title = QLabel("User Login")
        login_title.setObjectName("loginTitle")
        login_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        username_label = QLabel("Username")
        username_label.setObjectName("fieldLabel")
        self.username_input = QLineEdit()
        self.username_input.setObjectName("inputField")
        self.username_input.setClearButtonEnabled(True)
        self.username_input.setPlaceholderText("admin")
        self.username_input.setFixedHeight(48)

        password_label = QLabel("Password")
        password_label.setObjectName("fieldLabel")
        self.password_input = QLineEdit()
        self.password_input.setObjectName("inputField")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setFixedHeight(48)

        lang_label = QLabel("Language")
        lang_label.setObjectName("fieldLabel")
        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("comboBox")
        self.lang_combo.addItems(["中", "English"])
        self.lang_combo.setFixedHeight(48)

        self.remember_checkbox = QCheckBox("Remember username")
        self.remember_checkbox.setObjectName("checkBox")

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(26)

        self.login_button = QPushButton("Login")
        self.login_button.setObjectName("loginButton")
        self.login_button.setFixedSize(220, 44)

        right_layout.addStretch()
        right_layout.addWidget(brand_title)
        right_layout.addWidget(login_title)
        right_layout.addSpacing(10)

        right_layout.addWidget(username_label)
        right_layout.addWidget(self.username_input)
        right_layout.addSpacing(16)

        right_layout.addWidget(password_label)
        right_layout.addWidget(self.password_input)
        right_layout.addSpacing(16)

        right_layout.addWidget(lang_label)
        right_layout.addWidget(self.lang_combo)
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
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: {self.colors['deep_graphite']};
                border-radius: 10px;
            }}

            #centralWidget {{
                background-color: {self.colors['deep_graphite']};
                border-radius: 10px;
            }}

            #mainSplitter {{
                background-color: {self.colors['deep_graphite']};
            }}

            #mainSplitter::handle {{
                background-color: transparent;
            }}

            #titleBar {{
                background-color: {self.colors['steel_grey']};
                border-bottom: 1px solid {self.colors['dark_border']};
            }}

            #titleBarLabel {{
                color: {self.colors['arctic_white']};
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}

            #titleVersion {{
                color: {self.colors['cool_grey']};
                font-size: 12px;
                text-transform: uppercase;
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

            #leftFrame {{
                border-top-left-radius: 10px;
                border-bottom-left-radius: 10px;
                border-right: none;
            }}

            #leftImage {{
                border-radius: 10px 0 0 10px;
            }}

            #rightFrame {{
                background-color: {self.colors['steel_grey']};
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
                border-left: 1px solid {self.colors['dark_border']};
            }}

            #brandTitle {{
                color: {self.colors['arctic_white']};
                font-size: 30px;
                font-weight: bold;
                letter-spacing: 1px;
            }}

            #loginTitle {{
                color: {self.colors['cool_grey']};
                font-size: 16px;
                letter-spacing: 2px;
                text-transform: uppercase;
            }}

            #fieldLabel {{
                color: {self.colors['cool_grey']};
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            }}

            #inputField {{
                background-color: {self.colors['deep_graphite']};
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                font-size: 14px;
                padding: 0 18px;
                border-radius: 6px;
            }}

            #inputField:focus {{
                border: 1px solid {self.colors['hover_orange']};
            }}

            #comboBox {{
                background-color: {self.colors['deep_graphite']};
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                font-size: 14px;
                padding: 0 14px;
                border-radius: 6px;
            }}

            #comboBox:focus {{
                border: 1px solid {self.colors['hover_orange']};
            }}

            #comboBox QAbstractItemView {{
                background-color: {self.colors['steel_grey']};
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                selection-background-color: {self.colors['hover_orange']};
            }}

            #checkBox {{
                color: {self.colors['arctic_white']};
                font-size: 12px;
                text-transform: uppercase;
            }}

            #checkBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {self.colors['dark_border']};
                background-color: {self.colors['deep_graphite']};
                border-radius: 2px;
            }}

            #checkBox::indicator:checked {{
                background-color: {self.colors['hover_orange']};
                border: 1px solid {self.colors['hover_orange']};
            }}

            #loginButton {{
                background-color: {self.colors['hover_orange']};
                color: {self.colors['arctic_white']};
                border: none;
                font-size: 15px;
                font-weight: bold;
                letter-spacing: 1px;
                border-radius: 6px;
                text-transform: uppercase;
            }}

            #loginButton:hover {{
                background-color: {self.colors['amber']};
            }}

            #loginButton:disabled {{
                background-color: {self.colors['dark_border']};
                color: {self.colors['cool_grey']};
            }}

            #statusLabel {{
                color: {self.colors['cool_grey']};
                font-size: 12px;
                font-weight: bold;
            }}
            """
        )

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
        image_path = self.project_root / "left.png"
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
                return
        self.hero_label.setText("PROC VISION")
        self.hero_label.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 20px; letter-spacing: 4px;")

    # --- Preference handling --------------------------------------------
    def load_saved_preferences(self) -> None:
        if self.session_manager.is_authenticated():
            username = self.session_manager.get_username()
            language = self.session_manager.get_language_preference()
            if username:
                self.username_input.setText(username)
                self.remember_checkbox.setChecked(True)
            if language:
                index = self.lang_combo.findText(language)
                if index >= 0:
                    self.lang_combo.setCurrentIndex(index)

    def save_user_preferences(self, username: str, language: str) -> None:
        try:
            preferences = {
                "language_preference": language,
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
        language = self.lang_combo.currentText()
        remember_me = self.remember_checkbox.isChecked()

        self.clear_status()

        is_valid, error = self.validate_login_input(username, password)
        if not is_valid:
            self.show_error(error)
            return

        self.set_loading_state(True)
        try:
            success, error = self.session_manager.login(username=username, password=password, language=language)
            if success:
                if remember_me:
                    self.save_user_preferences(username, language)
                self.show_success("Login successful. Redirecting…")
                QTimer.singleShot(800, self.navigate_to_main_window)
            else:
                self.show_error(error or "Login failed")
                self.login_attempts += 1
                if self.login_attempts >= self.max_login_attempts:
                    self.lock_login_form()
        except Exception as exc:  # pragma: no cover - logging only
            logger.error(f"Login error: {exc}")
            self.show_error("An unexpected error occurred")
        finally:
            self.set_loading_state(False)

    def validate_login_input(self, username: str, password: str) -> tuple[bool, Optional[str]]:
        """Permit all input combinations."""
        return True, None

    def set_loading_state(self, loading: bool) -> None:
        self.is_loading = loading
        self.username_input.setEnabled(not loading)
        self.password_input.setEnabled(not loading)
        self.lang_combo.setEnabled(not loading)
        self.remember_checkbox.setEnabled(not loading)
        self.login_button.setEnabled(not loading)
        if loading:
            self.login_button.setText("Authenticating…")
        else:
            self.login_button.setText("Login")

    def show_error(self, message: str) -> None:
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {self.colors['error_red']}; font-size: 12px;")
        self.password_input.setStyleSheet(
            f"border: 1px solid {self.colors['error_red']}; background-color: {self.colors['deep_graphite']};"
        )

    def show_success(self, message: str) -> None:
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {self.colors['success_green']}; font-size: 12px;")

    def clear_status(self) -> None:
        self.status_label.setText("")
        self.status_label.setStyleSheet("")
        self.password_input.setStyleSheet("")

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

    def on_remember_toggled(self, checked: bool) -> None:  # pragma: no cover - logging only
        logger.info(f"Remember username toggled: {checked}")

    def navigate_to_main_window(self) -> None:
        try:
            self.hide()
            try:
                from src.ui.main_window import MainWindow
            except ImportError:  # pragma: no cover - fallback for script execution
                from .main_window import MainWindow  # type: ignore
            self.main_window = MainWindow(self.session_manager)
            self.main_window.show()
            logger.info("Navigated to main window")
        except Exception as exc:  # pragma: no cover - logging only
            logger.error(f"Failed to navigate to main window: {exc}")
            QMessageBox.critical(self, "Navigation Error", "Failed to open main window.")
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
