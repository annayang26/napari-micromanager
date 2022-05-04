from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt

from .._core import get_core_singleton
from .._core_widgets import DefaultCameraExposureWidget
from .._core_widgets._live_button_widget import LiveButton
from .._core_widgets._snap_button_widget import SnapButton
from .._gui_objects._camera_widget import MMCameraWidget
from .._gui_objects._channel_widget import ChannelWidget
from .._gui_objects._group_preset_table_widget import MMGroupPresetTableWidget
from .._gui_objects._mda_widget import MultiDWidget
from .._gui_objects._mm_illumination_wdg import MMIlluminationWidget
from .._gui_objects._mm_shutters_widget import MMShuttersWidget
from .._gui_objects._objective_widget import MMObjectivesWidget
from .._gui_objects._sample_explorer_widget._sample_explorer_widget import ExploreSample
from .._gui_objects._xyz_stages import MMStagesWidget


class MMTabWidget(QtW.QTabWidget):
    def __init__(self):
        super().__init__()

        self._mmc = get_core_singleton()
        self._mmc.events.systemConfigurationLoaded.connect(self._resize)

        self.setMovable(True)
        self.tab_layout = QtW.QVBoxLayout()
        self.tab_layout.setSpacing(0)
        self.tab_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.tab_layout)
        self.setSizePolicy(
            QtW.QSizePolicy(QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Minimum)
        )

        # sub_widgets
        self.shutter_wdg = MMShuttersWidget()
        self.obj_wdg = MMObjectivesWidget()
        self.cam_wdg = MMCameraWidget()
        self.ch_wdg = ChannelWidget()
        self.exp_wdg = DefaultCameraExposureWidget()
        self.ill = MMIlluminationWidget()
        self.stages_wdg = MMStagesWidget()
        self.mda = MultiDWidget()
        self.explorer = ExploreSample()
        self.group_preset = MMGroupPresetTableWidget()

        self._create_gui()

        self.addTab(self.mda, "Multi-D Acquisition")
        self.addTab(self.explorer, "Sample Explorer")

    def _create_gui(self):

        self.tab = QtW.QWidget()
        self.tab_layout = QtW.QVBoxLayout()
        self.tab_layout.setSpacing(0)
        self.tab_layout.setContentsMargins(10, 10, 10, 10)
        self.tab.setLayout(self.tab_layout)
        self.addTab(self.tab, "Main")

        self._scroll = QtW.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self_tab = self._create_tab()
        self._scroll.setWidget(self_tab)
        self.tab_layout.addWidget(self._scroll)

        self._resize()

    def _create_tab(self):

        tab = QtW.QWidget()
        tab_layout = QtW.QVBoxLayout()
        tab_layout.setSpacing(10)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab.setLayout(tab_layout)

        tab_layout.addWidget(self.shutter_wdg)

        self.cam = QtW.QGroupBox()
        self.cam_layout = QtW.QVBoxLayout()
        self.cam_layout.setSpacing(10)
        self.cam_layout.setContentsMargins(5, 0, 5, 0)
        self.cam.setLayout(self.cam_layout)
        self.cam_layout.addWidget(self.cam_wdg)
        tab_layout.addWidget(self.cam)

        self.obj = QtW.QGroupBox()
        self.obj_layout = QtW.QHBoxLayout()
        self.obj_layout.setSpacing(10)
        self.obj_layout.setContentsMargins(5, 0, 5, 0)
        self.obj.setLayout(self.obj_layout)
        self.obj_layout.addWidget(self.obj_wdg)
        self.escape_btn = QtW.QPushButton("Escape")
        self.escape_btn.clicked.connect(self._escape)
        self.obj_layout.addWidget(self.escape_btn)
        tab_layout.addWidget(self.obj)

        self.ch_exp_snap_live = QtW.QGroupBox()
        self.ch_exp_snap_live_layout = QtW.QVBoxLayout()
        self.ch_exp_snap_live_layout.setSpacing(10)
        self.ch_exp_snap_live_layout.setContentsMargins(5, 0, 5, 0)
        self.ch_exp_snap_live.setLayout(self.ch_exp_snap_live_layout)
        tab_layout.addWidget(self.ch_exp_snap_live)
        self.ch_exp = self._create_ch_exp_wdg()
        self.ch_exp_snap_live_layout.addWidget(self.ch_exp)
        self.snap_live = self._create_snap_live_wdg()
        self.max_min_wdg = QtW.QWidget()
        self.max_min_wdg_layout = QtW.QHBoxLayout()
        self.max_min_val_label_name = QtW.QLabel()
        self.max_min_val_label_name.setText("(min, max)")
        self.max_min_wdg.setSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Fixed)
        self.max_min_val_label = QtW.QLabel()
        self.max_min_wdg_layout.addWidget(self.max_min_val_label_name)
        self.max_min_wdg_layout.addWidget(self.max_min_val_label)
        self.max_min_wdg.setLayout(self.max_min_wdg_layout)
        self.ch_exp_snap_live_layout.addWidget(self.snap_live)
        self.ch_exp_snap_live_layout.addWidget(self.max_min_wdg)

        self.ill_wdg = QtW.QGroupBox()
        self.ill_wdg_layout = QtW.QVBoxLayout()
        self.ill_wdg_layout.setSpacing(0)
        self.ill_wdg_layout.setContentsMargins(5, 0, 5, 0)
        self.ill_wdg.setLayout(self.ill_wdg_layout)
        self.ill_wdg_layout.addWidget(self.ill)
        tab_layout.addWidget(self.ill_wdg)

        self.stages = QtW.QGroupBox()
        self.stages_layout = QtW.QVBoxLayout()
        self.stages_layout.setSpacing(0)
        self.stages_layout.setContentsMargins(5, 0, 5, 0)
        self.stages.setLayout(self.stages_layout)
        self.stages_layout.addWidget(self.stages_wdg)
        tab_layout.addWidget(self.stages)

        self.gp = QtW.QGroupBox()
        self.gp_layout = QtW.QVBoxLayout()
        self.gp_layout.setSpacing(0)
        self.gp_layout.setContentsMargins(5, 0, 5, 0)
        self.gp.setLayout(self.gp_layout)
        self.gp_layout.addWidget(self.group_preset)
        tab_layout.addWidget(self.gp)

        return tab

    def _create_ch_exp_wdg(self):
        self.ch_exp_wdg = QtW.QWidget()
        self.ch_exp_wdg_layout = QtW.QHBoxLayout()
        self.ch_exp_wdg_layout.setSpacing(10)
        self.ch_exp_wdg_layout.setContentsMargins(0, 0, 0, 0)
        self.ch_exp_wdg.setLayout(self.ch_exp_wdg_layout)

        ch_lbl = QtW.QLabel("Channel:")
        ch_lbl.setSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Fixed)
        exp_lbl = QtW.QLabel("Exposure Time:")
        exp_lbl.setSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Fixed)

        self.ch_exp_wdg_layout.addWidget(ch_lbl)
        self.ch_exp_wdg_layout.addWidget(self.ch_wdg)
        self.ch_exp_wdg_layout.addWidget(exp_lbl)
        self.ch_exp_wdg_layout.addWidget(self.exp_wdg)
        return self.ch_exp_wdg

    def _create_snap_live_wdg(self):

        self.btn_wdg = QtW.QWidget()
        self.btn_wdg_layout = QtW.QHBoxLayout()
        self.btn_wdg_layout.setSpacing(10)
        self.btn_wdg_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_wdg.setLayout(self.btn_wdg_layout)
        self.snap_Button = SnapButton(
            button_text="Snap", icon_size=40, icon_color=(0, 255, 0)
        )
        self.live_Button = LiveButton(
            button_text_on_off=("Live", "Stop"),
            icon_size=40,
            icon_color_on_off=((0, 255, 0), "magenta"),
        )
        self.btn_wdg_layout.addWidget(self.snap_Button)
        self.btn_wdg_layout.addWidget(self.live_Button)

        return self.btn_wdg

    def _escape(self):
        self._mmc.setPosition(0.0)

    def _resize(self):
        self.setMinimumWidth(self.sizeHint().width())
