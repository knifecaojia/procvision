"""
Model management page for the industrial vision system.
"""

import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QScrollArea, QWidget, QGridLayout, QLineEdit, QSizePolicy
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
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Header with icon and title
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Icon
        icon_frame = QFrame()
        icon_frame.setObjectName("iconFrame")
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
        
        # Status badge
        status_badge = QLabel(self.model_data["status_label"])
        status_badge.setObjectName("statusBadge")
        
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
        actions_layout.setSpacing(5)
        
        view_btn = QPushButton("查看")
        view_btn.setObjectName("viewButton")
        view_btn.setFixedHeight(30)
        
        update_btn = QPushButton("更新")
        update_btn.setObjectName("updateButton")
        update_btn.setFixedHeight(30)
        
        delete_btn = QPushButton("删除")
        delete_btn.setObjectName("deleteButton")
        delete_btn.setFixedHeight(30)
        delete_btn.setFixedWidth(30)
        
        actions_layout.addWidget(view_btn)
        actions_layout.addWidget(update_btn)
        actions_layout.addWidget(delete_btn)
        
        layout.addLayout(actions_layout)


class ModelPage(QFrame):
    """Model management page implementation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("modelPage")
        self.init_ui()
        
    def init_ui(self):
        """Initialize the model page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header section
        header_frame = QFrame()
        header_frame.setObjectName("modelHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("模型管理")
        title_label.setObjectName("modelTitle")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        download_btn = QPushButton("从服务器下载")
        download_btn.setObjectName("downloadButton")
        download_btn.setFixedHeight(40)
        
        upload_btn = QPushButton("上传模型")
        upload_btn.setObjectName("uploadButton")
        upload_btn.setFixedHeight(40)
        
        button_layout.addWidget(download_btn)
        button_layout.addWidget(upload_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Filter section
        filter_frame = QFrame()
        filter_frame.setObjectName("filterFrame")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(15)
        
        # Search
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_label.setObjectName("filterLabel")
        search_input = QLineEdit()
        search_input.setPlaceholderText("搜索模型名称或描述...")
        search_input.setObjectName("searchInput")
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_input)
        
        # Type filter
        type_layout = QHBoxLayout()
        type_label = QLabel("类型:")
        type_label.setObjectName("filterLabel")
        type_combo = QComboBox()
        type_combo.addItems(["所有类型", "OpenCV传统", "深度学习"])
        type_combo.setObjectName("filterCombo")
        type_layout.addWidget(type_label)
        type_layout.addWidget(type_combo)
        
        filter_layout.addLayout(search_layout)
        filter_layout.addLayout(type_layout)
        filter_layout.addStretch()
        
        layout.addWidget(filter_frame)
        
        # Model cards in scroll area
        scroll_area = QScrollArea()
        scroll_area.setObjectName("modelScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container for cards
        cards_container = QWidget()
        cards_container.setObjectName("cardsContainer")
        cards_layout = QVBoxLayout(cards_container)
        cards_layout.setSpacing(15)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sample model data
        models_data = [
            {
                "id": 1,
                "name": "Edge Detection Standard",
                "type": "opencv",
                "type_icon": "C",
                "type_label": "OpenCV",
                "version": "v2.1.0",
                "description": "Canny边缘检测算法，用于零件边缘识别",
                "size": "1.2 MB",
                "last_updated": "2024-11-05",
                "status": "active",
                "status_label": "启用"
            },
            {
                "id": 2,
                "name": "Component Position Check",
                "type": "opencv",
                "type_icon": "C",
                "type_label": "OpenCV",
                "version": "v1.8.3",
                "description": "基于模板匹配的零件位置检测",
                "size": "850 KB",
                "last_updated": "2024-11-01",
                "status": "active",
                "status_label": "启用"
            },
            {
                "id": 3,
                "name": "PCB Defect Detection",
                "type": "yolo",
                "type_icon": "B",
                "type_label": "YOLO",
                "version": "v5.0.2",
                "description": "YOLOv8缺陷检测模型，识别PCB焊接缺陷",
                "size": "45.6 MB",
                "last_updated": "2024-11-03",
                "status": "active",
                "status_label": "启用"
            },
            {
                "id": 4,
                "name": "Screw Detection",
                "type": "yolo",
                "type_icon": "B",
                "type_label": "YOLO",
                "version": "v3.2.1",
                "description": "YOLOv5螺丝检测模型，验证螺丝安装",
                "size": "28.3 MB",
                "last_updated": "2024-10-28",
                "status": "active",
                "status_label": "启用"
            },
            {
                "id": 5,
                "name": "QR Code Reader",
                "type": "opencv",
                "type_icon": "C",
                "type_label": "OpenCV",
                "version": "v1.5.0",
                "description": "QR码识别与解码算法",
                "size": "600 KB",
                "last_updated": "2024-10-25",
                "status": "inactive",
                "status_label": "未用"
            },
            {
                "id": 6,
                "name": "Assembly Classification",
                "type": "yolo",
                "type_icon": "B",
                "type_label": "YOLO",
                "version": "v4.1.0",
                "description": "YOLOv7装配状态分类模型",
                "size": "52.1 MB",
                "last_updated": "2024-11-02",
                "status": "active",
                "status_label": "启用"
            }
        ]
        
        # Create and add cards
        for model_data in models_data:
            card = ModelCard(model_data)
            cards_layout.addWidget(card)
        
        cards_layout.addStretch()
        
        scroll_area.setWidget(cards_container)
        layout.addWidget(scroll_area)