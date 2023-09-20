from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING, cast

from pymmcore_mda_writers import MultiTiffWriter
from pymmcore_widgets import MDAWidget
from pymmcore_widgets._hcs_widget._main_wizard_widget import Center, HCSWizard, WellInfo
from pymmcore_widgets._hcs_widget._util import apply_rotation_matrix, get_well_center
from qtpy.QtCore import Signal
from qtpy.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from useq import AxesBasedAF, GridRowsColumns, MDASequence, Position, RandomPoints

from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta

from ._save_widget import SaveWidget

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from pymmcore_widgets import PositionTable


class HCSWidget(HCSWizard):
    valueChanged = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        mmcore: CMMCorePlus | None = None,
        plate_database_path: Path | str | None = None,
        position_table: PositionTable,
    ) -> None:
        super().__init__(parent, mmcore=mmcore, plate_database_path=plate_database_path)

        self._pt = position_table

    def accept(self) -> None:
        """Override QWizard default accept method."""
        well_centers = self._get_well_center_in_stage_coordinates()
        if well_centers is None:
            return
        _positions = self._get_fovs_in_stage_coords(well_centers)

        # update with current z position and z autofocus if `Locked`
        positions = []
        for pos in _positions:
            if self._mmc.getFocusDevice():
                pos = pos.replace(z=self._mmc.getPosition(self._mmc.getFocusDevice()))

            if self._mmc.isContinuousFocusLocked():
                af_z_device = self._pt._get_af_device()
                if af_z_device is not None:
                    pos = pos.replace(
                        sequence=MDASequence(
                            autofocus_plan=AxesBasedAF(
                                axes=("t", "p", "g"),
                                autofocus_device_name=af_z_device,
                                autofocus_motor_offset=self._mmc.getPosition(
                                    af_z_device
                                ),
                            )
                        )
                    )

            positions.append(pos)

        self.valueChanged.emit(positions)

    def _get_well_center_in_stage_coordinates(
        self,
    ) -> list[tuple[WellInfo, float, float]] | None:
        plate, _, calibration, _ = self.value()
        _, wells = self.plate_page.value()

        if wells is None or calibration is None:
            return None

        a1_x, a1_y = (calibration.well_A1_center_x, calibration.well_A1_center_y)
        wells_center_stage_coords = []
        for well in wells:
            x, y = get_well_center(plate, well, a1_x, a1_y)
            if calibration.rotation_matrix is not None:
                x, y = apply_rotation_matrix(
                    calibration.rotation_matrix,
                    calibration.well_A1_center_x,
                    calibration.well_A1_center_y,
                    x,
                    y,
                )
            wells_center_stage_coords.append((well, x, y))

        return wells_center_stage_coords

    def _get_fovs_in_stage_coords(
        self, wells_center: list[tuple[WellInfo, float, float]], _show: bool = True
    ) -> list[Position]:
        """Get the calibrated stage coords of each FOV of the selected wells."""
        _, _, _, mode = self.value()

        positions: list[Position] = []

        for well, well_center_x, well_center_y in wells_center:
            if isinstance(mode, Center):
                positions.append(
                    Position(x=well_center_x, y=well_center_y, name=f"{well.name}")
                )

            elif isinstance(mode, GridRowsColumns):
                positions.append(
                    Position(
                        x=well_center_x,
                        y=well_center_y,
                        name=f"{well.name}",
                        sequence=MDASequence(grid_plan=mode),
                    )
                )

            elif isinstance(mode, RandomPoints):
                for idx, fov in enumerate(mode):
                    x, y = (fov.x * 1000) + well_center_x, (
                        fov.y * 1000
                    ) + well_center_y
                    positions.append(Position(x=x, y=y, name=f"{well.name}_{idx:04d}"))

        return positions


class MultiDWidget(MDAWidget):
    """Main napari-micromanager GUI."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(include_run_button=True, parent=parent, mmcore=mmcore)

        self._tiff_writer = MultiTiffWriter(core=mmcore)

        # add HCS button
        self._hcs_btn = QPushButton(text="HCS")
        self._hcs_btn.clicked.connect(self._on_hcs_clicked)
        self.position_widget.layout().itemAt(1).widget().layout().insertWidget(
            7, self._hcs_btn
        )

        # add save widget
        v_layout = cast(QVBoxLayout, self._central_widget.layout())
        self._save_groupbox = SaveWidget()
        self._save_groupbox.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self._save_groupbox.setChecked(False)
        self._save_groupbox.toggled.connect(self._on_save_toggled)
        self._save_groupbox._directory.textChanged.connect(self._on_save_toggled)
        self._save_groupbox._fname.textChanged.connect(self._on_save_toggled)
        v_layout.insertWidget(0, self._save_groupbox)

        # add split channel checkbox
        self.channel_widget.setMinimumHeight(230)
        self.checkBox_split_channels = QCheckBox(text="Split Channels")
        self.checkBox_split_channels.toggled.connect(self._toggle_split_channel)
        g_layout = cast(QGridLayout, self.channel_widget.layout())
        g_layout.addWidget(self.checkBox_split_channels, 1, 0)
        self.channel_widget.valueChanged.connect(self._toggle_split_channel)

    def _on_hcs_clicked(self) -> None:
        if not hasattr(self, "_hcs"):
            self._hcs = HCSWidget(position_table=self.position_widget)
            self._hcs.valueChanged.connect(lambda x: self.position_widget.set_state(x))
        self._hcs.show()
        self._hcs.raise_()

    def _toggle_split_channel(self) -> None:
        if (
            not self.channel_widget.value()
            or self.channel_widget._table.rowCount() == 1
        ):
            self.checkBox_split_channels.setChecked(False)

    def _on_save_toggled(self) -> None:
        checked = self._save_groupbox.isChecked()

        self._tiff_writer.folder_path = (
            self._save_groupbox._directory.text() if checked else None
        )
        self._tiff_writer.file_name = (
            self._save_groupbox._fname.text() if checked else ""
        )

        self._tiff_writer.enabled = bool(checked and self._tiff_writer.folder_path)

    def get_state(self) -> MDASequence:
        sequence = cast(MDASequence, super().get_state())
        sequence.metadata[SEQUENCE_META_KEY] = SequenceMeta(
            mode="mda",
            split_channels=self.checkBox_split_channels.isChecked(),
            **self._save_groupbox.get_state(),
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
            warnings.warn("Select a directory to save the data.", stacklevel=2)
            return

        if not Path(self._save_groupbox._directory.text()).exists():
            if self._create_new_folder():
                Path(self._save_groupbox._directory.text()).mkdir(parents=True)
            else:
                return

        super()._on_run_clicked()

    def _create_new_folder(self) -> bool:
        """Create a QMessageBox to ask to create directory if it doesn't exist."""
        msgBox = QMessageBox()
        msgBox.setWindowTitle("Create Directory")
        msgBox.setIcon(QMessageBox.Icon.Question)
        msgBox.setText(
            f"Directory {self._save_groupbox._directory.text()} "
            "does not exist. Create it?"
        )
        msgBox.setStandardButtons(
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        return bool(msgBox.exec() == QMessageBox.StandardButton.Ok)
