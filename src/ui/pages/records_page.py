"""
Work records page for the industrial vision system.
"""

import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit
)
from PySide6.QtCore import Qt

from ..components.records_table import RecordsTableWidget

logger = logging.getLogger(__name__)


class RecordsPage(QFrame):
    """Work records page implementation aligned with the records table spec."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("recordsPage")

        # State for filtering and display
        self.search_term = ""
        self.filter_status = "all"
        self.all_records = []
        self.filtered_records = []

        self.setup_colors()
        self.init_ui()
        self.load_sample_data()

    # --------------------------------------------------------------------- UI
    def init_ui(self):
        """Initialize the records page UI."""
        self.setStyleSheet(f"background-color: {self.color_surface_darker};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._create_title_bar())
        layout.addWidget(self._create_filter_bar())
        layout.addWidget(self._create_table_section(), stretch=1)

    def _create_title_bar(self):
        """Create the title bar per spec."""
        frame = QFrame()
        frame.setObjectName("recordsTitleBar")
        frame.setStyleSheet(
            "QFrame#recordsTitleBar {"
            f"background-color: {self.color_surface};"
            f"border-bottom: 1px solid {self.color_border_subtle};"
            "}"
        )

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignVCenter)

        # Left: icon + title
        left_container = QHBoxLayout()
        left_container.setSpacing(16)

        icon_frame = QFrame()
        icon_frame.setFixedSize(44, 44)
        icon_frame.setStyleSheet(
            f"background-color: {self.color_hover_orange}; border-radius: 12px;"
        )
        icon_label = QLabel("WR", icon_frame)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("color: white; font-weight: 700;")

        text_container = QVBoxLayout()
        text_container.setContentsMargins(0, 0, 0, 0)
        text_container.setSpacing(4)

        title_label = QLabel("工作记录")
        title_label.setObjectName("recordsTitleLabel")
        title_label.setStyleSheet(
            f"color: {self.color_text_primary}; font-size: 20px; font-weight: 700;"
        )

        self.subtitle_label = QLabel("Work Records - 0 条记录")
        self.subtitle_label.setObjectName("recordsSubtitleLabel")
        self.subtitle_label.setStyleSheet(
            f"color: {self.color_text_muted}; font-size: 13px;"
        )

        text_container.addWidget(title_label)
        text_container.addWidget(self.subtitle_label)

        left_container.addWidget(icon_frame)
        left_container.addLayout(text_container)

        layout.addLayout(left_container, stretch=1)

        # Right: action buttons
        button_row = QHBoxLayout()
        button_row.setSpacing(12)

        date_btn = QPushButton("选择日期")
        date_btn.setFixedHeight(38)
        date_btn.setCursor(Qt.PointingHandCursor)
        date_btn.setStyleSheet(self._secondary_button_style())
        date_btn.clicked.connect(self.on_select_date)

        export_btn = QPushButton("导出报表")
        export_btn.setFixedHeight(38)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.setStyleSheet(self._primary_button_style())
        export_btn.clicked.connect(self.on_export)

        button_row.addWidget(date_btn)
        button_row.addWidget(export_btn)

        layout.addLayout(button_row)

        return frame

    def _create_filter_bar(self):
        """Create the search and filter bar."""
        frame = QFrame()
        frame.setObjectName("recordsFilterBar")
        frame.setStyleSheet(
            "QFrame#recordsFilterBar {"
            f"background-color: {self.color_surface_dark};"
            f"border-bottom: 1px solid {self.color_border_subtle};"
            "}"
        )

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignVCenter)

        # Search input with icon
        search_container = QFrame()
        search_container.setObjectName("recordsSearchContainer")
        search_container.setStyleSheet(
            "QFrame#recordsSearchContainer {"
            f"background-color: {self.color_surface_darker};"
            f"border: 1px solid {self.color_border_subtle};"
            "border-radius: 8px;"
            "}"
        )
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(12, 6, 12, 6)
        search_layout.setSpacing(8)

        search_icon = QLabel("🔍")
        search_icon.setStyleSheet(f"color: {self.color_text_muted}; font-size: 14px;")

        self.search_input = QLineEdit()
        self.search_input.setObjectName("recordsSearchInput")
        self.search_input.setPlaceholderText("搜索记录编号、产品SN或工艺名称...")
        self.search_input.setStyleSheet(
            f"border: none; background: transparent; color: {self.color_text_primary}; font-size: 14px;"
        )
        self.search_input.textChanged.connect(self.on_search_changed)

        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input)
        layout.addWidget(search_container, stretch=1)

        # Status filter combo
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.setObjectName("statusFilterCombo")
        self.status_filter_combo.addItem("所有状态", "all")
        self.status_filter_combo.addItem("OK", "ok")
        self.status_filter_combo.addItem("NG", "ng")
        self.status_filter_combo.addItem("条件通过", "conditional")
        self.status_filter_combo.setFixedWidth(180)
        self.status_filter_combo.setStyleSheet(
            "QComboBox#statusFilterCombo {"
            f"background-color: {self.color_surface_darker};"
            f"border: 1px solid {self.color_border_subtle};"
            f"color: {self.color_text_primary};"
            "border-radius: 8px;"
            "padding: 6px 10px;"
            "}"
            "QComboBox QAbstractItemView {"
            f"background-color: {self.color_surface};"
            f"color: {self.color_text_primary};"
            f"border: 1px solid {self.color_border_subtle};"
            "selection-background-color: #2a2a2a;"
            "}"
        )
        self.status_filter_combo.currentIndexChanged.connect(self.on_status_changed)
        layout.addWidget(self.status_filter_combo)

        return frame

    def _create_table_section(self):
        """Create the table container section."""
        frame = QFrame()
        frame.setObjectName("recordsContentFrame")
        frame.setStyleSheet(
            "QFrame#recordsContentFrame {"
            f"background-color: {self.color_surface_darker};"
            "}"
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(0)

        self.table_widget = RecordsTableWidget()
        self.table_widget.get_table().view_detail.connect(self.on_view_detail)
        layout.addWidget(self.table_widget, stretch=1)

        return frame

    def _primary_button_style(self):
        return (
            "QPushButton {"
            f"background-color: {self.color_hover_orange};"
            "border: none;"
            "color: white;"
            "border-radius: 8px;"
            "font-weight: 600;"
            "padding: 0 20px;"
            "}"
            "QPushButton:hover {"
            "background-color: #ea580c;"
            "}"
        )

    def _secondary_button_style(self):
        return (
            "QPushButton {"
            "background-color: transparent;"
            f"border: 1px solid {self.color_border_subtle};"
            f"color: {self.color_text_muted};"
            "border-radius: 8px;"
            "font-weight: 600;"
            "padding: 0 20px;"
            "}"
            "QPushButton:hover {"
            "background-color: #2a2a2a;"
            "color: white;"
            "}"
        )

    # --------------------------------------------------------------- Data/State
    def setup_colors(self):
        """Setup dark mode color palette from config."""
        try:
            from ...core.config import get_config
            config = get_config()
            colors = config.ui.colors

            self.color_deep_graphite = colors.get('deep_graphite', '#1A1D23')
            self.color_steel_grey = colors.get('steel_grey', '#1F232B')
            self.color_dark_border = colors.get('dark_border', '#242831')
            self.color_arctic_white = colors.get('arctic_white', '#F2F4F8')
            self.color_cool_grey = colors.get('cool_grey', '#8C92A0')
            self.color_hover_orange = colors.get('hover_orange', '#FF8C32')
            self.color_success_green = colors.get('success_green', '#3CC37A')
            self.color_error_red = colors.get('error_red', '#E85454')
            self.color_warning_yellow = colors.get('warning_yellow', '#FFB347')
            self.color_surface = colors.get('surface', '#252525')
            self.color_surface_dark = colors.get('surface_dark', '#1F1F1F')
            self.color_surface_darker = colors.get('surface_darker', '#1A1A1A')
            self.color_border_subtle = colors.get('border_subtle', '#3A3A3A')
            self.color_text_primary = colors.get('text_primary', '#FFFFFF')
            self.color_text_muted = colors.get('text_muted', '#9CA3AF')
        except Exception:
            # Fallback defaults
            self.color_deep_graphite = "#1A1D23"
            self.color_steel_grey = "#1F232B"
            self.color_dark_border = "#242831"
            self.color_arctic_white = "#F2F4F8"
            self.color_cool_grey = "#8C92A0"
            self.color_hover_orange = "#FF8C32"
            self.color_success_green = "#3CC37A"
            self.color_error_red = "#E85454"
            self.color_warning_yellow = "#FFB347"
            self.color_surface = "#252525"
            self.color_surface_dark = "#1F1F1F"
            self.color_surface_darker = "#1A1A1A"
            self.color_border_subtle = "#3A3A3A"
            self.color_text_primary = "#FFFFFF"
            self.color_text_muted = "#9CA3AF"

    def load_sample_data(self):
        """Load sample records data."""
        self.all_records = [
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

        self.apply_filters()

    # --------------------------------------------------------- Event handlers
    def on_search_changed(self, text):
        self.search_term = text.strip()
        self.apply_filters()

    def on_status_changed(self):
        self.filter_status = self.status_filter_combo.currentData()
        self.apply_filters()

    def on_select_date(self):
        logger.info("Date selection triggered - pending implementation")

    def on_export(self):
        logger.info("Exporting %d filtered records", len(self.filtered_records))
        # In real implementation, would export data to file

    def on_view_detail(self, record_id):
        logger.info("Viewing detail for record %s", record_id)
        # In real implementation, would open detail dialog

    # ---------------------------------------------------------- Data helpers
    def apply_filters(self):
        """Apply search and status filters to the data set."""
        search_lower = self.search_term.lower()

        def matches_search(record):
            if not search_lower:
                return True
            targets = [
                record.get("record_id", ""),
                record.get("product_sn", ""),
                record.get("process_title", "")
            ]
            return any(search_lower in (target or "").lower() for target in targets)

        def matches_status(record):
            if self.filter_status == "all":
                return True
            return record.get("status") == self.filter_status

        self.filtered_records = [
            record for record in self.all_records
            if matches_search(record) and matches_status(record)
        ]

        self.table_widget.set_records(self.filtered_records)
        self.update_record_summary(len(self.filtered_records))

    def update_record_summary(self, record_count):
        """Update the subtitle with the current record count."""
        self.subtitle_label.setText(f"Work Records - {record_count} 条记录")
