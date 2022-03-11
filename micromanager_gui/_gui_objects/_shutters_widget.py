from __future__ import annotations

from typing import Optional

from pymmcore_plus import CMMCorePlus, DeviceType
from qtpy import QtWidgets as QtW

from .._core import get_core_singleton


class MMShuttersWidget(QtW.QWidget):
    """A Widget to control shutters."""

    def __init__(
        self,
        mmcore: Optional[CMMCorePlus] = None,
    ):
        super().__init__()
        self._mmc = mmcore or get_core_singleton()
        self.setup_gui()

        self.shutter_list = []

        sig = self._mmc.events
        sig.systemConfigurationLoaded.connect(self._on_system_cfg_loaded)
        sig.configSet.connect(self._on_channel_changed)
        sig.propertyChanged.connect(self._on_property_changed)
        sig.systemConfigurationLoaded.connect(self._refresh_shutter_device)

        self.shutter_btn.clicked.connect(self._on_shutter_btn_clicked)

        self.shutter_checkbox.toggled.connect(self._on_shutter_checkbox_toggled)

    def setup_gui(self):

        self.main_layout = QtW.QHBoxLayout()
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.shutter_label = QtW.QLabel(text="Shutters:")
        self.shutter_label.setMaximumWidth(80)
        self.shutter_label.setMinimumWidth(80)
        self.main_layout.addWidget(self.shutter_label)

        self.shutter_comboBox = QtW.QComboBox()
        self.shutter_comboBox.setMinimumWidth(150)
        self.main_layout.addWidget(self.shutter_comboBox)

        self.shutter_checkbox = QtW.QCheckBox(text="Auto")
        self.main_layout.addWidget(self.shutter_checkbox)

        self.shutter_btn = QtW.QPushButton(text="Closed")
        self.shutter_btn.setStyleSheet("background-color: magenta;")
        self.shutter_btn.setMinimumWidth(70)
        self.shutter_btn.setMaximumWidth(70)
        self.main_layout.addWidget(self.shutter_btn)

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
        self.shutter_btn.setText("Opened")
        self.shutter_btn.setStyleSheet("background-color: green;")

    def _set_shutter_wdg_to_closed(self):
        self.shutter_btn.setText("Closed")
        self.shutter_btn.setStyleSheet("background-color: magenta;")

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
        self.shutter_btn.setText("Closed")
        self.shutter_btn.setStyleSheet("background-color: magenta;")

    def _open_shutter_on_btn_pressed(self):
        current_sht = self.shutter_comboBox.currentText()
        self._mmc.setShutterOpen(current_sht, True)
        self.shutter_btn.setText("Opened")
        self.shutter_btn.setStyleSheet("background-color: green;")

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


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMShuttersWidget()
    win.show()
    sys.exit(app.exec_())
