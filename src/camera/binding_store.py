from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional

from .types import CameraInfo


@dataclass(frozen=True)
class CameraBinding:
    """Persistent binding between a client slot and a physical camera."""

    slot_name: str
    serial_number: Optional[str]
    expected_ip: Optional[str]
    transport: str
    model_name: Optional[str]
    last_seen_name: Optional[str]

    @classmethod
    def from_camera(cls, slot_name: str, camera: CameraInfo) -> "CameraBinding":
        return cls(
            slot_name=slot_name,
            serial_number=camera.serial_number,
            expected_ip=camera.ip_address,
            transport=camera.transport.value,
            model_name=camera.model_name,
            last_seen_name=camera.name,
        )


class CameraBindingStore:
    """File-backed storage for camera bindings on the local client."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def get(self, slot_name: str) -> Optional[CameraBinding]:
        payload = self._load()
        record = payload.get(slot_name)
        if not isinstance(record, dict):
            return None
        return CameraBinding(
            slot_name=slot_name,
            serial_number=record.get("serial_number"),
            expected_ip=record.get("expected_ip"),
            transport=str(record.get("transport") or "Unknown"),
            model_name=record.get("model_name"),
            last_seen_name=record.get("last_seen_name"),
        )

    def set(self, binding: CameraBinding) -> None:
        payload = self._load()
        payload[binding.slot_name] = asdict(binding)
        self._save(payload)

    def clear(self, slot_name: str) -> None:
        payload = self._load()
        if slot_name in payload:
            payload.pop(slot_name)
            self._save(payload)

    def _load(self) -> Dict[str, dict]:
        if not self.file_path.exists():
            return {}

        try:
            raw = self.file_path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else {}
        except (OSError, json.JSONDecodeError):
            return {}

        return data if isinstance(data, dict) else {}

    def _save(self, payload: Dict[str, dict]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
