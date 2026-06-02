"""
高级过滤窗口组件
用于装配任务列表的多条件组合查询
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QCheckBox, QLineEdit, QDateEdit, QComboBox, QMessageBox,
    QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)

STATUS_OPTIONS = [
    (-1, "引导未就绪"),
    (-2, "检测未就绪"),
    (1, "待执行"),
    (2, "进行中"),
    (3, "已完成"),
    (4, "手工通过"),
]

DARK_THEME = {
    "bg": "#1F232B",
    "surface": "#252A33",
    "border": "#3A3F4B",
    "text_primary": "#F2F4F8",
    "text_muted": "#8C92A0",
    "accent": "#FF8C32",
    "accent_hover": "#FF9D4D",
    "success": "#3CC37A",
    "input_bg": "#1A1D23",
}

LIGHT_THEME = {
    "bg": "#F3F4F7",
    "surface": "#FFFFFF",
    "border": "#CED3E5",
    "text_primary": "#111827",
    "text_muted": "#4B5563",
    "accent": "#2563EB",
    "accent_hover": "#1D4ED8",
    "success": "#22C55E",
    "input_bg": "#FFFFFF",
}


class TaskFilterWindow(QDialog):
    filter_applied = Signal(dict)

    def __init__(self, parent=None, current_filters: Optional[Dict[str, Any]] = None, theme: str = "dark"):
        super().__init__(parent)
        self.current_filters = current_filters or {}
        self._result_filters: Dict[str, Any] = {}
        self._theme = theme if theme in ("dark", "light") else "dark"
        
        self.setWindowTitle("高级过滤")
        self.setFixedSize(720, 520)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self._apply_theme()
        self._init_ui()
        self._load_current_filters()

    def _get_colors(self) -> Dict[str, str]:
        return LIGHT_THEME if self._theme == "light" else DARK_THEME

    def _apply_theme(self):
        c = self._get_colors()
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c['bg']};
            }}
            QLabel {{
                color: {c['text_primary']};
                font-size: 13px;
            }}
            QCheckBox {{
                color: {c['text_primary']};
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {c['border']};
                border-radius: 4px;
                background-color: {c['input_bg']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {c['accent']};
                border-color: {c['accent']};
                image: none;
            }}
            QCheckBox::indicator:checked::after {{
                content: "";
            }}
            QLineEdit {{
                background-color: {c['input_bg']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 8px 12px;
                color: {c['text_primary']};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {c['accent']};
            }}
            QLineEdit::placeholder {{
                color: {c['text_muted']};
            }}
            QComboBox {{
                background-color: {c['input_bg']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 6px 12px;
                color: {c['text_primary']};
                font-size: 13px;
                min-width: 100px;
            }}
            QComboBox:focus {{
                border: 1px solid {c['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {c['text_muted']};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {c['surface']};
                border: 1px solid {c['border']};
                color: {c['text_primary']};
                selection-background-color: {c['accent']};
                selection-color: white;
                outline: none;
            }}
            QDateEdit {{
                background-color: {c['input_bg']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 6px 12px;
                color: {c['text_primary']};
                font-size: 13px;
            }}
            QDateEdit:focus {{
                border: 1px solid {c['accent']};
            }}
            QDateEdit::drop-down {{
                border: none;
                width: 24px;
            }}
            QDateEdit::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {c['text_muted']};
                margin-right: 8px;
            }}
            QDateEdit QCalendarWidget {{
                background-color: {c['surface']};
                color: {c['text_primary']};
            }}
            QDateEdit QCalendarWidget QToolButton {{
                color: {c['text_primary']};
                background-color: {c['surface']};
                border: none;
            }}
            QDateEdit QCalendarWidget QMenu {{
                background-color: {c['surface']};
            }}
            QDateEdit QCalendarWidget QSpinBox {{
                background-color: {c['input_bg']};
                color: {c['text_primary']};
            }}
            QDateEdit QCalendarWidget QTableView {{
                background-color: {c['surface']};
                selection-background-color: {c['accent']};
                selection-color: white;
            }}
            QPushButton {{
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                padding: 8px 20px;
            }}
            QPushButton#filterBtnPrimary {{
                background-color: {c['accent']};
                border: none;
                color: white;
            }}
            QPushButton#filterBtnPrimary:hover {{
                background-color: {c['accent_hover']};
            }}
            QPushButton#filterBtnSecondary {{
                background-color: transparent;
                border: 1px solid {c['border']};
                color: {c['text_muted']};
            }}
            QPushButton#filterBtnSecondary:hover {{
                border-color: {c['text_muted']};
                color: {c['text_primary']};
            }}
            QPushButton#filterBtnReset {{
                background-color: transparent;
                border: 1px solid {c['border']};
                color: {c['text_muted']};
            }}
            QPushButton#filterBtnReset:hover {{
                border-color: {c['success']};
                color: {c['success']};
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QWidget#scrollContent {{
                background-color: transparent;
            }}
            QFrame#divider {{
                background-color: {c['border']};
            }}
        """)

    def _init_ui(self):
        c = self._get_colors()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        title_label = QLabel("设置过滤条件")
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {c['text_primary']};
        """)
        main_layout.addWidget(title_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        form_layout = QVBoxLayout(scroll_content)
        form_layout.setContentsMargins(0, 0, 8, 0)
        form_layout.setSpacing(14)

        status_label = QLabel("任务状态（可多选）")
        status_label.setStyleSheet(f"font-weight: 600; color: {c['text_primary']};")
        form_layout.addWidget(status_label)

        self.status_checkboxes: List[QCheckBox] = []
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(12)

        for status_code, status_name in STATUS_OPTIONS:
            cb = QCheckBox(status_name)
            cb.setProperty("statusCode", status_code)
            cb.setMinimumWidth(100)
            self.status_checkboxes.append(cb)
            status_layout.addWidget(cb)
        status_layout.addStretch()
        form_layout.addWidget(status_widget)

        divider1 = QFrame()
        divider1.setObjectName("divider")
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setFixedHeight(1)
        form_layout.addWidget(divider1)

        row1_widget = QWidget()
        row1_layout = QHBoxLayout(row1_widget)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(16)

        task_no_widget = QWidget()
        task_no_layout = QVBoxLayout(task_no_widget)
        task_no_layout.setContentsMargins(0, 0, 0, 0)
        task_no_layout.setSpacing(6)
        task_label = QLabel("任务号")
        task_label.setStyleSheet(f"font-weight: 600;")
        task_no_layout.addWidget(task_label)
        self.task_no_input = QLineEdit()
        self.task_no_input.setPlaceholderText("至少4个字符")
        self.task_no_input.setFixedHeight(36)
        task_no_layout.addWidget(self.task_no_input)
        row1_layout.addWidget(task_no_widget)

        prod_order_widget = QWidget()
        prod_order_layout = QVBoxLayout(prod_order_widget)
        prod_order_layout.setContentsMargins(0, 0, 0, 0)
        prod_order_layout.setSpacing(6)
        order_label = QLabel("订单号")
        order_label.setStyleSheet(f"font-weight: 600;")
        prod_order_layout.addWidget(order_label)
        self.prod_order_no_input = QLineEdit()
        self.prod_order_no_input.setPlaceholderText("至少4个字符")
        self.prod_order_no_input.setFixedHeight(36)
        prod_order_layout.addWidget(self.prod_order_no_input)
        row1_layout.addWidget(prod_order_widget)

        form_layout.addWidget(row1_widget)

        row2_widget = QWidget()
        row2_layout = QHBoxLayout(row2_widget)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(16)

        craft_widget = QWidget()
        craft_layout = QVBoxLayout(craft_widget)
        craft_layout.setContentsMargins(0, 0, 0, 0)
        craft_layout.setSpacing(6)
        craft_label = QLabel("工艺编码")
        craft_label.setStyleSheet(f"font-weight: 600;")
        craft_layout.addWidget(craft_label)
        self.craft_no_input = QLineEdit()
        self.craft_no_input.setPlaceholderText("多个用逗号分隔")
        self.craft_no_input.setFixedHeight(36)
        craft_layout.addWidget(self.craft_no_input)
        row2_layout.addWidget(craft_widget)

        process_widget = QWidget()
        process_layout = QVBoxLayout(process_widget)
        process_layout.setContentsMargins(0, 0, 0, 0)
        process_layout.setSpacing(6)
        process_label = QLabel("工序名称")
        process_label.setStyleSheet(f"font-weight: 600;")
        process_layout.addWidget(process_label)
        self.process_name_input = QLineEdit()
        self.process_name_input.setPlaceholderText("模糊匹配")
        self.process_name_input.setFixedHeight(36)
        process_layout.addWidget(self.process_name_input)
        row2_layout.addWidget(process_widget)

        form_layout.addWidget(row2_widget)

        divider2 = QFrame()
        divider2.setObjectName("divider")
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setFixedHeight(1)
        form_layout.addWidget(divider2)

        time_header = QWidget()
        time_header_layout = QHBoxLayout(time_header)
        time_header_layout.setContentsMargins(0, 0, 0, 0)
        time_header_layout.setSpacing(12)

        time_label = QLabel("时间范围")
        time_label.setStyleSheet(f"font-weight: 600;")
        time_header_layout.addWidget(time_label)

        self.enable_time_checkbox = QCheckBox("启用")
        self.enable_time_checkbox.stateChanged.connect(self._on_enable_time_changed)
        time_header_layout.addWidget(self.enable_time_checkbox)
        time_header_layout.addStretch()

        form_layout.addWidget(time_header)

        self.time_widget = QWidget()
        time_layout = QHBoxLayout(self.time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(12)

        time_type_label = QLabel("类型:")
        time_type_label.setStyleSheet(f"color: {c['text_muted']};")
        time_layout.addWidget(time_type_label)
        self.time_type_combo = QComboBox()
        self.time_type_combo.addItem("计划开始时间", "start")
        self.time_type_combo.addItem("计划结束时间", "end")
        self.time_type_combo.setFixedHeight(36)
        time_layout.addWidget(self.time_type_combo)

        from_label = QLabel("从")
        from_label.setStyleSheet(f"color: {c['text_muted']};")
        time_layout.addWidget(from_label)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setFixedHeight(36)
        self.start_date_edit.setFixedWidth(120)
        self.start_date_edit.setDate(QDate.currentDate().addDays(-7))
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        time_layout.addWidget(self.start_date_edit)

        to_label = QLabel("至")
        to_label.setStyleSheet(f"color: {c['text_muted']};")
        time_layout.addWidget(to_label)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setFixedHeight(36)
        self.end_date_edit.setFixedWidth(120)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        time_layout.addWidget(self.end_date_edit)

        time_layout.addStretch()
        form_layout.addWidget(self.time_widget)
        self.time_widget.setEnabled(False)

        form_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=1)

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(12)

        reset_btn = QPushButton("重置")
        reset_btn.setObjectName("filterBtnReset")
        reset_btn.setFixedSize(90, 38)
        reset_btn.clicked.connect(self._on_reset)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("filterBtnSecondary")
        cancel_btn.setFixedSize(90, 38)
        cancel_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton("确定")
        confirm_btn.setObjectName("filterBtnPrimary")
        confirm_btn.setFixedSize(100, 38)
        confirm_btn.clicked.connect(self._on_confirm)

        button_layout.addStretch()
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(confirm_btn)

        main_layout.addWidget(button_widget)

    def _on_enable_time_changed(self, state):
        self.time_widget.setEnabled(state == Qt.CheckState.Checked.value)

    def _load_current_filters(self):
        if not self.current_filters:
            return

        status_list = self.current_filters.get("status", [])
        if isinstance(status_list, list):
            for cb in self.status_checkboxes:
                status_code = cb.property("statusCode")
                cb.setChecked(status_code in status_list)

        task_no = self.current_filters.get("task_no", "")
        if task_no:
            self.task_no_input.setText(str(task_no))

        prod_order_no = self.current_filters.get("prod_order_no", "")
        if prod_order_no:
            self.prod_order_no_input.setText(str(prod_order_no))

        craft_no = self.current_filters.get("craft_no", [])
        if isinstance(craft_no, list):
            self.craft_no_input.setText(",".join(craft_no))
        elif craft_no:
            self.craft_no_input.setText(str(craft_no))

        process_name = self.current_filters.get("process_name", "")
        if process_name:
            self.process_name_input.setText(str(process_name))

        time_range = self.current_filters.get("time_range")
        if time_range and isinstance(time_range, dict):
            self.enable_time_checkbox.setChecked(True)
            time_type = time_range.get("type", "start")
            self.time_type_combo.setCurrentIndex(0 if time_type == "start" else 1)

            begin = time_range.get("begin", "")
            if begin:
                try:
                    dt = datetime.strptime(begin[:10], "%Y-%m-%d")
                    self.start_date_edit.setDate(QDate(dt.year, dt.month, dt.day))
                except Exception:
                    pass

            end = time_range.get("end", "")
            if end:
                try:
                    dt = datetime.strptime(end[:10], "%Y-%m-%d")
                    self.end_date_edit.setDate(QDate(dt.year, dt.month, dt.day))
                except Exception:
                    pass

    def _on_reset(self):
        for cb in self.status_checkboxes:
            cb.setChecked(False)

        self.task_no_input.clear()
        self.prod_order_no_input.clear()
        self.craft_no_input.clear()
        self.process_name_input.clear()
        self.enable_time_checkbox.setChecked(False)
        self.start_date_edit.setDate(QDate.currentDate().addDays(-7))
        self.end_date_edit.setDate(QDate.currentDate())

    def _on_confirm(self):
        filters: Dict[str, Any] = {}

        selected_status = []
        for cb in self.status_checkboxes:
            if cb.isChecked():
                status_code = cb.property("statusCode")
                selected_status.append(status_code)
        if selected_status:
            filters["status"] = selected_status

        task_no = self.task_no_input.text().strip()
        if task_no:
            if len(task_no) < 4:
                QMessageBox.warning(self, "提示", "任务号至少需要输入4个字符")
                return
            filters["task_no"] = task_no

        prod_order_no = self.prod_order_no_input.text().strip()
        if prod_order_no:
            if len(prod_order_no) < 4:
                QMessageBox.warning(self, "提示", "订单号至少需要输入4个字符")
                return
            filters["prod_order_no"] = prod_order_no

        craft_no = self.craft_no_input.text().strip()
        if craft_no:
            filters["craft_no"] = [c.strip() for c in craft_no.split(",") if c.strip()]

        process_name = self.process_name_input.text().strip()
        if process_name:
            filters["process_name"] = process_name

        if self.enable_time_checkbox.isChecked():
            time_type = self.time_type_combo.currentData()
            start_date = self.start_date_edit.date()
            end_date = self.end_date_edit.date()

            if start_date > end_date:
                QMessageBox.warning(self, "提示", "结束日期必须晚于或等于开始日期")
                return

            begin_dt = datetime(start_date.year(), start_date.month(), start_date.day(), 0, 0, 0)
            end_dt = datetime(end_date.year(), end_date.month(), end_date.day(), 23, 59, 59)

            if (end_dt - begin_dt).days > 90:
                QMessageBox.warning(self, "提示", "时间跨度不能超过3个月")
                return

            filters["time_range"] = {
                "type": time_type,
                "begin": begin_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "end": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            }

        filters["pagination"] = {"page": 1, "page_size": 20}

        logger.info(f"Filter applied: {filters}")
        self._result_filters = filters
        self.filter_applied.emit(filters)
        self.accept()

    def get_filters(self) -> Dict[str, Any]:
        return self._result_filters
