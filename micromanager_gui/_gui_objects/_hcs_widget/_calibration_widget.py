from pathlib import Path
from typing import Optional, Tuple

import yaml
from fonticon_mdi6 import MDI6
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import QSize, Qt
from qtpy.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from superqt.fonticon import icon
from sympy import Eq, solve, symbols

from micromanager_gui._core import get_core_singleton

PLATE_DATABASE = Path(__file__).parent / "_well_plate.yaml"


class PlateCalibration(QWidget):
    def __init__(
        self,
        # viewer: napari.viewer.Viewer,
        parent: Optional[QWidget] = None,
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ):
        super().__init__(parent)

        self._mmc = mmcore or get_core_singleton()
        # self.viever = viewer

        # self._mmc.loadSystemConfiguration()  # to remove

        self.plate = None
        self.calibration_well = tuple()
        self.is_calibrated = False

        self._create_gui()

    def _create_gui(self):

        layout = QHBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        group = QGroupBox()
        group_layout = QHBoxLayout()
        group_layout.setSpacing(15)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group.setLayout(group_layout)
        layout.addWidget(group)
        self.table_1 = CalibrationTable()
        group_layout.addWidget(self.table_1)

        bottom_group = QGroupBox()
        bottom_group_layout = QVBoxLayout()
        bottom_group_layout.setSpacing(10)
        bottom_group_layout.setContentsMargins(0, 0, 0, 0)
        bottom_group.setLayout(bottom_group_layout)

        self.info_lbl = QLabel()
        self.info_lbl.setAlignment(Qt.AlignCenter)

        cal_state_wdg = QWidget()
        cal_state_wdg_layout = QHBoxLayout()
        cal_state_wdg_layout.setAlignment(Qt.AlignCenter)
        cal_state_wdg_layout.setSpacing(0)
        cal_state_wdg_layout.setContentsMargins(0, 0, 0, 0)
        cal_state_wdg.setLayout(cal_state_wdg_layout)
        self.icon_lbl = QLabel()
        self.icon_lbl.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.icon_lbl.setPixmap(
            icon(MDI6.close_octagon_outline, color="magenta").pixmap(QSize(30, 30))
        )
        self.cal_lbl = QLabel()
        self.cal_lbl.setText("Plate non Calibrated!")
        cal_state_wdg_layout.addWidget(self.icon_lbl)
        cal_state_wdg_layout.addWidget(self.cal_lbl)

        calibrate_btn = QPushButton(text="Calibrate Plate")
        calibrate_btn.clicked.connect(self._calibrate_plate)

        bottom_group_layout.addWidget(self.info_lbl)
        bottom_group_layout.addWidget(calibrate_btn)
        bottom_group_layout.addWidget(cal_state_wdg)

        layout.addWidget(bottom_group)

    def _load_plate_info(self) -> list:
        with open(
            PLATE_DATABASE,
        ) as file:
            return yaml.safe_load(file)

    def _update_gui(self, plate):

        if self.plate and self.plate.get("id") == plate:
            return

        self._set_calibrated(False)
        self.table_1._clear_table()

        try:
            self.plate = self._load_plate_info()[plate]
        except KeyError:
            self.plate = None
            return

        text = (
            f"Add {3 if self.plate.get('circular') else 4} "
            f"points on the edge of well A1\nand click on 'Calibrate Plate'."
        )
        self.info_lbl.setText(text)

        # to test
        # self.table_1.tb.setRowCount(3)
        # self.table_1.tb.setItem(0, 0, QTableWidgetItem("-100"))
        # self.table_1.tb.setItem(0, 1, QTableWidgetItem("200"))
        # self.table_1.tb.setItem(1, 0, QTableWidgetItem("-200"))
        # self.table_1.tb.setItem(1, 1, QTableWidgetItem("100"))
        # self.table_1.tb.setItem(2, 0, QTableWidgetItem("-100.675"))
        # self.table_1.tb.setItem(2, 1, QTableWidgetItem("-0"))

    def _set_calibrated(self, state: bool):
        if state:
            self.is_calibrated = True
            self.icon_lbl.setPixmap(
                icon(MDI6.check_bold, color=(0, 255, 0)).pixmap(QSize(20, 20))
            )
            self.cal_lbl.setText("Plate Calibrated!")
        else:
            self.is_calibrated = False
            self.calibration_well = tuple()
            self.icon_lbl.setPixmap(
                icon(MDI6.close_octagon_outline, color="magenta").pixmap(QSize(30, 30))
            )
            self.cal_lbl.setText("Plate non Calibrated!")

    def get_center_of_round_well(
        self, a: Tuple[int, int], b: Tuple[int, int], c: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Find the center of a round well given 3 edge points"""
        # eq circle (x - x1)^2 + (y - y1)^2 = r^2
        # for point a: (x - ax)^2 + (y - ay)^2 = r^2
        # for point b: = (x - bx)^2 + (y - by)^2 = r^2
        # for point c: = (x - cx)^2 + (y - cy)^2 = r^2

        x1, y1 = a
        x2, y2 = b
        x3, y3 = c

        x, y = symbols("x y")

        eq1 = Eq((x - x1) ** 2 + (y - y1) ** 2, (x - x2) ** 2 + (y - y2) ** 2)
        eq2 = Eq((x - x1) ** 2 + (y - y1) ** 2, (x - x3) ** 2 + (y - y3) ** 2)

        dict_center = solve((eq1, eq2), (x, y))
        try:
            xc = dict_center[x]
            yc = dict_center[y]
            print(xc, yc)
        except TypeError as e:
            self._set_calibrated(False)
            raise TypeError("Invalid Coordinates!") from e

        return xc, yc

    def get_center_of_squared_well(
        self,
        a: Tuple[float, float],
        b: Tuple[float, float],
        c: Tuple[float, float],
        d: Tuple[float, float],
    ) -> Tuple[float, float]:
        """Find the center of a square well given 4 edge points"""

        x_list = [x[0] for x in [a, b, c, d]]
        y_list = [y[1] for y in [a, b, c, d]]

        x_max, x_min = (max(x_list), min(x_list))
        y_max, y_min = (max(y_list), min(y_list))

        xc = (x_max - x_min) / 2
        yc = (y_max - y_min) / 2

        return xc, yc

    def _calibrate_plate(self):

        self._set_calibrated(False)

        if self._mmc.isSequenceRunning():
            self._mmc.stopSequenceAcquisition()

        if not self.plate:
            return

        if self.table_1.tb.rowCount() < (3 if self.plate.get("circular") else 4):
            raise ValueError("Not enough points for well A1.")

        pos = ()
        for r in range(3 if self.plate.get("circular") else 4):
            x = round(float(self.table_1.tb.item(r, 0).text()))
            y = round(float(self.table_1.tb.item(r, 1).text()))
            pos += ((x, y),)

        if self.plate.get("circular"):
            xc, yc = self.get_center_of_round_well(*pos)
        else:
            xc, yc = self.get_center_of_squared_well(*pos)

        self.calibration_well = tuple()
        self.calibration_well = ("A1", xc, yc)

        self._set_calibrated(True)


class CalibrationTable(QWidget):
    def __init__(self, *, mmcore: Optional[CMMCorePlus] = None):
        super().__init__()

        self._mmc = mmcore or get_core_singleton()

        self._create_wdg()

    def _create_wdg(self):
        layout = QGridLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.well_lbl = QLabel()
        self.well_lbl.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))
        self.well_lbl.setAlignment(Qt.AlignCenter)
        self.well_lbl.setText("Well A1")
        layout.addWidget(self.well_lbl, 0, 0, 1, 2)

        self.tb = QTableWidget()
        self.tb.setMinimumHeight(150)
        hdr = self.tb.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        self.tb.verticalHeader().setVisible(False)
        self.tb.setTabKeyNavigation(True)
        self.tb.setColumnCount(2)
        self.tb.setRowCount(0)
        self.tb.setHorizontalHeaderLabels(["X", "Y"])
        self.tb.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tb.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tb, 1, 0, 3, 1)

        btn_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        min_size = 100
        add_btn = QPushButton(text="Add")
        add_btn.clicked.connect(self._add_pos)
        add_btn.setMinimumWidth(min_size)
        add_btn.setSizePolicy(btn_sizepolicy)
        remove_btn = QPushButton(text="Remove")
        remove_btn.clicked.connect(self._remove_position_row)
        remove_btn.setMinimumWidth(min_size)
        remove_btn.setSizePolicy(btn_sizepolicy)
        clear_btn = QPushButton(text="Clear")
        clear_btn.clicked.connect(self._clear_table)
        clear_btn.setMinimumWidth(min_size)
        clear_btn.setSizePolicy(btn_sizepolicy)
        layout.addWidget(add_btn, 1, 1, 1, 1)
        layout.addWidget(remove_btn, 2, 1, 1, 2)
        layout.addWidget(clear_btn, 3, 1, 1, 2)

    def _add_pos(self):

        if not self._mmc.getXYStageDevice():
            return

        if len(self._mmc.getLoadedDevices()) > 1:
            idx = self._add_position_row()

            for c, ax in enumerate("XY"):
                cur = getattr(self._mmc, f"get{ax}Position")()
                item = QTableWidgetItem(str(cur))
                item.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
                self.tb.setItem(idx, c, item)

    def _add_position_row(self) -> int:
        idx = self.tb.rowCount()
        self.tb.insertRow(idx)
        return idx

    def _remove_position_row(self):
        rows = {r.row() for r in self.tb.selectedIndexes()}
        for idx in sorted(rows, reverse=True):
            self.tb.removeRow(idx)

    def _clear_table(self):
        self.tb.clearContents()
        self.tb.setRowCount(0)

    def get_positions(self):
        pass


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = PlateCalibration()
    win.show()
    sys.exit(app.exec_())
