import json
import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from PySide6.QtCore import QTimer, QRect, QSize
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QGraphicsOpacityEffect

logger = logging.getLogger(__name__)

DetectionStatus = Literal['idle', 'detecting', 'pass', 'fail']


class NgFlashController:
    def __init__(self, parent_widget):
        self._parent = parent_widget
        self._timer: Optional[QTimer] = None
        self._count: int = 0
        self._max_flashes: int = 6
        self._effect: Optional[QGraphicsOpacityEffect] = None

    def start(self, fail_overlay):
        self.stop()
        if fail_overlay is None:
            return
        if self._effect is None:
            self._effect = QGraphicsOpacityEffect(fail_overlay)
            fail_overlay.setGraphicsEffect(self._effect)
        self._effect.setOpacity(1.0)
        self._count = 0
        self._timer = QTimer(self._parent)
        self._timer.timeout.connect(lambda: self._tick(fail_overlay))
        self._timer.start(500)

    def _tick(self, fail_overlay):
        self._count += 1
        if self._count >= self._max_flashes:
            self.stop()
            return
        if self._effect is not None:
            opacity = 0.3 if self._count % 2 == 1 else 1.0
            self._effect.setOpacity(opacity)

    def stop(self):
        if self._timer is not None:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None
        self._count = 0
        if self._effect is not None:
            self._effect.setOpacity(1.0)


def save_local_record(
    process_data: Dict[str, Any],
    is_ok: bool,
    step_code: str,
    step_number: int,
    algo_result: Optional[Dict[str, Any]],
    qimage: Optional[QImage],
):
    try:
        from src.services.local_record_service import LocalRecordService
        data = algo_result.get("data", {}) if isinstance(algo_result, dict) else {}
        ng_reason = str(data.get("ng_reason", "")).strip() if isinstance(data, dict) else ""
        defect_rects = data.get("defect_rects", []) if isinstance(data, dict) else []
        LocalRecordService().save_record(
            task_no=str(process_data.get("task_no") or "").strip(),
            step_code=step_code,
            step_number=step_number,
            is_ok=is_ok,
            process_code=str(process_data.get("process_code") or ""),
            algorithm_name=str(process_data.get("algorithm_name") or ""),
            algorithm_version=str(process_data.get("algorithm_version") or ""),
            ng_reason=ng_reason,
            defect_rects=defect_rects,
            algo_result=algo_result,
            qimage=qimage,
        )
    except Exception as e:
        logger.warning("Local record save failed: %s", e)


def get_step_code_from_payload(step_payload: Dict[str, Any], fallback_index: int) -> str:
    return str(
        step_payload.get("step_code")
        or step_payload.get("step_number")
        or (fallback_index + 1)
    ).strip()


def run_simulated_detection(window) -> None:
    window.detection_status = 'detecting'
    window.update_overlay_visibility()
    window.rebuild_status_section()
    window.detection_timer = QTimer()
    window.detection_timer.setSingleShot(True)
    window.detection_timer.timeout.connect(lambda: _on_simulated_complete(window))
    window.detection_timer.start(1500)


def _on_simulated_complete(window) -> None:
    passed = random.random() < 0.7
    step_payload = window._get_step_payload(window.current_step_index)
    step_code = get_step_code_from_payload(step_payload, window.current_step_index)

    if passed:
        logger.info("Detection PASSED (simulated)")
        window.detection_status = 'pass'
        window.update_overlay_visibility()
        window.rebuild_status_section()
        save_local_record(
            window.process_data, True, step_code,
            window.current_step_index + 1,
            {"status": "OK", "simulated": True}, window._last_qimage,
        )
        _report_simulated_step(window, step_code)
        window.advance_timer = QTimer()
        window.advance_timer.setSingleShot(True)
        window.advance_timer.timeout.connect(window.advance_to_next_step)
        window.advance_timer.start(window.ok_toast_duration * 1000)
    else:
        logger.info("Detection FAILED (simulated)")
        window.detection_status = 'fail'
        window.update_overlay_visibility()
        window.rebuild_status_section()
        window._start_ng_flash()
        save_local_record(
            window.process_data, False, step_code,
            window.current_step_index + 1,
            {"status": "NG", "simulated": True}, window._last_qimage,
        )
        _report_simulated_step(window, step_code)


def _report_simulated_step(window, step_code: str) -> None:
    try:
        from src.services.result_report_service import ResultReportService
        ResultReportService().enqueue_step_result(
            task_no=str(window.process_data.get("task_no") or ""),
            step_code=str(step_code),
            step_status=2,
            process_code=str(window.process_data.get("process_code") or ""),
            qimage=window._last_qimage.copy() if window._last_qimage is not None else None,
            algo_result={"status": "OK", "simulated": True},
        )
    except Exception:
        pass


def handle_external_detection(window) -> None:
    if window._last_qimage is None:
        logger.warning("No camera frame available for external detection")
        return

    idx = window.current_step_index
    guide_url = window._get_step_guide_url(idx)
    guide_qi = window._guide_qimages.get(idx)
    if guide_url and guide_qi is None:
        window._ensure_guide_for_step(idx, preload_next=True)
        err = window._guide_errors.get(idx, "")
        if err:
            window.show_toast(f"引导图加载失败，正在重试: {err}", False)
        else:
            window.show_toast("引导图加载中，请稍后重试", True)
        return

    window._mark_task_running_once()
    window.detection_status = 'detecting'
    window.update_overlay_visibility()
    window.rebuild_status_section()
    try:
        window._set_instruction_text("检测中…")
    except Exception:
        pass

    try:
        start_time = datetime.now()
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

        camera_id = window.camera_service.current_camera.info.id if window.camera_service and window.camera_service.current_camera else "unknown"
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

        try:
            guide_info = window._get_step_guide_info(idx)
            result = runner.execute_flow(
                name=algo_name, version=algo_ver,
                step_index=step_number, step_desc=step_desc,
                cur_image=img, guide_image=guide_img,
                guide_info=guide_info, context=context,
            )
        except Exception as call_err:
            try:
                from src.runner.exceptions import InvalidPidError
                if isinstance(call_err, InvalidPidError):
                    window.show_toast("算法未部署或PID未匹配，已切换为模拟检测", True)
                    run_simulated_detection(window)
                    return
            except Exception:
                pass
            raise call_err

        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        logger.info(f"Detection executed in {duration_ms:.2f}ms, algo_result={json.dumps(result, ensure_ascii=False, default=str)}")

        _process_algo_result(window, result, step_code, step_number, idx)

    except Exception as e:
        logger.error(f"External detection failed: {e}")
        window.detection_status = 'fail'
        window.detection_boxes = []
        try:
            msg = str(e).strip()
            window._set_instruction_text(f"执行失败: {msg}" if msg else "执行失败")
        except Exception:
            pass
        window.update_overlay_visibility()
        window.rebuild_status_section()
        window._start_ng_flash()
        try:
            sp = window._get_step_payload(window.current_step_index)
            sc = get_step_code_from_payload(sp, window.current_step_index)
            save_local_record(window.process_data, False, sc, window.current_step_index + 1, {"status": "ERROR", "message": str(e)}, window._last_qimage)
        except Exception:
            pass
        _report_step_result(window, get_step_code_from_payload(window._get_step_payload(window.current_step_index), window.current_step_index), {"status": "ERROR", "message": str(e)})


def _process_algo_result(window, result: Dict[str, Any], step_code: str, step_number: int, idx: int):
    status = str(result.get('status', '')).upper()
    if status == 'OK':
        data = result.get("data", {})
        result_status = data.get("result_status", "NG")

        if result_status == "OK":
            _handle_detection_ok(window, data, step_code, step_number, idx)
        else:
            _handle_detection_ng(window, data, step_code, step_number, idx)
    else:
        _handle_detection_error(window, result, step_code, step_number, idx)


def _handle_detection_ok(window, data: Dict, step_code: str, step_number: int, idx: int):
    logger.info(f"Detection OK: step={step_number}, data={json.dumps(data, ensure_ascii=False, default=str)}")

    executed_steps = data.get("executed_steps", [])
    valid_rects = []
    for s in executed_steps:
        if s.get("is_correct") and s.get("bbox"):
            bbox_data = s["bbox"]
            if bbox_data and isinstance(bbox_data[0], (list, tuple)):
                for box in bbox_data:
                    if len(box) >= 4:
                        valid_rects.append({"box_coords": list(box[:4])})
            else:
                if len(bbox_data) >= 4:
                    valid_rects.append({"box_coords": list(bbox_data[:4])})

    window.detection_boxes = window._ng_regions_to_rects(valid_rects)
    window.detection_status = 'pass'
    try:
        window._set_instruction_text("执行成功")
    except Exception:
        pass
    window.update_overlay_visibility()
    window.rebuild_status_section()
    save_local_record(window.process_data, True, step_code, step_number, {"status": "OK", "data": data}, window._last_qimage)
    _report_step_result(window, step_code, {"status": "OK", "data": data})

    window.advance_timer = QTimer()
    window.advance_timer.setSingleShot(True)
    window.advance_timer.timeout.connect(window.advance_to_next_step)
    window.advance_timer.start(window.ok_toast_duration * 1000)


def _handle_detection_ng(window, data: Dict, step_code: str, step_number: int, idx: int):
    logger.warning(f"Detection NG: step={step_number}, data={json.dumps(data, ensure_ascii=False, default=str)}")
    defect_rects = data.get('defect_rects', [])
    window.detection_boxes = window._ng_regions_to_rects(defect_rects)
    window.detection_status = 'fail'
    try:
        ng_reason = str(data.get("ng_reason") or "").strip()
        window._set_instruction_text(f"NG原因: {ng_reason}" if ng_reason else "执行失败")
    except Exception:
        pass
    window.update_overlay_visibility()
    window.rebuild_status_section()
    window._start_ng_flash()
    save_local_record(window.process_data, False, step_code, step_number, {"status": "OK", "data": data}, window._last_qimage)
    _report_step_result(window, step_code, {"status": "OK", "data": data})


def _handle_detection_error(window, result: Dict, step_code: str, step_number: int, idx: int):
    logger.error(f"Runner execution failed: {json.dumps(result, ensure_ascii=False, default=str)}")
    window.detection_status = 'fail'
    window.detection_boxes = []
    try:
        msg = str(result.get("message") or "").strip()
        window._set_instruction_text(f"执行失败: {msg}" if msg else "执行失败")
    except Exception:
        pass
    window.update_overlay_visibility()
    window.rebuild_status_section()
    window._start_ng_flash()
    save_local_record(window.process_data, False, step_code, step_number, {"status": "ERROR", "message": result.get("message")}, window._last_qimage)
    window.show_toast(f"执行出错: {result.get('message')}", False)
    _report_step_result(window, step_code, {"status": str(result.get('status', '')).upper() or "ERROR", "message": result.get("message")})


def _report_step_result(window, step_code: str, algo_result: Dict) -> None:
    try:
        from src.services.result_report_service import ResultReportService
        ResultReportService().enqueue_step_result(
            task_no=str(window.process_data.get("task_no") or ""),
            step_code=str(step_code),
            step_status=2,
            process_code=str(window.process_data.get("process_code") or ""),
            qimage=window._last_qimage.copy() if window._last_qimage is not None else None,
            algo_result=algo_result,
        )
    except Exception:
        pass
