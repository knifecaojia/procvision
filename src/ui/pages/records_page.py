"""
Work records page for the industrial vision system.
"""

import html
import logging
import math
import base64
import json
from typing import Any, Dict, List, Optional, Set, Tuple
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QTextBrowser,
    QApplication,
    QDialog,
)
from PySide6.QtCore import Qt, QUrl, QUrlQuery, QObject, Signal, QRunnable, QThreadPool, QByteArray, QBuffer, QIODevice, QTimer
from PySide6.QtGui import QPixmap, QImage, QGuiApplication

from src.services.data_service import DataService
from ..components.pagination_widget import PaginationWidget

import requests

logger = logging.getLogger(__name__)

class _ImageFetchTask(QObject, QRunnable):
    finished = Signal(str, str, object, str, str)
    failed = Signal(str, str, str)

    def __init__(self, task_no: str, step_key: str, url: str, thumb_width: int = 160):
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.task_no = str(task_no)
        self.step_key = str(step_key)
        self.url = str(url)
        self.thumb_width = int(thumb_width)

    def run(self) -> None:
        try:
            r = requests.get(self.url, timeout=20)
            r.raise_for_status()
            raw = r.content
            content_type = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if not content_type.startswith("image/"):
                content_type = "image/jpeg"

            img = QImage.fromData(raw)
            thumb_data_url = ""
            if not img.isNull():
                thumb = img.scaledToWidth(self.thumb_width, Qt.TransformationMode.SmoothTransformation)
                buf = QByteArray()
                qb = QBuffer(buf)
                qb.open(QIODevice.OpenModeFlag.WriteOnly)
                thumb.save(qb, "JPG", quality=75)
                qb.close()
                b64 = base64.b64encode(bytes(buf)).decode("ascii")
                thumb_data_url = f"data:image/jpeg;base64,{b64}"
            self.finished.emit(self.task_no, self.step_key, raw, content_type, thumb_data_url)
        except Exception as e:
            self.failed.emit(self.task_no, self.step_key, str(e))


class RecordsPage(QFrame):
    """Work records page implementation aligned with the design spec."""

    def __init__(self, parent=None, initial_theme: str = "dark"):
        super().__init__(parent)
        self.setObjectName("recordsPage")

        self.current_theme = initial_theme if initial_theme in {"dark", "light"} else "dark"

        self.data_service = DataService()

        # State for filtering and pagination
        self.search_term = ""
        self.filter_status = None
        self.page_size = 10
        self.current_page = 1
        self.total_pages = 1
        self.total_records = 0
        self.current_items: List[Dict[str, Any]] = []
        self.expanded_tasks: Set[str] = set()
        self.expanded_steps: Dict[str, Set[str]] = {}
        self._thumb_cache: Dict[Tuple[str, str], str] = {}
        self._full_image_cache: Dict[Tuple[str, str], bytes] = {}
        self._loading_images: Set[Tuple[str, str]] = set()
        self._pending_image_tasks: Dict[Tuple[str, str], _ImageFetchTask] = {}
        self._thread_pool = QThreadPool.globalInstance()

        # UI references
        self.subtitle_label = None
        self.html_viewer = None
        self.pagination = None

        self.setup_colors(self.current_theme)
        self.init_ui()
        self.load_data()

    # ------------------------------------------------------------------ UI ----
    def init_ui(self):
        """Initialize the records page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        layout.addWidget(self._create_header_section())
        layout.addWidget(self._create_table_section(), stretch=1)

    def _create_header_section(self):
        frame = QFrame()
        frame.setObjectName("recordsHeader")

        root_layout = QVBoxLayout(frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(8)

        top_row = QFrame()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        title_label = QLabel("工作记录")
        title_label.setObjectName("recordsTitleLabel")
        top_layout.addWidget(title_label)
        top_layout.addStretch(1)

        self.page_size_combo = QComboBox()
        self.page_size_combo.setObjectName("processFilterCombo")
        self.page_size_combo.addItem("10/页", 10)
        self.page_size_combo.addItem("20/页", 20)
        self.page_size_combo.addItem("50/页", 50)
        self.page_size_combo.setFixedWidth(90)
        self.page_size_combo.currentIndexChanged.connect(self.on_page_size_changed)
        top_layout.addWidget(self.page_size_combo)

        self.subtitle_label = QLabel("Work Records - 0 条记录")
        self.subtitle_label.setObjectName("recordsSubtitleLabel")

        root_layout.addWidget(top_row)
        root_layout.addWidget(self.subtitle_label)

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

        self.pagination = PaginationWidget()
        self.pagination.page_changed.connect(self.on_page_changed)
        layout.addWidget(self.pagination, 0, Qt.AlignmentFlag.AlignCenter)

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

    def load_data(self) -> None:
        result = self.data_service.get_record_list_online(
            page=self.current_page,
            page_size=self.page_size,
            status=self.filter_status,
        )
        self.current_items = list(result.get("items") or [])
        self.total_pages = int(result.get("total_pages") or 1)
        self.total_records = int(result.get("total") or 0)
        error = result.get("error")
        if self.pagination:
            self.pagination.set_total_pages(self.total_pages)
            self.pagination.set_current_page(self.current_page)
        self._refresh_table_view(error_msg=error)
        self.update_record_summary(self.total_records)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            QTimer.singleShot(0, self.load_data)
        except Exception:
            pass

    # -------------------------------------------------------- Interaction ----
    def on_page_size_changed(self, _index=None):
        try:
            self.page_size = int(self.page_size_combo.currentData() or 10)
        except Exception:
            self.page_size = 10
        self.current_page = 1
        self.load_data()

    def on_page_changed(self, page: int) -> None:
        try:
            page_int = int(page)
        except Exception:
            page_int = 1
        self.current_page = max(1, min(page_int, int(self.total_pages or 1)))
        self.load_data()

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
        if url.scheme() != "app":
            return
        query = QUrlQuery(url)
        action = url.host()
        task_no = query.queryItemValue("taskNo")
        step_key = query.queryItemValue("stepKey")
        if action == "toggle_task" and task_no:
            if task_no in self.expanded_tasks:
                self.expanded_tasks.remove(task_no)
            else:
                self.expanded_tasks.add(task_no)
            self._refresh_table_view()
            return
        if action == "toggle_step" and task_no and step_key:
            group = self.expanded_steps.get(task_no)
            if group is None:
                group = set()
                self.expanded_steps[task_no] = group
            if step_key in group:
                group.remove(step_key)
            else:
                group.add(step_key)
            self._refresh_table_view()
            return
        if action == "load_img" and task_no and step_key:
            self._start_image_load(task_no, step_key)
            self._refresh_table_view()
            return
        if action == "preview_img" and task_no and step_key:
            self._show_image_preview(task_no, step_key)
            return

    # ----------------------------------------------------------- Helpers ----
    def _refresh_table_view(self, error_msg: Optional[str] = None):
        items = list(self.current_items or [])
        if self.search_term:
            needle = self.search_term.lower()
            def _match(it: Dict[str, Any]) -> bool:
                targets = [str(it.get("taskNo") or ""), str(it.get("processName") or ""), str(it.get("processNo") or "")]
                return any(needle in (t or "").lower() for t in targets)
            items = [it for it in items if _match(it)]
        if self.html_viewer:
            self.html_viewer.setHtml(self._render_records_table_html(items, error_msg=error_msg))
        self._update_pagination_controls()

    def _update_pagination_controls(self):
        if self.pagination:
            self.pagination.set_total_pages(int(self.total_pages or 1))
            self.pagination.set_current_page(int(self.current_page or 1))

    def update_record_summary(self, record_count):
        """Update the subtitle with the current record count."""
        if self.subtitle_label:
            self.subtitle_label.setText(f"Work Records - {record_count} 条记录")

    def _sanitize_url(self, url: str) -> str:
        if not url:
            return ""
        u = str(url).strip()
        while (u.startswith("`") and u.endswith("`")) or (u.startswith("\"") and u.endswith("\"")) or (u.startswith("'") and u.endswith("'")):
            u = u[1:-1].strip()
        if u.startswith("`"):
            u = u.strip("`").strip()
        return u

    def _start_image_load(self, task_no: str, step_key: str) -> None:
        cache_key = (str(task_no), str(step_key))
        if cache_key in self._thumb_cache or cache_key in self._loading_images:
            return
        step = self._find_step(task_no, step_key)
        if not step:
            return
        url = self._sanitize_url(str(step.get("imgUrl") or ""))
        if not url:
            return
        self._loading_images.add(cache_key)
        task = _ImageFetchTask(task_no=str(task_no), step_key=str(step_key), url=url)
        task.finished.connect(self._on_image_loaded)
        task.failed.connect(self._on_image_failed)
        self._pending_image_tasks[cache_key] = task
        self._thread_pool.start(task)

    def _on_image_loaded(self, task_no: str, step_key: str, raw: Any, _content_type: str, thumb_data_url: str) -> None:
        cache_key = (str(task_no), str(step_key))
        try:
            self._loading_images.discard(cache_key)
            self._pending_image_tasks.pop(cache_key, None)
            if isinstance(raw, (bytes, bytearray)):
                self._full_image_cache[cache_key] = bytes(raw)
            if thumb_data_url:
                self._thumb_cache[cache_key] = str(thumb_data_url)
        except Exception:
            pass
        self._refresh_table_view()

    def _on_image_failed(self, task_no: str, step_key: str, _error: str) -> None:
        cache_key = (str(task_no), str(step_key))
        try:
            self._loading_images.discard(cache_key)
            self._pending_image_tasks.pop(cache_key, None)
        except Exception:
            pass
        self._refresh_table_view()

    def _find_step(self, task_no: str, step_key: str) -> Optional[Dict[str, Any]]:
        for it in self.current_items or []:
            if str(it.get("taskNo") or "") != str(task_no):
                continue
            steps = it.get("stepInfo") or []
            if not isinstance(steps, list):
                continue
            for idx, s in enumerate(steps):
                key = f"{idx}"
                if key == str(step_key):
                    return s if isinstance(s, dict) else None
        return None

    def _show_image_preview(self, task_no: str, step_key: str) -> None:
        cache_key = (str(task_no), str(step_key))
        raw = self._full_image_cache.get(cache_key)
        if raw is None:
            self._start_image_load(task_no, step_key)
            return
        try:
            pix = QPixmap()
            pix.loadFromData(raw)
        except Exception:
            return
        if pix.isNull():
            return

        screen = None
        try:
            screen = self.screen()
        except Exception:
            screen = None
        if screen is None:
            try:
                screen = QGuiApplication.primaryScreen()
            except Exception:
                screen = None
        if screen is not None:
            geom = screen.availableGeometry()
            max_w = max(600, int(geom.width() * 0.9))
            max_h = max(400, int(geom.height() * 0.9))
        else:
            max_w, max_h = 1200, 800

        pad = 40
        scaled = pix.scaled(
            max_w - pad,
            max_h - pad,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("图片预览")
        dlg.setMaximumSize(max_w, max_h)
        dlg_layout = QVBoxLayout(dlg)
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setPixmap(scaled)
        dlg_layout.addWidget(lbl)
        try:
            dlg.resize(min(max_w, scaled.width() + pad), min(max_h, scaled.height() + pad))
        except Exception:
            dlg.resize(min(max_w, 900), min(max_h, 700))
        dlg.exec()

    def _render_records_table_html(self, items: List[Dict[str, Any]], error_msg: Optional[str] = None) -> str:
        def escape(value):
            return html.escape("" if value is None else str(value), quote=True)

        def badge(text, role):
            return f"<span class='badge badge-{escape(role)}'>{escape(text)}</span>"

        task_status_map = {
            "-1": ("引导未就绪", "warn"),
            "-2": ("检测未就绪", "warn"),
            "1": ("待派单", "pending"),
            "2": ("进行中", "running"),
            "3": ("已完成", "done"),
            "4": ("手工通过", "done"),
        }
        step_status_map = {
            "1": ("未完成", "pending"),
            "2": ("已完成", "done"),
        }

        rows: List[str] = []
        for it in items or []:
            task_no = str(it.get("taskNo") or "")
            task_status_code = str(it.get("taskStatus") if it.get("taskStatus") is not None else "")
            task_status_text, task_role = task_status_map.get(task_status_code, ("未知", "pending"))
            process_no = str(it.get("processNo") or "")
            process_name = str(it.get("processName") or "")
            steps = it.get("stepInfo") or []
            step_count = len(steps) if isinstance(steps, list) else 0

            is_expanded = task_no in self.expanded_tasks
            toggle_text = "收起" if is_expanded else "展开"
            toggle_href = f"app://toggle_task?taskNo={escape(task_no)}"

            rows.append(
                "<tr>"
                f"<td><code>{escape(task_no)}</code></td>"
                f"<td>{badge(task_status_text, task_role)}</td>"
                f"<td><code>{escape(process_no)}</code></td>"
                f"<td>{escape(process_name)}</td>"
                f"<td>{escape(step_count)}</td>"
                f"<td><a class='action' href='{toggle_href}'>{toggle_text}</a></td>"
                "</tr>"
            )

            if is_expanded:
                step_rows: List[str] = []
                if isinstance(steps, list):
                    for idx, s in enumerate(steps):
                        step = s if isinstance(s, dict) else {}
                        step_no = str(step.get("stepNo") or "")
                        step_name = str(step.get("stepName") or "")
                        step_status_code = str(step.get("stepStatus") if step.get("stepStatus") is not None else "")
                        step_status_text, step_role = step_status_map.get(step_status_code, ("未知", "pending"))

                        step_key = str(idx)
                        step_toggle_href = f"app://toggle_step?taskNo={escape(task_no)}&stepKey={escape(step_key)}"
                        step_expanded = step_key in self.expanded_steps.get(task_no, set())
                        step_toggle_text = "收起详情" if step_expanded else "查看详情"

                        cache_key = (task_no, step_key)
                        thumb_url = self._thumb_cache.get(cache_key)
                        if thumb_url:
                            img_html = (
                                f"<a href='app://preview_img?taskNo={escape(task_no)}&stepKey={escape(step_key)}'>"
                                f"<img class='thumb' src='{escape(thumb_url)}' />"
                                "</a>"
                            )
                        elif cache_key in self._loading_images:
                            img_html = (
                                "<div class='thumb-placeholder'>"
                                "<div class='thumb-text'>图片加载中...</div>"
                                "</div>"
                            )
                        else:
                            img_html = (
                                "<div class='thumb-placeholder'>"
                                "<div class='thumb-text'>图片未加载</div>"
                                f"<a class='action' href='app://load_img?taskNo={escape(task_no)}&stepKey={escape(step_key)}'>加载图片</a>"
                                "</div>"
                            )

                        step_rows.append(
                            "<tr>"
                            f"<td><code>{escape(step_no)}</code></td>"
                            f"<td>{escape(step_name)}</td>"
                            f"<td>{badge(step_status_text, step_role)}</td>"
                            f"<td>{img_html}</td>"
                            f"<td><a class='action' href='{step_toggle_href}'>{step_toggle_text}</a></td>"
                            "</tr>"
                        )

                        if step_expanded:
                            raw_alg = step.get("algResult")
                            alg_text = "" if raw_alg is None else str(raw_alg)
                            pretty = ""
                            if alg_text and alg_text.lower() != "null":
                                try:
                                    obj = json.loads(alg_text)
                                    pretty = json.dumps(obj, ensure_ascii=False, indent=2)
                                except Exception:
                                    pretty = alg_text
                            else:
                                pretty = "无"
                            step_rows.append(
                                "<tr>"
                                f"<td colspan='5'><pre class='alg-result'>{escape(pretty)}</pre></td>"
                                "</tr>"
                            )

                nested = (
                    "<div class='nested-wrap'>"
                    "<table class='steps-table' width='100%' cellspacing='0' cellpadding='0'>"
                    "<colgroup>"
                    "<col style='width:10%;' />"
                    "<col style='width:34%;' />"
                    "<col style='width:12%;' />"
                    "<col style='width:34%;' />"
                    "<col style='width:10%;' />"
                    "</colgroup>"
                    "<thead><tr>"
                    "<th>步骤号</th><th>步骤名</th><th>状态</th><th>图片</th><th>详情</th>"
                    "</tr></thead>"
                    f"<tbody>{''.join(step_rows) if step_rows else '<tr><td colspan=5 class=empty-cell>暂无步骤</td></tr>'}</tbody>"
                    "</table>"
                    "</div>"
                )
                rows.append(
                    "<tr>"
                    f"<td colspan='6'>{nested}</td>"
                    "</tr>"
                )

        if error_msg:
            table_body = f"<div class='empty'>{escape(error_msg)}</div>"
        elif not rows:
            table_body = (
                "<div class='empty'>暂无记录</div>"
            )
        else:
            table_body = (
                "<div class='table-wrap'>"
                "<table class='records-table' width='100%' cellspacing='0' cellpadding='0'>"
                "<colgroup>"
                "<col style='width:18%;' />"
                "<col style='width:14%;' />"
                "<col style='width:12%;' />"
                "<col style='width:34%;' />"
                "<col style='width:8%;' />"
                "<col style='width:14%;' />"
                "</colgroup>"
                "<thead>"
                "<tr>"
                "<th>任务编码</th>"
                "<th>任务状态</th>"
                "<th>工序编号</th>"
                "<th>工序名称</th>"
                "<th>步骤数</th>"
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
            f".records-table th{{text-align:left;font-size:21px;color:{text_muted};font-weight:800;padding:12px 14px;border-bottom:1px solid {border};}}"
            f".records-table td{{font-size:21px;color:{text_primary};padding:14px;border-bottom:1px solid {border};vertical-align:top;}}"
            f"code{{font-family:Consolas,'Courier New',monospace;color:{text_primary};background:{deep_graphite};padding:2px 8px;border:1px solid {border};border-radius:8px;}}"
            ".badge{display:inline-block;font-size:13px;font-weight:800;border-radius:999px;padding:4px 10px;}"
            f".badge-warn{{border:1px solid {warning_yellow};background:rgba(255,179,71,0.16);color:{warning_yellow};}}"
            f".badge-pending{{border:1px solid {border};background:{deep_graphite};color:{text_muted};}}"
            f".badge-running{{border:1px solid {hover_orange};background:rgba(255,140,50,0.12);color:{hover_orange};}}"
            f".badge-done{{border:1px solid {success_green};background:rgba(60,195,122,0.18);color:{success_green};}}"
            f"a.action{{display:inline-block;text-decoration:none;color:{text_muted};border:1px solid {border_subtle};border-radius:8px;padding:6px 12px;font-weight:700;}}"
            f"a.action:hover{{background:{steel_grey};color:{text_primary};border-color:{hover_orange};}}"
            ".nested-wrap{margin-top:8px;margin-bottom:8px;padding:12px;border:1px solid rgba(255,255,255,0.06);border-radius:10px;background:rgba(0,0,0,0.06);}"
            ".steps-table{width:100%;border-collapse:collapse;}"
            f".steps-table th{{font-size:13px;color:{text_muted};padding:10px 12px;border-bottom:1px solid {border};}}"
            f".steps-table td{{font-size:13px;color:{text_primary};padding:12px;border-bottom:1px solid {border};vertical-align:top;}}"
            ".thumb{display:block;width:160px;max-height:120px;border-radius:10px;border:1px solid rgba(255,255,255,0.08);object-fit:cover;}"
            ".thumb-placeholder{width:160px;min-height:120px;border-radius:10px;border:1px dashed rgba(255,255,255,0.20);display:flex;flex-direction:column;gap:8px;align-items:center;justify-content:center;}"
            ".thumb-text{font-size:12px;color:rgba(255,255,255,0.65);}"
            ".alg-result{white-space:pre-wrap;background:rgba(0,0,0,0.20);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:10px;font-size:12px;}"
            ".empty-cell{padding:14px;color:rgba(255,255,255,0.65);text-align:center;}"
            f".empty{{padding:40px 10px;color:{text_muted};text-align:center;font-size:14px;}}"
            "</style>"
            "</head>"
            "<body>"
            f"{table_body}"
            "</body>"
            "</html>"
        )
