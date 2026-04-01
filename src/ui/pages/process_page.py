"""
Assembly guidance and inspection page for the industrial vision system.
"""

import logging
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QGridLayout
)
from PySide6.QtCore import Qt
import json
from pathlib import Path
from src.services.data_service import DataService
from src.services.algorithm_manager import AlgorithmManager
from ..components.process_card import ProcessCard
from ..components.pagination_widget import PaginationWidget
from ..windows.process_execution_window import ProcessExecutionWindow
from ..windows.task_filter_window import TaskFilterWindow

logger = logging.getLogger(__name__)


class ProcessPage(QFrame):
    """Assembly guidance and inspection page implementation."""

    def __init__(self, parent=None, camera_service=None):
        super().__init__(parent)
        self.setObjectName("processPage")
        self.camera_service = camera_service
        self.data_service = DataService()
        self.algorithm_manager = AlgorithmManager()
        
        # Pagination state
        self.current_page = 1
        self.page_size = 5
        self.total_pages = 1
        
        # Advanced filter state
        self.current_filters: Optional[Dict[str, Any]] = None
        self.filter_window: Optional[TaskFilterWindow] = None
        
        self.init_ui()
        self.load_data()
        
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
        
        title_label = QLabel("装配引导与检测")
        title_label.setObjectName("processTitle")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Advanced filter button
        self.filter_btn = QPushButton("高级过滤")
        self.filter_btn.setObjectName("advancedFilterButton")
        self.filter_btn.setFixedSize(100, 36)
        self.filter_btn.clicked.connect(self._on_filter_clicked)
        header_layout.addWidget(self.filter_btn)
        
        layout.addWidget(header_frame)
        
        # Process cards in scroll area
        scroll_area = QScrollArea()
        scroll_area.setObjectName("processScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container for cards
        self.cards_container = QWidget()
        self.cards_container.setObjectName("cardsContainer")
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(15)
        self.cards_layout.setContentsMargins(20, 20, 20, 20)
        
        self.cards_container.setLayout(self.cards_layout)

        scroll_area.setWidget(self.cards_container)
        layout.addWidget(scroll_area)
        
        # Pagination Widget
        self.pagination = PaginationWidget()
        self.pagination.page_changed.connect(self._on_page_changed)
        layout.addWidget(self.pagination, 0, Qt.AlignmentFlag.AlignCenter)

    def load_data(self):
        """Load work orders from data service."""
        # Clear existing
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Fetch data based on filter mode
        if self.current_filters:
            result = self.data_service.search_work_orders(
                self.current_filters,
                page=self.current_page,
                page_size=self.page_size
            )
        else:
            result = self.data_service.get_work_orders(
                self.current_page, 
                self.page_size,
                status=None
            )
            
        items = result.get("items", [])
        self.total_pages = result.get("total_pages", 1)
        
        # Update cards
        for index, process_data in enumerate(items):
            # Check algorithm deployment status
            algo_code = process_data.get("algorithm_code", "")
            algo_name = process_data.get("algorithm_name", "")
            algo_version = process_data.get("algorithm_version", "")
            
            deploy_status = self.algorithm_manager.check_deployment_status(
                algo_name, algo_version, algo_code
            )
            process_data["deployment_status"] = deploy_status
            
            card = ProcessCard(process_data)
            card.start_process_clicked.connect(self.on_start_process)
            self.cards_layout.addWidget(card, index, 0)
            
        # Add stretch
        if items:
            self.cards_layout.setRowStretch(len(items), 1)
            
        # Update pagination widget
        self.pagination.set_total_pages(self.total_pages)
        self.pagination.set_current_page(self.current_page)

    def _on_filter_clicked(self):
        """Handle advanced filter button click."""
        self.filter_window = TaskFilterWindow(self, self.current_filters)
        self.filter_window.filter_applied.connect(self._on_filter_applied)
        self.filter_window.exec()

    def _on_filter_applied(self, filters: Dict[str, Any]):
        """Handle filter applied from TaskFilterWindow."""
        self.current_filters = filters
        pagination = filters.get("pagination", {})
        self.current_page = pagination.get("page", 1)
        self.load_data()

    def _on_page_changed(self, page):
        """Handle page change from pagination widget."""
        self.current_page = page
        if self.current_filters:
            self.current_filters["pagination"] = {
                "page": page,
                "page_size": self.page_size,
            }
        self.load_data()

    def on_start_process(self, process_data: dict):
        """Handle start process signal from process card."""
        logger.info(f"Launching process execution window for: {process_data.get('process_name', 'Unknown')}")

        # Create and show process execution window with camera service
        self.execution_window = ProcessExecutionWindow(
            process_data,
            None,
            camera_service=self.camera_service
        )
        self.execution_window.show_centered()

        logger.info("Process execution window launched")
