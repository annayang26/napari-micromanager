from qtpy.QtCore import QRect, QRectF, Qt
from qtpy.QtGui import QBrush, QTransform
from qtpy.QtWidgets import QGraphicsScene, QRubberBand


class GraphicsScene(QGraphicsScene):
    def __init__(self):
        super().__init__()

        self.unselected = QBrush(Qt.green)
        self.selected = QBrush(Qt.magenta)

        self.well_pos = 0
        self.new_well_pos = 0

        self._selected_wells = []

    def mousePressEvent(self, event):
        self.originQPoint = event.screenPos()
        self.currentQRubberBand = QRubberBand(QRubberBand.Rectangle)
        self.originCropPoint = event.scenePos()

        self._selected_wells = [item for item in self.items() if item.isSelected()]

        for item in self._selected_wells:
            item.setBrush(self.selected)

        if well := self.itemAt(self.originCropPoint, QTransform()):
            if well.isSelected():
                well.setBrush(self.unselected)
                well.setSelected(False)
            else:
                well.setBrush(self.selected)
                well.setSelected(True)

    def mouseMoveEvent(self, event):
        self.currentQRubberBand.setGeometry(QRect(self.originQPoint, event.screenPos()))
        self.currentQRubberBand.show()
        selection = self.items(QRectF(self.originCropPoint, event.scenePos()))
        for item in self.items():
            if item in selection:
                item.setBrush(self.selected)
                item.setSelected(True)
            elif item not in self._selected_wells:
                item.setBrush(self.unselected)
                item.setSelected(False)

    def mouseReleaseEvent(self, event):
        self.currentQRubberBand.hide()

    def _clear_selection(self):
        """clear selection"""
        for item in self.items():
            if item.isSelected():
                item.setSelected(False)
                item.setBrush(self.unselected)

    def _get_plate_positions(self):

        if not self.items():
            return

        well_list_to_order = [
            item.getPos() for item in reversed(self.items()) if item.isSelected()
        ]

        # for 'snake' acquisition
        correct_order = []
        to_add = []
        try:
            previous_row = well_list_to_order[0][1]
        except IndexError:
            return
        corrent_row = 0
        for idx, wrc in enumerate(well_list_to_order):
            well, row, col = wrc
            if row > previous_row or idx == len(well_list_to_order) - 1:
                if idx == len(well_list_to_order) - 1:
                    to_add.append((well, row, col))
                if corrent_row % 2 == 0:
                    correct_order.extend(iter(to_add))
                else:
                    correct_order.extend(iter(reversed(to_add)))
                to_add.clear()
                corrent_row += 1

            to_add.append((well, row, col))
            previous_row = row

        return correct_order
