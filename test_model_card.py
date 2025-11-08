#!/usr/bin/env python3
"""
Test script for ModelCard component.
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QScrollArea

# Add src to path
sys.path.insert(0, 'src')

from ui.components.model_card import ModelCard

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ModelCard Test")
        self.setMinimumSize(800, 600)

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

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(1)  # ScrollBarAsNeeded

        # Container for cards
        cards_container = QWidget()
        cards_layout = QVBoxLayout(cards_container)
        cards_layout.setSpacing(15)

        # Create cards
        for model_data in models_data:
            card = ModelCard(model_data)
            cards_layout.addWidget(card)

        cards_layout.addStretch()

        scroll.setWidget(cards_container)
        layout.addWidget(scroll)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
