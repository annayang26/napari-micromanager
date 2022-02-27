from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pymmcore_plus import DeviceType
from qtpy import QtCore, QtGui
from qtpy import QtWidgets as QtW
from qtpy.QtCore import QSize
from qtpy.QtGui import QIcon

from ._tab_widget import MMTabWidget

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus, RemoteMMCore


ICONS = Path(__file__).parent.parent / "icons"


class MMStagesWidget(QtW.QWidget):
    """
    Contains the following objects:

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
    """

    def __init__(self, mmc: CMMCorePlus | RemoteMMCore = None):
        super().__init__()

        self._mmc = mmc

        self.setup_gui()

        print("mmc_stages:", self._mmc)
        print("XY_stage_stages", self._mmc.getXYStageDevice())

        self.snap = MMTabWidget.snap()

        sig = self._mmc.events
        sig.XYStagePositionChanged.connect(self._on_xy_stage_position_changed)
        sig.stagePositionChanged.connect(self._on_stage_position_changed)

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

    def setup_gui(self):

        self.gridLayout = QtW.QGridLayout()
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.XY_groupBox = QtW.QGroupBox()
        self.XY_groupBox.setTitle("XY Control")
        self.XY_groupBox.setEnabled(True)
        sizePolicy = QtW.QSizePolicy(
            QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.XY_groupBox.sizePolicy().hasHeightForWidth())
        self.XY_groupBox.setSizePolicy(sizePolicy)
        self.XY_groupBox.setMinimumSize(QtCore.QSize(180, 0))
        self.XY_groupBox.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.XY_groupBox.setObjectName("XY_groupBox")
        self.verticalLayout_3 = QtW.QVBoxLayout(self.XY_groupBox)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.xy_device_comboBox = QtW.QComboBox(self.XY_groupBox)
        self.xy_device_comboBox.setMinimumSize(QtCore.QSize(0, 25))
        self.xy_device_comboBox.setMaximumSize(QtCore.QSize(16777215, 25))
        self.xy_device_comboBox.setObjectName("xy_device_comboBox")
        self.verticalLayout_3.addWidget(self.xy_device_comboBox)
        self.horizontalLayout = QtW.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtW.QSpacerItem(
            40, 20, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout.addItem(spacerItem)
        self.y_up_Button = QtW.QPushButton(self.XY_groupBox)
        self.y_up_Button.setEnabled(True)
        self.y_up_Button.setMaximumSize(QtCore.QSize(30, 20))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(179, 179, 179))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(179, 179, 179))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(179, 179, 179))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        self.y_up_Button.setPalette(palette)
        self.y_up_Button.setText("")
        self.y_up_Button.setObjectName("y_up_Button")
        self.horizontalLayout.addWidget(self.y_up_Button)
        spacerItem1 = QtW.QSpacerItem(
            40, 20, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout.addItem(spacerItem1)
        self.verticalLayout_3.addLayout(self.horizontalLayout)
        self.horizontalLayout_9 = QtW.QHBoxLayout()
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.left_Button = QtW.QPushButton(self.XY_groupBox)
        self.left_Button.setEnabled(True)
        sizePolicy = QtW.QSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.left_Button.sizePolicy().hasHeightForWidth())
        self.left_Button.setSizePolicy(sizePolicy)
        self.left_Button.setMinimumSize(QtCore.QSize(20, 30))
        self.left_Button.setMaximumSize(QtCore.QSize(20, 30))
        self.left_Button.setText("")
        self.left_Button.setObjectName("left_Button")
        self.horizontalLayout_9.addWidget(self.left_Button)
        self.xy_step_size_SpinBox = QtW.QSpinBox(self.XY_groupBox)
        self.xy_step_size_SpinBox.setEnabled(True)
        sizePolicy = QtW.QSizePolicy(QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.xy_step_size_SpinBox.sizePolicy().hasHeightForWidth()
        )
        self.xy_step_size_SpinBox.setSizePolicy(sizePolicy)
        self.xy_step_size_SpinBox.setMinimumSize(QtCore.QSize(100, 30))
        self.xy_step_size_SpinBox.setMaximumSize(QtCore.QSize(16777215, 30))
        self.xy_step_size_SpinBox.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.xy_step_size_SpinBox.setAlignment(QtCore.Qt.AlignCenter)
        self.xy_step_size_SpinBox.setButtonSymbols(QtW.QAbstractSpinBox.PlusMinus)
        self.xy_step_size_SpinBox.setProperty("showGroupSeparator", False)
        self.xy_step_size_SpinBox.setMinimum(0)
        self.xy_step_size_SpinBox.setMaximum(10000)
        self.xy_step_size_SpinBox.setProperty("value", 100)
        self.xy_step_size_SpinBox.setObjectName("xy_step_size_SpinBox")
        self.horizontalLayout_9.addWidget(self.xy_step_size_SpinBox)
        self.right_Button = QtW.QPushButton(self.XY_groupBox)
        self.right_Button.setEnabled(True)
        sizePolicy = QtW.QSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.right_Button.sizePolicy().hasHeightForWidth())
        self.right_Button.setSizePolicy(sizePolicy)
        self.right_Button.setMinimumSize(QtCore.QSize(20, 30))
        self.right_Button.setMaximumSize(QtCore.QSize(20, 30))
        self.right_Button.setText("")
        self.right_Button.setObjectName("right_Button")
        self.horizontalLayout_9.addWidget(self.right_Button)
        self.verticalLayout_3.addLayout(self.horizontalLayout_9)
        self.horizontalLayout_4 = QtW.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        spacerItem2 = QtW.QSpacerItem(
            40, 20, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout_4.addItem(spacerItem2)
        self.y_down_Button = QtW.QPushButton(self.XY_groupBox)
        self.y_down_Button.setEnabled(True)
        self.y_down_Button.setMaximumSize(QtCore.QSize(30, 20))
        self.y_down_Button.setText("")
        self.y_down_Button.setObjectName("y_down_Button")
        self.horizontalLayout_4.addWidget(self.y_down_Button)
        spacerItem3 = QtW.QSpacerItem(
            40, 20, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout_4.addItem(spacerItem3)
        self.verticalLayout_3.addLayout(self.horizontalLayout_4)
        self.gridLayout.addWidget(self.XY_groupBox, 0, 0, 1, 1)
        self.Z_groupBox = QtW.QGroupBox()
        self.Z_groupBox.setTitle("Z Control")
        self.Z_groupBox.setEnabled(True)
        sizePolicy = QtW.QSizePolicy(
            QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Z_groupBox.sizePolicy().hasHeightForWidth())
        self.Z_groupBox.setSizePolicy(sizePolicy)
        self.Z_groupBox.setMinimumSize(QtCore.QSize(170, 0))
        self.Z_groupBox.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.Z_groupBox.setObjectName("Z_groupBox")
        self.gridLayout_2 = QtW.QGridLayout(self.Z_groupBox)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.focus_device_comboBox = QtW.QComboBox(self.Z_groupBox)
        self.focus_device_comboBox.setMinimumSize(QtCore.QSize(0, 25))
        self.focus_device_comboBox.setMaximumSize(QtCore.QSize(16777215, 25))
        self.focus_device_comboBox.setObjectName("focus_device_comboBox")
        self.gridLayout_2.addWidget(self.focus_device_comboBox, 0, 0, 1, 1)
        self.horizontalLayout_6 = QtW.QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        spacerItem4 = QtW.QSpacerItem(
            40, 20, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout_6.addItem(spacerItem4)
        self.up_Button = QtW.QPushButton(self.Z_groupBox)
        self.up_Button.setEnabled(True)
        self.up_Button.setMaximumSize(QtCore.QSize(30, 20))
        self.up_Button.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.up_Button.setAutoFillBackground(False)
        self.up_Button.setText("")
        self.up_Button.setObjectName("up_Button")
        self.horizontalLayout_6.addWidget(self.up_Button)
        spacerItem5 = QtW.QSpacerItem(
            40, 20, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout_6.addItem(spacerItem5)
        self.gridLayout_2.addLayout(self.horizontalLayout_6, 1, 0, 1, 1)
        self.horizontalLayout_2 = QtW.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        spacerItem6 = QtW.QSpacerItem(
            18, 20, QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout_2.addItem(spacerItem6)
        self.z_step_size_doubleSpinBox = QtW.QDoubleSpinBox(self.Z_groupBox)
        self.z_step_size_doubleSpinBox.setEnabled(True)
        sizePolicy = QtW.QSizePolicy(QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.z_step_size_doubleSpinBox.sizePolicy().hasHeightForWidth()
        )
        self.z_step_size_doubleSpinBox.setSizePolicy(sizePolicy)
        self.z_step_size_doubleSpinBox.setMinimumSize(QtCore.QSize(100, 30))
        self.z_step_size_doubleSpinBox.setMaximumSize(QtCore.QSize(16777215, 30))
        self.z_step_size_doubleSpinBox.setAlignment(QtCore.Qt.AlignCenter)
        self.z_step_size_doubleSpinBox.setButtonSymbols(QtW.QAbstractSpinBox.PlusMinus)
        self.z_step_size_doubleSpinBox.setProperty("showGroupSeparator", False)
        self.z_step_size_doubleSpinBox.setMaximum(10000.0)
        self.z_step_size_doubleSpinBox.setSingleStep(0.1)
        self.z_step_size_doubleSpinBox.setProperty("value", 1.0)
        self.z_step_size_doubleSpinBox.setObjectName("z_step_size_doubleSpinBox")
        self.horizontalLayout_2.addWidget(self.z_step_size_doubleSpinBox)
        spacerItem7 = QtW.QSpacerItem(
            18, 20, QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout_2.addItem(spacerItem7)
        self.gridLayout_2.addLayout(self.horizontalLayout_2, 2, 0, 1, 1)
        self.horizontalLayout_5 = QtW.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        spacerItem8 = QtW.QSpacerItem(
            40, 20, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout_5.addItem(spacerItem8)
        self.down_Button = QtW.QPushButton(self.Z_groupBox)
        self.down_Button.setEnabled(True)
        self.down_Button.setMaximumSize(QtCore.QSize(30, 20))
        self.down_Button.setText("")
        self.down_Button.setObjectName("down_Button")
        self.horizontalLayout_5.addWidget(self.down_Button)
        spacerItem9 = QtW.QSpacerItem(
            40, 20, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout_5.addItem(spacerItem9)
        self.gridLayout_2.addLayout(self.horizontalLayout_5, 3, 0, 1, 1)
        self.gridLayout.addWidget(self.Z_groupBox, 0, 1, 1, 1)
        self.offset_Z_groupBox = QtW.QGroupBox()
        self.offset_Z_groupBox.setTitle("Z Offset")
        self.offset_Z_groupBox.setEnabled(True)
        sizePolicy = QtW.QSizePolicy(
            QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.offset_Z_groupBox.sizePolicy().hasHeightForWidth()
        )
        self.offset_Z_groupBox.setSizePolicy(sizePolicy)
        self.offset_Z_groupBox.setMinimumSize(QtCore.QSize(170, 0))
        self.offset_Z_groupBox.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.offset_Z_groupBox.setObjectName("offset_Z_groupBox")
        self.gridLayout_3 = QtW.QGridLayout(self.offset_Z_groupBox)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.offset_device_comboBox = QtW.QComboBox(self.offset_Z_groupBox)
        self.offset_device_comboBox.setMinimumSize(QtCore.QSize(0, 25))
        self.offset_device_comboBox.setMaximumSize(QtCore.QSize(16777215, 25))
        self.offset_device_comboBox.setObjectName("offset_device_comboBox")
        self.gridLayout_3.addWidget(self.offset_device_comboBox, 0, 0, 1, 1)
        self.horizontalLayout_7 = QtW.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        spacerItem10 = QtW.QSpacerItem(
            40, 20, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout_7.addItem(spacerItem10)
        self.offset_up_Button = QtW.QPushButton(self.offset_Z_groupBox)
        self.offset_up_Button.setEnabled(True)
        self.offset_up_Button.setMaximumSize(QtCore.QSize(30, 20))
        self.offset_up_Button.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.offset_up_Button.setAutoFillBackground(False)
        self.offset_up_Button.setText("")
        self.offset_up_Button.setObjectName("offset_up_Button")
        self.horizontalLayout_7.addWidget(self.offset_up_Button)
        spacerItem11 = QtW.QSpacerItem(
            40, 20, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout_7.addItem(spacerItem11)
        self.gridLayout_3.addLayout(self.horizontalLayout_7, 1, 0, 1, 1)
        self.horizontalLayout_3 = QtW.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        spacerItem12 = QtW.QSpacerItem(
            18, 20, QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout_3.addItem(spacerItem12)
        self.offset_z_step_size_doubleSpinBox = QtW.QDoubleSpinBox(
            self.offset_Z_groupBox
        )
        self.offset_z_step_size_doubleSpinBox.setEnabled(True)
        sizePolicy = QtW.QSizePolicy(QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.offset_z_step_size_doubleSpinBox.sizePolicy().hasHeightForWidth()
        )
        self.offset_z_step_size_doubleSpinBox.setSizePolicy(sizePolicy)
        self.offset_z_step_size_doubleSpinBox.setMinimumSize(QtCore.QSize(100, 30))
        self.offset_z_step_size_doubleSpinBox.setMaximumSize(QtCore.QSize(16777215, 30))
        self.offset_z_step_size_doubleSpinBox.setAlignment(QtCore.Qt.AlignCenter)
        self.offset_z_step_size_doubleSpinBox.setButtonSymbols(
            QtW.QAbstractSpinBox.PlusMinus
        )
        self.offset_z_step_size_doubleSpinBox.setProperty("showGroupSeparator", False)
        self.offset_z_step_size_doubleSpinBox.setMaximum(10000.0)
        self.offset_z_step_size_doubleSpinBox.setSingleStep(0.1)
        self.offset_z_step_size_doubleSpinBox.setProperty("value", 1.0)
        self.offset_z_step_size_doubleSpinBox.setObjectName(
            "offset_z_step_size_doubleSpinBox"
        )
        self.horizontalLayout_3.addWidget(self.offset_z_step_size_doubleSpinBox)
        spacerItem13 = QtW.QSpacerItem(
            18, 20, QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout_3.addItem(spacerItem13)
        self.gridLayout_3.addLayout(self.horizontalLayout_3, 2, 0, 1, 1)
        self.horizontalLayout_8 = QtW.QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        spacerItem14 = QtW.QSpacerItem(
            40, 20, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout_8.addItem(spacerItem14)
        self.offset_down_Button = QtW.QPushButton(self.offset_Z_groupBox)
        self.offset_down_Button.setEnabled(True)
        self.offset_down_Button.setMaximumSize(QtCore.QSize(30, 20))
        self.offset_down_Button.setText("")
        self.offset_down_Button.setObjectName("offset_down_Button")
        self.horizontalLayout_8.addWidget(self.offset_down_Button)
        spacerItem15 = QtW.QSpacerItem(
            40, 20, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Minimum
        )
        self.horizontalLayout_8.addItem(spacerItem15)
        self.gridLayout_3.addLayout(self.horizontalLayout_8, 3, 0, 1, 1)
        self.gridLayout.addWidget(self.offset_Z_groupBox, 0, 2, 1, 1)
        self.gridLayout_8 = QtW.QGridLayout()
        self.gridLayout_8.setObjectName("gridLayout_8")
        self.y_lineEdit = QtW.QLineEdit()
        self.y_lineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.y_lineEdit.setReadOnly(True)
        self.y_lineEdit.setObjectName("y_lineEdit")
        self.gridLayout_8.addWidget(self.y_lineEdit, 0, 5, 1, 1)
        self.label_8 = QtW.QLabel()
        self.label_8.setText("y:")
        self.label_8.setObjectName("label_8")
        sizePolicy = QtW.QSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_8.sizePolicy().hasHeightForWidth())
        self.label_8.setSizePolicy(sizePolicy)
        self.label_8.setObjectName("label_8")
        self.gridLayout_8.addWidget(self.label_8, 0, 3, 1, 1)
        self.z_lineEdit = QtW.QLineEdit()
        self.z_lineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.z_lineEdit.setReadOnly(True)
        self.z_lineEdit.setObjectName("z_lineEdit")
        self.gridLayout_8.addWidget(self.z_lineEdit, 0, 7, 1, 1)
        self.label_9 = QtW.QLabel()
        self.label_9.setText("z:")
        sizePolicy = QtW.QSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_9.sizePolicy().hasHeightForWidth())
        self.label_9.setSizePolicy(sizePolicy)
        self.label_9.setObjectName("label_9")
        self.gridLayout_8.addWidget(self.label_9, 0, 6, 1, 1)
        self.x_lineEdit = QtW.QLineEdit()
        self.x_lineEdit.setEnabled(True)
        self.x_lineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.x_lineEdit.setReadOnly(True)
        self.x_lineEdit.setObjectName("x_lineEdit")
        self.gridLayout_8.addWidget(self.x_lineEdit, 0, 2, 1, 1)
        self.label_7 = QtW.QLabel()
        self.label_7.setText("x:")
        sizePolicy = QtW.QSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_7.sizePolicy().hasHeightForWidth())
        self.label_7.setSizePolicy(sizePolicy)
        self.label_7.setObjectName("label_7")
        self.gridLayout_8.addWidget(self.label_7, 0, 1, 1, 1)
        self.snap_on_click_checkBox = QtW.QCheckBox()
        self.snap_on_click_checkBox.setText("snap on click")
        self.snap_on_click_checkBox.setObjectName("snap_on_click_checkBox")
        self.gridLayout_8.addWidget(self.snap_on_click_checkBox, 0, 8, 1, 1)
        self.gridLayout.addLayout(self.gridLayout_8, 1, 0, 1, 3)

        self.setLayout(self.gridLayout)

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

        print("mmc_stages_refresh:", self._mmc)
        print("XY_stage_stages_refresh", self._mmc.getXYStageDevice())

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

    def _snap(self):
        if self.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_x_left(self):
        self._mmc.setRelativeXYPosition(-float(self.xy_step_size_SpinBox.value()), 0.0)
        self._snap()

    def stage_x_right(self):
        self._mmc.setRelativeXYPosition(float(self.xy_step_size_SpinBox.value()), 0.0)
        self._snap()

    def stage_y_up(self):
        self._mmc.setRelativeXYPosition(
            0.0,
            float(self.xy_step_size_SpinBox.value()),
        )
        self._snap()

    def stage_y_down(self):
        self._mmc.setRelativeXYPosition(
            0.0,
            -float(self.xy_step_size_SpinBox.value()),
        )
        self._snap()

    def stage_z_up(self):
        self._mmc.setRelativePosition(float(self.z_step_size_doubleSpinBox.value()))
        self._snap()

    def stage_z_down(self):
        self._mmc.setRelativePosition(-float(self.z_step_size_doubleSpinBox.value()))
        self._snap()


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMStagesWidget()
    win.show()
    sys.exit(app.exec_())
