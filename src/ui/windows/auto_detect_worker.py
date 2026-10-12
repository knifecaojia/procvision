import copy
import random
import time
from datetime import datetime

from PySide6.QtCore import QThread, Signal

SIMULATED_PASS_PROBABILITY = 0.3


class AutoDetectWorker(QThread):
    result_ready = Signal(str, dict, object)
    error_occurred = Signal(str)

    def __init__(self, window, is_simulated: bool, task_seq: int):
        super().__init__()
        self._is_simulated = is_simulated
        self._task_seq = task_seq
        self._source_qimage = window._last_qimage.copy() if window._last_qimage is not None else None
        self._inputs = None
        if not is_simulated and self._source_qimage is not None:
            idx = window.current_step_index
            payload = copy.deepcopy(window._get_step_payload(idx))
            raw_step_no = payload.get("step_number") or payload.get("step_code") or payload.get("step_name")
            try:
                step_number = int(str(raw_step_no).strip())
            except (ValueError, TypeError):
                step_number = idx + 1
            self._step_code = str(payload.get("step_code") or payload.get("step_number") or step_number).strip()
            self._step_number = step_number
            image = window._qimage_to_numpy(self._source_qimage).copy()
            guide = window._guide_qimages.get(idx)
            guide_image = image
            if guide is not None:
                try:
                    guide_image = window._qimage_to_numpy(guide.copy()).copy()
                except Exception:
                    guide_image = image
            camera_id = "unknown"
            if window.camera_service and window.camera_service.current_camera:
                camera_id = window.camera_service.current_camera.info.id
            name = str(window.process_data.get("algorithm_name") or "").strip()
            version = str(window.process_data.get("algorithm_version") or "").strip()
            self._inputs = {
                "name": name, "version": version, "step_index": step_number,
                "step_desc": str(payload.get("operation_guide") or payload.get("step_content") or "").strip() or f"步骤 {step_number}",
                "cur_image": image, "guide_image": guide_image,
                "guide_info": copy.deepcopy(window._get_step_guide_info(idx)),
                "context": {
                    "user_params": {"step_number": step_number},
                    "camera_id_cur": camera_id, "camera_id_guide": camera_id,
                    "algorithm_name": name, "algorithm_version": version,
                },
            }

    def run(self):
        try:
            if self.isInterruptionRequested():
                return
            started_at = datetime.now()
            if self._is_simulated:
                time.sleep(1.5)
                passed = random.random() < SIMULATED_PASS_PROBABILITY
                result = {"status": "OK", "data": {"result_status": "OK" if passed else "NG"}, "simulated": True}
            else:
                if self._inputs is None:
                    self.error_occurred.emit("无可用画面帧")
                    return
                from src.runner.engine import RunnerEngine
                result = RunnerEngine().execute_flow(**self._inputs)
            if self.isInterruptionRequested():
                return
            finished_at = datetime.now()
            data = result.get("data", {}) if isinstance(result.get("data"), dict) else {}
            result["__trace"] = {
                "task_seq": self._task_seq,
                "started_at": started_at.isoformat(timespec="milliseconds"),
                "finished_at": finished_at.isoformat(timespec="milliseconds"),
                "elapsed_ms": round((finished_at - started_at).total_seconds() * 1000, 2),
                "algo_debug": data.get("debug"), "algo_executed_steps": data.get("executed_steps"),
                "message": result.get("message", ""),
            }
            if not self._is_simulated:
                result["step_code"] = self._step_code
                result["step_number"] = self._step_number
            status = "ERROR"
            if str(result.get("status", "")).upper() == "OK":
                status = "OK" if data.get("result_status", "NG") == "OK" else "NG"
            self.result_ready.emit(status, result, self._source_qimage)
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.error_occurred.emit(str(exc))
