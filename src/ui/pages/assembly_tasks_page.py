"""
Assembly tasks page rendered as HTML in QTextBrowser.
"""

import html
import logging
from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTextBrowser,
    QVBoxLayout,
)
from PySide6.QtCore import Qt, QUrl, QUrlQuery
from PySide6.QtCore import QTimer

from src.services.data_service import DataService
from src.services.algorithm_manager import AlgorithmManager
from ..components.pagination_widget import PaginationWidget
from ..windows.process_execution_window import ProcessExecutionWindow

logger = logging.getLogger(__name__)


class AssemblyTasksPage(QFrame):
    def __init__(self, parent=None, camera_service=None, initial_theme: str = "dark"):
        super().__init__(parent)
        self.setObjectName("processPage")
        self.current_theme = initial_theme if initial_theme in {"dark", "light"} else "dark"
        self.camera_service = camera_service
        self.data_service = DataService()
        self.algorithm_manager = AlgorithmManager()

        self.current_page = 1
        self.page_size = 10
        self.total_pages = 1
        self.current_status_filter = None

        self._work_orders_by_code: Dict[str, Dict[str, Any]] = {}

        self.setup_colors(self.current_theme)
        self.init_ui()
        self.load_data()

    def apply_theme(self, theme: str) -> None:
        if theme not in {"dark", "light"}:
            return
        if theme == getattr(self, "current_theme", "dark"):
            return
        self.current_theme = theme
        self.setup_colors(theme)
        self.load_data()

    def setup_colors(self, theme_name: str = "dark"):
        theme_name = theme_name if theme_name in {"dark", "light"} else "dark"
        try:
            from ...core.config import get_config
            from ..styles.theme_loader import resolve_theme_colors

            config = get_config()
            base_colors = dict(getattr(getattr(config, "ui", None), "colors", {}) or {})
            colors = resolve_theme_colors(theme_name, base_colors)

            self.color_deep_graphite = colors.get("deep_graphite", "#1A1D23")
            self.color_steel_grey = colors.get("steel_grey", "#1F232B")
            self.color_dark_border = colors.get("dark_border", "#242831")
            self.color_arctic_white = colors.get("arctic_white", "#F2F4F8")
            self.color_cool_grey = colors.get("cool_grey", "#8C92A0")
            self.color_hover_orange = colors.get("hover_orange", "#FF8C32")
            self.color_success_green = colors.get("success_green", "#3CC37A")
            self.color_error_red = colors.get("error_red", "#E85454")
            self.color_warning_yellow = colors.get("warning_yellow", "#FFB347")
            self.color_border_subtle = colors.get("border_subtle", self.color_dark_border)
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
                self.color_border_subtle = "#D1D7E6"
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
                self.color_border_subtle = "#3A3A3A"

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header_frame = QFrame()
        header_frame.setObjectName("processHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("装配引导与检测")
        title_label.setObjectName("processTitle")

        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.status_filter = QComboBox()
        self.status_filter.setObjectName("processFilterCombo")
        self.status_filter.addItem("全部", None)
        self.status_filter.addItem("引导未就绪", "-1")
        self.status_filter.addItem("检测未就绪", "-2")
        self.status_filter.addItem("待执行", "1")
        self.status_filter.addItem("执行中", "2")
        self.status_filter.addItem("已完成", "3")
        self.status_filter.addItem("手工通过", "4")
        self.status_filter.setFixedWidth(120)
        self.status_filter.currentIndexChanged.connect(self._on_filter_changed)

        self.page_size_filter = QComboBox()
        self.page_size_filter.setObjectName("processFilterCombo")
        self.page_size_filter.addItem("10/页", 10)
        self.page_size_filter.addItem("20/页", 20)
        self.page_size_filter.addItem("50/页", 50)
        self.page_size_filter.setFixedWidth(90)
        self.page_size_filter.setCurrentIndex(0)
        self.page_size_filter.currentIndexChanged.connect(self._on_page_size_changed)
        header_layout.addWidget(self.page_size_filter)
        header_layout.addWidget(self.status_filter)

        layout.addWidget(header_frame)

        self.html_viewer = QTextBrowser()
        self.html_viewer.setObjectName("processHtmlViewer")
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
        self.pagination.page_changed.connect(self._on_page_changed)
        layout.addWidget(self.pagination, 0, Qt.AlignmentFlag.AlignCenter)

    def load_data(self):
        result = self.data_service.get_work_orders_online(
            self.current_page,
            self.page_size,
            status=self.current_status_filter,
        )
        raw_items = result.get("items", [])
        self.total_pages = result.get("total_pages", 1)
        error_msg = result.get("error")

        algo_lookup = self._build_algorithm_lookup()
        items = [self._normalize_task_row(r, algo_lookup) for r in (raw_items or [])]

        self._work_orders_by_code = {}
        for process_data in items:
            algo_code = process_data.get("algorithm_code", "")
            algo_name = process_data.get("algorithm_name", "")
            algo_version = process_data.get("algorithm_version", "")

            deploy_status = self.algorithm_manager.check_deployment_status(algo_name, algo_version, algo_code)
            process_data["deployment_status"] = deploy_status

            work_order_code = str(process_data.get("work_order_code", "")).strip()
            if work_order_code:
                self._work_orders_by_code[work_order_code] = process_data

        self.pagination.set_total_pages(self.total_pages)
        self.pagination.set_current_page(self.current_page)
        self.html_viewer.setHtml(self._render_work_orders_table_html(items, error_msg))

    def showEvent(self, event):
        super().showEvent(event)
        try:
            QTimer.singleShot(0, self.load_data)
        except Exception:
            pass

    def _build_algorithm_lookup(self) -> Dict[str, Dict[str, str]]:
        lookup: Dict[str, Dict[str, str]] = {}
        try:
            algos = self.data_service.get_algorithms()
            for a in algos or []:
                algo_id = str(a.get("code") or a.get("id") or "").strip()
                if not algo_id:
                    continue
                lookup[algo_id] = {
                    "name": str(a.get("name") or "").strip(),
                    "version": str(a.get("version") or "").strip(),
                }
        except Exception:
            pass
        return lookup

    def _normalize_task_row(self, row: Dict[str, Any], algo_lookup: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        task_no = str(row.get("task_no") or row.get("work_order_code") or "").strip()
        craft_no = str(row.get("craft_no") or row.get("craft_code") or "").strip()
        craft_version = str(row.get("craft_version") or "").strip()
        craft_name = str(row.get("craft_name") or "").strip()
        process_code = str(row.get("process_code") or "").strip()
        process_name = str(row.get("process_name") or row.get("process") or "").strip()
        worker_name = str(row.get("worker_name") or "").strip()
        status = row.get("status")
        status_str = str(status) if status is not None else ""
        algorithm_id = str(row.get("algorithm_id") or row.get("algorithm_code") or "").strip()
        step_infos = row.get("step_infos") or row.get("steps") or row.get("step_list") or []

        algo_meta = algo_lookup.get(algorithm_id, {}) if algorithm_id else {}
        algorithm_name = (algo_meta.get("name") or "").strip() or algorithm_id
        algorithm_version = (algo_meta.get("version") or "").strip()

        return {
            "work_order_code": task_no,
            "craft_code": craft_no,
            "craft_version": craft_version,
            "craft_name": craft_name,
            "process_code": process_code,
            "process_name": process_name,
            "start_time": row.get("start_time"),
            "end_time": row.get("end_time"),
            "worker_code": row.get("worker_code"),
            "worker_name": worker_name,
            "status": status_str,
            "algorithm_code": algorithm_id,
            "algorithm_name": algorithm_name,
            "algorithm_version": algorithm_version,
            "step_infos": step_infos if isinstance(step_infos, list) else [],
            "raw_task": row,
        }

    def _on_filter_changed(self, index):
        self.current_status_filter = self.status_filter.currentData()
        self.current_page = 1
        self.load_data()

    def _on_page_size_changed(self, index):
        try:
            size = self.page_size_filter.currentData()
            self.page_size = int(size) if size else 10
        except Exception:
            self.page_size = 10
        self.current_page = 1
        self.load_data()

    def _on_page_changed(self, page):
        self.current_page = page
        self.load_data()

    def on_html_anchor_clicked(self, url: QUrl):
        if url.scheme() != "app":
            return
        query = QUrlQuery(url)
        work_order_code = query.queryItemValue("work_order")
        if not work_order_code:
            return
        if url.host() == "start":
            self._start_process_by_work_order(work_order_code)
            return
        if url.host() == "manual_pass":
            try:
                data = self._work_orders_by_code.get(str(work_order_code))
                status = str((data or {}).get("status") or "")
                if status in {"3", "4"}:
                    return
            except Exception:
                pass
            reply = QMessageBox.question(
                self,
                "确认人工通过",
                f"确认将任务 {work_order_code} 标记为人工通过？\n\n人工通过将绕过检测流程。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self._manual_pass_work_order(work_order_code)
            return

    def _manual_pass_work_order(self, work_order_code: str) -> None:
        data = self._work_orders_by_code.get(str(work_order_code))
        if not data:
            return
        if str(data.get("status")) in {"3", "4"}:
            return
        data["status"] = "4"
        try:
            from src.services.result_report_service import ResultReportService
            ResultReportService().enqueue_task_status_update(str(work_order_code), 4)
        except Exception:
            pass
        try:
            if self.current_status_filter is not None and str(self.current_status_filter) != "4":
                try:
                    del self._work_orders_by_code[str(work_order_code)]
                except Exception:
                    pass
        except Exception:
            pass
        self.html_viewer.setHtml(self._render_work_orders_table_html(list(self._work_orders_by_code.values()), None))

    def _start_process_by_work_order(self, work_order_code: str):
        data = self._work_orders_by_code.get(str(work_order_code))
        if not data:
            return

        display_pid = ""
        craft_no = str(data.get("craft_code") or "").strip()
        process_code = str(data.get("process_code") or "").strip()
        if craft_no or process_code:
            display_pid = f"{craft_no}{('-' + process_code) if process_code else ''}"

        operator_name = ""
        try:
            win = self.window()
            sm = getattr(win, "session_manager", None)
            if sm is not None:
                operator_name = str(sm.get_username() or "").strip()
        except Exception:
            operator_name = ""
        if not operator_name:
            operator_name = str(data.get("worker_name") or data.get("worker_code") or "").strip()

        normalized = {
            "name": data.get("work_order_code", ""),
            "title": data.get("craft_name") or data.get("process_name", ""),
            "version": data.get("craft_version", ""),
            "steps": len(data.get("step_infos", []) or []),
            "algorithm_name": data.get("algorithm_name", ""),
            "algorithm_version": data.get("algorithm_version", ""),
            "operator_name": operator_name,
            "summary": f"Task: {data.get('work_order_code')}",
            "steps_detail": data.get("step_infos", []),
            "pid": data.get("algorithm_code", None),
            "display_pid": display_pid,
            "task_no": data.get("work_order_code", ""),
            "craft_no": craft_no,
            "process_code": process_code,
            "algorithm_code": data.get("algorithm_code", ""),
            "raw_work_order": data,
        }

        self.execution_window = ProcessExecutionWindow(
            normalized,
            None,
            camera_service=self.camera_service,
        )
        try:
            self.execution_window.closed.connect(self._on_execution_window_closed)
        except Exception:
            pass
        self.execution_window.show_centered()

    def _on_execution_window_closed(self) -> None:
        try:
            self.execution_window = None
        except Exception:
            pass
        try:
            QTimer.singleShot(0, self.load_data)
        except Exception:
            pass

    def _render_work_orders_table_html(self, items: list[dict], error_msg: Optional[str]) -> str:
        def escape(value):
            return html.escape("" if value is None else str(value), quote=True)

        def badge(text, role):
            return f"<span class='badge badge-{escape(role)}'>{escape(text)}</span>"

        def action_button(text: str, href: str, variant: str) -> str:
            extra = ""
            if text == "启动" and variant == "primary":
                extra = " btn-start"
            elif text == "人工通过" and variant == "success":
                extra = " btn-manual"
            return (
                f"<a class='btn-link' href='{escape(href)}'>"
                f"<span class='btn btn-{escape(variant)}{extra}'>{escape(text)}</span>"
                "</a>"
            )

        def action_disabled(text: str, suffix: str = "") -> str:
            full = f"{text}{(' · ' + suffix) if suffix else ''}"
            return f"<span class='btn btn-disabled'>{escape(full)}</span>"

        status_map = {
            "-1": ("引导未就绪", "notready"),
            "-2": ("检测未就绪", "notready"),
            "1": ("待执行", "pending"),
            "2": ("进行中", "running"),
            "3": ("已完成", "done"),
            "4": ("手工通过", "done"),
        }

        rows = []
        for it in items or []:
            task_no = it.get("work_order_code", "")
            craft_code = it.get("craft_code", "")
            craft_version = it.get("craft_version", "")
            craft_name = it.get("craft_name") or it.get("process_name") or ""
            process_name = it.get("process_name", "")
            worker_name = it.get("worker_name", "")
            worker_code = it.get("worker_code", "")
            start_time = it.get("start_time")
            end_time = it.get("end_time")

            algorithm_name = it.get("algorithm_name", "")
            algorithm_version = it.get("algorithm_version", "")

            status_code = str(it.get("status", "1"))
            status_text, status_role = status_map.get(status_code, ("未知状态", "pending"))

            deploy = it.get("deployment_status", {}) or {}
            deploy_label = deploy.get("label", "") or "Unknown"
            deployed = bool(deploy.get("deployed", False))

            action_parts = []
            if status_code in {"-1", "-2"}:
                action_parts.append(action_button("人工通过", f"app://manual_pass?work_order={task_no}", "success"))
            elif status_code in {"1", "2"}:
                if deployed:
                    action_parts.append(action_button("启动", f"app://start?work_order={task_no}", "primary"))
                else:
                    action_parts.append(action_disabled("启动", deploy_label or "未部署"))
                action_parts.append(action_button("人工通过", f"app://manual_pass?work_order={task_no}", "success"))
            elif status_code in {"3", "4"}:
                action_parts.append(action_disabled("不可操作"))
            else:
                action_parts.append(action_disabled("不可操作"))

            wrapped_actions = []
            for i, part in enumerate(action_parts):
                mb = "20px" if i < (len(action_parts) - 1) else "0"
                wrapped_actions.append(f"<div class='action-item' style='margin-bottom:{mb};'>{part}</div>")
            action = f"<div class='actions'>{''.join(wrapped_actions)}</div>"

            craft_block = (
                "<div class='process-title'>"
                f"{escape(craft_name or '-')} <span class='muted'>· {escape(process_name or '')}</span>"
                "</div>"
                f"<div class='process-code'>{escape(craft_code or '-')} · {escape(craft_version or '-')}</div>"
            )
            time_block = (
                f"<div class='process-title'>{escape(start_time or '-')}</div>"
                f"<div class='process-code'>{escape(end_time or '-')}</div>"
            )
            algo_block = (
                f"<div class='process-title'>{escape(algorithm_name or '-')}</div>"
                f"<div class='process-code'>{escape(algorithm_version or '')}</div>"
            )
            worker_block = (
                f"<div class='process-title'>{escape(worker_name or '-')}</div>"
                f"<div class='process-code'>{escape(worker_code or '')}</div>"
            )

            rows.append(
                "<tr>"
                f"<td><code>{escape(task_no)}</code></td>"
                f"<td>{craft_block}</td>"
                f"<td>{worker_block}</td>"
                f"<td>{time_block}</td>"
                f"<td>{algo_block}</td>"
                f"<td>{badge(status_text, status_role)}</td>"
                f"<td>{badge(deploy_label, 'deploy-ok' if deployed else 'deploy-warn')}</td>"
                f"<td>{action}</td>"
                "</tr>"
            )

        if error_msg:
            table_body = f"<div class='empty'>{escape(error_msg)}</div>"
        elif not rows:
            table_body = "<div class='empty'>暂无任务</div>"
        else:
            table_body = (
                "<div class='table-wrap'>"
                "<table class='tasks-table' width='100%' cellspacing='0' cellpadding='0'>"
                "<colgroup>"
                "<col style='width:16%;' />"
                "<col style='width:26%;' />"
                "<col style='width:12%;' />"
                "<col style='width:16%;' />"
                "<col style='width:16%;' />"
                "<col style='width:8%;' />"
                "<col style='width:10%;' />"
                "<col style='width:8%;' />"
                "</colgroup>"
                "<thead>"
                "<tr>"
                "<th>任务编码</th>"
                "<th>工艺/工序</th>"
                "<th>装配工人</th>"
                "<th>计划时间</th>"
                "<th>算法</th>"
                "<th>状态</th>"
                "<th>资源</th>"
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
            ".tasks-table{width:100%;border-collapse:collapse;background:transparent;}"
            f"th{{text-align:left;font-size:21px;color:{text_muted};font-weight:800;padding:16px 16px;border-bottom:1px solid {border};}}"
            f"td{{font-size:16px;color:{text_primary};padding:16px;border-bottom:1px solid {border};vertical-align:top;}}"
            f"code{{font-family:Consolas,'Courier New',monospace;font-size:15px;color:{text_primary};background:{deep_graphite};padding:3px 10px;border:1px solid {border};border-radius:10px;}}"
            f".process-title{{font-size:17px;font-weight:800;color:{text_primary};margin-bottom:6px;}}"
            f".process-code{{font-size:14px;color:{text_muted};}}"
            f".muted{{font-size:14px;color:{text_muted};font-weight:700;}}"
            ".badge{display:inline-block;font-size:14px;font-weight:800;border-radius:999px;padding:5px 12px;}"
            f".badge-notready{{border:1px solid {warning_yellow};background:rgba(255,179,71,0.16);color:{warning_yellow};}}"
            f".badge-pending{{border:1px solid {border};background:{deep_graphite};color:{text_muted};}}"
            f".badge-running{{border:1px solid {hover_orange};background:rgba(255,140,50,0.12);color:{hover_orange};}}"
            f".badge-done{{border:1px solid {success_green};background:rgba(60,195,122,0.18);color:{success_green};}}"
            f".badge-deploy-ok{{border:1px solid {success_green};background:rgba(60,195,122,0.12);color:{success_green};}}"
            f".badge-deploy-warn{{border:1px solid {warning_yellow};background:rgba(255,179,71,0.12);color:{warning_yellow};}}"
            ".actions{width:180px;}"
            ".btn-link{display:block;width:180px;text-decoration:none;}"
            f".btn{{display:block;width:180px;box-sizing:border-box;border-radius:14px;padding:12px 18px;font-size:17px;font-weight:900;letter-spacing:0.2px;text-align:center;}}"
            f".btn-primary{{border:1px solid {hover_orange};background:rgba(255,140,50,0.10);color:{hover_orange};}}"
            f".btn-primary:hover{{background:rgba(255,140,50,0.18);color:{text_primary};}}"
            f".btn-start{{background:{hover_orange};border:1px solid {hover_orange};color:#FFFFFF;box-shadow:0 8px 18px rgba(0,0,0,0.30);}}"
            f".btn-start:hover{{filter:brightness(1.05);color:#FFFFFF;}}"
            f".btn-success{{border:1px solid {success_green};background:rgba(60,195,122,0.12);color:{success_green};}}"
            f".btn-success:hover{{background:rgba(60,195,122,0.20);color:{text_primary};}}"
            f".btn-manual{{background:{success_green};border:1px solid {success_green};color:#FFFFFF;box-shadow:0 8px 18px rgba(0,0,0,0.26);}}"
            f".btn-manual:hover{{filter:brightness(1.05);color:#FFFFFF;}}"
            f".btn-disabled{{border:1px solid {border_subtle};background:{deep_graphite};color:{text_muted};opacity:0.78;}}"
            f".empty{{padding:48px 12px;color:{text_muted};text-align:center;font-size:17px;font-weight:700;}}"
            "</style>"
            "</head>"
            "<body>"
            f"{table_body}"
            "</body>"
            "</html>"
        )
