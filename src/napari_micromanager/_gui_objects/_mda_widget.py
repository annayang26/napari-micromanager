from __future__ import annotations

import warnings
from pathlib import Path
from typing import cast

from pymmcore_mda_writers import MiltiTiffWriter, ZarrWriter
from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import MDAWidget
from qtpy.QtWidgets import QCheckBox, QGridLayout, QSizePolicy, QVBoxLayout, QWidget
from useq import MDASequence

from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta

from ._save_widget import SaveWidget


class MultiDWidget(MDAWidget):
    """Main napari-micromanager GUI."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(include_run_button=True, parent=parent, mmcore=mmcore)

        self._tiff_writer = MiltiTiffWriter(core=self._mmc)
        self._zarr_writer = ZarrWriter(core=self._mmc)

        v_layout = cast(QVBoxLayout, self._central_widget.layout())
        self._save_groupbox = SaveWidget()
        self._save_groupbox.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self._save_groupbox.setChecked(False)
        v_layout.insertWidget(0, self._save_groupbox)

        self.channel_groupbox.setMinimumHeight(230)
        self.checkBox_split_channels = QCheckBox(text="Split Channels")
        self.checkBox_split_channels.toggled.connect(self._toggle_split_channel)
        g_layout = cast(QGridLayout, self.channel_groupbox.layout())
        g_layout.addWidget(self.checkBox_split_channels, 1, 0)

        self._save_groupbox.toggled.connect(self._on_save_toggled)
        self._save_groupbox._directory.textChanged.connect(
            lambda x: self._on_save_toggled(True)
        )
        self._save_groupbox._fname.textChanged.connect(
            lambda x: self._on_save_toggled(True)
        )
        self._save_groupbox.zarr_radiobutton.toggled.connect(
            lambda x: self._on_save_toggled(True)
        )
        self._save_groupbox.tiff_radiobutton.toggled.connect(
            lambda x: self._on_save_toggled(True)
        )

        self.channel_groupbox.valueChanged.connect(self._toggle_split_channel)

    def _toggle_split_channel(self) -> None:
        if (
            not self.channel_groupbox.value()
            or self.channel_groupbox._table.rowCount() == 1
        ):
            self.checkBox_split_channels.setChecked(False)

    def _on_save_toggled(self, checked: bool) -> None:
        self._tiff_writer.folder_path = (
            self._save_groupbox._directory.text()
            if (checked and self._save_groupbox.tiff_radiobutton.isChecked())
            else None
        )
        self._tiff_writer.file_name = (
            self._save_groupbox._fname.text() if checked else ""
        )

        self._zarr_writer.folder_path = (
            self._save_groupbox._directory.text()
            if (checked and self._save_groupbox.zarr_radiobutton.isChecked())
            else None
        )
        self._zarr_writer.file_name = (
            self._save_groupbox._fname.text() if checked else ""
        )

    def get_state(self) -> MDASequence:
        sequence = cast(MDASequence, super().get_state())

        try:
            _split_channels = self.checkBox_split_channels.isChecked()
            _save_info = self._save_groupbox.get_state()
        except AttributeError:
            _split_channels = False
            _save_info = {
                "file_name": "",
                "save_dir": "",
                "should_save": False,
            }

        sequence.metadata[SEQUENCE_META_KEY] = SequenceMeta(
            mode="mda",
            split_channels=_split_channels,
            **_save_info,
        )
        return sequence

    def set_state(self, state: dict | MDASequence | str | Path) -> None:
        super().set_state(state)
        meta = None
        if isinstance(state, dict):
            meta = state.get("metadata", {}).get(SEQUENCE_META_KEY)
        elif isinstance(state, MDASequence):
            meta = state.metadata.get(SEQUENCE_META_KEY)

        if meta is None:
            return
        if not isinstance(meta, SequenceMeta):
            raise TypeError(f"Expected {SequenceMeta}, got {type(meta)}")
        if meta.mode.lower() != "mda":
            raise ValueError(f"Expected mode 'mda', got {meta.mode}")

        self.checkBox_split_channels.setChecked(meta.split_channels)
        self._save_groupbox.set_state(meta)

    def _on_run_clicked(self) -> None:
        if (
            self._save_groupbox.isChecked()
            and not self._save_groupbox._directory.text()
        ):
            warnings.warn("Select a directory to save the data.")
            return

        if not Path(self._save_groupbox._directory.text()).exists():
            # TODO: ask to create the directory if it does not exist
            warnings.warn("The selected directory does not exist.")
            return

        super()._on_run_clicked()
