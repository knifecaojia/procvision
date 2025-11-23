"""
Work records page for the industrial vision system.
"""

import logging
import math
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit
)
from PySide6.QtCore import Qt

from ..components.records_table import RecordsTableWidget

logger = logging.getLogger(__name__)


class RecordsPage(QFrame):
    """Work records page implementation aligned with the design spec."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("recordsPage")

        # State for filtering and pagination
        self.search_term = ""
        self.filter_status = "all"
        self.page_size = 10
        self.current_page = 1
        self.total_pages = 1
        self.all_records = []
        self.filtered_records = []

        # UI references
        self.subtitle_label = None
        self.pagination_label = None
        self.prev_page_btn = None
        self.next_page_btn = None

        self.setup_colors()
        self.init_ui()
        self.load_sample_data()

    # ------------------------------------------------------------------ UI ----
    def init_ui(self):
        """Initialize the records page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        layout.addWidget(self._create_header_section())
        layout.addWidget(self._create_filter_bar())
        layout.addWidget(self._create_table_section(), stretch=1)

    def _create_header_section(self):
        frame = QFrame()
        frame.setObjectName("recordsHeader")

        header_layout = QVBoxLayout(frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        title_label = QLabel("工作记录")
        title_label.setObjectName("recordsTitleLabel")

        self.subtitle_label = QLabel("Work Records - 0 条记录")
        self.subtitle_label.setObjectName("recordsSubtitleLabel")

        header_layout.addWidget(title_label)
        header_layout.addWidget(self.subtitle_label)

        # Actions row
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 12, 0, 0)
        actions_layout.setSpacing(12)
        actions_layout.addStretch()

        date_btn = QPushButton("选择日期")
        date_btn.setObjectName("recordsSecondaryButton")
        date_btn.setFixedHeight(36)
        date_btn.setCursor(Qt.PointingHandCursor)
        date_btn.clicked.connect(self.on_select_date)

        export_btn = QPushButton("导出报表")
        export_btn.setObjectName("recordsPrimaryButton")
        export_btn.setFixedHeight(36)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self.on_export)

        actions_layout.addWidget(date_btn)
        actions_layout.addWidget(export_btn)
        header_layout.addLayout(actions_layout)

        return frame

    def _create_filter_bar(self):
        frame = QFrame()
        frame.setObjectName("recordsFilterBar")

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignVCenter)

        # Search input
        search_container = QFrame()
        search_container.setObjectName("recordsSearchContainer")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(12, 6, 12, 6)
        search_layout.setSpacing(8)

        search_icon = QLabel("🔍")
        search_icon.setObjectName("recordsSearchIcon")

        self.search_input = QLineEdit()
        self.search_input.setObjectName("recordsSearchInput")
        self.search_input.setPlaceholderText("搜索记录编号、产品SN或工艺名称...")
        self.search_input.textChanged.connect(self.on_search_changed)

        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input)
        layout.addWidget(search_container, stretch=1)

        # Status filter
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.setObjectName("statusFilterCombo")
        self.status_filter_combo.addItem("所有状态", "all")
        self.status_filter_combo.addItem("OK", "ok")
        self.status_filter_combo.addItem("NG", "ng")
        self.status_filter_combo.addItem("条件通过", "conditional")
        self.status_filter_combo.setFixedWidth(180)
        self.status_filter_combo.currentIndexChanged.connect(self.on_status_changed)
        layout.addWidget(self.status_filter_combo)

        return frame

    def _create_table_section(self):
        frame = QFrame()
        frame.setObjectName("recordsContentFrame")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        self.table_widget = RecordsTableWidget()
        self.table_widget.get_table().view_detail.connect(self.on_view_detail)
        layout.addWidget(self.table_widget, stretch=1)

        # Pagination bar
        pagination_frame = QFrame()
        pagination_layout = QHBoxLayout(pagination_frame)
        pagination_layout.setContentsMargins(0, 0, 0, 0)
        pagination_layout.setSpacing(12)

        self.pagination_label = QLabel("第 1/1 页 · 共 0 条记录")
        self.pagination_label.setObjectName("recordsPaginationLabel")

        self.prev_page_btn = QPushButton("上一页")
        self.prev_page_btn.setObjectName("recordsSecondaryButton")
        self.prev_page_btn.setFixedHeight(32)
        self.prev_page_btn.setCursor(Qt.PointingHandCursor)
        self.prev_page_btn.clicked.connect(self.on_prev_page)

        self.next_page_btn = QPushButton("下一页")
        self.next_page_btn.setObjectName("recordsSecondaryButton")
        self.next_page_btn.setFixedHeight(32)
        self.next_page_btn.setCursor(Qt.PointingHandCursor)
        self.next_page_btn.clicked.connect(self.on_next_page)

        pagination_layout.addWidget(self.pagination_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.prev_page_btn)
        pagination_layout.addWidget(self.next_page_btn)

        layout.addWidget(pagination_frame)

        return frame

    # ----------------------------------------------------- Data & State ----
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
        """Generate mock data with 20 records."""
        templates = [
            ("ME-ASM-2024-001", "机械底座装配工艺", "OK", "ok", "A01", []),
            ("PCB-ASM-2024-015", "主控板PCB装配工艺", "NG", "ng", "B02", ["焊点缺失", "PCB位置偏移"]),
            ("PKG-STD-2024-003", "标准包装工艺流程", "条件通过", "conditional", "C01", ["标签轻微歪斜"]),
            ("PCB-ASM-2024-016", "接口板PCB装配工艺", "OK", "ok", "B03", []),
        ]

        records = []
        base_record_id = 1234
        for idx in range(20):
            template = templates[idx % len(templates)]
            process_code, process_title, status_label, status, workstation, defects = template
            record = {
                "id": idx + 1,
                "record_id": f"REC-20241107{base_record_id + idx:04d}",
                "process_name": process_code,
                "process_title": process_title,
                "product_sn": f"SN20241107{idx + 1:03d}",
                "order_no": "ORD-2024-1105" if idx < 10 else "ORD-2024-1106",
                "operator": ["张三", "李四", "王五", "赵六", "钱七"][idx % 5],
                "workstation": workstation,
                "status": status,
                "status_label": status_label,
                "start_time": f"2024-11-07 {9 + (idx // 4):02d}:{10 + (idx * 3) % 50:02d}:15",
                "end_time": f"2024-11-07 {9 + (idx // 4):02d}:{20 + (idx * 3) % 50:02d}:45",
                "duration": f"{8 + (idx % 6)}min {10 + idx % 50}s",
                "defects": defects if status != "ok" else [],
            }
            records.append(record)

        self.all_records = records
        self.apply_filters()

    # -------------------------------------------------------- Interaction ----
    def on_search_changed(self, text):
        self.search_term = text.strip()
        self.current_page = 1
        self.apply_filters()

    def on_status_changed(self):
        self.filter_status = self.status_filter_combo.currentData()
        self.current_page = 1
        self.apply_filters()

    def on_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._refresh_table_view()

    def on_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._refresh_table_view()

    def on_select_date(self):
        logger.info("Date selection triggered - pending implementation")

    def on_export(self):
        logger.info("Exporting %d filtered records", len(self.filtered_records))

    def on_view_detail(self, record_id):
        logger.info("Viewing detail for record %s", record_id)

    # ----------------------------------------------------------- Helpers ----
    def apply_filters(self):
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

        total = len(self.filtered_records)
        self.total_pages = max(1, math.ceil(total / self.page_size)) if total else 1
        self.current_page = min(self.current_page, self.total_pages)

        self._refresh_table_view()
        self.update_record_summary(total)

    def _refresh_table_view(self):
        start = (self.current_page - 1) * self.page_size
        end = start + self.page_size
        page_records = self.filtered_records[start:end]
        self.table_widget.set_records(page_records)
        self._update_pagination_controls()

    def _update_pagination_controls(self):
        total_records = len(self.filtered_records)
        if self.pagination_label:
            self.pagination_label.setText(
                f"第 {self.current_page}/{self.total_pages} 页 · 共 {total_records} 条记录"
            )
        if self.prev_page_btn:
            self.prev_page_btn.setEnabled(self.current_page > 1)
        if self.next_page_btn:
            self.next_page_btn.setEnabled(self.current_page < self.total_pages)

    def update_record_summary(self, record_count):
        """Update the subtitle with the current record count."""
        if self.subtitle_label:
            self.subtitle_label.setText(f"Work Records - {record_count} 条记录")
