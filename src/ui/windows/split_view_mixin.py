import json
import logging
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QStackedWidget, QSizePolicy, QScrollArea,
)
from PySide6.QtCore import Qt, QEvent, QObject, QRect, QSize
from PySide6.QtGui import QPixmap

logger = logging.getLogger(__name__)


class SplitViewMixin:
    def create_visual_area_container(self) -> QWidget:
        self._view_stack = QStackedWidget()
        self._view_stack.setObjectName("viewStack")

        self._classic_page = self._build_classic_page()
        self._split_page = self._build_split_page()

        self._view_stack.addWidget(self._classic_page)
        self._view_stack.addWidget(self._split_page)

        split_mode = getattr(self, "split_layout_mode", False)
        self._view_stack.setCurrentIndex(1 if split_mode else 0)

        self._ensure_base_image_in_active_page()

        return self._view_stack

    def _build_classic_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("classicPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        container = QFrame()
        container.setObjectName("visualGuidanceArea")
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        self._classic_camera_container = container
        layout.addWidget(container, 1)
        return page

    def _build_split_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("splitPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        step_bar = self._build_step_bar()
        layout.addWidget(step_bar)

        sep = QFrame()
        sep.setObjectName("splitSeparator")
        sep.setFixedHeight(1)
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        split_container = QWidget()
        split_layout = QHBoxLayout(split_container)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(0)

        guide_area = self._build_guide_image_area()
        split_layout.addWidget(guide_area, 1)

        vsep = QFrame()
        vsep.setObjectName("splitSeparator")
        vsep.setFixedWidth(1)
        vsep.setFrameShape(QFrame.Shape.VLine)
        split_layout.addWidget(vsep)

        camera_area = self._build_split_camera_area()
        split_layout.addWidget(camera_area, 1)

        layout.addWidget(split_container, 1)
        return page

    def _build_step_bar(self) -> QWidget:
        bar_container = QWidget()
        bar_container.setObjectName("stepBarContainer")
        bar_container.setFixedHeight(80)

        bar_layout = QHBoxLayout(bar_container)
        bar_layout.setContentsMargins(8, 4, 8, 4)
        bar_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("stepBarScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        steps_widget = QWidget()
        steps_widget.setObjectName("stepBarStepsWidget")
        steps_layout = QHBoxLayout(steps_widget)
        steps_layout.setContentsMargins(4, 4, 4, 4)
        steps_layout.setSpacing(6)

        self.step_bar_card_widgets = []
        for step in self.steps:
            card = self._create_step_bar_card(step)
            steps_layout.addWidget(card)
            self.step_bar_card_widgets.append(card)
        steps_layout.addStretch()

        scroll_area.setWidget(steps_widget)
        bar_layout.addWidget(scroll_area)
        self._step_bar_scroll_area = scroll_area
        return bar_container

    def _build_guide_image_area(self) -> QWidget:
        area = QWidget()
        area.setObjectName("guideImageArea")

        layout = QVBoxLayout(area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("引导图")
        title.setObjectName("guideImageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(32)
        layout.addWidget(title)

        self.guide_image_label = QLabel()
        self.guide_image_label.setObjectName("guideImageLabel")
        self.guide_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.guide_image_label.setMinimumSize(320, 240)
        self.guide_image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.guide_image_label.setText("暂无引导图")
        layout.addWidget(self.guide_image_label, 1)

        return area

    def _build_split_camera_area(self) -> QWidget:
        area = QWidget()
        area.setObjectName("splitCameraArea")

        layout = QVBoxLayout(area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("实时画面")
        title.setObjectName("cameraImageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(32)
        layout.addWidget(title)

        container = QFrame()
        container.setObjectName("visualGuidanceArea")
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        self._split_camera_container = container
        layout.addWidget(container, 1)
        return area

    def _ensure_base_image_in_active_page(self):
        if not hasattr(self, "base_image_label") or self.base_image_label is None:
            self.base_image_label = QLabel()
            self.base_image_label.setObjectName("baseImageLabel")
            self.base_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.base_image_label.setMinimumSize(720, 480)
            self.base_image_label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )

        current = self._view_stack.currentIndex()
        if current == 0:
            target = self._classic_camera_container
        else:
            target = self._split_camera_container

        self.base_image_label.setParent(target)
        target.layout().addWidget(self.base_image_label, 1)

        self._rebuild_overlay_in_container(target)

    def _rebuild_overlay_in_container(self, container: QWidget):
        overlay = getattr(self, "overlay_widget", None)
        if overlay is not None:
            overlay.setParent(container)
            overlay.setVisible(False)
            overlay.setGeometry(self.base_image_label.geometry())
            overlay.raise_()

        if not hasattr(self, "base_image_label"):
            return

        try:
            self.base_image_label.removeEventFilter(self._overlay_sync_filter)
        except Exception:
            pass

        sync = self._make_overlay_sync()
        self._overlay_sync_filter = sync
        self.base_image_label.installEventFilter(sync)

    def toggle_layout_mode(self, split: bool):
        self.split_layout_mode = split

        old_index = self._view_stack.currentIndex()
        new_index = 1 if split else 0
        if old_index == new_index:
            return

        old_container = (
            self._classic_camera_container
            if old_index == 0
            else self._split_camera_container
        )
        old_container.layout().removeWidget(self.base_image_label)

        step_list_panel = getattr(self, "step_list_panel", None)
        if step_list_panel is not None:
            step_list_panel.setVisible(not split)

        self._view_stack.setCurrentIndex(new_index)

        self._ensure_base_image_in_active_page()

        if split:
            try:
                self._display_guide_image(getattr(self, "current_step_index", 0))
            except Exception:
                pass
            try:
                self._scroll_step_bar_to_current()
            except Exception:
                pass
        else:
            self._clear_guide_image_display()

        try:
            self._align_overlay_geometry()
        except Exception:
            pass

        self._save_layout_preference(split)

        btn = getattr(self, "layout_toggle_btn", None)
        if btn is not None:
            btn.setChecked(split)
            btn.setText("🔀 单画面" if split else "🔀 分栏")

        logger.info("Layout mode switched to: %s", "split" if split else "classic")

    def _scroll_step_bar_to_current(self):
        scroll_area = getattr(self, "_step_bar_scroll_area", None)
        if scroll_area is None:
            return
        idx = getattr(self, "current_step_index", 0)
        cards = getattr(self, "step_bar_card_widgets", [])
        if idx < 0 or idx >= len(cards):
            return
        card = cards[idx]
        scroll_area.ensureWidgetVisible(card, 50, 0)

    def _save_layout_preference(self, split: bool):
        try:
            from src.core.paths import get_config_json_path

            p = get_config_json_path()
            data = {}
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
            if "general" not in data or not isinstance(data["general"], dict):
                data["general"] = {}
            data["general"]["layout_mode"] = "split" if split else "classic"
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to save layout preference: %s", e)

    def _load_layout_preference(self) -> bool:
        try:
            from src.core.paths import get_config_json_path

            p = get_config_json_path()
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                return data.get("general", {}).get("layout_mode") == "split"
        except Exception:
            pass
        return False

    def _make_overlay_sync(self):
        parent_self = self

        class _Sync(QObject):
            def eventFilter(self, obj, event):
                if event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
                    overlay = getattr(parent_self, "overlay_widget", None)
                    if overlay is not None:
                        overlay.setGeometry(obj.geometry())
                        try:
                            target = None
                            for child in overlay.children():
                                if isinstance(child, QWidget) and child.isVisible():
                                    target = child
                                    break
                            if target is not None:
                                target.adjustSize()
                                g = parent_self._compute_prompt_geometry(target.sizeHint())
                                target.setGeometry(g)
                        except Exception:
                            pass
                return False

        return _Sync()
