from qtpy import QtWidgets as QtW

policy_max = QtW.QSizePolicy.Policy.Maximum


class MMCameraWidget(QtW.QWidget):
    """A Widget to control camera ROI and pixel size."""

    def __init__(self):
        super().__init__()

        self.cam_roi_combo = QtW.QComboBox()
        self.crop_btn = QtW.QPushButton("Crop")

        roi_label = QtW.QLabel("Camera ROI:")
        roi_label.setSizePolicy(policy_max, policy_max)

        layout = QtW.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(roi_label)
        layout.addWidget(self.cam_roi_combo)
        layout.addWidget(self.crop_btn)
        self.setLayout(layout)

    def setEnabled(self, enabled: bool) -> None:
        self.cam_roi_combo.setEnabled(enabled)
        self.crop_btn.setEnabled(enabled)
