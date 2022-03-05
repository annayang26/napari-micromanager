from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QVBoxLayout

from .. import _core
from .._core_widgets._presets_widget import PresetsWidget
from .._core_widgets._property_widget import PropertyWidget


class MainTable(QtW.QTableWidget):
    def __init__(self) -> None:
        super().__init__()
        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        hdr.setDefaultAlignment(Qt.AlignHCenter)
        vh = self.verticalHeader()
        vh.setVisible(False)
        vh.setSectionResizeMode(vh.Fixed)
        vh.setDefaultSectionSize(24)
        self.setEditTriggers(QtW.QTableWidget.NoEditTriggers)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["Group", "Preset"])


class MMGroupPresetTableWidget(QtW.QWidget):
    def __init__(self):
        super().__init__()

        self._mmc = _core.get_core_singleton()
        self._mmc.events.systemConfigurationLoaded.connect(self._populate_table)
        self.table_wdg = MainTable()
        self.table_wdg.show()
        self.setLayout(QVBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.table_wdg)

    def _on_system_cfg_loaded(self):
        self._populate_table()

    def _reset_table(self):
        self.table_wdg.clearContents()
        self.table_wdg.setRowCount(0)
        self.table_wdg.setHorizontalHeaderLabels(["Group", "Preset"])

    def _populate_table(self):
        self._reset_table()
        if groups := self._mmc.getAvailableConfigGroups():
            for row, group in enumerate(groups):
                self.table_wdg.insertRow(row)
                self.table_wdg.setItem(row, 0, QtW.QTableWidgetItem(str(group)))
                self.table_wdg.setCellWidget(row, 1, self.create_group_widget(group))

    def _get_cfg_data(self, group: str, preset: str):
        """
        Return last device-property-value for the preset and the
        total number of device-property-value included in the preset.
        """

        for dev_prop_val_count, key in enumerate(
            self._mmc.getConfigData(group, preset)
        ):
            dev = key[0]
            prop = key[1]
            val = key[2]
        return dev, prop, val, (dev_prop_val_count + 1)

    def create_group_widget(self, group: str):
        """Return a widget depending on presets and device-property"""

        # get group presets
        presets = list(self._mmc.getAvailableConfigs(group))

        if not presets:
            return

        # use only the first preset since device
        # and property are the same for the presets
        device, property, _, dev_prop_val_count = self._get_cfg_data(group, presets[0])

        if len(presets) > 1 or dev_prop_val_count > 1:
            return PresetsWidget(group)
        else:
            return PropertyWidget(device, property)