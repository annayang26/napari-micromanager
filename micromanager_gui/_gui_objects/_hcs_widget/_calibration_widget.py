from pathlib import Path
from typing import Optional, Tuple, overload

import yaml
from fonticon_mdi6 import MDI6
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import QSize, Qt, Signal
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

    PlateFromCalibration = Signal(tuple)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ):
        super().__init__(parent)

        self._mmc = mmcore or get_core_singleton()

        self.plate = None
        self.A1_well = tuple()
        self.is_calibrated = False

        self._create_gui()

    def _create_gui(self):

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.info_lbl = QLabel()
        self.info_lbl.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(self.info_lbl)

        group = QGroupBox()
        group_layout = QHBoxLayout()
        group_layout.setSpacing(15)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group.setLayout(group_layout)
        layout.addWidget(group)
        self.table_1 = CalibrationTable()
        group_layout.addWidget(self.table_1)

        bottom_group = QGroupBox()
        bottom_group_layout = QHBoxLayout()
        bottom_group_layout.setSpacing(10)
        bottom_group_layout.setContentsMargins(10, 10, 10, 10)
        bottom_group.setLayout(bottom_group_layout)

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

        # bottom_group_layout.addWidget(self.info_lbl)
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

        if self.plate.get("circular"):
            text = (
                "Add 3 points on the circonference of the round well"
                "and click on 'Calibrate Plate'."
            )
        else:
            text = (
                "Add 2 points (opposite vertices) "
                "or 4 points (1 point per side) "
                "and click on 'Calibrate Plate'."
            )
        self.info_lbl.setText(text)

        # to test
        # self.table_1.tb.setRowCount(2)
        # self.table_1.tb.setItem(0, 0, QTableWidgetItem("-100"))
        # self.table_1.tb.setItem(0, 1, QTableWidgetItem("100"))
        # self.table_1.tb.setItem(1, 0, QTableWidgetItem("100"))
        # self.table_1.tb.setItem(1, 1, QTableWidgetItem("-100"))

    def _set_calibrated(self, state: bool):
        if state:
            self.is_calibrated = True
            self.icon_lbl.setPixmap(
                icon(MDI6.check_bold, color=(0, 255, 0)).pixmap(QSize(20, 20))
            )
            self.cal_lbl.setText("Plate Calibrated!")
        else:
            self.is_calibrated = False
            self.A1_well = tuple()
            self.icon_lbl.setPixmap(
                icon(MDI6.close_octagon_outline, color="magenta").pixmap(QSize(30, 30))
            )
            self.cal_lbl.setText("Plate non Calibrated!")

    def get_circle_center_(
        self, a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]
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

        eq1 = Eq(
            (x - round(x1)) ** 2 + (y - round(y1)) ** 2,
            (x - round(x2)) ** 2 + (y - round(y2)) ** 2,
        )
        eq2 = Eq(
            (x - round(x1)) ** 2 + (y - round(y1)) ** 2,
            (x - round(x3)) ** 2 + (y - round(y3)) ** 2,
        )

        dict_center = solve((eq1, eq2), (x, y))
        try:
            xc = dict_center[x]
            yc = dict_center[y]
        except TypeError as e:
            self._set_calibrated(False)
            raise TypeError("Invalid Coordinates!") from e

        return xc, yc

    @overload
    def get_rect_center(self, a: Tuple, b: Tuple, c: Tuple, d: Tuple) -> Tuple:
        ...

    @overload
    def get_rect_center(self, a: Tuple, b: Tuple) -> Tuple:
        ...

    def get_rect_center(self, *args) -> Tuple:
        """
        Find the center of a rectanle/square well given
        two opposite verices coordinates or 4 points on the edges.
        """

        # add block if wrong coords!!!

        x_list = [x[0] for x in [*args]]
        y_list = [y[1] for y in [*args]]
        x_max, x_min = (max(x_list), min(x_list))
        y_max, y_min = (max(y_list), min(y_list))

        if x_max == x_min or y_max == y_min:
            raise ValueError("Invalid Coordinates!")

        x_val = abs(x_min) if x_min < 0 else 0
        y_val = abs(y_min) if y_min < 0 else 0

        x1, y1 = (x_min + x_val, y_max + y_val)
        x2, y2 = (x_max + x_val, y_min + y_val)

        x_max_, x_min_ = (max(x1, x2), min(x1, x2))
        y_max_, y_min_ = (max(y1, y2), min(y1, y2))

        xc = ((x_max_ - x_min_) / 2) - x_val
        yc = ((y_max_ - y_min_) / 2) - y_val

        if x_min > 0:
            xc += x_min
        if y_min > 0:
            yc += y_min

        return xc, yc

    def _calibrate_plate(self):

        self._set_calibrated(False)

        if self._mmc.isSequenceRunning():
            self._mmc.stopSequenceAcquisition()

        if not self.plate:
            return

        if self.plate.get("circular"):
            if self.table_1.tb.rowCount() < 3:
                raise ValueError("Not enough points for well A1.")
        elif self.table_1.tb.rowCount() < 2 or self.table_1.tb.rowCount() == 3:
            raise ValueError("Not enough points for well A1.")

        pos = ()
        if self.plate.get("circular"):
            _range = 3
        elif self.table_1.tb.rowCount() == 2:
            _range = 2
        elif self.table_1.tb.rowCount() >= 4:
            _range = 4

        for r in range(_range):
            x = float(self.table_1.tb.item(r, 0).text())
            y = float(self.table_1.tb.item(r, 1).text())
            pos += ((x, y),)

        if self.plate.get("circular"):
            xc, yc = self.get_circle_center_(*pos)
        else:
            xc, yc = self.get_rect_center(*pos)

        self.A1_well = tuple()
        self.A1_well = ("A1", xc, yc)

        self._set_calibrated(True)

        if self.plate.get("id") == "_from calibration":
            self.PlateFromCalibration.emit(pos)


class CalibrationTable(QWidget):
    def __init__(self, *, mmcore: Optional[CMMCorePlus] = None):
        super().__init__()

        self._mmc = mmcore or get_core_singleton()

        self._create_wdg()

    def _create_wdg(self):
        layout = QGridLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 0, 0, 0)
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
