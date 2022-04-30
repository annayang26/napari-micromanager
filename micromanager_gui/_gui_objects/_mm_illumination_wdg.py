import re
from typing import Optional

from pymmcore_plus import CMMCorePlus, PropertyType
from qtpy.QtWidgets import QApplication, QGridLayout, QLabel, QWidget

from .._core import get_core_singleton, iter_dev_props
from .._core_widgets._property_widget import PropertyWidget


class MMIlluminationWidget(QWidget):
    def __init__(
        self,
        property_regex: str = "(Intensity|Power|test)s?",
        parent: Optional[QWidget] = None,
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ):
        super().__init__(parent)

        self.setLayout(QGridLayout())

        self.ptrn = re.compile(property_regex, re.IGNORECASE)
        self._mmc = mmcore or get_core_singleton()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_cfg_loaded)

        self.destroyed.connect(self._disconnect)

        self._on_cfg_loaded()

    def _create_wdg(self):

        lights = [
            dp
            for dp in iter_dev_props(self._mmc)
            if self.ptrn.search(dp[1])
            and self._mmc.hasPropertyLimits(*dp)
            and self._mmc.getPropertyType(*dp)
            in {PropertyType.Integer, PropertyType.Float}
        ]
        for i, (dev, prop) in enumerate(lights):
            self.layout().addWidget(QLabel(f"{dev}::{prop}"), i, 0)
            self.layout().addWidget(PropertyWidget(dev, prop, core=self._mmc), i, 1)

    def _on_cfg_loaded(self):
        self._clear()
        self._create_wdg()

    def _clear(self):
        for i in reversed(range(self.layout().count())):
            if item := self.layout().takeAt(i):
                if wdg := item.widget():
                    wdg.deleteLater()

    def _disconnect(self):
        self._mmc.events.systemConfigurationLoaded.disconnect(self._on_cfg_loaded)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = MMIlluminationWidget()
    win.show()
    sys.exit(app.exec_())
