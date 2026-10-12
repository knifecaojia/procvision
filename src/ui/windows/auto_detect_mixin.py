import logging
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtGui import QImage

from .auto_detect_worker import AutoDetectWorker

from src.services.detection_image_annotation_service import (
    build_annotated_qimage,
    build_detection_labels,
    extract_detection_regions,
)
from src.services.detection_task_trace_service import DetectionTaskTraceService

logger = logging.getLogger(__name__)


class AutoDetectController(QObject):
    worker_drained = Signal()

    def __init__(self, window):
        super().__init__()
        self._window = window
        self._reset_pending = False
        self._restore_idle = False
        self._active = False
        self._worker: Optional[AutoDetectWorker] = None
        self._retry_timer: Optional[QTimer] = None
        self._ng_retry_delay = 2000
        self._trace_service = DetectionTaskTraceService()

    @property
    def active(self) -> bool:
        return self._active

    @property
    def busy(self) -> bool:
        return self._worker is not None

    def start(self):
        if self._active or self.busy or self._reset_pending or getattr(self._window, "_closing", False):
            logger.info("Auto detect start ignored: active=%s busy=%s", self._active, self.busy)
            return
        self._active = True
        self._window.auto_detect_active = True
        logger.info("Auto detect started")
        self._run_step()

    def stop(self, *, reset_detection_state: bool = True):
        was_active = self._active
        self._active = False
        w = self._window
        w.auto_detect_active = False
        if not was_active and not reset_detection_state and not self.busy:
            return
        self._stop_retry_timer()
        self._restore_idle = self._restore_idle or reset_detection_state
        self._reset_pending = True
        self._stop_worker()
        if self.busy:
            if reset_detection_state:
                w.detection_status = 'detecting'
                w._set_instruction_text("正在结束自动检测，请稍候…")
            w.rebuild_status_section()
            logger.info("Auto detect cancellation pending worker finish: task=%s", w.auto_detect_task_seq)
            return
        self._finish_stop()

    def _finish_stop(self):
        if not self._reset_pending:
            return
        self._reset_pending = False
        restore_idle = self._restore_idle
        self._restore_idle = False
        w = self._window
        w.clear_preview_annotation()
        w.reset_auto_detect_ng_latch()
        if restore_idle:
            w._set_relay_ng_active(False, "auto_detect_stop")
            w._stop_ng_flash()
            w.detection_status = 'idle'
            w.detection_boxes = []
            w.detection_labels = []
            w._overlay_dismissed = False
            w._set_instruction_text(w.current_instruction)
            w.update_overlay_visibility()
            self._update_indicator("idle")
        w.rebuild_status_section()
        logger.info("Auto detect stopped: task=%s", w.auto_detect_task_seq)

    def clear_cache(self):
        self._window.reset_auto_detect_ng_latch()

    def _stop_worker(self):
        if self._worker is not None:
            self._worker.requestInterruption()
            logger.info("Auto detect interruption requested: task=%s", self._window.auto_detect_task_seq)

    def _stop_retry_timer(self):
        if self._retry_timer is not None:
            self._retry_timer.stop()
            try:
                self._retry_timer.deleteLater()
            except Exception:
                pass
            self._retry_timer = None

    def _update_indicator(self, state: str):
        indicator = getattr(self._window, "status_indicator", None)
        if indicator is not None:
            try:
                indicator.set_state(state)
            except Exception:
                pass

    def _run_step(self):
        if not self._active:
            return
        w = self._window
        if self.busy or self._reset_pending or w.detection_status == 'detecting':
            return
        if not bool(getattr(w, "_has_detection_source", lambda: False)()):
            logger.warning("Auto detect: no camera/image available")
            self.stop()
            try:
                w.show_toast("自动检测停止：无可用画面", False)
            except Exception:
                pass
            return

        w._mark_task_running_once()
        w.detection_status = 'detecting'
        w.rebuild_status_section()
        self._update_indicator("detecting")
        try:
            w._set_instruction_text(f"自动检测中…\n{w.current_instruction}")
        except Exception:
            pass
        w.auto_detect_task_seq += 1

        try:
            worker = AutoDetectWorker(w, w.is_simulated, w.auto_detect_task_seq)
            self._worker = worker
            worker.result_ready.connect(self._on_result)
            worker.error_occurred.connect(self._on_error)
            worker.finished.connect(self._on_worker_finished)
            worker.start()
            logger.info("Auto detect worker started: task=%s", w.auto_detect_task_seq)
        except Exception as exc:
            self._worker = None
            self._handle_error(str(exc))

    @Slot(str, dict, object)
    def _on_result(self, status: str, result: Dict[str, Any], qimage: Optional[QImage]):
        if not self._active or self.sender() is not self._worker:
            logger.info("Auto detect late result discarded")
            return
        trace_payload: Dict[str, Any] = dict(result.get("__trace") or {})
        ng_latched_before = self._is_ng_latched(result.get("step_code"))
        ng_reported = False
        if status == "OK":
            ng_reported = self._handle_ok(result, qimage)
        elif status == "NG":
            ng_reported = self._handle_ng(result, qimage)
        else:
            self._handle_error(result.get("message", "检测执行失败"))
        self._log_task_trace(result, status, trace_payload, ng_reported, ng_latched_before)

    @Slot(str)
    def _on_error(self, msg: str):
        if not self._active or self.sender() is not self._worker:
            logger.info("Auto detect late error discarded")
            return
        self._handle_error(msg)

    @Slot()
    def _on_worker_finished(self, worker=None):
        worker = worker or self.sender()
        if worker is not self._worker:
            logger.info("Auto detect stale finish ignored")
            return
        logger.info("Auto detect worker finished: task=%s", self._window.auto_detect_task_seq)
        self._worker = None
        worker.deleteLater()
        self._finish_stop()
        self.worker_drained.emit()

    def _handle_ok(self, result: Dict[str, Any], qimage: Optional[QImage]) -> bool:
        w = self._window
        step_number = result.get("step_number", w.current_step_index + 1)
        data = result.get("data", {})
        step_code = str(result.get("step_code") or "").strip()

        logger.info("Auto detect OK: step=%s", step_number)
        regions = extract_detection_regions(result)
        w.detection_status = 'pass'
        w.detection_boxes = w._ng_regions_to_rects(regions)
        w.detection_labels = build_detection_labels(result, len(w.detection_boxes), is_ok=True)
        w.set_preview_annotation(regions, w.detection_labels, "pass", visible=bool(w.draw_boxes_ok))
        try:
            from .detection_mixin import resolve_success_instruction_text
            w._set_instruction_text(resolve_success_instruction_text(data, "自动检测通过"))
        except Exception:
            pass
        w.update_overlay_visibility()
        w.rebuild_status_section()
        self._update_indicator("ok")

        from .detection_mixin import save_local_record, get_step_code_from_payload
        sp = w._get_step_payload(w.current_step_index)
        sc = get_step_code_from_payload(sp, w.current_step_index)
        annotated_qimage = build_annotated_qimage(
            qimage,
            result,
            is_ok=True,
            draw_ok=bool(getattr(w, "draw_boxes_ok", True)),
            draw_ng=bool(getattr(w, "draw_boxes_ng", True)),
        )
        save_local_record(w.process_data, True, sc, w.current_step_index + 1, result, annotated_qimage)
        self._report_ok(result, annotated_qimage, sc)
        self.clear_cache()
        w.auto_detect_last_result_status = "OK"

        self._retry_timer = QTimer()
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._advance_and_continue)
        self._retry_timer.start(w.ok_toast_duration * 1000)
        return False

    def _handle_ng(self, result: Dict[str, Any], qimage: Optional[QImage]) -> bool:
        w = self._window
        step_number = result.get("step_number", w.current_step_index + 1)
        step_code = str(result.get("step_code") or "").strip()

        logger.info("Auto detect NG: step=%s", step_number)
        regions = extract_detection_regions(result)
        w.detection_status = 'fail'
        w.detection_boxes = w._ng_regions_to_rects(regions)
        w.detection_labels = build_detection_labels(result, len(w.detection_boxes), is_ok=False)
        w.set_preview_annotation(regions, w.detection_labels, "fail", visible=bool(w.draw_boxes_ng))

        data = result.get("data", {})
        ng_reason = str(data.get("ng_reason", "")).strip()
        try:
            w._set_instruction_text(f"自动检测NG: {ng_reason}" if ng_reason else "自动检测NG，重试中…")
        except Exception:
            pass

        w.update_overlay_visibility()
        w.rebuild_status_section()
        self._update_indicator("ng")
        w._set_relay_ng_active(True, "auto_ng")

        from .detection_mixin import save_local_record, get_step_code_from_payload
        sp = w._get_step_payload(w.current_step_index)
        sc = get_step_code_from_payload(sp, w.current_step_index)
        annotated_qimage = build_annotated_qimage(
            qimage,
            result,
            is_ok=False,
            draw_ok=bool(getattr(w, "draw_boxes_ok", True)),
            draw_ng=bool(getattr(w, "draw_boxes_ng", True)),
        )
        should_report_ng = not self._is_ng_latched(step_code)
        if should_report_ng:
            save_local_record(w.process_data, False, sc, w.current_step_index + 1, result, annotated_qimage)
            self._report_ng(result, annotated_qimage, sc)
            w.auto_detect_ng_latched_step_code = step_code
            w.auto_detect_ng_reported = True
        w.auto_detect_last_result_status = "NG"

        self._retry_timer = QTimer()
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._retry_current_step)
        self._retry_timer.start(self._ng_retry_delay)
        return should_report_ng

    def _handle_error(self, msg: str):
        logger.error("Auto detect error: %s", msg)
        w = self._window
        w.detection_status = 'fail'
        w.detection_boxes = []
        w.detection_labels = []
        w.clear_preview_annotation()
        try:
            w._set_instruction_text(f"自动检测出错: {msg}")
        except Exception:
            pass
        w.update_overlay_visibility()
        self._update_indicator("error")
        self.stop(reset_detection_state=False)
        w.rebuild_status_section()
        try:
            w.show_toast(f"自动检测已停止: {msg}", False)
        except Exception:
            pass

    def _advance_and_continue(self):
        self._stop_retry_timer()
        w = self._window
        if not self._active:
            return
        is_last = w.current_step_index >= len(w.steps) - 1
        w.advance_to_next_step()
        if is_last:
            if self._active:
                self.stop()
            return
        self._retry_timer = QTimer()
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._run_step)
        self._retry_timer.start(500)

    def _retry_current_step(self):
        self._stop_retry_timer()
        if not self._active:
            return
        w = self._window
        w._set_relay_ng_active(False, "auto_ng_retry")
        w._stop_ng_flash()
        w.detection_status = 'idle'
        w.detection_boxes = []
        w.detection_labels = []
        w.refresh_preview_annotation_overlay()
        w.update_overlay_visibility()
        self._run_step()

    def _report_ng(self, ng_result: Dict, ng_qimage: Optional[QImage], ng_step_code: str) -> None:
        w = self._window
        if bool(getattr(w, "is_simulated", False)):
            return
        try:
            from src.services.result_report_service import ResultReportService
            svc = ResultReportService()
            task_no = str(w.process_data.get("task_no") or "")
            process_code = str(w.process_data.get("process_code") or "")
            svc.enqueue_step_result(
                task_no=task_no,
                step_code=str(ng_step_code),
                step_status=3,
                process_code=process_code,
                qimage=ng_qimage.copy() if ng_qimage is not None else None,
                algo_result=ng_result,
            )
            logger.info("Reported first NG for step=%s", ng_step_code)
        except Exception as e:
            logger.warning("Failed to report NG: %s", e)

    def _report_ok(self, ok_result: Dict, ok_qimage: Optional[QImage], ok_step_code: str) -> None:
        w = self._window
        if bool(getattr(w, "is_simulated", False)):
            return
        try:
            from src.services.result_report_service import ResultReportService
            svc = ResultReportService()
            task_no = str(w.process_data.get("task_no") or "")
            process_code = str(w.process_data.get("process_code") or "")
            svc.enqueue_step_result(
                task_no=task_no,
                step_code=str(ok_step_code),
                step_status=2,
                process_code=process_code,
                qimage=ok_qimage.copy() if ok_qimage is not None else None,
                algo_result=ok_result,
            )
            logger.info("Reported OK for step=%s", ok_step_code)
        except Exception as e:
            logger.warning("Failed to report OK: %s", e)

    def _is_ng_latched(self, step_code: Optional[str]) -> bool:
        step_code_text = str(step_code or "").strip()
        if not step_code_text:
            return False
        w = self._window
        return bool(
            getattr(w, "auto_detect_ng_reported", False)
            and str(getattr(w, "auto_detect_ng_latched_step_code", "")).strip() == step_code_text
        )

    def _log_task_trace(
        self,
        result: Dict[str, Any],
        status: str,
        trace_payload: Dict[str, Any],
        ng_reported: bool,
        ng_latched_before: bool,
    ) -> None:
        w = self._window
        data = result.get("data", {}) if isinstance(result.get("data"), dict) else {}
        regions = extract_detection_regions(result)
        trace_payload.update(
            {
                "task_no": str(w.process_data.get("task_no") or ""),
                "process_code": str(w.process_data.get("process_code") or ""),
                "step_code": str(result.get("step_code") or ""),
                "step_index": result.get("step_number", w.current_step_index + 1),
                "result_status": status,
                "ng_reported": bool(ng_reported),
                "ng_latched_before": bool(ng_latched_before),
                "ng_latched_after": bool(self._is_ng_latched(result.get("step_code"))),
                "draw_boxes_ok": bool(getattr(w, "draw_boxes_ok", True)),
                "draw_boxes_ng": bool(getattr(w, "draw_boxes_ng", True)),
                "box_count": len(regions),
                "message": result.get("message") or data.get("ng_reason") or trace_payload.get("message", ""),
            }
        )
        self._trace_service.log_summary(trace_payload)
