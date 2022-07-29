from pymmcore_widgets._camera_roi_widget import CameraRoiWidget
from pymmcore_widgets._channel_widget import ChannelWidget
from pymmcore_widgets._core import get_core_singleton
from pymmcore_widgets._exposure_widget import DefaultCameraExposureWidget
from pymmcore_widgets._group_preset_table_widget import GroupPresetTableWidget
from pymmcore_widgets._live_button_widget import LiveButton

# from pymmcore_widgets.mda_widget.mda_widget import MultiDWidget
from pymmcore_widgets._objective_widget import ObjectivesWidget
from pymmcore_widgets._snap_button_widget import SnapButton
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from superqt import QCollapsible

from .._gui_objects._sample_explorer_widget._sample_explorer_widget import (
    MMExploreSample,
)

# from .._gui_objects._shutters_widget import MMShuttersWidget
from ._illumination_widget import IlluminationWidget


class MMTabWidget(QtW.QTabWidget):
    """GUI main QTabWidget."""

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
        # self.shutter_wdg = MMShuttersWidget()
        self.obj_wdg = ObjectivesWidget()
        self.ch_wdg = ChannelWidget()
        self.exp_wdg = DefaultCameraExposureWidget()
        self.ill = IlluminationWidget()
        # self.mda = MultiDWidget()
        self.explorer = MMExploreSample()
        self.group_preset = GroupPresetTableWidget()
        self.cam_wdg = CameraRoiWidget()

        self._create_gui()

        # self.addTab(self.mda, "Multi-D Acquisition")
        self.addTab(self.explorer, "Sample Explorer")
        plus_tab = SelectTabs(self)
        self.addTab(plus_tab, "+")

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

        cam = self._create_cam_collapsible()
        tab_layout.addWidget(cam)

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

        self.gp = QtW.QGroupBox()
        self.gp_layout = QtW.QVBoxLayout()
        self.gp_layout.setSpacing(0)
        self.gp_layout.setContentsMargins(5, 0, 5, 0)
        self.gp.setLayout(self.gp_layout)
        self.gp_layout.addWidget(self.group_preset)
        tab_layout.addWidget(self.gp)

        return tab

    def _create_cam_collapsible(self) -> QtW.QWidget:

        cam = QtW.QGroupBox()
        cam.setSizePolicy(
            QtW.QSizePolicy(QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Fixed)
        )
        cam_layout = QtW.QVBoxLayout()
        cam_layout.setSpacing(0)
        cam_layout.setContentsMargins(0, 0, 0, 0)
        cam.setLayout(cam_layout)

        coll = QCollapsible(title="Camera ROI")
        coll.layout().setSpacing(0)
        coll.layout().setContentsMargins(0, 0, 0, 0)
        coll.addWidget(self.cam_wdg)

        cam_layout.addWidget(coll)

        return cam

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
        self.snap_Button = SnapButton()
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


class SelectTabs(QtW.QWidget):
    """
    A widget that creates a TabCheckbox list of the main QTabWidget tabs.

    It can be used to show/hide each tab (excluding the main tab).
    """

    def __init__(self, parent: QtW.QTabWidget):
        super().__init__(parent)

        layout = QtW.QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        for idx in range(1, parent.count()):
            checkbox = TabCheckbox(parent.tabText(idx), idx, parent)
            if parent.isTabVisible(idx):
                checkbox.setChecked(True)

            layout.addWidget(checkbox)

        spacer = QtW.QSpacerItem(
            10, 10, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Expanding
        )
        layout.addItem(spacer)


class TabCheckbox(QtW.QCheckBox):
    """A CheckBox widget to show/hide tabs in a QTabWidget."""

    def __init__(self, tab_label: str, tab_index: int, parent: QtW.QTabWidget):
        super().__init__()

        self.tab_wdg = parent
        self.tab_index = tab_index
        self.setText(tab_label)
        self.toggled.connect(self._on_checkbox_toggled)

    def _on_checkbox_toggled(self, state: bool):
        self.tab_wdg.setTabVisible(self.tab_index, state)
