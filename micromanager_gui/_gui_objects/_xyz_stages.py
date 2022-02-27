from pathlib import Path

from pymmcore_plus import CMMCorePlus, DeviceType
from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtCore import QSize
from qtpy.QtGui import QIcon

# to add when merging "move_tab_methods_in_tab_widget"
# from _tab_widget import MMTabWidget


ICONS = Path(__file__).parent.parent / "icons"


class MMStagesWidget(QtW.QWidget):

    MM_XYZ_STAGE = str(Path(__file__).parent / "mm_xyz_stage.ui")

    # The MM_XYZ_STAGE above contains these objects:

    XY_groupBox: QtW.QGroupBox
    xy_device_comboBox: QtW.QComboBox
    xy_step_size_SpinBox: QtW.QSpinBox
    y_up_Button: QtW.QPushButton
    y_down_Button: QtW.QPushButton
    left_Button: QtW.QPushButton
    right_Button: QtW.QPushButton

    Z_groupBox: QtW.QGroupBox
    z_step_size_doubleSpinBox: QtW.QDoubleSpinBox
    focus_device_comboBox: QtW.QComboBox
    up_Button: QtW.QPushButton
    down_Button: QtW.QPushButton

    offset_Z_groupBox: QtW.QGroupBox
    offset_device_comboBox: QtW.QComboBox
    offset_z_step_size_doubleSpinBox: QtW.QDoubleSpinBox
    offset_up_Button: QtW.QPushButton
    offset_down_Button: QtW.QPushButton

    x_lineEdit: QtW.QLineEdit
    y_lineEdit: QtW.QLineEdit
    z_lineEdit: QtW.QLineEdit

    snap_on_click_checkBox: QtW.QCheckBox

    def __init__(self, mmc: CMMCorePlus = None):
        super().__init__()

        self._mmc = mmc

        print("mmc_0:", self._mmc)

        self.available_focus_devs = []

        # to add when merging "move_tab_methods_in_tab_widget"
        # self.snap = MMTabWidget.snap()

        sig = self._mmc.events
        sig.XYStagePositionChanged.connect(self._on_xy_stage_position_changed)
        sig.stagePositionChanged.connect(self._on_stage_position_changed)

        uic.loadUi(self.MM_XYZ_STAGE, self)

        self.left_Button.clicked.connect(self.stage_x_left)
        self.right_Button.clicked.connect(self.stage_x_right)
        self.y_up_Button.clicked.connect(self.stage_y_up)
        self.y_down_Button.clicked.connect(self.stage_y_down)
        self.up_Button.clicked.connect(self.stage_z_up)
        self.down_Button.clicked.connect(self.stage_z_down)

        self.focus_device_comboBox.currentTextChanged.connect(self._set_focus_device)

        # button icons
        for attr, icon in [
            ("left_Button", "left_arrow_1_green.svg"),
            ("right_Button", "right_arrow_1_green.svg"),
            ("y_up_Button", "up_arrow_1_green.svg"),
            ("y_down_Button", "down_arrow_1_green.svg"),
            ("up_Button", "up_arrow_1_green.svg"),
            ("down_Button", "down_arrow_1_green.svg"),
            ("offset_up_Button", "up_arrow_1_green.svg"),
            ("offset_down_Button", "down_arrow_1_green.svg"),
        ]:
            btn = getattr(self, attr)
            btn.setIcon(QIcon(str(ICONS / icon)))
            btn.setIconSize(QSize(30, 30))

    def _on_xy_stage_position_changed(self, name, x, y):
        self.x_lineEdit.setText(f"{x:.1f}")
        self.y_lineEdit.setText(f"{y:.1f}")

    def _refresh_positions(self):
        if self._mmc.getXYStageDevice():
            x, y = self._mmc.getXPosition(), self._mmc.getYPosition()
            self._on_xy_stage_position_changed(self._mmc.getXYStageDevice(), x, y)
        if self._mmc.getFocusDevice():
            self.z_lineEdit.setText(f"{self._mmc.getZPosition():.1f}")

    def _refresh_xyz_devices(self):

        print("stageeeeeeeee_4", self._mmc.getXYStageDevice())
        print("mmc_4:", self._mmc)

        # since there is no offset control yet:
        self.offset_Z_groupBox.setEnabled(False)

        self.focus_device_comboBox.clear()
        self.xy_device_comboBox.clear()

        xy_stage_devs = list(self._mmc.getLoadedDevicesOfType(DeviceType.XYStageDevice))

        focus_devs = list(self._mmc.getLoadedDevicesOfType(DeviceType.StageDevice))

        if not xy_stage_devs:
            self.XY_groupBox.setEnabled(False)
        else:
            self.XY_groupBox.setEnabled(True)
            self.xy_device_comboBox.addItems(xy_stage_devs)
            self._set_xy_stage_device()

        if not focus_devs:
            self.Z_groupBox.setEnabled(False)
        else:
            self.Z_groupBox.setEnabled(True)
            self.focus_device_comboBox.addItems(focus_devs)
            self._set_focus_device()

    def _set_xy_stage_device(self):
        if not self.xy_device_comboBox.count():
            return
        self._mmc.setXYStageDevice(self.xy_device_comboBox.currentText())

    def _set_focus_device(self):
        if not self.focus_device_comboBox.count():
            return
        self._mmc.setFocusDevice(self.focus_device_comboBox.currentText())

    def _on_stage_position_changed(self, name, value):
        if "z" in name.lower():  # hack
            self.z_lineEdit.setText(f"{value:.1f}")

    # def _snap(self):
    #     if self.snap_on_click_checkBox.isChecked():
    #         self.snap()

    def stage_x_left(self):
        self._mmc.setRelativeXYPosition(-float(self.xy_step_size_SpinBox.value()), 0.0)
        # self._snap()

    def stage_x_right(self):
        self._mmc.setRelativeXYPosition(float(self.xy_step_size_SpinBox.value()), 0.0)
        # self._snap()

    def stage_y_up(self):
        self._mmc.setRelativeXYPosition(
            0.0,
            float(self.xy_step_size_SpinBox.value()),
        )
        # self._snap()

    def stage_y_down(self):
        self._mmc.setRelativeXYPosition(
            0.0,
            -float(self.xy_step_size_SpinBox.value()),
        )
        # self._snap()

    def stage_z_up(self):
        self._mmc.setRelativePosition(float(self.z_step_size_doubleSpinBox.value()))
        # self._snap()

    def stage_z_down(self):
        self._mmc.setRelativePosition(-float(self.z_step_size_doubleSpinBox.value()))
        # self._snap()


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMStagesWidget()
    win.show()
    sys.exit(app.exec_())
