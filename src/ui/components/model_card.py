"""
Model card component for displaying model information.
"""

import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, QProgressBar
)
from PySide6.QtCore import Qt, Signal

logger = logging.getLogger(__name__)


class ModelCard(QFrame):
    """Model card widget to display model information."""
    
    # Signals for parent to handle
    download_requested = Signal(dict)
    deploy_requested = Signal(dict)
    undeploy_requested = Signal(dict)
    delete_requested = Signal(dict)

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
        icon_label = QLabel(self.model_data.get("type_icon", "📦"))
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

        # Status/Source Badge
        badges_layout = QVBoxLayout()
        badges_layout.setSpacing(4)
        badges_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Status Badge
        status = self.model_data.get("status", "remote_only")
        status_label = self.model_data.get("status_label", "未知")
        status_badge = QLabel(status_label)
        status_badge.setObjectName("statusBadge")
        status_badge.setProperty("status", status) # For CSS styling
        badges_layout.addWidget(status_badge)

        header_layout.addWidget(icon_frame)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addLayout(badges_layout)

        layout.addLayout(header_layout)

        # Description
        desc_label = QLabel(self.model_data.get("description", ""))
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
        source = self.model_data.get("source", "server")
        source_text = "云端" if source == "server" else "本地"
        type_value = QLabel(source_text)
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
        size_value = QLabel(self.model_data.get("size", "Unknown"))
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
        updated_value = QLabel(self.model_data.get("last_updated", "Unknown"))
        updated_value.setObjectName("infoValue")
        updated_layout.addWidget(updated_label)
        updated_layout.addWidget(updated_value)

        info_grid.addWidget(type_frame, 0, 0)
        info_grid.addWidget(size_frame, 0, 1)
        info_grid.addWidget(updated_frame, 1, 0, 1, 2)  # Span 2 columns

        layout.addLayout(info_grid)

        # Progress Bar (Hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Action buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        # Dynamic Buttons based on Status
        # Remote Only -> Download
        if status == "remote_only":
            download_btn = QPushButton("下载")
            download_btn.setObjectName("downloadButton") # Style needed
            download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            download_btn.clicked.connect(self._on_download)
            actions_layout.addWidget(download_btn)
        
        # Downloaded -> Deploy, Delete Zip
        elif status == "downloaded":
            deploy_btn = QPushButton("部署")
            deploy_btn.setObjectName("uploadButton") # Use uploadButton style for Deploy
            deploy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            deploy_btn.clicked.connect(self._on_deploy)
            actions_layout.addWidget(deploy_btn)

            del_zip_btn = QPushButton("移除包")
            del_zip_btn.setObjectName("deleteButton")
            del_zip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_zip_btn.clicked.connect(self._on_delete)
            actions_layout.addWidget(del_zip_btn)
            
        # Deployed -> Undeploy
        elif status == "deployed":
            undeploy_btn = QPushButton("卸载部署")
            undeploy_btn.setObjectName("deleteButton")
            undeploy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            undeploy_btn.clicked.connect(self._on_undeploy)
            actions_layout.addWidget(undeploy_btn)

        layout.addLayout(actions_layout)

    def _on_download(self):
        self.download_requested.emit(self.model_data)

    def _on_deploy(self):
        self.deploy_requested.emit(self.model_data)

    def _on_undeploy(self):
        self.undeploy_requested.emit(self.model_data)

    def _on_delete(self):
        self.delete_requested.emit(self.model_data)

    def set_progress(self, value: int):
        if value < 100:
            self.progress_bar.show()
            self.progress_bar.setValue(value)
        else:
            self.progress_bar.hide()

