"""
Dialog shown before starting a task with material guidance.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .component_theme import resolve_component_theme


class MaterialWarningDialog(QDialog):
    """Show task materials and highlight items that need extra attention."""

    def __init__(self, task_data: Dict[str, Any], parent: QWidget | None = None):
        super().__init__(parent)
        self.task_data = task_data
        self.setWindowTitle("启动前确认")
        self.setModal(True)
        self.resize(760, 620)
        self._init_ui()

    def _init_ui(self) -> None:
        colors = resolve_component_theme(self)
        muted = colors["cool_grey"] if colors.get("theme_name") == "light" else colors["text_muted"]
        summary_bg = colors["steel_grey"]
        card_bg = colors["surface_dark"]
        dialog_bg = colors["deep_graphite"]
        border = colors["border_subtle"]
        text_primary = colors["text_primary"]
        accent = colors["hover_orange"]
        accent_hover = colors["warning_yellow"] if colors.get("theme_name") == "dark" else colors["amber"]
        alert_border = colors["error_red"]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("请先确认本工序物料信息")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {text_primary};")
        layout.addWidget(title)

        summary = QFrame()
        summary.setStyleSheet(f"background:{summary_bg}; border:1px solid {border}; border-radius:12px;")
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(16, 16, 16, 16)
        summary_layout.setSpacing(8)

        for label, value in self._summary_items():
            item = QLabel(f"{label}：{value}")
            item.setStyleSheet(f"font-size: 14px; color: {text_primary};")
            item.setWordWrap(True)
            summary_layout.addWidget(item)
        layout.addWidget(summary)

        materials_label = QLabel("物料清单")
        materials_label.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {text_primary};")
        layout.addWidget(materials_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background:transparent;")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        material_list = self.task_data.get("material_list") or []
        for material in material_list:
            content_layout.addWidget(self._build_material_card(material))
        content_layout.addStretch(1)

        scroll_area.setWidget(content)
        layout.addWidget(scroll_area, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(120, 40)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(
            f"QPushButton{{background:{card_bg};color:{text_primary};border:1px solid {border};border-radius:10px;}}"
            f"QPushButton:hover{{border-color:{accent};}}"
        )
        btn_row.addWidget(cancel_btn)

        confirm_btn = QPushButton("确认并开始")
        confirm_btn.setFixedSize(140, 40)
        confirm_btn.clicked.connect(self.accept)
        confirm_btn.setStyleSheet(
            f"QPushButton{{background:{accent};color:white;border:none;border-radius:10px;font-weight:700;}}"
            f"QPushButton:hover{{background:{accent_hover};}}"
        )
        btn_row.addWidget(confirm_btn)

        layout.addLayout(btn_row)
        self.setStyleSheet(f"QDialog{{background:{dialog_bg};}}")
        self._dialog_colors = {
            "card_bg": card_bg,
            "border": border,
            "text_primary": text_primary,
            "muted": muted,
            "alert_border": alert_border,
        }

    def _summary_items(self) -> Iterable[tuple[str, str]]:
        return [
            ("任务号", self._text(self.task_data.get("work_order_code"))),
            ("生产订单号", self._text(self.task_data.get("prod_order_no"))),
            ("工艺名称", self._text(self.task_data.get("craft_name"))),
            ("工序名称", self._text(self.task_data.get("process_name"))),
            ("工序描述", self._text(self.task_data.get("process_desc"))),
        ]

    def _build_material_card(self, material: Dict[str, Any]) -> QWidget:
        colors = getattr(self, "_dialog_colors", {})
        card = QFrame()
        has_mark = bool(material.get("has_error_prevention_mark"))
        border_color = colors.get("border", "#2E3440")
        background = colors.get("card_bg", "#1F232B")
        card.setStyleSheet(
            f"QFrame{{background:{background};border:1px solid {border_color};border-radius:12px;}}"
        )

        outer_layout = QHBoxLayout(card)
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(10)

        if has_mark:
            accent = QFrame(card)
            accent.setFixedWidth(4)
            accent.setStyleSheet(
                f"QFrame{{background:{colors.get('alert_border', '#E85454')};border:none;border-radius:2px;}}"
            )
            outer_layout.addWidget(accent)

        content = QWidget(card)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        outer_layout.addWidget(content, 1)

        header = QHBoxLayout()
        name = QLabel(
            f"{self._text(material.get('material_name_display'))}  "
            f"({self._text(material.get('material_no_display'))})"
        )
        name.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {colors.get('text_primary', '#F2F4F8')};"
        )
        name.setWordWrap(True)
        header.addWidget(name, 1)

        if has_mark:
            badge_text = self._warning_badge_text(material)
            badge = QLabel(badge_text)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                f"background:transparent;color:{colors.get('alert_border', '#E85454')};"
                f"border:1px solid {colors.get('alert_border', '#E85454')};"
                "padding:3px 10px;border-radius:999px;font-size:12px;font-weight:700;"
            )
            header.addWidget(badge)
        layout.addLayout(header)

        info_rows = [
            ("装配序号", material.get("assembly_number_display")),
            ("位号", material.get("position_number_display")),
            ("型号", material.get("model_no_display")),
            ("极性方向", material.get("polarity_direction_display")),
            ("数量", self._quantity_text(material)),
        ]

        for label, value in info_rows:
            row = QLabel(f"{label}：{self._text(value)}")
            row.setStyleSheet(f"font-size: 13px; color: {colors.get('muted', '#D6DBE6')};")
            row.setWordWrap(True)
            layout.addWidget(row)

        return card

    def _quantity_text(self, material: Dict[str, Any]) -> str:
        quantity = self._text(material.get("material_quantity_display"))
        unit = self._text(material.get("material_unit_display"))
        if unit == "-":
            return quantity
        return f"{quantity} {unit}"

    def _warning_badge_text(self, material: Dict[str, Any]) -> str:
        text = self._text(material.get("error_prevention_mark_display"))
        return text if text != "-" else "易错"

    @staticmethod
    def _text(value: Any) -> str:
        text = str(value or "").strip()
        return text or "-"
