import contextlib
from itertools import chain, product, repeat
from typing import Optional

from fonticon_mdi6 import MDI6
from pymmcore_plus import CMMCorePlus, DeviceType
from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from superqt.fonticon import icon, setTextIcon
from superqt.utils import signals_blocked

from micromanager_gui import _core

from ..._core_widgets._stage_widget._autofocusDevicies import AutofocusDevice

AlignCenter = Qt.AlignmentFlag.AlignCenter
PREFIX = MDI6.__name__.lower()
STAGE_DEVICES = {DeviceType.Stage, DeviceType.XYStage}
STYLE = """
QPushButton {
    border: none;
    background: transparent;
    color: rgb(0, 180, 0);
    font-size: 40px;
}
QPushButton:hover:!pressed {
    color: rgb(0, 255, 0);
}
QPushButton:disabled {
    color: rgb(169, 169, 169);
}
QPushButton:hover:!pressed {
    color: rgb(0, 255, 0);
}
QSpinBox {
    min-width: 35px;
    height: 22px;
}
QLabel {
    color: #999;
}
QCheckBox {
    color: #999;
}
QCheckBox::indicator {
    width: 11px;
    height: 11px;
}
"""


class StageWidget(QWidget):
    """Create a widget to control a XY and/or a Z stage.

    Parameters
    ----------
    device: str:
        Stage device label. For Autofocus devices, is the label of type 'StageDevice'.
        e.g. for Nikon Ti PFS, 'TIPFSOffset'.
    levels: Optional[int]:
        Number of "arrow" buttons per widget per direction, by default, 2.
    parent : Optional[QWidget]
        Optional parent widget, by default None.
    """

    # fmt: off
    BTNS = {
        # btn glyph                (r, c, xmag, ymag)
        MDI6.chevron_triple_up:    (0, 3,  0,  3),
        MDI6.chevron_double_up:    (1, 3,  0,  2),
        MDI6.chevron_up:           (2, 3,  0,  1),
        MDI6.chevron_down:         (4, 3,  0, -1),
        MDI6.chevron_double_down:  (5, 3,  0, -2),
        MDI6.chevron_triple_down:  (6, 3,  0, -3),
        MDI6.chevron_triple_left:  (3, 0, -3,  0),
        MDI6.chevron_double_left:  (3, 1, -2,  0),
        MDI6.chevron_left:         (3, 2, -1,  0),
        MDI6.chevron_right:        (3, 4,  1,  0),
        MDI6.chevron_double_right: (3, 5,  2,  0),
        MDI6.chevron_triple_right: (3, 6,  3,  0),
    }
    BTN_SIZE = 30
    # fmt: on

    def __init__(
        self,
        device: str,
        levels: Optional[int] = 2,
        parent: Optional[QWidget] = None,
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ):
        super().__init__()

        self.setStyleSheet(STYLE)

        self._mmc = mmcore or _core.get_core_singleton()
        self._levels = levels

        self._device = device
        self._dtype = self._mmc.getDeviceType(self._device)

        assert self._dtype in STAGE_DEVICES, f"{self._dtype} not in {STAGE_DEVICES}"

        self._timer = None
        self._on_off = False

        self._is_autofocus = False
        self._check_if_autofocus()

        self._create_widget()

        self._connect_events()

        self._set_as_default()

        self.destroyed.connect(self._disconnect)

        if self._is_autofocus:
            self._set_offset_checkbox_state(
                self._device.autofocus_device,
                "State",
                self._mmc.getProperty(self._device.autofocus_device, "State")
            )
            self._on_offset_changed(self._device.autofocus_device, "State")
        elif self._dtype is DeviceType.Stage:
            self._disable_Z_Stage()

    def _check_if_autofocus(self):
        if self._dtype is DeviceType.Stage and self._mmc.getAutoFocusDevice():

            with contextlib.suppress(Exception):
                autofocus = AutofocusDevice.create(
                    self._mmc.getAutoFocusDevice(), self._mmc
                )
                if autofocus.offset_device == self._device:
                    self._device = autofocus
                    self._is_autofocus = True

    def _create_widget(self):
        self._step = QDoubleSpinBox()
        self._step.setValue(10)
        self._step.setMaximum(9999)
        self._step.valueChanged.connect(self._update_ttips)
        self._step.clearFocus()
        self._step.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, 0)
        self._step.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._step.setAlignment(AlignCenter)

        self._btns = QWidget()
        self._btns.setLayout(QGridLayout())
        self._btns.layout().setContentsMargins(0, 0, 0, 0)
        self._btns.layout().setSpacing(0)
        for glpyh, (row, col, *_) in self.BTNS.items():
            btn = QPushButton()
            btn.setFlat(True)
            btn.setFixedSize(self.BTN_SIZE, self.BTN_SIZE)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            setTextIcon(btn, glpyh)
            btn.clicked.connect(self._on_click)
            self._btns.layout().addWidget(btn, row, col, AlignCenter)

        self._btns.layout().addWidget(self._step, 3, 3, AlignCenter)
        self._set_visible_levels(self._levels)
        self._set_xy_visible()
        self._update_ttips()

        self._readout = QLabel()
        self._readout.setAlignment(AlignCenter)
        self._update_position_label()

        self._poll_cb = QCheckBox("poll")
        self._poll_cb.setMaximumWidth(50)
        self._poll_timer = QTimer()
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self._update_position_label)
        self._poll_cb.toggled.connect(self._toggle_poll_timer)

        self.snap_checkbox = QCheckBox(text="Snap on Click")

        self.radiobutton = QRadioButton(text="Set as Default")
        self.radiobutton.toggled.connect(self._on_radiobutton_toggled)

        if self._is_autofocus:
            self.offset_checkbox = QCheckBox(text="On/Off")
            self.offset_checkbox.setIcon(
                icon(MDI6.checkbox_blank_circle, color=(169, 169, 169))
            )
            self.offset_checkbox.stateChanged.connect(self._on_offset_checkbox_toggled)

        top_row = QWidget()
        top_row_layout = QHBoxLayout()
        top_row_layout.setAlignment(AlignCenter)
        top_row.setLayout(top_row_layout)
        if not self._is_autofocus:
            top_row.layout().addWidget(self.radiobutton)

        bottom_row_1 = QWidget()
        bottom_row_1.setLayout(QHBoxLayout())
        bottom_row_1.layout().addWidget(self._readout)

        bottom_row_2 = QWidget()
        bottom_row_2_layout = QHBoxLayout()
        bottom_row_2_layout.setSpacing(10)
        bottom_row_2_layout.setContentsMargins(0, 0, 0, 0)
        bottom_row_2_layout.setAlignment(AlignCenter)
        bottom_row_2.setLayout(bottom_row_2_layout)
        bottom_row_2.layout().addWidget(self.snap_checkbox)
        if self._is_autofocus:
            bottom_row_2.layout().addWidget(self.offset_checkbox)
        else:
            bottom_row_2.layout().addWidget(self._poll_cb)

        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(5, 5, 5, 5)
        self.layout().addWidget(top_row)
        self.layout().addWidget(self._btns, AlignCenter)
        self.layout().addWidget(bottom_row_1)
        self.layout().addWidget(bottom_row_2)

    def _connect_events(self):
        self._mmc.events.propertyChanged.connect(self._on_prop_changed)
        self._mmc.events.systemConfigurationLoaded.connect(self._os_system_cfg)
        if self._dtype is DeviceType.XYStage:
            event = self._mmc.events.XYStagePositionChanged
        else:
            event = self._mmc.events.stagePositionChanged
        event.connect(self._update_position_label)

    def _on_prop_changed(self, dev_name: str, prop_name: str, value: str):
        self._on_prop_core_changed(dev_name, prop_name, value)
        self._disable_if_autofocus_is_locked(dev_name)
        self._set_offset_checkbox_state(dev_name, prop_name, value)
        self._on_offset_changed(dev_name, prop_name)

    def _os_system_cfg(self):
        if self._dtype is DeviceType.XYStage:
            if self._device not in self._mmc.getLoadedDevicesOfType(DeviceType.XYStage):
                self._enable_and_update(False)
            else:
                self._enable_and_update(True)

        elif self._is_autofocus:
            if self._device.offset_device not in self._mmc.getLoadedDevicesOfType(
                DeviceType.Stage
            ) or self._device.autofocus_device not in self._mmc.getLoadedDevicesOfType(
                DeviceType.AutoFocus
            ):
                self._enable_and_update(False)
            else:
                self._enable_and_update(True)

            self._on_offset_changed(self._device.autofocus_device, "State")

        elif self._dtype is DeviceType.Stage:
            if self._device not in self._mmc.getLoadedDevicesOfType(DeviceType.Stage):
                self._enable_and_update(False)
            else:
                self._enable_and_update(True)

            self._disable_Z_Stage()

        self._set_as_default()

    def _enable_and_update(self, enable: bool):
        if enable:
            self._enable_wdg(True)
            self._update_position_label()
        else:
            self._readout.setText(f"{self._device} not loaded.")
            self._enable_wdg(False)

    def _enable_wdg(self, enabled):
        self._step.setEnabled(enabled)
        self._btns.setEnabled(enabled)
        self.snap_checkbox.setEnabled(enabled)
        self._poll_cb.setEnabled(enabled)
        if not self._is_autofocus:
            self.radiobutton.setEnabled(enabled)

    def _on_prop_core_changed(self, dev_name: str, prop_name: str, value: str):
        if dev_name != "Core" or self._is_autofocus:
            return

        if self._dtype is DeviceType.XYStage and prop_name == "XYStage":
            with signals_blocked(self.radiobutton):
                self.radiobutton.setChecked(value == self._device)

        elif self._dtype is DeviceType.Stage and prop_name == "Focus":
            with signals_blocked(self.radiobutton):
                self.radiobutton.setChecked(value == self._device)

    def _disable_if_autofocus_is_locked(self, dev_name: str):
        if self._is_autofocus or dev_name != self._mmc.getAutoFocusDevice():
            return

        if self._dtype is DeviceType.Stage:

            if (
                self._mmc.isContinuousFocusEnabled()
                and self._mmc.isContinuousFocusLocked()
            ) or self._mmc.getProperty(
                self._mmc.getAutoFocusDevice(), "Status"
            ) == "Focusing":
                self._enable_wdg(False)
            else:
                self._enable_wdg(True)

    def _on_offset_changed(self, dev_name: str, prop_name: str):
        if (
            self._is_autofocus
            and dev_name == self._device.autofocus_device
            and prop_name
            in {
                "State",
                "Status",
            }
        ):  
            self._on_offset_state_changed()
    
    def _set_offset_checkbox_state(self, dev_name: str, prop_name: str, value: str):
        if (
            self._is_autofocus
            and dev_name == self._device.autofocus_device
            and prop_name == "State"
        ):  
            with signals_blocked(self.offset_checkbox):
                self.offset_checkbox.setChecked(value == "On")

    def _set_as_default(self):
        current_xy = self._mmc.getXYStageDevice()
        current_z = self._mmc.getFocusDevice()
        if self._dtype is DeviceType.XYStage and current_xy == self._device:
            self.radiobutton.setChecked(True)

        elif self._is_autofocus:
            return

        elif current_z == self._device:
            self.radiobutton.setChecked(True)

    def _disable_Z_Stage(self):
        autofocusf_dev = self._mmc.getAutoFocusDevice()
        if not autofocusf_dev:
            return
        if self._mmc.isContinuousFocusEnabled() and self._mmc.isContinuousFocusLocked():
            self._enable_wdg(False)

    def _on_offset_checkbox_toggled(self, state: int):
        self._device.setState(self._device.autofocus_device, state > 0)

    def _on_radiobutton_toggled(self, state: bool):
        if self._dtype is DeviceType.XYStage:
            if state:
                self._mmc.setProperty("Core", "XYStage", self._device)
            elif (
                not state
                and len(self._mmc.getLoadedDevicesOfType(DeviceType.XYStage)) == 1
            ):
                with signals_blocked(self.radiobutton):
                    self.radiobutton.setChecked(True)
            else:
                self._mmc.setProperty("Core", "XYStage", "")

        elif self._is_autofocus:
            return

        elif self._dtype is DeviceType.Stage:
            if state:
                self._mmc.setProperty("Core", "Focus", self._device)
            else:
                devs = len(self._mmc.getLoadedDevicesOfType(DeviceType.Stage))
                if (self._mmc.getAutoFocusDevice() and devs == 2) or devs == 1:
                    with signals_blocked(self.radiobutton):
                        self.radiobutton.setChecked(True)
                else:
                    self._mmc.setProperty("Core", "Focus", "")

    def _toggle_poll_timer(self, on: bool):
        self._poll_timer.start() if on else self._poll_timer.stop()

    def _update_position_label(self):
        if (
            self._dtype is DeviceType.XYStage
            and self._device in self._mmc.getLoadedDevicesOfType(DeviceType.XYStage)
        ):
            pos = self._mmc.getXYPosition(self._device)
            p = ", ".join(str(round(x, 2)) for x in pos)
            self._readout.setText(f"{self._device}:  {p}")

        else:
            dev = self._device.offset_device if self._is_autofocus else self._device
            if dev in self._mmc.getLoadedDevicesOfType(DeviceType.Stage):
                if self._is_autofocus:
                    p = round(self._device.get_position(dev), 2)
                else:
                    p = round(self._mmc.getPosition(dev), 2)
                self._readout.setText(f"{dev}:  {p}")

    def _on_offset_state_changed(self):

        af = self._device.autofocus_device
        
        if not self._device.isEnabled():
            self._enable_wdg(False)
            self._stop_offset_timer()
            self.offset_checkbox.setIcon(
                icon(MDI6.checkbox_blank_circle, color=(169, 169, 169))
            )  # gray

        elif self._device.isEnabled():
            if self._device.isLocked() or (
                self._device.isLocked() and self._device.isFocusing(af)
            ):
                self._enable_wdg(True)
                self._stop_offset_timer()
                self.offset_checkbox.setIcon(
                    icon(MDI6.checkbox_blank_circle, color=(0, 255, 0))
                )  # green

            else:
                self._start_offset_timer()

    def _start_offset_timer(self):
        self._timer = QTimer()
        self._timer.timeout.connect(self._blink)
        self._timer.start(500)

    def _stop_offset_timer(self):
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
            self._on_off

    def _blink(self):
        if self._on_off:
            self.offset_checkbox.setIcon(
                icon(MDI6.checkbox_blank_circle, color=(0, 255, 0))
            )
        else:
            self.offset_checkbox.setIcon(
                icon(MDI6.checkbox_blank_circle, color=(69, 69, 69))
            )
        self._on_off = not self._on_off

    def _update_ttips(self):
        coords = chain(zip(repeat(3), range(7)), zip(range(7), repeat(3)))

        if self._dtype is DeviceType.XYStage:
            Y = "Y"
        elif self._is_autofocus:
            Y = "Offset"
        else:
            Y = "Z"

        btn_layout: QGridLayout = self._btns.layout()
        for r, c in coords:
            if item := btn_layout.itemAtPosition(r, c):
                if (r, c) == (3, 3):
                    continue
                if btn := item.widget():
                    xmag, ymag = self.BTNS[f"{PREFIX}.{btn.text()}"][-2:]
                    if xmag:
                        btn.setToolTip(f"move X by {self._scale(xmag)} µm")
                    elif ymag:
                        btn.setToolTip(f"move {Y} by {self._scale(ymag)} µm")

    def _set_xy_visible(self):
        if self._dtype is not DeviceType.XYStage:
            btn_layout: QGridLayout = self._btns.layout()
            for c in (0, 1, 2, 4, 5, 6):
                if item := btn_layout.itemAtPosition(3, c):
                    item.widget().hide()

    def _set_visible_levels(self, levels: int):
        """Hide upper-level stage buttons as desired. Levels must be between 1-3."""
        assert 1 <= levels <= 3, "levels must be between 1-3"
        btn_layout: QGridLayout = self._btns.layout()
        for btn in self._btns.findChildren(QPushButton):
            btn.show()
        if levels < 3:
            # hide row/col 0, 6
            for r, c in product(range(7), (0, 6)):
                if item := btn_layout.itemAtPosition(r, c):
                    item.widget().hide()
                if item := btn_layout.itemAtPosition(c, r):
                    item.widget().hide()
        if levels < 2:
            # hide row/col 1, 5
            for r, c in product(range(1, 6), (1, 5)):
                if item := btn_layout.itemAtPosition(r, c):
                    item.widget().hide()
                if item := btn_layout.itemAtPosition(c, r):
                    item.widget().hide()

    def _on_click(self):
        btn: QPushButton = self.sender()
        xmag, ymag = self.BTNS[f"{PREFIX}.{btn.text()}"][-2:]
        self._move_stage(self._scale(xmag), self._scale(ymag))

    def _move_stage(self, x, y):
        if self._dtype is DeviceType.XYStage:
            self._mmc.setRelativeXYPosition(self._device, x, y)
        elif self._is_autofocus:
            self._move_offset(y)
        else:
            self._mmc.setRelativePosition(self._device, y)
        if self.snap_checkbox.isChecked():
            self._mmc.snap()

    def _move_offset(self, y):
        if self._mmc.isContinuousFocusLocked():
            offset_dev = self._device.offset_device
            current_offset = self._device.get_position(offset_dev)
            new_offset = current_offset + float(y)
            self._device.set_offset(offset_dev, new_offset)

    def _scale(self, mag: int):
        """
        Convert step mag of (1, 2, 3) to absolute XY units.
        Can be used to step 1x field of view, etc...
        """
        return mag * self._step.value()

    def _disconnect(self):
        self._mmc.events.propertyChanged.disconnect(self._on_prop_changed)
        self._mmc.events.systemConfigurationLoaded.disconnect(self._os_system_cfg)
        if self._dtype is DeviceType.XYStage:
            event = self._mmc.events.XYStagePositionChanged
        if self._dtype is DeviceType.Stage:
            event = self._mmc.events.stagePositionChanged
        event.disconnect(self._update_position_label)
