from pathlib import Path
from typing import Optional

from fonticon_mdi6 import MDI6
from qtpy.QtCore import QSize, Qt
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from superqt.fonticon import icon

from micromanager_gui._gui_objects._hcs_widget._calibration_widget import (
    PlateCalibration,
)
from micromanager_gui._gui_objects._hcs_widget._generate_fov_widget import SelectFOV
from micromanager_gui._gui_objects._hcs_widget._graphics_scene_widget import (
    GraphicsScene,
)
from micromanager_gui._gui_objects._hcs_widget._hcs_mda_widget import (
    ChannelPositionWidget,
)

PLATE_DATABASE = Path(__file__).parent / "_well_plate.yaml"
AlignCenter = Qt.AlignmentFlag.AlignCenter


class HCSGui(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(AlignCenter)
        widgets = self._add_tab_wdg()
        scroll.setWidget(widgets)

        layout.addWidget(scroll)

        btns = self._create_btns_wdg()
        layout.addWidget(btns)

    def _add_tab_wdg(self):

        tab = QTabWidget()
        tab.setTabPosition(QTabWidget.West)

        select_plate_tab = self._create_plate_and_fov_tab()
        self.ch_and_pos_list = ChannelPositionWidget()
        # self.ch_and_pos_list.position_list_button.clicked.connect(
        #     self._generate_pos_list
        # )
        self.saving_tab = QWidget()

        tab.addTab(select_plate_tab, "  Plate, FOVs and Calibration  ")
        tab.addTab(self.ch_and_pos_list, "  Channel and Positions List  ")
        tab.addTab(self.saving_tab, "  Saving  ")

        return tab

    def _create_plate_and_fov_tab(self):
        wdg = QWidget()
        wdg_layout = QVBoxLayout()
        wdg_layout.setSpacing(20)
        wdg_layout.setContentsMargins(10, 10, 10, 10)
        wdg.setLayout(wdg_layout)

        self.scene = GraphicsScene()
        self.view = QGraphicsView(self.scene, self)
        self.view.setStyleSheet("background:grey;")
        self._width = 500
        self._height = 300
        self.view.setMinimumSize(self._width, self._height)

        # well plate selector combo and clear selection QPushButton
        upper_wdg = QWidget()
        upper_wdg_layout = QHBoxLayout()
        wp_combo_wdg = self._create_wp_combo_selector()
        self.custom_plate = QPushButton(text="Custom Plate")
        # self.custom_plate.clicked.connect(self._update_plate_yaml)
        self.clear_button = QPushButton(text="Clear Selection")
        # self.clear_button.clicked.connect(self.scene._clear_selection)
        upper_wdg_layout.addWidget(wp_combo_wdg)
        upper_wdg_layout.addWidget(self.custom_plate)
        upper_wdg_layout.addWidget(self.clear_button)
        upper_wdg.setLayout(upper_wdg_layout)

        self.FOV_selector = SelectFOV()

        # add widgets
        view_group = QGroupBox("Plate Selection")
        view_gp_layout = QVBoxLayout()
        view_gp_layout.setSpacing(0)
        view_gp_layout.setContentsMargins(10, 10, 10, 10)
        view_group.setLayout(view_gp_layout)
        view_gp_layout.addWidget(upper_wdg)
        view_gp_layout.addWidget(self.view)
        wdg_layout.addWidget(view_group)

        FOV_group = QGroupBox(title="FOVs Selection")
        FOV_group.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        FOV_gp_layout = QVBoxLayout()
        FOV_gp_layout.setSpacing(0)
        FOV_gp_layout.setContentsMargins(10, 10, 10, 10)
        FOV_group.setLayout(FOV_gp_layout)
        FOV_gp_layout.addWidget(self.FOV_selector)
        wdg_layout.addWidget(FOV_group)

        cal_group = QGroupBox(title="Plate Calibration")
        cal_group_layout = QVBoxLayout()
        cal_group_layout.setSpacing(0)
        cal_group_layout.setContentsMargins(10, 10, 10, 10)
        cal_group.setLayout(cal_group_layout)
        self.calibration = PlateCalibration()
        # self.calibration.PlateFromCalibration.connect(self._on_plate_from_calobration)
        cal_group_layout.addWidget(self.calibration)
        wdg_layout.addWidget(cal_group)

        verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        wdg_layout.addItem(verticalSpacer)

        return wdg

    def _create_btns_wdg(self):

        wdg = QWidget()
        wdg.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))
        wdg_layout = QHBoxLayout()
        wdg_layout.setAlignment(Qt.AlignVCenter)
        wdg_layout.setSpacing(10)
        wdg_layout.setContentsMargins(10, 15, 10, 10)
        wdg.setLayout(wdg_layout)

        acq_wdg = QWidget()
        acq_wdg_layout = QHBoxLayout()
        acq_wdg_layout.setSpacing(0)
        acq_wdg_layout.setContentsMargins(0, 0, 0, 0)
        acq_wdg.setLayout(acq_wdg_layout)
        acquisition_order_label = QLabel(text="Acquisition Order:")
        lbl_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        acquisition_order_label.setSizePolicy(lbl_sizepolicy)
        self.acquisition_order_comboBox = QComboBox()
        self.acquisition_order_comboBox.setMinimumWidth(100)
        self.acquisition_order_comboBox.addItems(["tpzc", "tpcz", "ptzc", "ptcz"])
        acq_wdg_layout.addWidget(acquisition_order_label)
        acq_wdg_layout.addWidget(self.acquisition_order_comboBox)

        btn_sizepolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        min_width = 100
        icon_size = 40
        self.run_Button = QPushButton(text="Run")
        # self.run_Button.clicked.connect(self._on_run_clicked)
        self.run_Button.setMinimumWidth(min_width)
        self.run_Button.setStyleSheet("QPushButton { text-align: center; }")
        self.run_Button.setSizePolicy(btn_sizepolicy)
        self.run_Button.setIcon(icon(MDI6.play_circle_outline, color=(0, 255, 0)))
        self.run_Button.setIconSize(QSize(icon_size, icon_size))
        self.pause_Button = QPushButton("Pause")
        # self.pause_Button.released.connect(lambda: self._mmc.mda.toggle_pause())
        self.pause_Button.setMinimumWidth(min_width)
        self.pause_Button.setStyleSheet("QPushButton { text-align: center; }")
        self.pause_Button.setSizePolicy(btn_sizepolicy)
        self.pause_Button.setIcon(icon(MDI6.pause_circle_outline, color="green"))
        self.pause_Button.setIconSize(QSize(icon_size, icon_size))
        self.pause_Button.hide()
        self.cancel_Button = QPushButton("Cancel")
        # self.cancel_Button.released.connect(lambda: self._mmc.mda.cancel())
        self.cancel_Button.setMinimumWidth(min_width)
        self.cancel_Button.setStyleSheet("QPushButton { text-align: center; }")
        self.cancel_Button.setSizePolicy(btn_sizepolicy)
        self.cancel_Button.setIcon(icon(MDI6.stop_circle_outline, color="magenta"))
        self.cancel_Button.setIconSize(QSize(icon_size, icon_size))
        self.cancel_Button.hide()

        spacer = QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Expanding)

        wdg_layout.addWidget(acq_wdg)
        wdg_layout.addItem(spacer)
        wdg_layout.addWidget(self.run_Button)
        wdg_layout.addWidget(self.pause_Button)
        wdg_layout.addWidget(self.cancel_Button)

        return wdg

    def _create_wp_combo_selector(self):
        combo_wdg = QWidget()
        wp_combo_layout = QHBoxLayout()
        wp_combo_layout.setContentsMargins(0, 0, 0, 0)
        wp_combo_layout.setSpacing(0)

        combo_label = QLabel()
        combo_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        combo_label.setText("Plate:")
        combo_label.setMaximumWidth(75)

        self.wp_combo = QComboBox()
        # self.wp_combo.currentTextChanged.connect(self._on_combo_changed)

        wp_combo_layout.addWidget(combo_label)
        wp_combo_layout.addWidget(self.wp_combo)
        combo_wdg.setLayout(wp_combo_layout)

        return combo_wdg


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = HCSGui()
    win.show()
    sys.exit(app.exec_())
