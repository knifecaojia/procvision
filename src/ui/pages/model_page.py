"""
Model management page for the industrial vision system.
"""

import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QGridLayout
)
from PySide6.QtCore import Qt
from ..components.model_card import ModelCard

logger = logging.getLogger(__name__)


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
        
        # Model cards in scroll area
        scroll_area = QScrollArea()
        scroll_area.setObjectName("modelScrollArea")
        scroll_area.setStyleSheet("QScrollArea#modelScrollArea { background-color: #1f232b; border: none; }")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container for cards
        cards_container = QWidget()
        cards_container.setObjectName("cardsContainer")
        cards_container.setStyleSheet("QWidget#cardsContainer { background-color: #1f232b; border: 1px solid #1f232b; }")
        # cards_layout will be created later as QGridLayout
        
        # Sample model data
        models_data = [
            {
                "id": 1,
                "name": "Edge Detection Standard",
                "type": "opencv",
                "type_icon": "🖥️",
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
                "type_icon": "🖥️",
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
                "type_icon": "🧠",
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
                "type_icon": "🧠",
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
                "type_icon": "🖥️",
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
                "type_icon": "🧠",
                "type_label": "YOLO",
                "version": "v4.1.0",
                "description": "YOLOv7装配状态分类模型",
                "size": "52.1 MB",
                "last_updated": "2024-11-02",
                "status": "active",
                "status_label": "启用"
            }
        ]
        
        # Create and add cards in 2 columns
        cards_layout = QGridLayout()
        cards_layout.setSpacing(15)
        cards_layout.setContentsMargins(15, 15, 15, 15)

        for index, model_data in enumerate(models_data):
            card = ModelCard(model_data)
            row = index // 2
            col = index % 2
            cards_layout.addWidget(card, row, col)

        # Add stretch to the last row to push cards up
        cards_layout.setRowStretch(len(models_data) // 2 + 1, 1)

        cards_container.setLayout(cards_layout)
        
        scroll_area.setWidget(cards_container)
        layout.addWidget(scroll_area)