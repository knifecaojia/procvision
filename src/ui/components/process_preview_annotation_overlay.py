from typing import List, Literal, Optional

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

DetectionStatus = Literal["idle", "detecting", "pass", "fail"]


class ProcessPreviewAnnotationOverlay(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._boxes: List[QRect] = []
        self._labels: List[str] = []
        self._status: DetectionStatus = "idle"
        self._draw_ok = True
        self._draw_ng = True
        self._show_hint = False
        self._hint_text = "最近检测结果"

    def set_boxes(self, boxes: List[QRect]) -> None:
        self._boxes = list(boxes or [])
        self.update()

    def set_labels(self, labels: List[str]) -> None:
        self._labels = list(labels or [])
        self.update()

    def set_status(self, status: DetectionStatus) -> None:
        self._status = status
        self.update()

    def set_draw_options(self, draw_ok: bool, draw_ng: bool) -> None:
        self._draw_ok = bool(draw_ok)
        self._draw_ng = bool(draw_ng)
        self.update()

    def set_hint_visible(self, visible: bool, text: str = "最近检测结果") -> None:
        self._show_hint = bool(visible)
        self._hint_text = str(text or "最近检测结果")
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._status not in ("pass", "fail"):
            return
        if self._status == "pass" and not self._draw_ok:
            return
        if self._status == "fail" and not self._draw_ng:
            return
        if not self._boxes:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._status == "pass":
            pen_color = QColor(34, 197, 94, 210)
            fill_color = QColor(34, 197, 94, 55)
            label_bg = QColor(34, 197, 94, 225)
        else:
            pen_color = QColor(239, 68, 68, 210)
            fill_color = QColor(239, 68, 68, 55)
            label_bg = QColor(239, 68, 68, 225)

        painter.setPen(QPen(pen_color, 2))
        for index, rect in enumerate(self._boxes):
            painter.fillRect(rect, fill_color)
            painter.drawRect(rect)
            text = self._labels[index] if index < len(self._labels) else ("NG" if self._status == "fail" else "OK")
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            font = painter.font()
            font.setPixelSize(13)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            text_width = max(38, metrics.horizontalAdvance(text) + 12)
            text_height = max(20, metrics.height() + 6)
            label_rect = QRect(rect.x(), rect.y() - text_height - 2, text_width, text_height)
            if label_rect.y() < 0:
                label_rect.moveTop(rect.y() + 2)
            painter.fillRect(label_rect, label_bg)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, text)
            painter.setPen(QPen(pen_color, 2))

        if self._show_hint:
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            font = painter.font()
            font.setPixelSize(12)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            hint_width = metrics.horizontalAdvance(self._hint_text) + 18
            hint_height = max(20, metrics.height() + 6)
            hint_rect = QRect(12, 12, hint_width, hint_height)
            painter.fillRect(hint_rect, QColor(15, 23, 42, 180))
            painter.drawText(hint_rect, Qt.AlignmentFlag.AlignCenter, self._hint_text)
        painter.end()
