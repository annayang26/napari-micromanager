import contextlib
from typing import Optional

from fonticon_mdi6 import MDI6
from pymmcore_plus import CMMCorePlus, DeviceType
from qtpy.QtCore import QSize, Qt
from qtpy.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from superqt.fonticon import icon
from superqt.utils import create_worker

from micromanager_gui._core import get_core_singleton
from micromanager_gui._signals import camStreamEvents


class CamStream(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        mmcore: Optional[CMMCorePlus] = None,
    ):

        super().__init__(parent)

        self._mmc = mmcore or get_core_singleton()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_sys_cfg)

        self.cam_event = camStreamEvents()

        self._lbl_min_width = 125
        self._stopped = False

        self._create_gui()

        self._on_sys_cfg()

        self._mmc.loadSystemConfiguration()

    def _create_gui(self):

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        cam = self._create_cam_wdg()
        layout.addWidget(cam)

        exp = self._create_exposure_wdg()
        layout.addWidget(exp)

        img = self._create_n_images_wdg()
        layout.addWidget(img)

        btns = self._create_start_stop_btn_wdg()
        layout.addWidget(btns)

    def _create_cam_wdg(self):

        wdg = QWidget()
        wdg_layout = QHBoxLayout()
        wdg_layout.setSpacing(5)
        wdg_layout.setContentsMargins(0, 0, 0, 0)
        wdg.setLayout(wdg_layout)

        lbl = QLabel(text="Camera Device:")
        lbl.setMinimumWidth(self._lbl_min_width)
        lbl.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.cam_combo = QComboBox()
        self.cam_combo.currentTextChanged.connect(self._on_cam_changed)
        wdg_layout.addWidget(lbl)
        wdg_layout.addWidget(self.cam_combo)

        return wdg

    def _create_exposure_wdg(self):
        wdg = QWidget()
        wdg_layout = QHBoxLayout()
        wdg_layout.setSpacing(5)
        wdg_layout.setContentsMargins(0, 0, 0, 0)
        wdg.setLayout(wdg_layout)

        lbl = QLabel(text="Exposure Time (ms):")
        lbl.setMinimumWidth(self._lbl_min_width)
        lbl.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))

        self.exp = QDoubleSpinBox()
        self.exp.setAlignment(Qt.AlignCenter)
        self.exp.setMinimum(1.0)
        self.exp.setMaximum(100000.0)
        self.exp.valueChanged.connect(self._set_exposure)

        wdg_layout.addWidget(lbl)
        wdg_layout.addWidget(self.exp)

        return wdg

    def _create_n_images_wdg(self):
        wdg = QWidget()
        wdg_layout = QHBoxLayout()
        wdg_layout.setSpacing(5)
        wdg_layout.setContentsMargins(0, 0, 0, 0)
        wdg.setLayout(wdg_layout)

        lbl = QLabel(text="Number of Images:")
        lbl.setMinimumWidth(self._lbl_min_width)
        lbl.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.n_images = QSpinBox()
        self.n_images.setAlignment(Qt.AlignCenter)
        self.n_images.setMinimum(1)
        self.n_images.setMaximum(100000)

        wdg_layout.addWidget(lbl)
        wdg_layout.addWidget(self.n_images)

        return wdg

    def _create_start_stop_btn_wdg(self):
        wdg = QWidget()
        wdg_layout = QHBoxLayout()
        wdg_layout.setSpacing(5)
        wdg_layout.setContentsMargins(0, 0, 0, 0)
        wdg.setLayout(wdg_layout)

        btn_sizepolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.start = QPushButton(text="Run")
        self.start.setSizePolicy(btn_sizepolicy)
        self.start.setIcon(icon(MDI6.play, color=(0, 255, 0)))
        self.start.setIconSize(QSize(40, 40))
        self.start.clicked.connect(self._on_start)

        self.stop = QPushButton(text="Stop")
        self.stop.setSizePolicy(btn_sizepolicy)
        self.stop.setIcon(icon(MDI6.stop, color="magenta"))
        self.stop.setIconSize(QSize(40, 40))
        self.stop.clicked.connect(self._on_stop)

        wdg_layout.addWidget(self.start)
        wdg_layout.addWidget(self.stop)

        return wdg

    def _on_sys_cfg(self):
        cams = list(self._mmc.getLoadedDevicesOfType(DeviceType.Camera))
        self.cam_combo.addItems(cams)
        self._stopped = False
        self._set_exposure(self.exp.value())

    def _on_cam_changed(self, camera_name: str):
        self._mmc.setCameraDevice(camera_name)

    def _set_exposure(self, value: float):
        if not self._mmc.getCameraDevice():
            return
        self._mmc.setExposure(value)

    def _on_start(self):
        create_worker(self._start_acquisition, _start_thread=True)

    def _start_acquisition(self):
        n_images = self.n_images.value()
        data = []

        self._mmc.startSequenceAcquisition(n_images, 0.0, True)
        while self._mmc.isSequenceRunning():
            if self._stopped:
                self._mmc.stopSequenceAcquisition(self.cam_combo.currentText())
                self._stopped = False
                break

        for i in range(n_images):
            with contextlib.suppress(IndexError):
                img = self._mmc.getNBeforeLastImageMD(i)
                data.append(img)

        # for m in reversed(stack):
        #     print(f"ElapsedTime: {m[1].get('ElapsedTime-ms')}")

        self.cam_event.camStreamData.emit(data, n_images)

    def _on_stop(self):
        self._stopped = True


if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    win = CamStream()
    win.show()
    sys.exit(app.exec_())
