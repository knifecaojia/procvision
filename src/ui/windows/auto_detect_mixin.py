import json
import logging
import random
import time
from datetime import datetime
from typing import Any, Dict, Optional

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtGui import QImage

logger = logging.getLogger(__name__)


class AutoDetectWorker(QThread):
    result_ready = Signal(str, dict, object)
    error_occurred = Signal(str)

    def __init__(self, window, is_simulated: bool):
        super().__init__()
        self._window = window
        self._is_simulated = is_simulated
        self._step_index = window.current_step_index
        self._process_data = dict(window.process_data)
        self._is_sim = window.is_simulated

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
        time.sleep(1.5)
        if self.isInterruptionRequested():
            return
        passed = random.random() < 0.7
        if passed:
            result = {"status": "OK", "simulated": True}
        else:
            result = {"status": "OK", "data": {"result_status": "NG"}, "simulated": True}
        status = "OK" if passed else "NG"
        qimage = self._window._last_qimage
        self.result_ready.emit(status, result, qimage)

    def _run_external(self):
        window = self._window
        if window._last_qimage is None:
            self.error_occurred.emit("无可用画面帧")
            return

        idx = self._step_index
        guide_url = window._get_step_guide_url(idx)
        guide_qi = window._guide_qimages.get(idx)

        img = window._qimage_to_numpy(window._last_qimage)
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

        status_str = str(result.get('status', '')).upper()
        if status_str == 'OK':
            data = result.get("data", {})
            result_status = data.get("result_status", "NG")
            if result_status == "OK":
                self.result_ready.emit("OK", {"status": "OK", "data": data, "step_code": step_code, "step_number": step_number}, window._last_qimage)
            else:
                self.result_ready.emit("NG", {"status": "OK", "data": data, "step_code": step_code, "step_number": step_number}, window._last_qimage)
        else:
            self.result_ready.emit("ERROR", {"status": "ERROR", "message": result.get("message", ""), "step_code": step_code, "step_number": step_number}, window._last_qimage)


class AutoDetectController:
    def __init__(self, window):
        self._window = window
        self._active = False
        self._pending_ng_data: Optional[Dict[str, Any]] = None
        self._pending_ng_image: Optional[QImage] = None
        self._pending_ng_step_code: Optional[str] = None
        self._worker: Optional[AutoDetectWorker] = None
        self._retry_timer: Optional[QTimer] = None
        self._advance_delay = 1500
        self._ng_retry_delay = 2000

    @property
    def active(self) -> bool:
        return self._active

    def start(self):
        if self._active:
            return
        self._active = True
        logger.info("Auto detect started")
        self._run_step()

    def stop(self):
        if not self._active:
            return
        self._active = False
        self._stop_worker()
        self._stop_retry_timer()
        logger.info("Auto detect stopped")

    def clear_cache(self):
        self._pending_ng_data = None
        self._pending_ng_image = None
        self._pending_ng_step_code = None

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
        if not w.camera_active and w._last_qimage is None:
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

        is_sim = w.is_simulated
        self._worker = AutoDetectWorker(w, is_sim)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_result(self, status: str, result: Dict[str, Any], qimage: Optional[QImage]):
        if not self._active:
            return
        if status == "OK":
            self._handle_ok(result, qimage)
        elif status == "NG":
            self._handle_ng(result, qimage)
        else:
            self._handle_error(result.get("message", "检测执行失败"))

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

    def _handle_ok(self, result: Dict[str, Any], qimage: Optional[QImage]):
        w = self._window
        step_code = result.get("step_code", "")
        step_number = result.get("step_number", w.current_step_index + 1)

        logger.info("Auto detect OK: step=%s", step_number)
        w.detection_status = 'pass'
        w.detection_boxes = []
        w.detection_labels = []
        try:
            w._set_instruction_text("自动检测通过")
        except Exception:
            pass
        w.rebuild_status_section()
        self._update_indicator("ok")

        from .detection_mixin import save_local_record, get_step_code_from_payload
        sp = w._get_step_payload(w.current_step_index)
        sc = get_step_code_from_payload(sp, w.current_step_index)
        save_local_record(w.process_data, True, sc, w.current_step_index + 1, result, qimage)

        self._report_cached_ng_with_ok(result, qimage, sc)

        self.clear_cache()

        self._retry_timer = QTimer()
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._advance_and_continue)
        self._retry_timer.start(w.ok_toast_duration * 1000)

    def _handle_ng(self, result: Dict[str, Any], qimage: Optional[QImage]):
        w = self._window
        step_code = result.get("step_code", "")
        step_number = result.get("step_number", w.current_step_index + 1)

        logger.info("Auto detect NG: step=%s (caching)", step_number)
        w.detection_status = 'fail'
        w.detection_boxes = []
        w.detection_labels = []

        data = result.get("data", {})
        ng_reason = str(data.get("ng_reason", "")).strip()
        try:
            w._set_instruction_text(f"自动检测NG: {ng_reason}" if ng_reason else "自动检测NG，重试中…")
        except Exception:
            pass

        w.rebuild_status_section()
        self._update_indicator("ng")

        from .detection_mixin import save_local_record, get_step_code_from_payload
        sp = w._get_step_payload(w.current_step_index)
        sc = get_step_code_from_payload(sp, w.current_step_index)
        save_local_record(w.process_data, False, sc, w.current_step_index + 1, result, qimage)

        self._pending_ng_data = result
        self._pending_ng_image = qimage.copy() if qimage is not None else None
        self._pending_ng_step_code = sc

        self._retry_timer = QTimer()
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._retry_current_step)
        self._retry_timer.start(self._ng_retry_delay)

    def _handle_error(self, msg: str):
        logger.error("Auto detect error: %s", msg)
        w = self._window
        w.auto_detect_active = False
        w.detection_status = 'fail'
        w.detection_boxes = []
        w.detection_labels = []
        try:
            w._set_instruction_text(f"自动检测出错: {msg}")
        except Exception:
            pass
        w.rebuild_status_section()
        self._update_indicator("error")
        self.stop()
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
        w._stop_ng_flash()
        w.detection_status = 'idle'
        w.detection_boxes = []
        w.detection_labels = []
        self._run_step()

    def _report_cached_ng_with_ok(self, ok_result: Dict, ok_qimage: Optional[QImage], ok_step_code: str):
        if self._pending_ng_data is None:
            return
        try:
            from src.services.result_report_service import ResultReportService
            w = self._window
            svc = ResultReportService()
            task_no = str(w.process_data.get("task_no") or "")
            process_code = str(w.process_data.get("process_code") or "")
            if self._pending_ng_step_code:
                svc.enqueue_step_result(
                    task_no=task_no,
                    step_code=str(self._pending_ng_step_code),
                    step_status=3,
                    process_code=process_code,
                    qimage=self._pending_ng_image.copy() if self._pending_ng_image is not None else None,
                    algo_result=self._pending_ng_data,
                )
            svc.enqueue_step_result(
                task_no=task_no,
                step_code=str(ok_step_code),
                step_status=2,
                process_code=process_code,
                qimage=ok_qimage.copy() if ok_qimage is not None else None,
                algo_result=ok_result,
            )
            logger.info("Reported cached NG (step=%s) + OK (step=%s)", self._pending_ng_step_code, ok_step_code)
        except Exception as e:
            logger.warning("Failed to report cached NG+OK: %s", e)
