"""
Assembly guidance and inspection page for the industrial vision system.
"""

import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QGridLayout, QComboBox
)
from PySide6.QtCore import Qt
import json
from pathlib import Path
from src.services.data_service import DataService
from ..components.process_card import ProcessCard
from ..components.pagination_widget import PaginationWidget
from ..windows.process_execution_window import ProcessExecutionWindow

logger = logging.getLogger(__name__)


class ProcessPage(QFrame):
    """Assembly guidance and inspection page implementation."""

    def __init__(self, parent=None, camera_service=None):
        super().__init__(parent)
        self.setObjectName("processPage")
        self.camera_service = camera_service
        self.data_service = DataService()
        
        # Pagination state
        self.current_page = 1
        self.page_size = 5 # Show 5 per page
        self.total_pages = 1
        self.current_status_filter = None # None means "All"
        
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
        
        # Filter ComboBox
        self.status_filter = QComboBox()
        self.status_filter.setObjectName("processFilterCombo")
        self.status_filter.addItem("全部", None)
        self.status_filter.addItem("待执行", "1")
        self.status_filter.addItem("执行中", "2")
        self.status_filter.addItem("已完成", "3")
        self.status_filter.setFixedWidth(120)
        self.status_filter.currentIndexChanged.connect(self._on_filter_changed)
        header_layout.addWidget(self.status_filter)
        
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
                
        # Fetch data
        result = self.data_service.get_work_orders(
            self.current_page, 
            self.page_size,
            status=self.current_status_filter
        )
        items = result.get("items", [])
        self.total_pages = result.get("total_pages", 1)
        
        # Update cards
        for index, process_data in enumerate(items):
            card = ProcessCard(process_data)
            card.start_process_clicked.connect(self.on_start_process)
            self.cards_layout.addWidget(card, index, 0)
            
        # Add stretch
        if items:
            self.cards_layout.setRowStretch(len(items), 1)
            
        # Update pagination widget
        self.pagination.set_total_pages(self.total_pages)
        self.pagination.set_current_page(self.current_page)

    def _on_filter_changed(self, index):
        """Handle filter change."""
        self.current_status_filter = self.status_filter.currentData()
        self.current_page = 1 # Reset to first page
        self.load_data()

    def _on_page_changed(self, page):
        """Handle page change from pagination widget."""
        self.current_page = page
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
