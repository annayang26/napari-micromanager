from pathlib import Path
from typing import Optional, Tuple

import yaml
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda import PMDAEngine
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QTableWidgetItem, QWidget
from superqt.utils import signals_blocked
from useq import MDASequence

from micromanager_gui._core import get_core_singleton
from micromanager_gui._gui_objects._hcs_widget._graphics_items import FOVPoints, Well
from micromanager_gui._gui_objects._hcs_widget._main_hcs_gui import HCSGui
from micromanager_gui._gui_objects._hcs_widget._update_yaml_widget import UpdateYaml
from micromanager_gui._gui_objects._hcs_widget._well_plate_database import WellPlate
from micromanager_gui._mda import SEQUENCE_META, SequenceMeta

PLATE_DATABASE = Path(__file__).parent / "_well_plate.yaml"
AlignCenter = Qt.AlignmentFlag.AlignCenter


class HCSWidget(HCSGui):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ):
        super().__init__(parent)

        self.wp = None

        # connect
        self._mmc = mmcore or get_core_singleton()
        self._mmc.mda.events.sequenceStarted.connect(self._on_mda_started)
        self._mmc.mda.events.sequenceFinished.connect(self._on_mda_finished)
        self._mmc.mda.events.sequencePauseToggled.connect(self._on_mda_paused)
        self._mmc.events.mdaEngineRegistered.connect(self._update_mda_engine)

        self.wp_combo.currentTextChanged.connect(self._on_combo_changed)
        self.custom_plate.clicked.connect(self._update_plate_yaml)
        self.clear_button.clicked.connect(self.scene._clear_selection)
        self.run_Button.clicked.connect(self._on_run_clicked)
        self.pause_Button.released.connect(lambda: self._mmc.mda.toggle_pause())
        self.cancel_Button.released.connect(lambda: self._mmc.mda.cancel())
        self.calibration.PlateFromCalibration.connect(self._on_plate_from_calibration)
        self.ch_and_pos_list.position_list_button.clicked.connect(
            self._generate_pos_list
        )

        self._update_wp_combo()

    def _update_wp_combo(self):
        plates = self._plates_names_from_database()
        plates.sort()
        self.wp_combo.clear()
        self.wp_combo.addItems(plates)

    def _plates_names_from_database(self) -> list:
        with open(
            PLATE_DATABASE,
        ) as file:
            return list(yaml.safe_load(file))

    def _on_combo_changed(self, value: str):
        self.scene.clear()
        self._draw_well_plate(value)
        self.calibration._update_gui(value)

    def _on_plate_from_calibration(self, coords: Tuple):
        x_list = [x[0] for x in [*coords]]
        y_list = [y[1] for y in [*coords]]
        x_max, x_min = (max(x_list), min(x_list))
        y_max, y_min = (max(y_list), min(y_list))

        width_mm = (abs(x_max) + abs(x_min)) / 1000
        height_mm = (abs(y_max) + abs(y_min)) / 1000

        with open(PLATE_DATABASE) as file:
            f = yaml.safe_load(file)
            f.pop("_from calibration")

        with open(PLATE_DATABASE, "w") as file:
            new = {
                "_from calibration": {
                    "circular": False,
                    "id": "_from calibration",
                    "cols": 1,
                    "rows": 1,
                    "well_size_x": width_mm,
                    "well_size_y": height_mm,
                    "well_spacing_x": 0,
                    "well_spacing_y": 0,
                }
            }
            f.update(new)
            yaml.dump(f, file)

        self.scene.clear()
        self._draw_well_plate("_from calibration")

    def _draw_well_plate(self, well_plate: str):
        self.wp = WellPlate.set_format(well_plate)

        max_w = self._width - 10
        max_h = self._height - 10
        size_y = max_h / self.wp.rows
        size_x = (
            size_y
            if self.wp.circular or self.wp.well_size_x == self.wp.well_size_y
            else (max_w / self.wp.cols)
        )
        text_size = size_y / 2.3

        width = size_x * self.wp.cols

        if width != self.scene.width() and self.scene.width() > 0:
            start_x = (self.scene.width() - width) / 2
            start_x = max(start_x, 0)
        else:
            start_x = 0

        self._create_well_plate(
            self.wp.rows,
            self.wp.cols,
            start_x,
            size_x,
            size_y,
            text_size,
            self.wp.circular,
        )

        self.FOV_selector._load_plate_info(
            self.wp.well_size_x, self.wp.well_size_y, self.wp.circular
        )

    def _create_well_plate(
        self,
        rows: int,
        cols: int,
        start_x: int,
        size_x: int,
        size_y: int,
        text_size: int,
        circular: bool,
    ):
        x = start_x
        y = 0
        for row in range(rows):
            for col in range(cols):
                self.scene.addItem(
                    Well(x, y, size_x, size_y, row, col, text_size, circular)
                )
                x += size_x
            y += size_y
            x = start_x

    def _update_plate_yaml(self):
        self.plate = UpdateYaml(self)
        self.plate.yaml_updated.connect(
            self._update_wp_combo_from_yaml
        )  # UpdateYaml() signal
        self.plate.show()
        self._clear_values()

    def _clear_values(self):
        self.plate._circular_checkbox.setChecked(False),
        self.plate._id.setText("")
        self.plate._cols.setValue(0)
        self.plate._rows.setValue(0)
        self.plate._well_size_x.setValue(0.0)
        self.plate._well_size_y.setValue(0.0)
        self.plate._well_spacing_x.setValue(0.0)
        self.plate._well_spacing_y.setValue(0.0)

    def _update_wp_combo_from_yaml(self, new_plate):
        plates = self._plates_names_from_database()
        plates.sort()
        with signals_blocked(self.wp_combo):
            self.wp_combo.clear()
            self.wp_combo.addItems(plates)
        if new_plate:
            value = list(new_plate.keys())[0]
            self.wp_combo.setCurrentText(value)
            self._on_combo_changed(value)
        else:
            items = [self.wp_combo.itemText(i) for i in range(self.wp_combo.count())]
            self.wp_combo.setCurrentText(items[0])
            self._on_combo_changed(items[0])

    def _generate_pos_list(self):

        if not self.calibration.is_calibrated:
            raise ValueError("Plate not calibrated! Calibrate it first.")

        if not self._mmc.getPixelSizeUm():
            raise ValueError("Pixel Size not defined! Set pixel size first.")

        well_list = self.scene._get_plate_positions()

        if not well_list:
            raise ValueError("No Well selected! Select at least one well first.")

        self.ch_and_pos_list.clear_positions()

        plate_info = self.wp.getAllInfo()

        ordered_wells_list = self._get_wells_stage_coords(well_list, plate_info)

        fovs = [
            item.getPositionsInfo()
            for item in self.FOV_selector.scene.items()
            if isinstance(item, FOVPoints)
        ]

        pos_list = self._get_well_and_fovs_position_list(
            plate_info, ordered_wells_list, fovs
        )

        for r, f in enumerate(pos_list):
            well_name, stage_coord_x, stage_coord_y = f
            self._add_to_table(r, well_name, stage_coord_x, stage_coord_y)

    def _get_wells_stage_coords(self, well_list, plate_info) -> list:
        # center stage coords of calibrated well a1
        a1_x = self.calibration.A1_well[1]
        a1_y = self.calibration.A1_well[2]

        # distance between wells from plate database (mm)
        x_step, y_step = plate_info.get("well_distance")

        well_list_to_order = []
        for pos in well_list:
            well, row, col = pos
            # find center stage coords for all the selected wells
            if well == "A1":
                x = a1_x
                y = a1_y
            else:
                x = a1_x + ((x_step * 1000) * col)
                y = a1_y + ((y_step * 1000) * row)

            well_list_to_order.append((row, well, x, y))

        # reorder wells for "snake" acquisition
        correct_order = []
        to_add = []
        previous_row = well_list_to_order[0][0]
        corrent_row = 0
        for idx, wl in enumerate(well_list_to_order):
            row, well, x, y = wl
            if row > previous_row or idx == len(well_list_to_order) - 1:
                if idx == len(well_list_to_order) - 1:
                    to_add.append((well, x, y))
                if corrent_row % 2 == 0:
                    correct_order.extend(iter(to_add))
                else:
                    correct_order.extend(iter(reversed(to_add)))
                to_add.clear()
                corrent_row += 1

            to_add.append((well, x, y))
            previous_row = row

        return correct_order

    def _get_well_and_fovs_position_list(
        self, plate_info, ordered_wells_list, fovs
    ) -> list:

        # center coord in px (of QGraphicsView))
        cx = 100
        cy = 100

        pos_list = []
        for pos in ordered_wells_list:
            well_name, center_stage_x, center_stage_y = pos

            # well dimensions from database (mm)
            well_x, well_y = plate_info.get("well_size")
            # well dimensions from database (um)
            well_x_um = well_x * 1000
            well_y_um = well_y * 1000

            mode = self.FOV_selector.tab_wdg.tabText(
                self.FOV_selector.tab_wdg.currentIndex()
            )

            fov_list = []
            for idx, fov in enumerate(fovs):
                # center fov scene x, y coord fx and fov scene width and height
                (
                    center_fov_scene_x,
                    center_fov_scene_y,
                    w_fov_scene,
                    h_fov_scene,
                    fov_row,
                    fov_col,
                ) = fov

                # find 1 px value in um depending on well dimension
                px_val_x = well_x_um / w_fov_scene
                px_val_y = well_y_um / h_fov_scene

                # shift point coords in px when center is (0, 0)
                new_fx = center_fov_scene_x - cx
                new_fy = center_fov_scene_y - cy

                # find stage coords of fov point
                stage_coord_x = center_stage_x + (new_fx * px_val_x)
                stage_coord_y = center_stage_y + (new_fy * px_val_y)

                # reorder fovs for "snake" acquisition
                if (mode == "Grid" and not fov_row % 2) or mode != "Grid":
                    fov_list.append((well_name, stage_coord_x, stage_coord_y))
                else:
                    fov_list.insert(
                        -fov_col * idx, (well_name, stage_coord_x, stage_coord_y)
                    )

            pos_list.extend(iter(fov_list))
        return pos_list

    def _add_to_table(self, row, well_name, stage_coord_x, stage_coord_y):
        self._add_position_row()
        name = QTableWidgetItem(f"{well_name}_pos{row:03d}")
        name.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
        self.ch_and_pos_list.stage_tableWidget.setItem(row, 0, name)
        stage_x = QTableWidgetItem(str(stage_coord_x))
        stage_x.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
        self.ch_and_pos_list.stage_tableWidget.setItem(row, 1, stage_x)
        stage_y = QTableWidgetItem(str(stage_coord_y))
        stage_y.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
        self.ch_and_pos_list.stage_tableWidget.setItem(row, 2, stage_y)

        if self.ch_and_pos_list.z_combo.currentText() != "None":
            selected_z_stage = self.ch_and_pos_list.z_combo.currentText()
            z_pos = self._mmc.getPosition(selected_z_stage)
            item = QTableWidgetItem(str(z_pos))
            item.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
            self.ch_and_pos_list.stage_tableWidget.setItem(row, 3, item)

    def _add_position_row(self) -> int:
        idx = self.ch_and_pos_list.stage_tableWidget.rowCount()
        self.ch_and_pos_list.stage_tableWidget.insertRow(idx)
        return idx

    def get_state(self) -> dict:
        ch_table = self.ch_and_pos_list.channel_tableWidget
        state = {
            "axis_order": self.acquisition_order_comboBox.currentText(),
            "channels": [
                {
                    "config": ch_table.cellWidget(c, 0).currentText(),
                    "group": self._mmc.getChannelGroup() or "Channel",
                    "exposure": ch_table.cellWidget(c, 1).value(),
                }
                for c in range(ch_table.rowCount())
            ],
            "time_plan": None,
            "z_plan": None,
            "stage_positions": [],
        }

        if self.ch_and_pos_list.time_group.isChecked():
            unit = {"min": "minutes", "sec": "seconds", "ms": "milliseconds"}[
                self.ch_and_pos_list.time_comboBox.currentText()
            ]
            state["time_plan"] = {
                "interval": {unit: self.ch_and_pos_list.interval_spinBox.value()},
                "loops": self.ch_and_pos_list.timepoints_spinBox.value(),
            }

        if self.ch_and_pos_list.stack_group.isChecked():

            if self.ch_and_pos_list.z_tabWidget.currentIndex() == 0:
                state["z_plan"] = {
                    "range": self.ch_and_pos_list.zrange_spinBox.value(),
                    "step": self.ch_and_pos_list.step_size_doubleSpinBox.value(),
                }
            elif self.ch_and_pos_list.z_tabWidget.currentIndex() == 1:
                state["z_plan"] = {
                    "above": self.ch_and_pos_list.above_doubleSpinBox.value(),
                    "below": self.ch_and_pos_list.below_doubleSpinBox.value(),
                    "step": self.ch_and_pos_list.step_size_doubleSpinBox.value(),
                }

        for r in range(self.ch_and_pos_list.stage_tableWidget.rowCount()):
            pos = {
                "x": float(self.ch_and_pos_list.stage_tableWidget.item(r, 1).text()),
                "y": float(self.ch_and_pos_list.stage_tableWidget.item(r, 2).text()),
            }
            if self.ch_and_pos_list.z_combo.currentText() != "None":
                pos["z"] = float(
                    self.ch_and_pos_list.stage_tableWidget.item(r, 3).text()
                )
            state["stage_positions"].append(pos)

        return MDASequence(**state)

    def _update_mda_engine(self, newEngine: PMDAEngine, oldEngine: PMDAEngine):
        oldEngine.events.sequenceStarted.disconnect(self._on_mda_started)
        oldEngine.events.sequenceFinished.disconnect(self._on_mda_finished)
        oldEngine.events.sequencePauseToggled.disconnect(self._on_mda_paused)

        newEngine.events.sequenceStarted.connect(self._on_mda_started)
        newEngine.events.sequenceFinished.connect(self._on_mda_finished)
        newEngine.events.sequencePauseToggled.connect(self._on_mda_paused)

    def _on_mda_started(self, sequence):
        self.pause_Button.show()
        self.cancel_Button.show()
        self.run_Button.hide()

    def _on_mda_paused(self, paused):
        self.pause_Button.setText("Go" if paused else "Pause")

    def _on_mda_finished(self, sequence):
        self.pause_Button.hide()
        self.cancel_Button.hide()
        self.run_Button.show()

    def _on_run_clicked(self):

        if len(self._mmc.getLoadedDevices()) < 2:
            raise ValueError("Load a cfg file first.")

        if self.ch_and_pos_list.channel_tableWidget.rowCount() <= 0:
            raise ValueError("Select at least one channel.")

        if self.ch_and_pos_list.stage_tableWidget.rowCount() <= 0:
            raise ValueError("Select at least one position.")

        # if self.save_groupBox.isChecked() and not (
        #     self.fname_lineEdit.text() and Path(self.dir_lineEdit.text()).is_dir()
        # ):
        #     raise ValueError("Select a filename and a valid directory.")

        experiment = self.get_state()

        SEQUENCE_META[experiment] = SequenceMeta(
            mode="hca",
            split_channels=False,
            should_save=False,
            file_name="",
            save_dir="",
            save_pos=False,
        )
        self._mmc.run_mda(experiment)  # run the MDA experiment asynchronously
        return


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = HCSWidget()
    win.show()
    sys.exit(app.exec_())
