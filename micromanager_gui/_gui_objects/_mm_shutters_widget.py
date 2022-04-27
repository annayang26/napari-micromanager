from typing import Optional

from pymmcore_plus import CMMCorePlus, DeviceType
from qtpy import QtWidgets as QtW

from .._core import get_core_singleton
from .._core_widgets._shutter_widget import ShuttersWidget


class MMShuttersWidget(QtW.QWidget):
    def __init__(self, mmcore: Optional[CMMCorePlus] = None):
        super().__init__()

        self.setLayout(QtW.QHBoxLayout())
        self.layout().setSpacing(3)
        self.layout().setContentsMargins(0, 0, 0, 0)
        sizepolicy_btn = QtW.QSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Fixed)
        self.setSizePolicy(sizepolicy_btn)

        self._mmc = mmcore or get_core_singleton()
        self._on_cfg_loaded()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_cfg_loaded)

    def _on_cfg_loaded(self):

        self._clear()

        if not self._mmc.getLoadedDevicesOfType(DeviceType.ShutterDevice):
            empty_shutter = ShuttersWidget(
                "", icon_color_open_closed=("black", "magenta")
            )
            self.layout().addWidget(empty_shutter)
            return

        len_shutter_devices = len(
            self._mmc.getLoadedDevicesOfType(DeviceType.ShutterDevice)
        )

        for idx, shutter in enumerate(
            self._mmc.getLoadedDevicesOfType(DeviceType.ShutterDevice)
        ):
            if idx == len_shutter_devices - 1:
                s = ShuttersWidget(
                    shutter,
                    button_text_open_closed=(shutter, shutter),
                    icon_color_open_closed=((0, 255, 0), "magenta"),
                )
            else:
                s = ShuttersWidget(
                    shutter,
                    button_text_open_closed=(shutter, shutter),
                    icon_color_open_closed=((0, 255, 0), "magenta"),
                    autoshutter=False,
                )
            self.layout().addWidget(s)

    def _clear(self):
        for i in reversed(range(self.layout().count())):
            if item := self.layout().takeAt(i):
                if wdg := item.widget():
                    wdg.deleteLater()