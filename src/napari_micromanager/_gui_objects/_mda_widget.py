from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from pymmcore_widgets.mda import MDAWidget
from pymmcore_widgets.mda._core_mda import CRITICAL_MSG, POWER_EXCEEDED_MSG
from pymmcore_widgets.useq_widgets._mda_sequence import PYMMCW_METADATA_KEY
from qtpy.QtWidgets import (
    QCheckBox,
    QVBoxLayout,
    QWidget,
)

from napari_micromanager._util import NMM_METADATA_KEY
from napari_micromanager._writers._ome_tif import OMETifWriter
from napari_micromanager._writers._tif_sequence_writer import TifSequenceWriter

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from useq import MDASequence


class MultiDWidget(MDAWidget):
    """Main napari-micromanager GUI."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        # add split channel checkbox
        self.checkBox_split_channels = QCheckBox(text="Split channels in viewer")
        super().__init__(parent=parent, mmcore=mmcore)

        # setContentsMargins
        pos_layout = cast("QVBoxLayout", self.stage_positions.layout())
        pos_layout.setContentsMargins(10, 10, 10, 10)
        time_layout = cast("QVBoxLayout", self.time_plan.layout())
        time_layout.setContentsMargins(10, 10, 10, 10)
        ch_layout = cast("QVBoxLayout", self.channels.layout())
        ch_layout.setContentsMargins(10, 10, 10, 10)
        ch_layout.addWidget(self.checkBox_split_channels)

    def value(self) -> MDASequence:
        """Return the current value of the widget."""
        # Overriding the value method to add the metadata necessary for the handler.
        sequence = super().value()
        split = self.checkBox_split_channels.isChecked() and len(sequence.channels) > 1
        sequence.metadata[NMM_METADATA_KEY] = {
            "split_channels": split,
        }
        return sequence  # type: ignore[no-any-return]

    def setValue(self, value: MDASequence) -> None:
        """Set the current value of the widget."""
        if nmm_meta := value.metadata.get(NMM_METADATA_KEY):
            # set split_channels checkbox
            self.checkBox_split_channels.setChecked(
                nmm_meta.get("split_channels", False)
            )

        super().setValue(value)

    def run_mda(self) -> None:
        """Run the MDA sequence experiment."""
        # in case the user does not press enter after editing the save name.
        self.save_info.save_name.editingFinished.emit()

        # if autofocus has been requested, but the autofocus device is not engaged,
        # and position-specific offsets haven't been set, show a warning
        pos = self.stage_positions
        if (
            self.af_axis.value()
            and not self._mmc.isContinuousFocusLocked()
            and (not self.tab_wdg.isChecked(pos) or not pos.af_per_position.isChecked())
            and not self._confirm_af_intentions()
        ):
            return

        # Arduino checks___________________________________
        # hide the Arduino LED control widget if visible
        self._arduino_led_wdg._arduino_led_control.hide()
        if not self._arduino_led_wdg.isChecked():
            self._set_arduino_props(None, None)
        else:
            # check if power exceeded
            if self._arduino_led_wdg.is_max_power_exceeded():
                self._set_arduino_props(None, None)
                self._show_critical_led_message(POWER_EXCEEDED_MSG)
                return

            # check if the Arduino and the LED pin are available
            arduino = self._arduino_led_wdg.board()
            led = self._arduino_led_wdg.ledPin()
            if arduino is None or led is None or not self._test_arduino_connection(led):
                self._set_arduino_props(None, None)
                self._arduino_led_wdg._arduino_led_control._enable(False)
                self._show_critical_led_message(CRITICAL_MSG)
                return

            # enable the Arduino board and the LED pin in the MDA engine
            self._set_arduino_props(arduino, led)

        sequence = self.value()

        save_path: Path | OMETifWriter | TifSequenceWriter | None = None
        # technically, this is in the metadata as well, but isChecked is more direct
        if self.save_info.isChecked():
            save_path = self._update_save_path_from_metadata(
                sequence, update_metadata=True
            )

            # get save format from metadata
            save_meta = sequence.metadata.get(PYMMCW_METADATA_KEY, {})
            save_format = save_meta.get("format")

            if isinstance(save_path, Path):
                # use internal OME-TIFF writer if selected
                if "ome-tif" in save_format:
                    # if OME-TIFF, save_path should be a directory without extension, so
                    # we need to add the ".ome.tif" to correctly use the OMETifWriter
                    if not save_path.name.endswith(".ome.tif"):
                        save_path = save_path.with_suffix(".ome.tif")
                    save_path = OMETifWriter(save_path)
                # use internal tif sequence writer if selected
                elif "ome" not in save_format:
                    save_path = TifSequenceWriter(save_path)

        # run the MDA experiment asynchronously
        self._mmc.run_mda(sequence, output=save_path)

    def _update_save_path_from_metadata(
        self,
        sequence: MDASequence,
        update_widget: bool = True,
        update_metadata: bool = False,
    ) -> Path | None:
        """Get the next available save path from sequence metadata and update widget.

        Parameters
        ----------
        sequence : MDASequence
            The MDA sequence to get the save path from. (must be in the
            'pymmcore_widgets' key of the metadata)
        update_widget : bool, optional
            Whether to update the save widget with the new path, by default True.
        update_metadata : bool, optional
            Whether to update the Sequence metadata with the new path, by default False.
        """
        if (
            (meta := sequence.metadata.get(PYMMCW_METADATA_KEY, {}))
            and (save_dir := meta.get("save_dir"))
            and (save_name := meta.get("save_name"))
            and (file_format := meta.get("format"))
        ):
            # if OME-TIFF, we remove the suffix so ww will check if the directory exists
            # or not and increase the counter accordingly. This is because in this
            # version of napatari-micromanager, the OMETifWriter will create the
            # directory instead of saving the file directly.
            is_ome_tif = "ome-tif" in file_format
            if is_ome_tif:
                # remove suffix
                save_name = save_name.replace(".ome.tif", "")

            requested = (Path(save_dir) / str(save_name)).expanduser().resolve()
            next_path = self.get_next_available_path(requested)

            if next_path != requested:
                # put back suffix to correctly trigger the save widget update
                if is_ome_tif:
                    next_path = Path(next_path).with_suffix(".ome.tif")
                if update_widget:
                    self.save_info.setValue(next_path)
                    if update_metadata:
                        meta.update(self.save_info.value())
            return Path(next_path)
        return None
