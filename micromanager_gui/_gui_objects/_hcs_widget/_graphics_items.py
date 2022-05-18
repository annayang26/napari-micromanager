import string
from typing import Optional

from qtpy.QtCore import QRectF, Qt
from qtpy.QtGui import QBrush, QColor, QFont, QPen, QTextOption
from qtpy.QtWidgets import QGraphicsItem

ALPHABET = string.ascii_uppercase


class Well(QGraphicsItem):
    def __init__(
        self,
        x: int,
        y: int,
        size_x: float,
        size_y: float,
        row: int,
        col: int,
        text_size: int,
        circular: bool,
        text_color: str = "",
    ):
        super().__init__()

        self._x = x
        self._y = y

        self._size_x = size_x
        self._size_y = size_y

        self._row = row
        self._col = col
        self._text_size = text_size
        self.circular = circular

        self.text_color = text_color

        self.brush = QBrush(Qt.green)
        self.pen = QPen(Qt.black)
        self.well_shape = QRectF(self._x, self._y, self._size_x, self._size_y)

        self.setFlag(self.ItemIsSelectable, True)

    def boundingRect(self):
        return self.well_shape

    def paint(self, painter=None, style=None, widget=None):
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        if self.circular:
            painter.drawEllipse(self.well_shape)
        else:
            painter.drawRect(self.well_shape)

        font = QFont("Helvetica", self._text_size)
        font.setWeight(QFont.Bold)
        pen = QPen(QColor(self.text_color))
        painter.setPen(pen)
        painter.setFont(font)
        well_name = f"{ALPHABET[self._row]}{self._col + 1}"
        painter.drawText(self.well_shape, well_name, QTextOption(Qt.AlignCenter))

    def setBrush(self, brush: QColor = QBrush(Qt.green)):
        self.brush = brush
        self.update()

    def getBrush(self):
        return self.brush

    def getPos(self):
        row = self._row
        col = self._col
        well = f"{ALPHABET[self._row]}{self._col + 1}"
        return well, row, col


class WellArea(QGraphicsItem):
    def __init__(
        self,
        circular: bool,
        start_x: int,
        start_y: int,
        width: float,
        height: float,
        pen: QPen,
    ):

        super().__init__()

        self._view_size = 202  # size of QGraphicsView

        self._circular = circular
        self._start_x = start_x
        self._start_y = start_y
        self._w = width
        self._h = height
        self._pen = pen

        self.rect = QRectF(self._start_x, self._start_y, self._w, self._h)

    def boundingRect(self):
        return QRectF(0, 0, self._view_size, self._view_size)

    def paint(self, painter=None, style=None, widget=None):
        painter.setPen(self._pen)
        if self._circular:
            painter.drawEllipse(self.rect)
        else:
            painter.drawRect(self.rect)


class FOVPoints(QGraphicsItem):
    def __init__(
        self,
        x: int,
        y: int,
        scene_size_x: int,
        scene_size_y: int,
        plate_size_x: float,
        plate_size_y: float,
        image_size_mm_x: float,
        image_size_mm_y: float,
        fov_row: Optional[int] = None,
        fov_col: Optional[int] = None,
    ):
        super().__init__()

        self._view_size = 202  # size of QGraphicsView

        self._x = x
        self._y = y
        self.fov_row = fov_row
        self.fov_col = fov_col

        # fov width and height in scene px
        self._x_size = (scene_size_x * image_size_mm_x) / plate_size_x
        self._y_size = (scene_size_y * image_size_mm_y) / plate_size_y

        self.width = scene_size_x
        self.height = scene_size_y

    def boundingRect(self):
        return QRectF(0, 0, self._view_size, self._view_size)

    def paint(self, painter=None, style=None, widget=None):
        pen = QPen()
        pen.setWidth(2)
        painter.setPen(pen)

        # x, y = self.getCenter()
        # painter.drawPoint(x, y)

        start_x = self._x - (self._x_size / 2)
        start_y = self._y - (self._y_size / 2)
        painter.drawRect(QRectF(start_x, start_y, self._x_size, self._y_size))

    def getCenter(self):
        xc = round(self._x)
        yc = round(self._y)
        return xc, yc

    def getPositionsInfo(self):
        xc, yc = self.getCenter()
        return xc, yc, self.width, self.height
