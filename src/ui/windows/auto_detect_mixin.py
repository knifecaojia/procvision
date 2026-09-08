import json
import logging
import random
import time
from datetime import datetime
from typing import Any, Dict, Optional

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtGui import QImage

from src.services.detection_image_annotation_service import (
    build_annotated_qimage,
    build_detection_labels,
    extract_detection_regions,
)
from src.services.detection_task_trace_service import DetectionTaskTraceService

logger = logging.getLogger(__name__)
SIMULATED_PASS_PROBABILITY = 0.3


class AutoDetectWorker(QThread):
    result_ready = Signal(str, dict, object)
    error_occurred = Signal(str)

    def __init__(self, window, is_simulated: bool, task_seq: int):
        super().__init__()
        self._window = window
        self._is_simulated = is_simulated
        self._step_index = window.current_step_index
        self._process_data = dict(window.process_data)
        self._is_sim = window.is_simulated
        self._task_seq = task_seq

    def run(self):
        try:
            if self.isInterruptionRequested():
                return
            if self._is_simulated:
                self._run_simulated()
            else:
                self._run_external()
        except Exception as e:
            if not self.isInterruptionRequested():
                self.error_occurred.emit(str(e))

    def _run_simulated(self):
        started_at = datetime.now()
        time.sleep(1.5)
        if self.isInterruptionRequested():
            return
        passed = random.random() < SIMULATED_PASS_PROBABILITY
        if passed:
            result = {"status": "OK", "simulated": True}
        else:
            result = {"status": "OK", "data": {"result_status": "NG"}, "simulated": True}
        status = "OK" if passed else "NG"
        qimage = self._window._last_qimage.copy() if self._window._last_qimage is not None else None
        finished_at = datetime.now()
        result["__trace"] = {
            "task_seq": self._task_seq,
            "started_at": started_at.isoformat(timespec="milliseconds"),
            "finished_at": finished_at.isoformat(timespec="milliseconds"),
            "elapsed_ms": round((finished_at - started_at).total_seconds() * 1000, 2),
            "algo_debug": None,
            "algo_executed_steps": None,
            "message": "",
        }
        self.result_ready.emit(status, result, qimage)

    def _run_external(self):
        window = self._window
        if window._last_qimage is None:
            self.error_occurred.emit("无可用画面帧")
            return
        started_at = datetime.now()
        source_qimage = window._last_qimage.copy()

        idx = self._step_index
        guide_qi = window._guide_qimages.get(idx)

        img = window._qimage_to_numpy(source_qimage)
        guide_img = img
        if guide_qi is not None:
            try:
                guide_img = window._qimage_to_numpy(guide_qi)
            except Exception:
                guide_img = img

        step_payload = window._get_step_payload(idx)
        raw_step_no = step_payload.get("step_number") or step_payload.get("step_code") or step_payload.get("step_name")
        try:
            step_number = int(str(raw_step_no).strip())
        except Exception:
            step_number = idx + 1
        step_code = str(step_payload.get("step_code") or step_payload.get("step_number") or step_number).strip()

        algo_name = str(window.process_data.get("algorithm_name") or "").strip()
        algo_ver = str(window.process_data.get("algorithm_version") or "").strip()

        from src.runner.engine import RunnerEngine
        runner = RunnerEngine()

        camera_id = "unknown"
        if window.camera_service and window.camera_service.current_camera:
            camera_id = window.camera_service.current_camera.info.id

        step_desc = ""
        if step_payload:
            step_desc = str(step_payload.get("operation_guide") or step_payload.get("step_content") or "").strip()
        if not step_desc:
            step_desc = f"步骤 {step_number}"

        context = {
            "user_params": {"step_number": step_number},
            "camera_id_cur": camera_id,
            "camera_id_guide": camera_id,
            "algorithm_name": algo_name,
            "algorithm_version": algo_ver,
        }

        if self.isInterruptionRequested():
            return

        guide_info = window._get_step_guide_info(idx)
        result = runner.execute_flow(
            name=algo_name, version=algo_ver,
            step_index=step_number, step_desc=step_desc,
            cur_image=img, guide_image=guide_img,
            guide_info=guide_info, context=context,
        )

        if self.isInterruptionRequested():
            return
        finished_at = datetime.now()
        data = result.get("data", {}) if isinstance(result.get("data"), dict) else {}
        result["__trace"] = {
            "task_seq": self._task_seq,
            "started_at": started_at.isoformat(timespec="milliseconds"),
            "finished_at": finished_at.isoformat(timespec="milliseconds"),
            "elapsed_ms": round((finished_at - started_at).total_seconds() * 1000, 2),
            "algo_debug": data.get("debug"),
            "algo_executed_steps": data.get("executed_steps"),
            "message": result.get("message", ""),
        }

        status_str = str(result.get('status', '')).upper()
        if status_str == 'OK':
            result_status = data.get("result_status", "NG")
            if result_status == "OK":
                self.result_ready.emit("OK", {"status": "OK", "data": data, "step_code": step_code, "step_number": step_number, "__trace": result.get("__trace")}, source_qimage)
            else:
                self.result_ready.emit("NG", {"status": "OK", "data": data, "step_code": step_code, "step_number": step_number, "__trace": result.get("__trace")}, source_qimage)
        else:
            self.result_ready.emit("ERROR", {"status": "ERROR", "message": result.get("message", ""), "step_code": step_code, "step_number": step_number, "__trace": result.get("__trace")}, source_qimage)


class AutoDetectController:
    def __init__(self, window):
        self._window = window
        self._active = False
        self._worker: Optional[AutoDetectWorker] = None
        self._retry_timer: Optional[QTimer] = None
        self._ng_retry_delay = 2000
        self._trace_service = DetectionTaskTraceService()

    @property
    def active(self) -> bool:
        return self._active

    def start(self):
        if self._active:
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
        if not was_active and not reset_detection_state:
            return
        self._stop_worker()
        self._stop_retry_timer()
        w.clear_preview_annotation()
        w.reset_auto_detect_ng_latch()
        if reset_detection_state:
            w._set_relay_ng_active(False, "auto_detect_stop")
            w._stop_ng_flash()
            w.detection_status = 'idle'
            w.detection_boxes = []
            w.detection_labels = []
            w._overlay_dismissed = False
            w.update_overlay_visibility()
            w.rebuild_status_section()
            self._update_indicator("idle")
        logger.info("Auto detect stopped")

    def clear_cache(self):
        self._window.reset_auto_detect_ng_latch()

    def _stop_worker(self):
        if self._worker is not None:
            self._worker.requestInterruption()
            try:
                self._worker.quit()
                self._worker.wait(2000)
            except Exception:
                pass
            try:
                self._worker.deleteLater()
            except Exception:
                pass
            self._worker = None

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
        if w.detection_status == 'detecting':
            return
        if not bool(getattr(w, "_has_detection_source", lambda: False)()):
            logger.warning("Auto detect: no camera/image available")
            self.stop()
            try:
                w.show_toast("自动检测停止：无可用画面", False)
            except Exception:
                pass
            return

        self._stop_worker()

        w._mark_task_running_once()
        w.detection_status = 'detecting'
        w.rebuild_status_section()
        self._update_indicator("detecting")
        try:
            w._set_instruction_text("自动检测中…")
        except Exception:
            pass
        w.auto_detect_task_seq += 1

        is_sim = w.is_simulated
        self._worker = AutoDetectWorker(w, is_sim, w.auto_detect_task_seq)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_result(self, status: str, result: Dict[str, Any], qimage: Optional[QImage]):
        if not self._active:
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

    def _on_error(self, msg: str):
        if not self._active:
            return
        self._handle_error(msg)

    def _on_worker_finished(self):
        if self._worker is not None:
            try:
                self._worker.deleteLater()
            except Exception:
                pass
            self._worker = None

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
        w.rebuild_status_section()
        self._update_indicator("error")
        self.stop(reset_detection_state=False)
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
