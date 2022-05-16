from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGroupBox, QSizePolicy, QVBoxLayout, QWidget

from .._gui_objects._xyz_stages import MMStagesWidget
from ._config_widget import MMConfigurationWidget
from ._tab_wdg import MMTabWidget


class MicroManagerWidget(QWidget):
    def __init__(self):
        super().__init__()

        # sub_widgets
        self.cfg_wdg = MMConfigurationWidget()
        self.stages_wdg = MMStagesWidget()
        self.tab_wdg = MMTabWidget()

        self.create_gui()

    def create_gui(self):

        # main widget
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 0, 10, 0)
        self.main_layout.setSpacing(3)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.main_layout)

        # add
        self.main_layout.addWidget(self.cfg_wdg)
        stg = self._create_stage_wdg()
        self.main_layout.addWidget(stg)
        self.main_layout.addWidget(self.tab_wdg)

    def _create_stage_wdg(self):
        self.stages = QGroupBox()
        self.stages.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.stages_layout = QVBoxLayout()
        self.stages_layout.setSpacing(0)
        self.stages_layout.setContentsMargins(5, 0, 5, 0)
        self.stages.setLayout(self.stages_layout)
        self.stages_layout.addWidget(self.stages_wdg)
        return self.stages
