from __future__ import annotations

from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt

from ._config_widget import MMConfigurationWidget
from ._tab_wdg import MMTabWidget


class MicroManagerWidget(QtW.QWidget):
    def __init__(self):
        super().__init__()

        # sub_widgets
        self.cfg_wdg = MMConfigurationWidget()
        self.tab_wdg = MMTabWidget()

        self.create_gui()

    def create_gui(self):

        # main widget
        self.main_layout = QtW.QVBoxLayout()
        self.main_layout.setContentsMargins(10, 0, 10, 0)
        self.main_layout.setSpacing(3)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.main_layout)

        # add cfg_wdg
        self.main_layout.addWidget(self.cfg_wdg)

        self.main_layout.addWidget(self.tab_wdg)
