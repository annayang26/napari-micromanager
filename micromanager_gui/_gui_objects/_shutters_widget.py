from __future__ import annotations

from typing import Optional, Tuple, Union

from fonticon_mdi6 import MDI6
from pymmcore_plus import CMMCorePlus, DeviceType
from qtpy import QtWidgets as QtW
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor
from superqt.fonticon import icon
from superqt.utils import signals_blocked

# from .._core import get_core_singleton
# from .._util import set_wdg_color
from micromanager_gui._core import get_core_singleton
from micromanager_gui._util import set_wdg_color

COLOR_TYPE = Union[
    QColor,
    int,
    str,
    Qt.GlobalColor,
    Tuple[int, int, int, int],
    Tuple[int, int, int],
]


class MMShuttersWidget(QtW.QWidget):
    """A Widget to control shutters and micromanager autoshutter.

    Parameters
    ----------
    button_text_on_off: Optional[tuple[str, str]]
       Text of the QPushButton when the shutter is open or closed
    icon_size : Optional[str]
        Size of the QPushButton icon.
    icon_color_open_closed : Optional[COLOR_TYPE]
        Color of the QPushButton icon when the shutter is open or closed.
    text_color_combo:
        Text color of the shutter QComboBox
    """

    def __init__(
        self,
        button_text_open_closed: Optional[tuple[str, str]] = (None, None),
        icon_size: Optional[int] = 25,
        icon_color_open_closed: Optional[tuple[COLOR_TYPE, COLOR_TYPE]] = (
            "black",
            "black",
        ),
        text_color_combo: Optional[COLOR_TYPE] = "black",
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ):
        super().__init__()
        self._mmc = mmcore or get_core_singleton()

        self._mmc.loadSystemConfiguration(
            "/Users/FG/Desktop/test_config_multishutter.cfg"
        )

        self.button_text_open = button_text_open_closed[0]
        self.button_text_closed = button_text_open_closed[1]
        self.icon_size = icon_size
        self.icon_color_open = icon_color_open_closed[0]
        self.icon_color_closed = icon_color_open_closed[1]
        self.text_color_combo = text_color_combo

        self.shutter_list = []

        self._mmc.events.systemConfigurationLoaded.connect(self._on_system_cfg_loaded)
        self._mmc.events.configSet.connect(self._on_channel_changed)
        self._mmc.events.propertyChanged.connect(self._on_property_changed)
        self._mmc.events.systemConfigurationLoaded.connect(self._refresh_shutter_device)
        self.destroyed.connect(self.disconnect)

        self._mmc.events.shutterState.connect(self.shutterState)

        self.setup_gui()

        self._refresh_shutter_device()

    def shutterState(self, b: bool):
        print("shutter state:", b)

    def setup_gui(self):
        self.main_layout = QtW.QHBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.shutter_btn = QtW.QPushButton(text=self.button_text_closed)
        self.shutter_btn.setIcon(
            icon(MDI6.hexagon_slice_6, color=self.icon_color_closed)
        )
        self.shutter_btn.setIconSize(QSize(self.icon_size, self.icon_size))
        self.shutter_btn.clicked.connect(self._on_shutter_btn_clicked)
        self.main_layout.addWidget(self.shutter_btn)

        self.shutter_comboBox = QtW.QComboBox()
        sizepolicy = QtW.QSizePolicy(QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Minimum)
        self.shutter_comboBox.setSizePolicy(sizepolicy)
        self.shutter_comboBox.currentTextChanged.connect(self._on_combo_changed)
        self.shutter_comboBox.textActivated.connect(self._on_combo_changed)
        self.main_layout.addWidget(self.shutter_comboBox)

        self.shutter_checkbox = QtW.QCheckBox(text="Auto")
        self.shutter_checkbox.toggled.connect(self._on_shutter_checkbox_toggled)
        self.main_layout.addWidget(self.shutter_checkbox)

        self.setLayout(self.main_layout)

    def _on_system_cfg_loaded(self):
        self._refresh_shutter_device()

    def _on_shutter_btn_clicked(self):

        if not self._mmc.getShutterDevice():
            set_wdg_color("magenta", self.shutter_comboBox)
            return

        current_sth_state = self._mmc.getShutterOpen(self._mmc.getShutterDevice())

        if current_sth_state:
            self._close_shutter(self._mmc.getShutterDevice())
        else:
            self._open_shutter(self._mmc.getShutterDevice())

    def _on_combo_changed(self, shutter: str):

        # close if any shutter that is open
        current_sth_state = self._mmc.getShutterOpen()
        if current_sth_state and self._mmc.getShutterDevice():
            self._close_shutter(self._mmc.getShutterDevice())

        # set shutter device
        self._mmc.setShutterDevice(shutter)
        set_wdg_color(self.text_color_combo, self.shutter_comboBox)

    def _on_property_changed(self, dev_name: str, prop_name: str, value: str):

        # change combo text if core shutter is changed
        if dev_name == "Core" and prop_name == self._mmc.getShutterDevice():
            self.shutter_comboBox.setCurrentText(self._mmc.getShutterDevice())

        # change icon if shutter state is changed
        if dev_name == self._mmc.getShutterDevice() and prop_name == "State":
            (
                self._set_shutter_wdg_to_opened()
                if value == "1"
                else self._set_shutter_wdg_to_closed()
            )

        # change AutoShutter checkbox state if core AutoShutter is changed
        elif dev_name == "Core" and prop_name == "AutoShutter":
            (
                self.shutter_checkbox.setChecked(True)
                if value == "1"
                else self.shutter_checkbox.setChecked(False)
            )

    def _on_channel_changed(self, channel_group: str, channel_preset: str):
        if channel_group == self._mmc.getChannelGroup():
            self._set_shutter_from_channel(channel_group, channel_preset)

    def _set_shutter_wdg_to_opened(self):
        if self.button_text_open:
            self.shutter_btn.setText(self.button_text_open)
        self.shutter_btn.setIcon(icon(MDI6.hexagon_outline, color=self.icon_color_open))

    def _set_shutter_wdg_to_closed(self):
        if self.button_text_closed:
            self.shutter_btn.setText(self.button_text_closed)
        self.shutter_btn.setIcon(
            icon(MDI6.hexagon_slice_6, color=self.icon_color_closed)
        )

    def _refresh_shutter_device(self):
        self._reset_shutters()
        self.shutter_list = list(
            self._mmc.getLoadedDevicesOfType(DeviceType.ShutterDevice)
        )
        if self.shutter_list:
            with signals_blocked(self.shutter_comboBox):
                self.shutter_comboBox.addItems(self.shutter_list)
            if self._mmc.getShutterDevice():
                self._mmc.setShutterDevice(self._mmc.getShutterDevice())
                set_wdg_color(self.text_color_combo, self.shutter_comboBox)
            else:
                set_wdg_color("magenta", self.shutter_comboBox)
            self._mmc.setShutterOpen(False)
            self.shutter_btn.setEnabled(True)
            self.shutter_checkbox.setEnabled(True)
            self.shutter_checkbox.setChecked(True)
        else:
            self.shutter_btn.setEnabled(False)
            self.shutter_checkbox.setChecked(False)
            self.shutter_checkbox.setEnabled(False)

    def _reset_shutters(self):
        self._mmc.setShutterOpen(False)
        self.shutter_comboBox.clear()
        self.shutter_list.clear()
        self.shutter_checkbox.setChecked(False)
        self._set_shutter_wdg_to_closed()

    def _close_shutter(self, shutter):
        self._set_shutter_wdg_to_closed()
        self._mmc.setShutterOpen(shutter, False)

    def _open_shutter(self, shutter):
        self._set_shutter_wdg_to_opened()
        self._mmc.setShutterOpen(shutter, True)

    def _on_shutter_checkbox_toggled(self, state: bool):
        self._mmc.setAutoShutter(state)

    def _set_shutter_from_channel(self, group, channel):
        shutter_list = [
            (k[0], k[1], k[2])
            for k in self._mmc.getConfigData(group, channel)
            if self._mmc.getDeviceType(k[0]) == DeviceType.ShutterDevice
        ]
        if not shutter_list:
            set_wdg_color("magenta", self.shutter_comboBox)
            return

        if len(shutter_list) > 1:
            self.shutter_comboBox.setCurrentText("Multi Shutter")
        else:
            self.shutter_comboBox.setCurrentText(shutter_list[0])

        set_wdg_color(self.text_color_combo, self.shutter_comboBox)

    def disconnect(self):
        self._mmc.events.systemConfigurationLoaded.disconnect(
            self._on_system_cfg_loaded
        )
        self._mmc.events.configSet.disconnect(self._on_channel_changed)
        self._mmc.events.propertyChanged.disconnect(self._on_property_changed)
        self._mmc.events.systemConfigurationLoaded.disconnect(
            self._refresh_shutter_device
        )


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMShuttersWidget()
    win.show()
    sys.exit(app.exec_())
