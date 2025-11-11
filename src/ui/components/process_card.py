"""
Process card component for displaying process information.
"""

import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout
)
from PySide6.QtCore import Qt, Signal

logger = logging.getLogger(__name__)


class ProcessCard(QFrame):
    """Process card widget to display process information."""

    # Signal emitted when "启动工艺" button is clicked
    start_process_clicked = Signal(dict)  # Emits process_data

    def __init__(self, process_data, parent=None):
        super().__init__(parent)
        self.setObjectName("processCard")
        self.process_data = process_data
        self.init_ui()

    def init_ui(self):
        """Initialize the process card UI."""
        self.setMinimumWidth(800)
        self.setStyleSheet("""
            QFrame#processCard {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                font-family: "Arial";
            }
            QFrame#processCard:hover {
                border: 1px solid rgba(255, 165, 0, 0.5);
            }

            #cardTitle {
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
            }

            #cardId {
                color: #9ca3af;
                font-size: 12px;
            }

            #typeBadge {
                background-color: #1a1d23;
                color: #8C92A0;
                border: 1px solid #242831;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 12px;
            }

            #statusBadge {
                background-color: #3CC37A;
                color: #1a1d23;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 12px;
                font-weight: bold;
            }

            #infoFrame {
                background-color: #1a1a1a;
                border-radius: 4px;
            }

            #infoLabel {
                color: #6b7280;
                font-size: 12px;
            }

            #infoValue {
                color: #ffffff;
                font-size: 14px;
            }

            #modelsTitle {
                color: #9ca3af;
                font-size: 13px;
            }

            #modelBadge {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 12px;
                margin-right: 5px;
            }

            #viewButton {
                background-color: transparent;
                border: 1px solid #3a3a3a;
                color: #9ca3af;
                border-radius: 6px;
                font-size: 13px;
            }

            #viewButton:hover {
                border: 1px solid #ffa500;
                color: #ffffff;
            }

            #startButton {
                background-color: rgba(60, 195, 122, 0.15);
                border: 1px solid rgba(60, 195, 122, 0.55);
                color: #6ff3b3;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }

            #startButton:hover {
                border: 1px solid #6ff3b3;
                color: #ffffff;
                background-color: rgba(60, 195, 122, 0.35);
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header with title and badges
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Title section
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title_label = QLabel(self.process_data["title"])
        title_label.setObjectName("cardTitle")

        id_label = QLabel(f"{self.process_data['name']} · {self.process_data['version']}")
        id_label.setObjectName("cardId")

        title_layout.addWidget(title_label)
        title_layout.addWidget(id_label)

        # Badges
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(5)

        type_badge = QLabel(self.process_data["type_label"])
        type_badge.setObjectName("typeBadge")

        status_badge = QLabel(self.process_data["status_label"])
        status_badge.setObjectName("statusBadge")

        badges_layout.addWidget(type_badge)
        badges_layout.addWidget(status_badge)
        badges_layout.addStretch()

        header_layout.addLayout(title_layout)
        header_layout.addLayout(badges_layout)

        layout.addLayout(header_layout)

        # Info grid
        info_grid = QGridLayout()
        info_grid.setSpacing(8)
        info_grid.setObjectName("infoGrid")

        # Steps
        steps_frame = QFrame()
        steps_frame.setObjectName("infoFrame")
        steps_layout = QVBoxLayout(steps_frame)
        steps_layout.setContentsMargins(8, 8, 8, 8)
        steps_label = QLabel("工艺步骤")
        steps_label.setObjectName("infoLabel")
        steps_value = QLabel(f"{self.process_data['steps']} 步")
        steps_value.setObjectName("infoValue")
        steps_layout.addWidget(steps_label)
        steps_layout.addWidget(steps_value)

        # Models
        models_frame = QFrame()
        models_frame.setObjectName("infoFrame")
        models_layout = QVBoxLayout(models_frame)
        models_layout.setContentsMargins(8, 8, 8, 8)
        models_label = QLabel("使用模型")
        models_label.setObjectName("infoLabel")
        models_value = QLabel(f"{len(self.process_data['models'])} 个")
        models_value.setObjectName("infoValue")
        models_layout.addWidget(models_label)
        models_layout.addWidget(models_value)

        # Last modified
        modified_frame = QFrame()
        modified_frame.setObjectName("infoFrame")
        modified_layout = QVBoxLayout(modified_frame)
        modified_layout.setContentsMargins(8, 8, 8, 8)
        modified_label = QLabel("最后修改")
        modified_label.setObjectName("infoLabel")
        modified_value = QLabel(self.process_data["last_modified"])
        modified_value.setObjectName("infoValue")
        modified_layout.addWidget(modified_label)
        modified_layout.addWidget(modified_value)

        info_grid.addWidget(steps_frame, 0, 0)
        info_grid.addWidget(models_frame, 0, 1)
        info_grid.addWidget(modified_frame, 0, 2)

        layout.addLayout(info_grid)

        # Models list
        models_title = QLabel("关联模型：")
        models_title.setObjectName("modelsTitle")
        layout.addWidget(models_title)

        models_layout = QHBoxLayout()
        models_layout.setSpacing(5)
        models_layout.setContentsMargins(0, 0, 0, 0)

        for model in self.process_data["models"]:
            model_badge = QLabel(model)
            model_badge.setObjectName("modelBadge")
            models_layout.addWidget(model_badge)

        models_layout.addStretch()
        layout.addLayout(models_layout)

        # Action buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        view_btn = QPushButton("查看详情")
        view_btn.setObjectName("viewButton")
        view_btn.setFixedHeight(32)

        start_btn = QPushButton("启动工艺")
        start_btn.setObjectName("startButton")
        start_btn.setFixedHeight(32)
        start_btn.clicked.connect(self.on_start_process_clicked)

        actions_layout.addWidget(view_btn)
        actions_layout.addWidget(start_btn)

        layout.addLayout(actions_layout)

    def on_start_process_clicked(self):
        """Handle start process button click."""
        logger.info(f"Start process clicked for: {self.process_data['name']}")
        self.start_process_clicked.emit(self.process_data)
