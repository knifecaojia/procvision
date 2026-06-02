import logging
from typing import Any, Dict, List, Optional

from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen

logger = logging.getLogger(__name__)


def _unwrap_result_data(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return payload


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() == "none":
            return None
        try:
            return float(text)
        except Exception:
            return None
    return None


def _normalize_region(region: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(region, dict):
        return None

    coords = region.get("box_coords")
    x1 = y1 = x2 = y2 = None
    if isinstance(coords, (list, tuple)) and len(coords) >= 4:
        x1 = _to_float(coords[0])
        y1 = _to_float(coords[1])
        x2 = _to_float(coords[2])
        y2 = _to_float(coords[3])
    else:
        rx = _to_float(region.get("x"))
        ry = _to_float(region.get("y"))
        rw = _to_float(region.get("width"))
        rh = _to_float(region.get("height"))
        if all(v is not None for v in (rx, ry, rw, rh)):
            x1, y1, x2, y2 = rx, ry, rx + rw, ry + rh

    if any(v is None for v in (x1, y1, x2, y2)):
        return None
    if x2 <= x1 or y2 <= y1:
        return None

    normalized = dict(region)
    normalized["box_coords"] = [float(x1), float(y1), float(x2), float(y2)]
    return normalized


def _collect_regions_from_list(items: Any) -> List[Dict[str, Any]]:
    regions: List[Dict[str, Any]] = []
    if not isinstance(items, (list, tuple)):
        return regions
    for item in items:
        normalized = _normalize_region(item)
        if normalized is not None:
            regions.append(normalized)
    return regions


def extract_detection_regions(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    data = _unwrap_result_data(payload)

    position_rects = _collect_regions_from_list(data.get("position_rects"))
    if position_rects:
        return position_rects

    bbox_rects = _collect_regions_from_list(data.get("bbox"))
    if bbox_rects:
        return bbox_rects

    regions = _collect_regions_from_list(data.get("defect_rects"))
    executed_steps = data.get("executed_steps") or []
    if isinstance(executed_steps, (list, tuple)):
        for step in executed_steps:
            if not isinstance(step, dict):
                continue
            if not step.get("is_correct"):
                continue
            bbox = step.get("bbox")
            if isinstance(bbox, (list, tuple)) and bbox:
                if isinstance(bbox[0], (list, tuple)):
                    for box in bbox:
                        if len(box) >= 4:
                            normalized = _normalize_region({"box_coords": list(box[:4])})
                            if normalized is not None:
                                regions.append(normalized)
                elif len(bbox) >= 4:
                    normalized = _normalize_region({"box_coords": list(bbox[:4])})
                    if normalized is not None:
                        regions.append(normalized)
    return regions


def build_detection_labels(
    payload: Optional[Dict[str, Any]],
    region_count: int,
    *,
    is_ok: bool,
) -> List[str]:
    data = _unwrap_result_data(payload)
    labels: List[str] = []

    ng_reason_raw = str(data.get("ng_reason") or "").strip()
    if ng_reason_raw and "|" in ng_reason_raw:
        reason_parts = [part.strip() for part in ng_reason_raw.split("|") if part.strip()]
    elif ng_reason_raw:
        reason_parts = [ng_reason_raw]
    else:
        reason_parts = []

    source_regions = extract_detection_regions(payload)
    default_label = "OK" if is_ok else "NG"

    for index in range(region_count):
        if not is_ok and index < len(reason_parts):
            labels.append(reason_parts[index])
            continue
        if index < len(source_regions):
            label = str(source_regions[index].get("label") or "").strip()
            if label:
                labels.append(label)
                continue
        if is_ok:
            labels.append(default_label)
        else:
            labels.append(f"缺陷{index + 1}" if region_count > 1 else default_label)
    return labels


def build_annotated_qimage(
    qimage: Optional[QImage],
    payload: Optional[Dict[str, Any]],
    *,
    is_ok: bool,
    draw_ok: bool,
    draw_ng: bool,
) -> Optional[QImage]:
    if qimage is None or not isinstance(qimage, QImage):
        return qimage

    annotated = qimage.copy()
    if is_ok and not draw_ok:
        return annotated
    if not is_ok and not draw_ng:
        return annotated

    regions = extract_detection_regions(payload)
    if not regions:
        return annotated

    labels = build_detection_labels(payload, len(regions), is_ok=is_ok)

    if is_ok:
        pen_color = QColor(34, 197, 94, 220)
        fill_color = QColor(34, 197, 94, 60)
        label_color = QColor(34, 197, 94, 230)
    else:
        pen_color = QColor(239, 68, 68, 220)
        fill_color = QColor(239, 68, 68, 60)
        label_color = QColor(239, 68, 68, 230)

    try:
        painter = QPainter(annotated)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen_width = max(2, min(6, int(min(annotated.width(), annotated.height()) / 240) or 2))
        painter.setPen(QPen(pen_color, pen_width))
        font = QFont(painter.font())
        font.setPixelSize(max(13, min(24, int(min(annotated.width(), annotated.height()) / 36) or 13)))
        painter.setFont(font)
        metrics = painter.fontMetrics()

        for index, region in enumerate(regions):
            coords = region.get("box_coords") or []
            if len(coords) < 4:
                continue
            x1 = max(0, min(int(round(coords[0])), annotated.width() - 1))
            y1 = max(0, min(int(round(coords[1])), annotated.height() - 1))
            x2 = max(0, min(int(round(coords[2])), annotated.width()))
            y2 = max(0, min(int(round(coords[3])), annotated.height()))
            if x2 <= x1 or y2 <= y1:
                continue

            width = max(1, x2 - x1)
            height = max(1, y2 - y1)
            painter.fillRect(x1, y1, width, height, fill_color)
            painter.drawRect(x1, y1, width, height)

            label_text = labels[index] if index < len(labels) else ("OK" if is_ok else "NG")
            text_width = max(38, metrics.horizontalAdvance(label_text) + 12)
            text_height = max(20, metrics.height() + 6)
            label_top = y1 - text_height - 2
            if label_top < 0:
                label_top = y1 + 2
            label_left = max(0, min(x1, max(0, annotated.width() - text_width)))
            painter.fillRect(label_left, label_top, text_width, text_height, label_color)
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(label_left, label_top, text_width, text_height, 0x84, label_text)
            painter.setPen(QPen(pen_color, pen_width))
        painter.end()
    except Exception as exc:
        logger.warning("Failed to annotate detection image: %s", exc)
        return qimage.copy()

    return annotated
