"""
Process information page for the industrial vision system.
"""

import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QGridLayout
)
from PySide6.QtCore import Qt
from ..components.process_card import ProcessCard

logger = logging.getLogger(__name__)


class ProcessPage(QFrame):
    """Process information page implementation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("processPage")
        self.init_ui()
        
    def init_ui(self):
        """Initialize the process page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header section
        header_frame = QFrame()
        header_frame.setObjectName("processHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("工艺信息")
        title_label.setObjectName("processTitle")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
        
        # Process cards in scroll area
        scroll_area = QScrollArea()
        scroll_area.setObjectName("processScrollArea")
        scroll_area.setStyleSheet("QScrollArea#processScrollArea { background-color: #1f232b; border: none; }")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container for cards
        cards_container = QWidget()
        cards_container.setObjectName("cardsContainer")
        cards_container.setStyleSheet("QWidget#cardsContainer { background-color: #1f232b; border: 1px solid #1f232b; }")
        # cards_layout will be created later as QGridLayout
        
        # Sample process data
        processes_data = [
            {
                "id": 1,
                "name": "ME-ASM-2024-001",
                "title": "机械底座装配工艺",
                "type": "mechanical",
                "type_label": "机械安装",
                "version": "v3.2",
                "steps": 12,
                "models": ["Edge Detection Standard", "Screw Detection"],
                "status": "active",
                "status_label": "已发布",
                "last_modified": "2024-11-05"
            },
            {
                "id": 2,
                "name": "PCB-ASM-2024-015",
                "title": "主控板PCB装配工艺",
                "type": "pcb",
                "type_label": "PCB安装",
                "version": "v2.8",
                "steps": 8,
                "models": ["PCB Defect Detection", "Component Position Check"],
                "status": "active",
                "status_label": "已发布",
                "last_modified": "2024-11-03"
            },
            {
                "id": 3,
                "name": "PKG-STD-2024-003",
                "title": "标准包装工艺流程",
                "type": "packaging",
                "type_label": "包装",
                "version": "v1.5",
                "steps": 5,
                "models": ["QR Code Reader", "Assembly Classification"],
                "status": "active",
                "status_label": "已发布",
                "last_modified": "2024-10-28"
            },
            {
                "id": 4,
                "name": "ME-ASM-2024-002",
                "title": "外壳组件装配工艺",
                "type": "mechanical",
                "type_label": "机械安装",
                "version": "v2.1",
                "steps": 10,
                "models": ["Edge Detection Standard", "Component Position Check"],
                "status": "draft",
                "status_label": "草稿",
                "last_modified": "2024-11-01"
            },
            {
                "id": 5,
                "name": "PCB-ASM-2024-016",
                "title": "接口板PCB装配工艺",
                "type": "pcb",
                "type_label": "PCB安装",
                "version": "v1.9",
                "steps": 6,
                "models": ["PCB Defect Detection"],
                "status": "active",
                "status_label": "已发布",
                "last_modified": "2024-10-30"
            }
        ]
        
        # Create and add cards in single column
        cards_layout = QGridLayout()
        cards_layout.setSpacing(15)
        cards_layout.setContentsMargins(20, 20, 20, 20)

        for index, process_data in enumerate(processes_data):
            card = ProcessCard(process_data)
            cards_layout.addWidget(card, index, 0)

        # Add stretch to push cards up
        cards_layout.setRowStretch(len(processes_data), 1)

        cards_container.setLayout(cards_layout)

        scroll_area.setWidget(cards_container)
        layout.addWidget(scroll_area)