"""
Work records table component for the industrial vision system.
"""

import logging
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QPushButton, QFrame, QHBoxLayout, QVBoxLayout, QWidget, QLabel,
    QSizePolicy, QAbstractScrollArea
)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QFont, QColor, QPalette

from ..styles import refresh_widget_styles

logger = logging.getLogger(__name__)


class _DarkPaletteMixin:
    """Provides a shared dark theme palette for records components."""

    def setup_colors(self):
        """Setup dark mode color palette."""
        # Legacy names (kept for compatibility with existing code)
        self.color_deep_graphite = "#1a1d23"
        self.color_steel_grey = "#1f232b"
        self.color_dark_border = "#242831"
        self.color_arctic_white = "#f2f4f8"
        self.color_cool_grey = "#8c92a0"
        self.color_hover_orange = "#ff8c32"
        self.color_amber = "#ffac54"
        self.color_success_green = "#3cc37a"
        self.color_error_red = "#e85454"
        self.color_warning_yellow = "#ffb347"

        # Spec-driven palette
        self.color_surface = "#252525"
        self.color_surface_dark = "#1f1f1f"
        self.color_surface_darker = "#1a1a1a"
        self.color_border_subtle = "#3a3a3a"
        self.color_text_primary = "#f8fafc"
        self.color_text_muted = "#cbd5f5"
        self.color_text_secondary = "#6b7280"
        self.color_badge_orange_bg = "rgba(249, 115, 22, 0.22)"
        self.color_badge_orange_text = "#ffd7b0"
        self.color_badge_orange_border = "rgba(249, 115, 22, 0.6)"
        self.color_badge_green_bg = "rgba(34, 197, 94, 0.20)"
        self.color_badge_green_text = "#aefacb"
        self.color_badge_green_border = "rgba(34, 197, 94, 0.55)"
        self.color_badge_red_bg = "rgba(239, 68, 68, 0.18)"
        self.color_badge_red_text = "#ffb3b3"
        self.color_badge_red_border = "rgba(239, 68, 68, 0.55)"
        self.color_badge_yellow_bg = "rgba(234, 179, 8, 0.24)"
        self.color_badge_yellow_text = "#ffeeb3"
        self.color_badge_yellow_border = "rgba(234, 179, 8, 0.6)"
        self.color_status_conditional_text = "#fb923c"


class BadgeLabel(QLabel):
    """Reusable badge label styled via QSS."""

    def __init__(self, role: str, parent=None):
        super().__init__(parent)
        self.setObjectName("recordsBadge")
        self.setProperty("badgeRole", role)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(28)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    def set_role(self, role: str) -> None:
        self.setProperty("badgeRole", role)
        refresh_widget_styles(self)


class RecordsTable(QTableWidget, _DarkPaletteMixin):
    """Work records table widget."""

    record_selected = Signal(int)  # Signal emitted when a record is selected
    view_detail = Signal(int)  # Signal emitted when view detail button is clicked

    STATUS_STYLES = {
        "ok": {
            "label": "OK",
            "badge_role": "status-ok",
        },
        "ng": {
            "label": "NG",
            "badge_role": "status-ng",
        },
        "conditional": {
            "label": "条件通过",
            "badge_role": "status-conditional",
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("recordsTable")
        self.records_data = []
        self.setup_colors()
        self._palette_reapply = False
        self.init_ui()

    def init_ui(self):
        """Initialize the table UI."""
        self.setColumnCount(8)
        headers = [
            "记录编号", "产品SN", "工艺名称", "操作员",
            "工位", "耗时", "状态", "操作"
        ]
        self.setHorizontalHeaderLabels(headers)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(False)
        self.setSortingEnabled(False)
        self.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContentsOnFirstShow)
        self.setFocusPolicy(Qt.NoFocus)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self._apply_palette()

        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setMinimumSectionSize(80)

        # Column sizing per spec - mix of content-aware and stretch
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 记录编号
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 产品SN
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # 工艺名称
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 操作员
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 工位
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 耗时
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # 状态
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # 操作

        v_header = self.verticalHeader()
        v_header.setVisible(False)
        v_header.setSectionResizeMode(QHeaderView.Fixed)
        v_header.setDefaultSectionSize(84)
        v_header.setMinimumSectionSize(72)

    def _apply_palette(self):
        """Enforce a bright foreground palette so text never falls back to dark defaults."""
        if self._palette_reapply:
            return
        self._palette_reapply = True
        palette = self.palette()
        text_color = QColor(self.color_text_primary)
        base_color = QColor(self.color_surface)
        alt_color = QColor(self.color_surface_dark)

        palette.setColor(QPalette.Base, base_color)
        palette.setColor(QPalette.AlternateBase, alt_color)
        palette.setColor(QPalette.Window, base_color)
        palette.setColor(QPalette.WindowText, text_color)
        palette.setColor(QPalette.Text, text_color)
        palette.setColor(QPalette.Button, base_color)
        palette.setColor(QPalette.ButtonText, text_color)

        self.setPalette(palette)
        if self.viewport() is not None:
            self.viewport().setPalette(palette)
        self._palette_reapply = False

    def changeEvent(self, event):
        """Reapply palette after global style/palette changes."""
        super().changeEvent(event)
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.PaletteChange):
            self._apply_palette()

    def set_records(self, records_data):
        """Set records data and populate the table."""
        self.records_data = records_data or []
        self.populate_table()

    def populate_table(self):
        """Populate the table with records data."""
        self.setRowCount(len(self.records_data))

        for row, record in enumerate(self.records_data):
            self._set_text_item(row, 0, record.get("record_id", ""), monospace=True)
            self._set_text_item(row, 1, record.get("product_sn", ""), monospace=True)
            self.setCellWidget(row, 2, self._create_process_cell(record))
            self._set_text_item(row, 3, record.get("operator", ""), bold=False)
            self.setCellWidget(row, 4, self._create_workstation_badge(record.get("workstation", "")))
            self._set_text_item(row, 5, record.get("duration", ""), bold=False)
            self.setCellWidget(row, 6, self._create_status_cell(record))
            self.setCellWidget(row, 7, self._create_action_button(record.get("id", row)))

    def _set_text_item(self, row, column, text, monospace=False, bold=False):
        """Helper to set a styled QTableWidgetItem."""
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        font = QFont("Source Han Sans SC", 11)
        if monospace:
            font = QFont("Consolas", 11)
        font.setBold(bold)
        item.setFont(font)
        item.setForeground(QColor(self.color_text_primary))
        item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.setItem(row, column, item)

    def _create_process_cell(self, record):
        """Render process title + code with clear hierarchy."""
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(4)

        title_label = QLabel(record.get("process_title", ""))
        title_label.setObjectName("recordsProcessTitle")

        code_label = QLabel(record.get("process_name", ""))
        code_label.setObjectName("recordsProcessCode")

        layout.addWidget(title_label)
        layout.addWidget(code_label)
        return container

    def _create_workstation_badge(self, workstation):
        """Create workstation badge similar to specs."""
        badge = BadgeLabel("workstation")
        badge.setText(workstation or "-")
        wrapper = QWidget()
        wrapper.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.addWidget(badge, alignment=Qt.AlignCenter)
        return wrapper

    def _create_status_cell(self, record):
        """Create status badge + defects text."""
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(4)

        status = record.get("status", "ok")
        status_style = self.STATUS_STYLES.get(status, self.STATUS_STYLES["ok"])
        label_text = record.get("status_label") or status_style["label"]
        badge = BadgeLabel(status_style["badge_role"])
        badge.setText(label_text)

        layout.addWidget(badge, alignment=Qt.AlignLeft)

        defects = record.get("defects", [])
        if defects:
            defects_label = QLabel(", ".join(defects))
            defects_label.setWordWrap(False)  # keep NG reason on a single line so rows don't clip
            defects_label.setObjectName("recordsDefectsLabel")
            layout.addWidget(defects_label, alignment=Qt.AlignLeft)

        return container

    def _create_action_button(self, record_id):
        """Create the 'view detail' button per spec."""
        btn = QPushButton("查看详情")
        btn.setObjectName("recordsActionButton")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(32)
        btn.clicked.connect(lambda: self.view_detail.emit(record_id))

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.addWidget(btn, alignment=Qt.AlignCenter)
        return container

    def get_selected_record_id(self):
        """Get the ID of the currently selected record."""
        current_row = self.currentRow()
        if current_row >= 0 and current_row < len(self.records_data):
            return self.records_data[current_row].get("id")
        return None

    def clear_table(self):
        """Clear the table."""
        self.setRowCount(0)
        self.records_data = []


class RecordsTableWidget(QFrame, _DarkPaletteMixin):
    """Composite widget containing table and controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("recordsTableWidget")
        self.setup_colors()
        self.init_ui()
        self.records_data = []

    def init_ui(self):
        """Initialize the composite widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        container = QFrame()
        container.setObjectName("recordsTableContainer")

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self.table = RecordsTable()
        self.table.setObjectName("recordsTable")
        container_layout.addWidget(self.table, stretch=1)

        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(container, stretch=1)

    def set_records(self, records_data):
        """Set records data to display."""
        self.records_data = records_data
        self.table.set_records(records_data)

    def get_table(self):
        """Get the RecordsTable instance."""
        return self.table
