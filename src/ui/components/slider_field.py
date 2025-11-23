"""SliderField widget - combined slider and spinbox for numeric parameters."""

from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtWidgets


class SliderField(QtWidgets.QWidget):
    """Combined slider + spin editor for bounded numeric parameters."""

    value_changed = QtCore.Signal(float)

    def __init__(
        self,
        min_value: float,
        max_value: float,
        step: Optional[float],
        decimals: int,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("cameraParamControl")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self._decimals = max(0, decimals)
        self._factor = 10 ** self._decimals
        self._block = False

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Create slider
        self._slider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self._slider.setObjectName("cameraParamSlider")
        slider_min = int(round(min_value * self._factor))
        slider_max = int(round(max_value * self._factor))
        if slider_min == slider_max:
            slider_max = slider_min + 1
        self._slider.setRange(slider_min, slider_max)
        if step:
            slider_step = int(round(step * self._factor))
            self._slider.setSingleStep(max(1, slider_step))
        layout.addWidget(self._slider, 1)

        # Create spinbox
        self._spin = QtWidgets.QDoubleSpinBox(self)
        self._spin.setObjectName("cameraParamSpin")
        self._spin.setDecimals(self._decimals)
        self._spin.setMinimum(min_value)
        self._spin.setMaximum(max_value)
        if step:
            self._spin.setSingleStep(step)
        self._spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self._spin.setFixedWidth(90)
        layout.addWidget(self._spin, 0)

        # Connect signals
        self._slider.valueChanged.connect(self._handle_slider_change)
        self._spin.valueChanged.connect(self._handle_spin_change)

    def set_value(self, value: float) -> None:
        """Set the current value without triggering signals."""
        self._block = True
        try:
            slider_value = int(round(value * self._factor))
            self._slider.setValue(slider_value)
            self._spin.setValue(value)
        finally:
            self._block = False

    def value(self) -> float:
        """Get the current value."""
        return self._spin.value()

    def _handle_slider_change(self, slider_value: int) -> None:
        """Handle slider value change."""
        if self._block:
            return
        self._block = True
        try:
            real_value = slider_value / self._factor
            self._spin.setValue(real_value)
            self.value_changed.emit(real_value)
        finally:
            self._block = False

    def _handle_spin_change(self, spin_value: float) -> None:
        """Handle spinbox value change."""
        if self._block:
            return
        self._block = True
        try:
            slider_value = int(round(spin_value * self._factor))
            self._slider.setValue(slider_value)
            self.value_changed.emit(spin_value)
        finally:
            self._block = False

    def setEnabled(self, enabled: bool) -> None:
        """Enable or disable the widget."""
        super().setEnabled(enabled)
        self._slider.setEnabled(enabled)
        self._spin.setEnabled(enabled)
