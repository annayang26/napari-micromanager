from pathlib import Path
from typing import Optional

from pymmcore_plus import CMMCorePlus, DeviceType
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from micromanager_gui._core import get_core_singleton

PLATE_DATABASE = Path(__file__).parent / "_well_plate.yaml"
AlignCenter = Qt.AlignmentFlag.AlignCenter


class ChannelPositionWidget(QWidget):
    def __init__(
        self, parent: Optional[QWidget] = None, *, mmcore: Optional[CMMCorePlus] = None
    ):
        super().__init__(parent)

        self._mmc = mmcore or get_core_singleton()

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        z_selector = self._create_z_stage_selector()
        self.layout().addWidget(z_selector)
        pos = self._create_positions_list_wdg()
        self.layout().addWidget(pos)
        ch = self._create_channel_group()
        self.layout().addWidget(ch)
        timelapse = self._create_time_groupBox()
        self.layout().addWidget(timelapse)
        z_stack = self._create_stack_groupBox()
        self.layout().addWidget(z_stack)

        self._mmc.events.systemConfigurationLoaded.connect(self._on_sys_cfg)

        self._on_sys_cfg()

    def _create_z_stage_selector(self):

        z_wdg = QGroupBox(title="Z Stage Selector")
        z_layout = QHBoxLayout()
        z_layout.setSpacing(0)
        z_layout.setContentsMargins(10, 10, 10, 10)
        z_wdg.setLayout(z_layout)
        self.z_combo = QComboBox()
        self.update_stage_combo()
        z_layout.addWidget(self.z_combo)

        return z_wdg

    def _create_positions_list_wdg(self):
        group = QGroupBox(title="Positions")
        group.setMinimumHeight(230)
        group_layout = QVBoxLayout()
        group_layout.setSpacing(10)
        group_layout.setContentsMargins(10, 10, 10, 10)
        group.setLayout(group_layout)

        wdg = QWidget()
        wdg_layout = QHBoxLayout()
        wdg_layout.setSpacing(10)
        wdg_layout.setContentsMargins(0, 0, 0, 0)
        wdg.setLayout(wdg_layout)

        self.position_list_button = QPushButton(text="Create Position List")
        self.remove_position_button = QPushButton(text="Remove Position")
        self.remove_position_button.clicked.connect(self.remove_position)
        self.clear_positions_button = QPushButton(text="Clear List")
        self.clear_positions_button.clicked.connect(self.clear_positions)
        wdg_layout.addWidget(self.position_list_button)
        wdg_layout.addWidget(self.remove_position_button)
        wdg_layout.addWidget(self.clear_positions_button)
        group_layout.addWidget(wdg)

        # table
        self.stage_tableWidget = QTableWidget()
        self.stage_tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.stage_tableWidget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.stage_tableWidget.setMinimumHeight(90)
        hdr = self.stage_tableWidget.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        self.stage_tableWidget.verticalHeader().setVisible(True)
        self.stage_tableWidget.setTabKeyNavigation(True)
        self.stage_tableWidget.setColumnCount(4)
        self.stage_tableWidget.setRowCount(0)
        self.stage_tableWidget.setHorizontalHeaderLabels(["Well", "X", "Y", "Z"])
        group_layout.addWidget(self.stage_tableWidget)

        self.stage_tableWidget.cellDoubleClicked.connect(self.move_to_position)

        assign_z_wdg = QWidget()
        assign_z_wdg_layout = QHBoxLayout()
        assign_z_wdg_layout.setSpacing(5)
        assign_z_wdg_layout.setContentsMargins(0, 0, 0, 0)
        assign_z_wdg.setLayout(assign_z_wdg_layout)
        lbl = QLabel(text="Update the Z value of the selected wells:")
        lbl.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.assign_z = QPushButton(text="Update")
        self.assign_z.clicked.connect(self._assign_to_wells)
        self.z_doublespinbox = QDoubleSpinBox()
        self.z_doublespinbox.setAlignment(Qt.AlignCenter)
        self.z_doublespinbox.setMaximum(1000000)
        assign_z_wdg_layout.addWidget(lbl)
        assign_z_wdg_layout.addWidget(self.z_doublespinbox)
        assign_z_wdg_layout.addWidget(self.assign_z)
        group_layout.addWidget(assign_z_wdg)

        return group

    def _create_channel_group(self):

        group = QGroupBox(title="Channels")
        group.setMinimumHeight(230)
        group_layout = QGridLayout()
        group_layout.setHorizontalSpacing(15)
        group_layout.setVerticalSpacing(0)
        group_layout.setContentsMargins(10, 0, 10, 0)
        group.setLayout(group_layout)

        # table
        self.channel_tableWidget = QTableWidget()
        self.channel_tableWidget.setMinimumHeight(90)
        hdr = self.channel_tableWidget.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        self.channel_tableWidget.verticalHeader().setVisible(False)
        self.channel_tableWidget.setTabKeyNavigation(True)
        self.channel_tableWidget.setColumnCount(2)
        self.channel_tableWidget.setRowCount(0)
        self.channel_tableWidget.setHorizontalHeaderLabels(
            ["Channel", "Exposure Time (ms)"]
        )
        group_layout.addWidget(self.channel_tableWidget, 0, 0, 3, 1)

        # buttons
        btn_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        min_size = 100
        self.add_ch_Button = QPushButton(text="Add")
        self.add_ch_Button.clicked.connect(self.add_channel)
        self.add_ch_Button.setMinimumWidth(min_size)
        self.add_ch_Button.setSizePolicy(btn_sizepolicy)
        self.remove_ch_Button = QPushButton(text="Remove")
        self.remove_ch_Button.clicked.connect(self.remove_channel)
        self.remove_ch_Button.setMinimumWidth(min_size)
        self.remove_ch_Button.setSizePolicy(btn_sizepolicy)
        self.clear_ch_Button = QPushButton(text="Clear")
        self.clear_ch_Button.clicked.connect(self.clear_channel)
        self.clear_ch_Button.setMinimumWidth(min_size)
        self.clear_ch_Button.setSizePolicy(btn_sizepolicy)

        group_layout.addWidget(self.add_ch_Button, 0, 1, 1, 1)
        group_layout.addWidget(self.remove_ch_Button, 1, 1, 1, 2)
        group_layout.addWidget(self.clear_ch_Button, 2, 1, 1, 2)

        return group

    def _create_time_groupBox(self):
        self.time_group = QGroupBox(title="Time")
        self.time_group.setCheckable(True)
        self.time_group.setChecked(False)
        self.time_group.setSizePolicy(
            QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        )
        group_layout = QHBoxLayout()
        group_layout.setSpacing(10)
        group_layout.setContentsMargins(10, 10, 10, 10)
        self.time_group.setLayout(group_layout)

        lbl_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Timepoints
        wdg = QWidget()
        wdg_lay = QHBoxLayout()
        wdg_lay.setSpacing(5)
        wdg_lay.setContentsMargins(0, 0, 0, 0)
        wdg.setLayout(wdg_lay)
        lbl = QLabel(text="Timepoints:")
        lbl.setSizePolicy(lbl_sizepolicy)
        self.timepoints_spinBox = QSpinBox()
        self.timepoints_spinBox.setMinimum(1)
        self.timepoints_spinBox.setMaximum(10000)
        self.timepoints_spinBox.setAlignment(Qt.AlignCenter)
        wdg_lay.addWidget(lbl)
        wdg_lay.addWidget(self.timepoints_spinBox)
        group_layout.addWidget(wdg)

        # Interval
        wdg1 = QWidget()
        wdg1_lay = QHBoxLayout()
        wdg1_lay.setSpacing(5)
        wdg1_lay.setContentsMargins(0, 0, 0, 0)
        wdg1.setLayout(wdg1_lay)
        lbl1 = QLabel(text="Interval:")
        lbl1.setSizePolicy(lbl_sizepolicy)
        self.interval_spinBox = QSpinBox()
        self.interval_spinBox.setMinimum(0)
        self.interval_spinBox.setMaximum(10000)
        self.interval_spinBox.setAlignment(Qt.AlignCenter)
        wdg1_lay.addWidget(lbl1)
        wdg1_lay.addWidget(self.interval_spinBox)
        group_layout.addWidget(wdg1)

        self.time_comboBox = QComboBox()
        self.time_comboBox.setSizePolicy(
            QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        )
        self.time_comboBox.addItems(["ms", "sec", "min"])
        group_layout.addWidget(self.time_comboBox)

        return self.time_group

    def _create_stack_groupBox(self):
        self.stack_group = QGroupBox(title="Z Stacks")
        self.stack_group.setCheckable(True)
        self.stack_group.setChecked(False)
        self.stack_group.setSizePolicy(
            QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        )
        group_layout = QVBoxLayout()
        group_layout.setSpacing(10)
        group_layout.setContentsMargins(10, 10, 10, 10)
        self.stack_group.setLayout(group_layout)

        # tab
        self.z_tabWidget = QTabWidget()
        z_tab_layout = QVBoxLayout()
        z_tab_layout.setSpacing(0)
        z_tab_layout.setContentsMargins(0, 0, 0, 0)
        self.z_tabWidget.setLayout(z_tab_layout)
        group_layout.addWidget(self.z_tabWidget)

        # range around
        ra = QWidget()
        ra_layout = QHBoxLayout()
        ra_layout.setSpacing(10)
        ra_layout.setContentsMargins(10, 10, 10, 10)
        ra.setLayout(ra_layout)

        lbl_range_ra = QLabel(text="Range (µm):")
        lbl_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        lbl_range_ra.setSizePolicy(lbl_sizepolicy)

        self.zrange_spinBox = QSpinBox()
        self.zrange_spinBox.setValue(5)
        self.zrange_spinBox.setAlignment(Qt.AlignCenter)
        self.zrange_spinBox.setMaximum(100000)

        self.range_around_label = QLabel(text="-2.5 µm <- z -> +2.5 µm")
        self.range_around_label.setAlignment(Qt.AlignCenter)

        ra_layout.addWidget(lbl_range_ra)
        ra_layout.addWidget(self.zrange_spinBox)
        ra_layout.addWidget(self.range_around_label)

        self.z_tabWidget.addTab(ra, "RangeAround")

        # above below wdg
        ab = QWidget()
        ab_layout = QGridLayout()
        ab_layout.setContentsMargins(10, 0, 10, 15)
        ab.setLayout(ab_layout)

        lbl_above = QLabel(text="Above (µm):")
        lbl_above.setAlignment(Qt.AlignCenter)
        self.above_doubleSpinBox = QDoubleSpinBox()
        self.above_doubleSpinBox.setAlignment(Qt.AlignCenter)
        self.above_doubleSpinBox.setMinimum(0.05)
        self.above_doubleSpinBox.setMaximum(10000)
        self.above_doubleSpinBox.setSingleStep(0.5)
        self.above_doubleSpinBox.setDecimals(2)

        lbl_below = QLabel(text="Below (µm):")
        lbl_below.setAlignment(Qt.AlignCenter)
        self.below_doubleSpinBox = QDoubleSpinBox()
        self.below_doubleSpinBox.setAlignment(Qt.AlignCenter)
        self.below_doubleSpinBox.setMinimum(0.05)
        self.below_doubleSpinBox.setMaximum(10000)
        self.below_doubleSpinBox.setSingleStep(0.5)
        self.below_doubleSpinBox.setDecimals(2)

        lbl_range = QLabel(text="Range (µm):")
        lbl_range.setAlignment(Qt.AlignCenter)
        self.z_range_abovebelow_doubleSpinBox = QDoubleSpinBox()
        self.z_range_abovebelow_doubleSpinBox.setAlignment(Qt.AlignCenter)
        self.z_range_abovebelow_doubleSpinBox.setMaximum(10000000)
        self.z_range_abovebelow_doubleSpinBox.setButtonSymbols(
            QAbstractSpinBox.NoButtons
        )
        self.z_range_abovebelow_doubleSpinBox.setReadOnly(True)

        ab_layout.addWidget(lbl_above, 0, 0)
        ab_layout.addWidget(self.above_doubleSpinBox, 1, 0)
        ab_layout.addWidget(lbl_below, 0, 1)
        ab_layout.addWidget(self.below_doubleSpinBox, 1, 1)
        ab_layout.addWidget(lbl_range, 0, 2)
        ab_layout.addWidget(self.z_range_abovebelow_doubleSpinBox, 1, 2)

        self.z_tabWidget.addTab(ab, "AboveBelow")

        # z stage and step size
        step_wdg = QWidget()
        step_wdg_layout = QHBoxLayout()
        step_wdg_layout.setSpacing(15)
        step_wdg_layout.setContentsMargins(0, 10, 0, 0)
        step_wdg.setLayout(step_wdg_layout)

        s = QWidget()
        s_layout = QHBoxLayout()
        s_layout.setSpacing(0)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s.setLayout(s_layout)
        lbl = QLabel(text="Step Size (µm):")
        lbl_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        lbl.setSizePolicy(lbl_sizepolicy)
        self.step_size_doubleSpinBox = QDoubleSpinBox()
        self.step_size_doubleSpinBox.setAlignment(Qt.AlignCenter)
        self.step_size_doubleSpinBox.setMinimum(0.05)
        self.step_size_doubleSpinBox.setMaximum(10000)
        self.step_size_doubleSpinBox.setSingleStep(0.5)
        self.step_size_doubleSpinBox.setDecimals(2)
        s_layout.addWidget(lbl)
        s_layout.addWidget(self.step_size_doubleSpinBox)

        self.n_images_label = QLabel(text="Number of Images: 101")

        step_wdg_layout.addWidget(s)
        step_wdg_layout.addWidget(self.n_images_label)
        group_layout.addWidget(step_wdg)

        # connect
        self.zrange_spinBox.valueChanged.connect(self._update_rangearound_label)
        self.above_doubleSpinBox.valueChanged.connect(self._update_abovebelow_range)
        self.below_doubleSpinBox.valueChanged.connect(self._update_abovebelow_range)
        self.z_range_abovebelow_doubleSpinBox.valueChanged.connect(
            self._update_n_images
        )
        self.zrange_spinBox.valueChanged.connect(self._update_n_images)
        self.step_size_doubleSpinBox.valueChanged.connect(self._update_n_images)
        self.z_tabWidget.currentChanged.connect(self._update_n_images)
        self.stack_group.toggled.connect(self._update_n_images)

        return self.stack_group

    def _on_sys_cfg(self):
        self.clear_channel()
        self.clear_positions()
        self.update_stage_combo()

    def update_stage_combo(self):
        self.z_combo.clear()
        items = list(self._mmc.getLoadedDevicesOfType(DeviceType.Stage))
        items.append("None")
        self.z_combo.addItems(items)

    def remove_position(self):
        rows = {r.row() for r in self.stage_tableWidget.selectedIndexes()}
        for idx in sorted(rows, reverse=True):
            self.stage_tableWidget.removeRow(idx)

    def clear_positions(self):
        self.stage_tableWidget.clearContents()
        self.stage_tableWidget.setRowCount(0)

    def move_to_position(self):
        if not self._mmc.getXYStageDevice():
            return
        curr_row = self.stage_tableWidget.currentRow()
        x_val = self.stage_tableWidget.item(curr_row, 1).text()
        y_val = self.stage_tableWidget.item(curr_row, 2).text()
        if z_item := self.stage_tableWidget.item(curr_row, 3):
            z_val = z_item.text()
            self._mmc.setXYPosition(float(x_val), float(y_val))
            self._mmc.setPosition(self._mmc.getFocusDevice(), float(z_val))

    def add_channel(self) -> bool:
        if len(self._mmc.getLoadedDevices()) <= 1:
            return False

        channel_group = self._mmc.getChannelGroup()
        if not channel_group:
            return

        idx = self.channel_tableWidget.rowCount()
        self.channel_tableWidget.insertRow(idx)

        # create a combo_box for channels in the table
        channel_comboBox = QComboBox(self)
        channel_exp_spinBox = QSpinBox(self)
        channel_exp_spinBox.setRange(0, 10000)
        channel_exp_spinBox.setValue(100)

        if channel_group := self._mmc.getChannelGroup():
            channel_list = list(self._mmc.getAvailableConfigs(channel_group))
            channel_comboBox.addItems(channel_list)

        self.channel_tableWidget.setCellWidget(idx, 0, channel_comboBox)
        self.channel_tableWidget.setCellWidget(idx, 1, channel_exp_spinBox)
        return True

    def remove_channel(self):
        rows = {r.row() for r in self.channel_tableWidget.selectedIndexes()}
        for idx in sorted(rows, reverse=True):
            self.channel_tableWidget.removeRow(idx)

    def clear_channel(self):
        self.channel_tableWidget.clearContents()
        self.channel_tableWidget.setRowCount(0)

    def _update_rangearound_label(self, value):
        self.range_around_label.setText(f"-{value/2} µm <- z -> +{value/2} µm")

    def _update_abovebelow_range(self):
        self.z_range_abovebelow_doubleSpinBox.setValue(
            self.above_doubleSpinBox.value() + self.below_doubleSpinBox.value()
        )

    def _update_n_images(self):
        step = self.step_size_doubleSpinBox.value()
        # set what is the range to consider depending on the z_stack mode
        if self.z_tabWidget.currentIndex() == 0:
            _range = self.zrange_spinBox.value()
        if self.z_tabWidget.currentIndex() == 1:
            _range = self.z_range_abovebelow_doubleSpinBox.value()

        self.n_images_label.setText(f"Number of Images: {round((_range / step) + 1)}")

    def _assign_to_wells(self):
        if self.z_combo.currentText() == "None":
            return
        rows = {r.row() for r in self.stage_tableWidget.selectedIndexes()}
        for row in rows:
            item = QTableWidgetItem(str(self.z_doublespinbox.value()))
            item.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
            self.stage_tableWidget.setItem(row, 3, item)


if __name__ == "__main__":

    app = QApplication([])
    window = ChannelPositionWidget()
    window.show()
    app.exec_()
