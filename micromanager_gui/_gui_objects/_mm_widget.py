from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGroupBox, QSizePolicy, QVBoxLayout, QWidget
from superqt import QCollapsible

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

        stages = QGroupBox()
        stages.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))
        stages_layout = QVBoxLayout()
        stages_layout.setSpacing(0)
        stages_layout.setContentsMargins(5, 0, 5, 0)
        stages.setLayout(stages_layout)

        stages_coll = QCollapsible(title="Stages")
        stages_coll.layout().setSpacing(0)
        stages_coll.layout().setContentsMargins(0, 0, 5, 10)
        stages_coll.addWidget(self.stages_wdg)
        stages_coll.expand(animate=False)

        stages_layout.addWidget(stages_coll)

        return stages
