import math
import random

import numpy as np
from qtpy.QtCore import QRectF, Qt
from qtpy.QtGui import QPen
from qtpy.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QDoubleSpinBox,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from superqt.utils import signals_blocked

AlignCenter = Qt.AlignmentFlag.AlignCenter


class SelectFOV(QWidget):
    def __init__(self):
        super().__init__()

        self._size_x = None
        self._size_y = None
        self._is_circular = None

        self._create_widget()

    def _create_widget(self):
        self.lst = QListWidget()
        self.lst.insertItem(0, "Random")
        self.lst.insertItem(1, "Grid")
        self.lst.insertItem(2, "Center")
        self.lst.setMaximumWidth(self.lst.sizeHintForColumn(0) + 10)
        self.lst.setMaximumHeight(150)
        self.lst.currentRowChanged.connect(self.display)

        self.stack = QStackedWidget()

        self.center_wdg = QWidget()
        self.random_wdg = QWidget()
        self.grid_wdg = QWidget()

        self._set_random_wdg_gui()
        self._set_grid_wdg_gui()
        self._set_center_wdg_gui()

        self.stack.addWidget(self.random_wdg)
        self.stack.addWidget(self.grid_wdg)
        self.stack.addWidget(self.center_wdg)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene, self)
        self.view.setStyleSheet("background:grey;")
        self.view.setFixedSize(200, 150)

        hbox = QHBoxLayout()
        hbox.setSpacing(5)
        hbox.setContentsMargins(10, 0, 10, 0)
        hbox.addWidget(self.lst)
        hbox.addWidget(self.stack)
        hbox.addWidget(self.view)
        self.setLayout(hbox)

    def _set_random_wdg_gui(self):
        layout = QVBoxLayout()
        self.random_wdg.setLayout(layout)

        group_wdg = QGroupBox()
        group_wdg.setMinimumHeight(150)
        group_wdg_layout = QVBoxLayout()
        group_wdg_layout.setSpacing(5)
        group_wdg_layout.setContentsMargins(5, 5, 5, 5)
        group_wdg.setLayout(group_wdg_layout)
        layout.addWidget(group_wdg)

        plate_area_label_x = QLabel()
        plate_area_label_x.setMinimumWidth(120)
        plate_area_label_x.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        plate_area_label_x.setText("Area FOV x (mm):")
        self.plate_area_x = QDoubleSpinBox()
        self.plate_area_x.setAlignment(AlignCenter)
        self.plate_area_x.setMinimum(1)
        self.plate_area_x.valueChanged.connect(self._on_area_x_changed)
        _plate_area_x = self._make_QHBoxLayout_wdg_with_label(
            plate_area_label_x, self.plate_area_x
        )
        group_wdg_layout.addWidget(_plate_area_x)

        plate_area_label_y = QLabel()
        plate_area_label_y.setMinimumWidth(120)
        plate_area_label_y.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        plate_area_label_y.setText("Area FOV y (mm):")
        self.plate_area_y = QDoubleSpinBox()
        self.plate_area_y.setAlignment(AlignCenter)
        self.plate_area_y.setMinimum(1)
        self.plate_area_y.valueChanged.connect(self._on_area_y_changed)
        _plate_area_y = self._make_QHBoxLayout_wdg_with_label(
            plate_area_label_y, self.plate_area_y
        )
        group_wdg_layout.addWidget(_plate_area_y)

        number_of_FOV_label = QLabel()
        number_of_FOV_label.setMinimumWidth(120)
        number_of_FOV_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        number_of_FOV_label.setText("Number of FOV:")
        self.number_of_FOV = QSpinBox()
        self.number_of_FOV.setAlignment(AlignCenter)
        self.number_of_FOV.setMinimum(1)
        self.number_of_FOV.setMaximum(100)
        self.number_of_FOV.valueChanged.connect(self._on_number_of_FOV_changed)
        nFOV = self._make_QHBoxLayout_wdg_with_label(
            number_of_FOV_label, self.number_of_FOV
        )
        group_wdg_layout.addWidget(nFOV)

        self.random_button = QPushButton(text="Generate Random FOV(s)")
        self.random_button.clicked.connect(self._on_random_button_pressed)
        group_wdg_layout.addWidget(self.random_button)

    def _set_grid_wdg_gui(self):
        layout = QVBoxLayout()
        self.grid_wdg.setLayout(layout)

        group_wdg = QGroupBox()
        group_wdg.setMinimumHeight(150)
        group_wdg_layout = QVBoxLayout()
        group_wdg_layout.setSpacing(5)
        group_wdg_layout.setContentsMargins(5, 5, 5, 5)
        group_wdg.setLayout(group_wdg_layout)
        layout.addWidget(group_wdg)

        rows_lbl = QLabel()
        rows_lbl.setMinimumWidth(120)
        rows_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        rows_lbl.setText("Rows:")
        self.rows = QSpinBox()
        self.rows.setAlignment(AlignCenter)
        self.rows.setMinimum(1)
        # self.rows.valueChanged.connect(self._on_row_changed)
        _rows = self._make_QHBoxLayout_wdg_with_label(rows_lbl, self.rows)
        group_wdg_layout.addWidget(_rows)

        cols_lbl = QLabel()
        cols_lbl.setMinimumWidth(120)
        cols_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        cols_lbl.setText("Columns:")
        self.cols = QSpinBox()
        self.cols.setAlignment(AlignCenter)
        self.cols.setMinimum(1)
        # self.cols.valueChanged.connect(self._on_col_changed)
        _cols = self._make_QHBoxLayout_wdg_with_label(cols_lbl, self.cols)
        group_wdg_layout.addWidget(_cols)

        spacing_x_lbl = QLabel()
        spacing_x_lbl.setMinimumWidth(120)
        spacing_x_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        spacing_x_lbl.setText("Spacing x (µm):")
        self.spacing_x = QSpinBox()
        self.spacing_x.setAlignment(AlignCenter)
        self.spacing_x.setMinimum(1)
        # self.spacing_x.valueChanged.connect(self._on_spacing_x_changed)
        _spacing_x = self._make_QHBoxLayout_wdg_with_label(
            spacing_x_lbl, self.spacing_x
        )
        group_wdg_layout.addWidget(_spacing_x)

        spacing_y_lbl = QLabel()
        spacing_y_lbl.setMinimumWidth(120)
        spacing_y_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        spacing_y_lbl.setText("Spacing y (µm):")
        self.spacing_y = QSpinBox()
        self.spacing_y.setAlignment(AlignCenter)
        self.spacing_y.setMinimum(1)
        # self.spacing_y.valueChanged.connect(self._on_spacing_y_changed)
        _spacing_y = self._make_QHBoxLayout_wdg_with_label(
            spacing_y_lbl, self.spacing_y
        )
        group_wdg_layout.addWidget(_spacing_y)

    def _set_center_wdg_gui(self):
        layout = QVBoxLayout()
        self.center_wdg.setLayout(layout)

        group_wdg = QGroupBox()
        group_wdg.setMinimumHeight(150)
        group_wdg_layout = QVBoxLayout()
        group_wdg_layout.setSpacing(5)
        group_wdg_layout.setContentsMargins(5, 5, 5, 5)
        group_wdg.setLayout(group_wdg_layout)
        layout.addWidget(group_wdg)

        plate_area_label_x = QLabel()
        plate_area_label_x.setMinimumWidth(120)
        plate_area_label_x.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        plate_area_label_x.setText("Area FOV x (mm):")
        self.plate_area_x_c = QDoubleSpinBox()
        self.plate_area_x_c.setEnabled(False)
        self.plate_area_x_c.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.plate_area_x_c.setAlignment(AlignCenter)
        self.plate_area_x_c.setMinimum(1)
        _plate_area_x = self._make_QHBoxLayout_wdg_with_label(
            plate_area_label_x, self.plate_area_x_c
        )
        group_wdg_layout.addWidget(_plate_area_x)

        plate_area_label_y = QLabel()
        plate_area_label_y.setMinimumWidth(120)
        plate_area_label_y.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        plate_area_label_y.setText("Area FOV y (mm):")
        self.plate_area_y_c = QDoubleSpinBox()
        self.plate_area_y_c.setEnabled(False)
        self.plate_area_y_c.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.plate_area_y_c.setAlignment(AlignCenter)
        self.plate_area_y_c.setMinimum(1)
        _plate_area_y = self._make_QHBoxLayout_wdg_with_label(
            plate_area_label_y, self.plate_area_y_c
        )
        group_wdg_layout.addWidget(_plate_area_y)

        number_of_FOV_label = QLabel()
        number_of_FOV_label.setMinimumWidth(120)
        number_of_FOV_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        number_of_FOV_label.setText("Number of FOV:")
        self.number_of_FOV_c = QSpinBox()
        self.number_of_FOV_c.setEnabled(False)
        self.number_of_FOV_c.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.number_of_FOV_c.setAlignment(AlignCenter)
        self.number_of_FOV_c.setValue(1)
        nFOV = self._make_QHBoxLayout_wdg_with_label(
            number_of_FOV_label, self.number_of_FOV_c
        )
        group_wdg_layout.addWidget(nFOV)

    def _make_QHBoxLayout_wdg_with_label(self, label: QLabel, wdg: QWidget):
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(label)
        layout.addWidget(wdg)
        widget.setLayout(layout)
        return widget

    def display(self, i):
        self.stack.setCurrentIndex(i)

        if i == 0:  # Random
            self.scene.clear()
            nFOV = self.number_of_FOV.value()
            area_x = self.plate_area_x.value()
            area_y = self.plate_area_y.value()
            self._set_FOV_and_mode(nFOV, "Random", area_x, area_y)

        elif i == 1:  # Grid
            self.scene.clear()

        elif i == 2:  # Center
            self.scene.clear()
            nFOV = self.number_of_FOV_c.value()
            area_x = self.plate_area_x_c.value()
            area_y = self.plate_area_y_c.value()
            self._set_FOV_and_mode(nFOV, "Center", area_x, area_y)

    def _on_area_x_changed(self, value: int):

        self.scene.clear()

        mode = "Random"
        nFOV = self.number_of_FOV.value()
        area_y = self.plate_area_y.value()

        self._set_FOV_and_mode(nFOV, mode, value, area_y)

    def _on_area_y_changed(self, value: int):

        self.scene.clear()

        mode = "Random"
        nFOV = self.number_of_FOV.value()
        area_x = self.plate_area_x.value()

        self._set_FOV_and_mode(nFOV, mode, area_x, value)

    def _on_number_of_FOV_changed(self, value: int):

        self.scene.clear()

        mode = "Random"
        area_x = self.plate_area_x.value()
        area_y = self.plate_area_y.value()

        self._set_FOV_and_mode(value, mode, area_x, area_y)

    def _load_plate_info(self, size_x, size_y, is_circular):

        self._size_x = size_x
        self._size_y = size_y
        self._is_circular = is_circular

        self.plate_area_x.setEnabled(True)

        self._set_spinboxes_values(self.plate_area_x, self.plate_area_y)
        self._set_spinboxes_values(self.plate_area_x_c, self.plate_area_y_c)

        self.plate_area_y.setEnabled(not self._is_circular)
        self.plate_area_y.setButtonSymbols(
            QAbstractSpinBox.NoButtons
            if self._is_circular
            else QAbstractSpinBox.UpDownArrows
        )

        self._on_random_button_pressed()

    def _set_spinboxes_values(self, spin_x, spin_y):
        spin_x.setMaximum(self._size_x)
        with signals_blocked(spin_x):
            spin_x.setValue(self._size_x)
        spin_y.setMaximum(self._size_y)
        with signals_blocked(spin_y):
            spin_y.setValue(self._size_y)

    def _on_random_button_pressed(self):
        self.scene.clear()

        try:
            mode = self.lst.currentItem().text()
        except AttributeError:
            mode = "Random"

        nFOV = self.number_of_FOV.value()
        area_x = self.plate_area_x.value()
        area_y = self.plate_area_y.value()
        self._set_FOV_and_mode(nFOV, mode, area_x, area_y)

    def _set_FOV_and_mode(self, nFOV: int, mode: str, area_x: float, area_y: float):

        max_size_y = 140

        main_pen = QPen(Qt.magenta)
        main_pen.setWidth(4)
        area_pen = QPen(Qt.green)
        area_pen.setWidth(4)

        if self._is_circular:
            self.scene.addEllipse(0, 0, max_size_y, max_size_y, main_pen)

            if mode == "Center":
                self.scene.clear()
                self.scene.addEllipse(0, 0, max_size_y, max_size_y, area_pen)
                center_x, center_y = (max_size_y / 2, max_size_y / 2)
                self.scene.addItem(
                    FOVPoints(
                        center_x, center_y, 5, 5, "Center", max_size_y, max_size_y
                    )
                )

            elif mode == "Random":
                diameter = (max_size_y * area_x) / self._size_x
                center = (max_size_y - diameter) / 2

                fov_area = QRectF(center, center, diameter, diameter)
                self.scene.addEllipse(fov_area, area_pen)

                points = self._random_points_in_circle(nFOV, diameter, center)
                for p in points:
                    self.scene.addItem(
                        FOVPoints(p[0], p[1], 5, 5, "Random", max_size_y, max_size_y)
                    )

        else:
            max_size_x = 140 if self._size_x == self._size_y else 190

            self.scene.addRect(0, 0, max_size_x, max_size_y, main_pen)

            if mode == "Center":
                self.scene.clear()
                self.scene.addRect(0, 0, max_size_x, max_size_y, area_pen)
                center_x, center_y = (max_size_x / 2, max_size_y / 2)
                self.scene.addItem(
                    FOVPoints(
                        center_x, center_y, 5, 5, "Center", max_size_x, max_size_y
                    )
                )

            elif mode == "Random":
                size_x = (max_size_x * area_x) / self._size_x
                size_y = (max_size_y * area_y) / self._size_y
                center_x = (max_size_x - size_x) / 2
                center_y = (max_size_y - size_y) / 2

                fov_area = QRectF(center_x, center_y, size_x, size_y)
                self.scene.addRect(fov_area, area_pen)

                points = self._random_points_in_square(
                    nFOV, size_x, size_y, max_size_x, max_size_y
                )
                for p in points:
                    self.scene.addItem(
                        FOVPoints(p[0], p[1], 5, 5, "Random", max_size_x, max_size_y)
                    )

    def _random_points_in_circle(self, nFOV, diameter: float, center):
        points = []
        radius = diameter / 2
        for _ in range(nFOV):
            # random angle
            alpha = 2 * math.pi * random.random()
            # random radius
            r = radius * math.sqrt(random.random())
            # calculating coordinates
            x = r * math.cos(alpha) + center + radius
            y = r * math.sin(alpha) + center + radius
            points.append((x, y))
        return points

    def _random_points_in_square(self, nFOV, size_x, size_y, max_size_x, max_size_y):
        x_left = (max_size_x - size_x) / 2  # left bound
        x_right = x_left + size_x  # right bound
        y_up = (max_size_y - size_y) / 2  # upper bound
        y_down = y_up + size_y  # lower bound
        points = []
        for _ in range(nFOV):
            x = np.random.randint(x_left, x_right)
            y = np.random.randint(y_up, y_down)
            points.append((x, y))
        return points


class FOVPoints(QGraphicsItem):
    def __init__(
        self,
        x: int,
        y: int,
        size_x: float,
        size_y: float,
        mode: str,
        max_size_x: float,
        max_size_y: float,
    ):
        super().__init__()

        self._x = x
        self._y = y

        self._size_x = size_x
        self._size_y = size_y

        self._mode = mode

        self.width = max_size_x
        self.height = max_size_y

        self.point = QRectF(self._x, self._y, self._size_x, self._size_y)

    def boundingRect(self):
        return self.point

    def paint(self, painter=None, style=None, widget=None):
        x, y = self.getCenter()
        pen = QPen()
        pen.setWidth(5)
        painter.setPen(pen)
        painter.drawPoint(x, y)

    def getCenter(self):
        if self._mode == "Random":
            xc = round(self._x + (self._size_x / 2))
            yc = round(self._y + (self._size_y / 2))
        elif self._mode == "Center":
            xc = round(self._x)
            yc = round(self._y)
        return xc, yc

    def getPositionsInfo(self):
        xc, yc = self.getCenter()
        return xc, yc, self.width, self.height


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = SelectFOV()
    win.show()
    sys.exit(app.exec_())
