from __future__ import annotations

from typing import Optional, Tuple, Union

from fonticon_mdi6 import MDI6
from pymmcore_plus import CMMCorePlus, DeviceType
from qtpy import QtWidgets as QtW
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor
from superqt.fonticon import icon

# from .._core import get_core_singleton
from micromanager_gui._core import get_core_singleton

COLOR_TYPE = Union[
    QColor,
    int,
    str,
    Qt.GlobalColor,
    Tuple[int, int, int, int],
    Tuple[int, int, int],
]


class MMShuttersWidget(QtW.QWidget):
    """A Widget to control shutters."""

    def __init__(
        self,
        mmcore: Optional[CMMCorePlus] = None,
        button_text_on_off: Optional[tuple[str, str]] = (None, None),
        icon_size: Optional[int] = 30,
        icon_color_on_off: Optional[tuple[COLOR_TYPE, COLOR_TYPE]] = ("black", "black"),
    ):
        super().__init__()
        self._mmc = mmcore or get_core_singleton()

        self._mmc.loadSystemConfiguration()

        self.button_text_on = button_text_on_off[0]
        self.button_text_off = button_text_on_off[1]
        self.icon_size = icon_size
        self.icon_color_on = icon_color_on_off[0]
        self.icon_color_off = icon_color_on_off[1]

        self.shutter_list = []

        self._mmc.events.systemConfigurationLoaded.connect(self._on_system_cfg_loaded)
        self._mmc.events.configSet.connect(self._on_channel_changed)
        self._mmc.events.propertyChanged.connect(self._on_property_changed)
        self._mmc.events.systemConfigurationLoaded.connect(self._refresh_shutter_device)
        self.destroyed.connect(self.disconnect)

        self.setup_gui()

        self._refresh_shutter_device()

        self.shutter_btn.clicked.connect(self._on_shutter_btn_clicked)
        self.shutter_checkbox.toggled.connect(self._on_shutter_checkbox_toggled)

    def setup_gui(self):

        self.main_layout = QtW.QHBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.shutter_btn = QtW.QPushButton(text=self.button_text_off)
        self.shutter_btn.setIcon(icon(MDI6.hexagon_slice_6, color=self.icon_color_off))
        self.shutter_btn.setIconSize(QSize(self.icon_size, self.icon_size))
        # self.shutter_btn.setStyleSheet("background-color: magenta;")
        # self.shutter_btn.setMinimumWidth(70)
        # self.shutter_btn.setMaximumWidth(70)
        self.main_layout.addWidget(self.shutter_btn)

        self.shutter_comboBox = QtW.QComboBox()
        # self.shutter_comboBox.setMinimumWidth(150)
        self.main_layout.addWidget(self.shutter_comboBox)

        self.shutter_checkbox = QtW.QCheckBox(text="Auto")
        self.main_layout.addWidget(self.shutter_checkbox)

        self.setLayout(self.main_layout)

    def _on_system_cfg_loaded(self):
        self._refresh_shutter_device()

    def _on_property_changed(self, dev_name: str, prop_name: str, value: str):

        if dev_name == "Core" and prop_name == self._mmc.getShutterDevice():
            self.shutter_comboBox.setCurrentText(self._mmc.getShutterDevice())

        if dev_name == self._mmc.getShutterDevice() and prop_name == "State":
            (
                self._set_shutter_wdg_to_opened()
                if value == "1"
                else self._set_shutter_wdg_to_closed()
            )

        elif dev_name == "Core" and prop_name == "AutoShutter":
            (
                self.shutter_checkbox.setChecked(True)
                if value == "1"
                else self.shutter_checkbox.setChecked(False)
            )

    def _set_shutter_wdg_to_opened(self):
        self.shutter_btn.setText(self.button_text_on)
        self.shutter_btn.setIcon(icon(MDI6.hexagon_outline, color=self.icon_color_on))
        self.shutter_btn.setIconSize(QSize(self.icon_size, self.icon_size))
        # self.shutter_btn.setStyleSheet("background-color: green;")

    def _set_shutter_wdg_to_closed(self):
        self.shutter_btn.setText(self.button_text_off)
        self.shutter_btn.setIcon(icon(MDI6.hexagon_slice_6, color=self.icon_color_off))
        self.shutter_btn.setIconSize(QSize(self.icon_size, self.icon_size))
        # self.shutter_btn.setStyleSheet("background-color: magenta;")

    def _on_channel_changed(self, channel_group: str, channel_preset: str):
        if channel_group == self._mmc.getChannelGroup():
            self._get_shutter_from_channel(channel_group, channel_preset)

    def _refresh_shutter_device(self):
        self.shutter_comboBox.clear()
        self.shutter_list.clear()
        self.shutter_checkbox.setChecked(False)
        for d in self._mmc.getLoadedDevices():
            if self._mmc.getDeviceType(d) == DeviceType.ShutterDevice:
                self.shutter_list.append(d)
        if self.shutter_list:
            self.shutter_comboBox.addItems(self.shutter_list)
            self._mmc.setShutterOpen(False)
            self.shutter_btn.setEnabled(True)
            self.shutter_checkbox.setChecked(True)
        else:
            self.shutter_btn.setEnabled(False)
            self.shutter_checkbox.setChecked(False)
            self.shutter_checkbox.setEnabled(False)

    def _on_shutter_btn_clicked(self):
        sht = self.shutter_comboBox.currentText()
        current_sth_state = self._mmc.getShutterOpen(sht)

        if current_sth_state:
            self._close_shutter_on_btn_pressed()
        else:
            self._open_shutter_on_btn_pressed()

    def _close_shutter_on_btn_pressed(self):
        current_sht = self.shutter_comboBox.currentText()
        self._mmc.setShutterOpen(current_sht, False)
        self.shutter_btn.setText(self.button_text_off)
        self.shutter_btn.setIcon(icon(MDI6.hexagon_slice_6, color=self.icon_color_off))
        self.shutter_btn.setIconSize(QSize(self.icon_size, self.icon_size))
        # self.shutter_btn.setStyleSheet("background-color: magenta;")

    def _open_shutter_on_btn_pressed(self):
        current_sht = self.shutter_comboBox.currentText()
        self._mmc.setShutterOpen(current_sht, True)
        self.shutter_btn.setText(self.button_text_on)
        self.shutter_btn.setIcon(icon(MDI6.hexagon_outline, color=self.icon_color_on))
        self.shutter_btn.setIconSize(QSize(self.icon_size, self.icon_size))
        # self.shutter_btn.setStyleSheet("background-color: green;")

    def _on_shutter_checkbox_toggled(self, state: bool):
        self._mmc.setAutoShutter(state)

    def _get_shutter_from_channel(self, group, channel):
        shutter_list = [
            (k[0], k[1], k[2])
            for k in self._mmc.getConfigData(group, channel)
            if self._mmc.getDeviceType(k[0]) == DeviceType.ShutterDevice
        ]

        if not shutter_list:
            return

        if len(shutter_list) > 1:
            self.shutter_comboBox.setCurrentText("Multi Shutter")
        else:
            self.shutter_comboBox.setCurrentText(shutter_list[0])

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
