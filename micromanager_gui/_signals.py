from qtpy.QtCore import QObject, Signal


class camStreamEvents(QObject):
    camStreamData = Signal(list, int)
