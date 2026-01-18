import logging
import queue
import threading
import time
from dataclasses import dataclass
import json
from typing import Any, Dict, Optional, Tuple

import requests

from .network_service import NetworkService

logger = logging.getLogger(__name__)


@dataclass
class _ReportTask:
    kind: str
    payload: Dict[str, Any]
    attempts: int = 0
    created_at: float = 0.0


class ResultReportService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResultReportService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._queue: "queue.Queue[_ReportTask]" = queue.Queue()
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

        self._network = NetworkService()

    def stop(self) -> None:
        self._running = False
        try:
            self._thread.join(timeout=2.0)
        except Exception:
            pass

    def enqueue_step_result(
        self,
        task_no: str,
        step_code: str,
        step_status: int,
        *,
        qimage: Optional[object] = None,
        algo_result: Optional[object] = None,
    ) -> None:
        payload = {
            "task_no": str(task_no),
            "step_code": str(step_code or "").strip(),
            "step_status": int(step_status),
            "algo_result": algo_result,
            "qimage": qimage,
        }
        self._queue.put(_ReportTask(kind="step_result", payload=payload, attempts=0, created_at=time.time()))

    def enqueue_task_status_update(self, task_no: str, status: int) -> None:
        payload = {"task_no": str(task_no), "status": int(status)}
        self._queue.put(_ReportTask(kind="task_status", payload=payload, attempts=0, created_at=time.time()))

    def get_queue_size(self) -> int:
        return self._queue.qsize()

    def _worker_loop(self) -> None:
        while self._running:
            try:
                task = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            except Exception:
                continue

            try:
                self._process_task(task)
            except Exception as e:
                logger.warning("Result report task failed (kind=%s): %s", getattr(task, "kind", "?"), e)
                self._retry_or_drop(task, str(e))
            finally:
                try:
                    self._queue.task_done()
                except Exception:
                    pass

    def _retry_or_drop(self, task: _ReportTask, error: str) -> None:
        task.attempts += 1
        if task.attempts >= 3:
            logger.warning("Result report task dropped (kind=%s attempts=%s error=%s)", task.kind, task.attempts, error)
            return
        backoff = 0.5 * (2 ** (task.attempts - 1))
        time.sleep(backoff)
        self._queue.put(task)

    def _process_task(self, task: _ReportTask) -> None:
        if task.kind == "step_result":
            self._process_step_result(task.payload)
            return
        if task.kind == "task_status":
            self._process_task_status(task.payload)
            return

    def _process_step_result(self, payload: Dict[str, Any]) -> None:
        task_no = str(payload.get("task_no", "")).strip()
        step_code = str(payload.get("step_code", "")).strip()
        step_status = int(payload.get("step_status", 2))
        algo_result = payload.get("algo_result")
        qimage = payload.get("qimage")

        if not task_no or not step_code:
            raise RuntimeError("Missing task_no/step_code for step report")

        object_name = ""
        if qimage is not None:
            image_bytes, content_type = self._encode_qimage_jpeg(qimage, max_bytes=250 * 1024)
            object_name = self._upload_step_image(image_bytes, content_type)
        if not object_name:
            raise RuntimeError("Missing object_name for /client/process report")

        algo_result_str = None
        if algo_result is not None:
            if isinstance(algo_result, str):
                algo_result_str = algo_result
            else:
                algo_result_str = json.dumps(algo_result, ensure_ascii=False)

        body = {
            "task_no": task_no,
            "step_code": step_code,
            "step_status": step_status,
            "object_name": object_name,
            "algo_result": algo_result_str,
        }
        url = f"{self._network.base_url}/client/process"
        r = self._network.session.post(url, json=body, timeout=self._network.timeout)
        r.raise_for_status()

    def _process_task_status(self, payload: Dict[str, Any]) -> None:
        task_no = str(payload.get("task_no", "")).strip()
        status = int(payload.get("status", 3))
        if not task_no:
            raise RuntimeError("Missing task_no for status update")
        url = f"{self._network.base_url}/client/task/status/{task_no}/{status}"
        r = self._network.session.get(url, timeout=self._network.timeout)
        r.raise_for_status()

    def _encode_qimage_jpeg(self, qimage: object, *, max_bytes: int) -> Tuple[bytes, str]:
        try:
            from PySide6.QtCore import QBuffer, QByteArray, QIODevice
            from PySide6.QtGui import QImage
        except Exception as e:
            raise RuntimeError(f"PySide6 not available for image encoding: {e}")

        try:
            qi = qimage.copy() if hasattr(qimage, "copy") else qimage
        except Exception:
            qi = qimage

        if isinstance(qi, QImage):
            if qi.hasAlphaChannel():
                qi = qi.convertToFormat(QImage.Format.Format_RGB888)
            else:
                qi = qi.convertToFormat(QImage.Format.Format_RGB888)

        def encode_jpeg(img: object, quality: int) -> bytes:
            ba = QByteArray()
            buf = QBuffer(ba)
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            ok = False
            try:
                ok = bool(img.save(buf, "JPG", int(quality)))
            except Exception:
                ok = False
            try:
                buf.close()
            except Exception:
                pass
            if not ok:
                raise RuntimeError("Failed to encode image as JPEG")
            return bytes(ba)

        def pick_quality(img: object) -> bytes:
            best: Optional[bytes] = None
            low = 5
            high = 95
            while low <= high:
                mid = (low + high) // 2
                b = encode_jpeg(img, mid)
                if len(b) <= int(max_bytes):
                    best = b
                    low = mid + 1
                else:
                    high = mid - 1
            if best is not None:
                return best
            b = encode_jpeg(img, 1)
            if len(b) <= int(max_bytes):
                return b
            raise RuntimeError(f"JPEG too large even at min quality: size={len(b)} max={int(max_bytes)}")

        try:
            data = pick_quality(qi)
            return data, "image/jpeg"
        except Exception:
            try:
                if isinstance(qi, QImage):
                    gray = qi.convertToFormat(QImage.Format.Format_Grayscale8)
                    data = pick_quality(gray)
                    return data, "image/jpeg"
            except Exception:
                pass
            raise

    def _sanitize_url(self, url: str) -> str:
        s = str(url or "").strip()
        while True:
            before = s
            s = s.strip().strip("`").strip().strip("'").strip().strip('"').strip()
            if s == before:
                break
        return s

    def _upload_step_image(self, data: bytes, content_type: str) -> str:
        url = f"{self._network.base_url}/client/getUrl"
        r = self._network.session.get(url, timeout=self._network.timeout)
        r.raise_for_status()
        try:
            resp = r.json()
        except Exception:
            raise RuntimeError(f"Invalid getUrl response: {r.text}")

        resp_data = resp.get("data") if isinstance(resp, dict) else None
        if not isinstance(resp_data, dict):
            raise RuntimeError("Invalid getUrl response: missing data")

        object_name = str(resp_data.get("objectName") or "").strip()
        upload_url = self._sanitize_url(str(resp_data.get("url") or ""))
        if not object_name or not upload_url:
            raise RuntimeError("Invalid getUrl response: missing objectName/url")

        put = requests.put(upload_url, data=data, headers={"Content-Type": content_type}, timeout=self._network.timeout)
        put.raise_for_status()
        return object_name
