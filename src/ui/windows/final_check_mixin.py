import logging
from typing import Any, Dict, Optional, Tuple

from PySide6.QtWidgets import QScrollArea

logger = logging.getLogger(__name__)

FINAL_CHECK_STEP_CODE = "99"


class FinalCheckMixin:
    def has_final_check(self) -> bool:
        value = self.process_data.get("final_check_flag")
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        return text in {"1", "true", "yes", "y"}

    def get_final_check_step_index(self) -> Optional[int]:
        steps = self.process_data.get("steps_detail") or self.process_data.get("step_infos") or []
        if not isinstance(steps, list):
            return None
        for idx, item in enumerate(steps):
            if not isinstance(item, dict):
                continue
            step_code = str(item.get("step_code") or "").strip()
            if step_code == FINAL_CHECK_STEP_CODE:
                return idx
        return None

    def get_final_check_step_payload(self) -> Tuple[Optional[int], Dict[str, Any]]:
        idx = self.get_final_check_step_index()
        if idx is not None:
            payload = dict(self._get_step_payload(idx))
            if not payload.get("step_code"):
                payload["step_code"] = FINAL_CHECK_STEP_CODE
            if not payload.get("step_number"):
                payload["step_number"] = FINAL_CHECK_STEP_CODE
            return idx, payload
        logger.warning("Final check flag is set, but step_code=99 was not found; using fallback final step")
        return None, {
            "step_code": FINAL_CHECK_STEP_CODE,
            "step_number": 99,
            "step_name": "终检",
            "operation_guide": "终检",
        }

    def can_run_final_check(self) -> bool:
        if not self.has_final_check():
            return False
        if bool(getattr(self, "auto_detect_active", False)):
            return False
        if self.detection_status == "detecting":
            return False
        return bool(getattr(self, "_has_detection_source", lambda: False)())

    def on_final_check_detection(self) -> None:
        if not self.has_final_check():
            return
        if bool(getattr(self, "auto_detect_active", False)):
            self.show_toast("自动检测中不可手工终检", False)
            return
        if self.detection_status == "detecting":
            return
        if not self._has_detection_source():
            self.show_toast("请先开启相机", False)
            return

        if self.detection_status in ("pass", "fail"):
            if self.detection_status == "fail":
                self._set_relay_ng_active(False, "final_check_restart")
            self._stop_ng_flash()
            self.detection_status = "idle"
            self.detection_boxes = []
            self.detection_labels = []
            self._overlay_dismissed = False
            self.update_overlay_visibility()

        idx, payload = self.get_final_check_step_payload()
        self._active_final_check_step_index = idx
        if isinstance(idx, int):
            self._focus_final_check_step(idx)
        self._mark_task_running_once()
        if bool(getattr(self, "is_simulated", False)):
            from .detection_mixin import run_simulated_detection

            run_simulated_detection(
                self,
                step_payload=payload,
                step_index=idx,
                on_ok_complete=self.complete_final_check_task,
            )
            return

        from .detection_mixin import handle_external_detection

        handle_external_detection(
            self,
            step_payload=payload,
            step_index=idx,
            on_ok_complete=self.complete_final_check_task,
        )

    def _focus_final_check_step(self, step_index: int) -> None:
        if step_index < 0 or step_index >= len(self.steps):
            return
        for step in self.steps:
            if step.status == "current":
                step.status = "pending"
        self.current_step_index = step_index
        self.steps[step_index].status = "current"
        self.current_instruction = self.steps[step_index].description
        self._set_instruction_text(self.current_instruction)
        self.progress_label.setText(f"步骤: {step_index + 1} / {self.total_steps}")
        self.progress_bar.setValue(step_index + 1)
        self.rebuild_step_cards()
        self.rebuild_step_bar_cards()
        self._scroll_step_list_to_current()
        self.update_overlay_visibility()
        try:
            self._ensure_guide_for_step(step_index, preload_next=True)
        except Exception:
            pass
        if getattr(self, "split_layout_mode", False):
            try:
                self._display_guide_image(step_index)
            except Exception:
                pass

    def _scroll_step_list_to_current(self) -> None:
        try:
            cards = getattr(self, "step_card_widgets", [])
            idx = int(getattr(self, "current_step_index", 0))
            if idx < 0 or idx >= len(cards):
                return
            scroll_area = self.findChild(QScrollArea, "stepListScrollArea")
            if scroll_area is None:
                return
            scroll_area.ensureWidgetVisible(cards[idx], 0, 24)
        except Exception:
            pass

    def complete_final_check_task(self) -> None:
        self._set_relay_ng_active(False, "final_check_complete")
        idx = getattr(self, "_active_final_check_step_index", None)
        if isinstance(idx, int) and 0 <= idx < len(self.steps):
            self.set_step_status(idx, "completed")
        elif self.steps:
            self.set_step_status(self.current_step_index, "completed")

        self.detection_status = "pass"
        self._overlay_dismissed = False
        try:
            self.rebuild_step_cards()
            self.rebuild_step_bar_cards()
            self.update_overlay_visibility()
            self.rebuild_status_section()
        except Exception:
            pass

        if not bool(getattr(self, "is_simulated", False)):
            try:
                from src.services.result_report_service import ResultReportService

                ResultReportService().enqueue_task_status_update(
                    task_no=str(self.process_data.get("task_no") or ""),
                    status=3,
                )
            except Exception:
                logger.exception("Failed to enqueue final check task completion")

        if getattr(self, "auto_start_next", False):
            self.reset_for_next_product()
            self.show_toast("终检通过，已自动开始下一产品工艺检测", True)
            return
        self.show_completion_dialog()
