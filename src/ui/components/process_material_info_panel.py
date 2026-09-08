"""
Right-side process and material information panel for the execution window.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from .component_theme import resolve_component_theme


class ProcessMaterialInfoPanel(QFrame):
    """Show process summary and task material details."""

    def __init__(self, process_data: Dict[str, Any], parent: QWidget | None = None):
        super().__init__(parent)
        self.process_data = process_data
        self.setObjectName("processMaterialInfoPanel")
        self.expanded_width = 360
        self.collapsed_width = 44
        self.is_collapsed = False
        self._init_ui()

    def _init_ui(self) -> None:
        colors = resolve_component_theme(self)
        muted = colors["cool_grey"] if colors.get("theme_name") == "light" else colors["text_muted"]
        card_bg = colors["surface_dark"]
        panel_bg = colors["deep_graphite"]
        border = colors["border_subtle"]
        title_color = colors["text_primary"]
        alert_border = colors["error_red"]
        self.setStyleSheet(
            f"QFrame#processMaterialInfoPanel{{background:{panel_bg};border-left:1px solid {border};}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.expanded_widget = QWidget(self)
        self.expanded_widget.setStyleSheet("background:transparent;")
        expanded_layout = QVBoxLayout(self.expanded_widget)
        expanded_layout.setContentsMargins(14, 14, 14, 14)
        expanded_layout.setSpacing(12)

        header = QWidget(self.expanded_widget)
        header.setStyleSheet("background:transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title = QLabel("工艺文件信息")
        title.setStyleSheet(f"font-size:18px;font-weight:700;color:{title_color};")
        header_layout.addWidget(title)
        header_layout.addStretch(1)

        self.collapse_button = QPushButton("收起")
        self.collapse_button.setObjectName("materialPanelCollapseButton")
        self.collapse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_button.setFixedHeight(32)
        self.collapse_button.clicked.connect(lambda: self.set_collapsed(True))
        self.collapse_button.setStyleSheet(
            f"QPushButton{{background:{card_bg};color:{muted};border:1px solid {border};border-radius:8px;padding:0 10px;}}"
            f"QPushButton:hover{{border-color:{colors['hover_orange']};color:{title_color};}}"
        )
        header_layout.addWidget(self.collapse_button)
        expanded_layout.addWidget(header)

        summary = self._build_section("工艺摘要", self._summary_lines())
        expanded_layout.addWidget(summary)

        material_title = QLabel(f"物料清单（{len(self._material_list())}）")
        material_title.setStyleSheet(f"font-size:16px;font-weight:700;color:{title_color};")
        expanded_layout.addWidget(material_title)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background:transparent;")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        for material in self._material_list():
            content_layout.addWidget(self._build_material_card(material))
        content_layout.addStretch(1)

        self.scroll_area.setWidget(content)
        expanded_layout.addWidget(self.scroll_area, 1)
        layout.addWidget(self.expanded_widget, 1)

        self.collapsed_widget = QWidget(self)
        self.collapsed_widget.setStyleSheet("background:transparent;")
        collapsed_layout = QVBoxLayout(self.collapsed_widget)
        collapsed_layout.setContentsMargins(6, 14, 6, 14)
        collapsed_layout.setSpacing(10)

        self.expand_button = QPushButton(">")
        self.expand_button.setObjectName("materialPanelExpandButton")
        self.expand_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_button.setFixedSize(30, 30)
        self.expand_button.clicked.connect(lambda: self.set_collapsed(False))
        self.expand_button.setStyleSheet(
            f"QPushButton{{background:{card_bg};color:{title_color};border:1px solid {border};border-radius:8px;font-weight:700;}}"
            f"QPushButton:hover{{border-color:{colors['hover_orange']};}}"
        )
        collapsed_layout.addWidget(self.expand_button, 0, Qt.AlignmentFlag.AlignHCenter)

        collapsed_label = QLabel("工\n艺\n/\n物\n料")
        collapsed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        collapsed_label.setStyleSheet(f"font-size:12px;font-weight:700;color:{muted};line-height:1.3;")
        collapsed_layout.addWidget(collapsed_label, 1, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.collapsed_widget, 1)

        self._panel_colors = {
            "card_bg": card_bg,
            "border": border,
            "title_color": title_color,
            "muted": muted,
            "alert_border": alert_border,
        }

        self.set_collapsed(False)

    def set_collapsed(self, collapsed: bool) -> None:
        self.is_collapsed = bool(collapsed)
        self.expanded_widget.setVisible(not self.is_collapsed)
        self.collapsed_widget.setVisible(self.is_collapsed)
        self.setFixedWidth(self.collapsed_width if self.is_collapsed else self.expanded_width)

    def _build_section(self, section_title: str, lines: Iterable[str]) -> QWidget:
        colors = getattr(self, "_panel_colors", {})
        card = QFrame()
        card.setStyleSheet(
            f"QFrame{{background:{colors.get('card_bg', '#171B21')};"
            f"border:1px solid {colors.get('border', '#2E3440')};border-radius:12px;}}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        title = QLabel(section_title)
        title.setStyleSheet(f"font-size:14px;font-weight:700;color:{colors.get('title_color', '#F2F4F8')};")
        layout.addWidget(title)

        for line in lines:
            label = QLabel(line)
            label.setWordWrap(True)
            label.setStyleSheet(f"font-size:13px;color:{colors.get('muted', '#D6DBE6')};")
            layout.addWidget(label)
        return card

    def _build_material_card(self, material: Dict[str, Any]) -> QWidget:
        colors = getattr(self, "_panel_colors", {})
        card = QFrame()
        has_mark = bool(material.get("has_error_prevention_mark"))
        border = colors.get("border", "#2E3440")
        bg = colors.get("card_bg", "#171B21")
        card.setStyleSheet(f"QFrame{{background:{bg};border:1px solid {border};border-radius:12px;}}")

        outer_layout = QHBoxLayout(card)
        outer_layout.setContentsMargins(10, 10, 12, 10)
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
        layout.setSpacing(6)
        outer_layout.addWidget(content, 1)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        name = QLabel(
            f"{self._text(material.get('material_name_display'))}  "
            f"({self._text(material.get('material_no_display'))})"
        )
        name.setWordWrap(True)
        name.setStyleSheet(f"font-size:14px;font-weight:700;color:{colors.get('title_color', '#F2F4F8')};")
        header.addWidget(name, 1)

        if has_mark:
            badge = QLabel(self._warning_badge_text(material))
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                f"background:transparent;color:{colors.get('alert_border', '#E85454')};"
                f"border:1px solid {colors.get('alert_border', '#E85454')};"
                "padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;"
            )
            header.addWidget(badge)

        layout.addLayout(header)

        for text in self._material_lines(material):
            row = QLabel(text)
            row.setWordWrap(True)
            row.setStyleSheet(f"font-size:12px;color:{colors.get('muted', '#D6DBE6')};")
            layout.addWidget(row)
        return card

    def _summary_lines(self) -> List[str]:
        return [
            f"生产订单号：{self._text(self.process_data.get('prod_order_no'))}",
            f"工艺名称：{self._text(self.process_data.get('craft_name') or self.process_data.get('title'))}",
            f"工艺编码：{self._text(self.process_data.get('craft_no'))}",
            f"工艺版本：{self._text(self.process_data.get('craft_version') or self.process_data.get('version'))}",
            f"工序名称：{self._text(self.process_data.get('process_name'))}",
            f"工序编码：{self._text(self.process_data.get('process_code'))}",
            f"工序描述：{self._text(self.process_data.get('process_desc'))}",
        ]

    def _material_lines(self, material: Dict[str, Any]) -> List[str]:
        quantity = self._text(material.get("material_quantity_display"))
        unit = self._text(material.get("material_unit_display"))
        quantity_line = quantity if unit == "-" else f"{quantity} {unit}"
        return [
            f"装配序号：{self._text(material.get('assembly_number_display'))}",
            f"位号：{self._text(material.get('position_number_display'))}",
            f"型号：{self._text(material.get('model_no_display'))}",
            f"极性方向：{self._text(material.get('polarity_direction_display'))}",
            f"数量：{quantity_line}",
            f"易错标识：{self._text(material.get('error_prevention_mark_display'))}",
        ]

    def _material_list(self) -> List[Dict[str, Any]]:
        material_list = self.process_data.get("material_list")
        return material_list if isinstance(material_list, list) else []

    def _warning_badge_text(self, material: Dict[str, Any]) -> str:
        text = self._text(material.get("error_prevention_mark_display"))
        return text if text != "-" else "易错"

    @staticmethod
    def _text(value: Any) -> str:
        text = str(value or "").strip()
        return text or "-"
