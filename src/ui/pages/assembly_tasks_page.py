"""
Assembly tasks page rendered as HTML in QTextBrowser.
"""

import html
import logging
from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QDialog,
    QPushButton,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTextBrowser,
    QVBoxLayout,
)
from PySide6.QtCore import Qt, QEvent, QUrl, QUrlQuery
from PySide6.QtCore import QTimer

from src.services.data_service import DataService
from src.services.algorithm_manager import AlgorithmManager
from src.services.task_payload_mapper import normalize_material_list, normalize_task_row
from ..components.pagination_widget import PaginationWidget
from ..components.material_warning_dialog import MaterialWarningDialog
from ..windows.process_execution_window import ProcessExecutionWindow
from ..windows.task_filter_window import TaskFilterWindow

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
        
        # Advanced filter state
        self.current_filters: Optional[Dict[str, Any]] = None
        self.filter_window: Optional[TaskFilterWindow] = None

        self._work_orders_by_code: Dict[str, Dict[str, Any]] = {}
        self.execution_window: Optional[ProcessExecutionWindow] = None

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
        title_label.installEventFilter(self)
        self.title_label = title_label

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

        self.filter_btn = QPushButton("高级过滤")
        self.filter_btn.setObjectName("advancedFilterBtn")
        self.filter_btn.setFixedSize(100, 36)
        self.filter_btn.clicked.connect(self._on_filter_clicked)
        header_layout.addWidget(self.filter_btn)

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
        # Fetch data based on filter mode
        if self.current_filters:
            result = self.data_service.search_work_orders(
                self.current_filters,
                page=self.current_page,
                page_size=self.page_size
            )
        else:
            result = self.data_service.get_work_orders_online(
                self.current_page, 
                self.page_size,
                status=self.current_status_filter,
            )
        raw_items = result.get("items", [])
        self.total_pages = result.get("total_pages", 1)
        error_msg = result.get("error")

        algo_lookup = self._build_algorithm_lookup()
        items = [normalize_task_row(r, algo_lookup) for r in (raw_items or [])]

        self._work_orders_by_code = {}
        for process_data in items:
            algo_code = process_data.get("algorithm_code", "")
            algo_name = process_data.get("algorithm_name", "")
            algo_version = process_data.get("algorithm_version", "")

            deploy_status = self.algorithm_manager.check_deployment_status(algo_name, algo_version)
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

    def _on_filter_clicked(self):
        if self.current_filters:
            self._on_filter_applied(None)
            return
        if self.filter_window is None:
            self.filter_window = TaskFilterWindow(self, theme=self.current_theme)
            self.filter_window.filter_applied.connect(self._on_filter_applied)
        self.filter_window.show()

    def _on_filter_applied(self, filters: Dict[str, Any]):
        self.current_filters = filters if filters else None
        self.current_page = 1
        if self.current_filters:
            self.status_filter.setEnabled(False)
            self.filter_btn.setText("清除过滤")
        else:
            self.status_filter.setEnabled(True)
            self.filter_btn.setText("高级过滤")
        self.load_data()

    def eventFilter(self, obj, event):
        try:
            if obj is getattr(self, "title_label", None) and event.type() == QEvent.Type.MouseButtonDblClick:
                modifiers = event.modifiers() if hasattr(event, "modifiers") else Qt.KeyboardModifier.NoModifier
                with_materials = not bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
                self._handle_hidden_mock_launch(with_materials=with_materials)
                return True
        except Exception:
            logger.exception("Hidden mock launch event handling failed")
        return super().eventFilter(obj, event)

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

        self._confirm_and_launch_process(data)

    def _confirm_and_launch_process(self, data: Dict[str, Any]) -> bool:
        material_list = data.get("material_list") or []
        if material_list:
            dialog = MaterialWarningDialog(data, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return False

        normalized = self._build_process_payload_from_task(data)
        return self._launch_execution_window(normalized)

    def _on_execution_window_closed(self) -> None:
        try:
            self.execution_window = None
        except Exception:
            pass
        try:
            QTimer.singleShot(0, self.load_data)
        except Exception:
            pass

    def _get_operator_name(self, fallback: str = "") -> str:
        operator_name = ""
        try:
            win = self.window()
            sm = getattr(win, "session_manager", None)
            if sm is not None:
                operator_name = str(sm.get_username() or "").strip()
        except Exception:
            operator_name = ""
        if operator_name:
            return operator_name
        return str(fallback or "").strip()

    def _build_process_payload_from_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        display_pid = ""
        craft_no = str(data.get("craft_code") or "").strip()
        process_code = str(data.get("process_code") or "").strip()
        if craft_no or process_code:
            display_pid = f"{craft_no}{('-' + process_code) if process_code else ''}"
        operator_name = self._get_operator_name(
            str(data.get("worker_name") or data.get("worker_code") or "").strip()
        )
        step_infos = data.get("step_infos")
        if not isinstance(step_infos, list) or not step_infos:
            step_infos = data.get("steps_detail")
        if not isinstance(step_infos, list):
            step_infos = []
        return {
            "name": data.get("work_order_code", ""),
            "title": data.get("craft_name") or data.get("process_name", ""),
            "version": data.get("craft_version", ""),
            "steps": len(step_infos),
            "algorithm_name": data.get("algorithm_name", ""),
            "algorithm_version": data.get("algorithm_version", ""),
            "operator_name": operator_name,
            "summary": f"Task: {data.get('work_order_code')}",
            "steps_detail": step_infos,
            "step_infos": step_infos,
            "pid": data.get("algorithm_code", None),
            "display_pid": display_pid,
            "task_no": data.get("work_order_code", ""),
            "craft_no": craft_no,
            "craft_name": data.get("craft_name", ""),
            "process_code": process_code,
            "process_name": data.get("process_name", ""),
            "process_desc": data.get("process_desc", ""),
            "prod_order_no": data.get("prod_order_no", ""),
            "material_list": data.get("material_list", []),
            "algorithm_code": data.get("algorithm_code", ""),
            "allow_mock_camera": bool(data.get("allow_mock_camera", False)),
            "mock_camera_text": data.get("mock_camera_text", "MOCK CAM"),
            "raw_work_order": data,
        }

    def _build_mock_process_data(self, with_materials: bool = True) -> Dict[str, Any]:
        task_no = "MOCK-TEST-001"
        material_list = normalize_material_list(self._build_mock_material_items(with_materials))
        steps_detail = [
            {
                "step_number": 1,
                "step_code": "MOCK-STEP-01",
                "step_name": "取料定位",
                "operation_guide": "放置测试件并确认定位区域，核对当前工单与物料。",
            },
            {
                "step_number": 2,
                "step_code": "MOCK-STEP-02",
                "step_name": "主件装配",
                "operation_guide": "根据引导完成主件装配，注意易错料方向。",
            },
            {
                "step_number": 3,
                "step_code": "MOCK-STEP-03",
                "step_name": "辅件复核",
                "operation_guide": "复核辅件数量、位号和方向，准备进入检测。",
            },
            {
                "step_number": 4,
                "step_code": "MOCK-STEP-04",
                "step_name": "外观检测",
                "operation_guide": "触发模拟检测，观察 PASS/FAIL 与步骤流转。",
            },
            {
                "step_number": 5,
                "step_code": "MOCK-STEP-05",
                "step_name": "完成确认",
                "operation_guide": "确认本轮任务完成，验证最终步骤可继续流转。",
            },
        ]
        operator_name = self._get_operator_name("测试用户")
        raw_work_order = {
            "work_order_code": task_no,
            "craft_code": "MOCK",
            "craft_name": "隐藏测试流程",
            "process_code": "TEST",
            "process_name": "模拟检测",
            "process_desc": "用于本地验证启动前提醒、右侧物料信息和模拟检测流程。",
            "prod_order_no": "MOCK-PO-001",
            "algorithm_code": "SIM-HIDDEN-001",
            "algorithm_name": "模拟检测流程",
            "algorithm_version": "mock",
            "step_infos": steps_detail,
            "material_list": material_list,
        }
        return {
            "name": task_no,
            "title": "隐藏测试流程（Mock）",
            "version": "mock",
            "steps": len(steps_detail),
            "work_order_code": task_no,
            "algorithm_name": "模拟检测流程",
            "algorithm_version": "mock",
            "operator_name": operator_name,
            "worker_name": operator_name,
            "summary": "Hidden Mock Launch",
            "step_infos": steps_detail,
            "steps_detail": steps_detail,
            "pid": "SIM-HIDDEN-001",
            "display_pid": "SIM-HIDDEN-001",
            "task_no": task_no,
            "craft_no": "MOCK",
            "craft_code": "MOCK",
            "craft_name": "隐藏测试流程-有物料" if with_materials else "隐藏测试流程-无物料",
            "craft_version": "mock",
            "process_code": "TEST",
            "process_name": "模拟检测",
            "process_desc": "用于本地验证启动前提醒、右侧物料信息和模拟检测流程。",
            "prod_order_no": "MOCK-PO-001",
            "material_list": material_list,
            "allow_mock_camera": True,
            "mock_camera_text": "MOCK CAM",
            "algorithm_code": "SIM-HIDDEN-001",
            "raw_work_order": raw_work_order,
        }

    def _build_mock_material_items(self, with_materials: bool) -> list[dict]:
        if not with_materials:
            return []
        return [
            {
                "assembly_number": "A01",
                "position_number": "U1",
                "model_no": "TX-MAIN-01",
                "polarity_direction": "缺口朝上",
                "material_no": "9000000929403",
                "material_name": "主控芯片",
                "material_quantity": 1,
                "material_unit": "件",
                "error_prevention_mark": "错",
            },
            {
                "assembly_number": "A02",
                "position_number": "C3/C4",
                "model_no": "CAP-10UF",
                "polarity_direction": "白线朝右",
                "material_no": "9000000929404",
                "material_name": "电解电容",
                "material_quantity": 2,
                "material_unit": "件",
                "error_prevention_mark": "",
            },
            {
                "assembly_number": "A03",
                "position_number": "R12/R13/R14",
                "model_no": "RES-4K7-1%-0603",
                "polarity_direction": "无方向要求",
                "material_no": "9000000929405",
                "material_name": "精密电阻组件",
                "material_quantity": 3,
                "material_unit": "件",
                "error_prevention_mark": "",
            },
            {
                "assembly_number": "A04",
                "position_number": "J1",
                "model_no": "CONN-USB-TYPEC-16P",
                "polarity_direction": "开口朝外壳右侧，注意贴合边缘",
                "material_no": "9000000929406",
                "material_name": "Type-C 接口座",
                "material_quantity": 1,
                "material_unit": "件",
                "error_prevention_mark": "方向易错",
            },
            {
                "assembly_number": "A05",
                "position_number": "D5",
                "model_no": "LED-RED-0603-HL",
                "polarity_direction": "三角丝印对应负极，灯珠缺口朝左上",
                "material_no": "9000000929407",
                "material_name": "状态指示灯",
                "material_quantity": 1,
                "material_unit": "件",
                "error_prevention_mark": "",
            },
            {
                "assembly_number": "A06",
                "position_number": "U7",
                "model_no": "DRV-MOTOR-48PIN-QFN",
                "polarity_direction": "1脚圆点朝右下，芯片文字正向可读",
                "material_no": "9000000929408",
                "material_name": "电机驱动控制芯片长名称测试项",
                "material_quantity": 1,
                "material_unit": "件",
                "error_prevention_mark": "错",
            },
            {
                "assembly_number": "A07",
                "position_number": "TP1/TP2/TP3/TP4",
                "model_no": "TEST-PAD-GOLD",
                "polarity_direction": "无方向要求",
                "material_no": "9000000929409",
                "material_name": "测试焊盘保护片",
                "material_quantity": 4,
                "material_unit": "片",
                "error_prevention_mark": "",
            },
            {
                "assembly_number": "A08",
                "position_number": "L2",
                "model_no": "IND-22UH-SMD-LARGE",
                "polarity_direction": "顶部丝印需与板上白框长边平行",
                "material_no": "9000000929410",
                "material_name": "功率电感",
                "material_quantity": 1,
                "material_unit": "件",
                "error_prevention_mark": "",
            },
            {
                "assembly_number": "A09",
                "position_number": "F1",
                "model_no": "FUSE-RESET-1A-1206",
                "polarity_direction": "保险丝文字朝上，靠近输入端一侧安装",
                "material_no": "9000000929411",
                "material_name": "可恢复保险丝",
                "material_quantity": 1,
                "material_unit": "件",
                "error_prevention_mark": "复核",
            },
            {
                "assembly_number": "A10",
                "position_number": "CN8-LEFT-SIDE-EXTENSION",
                "model_no": "CABLE-HARNESS-POWER-SIGNAL-MIXED",
                "polarity_direction": "线束卡扣朝外，红线靠板边，插入到底后轻拉确认锁止",
                "material_no": "9000000929412",
                "material_name": "外接电源与信号混合线束总成长文本滚动测试项",
                "material_quantity": 1,
                "material_unit": "套",
                "error_prevention_mark": "",
            },
        ]

    def _launch_execution_window(self, process_data: Dict[str, Any]) -> bool:
        current_window = getattr(self, "execution_window", None)
        try:
            if current_window is not None and current_window.isVisible():
                logger.info("Skip launching another process window because one is already open")
                return False
        except Exception:
            pass
        self.execution_window = ProcessExecutionWindow(
            process_data,
            None,
            camera_service=self.camera_service,
        )
        try:
            self.execution_window.closed.connect(self._on_execution_window_closed)
        except Exception:
            pass
        self.execution_window.show_centered()
        return True

    def _handle_hidden_mock_launch(self, with_materials: bool = True) -> None:
        process_data = self._build_mock_process_data(with_materials=with_materials)
        launched = self._confirm_and_launch_process(process_data)
        if launched:
            logger.info(
                "Hidden mock process launched from AssemblyTasksPage title, with_materials=%s",
                with_materials,
            )

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
                f"<a class='btn-link' href='{href}'>"
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
                action_parts.append(action_disabled("不可操作"))
            elif status_code in {"1", "2"}:
                if deployed:
                    action_parts.append(action_button("启动", f"app://start?work_order={task_no}", "primary"))
                else:
                    action_parts.append(action_disabled("启动", deploy_label or "未部署"))
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
