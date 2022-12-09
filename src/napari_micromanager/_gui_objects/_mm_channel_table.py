from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, cast

from pymmcore_plus import CMMCorePlus
from pymmcore_widgets._mda import ChannelTable
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QWidget
from superqt.utils import signals_blocked

from ._channel_group_widget import ChannelGroupWidget

if TYPE_CHECKING:
    from typing_extensions import Required, TypedDict

    class ChannelDict(TypedDict, total=False):
        """Channel dictionary."""

        config: Required[str]
        group: str
        exposure: float | None
        z_offset: float
        do_stack: bool
        camera: str | None
        acquire_every: int


class MMChannelTable(ChannelTable):
    """Subclass of pymmcore-widgets ChannelTable."""

    def __init__(
        self,
        title: str = "Channels",
        parent: QWidget | None = None,
        *,
        channel_group: str = "",
        mmcore: CMMCorePlus | None = None,
    ) -> None:
        super().__init__(title, parent, channel_group=channel_group, mmcore=mmcore)

        self._table.setMinimumHeight(175)

        layout = cast(QGridLayout, self.layout())

        # add channelGroup combo
        btns_layout = layout.itemAtPosition(0, 1).widget().layout()
        self.channel_group_combo = ChannelGroupWidget()
        btns_layout.insertWidget(0, self.channel_group_combo)

        # add split channel checkbox
        self.checkBox_split_channels = QCheckBox(text="Split Channels")
        self.checkBox_split_channels.toggled.connect(self._toggle_split_channel)
        self.valueChanged.connect(self._toggle_split_channel)
        layout.addWidget(self.checkBox_split_channels, 1, 0)

        self._mmc.events.channelGroupChanged.connect(self.setChannelGroup)
        self._mmc.events.propertyChanged.connect(self._on_property_changed)
        self._mmc.events.configGroupDeleted.connect(self._on_group_deleted)
        self._mmc.events.configDeleted.connect(self._on_config_deleted)

        self.destroyed.connect(self._disconnect)

    def _on_property_changed(self, device: str, property: str, value: str) -> None:
        if device == "Core" and property == "ChannelGroup":
            self.setChannelGroup(value)

    def _on_group_deleted(self, group: str) -> None:
        """Remove rows that are using channels from the deleted group."""
        row = 0
        for ch in self.value():
            if ch["group"] == group:
                self._table.removeRow(row)
            else:
                row += 1

    def _on_config_deleted(self, group: str, config: str) -> None:
        """Remove deleted config from channel combo if present."""
        for row in range(self._table.rowCount()):
            combo = cast(QComboBox, self._table.cellWidget(row, 0))
            current_channel = combo.currentText()
            items = [combo.itemText(ch) for ch in range(combo.count())]
            if group == combo.whatsThis() and config in items:
                combo.clear()
                combo.addItems(self._mmc.getAvailableConfigs(group))
                if current_channel != config:
                    combo.setCurrentText(current_channel)

    def _toggle_split_channel(self) -> None:
        if not self.value():
            self.checkBox_split_channels.setChecked(False)

    def _create_new_row(
        self,
        channel: str | None = None,
        exposure: float | None = None,
        channel_group: str | None = None,
    ) -> None:
        """Create a new row in the table.

        If 'channel' is not provided, the first unused channel will be used.
        If 'exposure' is not provided, the current exposure will be used (or 100).
        """
        if len(self._mmc.getLoadedDevices()) <= 1:
            warnings.warn("No devices loaded.")
            return

        if not channel_group:
            warnings.warn("First select Micro-Manager 'ChannelGroup'.")
            return

        # channel dropdown
        channel_combo = QComboBox()
        channel_combo.setWhatsThis(channel_group)
        available = self._mmc.getAvailableConfigs(channel_group)
        channel = channel or self._pick_first_unused_channel(available)
        channel_combo.addItems(available)
        channel_combo.setCurrentText(channel)

        # exposure spinbox
        channel_exp_spinbox = QDoubleSpinBox()
        channel_exp_spinbox.setRange(0, 10000)
        channel_exp_spinbox.setValue(exposure or self._mmc.getExposure() or 100)
        channel_exp_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        channel_exp_spinbox.valueChanged.connect(self.valueChanged)

        idx = self._table.rowCount()
        self._table.insertRow(idx)
        self._table.setCellWidget(idx, 0, channel_combo)
        self._table.setCellWidget(idx, 1, channel_exp_spinbox)
        self.valueChanged.emit()

    def value(self) -> list[ChannelDict]:
        """Return the current channels settings.

        Note that output dict will match the Channel from useq schema:
        <https://pymmcore-plus.github.io/useq-schema/schema/axes/#useq.Channel>
        """
        values: list[ChannelDict] = []
        for c in range(self._table.rowCount()):
            name_widget = cast(QComboBox, self._table.cellWidget(c, 0))
            exposure_widget = cast(QDoubleSpinBox, self._table.cellWidget(c, 1))
            if name_widget and exposure_widget:
                values.append(
                    {
                        "config": name_widget.currentText(),
                        "group": name_widget.whatsThis(),
                        "exposure": exposure_widget.value(),
                    }
                )
        return values

    # note: this really ought to be ChannelDict, but it makes typing elsewhere harder
    # TODO: also accept actual useq objects
    def set_state(self, channels: list[dict]) -> None:
        """Set the state of the widget from a useq channel dictionary."""
        self.clear()
        with signals_blocked(self):
            for channel in channels:
                ch = channel.get("config")
                group = channel.get("group")

                if not ch:
                    raise ValueError("Dictionary should contain channel 'config' name.")
                avail_configs = self._mmc.getAvailableConfigs(
                    group or self._mmc.getChannelGroup()
                )
                if ch not in avail_configs:
                    warnings.warn(
                        f"'{ch}' config or its group doesn't exist in the "
                        f"'{group}' ChannelGroup!"
                    )
                    continue

                exposure = channel.get("exposure") or self._mmc.getExposure()
                self._create_new_row(ch, exposure, group)

        self.valueChanged.emit()

    def _disconnect(self) -> None:
        super()._disconnect()
        self._mmc.events.channelGroupChanged.disconnect(self.setChannelGroup)
        self._mmc.events.propertyChanged.disconnect(self._on_property_changed)
        self._mmc.events.configGroupDeleted.disconnect(self._on_group_deleted)
        self._mmc.events.configDeleted.disconnect(self._on_config_deleted)
