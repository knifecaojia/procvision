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


class ThemeLoader:
    """Load and compose QSS stylesheets from theme fragments."""

    DEFAULT_THEME = "dark"

    def __init__(self, theme_name: str = DEFAULT_THEME, base_path: Optional[Path] = None) -> None:
        self.theme_name = theme_name
        self.base_path = base_path or Path(__file__).resolve().parent / "themes" / theme_name

    def stylesheet_path(self, name: str) -> Path:
        """Return the path to a stylesheet fragment."""
        path = self.base_path / f"{name}.qss"
        if not path.exists():
            raise FileNotFoundError(f"Stylesheet fragment not found: {path}")
        return path

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
