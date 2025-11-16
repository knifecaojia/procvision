"""
Model card component for displaying model information.
"""

import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class ModelCard(QFrame):
    """Model card widget to display model information."""

    def __init__(self, model_data, parent=None):
        super().__init__(parent)
        self.setObjectName("modelCard")
        self.model_data = model_data
        self.init_ui()

    def init_ui(self):
        """Initialize the model card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header with icon and title
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Icon based on model type
        model_type = self.model_data.get("type", "opencv")
        icon_frame = QFrame()
        icon_frame.setObjectName(f"iconFrame {model_type}")
        icon_frame.setFixedSize(40, 40)
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)
        icon_label = QLabel(self.model_data["type_icon"])
        icon_label.setObjectName("iconLabel")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)

        # Title and version
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title_label = QLabel(self.model_data["name"])
        title_label.setObjectName("cardTitle")

        version_label = QLabel(self.model_data["version"])
        version_label.setObjectName("cardVersion")

        title_layout.addWidget(title_label)
        title_layout.addWidget(version_label)

        # Status badge based on status
        status = self.model_data.get("status", "active")
        status_badge = QLabel(self.model_data["status_label"])
        status_badge.setObjectName(f"statusBadge {status}")

        header_layout.addWidget(icon_frame)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addWidget(status_badge)

        layout.addLayout(header_layout)

        # Description
        desc_label = QLabel(self.model_data["description"])
        desc_label.setObjectName("descLabel")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Info grid
        info_grid = QGridLayout()
        info_grid.setSpacing(8)
        info_grid.setObjectName("infoGrid")

        # Type
        type_frame = QFrame()
        type_frame.setObjectName("infoFrame")
        type_layout = QVBoxLayout(type_frame)
        type_layout.setContentsMargins(8, 8, 8, 8)
        type_label = QLabel("类型")
        type_label.setObjectName("infoLabel")
        type_value = QLabel(self.model_data["type_label"])
        type_value.setObjectName("infoValue")
        type_layout.addWidget(type_label)
        type_layout.addWidget(type_value)

        # Size
        size_frame = QFrame()
        size_frame.setObjectName("infoFrame")
        size_layout = QVBoxLayout(size_frame)
        size_layout.setContentsMargins(8, 8, 8, 8)
        size_label = QLabel("大小")
        size_label.setObjectName("infoLabel")
        size_value = QLabel(self.model_data["size"])
        size_value.setObjectName("infoValue")
        size_layout.addWidget(size_label)
        size_layout.addWidget(size_value)

        # Last updated
        updated_frame = QFrame()
        updated_frame.setObjectName("infoFrame")
        updated_layout = QVBoxLayout(updated_frame)
        updated_layout.setContentsMargins(8, 8, 8, 8)
        updated_label = QLabel("更新时间")
        updated_label.setObjectName("infoLabel")
        updated_value = QLabel(self.model_data["last_updated"])
        updated_value.setObjectName("infoValue")
        updated_layout.addWidget(updated_label)
        updated_layout.addWidget(updated_value)

        info_grid.addWidget(type_frame, 0, 0)
        info_grid.addWidget(size_frame, 0, 1)
        info_grid.addWidget(updated_frame, 1, 0, 1, 2)  # Span 2 columns

        layout.addLayout(info_grid)

        # Action buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        view_btn = QPushButton("查看")
        view_btn.setObjectName("viewButton")
        view_btn.setFixedHeight(32)

        update_btn = QPushButton("更新")
        update_btn.setObjectName("updateButton")
        update_btn.setFixedHeight(32)

        delete_btn = QPushButton("删除")
        delete_btn.setObjectName("deleteButton")
        delete_btn.setFixedHeight(32)
        delete_btn.setFixedWidth(32)

        actions_layout.addWidget(view_btn)
        actions_layout.addWidget(update_btn)
        actions_layout.addWidget(delete_btn)

        layout.addLayout(actions_layout)
