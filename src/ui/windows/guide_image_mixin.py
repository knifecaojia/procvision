import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

logger = logging.getLogger(__name__)


class GuideImageDownloadWorker(QThread):
    result_ready = Signal(int, bool, object, str)

    def __init__(self, step_index: int, url: str):
        super().__init__()
        self.step_index = int(step_index)
        self.url = str(url or "").strip()

    def _sanitize_url(self, url: str) -> str:
        s = str(url or "").strip()
        while True:
            before = s
            s = s.strip().strip("`").strip().strip("'").strip().strip('"').strip()
            if s == before:
                break
        return s

    def _redact_url_for_log(self, url: str) -> str:
        s = str(url or "")
        if "X-Amz-" in s or "X-Amz-Signature" in s:
            return s.split("?", 1)[0] + "?<redacted>"
        return s

    def run(self):
        raw_url = self._sanitize_url(self.url)
        if not raw_url:
            logger.info("Guide image skipped (empty url): step_index=%s", self.step_index)
            self.result_ready.emit(self.step_index, False, None, "guide_url empty")
            return
        try:
            from src.services.network_service import NetworkService
            import requests

            ns = NetworkService()
            url = raw_url
            logger.info("Guide image downloading: step_index=%s url=%s", self.step_index, self._redact_url_for_log(url))

            if url.startswith("file://"):
                local_path = url[len("file://"):]
                if os.path.exists(local_path):
                    qi = self._load_local(local_path)
                    if qi:
                        self.result_ready.emit(self.step_index, True, qi, "")
                    else:
                        self.result_ready.emit(self.step_index, False, None, "guide image decode failed")
                    return

            if os.path.exists(url):
                qi = self._load_local(url)
                if qi:
                    self.result_ready.emit(self.step_index, True, qi, "")
                else:
                    self.result_ready.emit(self.step_index, False, None, "guide image decode failed")
                return

            is_presigned = "X-Amz-" in url or "X-Amz-Signature" in url
            if not (url.startswith("http://") or url.startswith("https://")):
                base = str(getattr(ns, "base_url", "") or "").rstrip("/")
                if url.startswith("/"):
                    url = f"{base}{url}" if base else url
                else:
                    url = f"{base}/{url}" if base else url
            if is_presigned:
                resp = requests.get(url, timeout=getattr(ns, "timeout", 10), proxies={"http": None, "https": None})
            else:
                resp = ns.session.get(url, timeout=getattr(ns, "timeout", 10))
            resp.raise_for_status()
            qi = QImage.fromData(resp.content)
            if qi.isNull():
                self.result_ready.emit(self.step_index, False, None, "guide image decode failed")
                return
            logger.info("Guide image loaded: step_index=%s size=%dx%d", self.step_index, qi.width(), qi.height())
            self.result_ready.emit(self.step_index, True, qi, "")
        except Exception as e:
            logger.warning("Guide image download failed: step_index=%s error=%s", self.step_index, e)
            self.result_ready.emit(self.step_index, False, None, str(e))

    def _load_local(self, path: str) -> Optional[QImage]:
        try:
            with open(path, "rb") as f:
                qi = QImage.fromData(f.read())
            if not qi.isNull():
                logger.info("Guide image loaded: step_index=%s size=%dx%d", self.step_index, qi.width(), qi.height())
                return qi
            logger.warning("Guide image decode failed: step_index=%s", self.step_index)
        except Exception:
            pass
        return None


class GuideImageMixin:
    def _get_step_payload(self, step_index: int) -> Dict[str, Any]:
        sd = self.process_data.get("steps_detail") or self.process_data.get("step_infos") or []
        if isinstance(sd, list) and 0 <= step_index < len(sd) and isinstance(sd[step_index], dict):
            return sd[step_index]
        return {}

    def _get_step_guide_url(self, step_index: int) -> str:
        payload = self._get_step_payload(step_index)
        for key in ("guide_url", "guideUrl", "guide_image_url", "guideImageUrl", "guide_img_url", "guideImgUrl", "guidePath"):
            s = str(payload.get(key) or "").strip()
            if s:
                return s
        return ""

    def _get_step_guide_info(self, step_index: int):
        payload = self._get_step_payload(step_index)
        for k in ("guide_info", "guideInfo", "guide_rects", "guideRects", "guide_boxes", "guideBoxes"):
            v = payload.get(k)
            if v is not None and v != "":
                if isinstance(v, str):
                    s = v.strip()
                    if s:
                        try:
                            return json.loads(s)
                        except Exception:
                            return v
                return v
        return []

    def _prune_guide_cache(self, current_step_index: int) -> None:
        keep = {int(current_step_index), int(current_step_index) + 1}
        for idx in list(self._guide_qimages.keys()):
            if idx not in keep:
                self._guide_qimages.pop(idx, None)
        for idx in list(self._guide_errors.keys()):
            if idx not in keep:
                self._guide_errors.pop(idx, None)

    def _ensure_guide_for_step(self, step_index: int, preload_next: bool = False) -> None:
        if getattr(self, "_closing", False):
            return
        try:
            step_index = int(step_index)
        except Exception:
            return
        self._prune_guide_cache(step_index)
        self._start_guide_download(step_index)
        if preload_next:
            self._start_guide_download(step_index + 1, prefetch=True)

    def _start_guide_download(self, step_index: int, prefetch: bool = False) -> None:
        if getattr(self, "_closing", False):
            return
        if step_index < 0 or step_index >= int(self.total_steps or 0):
            return
        if step_index in self._guide_qimages or step_index in self._guide_workers:
            return
        url = self._get_step_guide_url(step_index)
        if not url:
            return
        logger.info("Guide image enqueue: step_index=%s prefetch=%s", step_index, bool(prefetch))
        worker = GuideImageDownloadWorker(step_index, url)
        try:
            worker.setParent(self)
        except Exception:
            pass
        self._guide_workers[step_index] = worker
        worker.result_ready.connect(self._on_guide_download_finished)
        worker.finished.connect(lambda: self._on_guide_thread_finished(step_index))
        worker.finished.connect(worker.deleteLater)
        worker.start()
        if not prefetch and step_index == int(getattr(self, "current_step_index", 0)):
            try:
                self.show_toast("引导图加载中…", True)
            except Exception:
                pass

    def _on_guide_thread_finished(self, step_index: int) -> None:
        try:
            idx = int(step_index)
        except Exception:
            return
        worker = self._guide_workers.get(idx)
        if worker is not None and worker.isRunning():
            return
        self._guide_workers.pop(idx, None)

    def _on_guide_download_finished(self, step_index: int, ok: bool, qimage_obj: object, message: str) -> None:
        if getattr(self, "_closing", False):
            return
        if ok and isinstance(qimage_obj, QImage):
            self._guide_qimages[int(step_index)] = qimage_obj
            self._guide_errors.pop(int(step_index), None)
            logger.info("Guide image ready: step_index=%s", int(step_index))
            self._prune_guide_cache(int(getattr(self, "current_step_index", 0)))
            if int(step_index) == int(getattr(self, "current_step_index", 0)):
                self._start_guide_download(int(step_index) + 1, prefetch=True)
        else:
            self._guide_errors[int(step_index)] = str(message or "guide image download failed")
            logger.warning("Guide image failed: step_index=%s error=%s", int(step_index), message)
            if int(step_index) == int(getattr(self, "current_step_index", 0)):
                try:
                    self.show_toast(f"引导图加载失败: {message}", False)
                except Exception:
                    pass
