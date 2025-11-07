"""
Work records page for the industrial vision system.
"""

import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, 
    QScrollArea, QWidget, QGridLayout, QLineEdit, QDateEdit, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import QDate, Qt

logger = logging.getLogger(__name__)


class RecordCard(QFrame):
    """Record card widget to display work record information."""
    
    def __init__(self, record_data, parent=None):
        super().__init__(parent)
        self.setObjectName("recordCard")
        self.record_data = record_data
        self.init_ui()
        
    def init_ui(self):
        """Initialize the record card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Header with title and status
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title section
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        title_label = QLabel(self.record_data["process_title"])
        title_label.setObjectName("cardTitle")
        
        id_label = QLabel(f"{self.record_data['process_name']} | 记录编号: {self.record_data['record_id']}")
        id_label.setObjectName("cardId")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(id_label)
        
        # Status badge
        status_badge = QLabel(self.record_data["status_label"])
        status_badge.setObjectName(f"statusBadge_{self.record_data['status']}")
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addWidget(status_badge)
        
        layout.addLayout(header_layout)
        
        # Info grid
        info_grid = QGridLayout()
        info_grid.setSpacing(10)
        info_grid.setObjectName("infoGrid")
        
        # Product SN
        sn_frame = QFrame()
        sn_frame.setObjectName("infoFrame")
        sn_layout = QVBoxLayout(sn_frame)
        sn_layout.setContentsMargins(8, 8, 8, 8)
        sn_label = QLabel("产品SN")
        sn_label.setObjectName("infoLabel")
        sn_value = QLabel(self.record_data["product_sn"])
        sn_value.setObjectName("infoValue")
        sn_layout.addWidget(sn_label)
        sn_layout.addWidget(sn_value)
        
        # Operator
        operator_frame = QFrame()
        operator_frame.setObjectName("infoFrame")
        operator_layout = QVBoxLayout(operator_frame)
        operator_layout.setContentsMargins(8, 8, 8, 8)
        operator_label = QLabel("操作员")
        operator_label.setObjectName("infoLabel")
        operator_value = QLabel(self.record_data["operator"])
        operator_value.setObjectName("infoValue")
        operator_layout.addWidget(operator_label)
        operator_layout.addWidget(operator_value)
        
        # Workstation
        workstation_frame = QFrame()
        workstation_frame.setObjectName("infoFrame")
        workstation_layout = QVBoxLayout(workstation_frame)
        workstation_layout.setContentsMargins(8, 8, 8, 8)
        workstation_label = QLabel("工位")
        workstation_label.setObjectName("infoLabel")
        workstation_value = QLabel(self.record_data["workstation"])
        workstation_value.setObjectName("infoValue")
        workstation_layout.addWidget(workstation_label)
        workstation_layout.addWidget(workstation_value)
        
        # Duration
        duration_frame = QFrame()
        duration_frame.setObjectName("infoFrame")
        duration_layout = QVBoxLayout(duration_frame)
        duration_layout.setContentsMargins(8, 8, 8, 8)
        duration_label = QLabel("耗时")
        duration_label.setObjectName("infoLabel")
        duration_value = QLabel(self.record_data["duration"])
        duration_value.setObjectName("infoValue")
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(duration_value)
        
        info_grid.addWidget(sn_frame, 0, 0)
        info_grid.addWidget(operator_frame, 0, 1)
        info_grid.addWidget(workstation_frame, 1, 0)
        info_grid.addWidget(duration_frame, 1, 1)
        
        layout.addLayout(info_grid)
        
        # Defects list (if any)
        if self.record_data["defects"]:
            defects_title = QLabel("缺陷信息：")
            defects_title.setObjectName("defectsTitle")
            layout.addWidget(defects_title)
            
            defects_layout = QHBoxLayout()
            defects_layout.setSpacing(5)
            defects_layout.setContentsMargins(0, 0, 0, 0)
            
            for defect in self.record_data["defects"]:
                defect_badge = QLabel(defect)
                defect_badge.setObjectName("defectBadge")
                defects_layout.addWidget(defect_badge)
            
            defects_layout.addStretch()
            layout.addLayout(defects_layout)
        
        # Time info
        time_layout = QHBoxLayout()
        time_layout.setSpacing(15)
        
        start_label = QLabel(f"开始: {self.record_data['start_time']}")
        start_label.setObjectName("timeLabel")
        
        end_label = QLabel(f"结束: {self.record_data['end_time']}")
        end_label.setObjectName("timeLabel")
        
        time_layout.addWidget(start_label)
        time_layout.addWidget(end_label)
        time_layout.addStretch()
        
        layout.addLayout(time_layout)
        
        # Action button
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        detail_btn = QPushButton("详情")
        detail_btn.setObjectName("detailButton")
        detail_btn.setFixedWidth(80)
        
        action_layout.addWidget(detail_btn)
        
        layout.addLayout(action_layout)


class RecordsPage(QFrame):
    """Work records page implementation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("recordsPage")
        self.init_ui()
        
    def init_ui(self):
        """Initialize the records page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header section
        header_frame = QFrame()
        header_frame.setObjectName("recordsHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("工作记录")
        title_label.setObjectName("recordsTitle")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
        
        # Filter section
        filter_frame = QFrame()
        filter_frame.setObjectName("filterFrame")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(15)
        
        # Date range
        date_layout = QHBoxLayout()
        date_label = QLabel("日期:")
        date_label.setObjectName("filterLabel")
        
        start_date = QDateEdit()
        start_date.setDate(QDate.currentDate().addDays(-7))
        start_date.setDisplayFormat("yyyy-MM-dd")
        start_date.setObjectName("dateEdit")
        
        to_label = QLabel("至")
        to_label.setObjectName("filterLabel")
        
        end_date = QDateEdit()
        end_date.setDate(QDate.currentDate())
        end_date.setDisplayFormat("yyyy-MM-dd")
        end_date.setObjectName("dateEdit")
        
        date_layout.addWidget(date_label)
        date_layout.addWidget(start_date)
        date_layout.addWidget(to_label)
        date_layout.addWidget(end_date)
        
        # Product filter
        product_layout = QHBoxLayout()
        product_label = QLabel("产品:")
        product_label.setObjectName("filterLabel")
        product_combo = QComboBox()
        product_combo.addItems(["全部", "产品A", "产品B", "产品C"])
        product_combo.setObjectName("filterCombo")
        product_layout.addWidget(product_label)
        product_layout.addWidget(product_combo)
        
        # Search
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_label.setObjectName("filterLabel")
        search_input = QLineEdit()
        search_input.setPlaceholderText("输入产品名称或批次号")
        search_input.setObjectName("searchInput")
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_input)
        
        # Action buttons
        refresh_btn = QPushButton("刷新")
        refresh_btn.setObjectName("refreshButton")
        refresh_btn.setFixedHeight(36)
        
        export_btn = QPushButton("导出")
        export_btn.setObjectName("exportButton")
        export_btn.setFixedHeight(36)
        
        filter_layout.addLayout(date_layout)
        filter_layout.addLayout(product_layout)
        filter_layout.addLayout(search_layout)
        filter_layout.addStretch()
        filter_layout.addWidget(refresh_btn)
        filter_layout.addWidget(export_btn)
        
        layout.addWidget(filter_frame)
        
        # Records cards in scroll area
        scroll_area = QScrollArea()
        scroll_area.setObjectName("recordsScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container for cards
        cards_container = QWidget()
        cards_container.setObjectName("cardsContainer")
        cards_layout = QVBoxLayout(cards_container)
        cards_layout.setSpacing(15)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sample record data
        records_data = [
            {
                "id": 1,
                "record_id": "REC-2024110701234",
                "process_name": "ME-ASM-2024-001",
                "process_title": "机械底座装配工艺",
                "product_sn": "SN20241107001",
                "order_no": "ORD-2024-1105",
                "operator": "张三",
                "workstation": "A01",
                "status": "ok",
                "status_label": "OK",
                "start_time": "2024-11-07 09:15:23",
                "end_time": "2024-11-07 09:28:45",
                "duration": "13min 22s",
                "defects": []
            },
            {
                "id": 2,
                "record_id": "REC-2024110701235",
                "process_name": "PCB-ASM-2024-015",
                "process_title": "主控板PCB装配工艺",
                "product_sn": "SN20241107002",
                "order_no": "ORD-2024-1105",
                "operator": "李四",
                "workstation": "B02",
                "status": "ng",
                "status_label": "NG",
                "start_time": "2024-11-07 09:30:15",
                "end_time": "2024-11-07 09:42:30",
                "duration": "12min 15s",
                "defects": ["焊点缺失", "PCB位置偏移"]
            },
            {
                "id": 3,
                "record_id": "REC-2024110701236",
                "process_name": "PKG-STD-2024-003",
                "process_title": "标准包装工艺流程",
                "product_sn": "SN20241107003",
                "order_no": "ORD-2024-1106",
                "operator": "王五",
                "workstation": "C01",
                "status": "conditional",
                "status_label": "条件通过",
                "start_time": "2024-11-07 10:05:00",
                "end_time": "2024-11-07 10:12:18",
                "duration": "7min 18s",
                "defects": ["标签轻微歪斜"]
            },
            {
                "id": 4,
                "record_id": "REC-2024110701237",
                "process_name": "ME-ASM-2024-001",
                "process_title": "机械底座装配工艺",
                "product_sn": "SN20241107004",
                "order_no": "ORD-2024-1105",
                "operator": "张三",
                "workstation": "A01",
                "status": "ok",
                "status_label": "OK",
                "start_time": "2024-11-07 10:30:45",
                "end_time": "2024-11-07 10:43:20",
                "duration": "12min 35s",
                "defects": []
            },
            {
                "id": 5,
                "record_id": "REC-2024110701238",
                "process_name": "PCB-ASM-2024-016",
                "process_title": "接口板PCB装配工艺",
                "product_sn": "SN20241107005",
                "order_no": "ORD-2024-1106",
                "operator": "赵六",
                "workstation": "B03",
                "status": "ok",
                "status_label": "OK",
                "start_time": "2024-11-07 11:00:10",
                "end_time": "2024-11-07 11:08:55",
                "duration": "8min 45s",
                "defects": []
            }
        ]
        
        # Create and add cards
        for record_data in records_data:
            card = RecordCard(record_data)
            cards_layout.addWidget(card)
        
        cards_layout.addStretch()
        
        scroll_area.setWidget(cards_container)
        layout.addWidget(scroll_area)