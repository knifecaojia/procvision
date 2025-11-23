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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title_label = QLabel(self.process_data["algorithm_name"])
        title_label.setObjectName("cardTitle")

        id_label = QLabel(f"PID {self.process_data.get('pid', 'N/A')} · 版本 {self.process_data['algorithm_version']}")
        id_label.setObjectName("cardId")

        title_layout.addWidget(title_label)
        title_layout.addWidget(id_label)

        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(5)

        badges_layout.addStretch()

        header_layout.addLayout(title_layout)
        header_layout.addLayout(badges_layout)

        layout.addLayout(header_layout)

        # Info grid
        info_grid = QGridLayout()
        info_grid.setSpacing(8)
        info_grid.setObjectName("infoGrid")

        steps_frame = QFrame()
        steps_frame.setObjectName("infoFrame")
        steps_layout = QVBoxLayout(steps_frame)
        steps_layout.setContentsMargins(8, 8, 8, 8)
        steps_label = QLabel("工艺步骤")
        steps_label.setObjectName("infoLabel")
        steps_value = QLabel(f"{len(self.process_data['steps'])} 步")
        steps_value.setObjectName("infoValue")
        steps_layout.addWidget(steps_label)
        steps_layout.addWidget(steps_value)

        summary_frame = QFrame()
        summary_frame.setObjectName("infoFrame")
        summary_layout = QVBoxLayout(summary_frame)
        summary_layout.setContentsMargins(8, 8, 8, 8)
        summary_label = QLabel("摘要")
        summary_label.setObjectName("infoLabel")
        summary_value = QLabel(self.process_data["summary"])
        summary_value.setObjectName("infoValue")
        summary_value.setWordWrap(True)
        summary_layout.addWidget(summary_label)
        summary_layout.addWidget(summary_value)

        version_frame = QFrame()
        version_frame.setObjectName("infoFrame")
        version_layout = QVBoxLayout(version_frame)
        version_layout.setContentsMargins(8, 8, 8, 8)
        version_label = QLabel("版本")
        version_label.setObjectName("infoLabel")
        version_value = QLabel(self.process_data["algorithm_version"])
        version_value.setObjectName("infoValue")
        version_layout.addWidget(version_label)
        version_layout.addWidget(version_value)

        info_grid.addWidget(steps_frame, 0, 0)
        info_grid.addWidget(summary_frame, 0, 1)
        info_grid.addWidget(version_frame, 0, 2)

        layout.addLayout(info_grid)

        steps_title = QLabel("步骤预览：")
        steps_title.setObjectName("modelsTitle")
        layout.addWidget(steps_title)

        models_layout = QHBoxLayout()
        models_layout.setSpacing(5)
        models_layout.setContentsMargins(0, 0, 0, 0)

        for step in self.process_data["steps"]:
            model_badge = QLabel(step["step_name"])
            model_badge.setObjectName("modelBadge")
            models_layout.addWidget(model_badge)

        models_layout.addStretch()
        layout.addLayout(models_layout)

        # Action buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        start_btn = QPushButton("启动工艺")
        start_btn.setObjectName("startButton")
        start_btn.setFixedHeight(32)
        start_btn.clicked.connect(self.on_start_process_clicked)

        actions_layout.addWidget(start_btn)

        layout.addLayout(actions_layout)

    def on_start_process_clicked(self):
        """Handle start process button click."""
        logger.info(f"Start process clicked for: {self.process_data['algorithm_name']}")
        normalized = {
            "name": self.process_data.get("algorithm_name", ""),
            "title": self.process_data.get("algorithm_name", ""),
            "version": self.process_data.get("algorithm_version", ""),
            "steps": len(self.process_data.get("steps", [])),
            "algorithm_name": self.process_data.get("algorithm_name", ""),
            "algorithm_version": self.process_data.get("algorithm_version", ""),
            "summary": self.process_data.get("summary", ""),
            "steps_detail": self.process_data.get("steps", []),
            "pid": self.process_data.get("pid", None),
        }
        self.start_process_clicked.emit(normalized)
