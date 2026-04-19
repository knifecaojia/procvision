import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LocalRecordService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LocalRecordService, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._base_dir = self._resolve_base_dir()

    @staticmethod
    def _resolve_base_dir() -> Path:
        try:
            from src.core.paths import get_app_base_dir
            return get_app_base_dir() / "records"
        except Exception:
            return Path.cwd() / "records"

    def _ensure_dir(self, task_no: str) -> Path:
        now = datetime.now()
        month_dir = now.strftime("%Y-%m")
        record_dir = self._base_dir / month_dir / task_no
        record_dir.mkdir(parents=True, exist_ok=True)
        return record_dir

    @staticmethod
    def _make_timestamp() -> str:
        return datetime.now().strftime("%Y%m%d%H%M%S")

    @staticmethod
    def _status_label(is_ok: bool) -> str:
        return "OK" if is_ok else "NG"

    def save_record(
        self,
        task_no: str,
        step_code: str,
        step_number: int,
        is_ok: bool,
        process_code: str = "",
        algorithm_name: str = "",
        algorithm_version: str = "",
        ng_reason: str = "",
        defect_rects: Optional[list] = None,
        algo_result: Optional[Dict[str, Any]] = None,
        qimage: Optional[object] = None,
    ) -> Optional[str]:
        if not task_no:
            return None
        try:
            record_dir = self._ensure_dir(task_no)
            ts = self._make_timestamp()
            status_label = self._status_label(is_ok)
            base_name = f"{step_number}_{ts}_{status_label}"

            record = {
                "task_no": task_no,
                "step_code": str(step_code or "").strip(),
                "step_number": step_number,
                "status": status_label,
                "process_code": str(process_code or "").strip(),
                "algorithm_name": str(algorithm_name or "").strip(),
                "algorithm_version": str(algorithm_version or "").strip(),
                "ng_reason": str(ng_reason or "").strip(),
                "defect_rects": defect_rects or [],
                "algo_result": algo_result,
                "timestamp": datetime.now().isoformat(),
            }

            json_path = record_dir / f"{base_name}.json"
            json_path.write_text(
                json.dumps(record, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

            if qimage is not None:
                self._save_image(qimage, record_dir / f"{base_name}.jpg")

            logger.info(
                "Local record saved: %s step=%s status=%s",
                task_no, step_number, status_label,
            )
            return str(json_path)

        except Exception as e:
            logger.warning("Failed to save local record: %s", e)
            return None

    @staticmethod
    def _save_image(qimage: object, path: Path) -> None:
        try:
            from PySide6.QtGui import QImage
        except Exception:
            return
        if not isinstance(qimage, QImage):
            return
        qi = qimage.copy()
        if qi.hasAlphaChannel():
            qi = qi.convertToFormat(QImage.Format.Format_RGB888)
        else:
            qi = qi.convertToFormat(QImage.Format.Format_RGB888)
        qi.save(str(path), "JPG", 90)
