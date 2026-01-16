"""
Work records page for the industrial vision system.
"""

import html
import logging
import math
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTextBrowser, QApplication
)
from PySide6.QtCore import Qt, QUrl

logger = logging.getLogger(__name__)


class RecordsPage(QFrame):
    """Work records page implementation aligned with the design spec."""

    def __init__(self, parent=None, initial_theme: str = "dark"):
        super().__init__(parent)
        self.setObjectName("recordsPage")

        self.current_theme = initial_theme if initial_theme in {"dark", "light"} else "dark"

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
        self.html_viewer = None

        self.setup_colors(self.current_theme)
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

        self.html_viewer = QTextBrowser()
        self.html_viewer.setObjectName("recordsHtmlViewer")
        self.html_viewer.setOpenExternalLinks(False)
        self.html_viewer.setOpenLinks(False)
        self.html_viewer.setFrameStyle(QFrame.NoFrame)
        try:
            self.html_viewer.setViewportMargins(0, 0, 0, 0)
        except Exception:
            pass
        try:
            self.html_viewer.document().setDocumentMargin(0)
        except Exception:
            pass
        self.html_viewer.anchorClicked.connect(self.on_html_anchor_clicked)
        layout.addWidget(self.html_viewer, stretch=1)

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
    def setup_colors(self, theme_name: str = "dark"):
        """Setup theme color palette from config."""
        theme_name = theme_name if theme_name in {"dark", "light"} else "dark"
        try:
            from ...core.config import get_config
            from ..styles.theme_loader import resolve_theme_colors
            config = get_config()
            base_colors = dict(getattr(getattr(config, "ui", None), "colors", {}) or {})
            colors = resolve_theme_colors(theme_name, base_colors)

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
            if theme_name == "light":
                self.color_deep_graphite = "#F3F4F7"
                self.color_steel_grey = "#FFFFFF"
                self.color_dark_border = "#CED3E5"
                self.color_arctic_white = "#111827"
                self.color_cool_grey = "#4B5563"
                self.color_hover_orange = "#2563EB"
                self.color_success_green = "#22C55E"
                self.color_error_red = "#DC2626"
                self.color_warning_yellow = "#FACC15"
                self.color_surface = "#F9FAFE"
                self.color_surface_dark = "#EEF1F8"
                self.color_surface_darker = "#E0E6F3"
                self.color_border_subtle = "#D1D7E6"
                self.color_text_primary = "#111827"
                self.color_text_muted = "#4B5563"
            else:
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

    def apply_theme(self, theme: str) -> None:
        if theme not in {"dark", "light"}:
            return
        if theme == getattr(self, "current_theme", "dark"):
            return
        self.current_theme = theme
        self.setup_colors(theme)
        self._refresh_table_view()

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

    def on_status_changed(self, _index=None):
        self.filter_status = self.status_filter_combo.currentData()
        self.current_page = 1
        self.apply_filters()

    def on_prev_page(self, _checked=False):
        if self.current_page > 1:
            self.current_page -= 1
            self._refresh_table_view()

    def on_next_page(self, _checked=False):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._refresh_table_view()

    def on_select_date(self, _checked=False):
        logger.info("Date selection triggered - pending implementation")

    def on_export(self, _checked=False):
        html_text = ""
        if self.html_viewer:
            try:
                html_text = self.html_viewer.toHtml()
            except Exception:
                logger.exception("Failed to extract HTML content from viewer")
        if html_text:
            try:
                QApplication.clipboard().setText(html_text)
            except Exception:
                logger.exception("Failed to copy HTML to clipboard")
        logger.info("Export triggered (records=%d, html_size=%d)", len(self.filtered_records), len(html_text))

    def on_view_detail(self, record_id):
        logger.info("Viewing detail for record %s", record_id)

    def on_html_anchor_clicked(self, url: QUrl):
        text = url.toString()
        if text.startswith("detail:"):
            raw = text.split("detail:", 1)[1].strip()
            try:
                record_id = int(raw)
            except ValueError:
                record_id = raw
            self.on_view_detail(record_id)
            return
        logger.info("Unhandled link clicked: %s", text)

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
        if self.html_viewer:
            self.html_viewer.setHtml(self._render_records_table_html(page_records))
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

    def _render_records_table_html(self, records):
        def escape(value):
            return html.escape("" if value is None else str(value), quote=True)

        def badge(text, role):
            return f"<span class='badge badge-{escape(role)}'>{escape(text)}</span>"

        rows = []
        for record in records or []:
            status = record.get("status", "ok")
            status_label = record.get("status_label") or {"ok": "OK", "ng": "NG", "conditional": "条件通过"}.get(status, "OK")
            process_title = record.get("process_title", "")
            process_code = record.get("process_name", "")
            record_id_text = record.get("record_id", "")
            product_sn = record.get("product_sn", "")
            operator = record.get("operator", "")
            workstation = record.get("workstation", "")
            duration = record.get("duration", "")
            row_id = record.get("id", "")

            rows.append(
                "<tr>"
                f"<td><code>{escape(record_id_text)}</code></td>"
                f"<td><code>{escape(product_sn)}</code></td>"
                "<td>"
                f"<div class='process-title'>{escape(process_title)}</div>"
                f"<div class='process-code'>{escape(process_code)}</div>"
                "</td>"
                f"<td>{escape(operator)}</td>"
                f"<td>{badge(workstation or '-', 'workstation')}</td>"
                f"<td>{escape(duration)}</td>"
                f"<td>{badge(status_label, status)}</td>"
                f"<td><a class='action' href='detail:{escape(row_id)}'>查看详情</a></td>"
                "</tr>"
            )

        if not rows:
            table_body = (
                "<div class='empty'>暂无记录</div>"
            )
        else:
            table_body = (
                "<div class='table-wrap'>"
                "<table class='records-table' width='100%' cellspacing='0' cellpadding='0'>"
                "<colgroup>"
                "<col style='width:16%;' />"
                "<col style='width:14%;' />"
                "<col style='width:28%;' />"
                "<col style='width:10%;' />"
                "<col style='width:8%;' />"
                "<col style='width:10%;' />"
                "<col style='width:8%;' />"
                "<col style='width:6%;' />"
                "</colgroup>"
                "<thead>"
                "<tr>"
                "<th>记录编号</th>"
                "<th>产品SN</th>"
                "<th>工艺名称</th>"
                "<th>操作员</th>"
                "<th>工位</th>"
                "<th>耗时</th>"
                "<th>状态</th>"
                "<th>操作</th>"
                "</tr>"
                "</thead>"
                f"<tbody>{''.join(rows)}</tbody>"
                "</table>"
                "</div>"
            )

        deep_graphite = escape(getattr(self, "color_deep_graphite", "#1A1D23"))
        steel_grey = escape(getattr(self, "color_steel_grey", "#1F232B"))
        border = escape(getattr(self, "color_dark_border", "#242831"))
        text_primary = escape(getattr(self, "color_arctic_white", "#F2F4F8"))
        text_muted = escape(getattr(self, "color_cool_grey", "#8C92A0"))
        hover_orange = escape(getattr(self, "color_hover_orange", "#FF8C32"))
        success_green = escape(getattr(self, "color_success_green", "#3CC37A"))
        error_red = escape(getattr(self, "color_error_red", "#E85454"))
        warning_yellow = escape(getattr(self, "color_warning_yellow", "#FFB347"))
        border_subtle = escape(getattr(self, "color_border_subtle", border))

        return (
            "<html>"
            "<head>"
            "<meta charset='utf-8' />"
            "<style>"
            f"body{{margin:0;padding:0;width:100%;background:{steel_grey};color:{text_primary};font-family:'Source Han Sans SC','Microsoft YaHei',sans-serif;}}"
            ".table-wrap{width:100%;}"
            ".records-table{width:100%;border-collapse:collapse;background:transparent;}"
            f"th{{text-align:left;font-size:12px;color:{text_muted};font-weight:600;padding:12px 14px;border-bottom:1px solid {border};}}"
            f"td{{font-size:13px;color:{text_primary};padding:14px;border-bottom:1px solid {border};vertical-align:top;}}"
            f"code{{font-family:Consolas,'Courier New',monospace;color:{text_primary};background:{deep_graphite};padding:2px 8px;border:1px solid {border};border-radius:8px;}}"
            f".process-title{{font-size:14px;font-weight:700;color:{text_primary};margin-bottom:4px;}}"
            f".process-code{{font-size:12px;color:{text_muted};}}"
            ".badge{display:inline-block;font-size:12px;font-weight:600;border-radius:999px;padding:4px 10px;}"
            f".badge-workstation{{border:1px solid {border};background:{deep_graphite};color:{text_muted};}}"
            f".badge-ok{{border:1px solid {success_green};background:rgba(60,195,122,0.18);color:{success_green};}}"
            f".badge-ng{{border:1px solid {error_red};background:rgba(232,84,84,0.14);color:{error_red};}}"
            f".badge-conditional{{border:1px solid {warning_yellow};background:rgba(255,179,71,0.16);color:{warning_yellow};}}"
            f"a.action{{display:inline-block;text-decoration:none;color:{text_muted};border:1px solid {border_subtle};border-radius:6px;padding:6px 12px;font-weight:600;}}"
            f"a.action:hover{{background:{steel_grey};color:{text_primary};border-color:{hover_orange};}}"
            f".empty{{padding:40px 10px;color:{text_muted};text-align:center;font-size:14px;}}"
            "</style>"
            "</head>"
            "<body>"
            f"{table_body}"
            "</body>"
            "</html>"
        )
