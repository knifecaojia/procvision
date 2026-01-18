"""
Theme loader utilities for applying QSS-based UI styles.

Provides helpers to load theme-specific stylesheet fragments and
refresh widgets when dynamic properties change.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, Optional

from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)

LIGHT_THEME_COLORS: Dict[str, str] = {
    "deep_graphite": "#F3F4F7",
    "steel_grey": "#FFFFFF",
    "dark_border": "#CED3E5",
    "arctic_white": "#111827",
    "cool_grey": "#4B5563",
    "hover_orange": "#2563EB",
    "amber": "#1D4ED8",
    "icon_neutral": "#6B7280",
    "success_green": "#22C55E",
    "error_red": "#DC2626",
    "warning_yellow": "#FACC15",
    "title_bar_dark": "#E4E8F5",
    "surface": "#F9FAFE",
    "surface_dark": "#EEF1F8",
    "surface_darker": "#E0E6F3",
    "border_subtle": "#D1D7E6",
    "text_primary": "#111827",
    "text_muted": "#4B5563",
}


class ThemeLoader:
    """Load and compose QSS stylesheets from theme fragments."""

    DEFAULT_THEME = "dark"

    def __init__(self, theme_name: str = DEFAULT_THEME, base_path: Optional[Path] = None) -> None:
        self.theme_name = theme_name
        self.root_path = base_path or Path(__file__).resolve().parent / "themes"

    def stylesheet_path(self, name: str) -> Path:
        """Return the path to a stylesheet fragment."""
        path = self.root_path / self.theme_name / f"{name}.qss"
        if not path.exists():
            raise FileNotFoundError(f"Stylesheet fragment not found: {path}")
        return path

    def set_theme(self, theme_name: str) -> None:
        """Switch to a different theme directory."""
        self.theme_name = theme_name

    def load(self, *names: str, variables: Optional[Dict[str, str]] = None) -> str:
        """
        Load and concatenate one or more stylesheet fragments.

        Args:
            *names: One or more stylesheet fragment names (without .qss extension).
            variables: Optional placeholder replacements (e.g., {'@deep_graphite': '#1A1D23'}).
        """
        sections: Iterable[str] = names or ("base",)
        content: list[str] = []
        for name in sections:
            try:
                fragment = self.stylesheet_path(name).read_text(encoding="utf-8")
            except FileNotFoundError:
                logger.error("Stylesheet fragment '%s' missing for theme '%s'", name, self.theme_name)
                continue
            content.append(fragment)

        stylesheet = "\n\n".join(content)
        return self._inject_variables(stylesheet, variables)

    def apply(self, widget: QWidget, *names: str, variables: Optional[Dict[str, str]] = None) -> None:
        """Apply the composed stylesheet to the target widget."""
        widget.setStyleSheet(self.load(*names, variables=variables))

    @staticmethod
    def _inject_variables(stylesheet: str, variables: Optional[Dict[str, str]]) -> str:
        if not variables:
            return stylesheet
        result = stylesheet
        for placeholder, value in variables.items():
            token = placeholder if placeholder.startswith("@") else f"@{placeholder}"
            result = result.replace(token, value)
        return result


def build_theme_variables(
    colors: Optional[Dict[str, str]] = None,
    font_family: Optional[str] = None,
    extra: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Create a placeholder map for stylesheet injection."""
    replacements: Dict[str, str] = {}
    if colors:
        replacements.update({f"@{key}": value for key, value in colors.items()})
    if font_family:
        replacements["@font_family"] = font_family
    if extra:
        for key, value in extra.items():
            placeholder = key if key.startswith("@") else f"@{key}"
            replacements[placeholder] = value
    return replacements


def refresh_widget_styles(widget: QWidget) -> None:
    """Force Qt to re-evaluate a widget's stylesheet after property changes."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def resolve_theme_colors(theme_name: str, base_colors: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Return a palette adjusted for the requested theme."""
    colors: Dict[str, str] = {}
    if base_colors:
        colors.update(base_colors)
    if theme_name == "light":
        colors.update(LIGHT_THEME_COLORS)
    return colors


def load_user_theme_preference(config_path: Optional[Path] = None) -> str:
    """Read persisted theme preference from config.json."""
    path = config_path or Path.cwd() / "config.json"
    try:
        if not path.exists():
            return ThemeLoader.DEFAULT_THEME
        data = path.read_text(encoding="utf-8")
        import json

        payload = json.loads(data)
        theme = payload.get("general", {}).get("theme")
        if theme in {"dark", "light"}:
            return theme
    except Exception:
        logger.exception("Failed to load theme preference from %s", path)
    return ThemeLoader.DEFAULT_THEME


def save_user_theme_preference(theme: str, config_path: Optional[Path] = None) -> None:
    """Persist theme preference into config.json."""
    path = config_path or Path.cwd() / "config.json"
    try:
        import json

        payload = {}
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
        payload.setdefault("general", {})
        payload["general"]["theme"] = theme
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        logger.exception("Failed to save theme preference to %s", path)
