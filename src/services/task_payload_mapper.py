"""
Task payload normalization helpers for the assembly task workflow.
"""

from __future__ import annotations

from typing import Any, Dict, List


MATERIAL_FIELDS = [
    "assembly_number",
    "position_number",
    "model_no",
    "polarity_direction",
    "material_no",
    "material_name",
    "material_quantity",
    "material_unit",
    "error_prevention_mark",
]


def _as_text(value: Any) -> str:
    """Return a trimmed string representation for text-like values."""
    return str(value or "").strip()


def _display_value(value: Any) -> str:
    """Convert empty-like values to a UI-friendly placeholder."""
    if value is None:
        return "-"
    if isinstance(value, str) and not value.strip():
        return "-"
    return str(value)


def has_error_prevention_mark(material: Dict[str, Any]) -> bool:
    """Return whether a material entry carries an error-prevention marker."""
    return bool(_as_text(material.get("error_prevention_mark")))


def normalize_material_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a single material entry to the new API shape."""
    material: Dict[str, Any] = {}
    for field in MATERIAL_FIELDS:
        material[field] = item.get(field)
        material[f"{field}_display"] = _display_value(item.get(field))

    material["has_error_prevention_mark"] = has_error_prevention_mark(material)
    return material


def normalize_material_list(material_list: Any) -> List[Dict[str, Any]]:
    """Normalize material entries while keeping unknown values harmless."""
    if not isinstance(material_list, list):
        return []
    return [normalize_material_item(item) for item in material_list if isinstance(item, dict)]


def normalize_task_row(row: Dict[str, Any], algo_lookup: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    """Normalize a task list row for UI consumption."""
    task_no = _as_text(row.get("task_no") or row.get("work_order_code"))
    craft_no = _as_text(row.get("craft_no") or row.get("craft_code"))
    craft_version = _as_text(row.get("craft_version"))
    craft_name = _as_text(row.get("craft_name"))
    process_code = _as_text(row.get("process_code"))
    process_name = _as_text(row.get("process_name") or row.get("process"))
    process_desc = _as_text(row.get("process_desc"))
    worker_name = _as_text(row.get("worker_name"))
    status = row.get("status")
    status_str = str(status) if status is not None else ""
    algorithm_id = _as_text(row.get("algorithm_id") or row.get("algorithm_code"))
    step_infos = row.get("step_infos") or row.get("steps") or row.get("step_list") or []
    prod_order_no = _as_text(row.get("prod_order_no"))
    material_list = normalize_material_list(row.get("material_list"))

    algo_meta = algo_lookup.get(algorithm_id, {}) if algorithm_id else {}
    algorithm_name = _as_text(algo_meta.get("name")) or algorithm_id
    algorithm_version = _as_text(algo_meta.get("version"))

    return {
        "work_order_code": task_no,
        "craft_code": craft_no,
        "craft_version": craft_version,
        "craft_name": craft_name,
        "process_code": process_code,
        "process_name": process_name,
        "process_desc": process_desc,
        "prod_order_no": prod_order_no,
        "start_time": row.get("start_time"),
        "end_time": row.get("end_time"),
        "worker_code": row.get("worker_code"),
        "worker_name": worker_name,
        "status": status_str,
        "algorithm_code": algorithm_id,
        "algorithm_name": algorithm_name,
        "algorithm_version": algorithm_version,
        "step_infos": step_infos if isinstance(step_infos, list) else [],
        "material_list": material_list,
        "raw_task": row,
    }

