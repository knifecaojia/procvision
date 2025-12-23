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

        # Title: Process Name
        process_name = self.process_data.get("process_name", "Unknown Process")
        title_label = QLabel(process_name)
        title_label.setObjectName("cardTitle")

        # ID: Work Order Code
        work_order_code = self.process_data.get("work_order_code", "N/A")
        craft_version = self.process_data.get("craft_version", "N/A")
        id_label = QLabel(f"工单 {work_order_code} · 版本 {craft_version}")
        id_label.setObjectName("cardId")

        title_layout.addWidget(title_label)
        title_layout.addWidget(id_label)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        # Status Badge
        status_map = {"1": "待执行", "2": "执行中", "3": "已完成"}
        status_code = self.process_data.get("status", "1")
        status_text = status_map.get(status_code, "未知状态")
        status_badge = QLabel(status_text)
        status_badge.setObjectName("statusBadge") # Reusing statusBadge style
        # Add a property for potential styling differentiation
        status_badge.setProperty("status", status_code) 
        header_layout.addWidget(status_badge)

        layout.addLayout(header_layout)

        # Info grid
        info_grid = QGridLayout()
        info_grid.setSpacing(8)
        info_grid.setObjectName("infoGrid")

        # Steps Count
        steps_frame = QFrame()
        steps_frame.setObjectName("infoFrame")
        steps_layout = QVBoxLayout(steps_frame)
        steps_layout.setContentsMargins(8, 8, 8, 8)
        steps_label = QLabel("工艺步骤")
        steps_label.setObjectName("infoLabel")
        step_infos = self.process_data.get("step_infos", [])
        steps_value = QLabel(f"{len(step_infos)} 步")
        steps_value.setObjectName("infoValue")
        steps_layout.addWidget(steps_label)
        steps_layout.addWidget(steps_value)

        # Worker
        worker_frame = QFrame()
        worker_frame.setObjectName("infoFrame")
        worker_layout = QVBoxLayout(worker_frame)
        worker_layout.setContentsMargins(8, 8, 8, 8)
        worker_label = QLabel("操作员")
        worker_label.setObjectName("infoLabel")
        worker_name = self.process_data.get("worker_name", "Unknown")
        worker_value = QLabel(worker_name)
        worker_value.setObjectName("infoValue")
        worker_layout.addWidget(worker_label)
        worker_layout.addWidget(worker_value)

        # Algorithm
        algo_frame = QFrame()
        algo_frame.setObjectName("infoFrame")
        algo_layout = QVBoxLayout(algo_frame)
        algo_layout.setContentsMargins(8, 8, 8, 8)
        algo_label = QLabel("算法模型")
        algo_label.setObjectName("infoLabel")
        algo_name = self.process_data.get("algorithm_name", "Unknown")
        algo_value = QLabel(algo_name)
        algo_value.setObjectName("infoValue")
        algo_layout.addWidget(algo_label)
        algo_layout.addWidget(algo_value)

        info_grid.addWidget(steps_frame, 0, 0)
        info_grid.addWidget(worker_frame, 0, 1)
        info_grid.addWidget(algo_frame, 0, 2)

        layout.addLayout(info_grid)

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
        # Normalize data for the execution window
        # execution window expects: name, version, steps, summary, pid
        
        # Mapping from work_order data to execution data
        normalized = {
            "name": self.process_data.get("process_name", ""),
            "title": self.process_data.get("process_name", ""),
            "version": self.process_data.get("craft_version", ""),
            "steps": len(self.process_data.get("step_infos", [])),
            "algorithm_name": self.process_data.get("algorithm_name", ""),
            "algorithm_version": self.process_data.get("algorithm_version", ""),
            "summary": f"Work Order: {self.process_data.get('work_order_code')}",
            "steps_detail": self.process_data.get("step_infos", []),
            "pid": self.process_data.get("work_order_code", None),
            # Pass original data too just in case
            "raw_work_order": self.process_data
        }
        
        logger.info(f"Start process clicked for: {normalized['name']}")
        self.start_process_clicked.emit(normalized)
