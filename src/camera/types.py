from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class CameraTransport(Enum):
    """Logical transport types supported by the application."""

    GIGE = "GigE"
    USB = "USB"
    UNKNOWN = "Unknown"


@dataclass(frozen=True)
class CameraInfo:
    """Discovery information for a single camera device."""

    id: str
    name: str
    transport: CameraTransport
    serial_number: Optional[str] = None
    ip_address: Optional[str] = None
    manufacturer: Optional[str] = None
    model_name: Optional[str] = None
    backend_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CameraParameter:
    """Describes a camera parameter that can be shown and edited via the UI."""

    key: str
    display_name: str
    unit: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    value_type: type = float
    read_only: bool = False
    group: str = "Imaging"
    # For enum-like parameters: map choice key -> display name
    choices: Optional[Dict[str, str]] = None
