from __future__ import annotations

from typing import Optional

from .types import CameraInfo


def get_camera_usage_status(camera: CameraInfo) -> str:
    """Return a user-facing usage status for a discovered camera."""
    if camera.accessible is True:
        return "空闲可连接"
    if camera.accessible is False:
        return "使用中/不可访问"
    if camera.access_status:
        return camera.access_status
    return "状态未知"


def int_to_ipv4(value: object) -> Optional[str]:
    """Convert an SDK integer IPv4 value to dotted-decimal notation."""
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None

    try:
        number = int(value)
    except (TypeError, ValueError):
        return None

    if number < 0:
        return None

    return ".".join(
        str((number >> shift) & 0xFF)
        for shift in (24, 16, 8, 0)
    )


def build_camera_id(
    serial_number: Optional[str],
    transport: str,
    model_name: Optional[str],
    ip_address: Optional[str],
) -> str:
    """Build a stable application-level identifier for a camera."""
    if serial_number:
        return f"HIK-SN-{serial_number}"

    model_token = (model_name or "unknown").replace(" ", "_")
    ip_token = (ip_address or "unknown").replace(".", "_")
    return f"HIK-FALLBACK-{transport}-{model_token}-{ip_token}"


def camera_matches(left: CameraInfo, right: CameraInfo) -> bool:
    """Return True when two discovery entries refer to the same physical camera."""
    if left.serial_number and right.serial_number:
        return left.serial_number == right.serial_number

    if left.id and right.id and left.id == right.id:
        return True

    return (
        left.transport == right.transport
        and (left.model_name or "") == (right.model_name or "")
        and (left.ip_address or "") == (right.ip_address or "")
    )


def build_camera_display_label(camera: CameraInfo, *, is_bound: bool = False) -> str:
    """Create a human-readable label for camera selection widgets."""
    prefix = "已绑定" if is_bound else "未绑定"
    serial = camera.serial_number or "无序列号"
    ip_address = camera.ip_address or "无IP"
    status = get_camera_usage_status(camera)

    name = camera.name or camera.user_defined_name or camera.model_name or "未命名相机"
    return f"{prefix} | {name} | SN:{serial} | IP:{ip_address} | {status}"
