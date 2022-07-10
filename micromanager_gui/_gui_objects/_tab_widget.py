from pymmcore_widgets.camera_roi_widget import CameraWidget
from pymmcore_widgets.channel_widget import ChannelWidget
from pymmcore_widgets.core import get_core_singleton
from pymmcore_widgets.exposure_widget import DefaultCameraExposureWidget
from pymmcore_widgets.group_preset_table_widget import GroupPresetTableWidget
from pymmcore_widgets.live_button_widget import LiveButton
from pymmcore_widgets.mda_widget.mda_widget import MultiDWidget
from pymmcore_widgets.objective_widget import ObjectivesWidget
from pymmcore_widgets.snap_button_widget import SnapButton
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from superqt import QCollapsible

from .._gui_objects._sample_explorer_widget._sample_explorer_widget import (
    MMExploreSample,
)
from .._gui_objects._shutters_widget import MMShuttersWidget
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
        self.shutter_wdg = MMShuttersWidget()
        self.obj_wdg = ObjectivesWidget()
        self.ch_wdg = ChannelWidget()
        self.exp_wdg = DefaultCameraExposureWidget()
        self.ill = IlluminationWidget()
        self.mda = MultiDWidget()
        self.explorer = MMExploreSample()
        self.group_preset = GroupPresetTableWidget()
        self.cam_wdg = CameraWidget()

        self._create_gui()

        self.addTab(self.mda, "Multi-D Acquisition")
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

        cam = self._create_cam_collapsible()
        tab_layout.addWidget(cam)

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


# from pathlib import Path

# from pymmcore_widgets.channel_widget import ChannelWidget
# from pymmcore_widgets.exposure_widget import DefaultCameraExposureWidget
# from pymmcore_widgets.live_button_widget import LiveButton
# from pymmcore_widgets.snap_button_widget import SnapButton
# from qtpy import QtCore
# from qtpy import QtWidgets as QtW

# ICONS = Path(__file__).parent.parent / "icons"


# class MMTabWidget(QtW.QWidget):
#     """Tabs shown in the main window."""

#     def __init__(self):
#         super().__init__()
#         self.setup_gui()

#     def setup_gui(self):

#         # main_layout
#         self.main_layout = QtW.QGridLayout()
#         self.main_layout.setSpacing(0)
#         self.main_layout.setContentsMargins(0, 0, 0, 0)

#         # tabWidget
#         self.tabWidget = QtW.QTabWidget()
#         self.tabWidget.setMovable(True)
#         self.tabWidget_layout = QtW.QVBoxLayout()

#         sizepolicy = QtW.QSizePolicy(
#             QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Expanding
#         )
#         self.tabWidget.setSizePolicy(sizepolicy)

#         # snap_live_tab and layout
#         self.snap_live_tab = QtW.QWidget()
#         self.snap_live_tab_layout = QtW.QGridLayout()

#         wdg_sizepolicy = QtW.QSizePolicy(
#             QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Minimum
#         )

#         # channel in snap_live_tab
#         self.snap_channel_groupBox = QtW.QGroupBox()
#         self.snap_channel_groupBox.setSizePolicy(wdg_sizepolicy)
#         self.snap_channel_groupBox.setTitle("Channel")
#         self.snap_channel_groupBox_layout = QtW.QHBoxLayout()
#         self.snap_channel_comboBox = ChannelWidget()
#         self.snap_channel_groupBox_layout.addWidget(self.snap_channel_comboBox)
#         self.snap_channel_groupBox.setLayout(self.snap_channel_groupBox_layout)
#         self.snap_live_tab_layout.addWidget(self.snap_channel_groupBox, 0, 0)

#         # exposure in snap_live_tab
#         self.exposure_widget = DefaultCameraExposureWidget()
#         self.exp_groupBox = QtW.QGroupBox()
#         self.exp_groupBox.setSizePolicy(wdg_sizepolicy)
#         self.exp_groupBox.setTitle("Exposure Time")
#         self.exp_groupBox_layout = QtW.QHBoxLayout()
#         self.exp_groupBox_layout.addWidget(self.exposure_widget)
#         self.exp_groupBox.setLayout(self.exp_groupBox_layout)
#         self.snap_live_tab_layout.addWidget(self.exp_groupBox, 0, 1)

#         # snap/live in snap_live_tab
#         self.btn_wdg = QtW.QWidget()
#         self.btn_wdg.setMaximumHeight(65)
#         self.btn_wdg_layout = QtW.QHBoxLayout()
#         self.snap_Button = SnapButton(
#             button_text="Snap", icon_size=40, icon_color=(0, 255, 0)
#         )
#         self.snap_Button.setMinimumSize(QtCore.QSize(200, 50))
#         self.snap_Button.setMaximumSize(QtCore.QSize(200, 50))
#         self.btn_wdg_layout.addWidget(self.snap_Button)
#         self.live_Button = LiveButton(
#             button_text_on_off=("Live", "Stop"),
#             icon_size=40,
#             icon_color_on_off=((0, 255, 0), "magenta"),
#         )
#         self.live_Button.setMinimumSize(QtCore.QSize(200, 50))
#         self.live_Button.setMaximumSize(QtCore.QSize(200, 50))
#         self.btn_wdg_layout.addWidget(self.live_Button)
#         self.btn_wdg.setLayout(self.btn_wdg_layout)
#         self.snap_live_tab_layout.addWidget(self.btn_wdg, 1, 0, 1, 2)

#         # max min in snap_live_tab
#         self.max_min_wdg = QtW.QWidget()
#         self.max_min_wdg_layout = QtW.QHBoxLayout()
#         self.max_min_val_label_name = QtW.QLabel()
#         self.max_min_val_label_name.setText("(min, max)")
#         self.max_min_val_label_name.setMaximumWidth(70)
#         self.max_min_val_label = QtW.QLabel()
#         self.max_min_wdg_layout.addWidget(self.max_min_val_label_name)
#         self.max_min_wdg_layout.addWidget(self.max_min_val_label)
#         self.max_min_wdg.setLayout(self.max_min_wdg_layout)
#         self.snap_live_tab_layout.addWidget(self.max_min_wdg, 2, 0, 1, 2)

#         # spacer
#         spacer = QtW.QSpacerItem(
#             20, 40, QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Expanding
#         )
#         self.snap_live_tab_layout.addItem(spacer, 3, 0)

#         # set snap_live_tab layout
#         self.snap_live_tab.setLayout(self.snap_live_tab_layout)

#         # add tabWidget
#         self.tabWidget.setLayout(self.tabWidget_layout)
#         self.tabWidget.addTab(self.snap_live_tab, "Snap/Live")
#         self.main_layout.addWidget(self.tabWidget)

#         # Set main layout
#         self.setLayout(self.main_layout)


# if __name__ == "__main__":
#     import sys

#     app = QtW.QApplication(sys.argv)
#     win = MMTabWidget()
#     win.show()
#     sys.exit(app.exec_())
