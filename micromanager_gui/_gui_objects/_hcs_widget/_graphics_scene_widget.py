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
        # self._print_selected_wells()  # to be removed

    def _clear_selection(self):
        """clear selection"""
        for item in self.items():
            if item.isSelected():
                item.setSelected(False)
                item.setBrush(self.unselected)
        # self._print_selected_wells()  # to be removed

    def _get_plate_positions(self):
        return [item.getPos() for item in reversed(self.items()) if item.isSelected()]

    # def _get_A1_position(self):
    #     for item in reversed(self.items()):
    #         w = item.getPos()
    #         if w[0] == "A1":
    #             return w

    # def _print_selected_wells(self):  # to be removed
    #     print("___________")
    #     print("Selected wells:")
    #     self._selected_wells = [
    #         item.getPos() for item in self.items() if item.isSelected()
    #     ]
    #     self._selected_wells.sort()
    #     for i in self._selected_wells:
    #         print(i)
