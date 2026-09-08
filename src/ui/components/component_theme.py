"""
Shared theme helpers for lightweight UI components.
"""

from __future__ import annotations

from typing import Dict

from src.ui.styles import load_user_theme_preference, resolve_theme_colors

DARK_COMPONENT_DEFAULTS: Dict[str, str] = {
    "deep_graphite": "#1A1D23",
    "steel_grey": "#1F232B",
    "surface": "#252A33",
    "surface_dark": "#171B21",
    "surface_darker": "#101318",
    "dark_border": "#242831",
    "border_subtle": "#2E3440",
    "text_primary": "#F2F4F8",
    "text_muted": "#D6DBE6",
    "cool_grey": "#8C92A0",
    "hover_orange": "#FF8C32",
    "success_green": "#3CC37A",
    "error_red": "#E85454",
    "warning_yellow": "#FFB347",
}


def resolve_component_theme(widget=None) -> Dict[str, str]:
    theme_name = _get_theme_name(widget)
    colors = dict(DARK_COMPONENT_DEFAULTS)
    try:
        from src.core.config import get_config

        config = get_config()
        base_colors = dict(getattr(getattr(config, "ui", None), "colors", {}) or {})
    except Exception:
        base_colors = {}
    colors.update(base_colors)
    colors.update(resolve_theme_colors(theme_name, colors))
    colors["theme_name"] = theme_name
    return colors


def _get_theme_name(widget=None) -> str:
    candidates = [widget]
    if widget is not None:
        try:
            candidates.append(widget.window())
        except Exception:
            pass
        try:
            candidates.append(widget.parentWidget())
        except Exception:
            pass
    for candidate in candidates:
        theme = getattr(candidate, "current_theme", None)
        if theme in {"dark", "light"}:
            return theme
    return load_user_theme_preference()
