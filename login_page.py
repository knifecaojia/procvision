import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QLineEdit, QPushButton,
                              QComboBox, QCheckBox, QFrame, QSplitter)
from PySide6.QtCore import Qt, QEvent, QPoint


class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SMART-VISION LOGIN")
        self.setFixedSize(1200, 700)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.drag_pos = None

        # 设置主颜色
        self.colors = {
            'deep_graphite': '#1A1D23',
            'steel_grey': '#1F232B',
            'dark_border': '#242831',
            'arctic_white': '#F2F4F8',
            'cool_grey': '#8C92A0',
            'hover_orange': '#FF8C32',
            'amber': '#FFAC54',
            'icon_neutral': '#D7DCE6',
            'success_green': '#3CC37A',
            'error_red': '#E85454',
            'warning_yellow': '#FFB347'
        }

        self.init_ui()
        self.setup_style()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 自定义标题栏
        self.title_bar = self.create_title_bar()
        main_layout.addWidget(self.title_bar)

        # 使用分割器创建左右分栏
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        main_layout.addWidget(splitter)
        self.splitter = splitter

        # 左侧面板
        self.create_left_panel(splitter)

        # 右侧登录面板
        self.create_right_panel(splitter)

        # 设置分割器比例
        splitter.setSizes([300, 600])

    def create_title_bar(self):
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(12)

        title_label = QLabel("SMART-VISION")
        title_label.setObjectName("titleBarLabel")
        version_label = QLabel("v1.0.0")
        version_label.setObjectName("titleVersion")

        self.min_button = QPushButton("-")
        self.min_button.setObjectName("windowButton")
        self.min_button.setFixedSize(32, 24)
        self.min_button.clicked.connect(self.showMinimized)

        self.close_button = QPushButton("x")
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(32, 24)
        self.close_button.clicked.connect(self.close)

        layout.addWidget(title_label)
        layout.addWidget(version_label)
        layout.addStretch()
        layout.addWidget(self.min_button)
        layout.addWidget(self.close_button)

        title_bar.installEventFilter(self)
        return title_bar

    def create_left_panel(self, parent):
        left_frame = QFrame()
        left_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['deep_graphite']};
                border-right: 1px solid {self.colors['dark_border']};
            }}
        """)

        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(60, 80, 60, 60)
        left_layout.setSpacing(40)

        # SMART-VISION 标题
        title_label = QLabel("SMART-VISION")
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_label.setObjectName("titleLabel")

        # 版本信息
        version_label = QLabel("VERSION: 1.0.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        version_label.setObjectName("versionLabel")

        # 连接状态
        status_frame = QFrame()
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 0, 0, 0)

        status_title = QLabel("CAMERA CONNECTION")
        status_title.setObjectName("statusTitle")

        status_items = [
            ("Lower camera", False),
            ("Left camera", False),
            ("Right camera", False)
        ]

        for name, connected in status_items:
            item_layout = QHBoxLayout()
            item_layout.setContentsMargins(0, 10, 0, 10)

            # 状态指示灯
            status_indicator = QLabel("●")
            status_indicator.setObjectName("statusIndicator")
            color = self.colors['success_green'] if connected else self.colors['cool_grey']
            status_indicator.setStyleSheet(f"color: {color}; font-size: 16px;")

            # 状态文本
            status_text = QLabel(name.upper())
            status_text.setObjectName("statusText")

            item_layout.addWidget(status_indicator)
            item_layout.addWidget(status_text)
            item_layout.addStretch()

            status_layout.addLayout(item_layout)

        # 底部提示信息
        hint_label = QLabel("CAMERA NOT CONNECTED")
        hint_label.setObjectName("hintLabel")
        hint_label.setStyleSheet(f"color: {self.colors['error_red']};")

        left_layout.addWidget(title_label)
        left_layout.addWidget(version_label)
        left_layout.addStretch()
        left_layout.addWidget(status_title)
        left_layout.addLayout(status_layout)
        left_layout.addStretch()
        left_layout.addWidget(hint_label)

        parent.addWidget(left_frame)

    def create_right_panel(self, parent):
        right_frame = QFrame()
        right_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['steel_grey']};
            }}
        """)

        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(80, 80, 80, 60)
        right_layout.setSpacing(30)

        # 登录表单标题
        login_title = QLabel("USER LOGIN")
        login_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        login_title.setObjectName("loginTitle")

        # 用户名输入框
        username_label = QLabel("USERNAME")
        username_label.setObjectName("fieldLabel")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("admin")
        self.username_input.setObjectName("inputField")
        self.username_input.setClearButtonEnabled(True)
        self.username_input.setFixedHeight(48)

        # 密码输入框
        password_label = QLabel("PASSWORD")
        password_label.setObjectName("fieldLabel")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("●●●●●●●●")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setObjectName("inputField")
        self.password_input.setClearButtonEnabled(True)
        self.password_input.setFixedHeight(48)

        # 语言选择
        lang_label = QLabel("LANGUAGE")
        lang_label.setObjectName("fieldLabel")

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["中", "English"])
        self.lang_combo.setObjectName("comboBox")
        self.lang_combo.setFixedHeight(48)

        # 记住用户名复选框
        self.remember_checkbox = QCheckBox("Remember username")
        self.remember_checkbox.setObjectName("checkBox")

        # 登录按钮
        self.login_button = QPushButton("LOGIN")
        self.login_button.setObjectName("loginButton")

        # 添加到布局
        right_layout.addStretch()
        right_layout.addWidget(login_title)
        right_layout.addSpacing(40)

        # 用户名字段
        right_layout.addWidget(username_label)
        right_layout.addWidget(self.username_input)
        right_layout.addSpacing(20)

        # 密码字段
        right_layout.addWidget(password_label)
        right_layout.addWidget(self.password_input)
        right_layout.addSpacing(20)

        # 语言选择
        right_layout.addWidget(lang_label)
        right_layout.addWidget(self.lang_combo)
        right_layout.addSpacing(30)

        # 记住用户名
        right_layout.addWidget(self.remember_checkbox)
        right_layout.addSpacing(40)

        # 登录按钮
        right_layout.addWidget(self.login_button)
        right_layout.addStretch()

        # 底部按钮区域
        bottom_layout = QHBoxLayout()

        # 预设按钮
        preset_button = QPushButton("Preset")
        preset_button.setObjectName("bottomButton")

        # 主题切换按钮
        theme_button = QPushButton("Theme")
        theme_button.setObjectName("bottomButton")

        bottom_layout.addWidget(preset_button)
        bottom_layout.addStretch()
        bottom_layout.addWidget(theme_button)

        right_layout.addLayout(bottom_layout)

        parent.addWidget(right_frame)

    def setup_style(self):
        self.setStyleSheet(f"""
            /* 全局样式 */
            QMainWindow {{
                background-color: {self.colors['deep_graphite']};
            }}

            /* 标题样式 */
            #titleLabel {{
                color: {self.colors['arctic_white']};
                font-size: 28px;
                font-weight: bold;
                letter-spacing: 2px;
                text-transform: uppercase;
            }}

            #versionLabel {{
                color: {self.colors['cool_grey']};
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}

            #titleBar {{
                background-color: {self.colors['steel_grey']};
                border-bottom: 1px solid {self.colors['dark_border']};
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
                padding: 0;
            }}

            #closeButton:hover {{
                background-color: {self.colors['error_red']};
                border: 1px solid {self.colors['error_red']};
            }}

            #loginTitle {{
                color: {self.colors['arctic_white']};
                font-size: 24px;
                font-weight: bold;
                letter-spacing: 1.5px;
                text-transform: uppercase;
            }}

            /* 状态标题 */
            #statusTitle {{
                color: {self.colors['arctic_white']};
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}

            #statusText {{
                color: {self.colors['arctic_white']};
                font-size: 14px;
                text-transform: uppercase;
            }}

            /* 状态指示灯 */
            #statusIndicator {{
                color: {self.colors['cool_grey']};
                font-size: 16px;
                margin-right: 10px;
            }}

            #hintLabel {{
                color: {self.colors['error_red']};
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}

            /* 字段标签 */
            #fieldLabel {{
                color: {self.colors['cool_grey']};
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}

            /* 输入框样式 */
            #inputField {{
                background-color: {self.colors['deep_graphite']};
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                font-size: 14px;
                padding: 0 16px;
                border-radius: 6px;
                text-align: left;
                selection-background-color: {self.colors['hover_orange']};
            }}

            #inputField:focus {{
                border: 1px solid {self.colors['hover_orange']};
            }}

            /* 下拉框样式 */
            #comboBox {{
                background-color: {self.colors['deep_graphite']};
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                font-size: 14px;
                padding: 0 16px;
                border-radius: 6px;
            }}

            #comboBox:focus {{
                border: 1px solid {self.colors['hover_orange']};
            }}

            #comboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid {self.colors['dark_border']};
            }}

            #comboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {self.colors['icon_neutral']};
                margin-right: 10px;
            }}

            #comboBox QAbstractItemView {{
                background-color: {self.colors['steel_grey']};
                border: 1px solid {self.colors['dark_border']};
                color: {self.colors['arctic_white']};
                selection-background-color: {self.colors['hover_orange']};
            }}

            /* 复选框样式 */
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

            /* 登录按钮样式 */
            #loginButton {{
                background-color: {self.colors['hover_orange']};
                color: {self.colors['arctic_white']};
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 16px;
                border-radius: 4px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}

            #loginButton:hover {{
                background-color: {self.colors['amber']};
            }}

            #loginButton:pressed {{
                background-color: {self.colors['hover_orange']};
            }}

            /* 底部按钮样式 */
            #bottomButton {{
                background-color: transparent;
                color: {self.colors['icon_neutral']};
                border: 1px solid {self.colors['dark_border']};
                font-size: 12px;
                padding: 8px 16px;
                border-radius: 4px;
                text-transform: uppercase;
            }}

            #bottomButton:hover {{
                border: 1px solid {self.colors['hover_orange']};
                color: {self.colors['arctic_white']};
            }}
        """)

        # 连接信号
        self.login_button.clicked.connect(self.on_login_clicked)
        self.remember_checkbox.toggled.connect(self.on_remember_toggled)

    def on_login_clicked(self):
        username = self.username_input.text()
        password = self.password_input.text()
        print(f"Login attempt: {username}, {'*' * len(password) if password else ''}")

    def on_remember_toggled(self, checked):
        print(f"Remember username: {checked}")

    def eventFilter(self, watched, event):
        if watched == getattr(self, "title_bar", None):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if event.type() == QEvent.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton:
                if self.drag_pos:
                    self.move(event.globalPosition().toPoint() - self.drag_pos)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self.drag_pos = None
                return True
        return super().eventFilter(watched, event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = LoginWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
