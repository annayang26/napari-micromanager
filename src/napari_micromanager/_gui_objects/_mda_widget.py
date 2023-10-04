from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from pymmcore_plus.mda import mda_listeners_connected  # type: ignore
from pymmcore_plus.mda.handlers import ImageSequenceWriter
from pymmcore_widgets.mda import MDAWidget
from qtpy.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from useq import MDASequence

from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus


TIFF_WRITER = 0
OME_TIFF_WRITER = 1
ZARR_WRITER = 2


class MultiDWidget(MDAWidget):
    """Main napari-micromanager GUI."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(parent=parent, mmcore=mmcore)

        # setContentsMargins
        pos_layout = cast("QVBoxLayout", self.stage_positions.layout())
        pos_layout.setContentsMargins(10, 10, 10, 10)
        time_layout = cast("QVBoxLayout", self.time_plan.layout())
        time_layout.setContentsMargins(10, 10, 10, 10)
        ch_layout = cast("QVBoxLayout", self.channels.layout())
        ch_layout.setContentsMargins(10, 10, 10, 10)

        # add split channel checkbox
        self.checkBox_split_channels = QCheckBox(text="Split Channels")
        ch_layout.addWidget(self.checkBox_split_channels)

        # add writers
        writers_wdg = QWidget()
        writers_layout = QHBoxLayout(writers_wdg)
        writers_layout.setContentsMargins(0, 10, 0, 0)
        writers_layout.setSpacing(10)

        lbl = QLabel("Save as:")
        lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        writers_layout.addWidget(lbl)

        self._tiff_sequence_radio = QRadioButton("TIFF")
        self._tiff_sequence_radio.setChecked(True)
        self._ome_tiff_radio = QRadioButton("OME-TIFF")
        self._zarr_radio = QRadioButton("ZARR")
        writers_layout.addWidget(self._tiff_sequence_radio)
        writers_layout.addWidget(self._ome_tiff_radio)
        writers_layout.addWidget(self._zarr_radio)
        writers_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        )

        self._writers_btn_group = QButtonGroup()
        self._writers_btn_group.addButton(self._tiff_sequence_radio, TIFF_WRITER)
        self._writers_btn_group.addButton(self._ome_tiff_radio, OME_TIFF_WRITER)
        self._writers_btn_group.addButton(self._zarr_radio, ZARR_WRITER)

        save_layout = cast("QGridLayout", self.save_info.layout())
        save_layout.addWidget(writers_wdg, 2, 0, 1, 2)

    def value(self) -> MDASequence:
        """Return the current value of the widget."""
        # Overriding the value method to add the metadata necessary for the handler.
        sequence = cast(MDASequence, super().value())

        # this is to avoid the AttributeError the first time the MDAWidget is called
        try:
            split_channels = bool(
                self.checkBox_split_channels.isChecked() and len(sequence.channels) > 1
            )
        except AttributeError:
            split_channels = False

        save_info = self.save_info.value()
        sequence.metadata[SEQUENCE_META_KEY] = SequenceMeta(
            mode="mda",
            split_channels=split_channels,
            save_dir=save_info.get("save_dir", ""),
            file_name=save_info.get("save_name", ""),
        )
        return sequence

    def setValue(self, value: MDASequence) -> None:
        """Set the current value of the widget."""
        meta = value.metadata.get(SEQUENCE_META_KEY)
        if meta and not isinstance(meta, SequenceMeta):
            raise TypeError(f"Expected {SequenceMeta}, got {type(meta)}")
        super().setValue(value)

    def _on_run_clicked(self) -> None:
        sequence = self.value()
        if not self.save_info.isChecked():
            self._mmc.run_mda(sequence)
        else:
            meta = cast(SequenceMeta, sequence.metadata[SEQUENCE_META_KEY])

            if not meta.save_dir:
                self._mmc.run_mda(sequence)
                return

            # TODO: update prefix with number (e.g. _000, _001)
            directory = Path(meta.save_dir) / meta.file_name

            btn_idx = self._writers_btn_group.checkedId()
            if btn_idx == TIFF_WRITER:
                writer = ImageSequenceWriter(
                    prefix=meta.file_name, directory=directory, overwrite=True
                )
            elif btn_idx in [OME_TIFF_WRITER, ZARR_WRITER]:
                raise NotImplementedError()

            with mda_listeners_connected(writer):
                self._mmc.run_mda(sequence)
