import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _safe_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        return str(data)


class DetectionTaskTraceService:
    """Writes structured summaries for each auto-detect task."""

    def log_summary(self, payload: Optional[Dict[str, Any]]) -> None:
        if not isinstance(payload, dict):
            logger.info("DETECTION_TASK_TRACE payload=null")
            return

        summary = {
            "task_seq": payload.get("task_seq"),
            "task_no": payload.get("task_no"),
            "process_code": payload.get("process_code"),
            "step_code": payload.get("step_code"),
            "step_index": payload.get("step_index"),
            "started_at": payload.get("started_at"),
            "finished_at": payload.get("finished_at"),
            "elapsed_ms": payload.get("elapsed_ms"),
            "result_status": payload.get("result_status"),
            "ng_reported": payload.get("ng_reported"),
            "ng_latched_before": payload.get("ng_latched_before"),
            "ng_latched_after": payload.get("ng_latched_after"),
            "draw_boxes_ok": payload.get("draw_boxes_ok"),
            "draw_boxes_ng": payload.get("draw_boxes_ng"),
            "box_count": payload.get("box_count"),
            "message": payload.get("message"),
            "algo_debug": payload.get("algo_debug"),
            "algo_executed_steps": payload.get("algo_executed_steps"),
        }
        logger.info("DETECTION_TASK_TRACE %s", _safe_json(summary))
