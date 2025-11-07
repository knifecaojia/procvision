"""
Process information page for the industrial vision system.
"""

import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, 
    QScrollArea, QWidget, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class ProcessCard(QFrame):
    """Process card widget to display process information."""
    
    def __init__(self, process_data, parent=None):
        super().__init__(parent)
        self.setObjectName("processCard")
        self.process_data = process_data
        self.init_ui()
        
    def init_ui(self):
        """Initialize the process card UI."""
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
        
        start_btn = QPushButton("启动工艺")
        start_btn.setObjectName("startButton")
        
        edit_btn = QPushButton("编辑")
        edit_btn.setObjectName("editButton")
        
        actions_layout.addWidget(view_btn)
        actions_layout.addWidget(start_btn)
        actions_layout.addWidget(edit_btn)
        
        layout.addLayout(actions_layout)


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
        
        # Control section
        control_frame = QFrame()
        control_frame.setObjectName("controlFrame")
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(15)
        
        # Product selection
        product_layout = QHBoxLayout()
        product_label = QLabel("产品:")
        product_label.setObjectName("controlLabel")
        product_combo = QComboBox()
        product_combo.addItems(["产品A", "产品B", "产品C"])
        product_combo.setObjectName("productCombo")
        product_layout.addWidget(product_label)
        product_layout.addWidget(product_combo)
        
        # Process selection
        process_layout = QHBoxLayout()
        process_label = QLabel("工艺:")
        process_label.setObjectName("controlLabel")
        process_combo = QComboBox()
        process_combo.addItems(["工艺1", "工艺2", "工艺3"])
        process_combo.setObjectName("processCombo")
        process_layout.addWidget(process_label)
        process_layout.addWidget(process_combo)
        
        # Action buttons
        refresh_btn = QPushButton("刷新")
        refresh_btn.setObjectName("refreshButton")
        refresh_btn.setFixedHeight(36)
        
        export_btn = QPushButton("导出")
        export_btn.setObjectName("exportButton")
        export_btn.setFixedHeight(36)
        
        control_layout.addLayout(product_layout)
        control_layout.addLayout(process_layout)
        control_layout.addStretch()
        control_layout.addWidget(refresh_btn)
        control_layout.addWidget(export_btn)
        
        layout.addWidget(control_frame)
        
        # Process cards in scroll area
        scroll_area = QScrollArea()
        scroll_area.setObjectName("processScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container for cards
        cards_container = QWidget()
        cards_container.setObjectName("cardsContainer")
        cards_layout = QVBoxLayout(cards_container)
        cards_layout.setSpacing(15)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        
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
        
        # Create and add cards
        for process_data in processes_data:
            card = ProcessCard(process_data)
            cards_layout.addWidget(card)
        
        cards_layout.addStretch()
        
        scroll_area.setWidget(cards_container)
        layout.addWidget(scroll_area)