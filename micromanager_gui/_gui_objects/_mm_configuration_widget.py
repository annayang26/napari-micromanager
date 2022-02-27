from typing import TYPE_CHECKING

from qtpy import QtWidgets as QtW

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus, RemoteMMCore


class MMConfigurationWidget(QtW.QWidget):
    """
    Contains the following objects:
    cfg_groupBox: QtW.QGroupBox
    cfg_LineEdit: QtW.QLineEdit
    browse_cfg_Button: QtW.QPushButton
    load_cfg_Button: QtW.QPushButton
    """

    def __init__(self, mmc: CMMCorePlus | RemoteMMCore = None):
        super().__init__()

        self._mmc = mmc

        self.setup_gui()

    def setup_gui(self):

        self.main_layout = QtW.QGridLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        # cfg groupbox in widget
        self.cfg_groupBox = QtW.QGroupBox()
        # self.cfg_groupBox.setMinimumHeight(65)
        self.cfg_groupBox.setTitle("Micro-Manager Configuration")
        self.main_layout.addWidget(self.cfg_groupBox, 0, 0)

        # define camera_groupBox layout
        self.cfg_groupBox_layout = QtW.QGridLayout()
        self.cfg_groupBox_layout.setContentsMargins(5, 9, 5, 3)

        # add to cfg_groupBox layout:
        self.cfg_LineEdit = QtW.QLineEdit()
        self.cfg_LineEdit.setPlaceholderText("MMConfig_demo.cfg")
        self.browse_cfg_Button = QtW.QPushButton(text="...")
        self.load_cfg_Button = QtW.QPushButton(text="Load")
        self.load_cfg_Button.setMinimumWidth(60)
        # widgets in in cfg_groupBox layout
        self.cfg_groupBox_layout.addWidget(self.cfg_LineEdit, 0, 0)
        self.cfg_groupBox_layout.addWidget(self.browse_cfg_Button, 0, 1)
        self.cfg_groupBox_layout.addWidget(self.load_cfg_Button, 0, 2)
        # set cfg_groupBox layout
        self.cfg_groupBox.setLayout(self.cfg_groupBox_layout)

        self.setLayout(self.main_layout)

    def browse_cfg(self):
        (filename, _) = QtW.QFileDialog.getOpenFileName(self, "", "", "cfg(*.cfg)")
        if filename:
            self.cfg_LineEdit.setText(filename)
            self.load_cfg_Button.setEnabled(True)

    def load_cfg(self):

        self._mmc.unloadAllDevices()  # unload all devicies

        self.load_cfg_Button.setEnabled(False)
        cfg = self.cfg_LineEdit.text()
        if cfg == "":
            cfg = "MMConfig_demo.cfg"
        self._mmc.loadSystemConfiguration(cfg)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = MMConfigurationWidget()
    win.show()
    sys.exit(app.exec_())
