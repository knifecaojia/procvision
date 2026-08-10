import logging
from typing import Optional, Dict, Any, List, Literal
from pathlib import Path
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGraphicsOpacityEffect, QSizePolicy, QTextEdit,
)
from PySide6.QtCore import Qt, Signal, QTimer, QEvent, QThread, QRect, QSize
from PySide6.QtGui import QImage, QResizeEvent, QFontDatabase, QFont
from datetime import datetime
import numpy as np
import json

try:
    from ..core.config import get_config
except Exception:
    from src.core.config import get_config

from ..styles import (
    ThemeLoader,
    build_theme_variables,
    load_user_theme_preference,
    resolve_theme_colors,
)

from .ui_builder_mixin import UIBuilderMixin, StepStatus, DetectionStatus
from .split_view_mixin import SplitViewMixin
from .camera_mixin import CameraMixin
from .process_camera_panel_mixin import ProcessCameraPanelMixin
from .guide_image_mixin import GuideImageMixin
from .detection_mixin import (
    NgFlashController,
    save_local_record,
    get_step_code_from_payload,
    run_simulated_detection,
    handle_external_detection,
)
from .auto_detect_mixin import AutoDetectController

logger = logging.getLogger(__name__)


@dataclass
class ProcessStep:
    id: int
    name: str
    description: str
    status: StepStatus = 'pending'


class ProcessExecutionWindow(
    ProcessCameraPanelMixin,
    UIBuilderMixin,
    SplitViewMixin,
    CameraMixin,
    GuideImageMixin,
    QWidget,
):
    closed = Signal()

    def __init__(self, process_data: Dict[str, Any], parent: Optional[QWidget] = None, camera_service=None):
        super().__init__(parent)
        self.process_data = process_data
        self.camera_service = camera_service

        self.preview_worker = None
        self.camera_active = False
        self.available_cameras = []

        self.product_sn = str(process_data.get("task_no") or process_data.get("name") or "")
        self.order_number = str(process_data.get("display_pid") or process_data.get('pid', process_data.get('name', 'ME-ASM-2024-001')))
        self.operator_name = str(
            process_data.get("operator_name") or process_data.get("username")
            or process_data.get("worker_name") or process_data.get("operator") or ""
        ).strip() or "—"
        self.network_status: Literal['online', 'offline'] = "online"
        self.total_steps = len(process_data.get('steps_detail', [])) or process_data.get('steps', 12)
        self.current_step_index = 0
        self.detection_status: DetectionStatus = "idle"
        self.is_simulated = self._is_simulated_process()
        self._last_qimage: Optional[QImage] = None
        self._last_display_size = None
        self.detection_boxes: List[QRect] = []
        self.detection_labels: List[str] = []
        self.preview_annotation_regions: List[Dict[str, Any]] = []
        self.preview_annotation_boxes: List[QRect] = []
        self.preview_annotation_labels: List[str] = []
        self.preview_annotation_status: DetectionStatus = "idle"
        self.preview_annotation_visible = False
        self.auto_detect_ng_latched_step_code: Optional[str] = None
        self.auto_detect_ng_reported = False
        self.auto_detect_last_result_status: str = ""
        self.auto_detect_task_seq = 0
        self._overlay_dismissed = False
        self.auto_start_next = self._read_auto_start_next_setting()
        self.result_prompt_position = self._read_result_prompt_position()
        self.draw_boxes_ok, self.draw_boxes_ng = self._read_draw_box_settings()
        self.ok_toast_duration = self._read_ok_toast_duration()
        self.split_layout_mode = self._load_layout_preference()

        self.overlay_widget: Optional[QWidget] = None
        self.preview_annotation_widget: Optional[QWidget] = None
        self.pass_overlay: Optional[QWidget] = None
        self.fail_overlay: Optional[QWidget] = None

        self.custom_font_family = "Arial"
        self.custom_font = QFont(self.custom_font_family)
        self._load_custom_font()
        self.config = get_config()
        self.colors = getattr(self.config.ui, "colors", {})
        self.current_theme = load_user_theme_preference()
        self.theme_loader = ThemeLoader(theme_name=self.current_theme)

        self.steps: List[ProcessStep] = []
        task_steps = process_data.get("steps_detail") or process_data.get("step_infos")
        if isinstance(task_steps, list) and task_steps:
            try:
                self.steps = self._initialize_steps_from_task(task_steps)
            except Exception as e:
                logger.warning("Failed to load steps from task: %s", e)
                self.steps = []
        if not self.steps:
            try:
                self.steps = self._initialize_steps_from_algorithm()
            except Exception as e:
                logger.warning("Failed to load steps from algorithm: %s", e)
                self.steps = self._initialize_steps()
        if not self.steps:
            self.steps = self._initialize_steps()

        self.total_steps = len(self.steps)
        self.current_instruction = self.steps[0].description if self.steps else "No steps available"
        self._debug_input_enabled = False
        self._debug_image_path: Optional[str] = None
        self._guide_qimages: Dict[int, QImage] = {}
        self._guide_workers: Dict[int, QThread] = {}
        self._guide_errors: Dict[int, str] = {}
        self._closing: bool = False
        self._task_status_started: bool = False
        self._ng_flash = NgFlashController(self)
        self.auto_detect_active = False
        self._auto_detect_controller = AutoDetectController(self)

        self.setWindowTitle(f"工艺执行 - {process_data.get('name', '')}")
        self.setMinimumSize(1280, 720)
        self.resize(1800, 900)
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.detection_timer: Optional[QTimer] = None
        self.advance_timer: Optional[QTimer] = None

        self.init_ui()
        self._apply_theme()
        self.setup_connections()

        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
        self.reset_camera_placeholder()
        QTimer.singleShot(0, lambda: self._ensure_guide_for_step(self.current_step_index, preload_next=True))

        logger.info("ProcessExecutionWindow initialized for process: %s", process_data.get('name'))
        QTimer.singleShot(0, self._align_overlay_geometry)

    def _load_custom_font(self) -> None:
        try:
            font_path = Path(__file__).resolve().parents[2] / "assets" / "SourceHanSansSC-Normal-2.otf"
        except Exception:
            font_path = Path("src/assets/SourceHanSansSC-Normal-2.otf").resolve()
        if not font_path.exists():
            logger.warning("Custom font file not found: %s", font_path)
            self.setFont(self.custom_font)
            return
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id == -1:
            logger.warning("Failed to load custom font from: %s", font_path)
            self.setFont(self.custom_font)
            return
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.custom_font = QFont(font_family)
        self.custom_font_family = font_family
        self.setFont(self.custom_font)
        logger.info("Custom font applied: %s", font_family)

    def _apply_theme(self) -> None:
        try:
            variables = build_theme_variables(
                resolve_theme_colors(getattr(self, "current_theme", "dark"), self.colors),
                self.custom_font_family,
            )
            self.theme_loader.apply(self, "process_execution_window", variables=variables)
        except FileNotFoundError:
            logger.error("Process execution stylesheet missing")

    def _initialize_steps_from_algorithm(self) -> List[ProcessStep]:
        from src.runner.engine import RunnerEngine
        runner = RunnerEngine()
        algo_name = str(self.process_data.get("algorithm_name") or "").strip()
        algo_ver = str(self.process_data.get("algorithm_version") or "").strip()
        if not algo_name or not algo_ver:
            return []
        info_start = datetime.now()
        info = {}
        try:
            info = runner.get_algorithm_info(algo_name, algo_ver)
        except Exception as e:
            logger.warning("Primary info fetch failed: %s", e)
        logger.info("get_algorithm_info took %.2fms", (datetime.now() - info_start).total_seconds() * 1000)
        info_block = info.get("info", info)
        try:
            if "algorithm_name" in info_block:
                self.process_data["algorithm_name"] = info_block.get("algorithm_name")
            if "algorithm_version" in info_block:
                self.process_data["algorithm_version"] = info_block.get("algorithm_version")
        except Exception:
            pass
        algo_steps = info_block.get("steps", [])
        if not algo_steps:
            return []
        steps: List[ProcessStep] = []
        for i, item in enumerate(algo_steps):
            step_number = item.get('step_number', i + 1)
            step_name = item.get('step_name', f"步骤 {step_number}")
            operation_guide = item.get('operation_guide', step_name)
            status: StepStatus = 'current' if i == 0 else 'pending'
            steps.append(ProcessStep(
                id=i, name=(step_name or f"步骤 {step_number}"),
                description=operation_guide, status=status,
            ))
        self.process_data['steps_detail'] = algo_steps
        return steps

    def _initialize_steps_from_task(self, task_steps: List[Dict[str, Any]]) -> List[ProcessStep]:
        steps: List[ProcessStep] = []
        normalized_steps: List[Dict[str, Any]] = []
        for i, item in enumerate(task_steps):
            step_number_raw = item.get("step_number") or item.get("step_code")
            try:
                step_number = int(step_number_raw) if step_number_raw is not None and str(step_number_raw).strip() else (i + 1)
            except Exception:
                step_number = i + 1
            step_name = item.get("step_name") or item.get("name") or f"步骤 {step_number}"
            operation_guide = item.get("operation_guide") or item.get("step_content") or item.get("description") or step_name
            normalized = dict(item) if isinstance(item, dict) else {}
            normalized["step_number"] = step_number
            normalized["step_name"] = str(step_name)
            normalized["operation_guide"] = str(operation_guide)
            normalized_steps.append(normalized)
            status: StepStatus = "current" if i == 0 else "pending"
            steps.append(ProcessStep(id=i, name=str(step_name), description=str(operation_guide), status=status))
        self.process_data["steps_detail"] = normalized_steps
        return steps

    def _initialize_steps(self) -> List[ProcessStep]:
        provided = self.process_data.get('steps_detail')
        steps: List[ProcessStep] = []
        if isinstance(provided, list) and provided:
            for i, item in enumerate(provided):
                step_number = item.get('step_number', i + 1)
                step_name = item.get('step_name', f"步骤 {step_number}")
                operation_guide = item.get('operation_guide', step_name)
                status: StepStatus = 'current' if i == 0 else 'pending'
                steps.append(ProcessStep(id=i, name=(step_name or f"步骤 {step_number}"), description=operation_guide, status=status))
            return steps
        templates = [
            ("步骤 1", "安装电容 C101"), ("步骤 2", "安装电容 C102"), ("步骤 3", "安装电容 C103"),
            ("步骤 4", "安装电阻 R101"), ("步骤 5", "安装电阻 R102"), ("步骤 6", "安装电阻 R103"),
            ("步骤 7", "安装芯片 U101"), ("步骤 8", "安装连接器 J101"), ("步骤 9", "安装连接器 J102"),
            ("步骤 10", "焊接检查"), ("步骤 11", "电气测试"), ("步骤 12", "最终检验"),
        ]
        for i, (name, description) in enumerate(templates[: self.total_steps]):
            status: StepStatus = 'current' if i == 0 else 'pending'
            steps.append(ProcessStep(id=i, name=name, description=description, status=status))
        return steps

    def get_current_step(self) -> Optional[ProcessStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def set_step_status(self, step_id: int, status: StepStatus):
        if 0 <= step_id < len(self.steps):
            self.steps[step_id].status = status
            logger.debug("Step %d status updated to: %s", step_id, status)

    def setup_connections(self):
        self.retry_btn.clicked.connect(self.on_retry_detection)
        self.skip_btn.clicked.connect(self.on_skip_step)

    def toggle_auto_detect(self, checked: bool):
        if checked:
            if not self.camera_active and self._last_qimage is None:
                try:
                    self.show_toast("请先开启相机", False)
                except Exception:
                    pass
                btn = getattr(self, "auto_detect_btn", None)
                if btn:
                    btn.setChecked(False)
                return
            self._auto_detect_controller.start()
        else:
            self._auto_detect_controller.stop()

    def _mark_task_running_once(self) -> None:
        if getattr(self, "_task_status_started", False):
            return
        if bool(getattr(self, "is_simulated", False)):
            self._task_status_started = True
            return
        try:
            task_no = str(self.process_data.get("task_no") or "").strip()
            if not task_no:
                return
            from src.services.result_report_service import ResultReportService
            ResultReportService().enqueue_task_status_update(task_no=task_no, status=2)
            self._task_status_started = True
        except Exception:
            pass

    def _start_ng_flash(self):
        self._ng_flash.start(self.fail_overlay)

    def _stop_ng_flash(self):
        self._ng_flash.stop()

    def _qimage_to_numpy(self, qimage: QImage):
        qi = qimage.convertToFormat(QImage.Format.Format_RGB888)
        w, h = qi.width(), qi.height()
        bpl = qi.bytesPerLine()
        buf = qi.bits().tobytes()
        arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, bpl)[:, :w * 3].reshape(h, w, 3)
        return arr.copy()

    def _ng_regions_to_rects(self, regions: List[Dict[str, Any]]) -> List[QRect]:
        rects: List[QRect] = []
        try:
            lw = self.base_image_label.width()
            lh = self.base_image_label.height()
            ow = self._last_frame_size.width() if self._last_frame_size else lw
            oh = self._last_frame_size.height() if self._last_frame_size else lh
            dw = self._last_display_size.width() if self._last_display_size else lw
            dh = self._last_display_size.height() if self._last_display_size else lh
            sx = dw / float(ow) if ow else 1.0
            sy = dh / float(oh) if oh else 1.0
            ox, oy = int((lw - dw) / 2), int((lh - dh) / 2)

            def _to_float(v):
                if v is None:
                    return None
                if isinstance(v, (int, float)):
                    return float(v)
                if isinstance(v, str):
                    s = v.strip()
                    if not s or s.lower() == "none":
                        return None
                    try:
                        return float(s)
                    except Exception:
                        return None
                return None

            for r in regions:
                coords = r.get("box_coords")
                x1 = y1 = x2 = y2 = None
                if isinstance(coords, (list, tuple)) and len(coords) >= 4:
                    x1, y1, x2, y2 = _to_float(coords[0]), _to_float(coords[1]), _to_float(coords[2]), _to_float(coords[3])
                else:
                    rx, ry = _to_float(r.get("x")), _to_float(r.get("y"))
                    rw, rh = _to_float(r.get("width")), _to_float(r.get("height"))
                    if all(v is not None for v in (rx, ry, rw, rh)):
                        x1, y1, x2, y2 = rx, ry, rx + rw, ry + rh
                if any(v is None for v in (x1, y1, x2, y2)) or x2 <= x1 or y2 <= y1:
                    continue
                x1, y1 = max(0.0, min(float(ow), x1)), max(0.0, min(float(oh), y1))
                x2, y2 = max(0.0, min(float(ow), x2)), max(0.0, min(float(oh), y2))
                if x2 <= x1 or y2 <= y1:
                    continue
                rects.append(QRect(ox + int(x1 * sx), oy + int(y1 * sy), max(1, int((x2 - x1) * sx)), max(1, int((y2 - y1) * sy))))
        except Exception:
            pass
        return rects

    def on_start_detection(self):
        if self.detection_status == 'detecting':
            return
        if not self.camera_active and self._last_qimage is None:
            return
        if self.detection_status in ('pass', 'fail'):
            if self.detection_status == 'fail':
                self._set_relay_ng_active(False, "manual_restart_detection")
            self._stop_ng_flash()
            self.detection_status = 'idle'
            self.detection_boxes = []
            self.detection_labels = []
            self._overlay_dismissed = False
            self.update_overlay_visibility()
        if self.is_simulated:
            logger.info("Starting detection simulation")
            self._mark_task_running_once()
            run_simulated_detection(self)
            return
        self._mark_task_running_once()
        handle_external_detection(self)

    def on_detection_complete(self):
        run_simulated_detection(self)

    def on_retry_detection(self):
        logger.info("Retrying detection")
        self._set_relay_ng_active(False, "manual_retry")
        self._stop_ng_flash()
        self.detection_status = 'idle'
        self.detection_boxes = []
        self.detection_labels = []
        self.clear_preview_annotation()
        self._overlay_dismissed = False
        self.update_overlay_visibility()
        self.rebuild_status_section()

    def on_skip_step(self):
        logger.info("Skipping step %d", self.current_step_index + 1)
        self._stop_ng_flash()
        self.advance_to_next_step()

    def on_stop_detection(self):
        if self.detection_timer and self.detection_timer.isActive():
            self.detection_timer.stop()
        self._set_relay_ng_active(False, "manual_stop")
        self.detection_status = 'idle'
        self.detection_boxes = []
        self.detection_labels = []
        self.clear_preview_annotation()
        self._overlay_dismissed = False
        self.update_overlay_visibility()
        self.rebuild_status_section()

    def advance_to_next_step(self):
        self._set_relay_ng_active(False, "advance_step")
        if self.current_step_index >= len(self.steps) - 1:
            logger.info("All steps completed")
            self.set_step_status(self.current_step_index, 'completed')
            if not bool(getattr(self, "is_simulated", False)):
                try:
                    from src.services.result_report_service import ResultReportService
                    ResultReportService().enqueue_task_status_update(
                        task_no=str(self.process_data.get("task_no") or ""), status=3,
                    )
                except Exception:
                    pass
            if self.auto_detect_active:
                self._auto_detect_controller.stop()
                self.close()
                return
            elif getattr(self, 'auto_start_next', False):
                self.reset_for_next_product()
                try:
                    self.show_toast("已自动开始下一产品工艺检测", True)
                except Exception:
                    pass
            else:
                self.show_completion_dialog()
            return

        self.set_step_status(self.current_step_index, 'completed')
        self.current_step_index += 1
        self.set_step_status(self.current_step_index, 'current')
        self.current_instruction = self.steps[self.current_step_index].description
        self._set_instruction_text(self.current_instruction)
        self.detection_status = 'idle'
        self.detection_boxes = []
        self.detection_labels = []
        self.clear_preview_annotation()
        self.reset_auto_detect_ng_latch()
        self._overlay_dismissed = False
        self.progress_label.setText(f"步骤: {self.current_step_index + 1} / {self.total_steps}")
        self.progress_bar.setValue(self.current_step_index + 1)
        self.rebuild_step_cards()
        self.rebuild_step_bar_cards()
        self.update_overlay_visibility()
        self.rebuild_status_section()
        try:
            self._ensure_guide_for_step(self.current_step_index, preload_next=True)
        except Exception:
            pass
        if getattr(self, "split_layout_mode", False):
            try:
                self._display_guide_image(self.current_step_index)
            except Exception:
                pass
        logger.info("Advanced to step %d", self.current_step_index + 1)

    def show_toast(self, text: str, success: bool = True):
        if not hasattr(self, "toast_label"):
            return
        self.toast_label.setText(text)
        self._set_toast_state("success" if success else "error")
        self.toast_label.setVisible(True)
        self.toast_container.setVisible(True)
        try:
            self._position_toast()
        except Exception:
            pass
        duration_ms = getattr(self, 'ok_toast_duration', 2) * 1000
        QTimer.singleShot(duration_ms, self.hide_toast)

    def hide_toast(self):
        if hasattr(self, "toast_label"):
            self.toast_label.setVisible(False)
            self.toast_container.setVisible(False)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        try:
            if hasattr(self, 'toast_container') and self.toast_container.isVisible():
                self._position_toast()
        except Exception:
            pass

    def update_current_time(self):
        now = datetime.now()
        if hasattr(self, "time_label") and self.time_label:
            self.time_label.setText(now.strftime("%H:%M:%S"))
        if hasattr(self, "date_label") and self.date_label:
            self.date_label.setText(now.strftime("%Y-%m-%d"))

    def _is_simulated_process(self) -> bool:
        name = str(self.process_data.get('algorithm_name', self.process_data.get('name', '')))
        pid = str(self.process_data.get('pid', ''))
        return ('模拟' in name) or pid.startswith('SIM-')

    def _read_auto_start_next_setting(self) -> bool:
        try:
            from src.core.paths import get_config_json_path
            p = get_config_json_path()
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                return bool(data.get("general", {}).get("auto_start_next", False))
        except Exception:
            pass
        return False

    def _read_result_prompt_position(self) -> str:
        try:
            from src.core.paths import get_config_json_path
            p = get_config_json_path()
            if p.exists():
                val = str(json.loads(p.read_text(encoding="utf-8")).get("general", {}).get("result_prompt_position", "center"))
                allowed = {"top_left", "top_center", "top_right", "center_left", "center", "center_right", "bottom_left", "bottom_center", "bottom_right"}
                return val if val in allowed else "center"
        except Exception:
            pass
        return "center"

    def _read_draw_box_settings(self) -> tuple:
        try:
            from src.core.paths import get_config_json_path
            p = get_config_json_path()
            if p.exists():
                g = json.loads(p.read_text(encoding="utf-8")).get("general", {})
                return bool(g.get("draw_boxes_ok", True)), bool(g.get("draw_boxes_ng", True))
        except Exception:
            pass
        return True, True

    def _read_ok_toast_duration(self) -> int:
        try:
            from src.core.paths import get_config_json_path
            p = get_config_json_path()
            if p.exists():
                return max(1, min(30, int(json.loads(p.read_text(encoding="utf-8")).get("general", {}).get("ok_toast_duration", 2))))
        except Exception:
            pass
        return 2

    def _set_relay_ng_active(self, active: bool, source: str) -> None:
        try:
            from src.services.relay_service import RelayService

            RelayService().sync_with_ng(bool(active), source=source)
        except Exception:
            logger.exception("Failed to sync relay NG state: active=%s source=%s", active, source)

    def show_completion_dialog(self):
        from PySide6.QtWidgets import QDialog, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setObjectName("completionDialog")
        dialog.setWindowTitle("任务完成")
        dialog.setFixedSize(520, 360)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(20)
        icon = QLabel("✅")
        icon.setObjectName("completionDialogIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message = QLabel("所有工艺步骤已完成!")
        try:
            message.setWordWrap(True)
        except Exception:
            pass
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary = QLabel(f"工艺: {self.process_data.get('name')}\n完成步骤: {self.total_steps}/{self.total_steps}")
        summary.setObjectName("completionDialogSummary")
        try:
            summary.setWordWrap(True)
        except Exception:
            pass
        summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_box = QDialogButtonBox()
        next_btn = QPushButton("开始下一个产品")
        return_btn = QPushButton("返回任务列表")
        button_box.addButton(next_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton(return_btn, QDialogButtonBox.ButtonRole.RejectRole)
        next_btn.clicked.connect(dialog.accept)
        return_btn.clicked.connect(dialog.reject)
        layout.addWidget(icon)
        layout.addWidget(message)
        layout.addWidget(summary)
        layout.addWidget(button_box)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            logger.info("Starting next product")
            self.reset_for_next_product()
        else:
            logger.info("Returning to task list")
            self.close()

    def reset_for_next_product(self):
        self._set_relay_ng_active(False, "reset_next_product")
        for i, step in enumerate(self.steps):
            step.status = 'current' if i == 0 else 'pending'
        self.current_step_index = 0
        self.detection_status = 'idle'
        self.detection_boxes = []
        self.detection_labels = []
        self.clear_preview_annotation()
        self.reset_auto_detect_ng_latch()
        self._overlay_dismissed = False
        self.current_instruction = self.steps[0].description
        self._set_instruction_text(self.current_instruction)
        self.progress_label.setText(f"步骤: 1 / {self.total_steps}")
        self.progress_bar.setValue(1)
        self.rebuild_step_cards()
        self.rebuild_step_bar_cards()
        self.update_overlay_visibility()
        self.rebuild_status_section()
        self._auto_detect_controller.clear_cache()
        try:
            self._guide_qimages = {}
            self._guide_errors = {}
            self._ensure_guide_for_step(self.current_step_index, preload_next=True)
        except Exception:
            pass
        if getattr(self, "split_layout_mode", False):
            try:
                self._display_guide_image(self.current_step_index)
            except Exception:
                pass
        logger.info("Reset for next product")
        try:
            pid = self.process_data.get('algorithm_code', self.process_data.get('pid'))
            if pid:
                from src.runner.engine import RunnerEngine
                RunnerEngine().reset_algorithm(str(pid))
        except Exception:
            pass

    def closeEvent(self, event):
        self._closing = True
        self._set_relay_ng_active(False, "process_window_close")
        self._stop_ng_flash()
        self._auto_detect_controller.stop(reset_detection_state=False)
        if self.preview_worker:
            self.preview_worker.stop()
            self.preview_worker.wait(1000)
            self.preview_worker = None
        try:
            workers = list(getattr(self, "_guide_workers", {}).values())
            for w in workers:
                try:
                    w.requestInterruption()
                except Exception:
                    pass
            for w in workers:
                try:
                    if w.isRunning():
                        w.wait(1000)
                except Exception:
                    pass
            for w in workers:
                try:
                    if w.isRunning():
                        w.terminate()
                        w.wait(200)
                except Exception:
                    pass
            self._guide_workers = {}
        except Exception:
            pass
        if self.detection_timer:
            self.detection_timer.stop()
        if self.advance_timer:
            self.advance_timer.stop()
        logger.info("ProcessExecutionWindow closing (camera connection preserved if active)")
        self.closed.emit()
        super().closeEvent(event)

    def set_preview_annotation(
        self,
        regions: List[Dict[str, Any]],
        labels: List[str],
        status: DetectionStatus,
        *,
        visible: bool = True,
    ) -> None:
        self.preview_annotation_regions = list(regions or [])
        self.preview_annotation_labels = list(labels or [])
        self.preview_annotation_status = status
        self.preview_annotation_visible = bool(visible and self.preview_annotation_regions)
        self.refresh_preview_annotation_overlay()

    def clear_preview_annotation(self) -> None:
        self.preview_annotation_regions = []
        self.preview_annotation_boxes = []
        self.preview_annotation_labels = []
        self.preview_annotation_status = "idle"
        self.preview_annotation_visible = False
        self.refresh_preview_annotation_overlay()

    def refresh_preview_annotation_overlay(self) -> None:
        widget = getattr(self, "preview_annotation_widget", None)
        if widget is None:
            return
        try:
            self._align_overlay_geometry()
        except Exception:
            pass
        boxes = self._ng_regions_to_rects(self.preview_annotation_regions) if self.preview_annotation_visible else []
        self.preview_annotation_boxes = boxes
        try:
            widget.set_status(self.preview_annotation_status if boxes else "idle")
            widget.set_boxes(boxes)
            widget.set_labels(self.preview_annotation_labels if boxes else [])
            widget.set_draw_options(bool(self.draw_boxes_ok), bool(self.draw_boxes_ng))
            widget.set_hint_visible(bool(self.auto_detect_active and boxes), "最近检测结果")
            widget.setVisible(bool(self.preview_annotation_visible and boxes))
            if widget.isVisible():
                widget.raise_()
        except Exception:
            pass

    def reset_auto_detect_ng_latch(self) -> None:
        self.auto_detect_ng_latched_step_code = None
        self.auto_detect_ng_reported = False
        try:
            pid = self.process_data.get('algorithm_code', self.process_data.get('pid'))
            if pid:
                from src.runner.engine import RunnerEngine
                RunnerEngine().teardown_algorithm(str(pid))
        except Exception:
            pass

    def show_centered(self):
        self.showMaximized()
        self.raise_()
        self.activateWindow()
        if self.isMaximized():
            return
        self.show()
        screen = self.screen()
        if screen:
            sg = screen.availableGeometry()
            self.move((sg.width() - self.width()) // 2, (sg.height() - self.height()) // 2)
