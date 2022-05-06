from __future__ import annotations

import contextlib
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import napari
import numpy as np
from napari.experimental import link_layers
from pymmcore_plus._util import find_micromanager
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QColor, QIcon
from superqt.utils import ensure_main_thread

from . import _core, _mda
from ._camera_roi import CameraROI
from ._core_widgets import PixelSizeWidget, PropertyBrowser
from ._gui_objects._mm_widget import MicroManagerWidget
from ._gui_objects._stream_cam import CamStream
from ._saving import save_sequence
from ._util import event_indices, extend_array_for_index

if TYPE_CHECKING:
    import napari.layers
    import napari.viewer
    import useq
    from pymmcore_plus.core.events import QCoreSignaler
    from pymmcore_plus.mda import PMDAEngine

ICONS = Path(__file__).parent / "icons"
CAM_ICON = QIcon(str(ICONS / "vcam.svg"))
CAM_STOP_ICON = QIcon(str(ICONS / "cam_stop.svg"))


class MainWindow(MicroManagerWidget):
    def __init__(self, viewer: napari.viewer.Viewer, remote=False):
        super().__init__()

        # create connection to mmcore server or process-local variant
        self._mmc = _core.get_core_singleton(remote)

        self.viewer = viewer

        adapter_path = find_micromanager()
        if not adapter_path:
            raise RuntimeError(
                "Could not find micromanager adapters. Please run "
                "`python -m pymmcore_plus.install` or install manually and set "
                "MICROMANAGER_PATH."
            )

        # add mda and explorer tabs to mm_tab widget
        sizepolicy = QtW.QSizePolicy(
            QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Expanding
        )
        self.tab_wdg.setSizePolicy(sizepolicy)

        self.streaming_timer: QTimer | None = None

        # disable gui
        self._set_enabled(False)

        # connect mmcore signals
        sig: QCoreSignaler = self._mmc.events

        # note: don't use lambdas with closures on `self`, since the connection
        # to core may outlive the lifetime of this particular widget.
        sig.systemConfigurationLoaded.connect(self._on_system_cfg_loaded)
        sig.exposureChanged.connect(self._update_live_exp)

        sig.imageSnapped.connect(self.update_viewer)
        sig.imageSnapped.connect(self._stop_live)

        # mda events
        self._mmc.mda.events.frameReady.connect(self._on_mda_frame)
        self._mmc.mda.events.sequenceStarted.connect(self._on_mda_started)
        self._mmc.mda.events.sequenceFinished.connect(self._on_mda_finished)
        self._mmc.events.mdaEngineRegistered.connect(self._update_mda_engine)

        self._mmc.events.startContinuousSequenceAcquisition.connect(self._start_live)
        self._mmc.events.stopSequenceAcquisition.connect(self._stop_live)

        self.cam_roi = CameraROI(
            self.viewer,
            self._mmc,
            self.tab_wdg.cam_wdg.cam_roi_combo,
            self.tab_wdg.cam_wdg.crop_btn,
        )

        self.viewer.layers.events.connect(self.update_max_min)
        self.viewer.layers.selection.events.active.connect(self.update_max_min)
        self.viewer.dims.events.current_step.connect(self.update_max_min)
        self.viewer.mouse_drag_callbacks.append(self._get_event_explorer)

        self._add_menu()

    def _add_menu(self):
        w = getattr(self.viewer, "__wrapped__", self.viewer).window  # don't do this.
        self._menu = QtW.QMenu("&Micro-Manager", w._qt_window)

        action = self._menu.addAction("Device Property Browser...")
        action.triggered.connect(self._show_prop_browser)

        action_1 = self._menu.addAction("Set Pixel Size...")
        action_1.triggered.connect(self._show_pixel_size_table)

        action_2 = self._menu.addAction("Camera Stream...")
        action_2.triggered.connect(self._show_cam_stream)

        bar = w._qt_window.menuBar()
        bar.insertMenu(list(bar.actions())[-1], self._menu)

    def _show_prop_browser(self):
        if not hasattr(self, "_prop_browser"):
            self._prop_browser = PropertyBrowser(self._mmc, self)
        self._prop_browser.show()
        self._prop_browser.raise_()

    def _show_pixel_size_table(self):
        if len(self._mmc.getLoadedDevices()) <= 1:
            raise Warning("System Configuration not loaded!")
        if not hasattr(self, "_px_size_wdg"):
            self._px_size_wdg = PixelSizeWidget(self._mmc, self)
            self._px_size_wdg.setWindowFlags(
                Qt.Window
                | Qt.WindowTitleHint
                | Qt.WindowStaysOnTopHint
                | Qt.WindowCloseButtonHint
            )
        self._px_size_wdg.show()

    def _show_cam_stream(self):
        if len(self._mmc.getLoadedDevices()) <= 1:
            raise Warning("System Configuration not loaded!")
        if not hasattr(self, "_cam_stream"):
            self._cam_stream = CamStream(self)
            self._cam_stream.cam_event.camStreamData.connect(self._on_cam_stream)
            self._cam_stream.setWindowFlags(
                Qt.Window
                | Qt.WindowTitleHint
                | Qt.WindowStaysOnTopHint
                | Qt.WindowCloseButtonHint
            )
        self._cam_stream.show()

    def _on_cam_stream(self, data: list, n_images: int):
        if not data:
            return

        shape_x, shape_y = data[0][0]
        new_array = np.empty((n_images, shape_x, shape_y))
        for idx, d in enumerate(data):
            img = d[0]
            new_array[idx, :, :] = img
        self.viewer.add_image(new_array)

        for _, meta in reversed(data):
            print(meta.get("ElapsedTime-ms"))

    def _on_system_cfg_loaded(self):
        if len(self._mmc.getLoadedDevices()) > 1:
            self._set_enabled(True)

    def _set_enabled(self, enabled):

        self.tab_wdg.mda._set_enabled(enabled)
        if self._mmc.getXYStageDevice():
            self.tab_wdg.explorer._set_enabled(enabled)
        else:
            self.tab_wdg.explorer._set_enabled(False)

    @ensure_main_thread
    def update_viewer(self, data=None):

        if data is None:
            try:
                data = self._mmc.getLastImage()
            except (RuntimeError, IndexError):
                # circular buffer empty
                return

        x, y = self._translate_preview()

        try:
            preview_layer = self.viewer.layers["preview"]
            preview_layer.data = data
        except KeyError:
            preview_layer = self.viewer.add_image(data, name="preview")

        self.update_max_min()

        if self.streaming_timer is None:
            preview_layer.translate = (y, x)
            self.viewer.reset_view()

        # TODO: use self.viewer.camera.zoom to fix issue
        # when explorer + live mode
        # self.viewer.camera.zoom = 0.5

    def update_max_min(self, event=None):

        if self.tab_wdg.currentIndex() != 0:
            return

        min_max_txt = ""

        for layer in self.viewer.layers.selection:

            if isinstance(layer, napari.layers.Image) and layer.visible:

                col = layer.colormap.name

                if col not in QColor.colorNames():
                    col = "gray"

                # min and max of current slice
                min_max_show = tuple(layer._calc_data_range(mode="slice"))
                min_max_txt += f'<font color="{col}">{min_max_show}</font>'

        self.tab_wdg.max_min_val_label.setText(min_max_txt)

    def _translate_preview(self):
        x = (
            self._mmc.getXPosition() / self._mmc.getPixelSizeUm()
            if self._mmc.getPixelSizeUm() > 0
            else 0
        )
        y = (
            self._mmc.getYPosition() / self._mmc.getPixelSizeUm() * (-1)
            if self._mmc.getPixelSizeUm() > 0
            else 0
        )
        return x, y

    def _start_live(self):
        self.streaming_timer = QTimer()
        self.streaming_timer.timeout.connect(self.update_viewer)
        self.streaming_timer.start(self._mmc.getExposure())

    def _stop_live(self):
        if self.streaming_timer:
            self.streaming_timer.stop()
            self.streaming_timer = None

    def _update_mda_engine(self, newEngine: PMDAEngine, oldEngine: PMDAEngine):
        oldEngine.events.frameReady.connect(self._on_mda_frame)
        oldEngine.events.sequenceStarted.disconnect(self._on_mda_started)
        oldEngine.events.sequenceFinished.disconnect(self._on_mda_finished)

        newEngine.events.frameReady.connect(self._on_mda_frame)
        newEngine.events.sequenceStarted.connect(self._on_mda_started)
        newEngine.events.sequenceFinished.connect(self._on_mda_finished)

    def _on_mda_started(self, sequence: useq.MDASequence):
        """ "create temp folder and block gui when mda starts."""
        # self._set_enabled(False)

        self._mda_meta = _mda.SEQUENCE_META.get(sequence, _mda.SequenceMeta())
        if self._mda_meta.mode == "":
            # originated from user script - assume it's an mda
            self._mda_meta.mode = "mda"

        if self._mda_meta.mode == "explorer":
            with contextlib.suppress(ValueError):
                self.viewer.layers.remove("preview")

    @ensure_main_thread
    def _on_mda_frame(self, image: np.ndarray, event: useq.MDAEvent):

        meta = self._mda_meta
        if meta.mode == "mda":

            # pick layer name
            file_name = meta.file_name if meta.should_save else "Exp"
            channelstr = (
                f"[{event.channel.config}_idx{event.index['c']}]_"
                if meta.split_channels
                else ""
            )
            layer_name = f"{file_name}_{channelstr}{event.sequence.uid}"

            try:  # see if we already have a layer with this sequence
                layer = self.viewer.layers[layer_name]

                # get indices of new image
                im_idx = tuple(
                    event.index[k]
                    for k in event_indices(event)
                    if not (meta.split_channels and k == "c")
                )

                # make sure array shape contains im_idx, or pad with zeros
                new_array = extend_array_for_index(layer.data, im_idx)
                # add the incoming index at the appropriate index
                new_array[im_idx] = image
                # set layer data
                layer.data = new_array
                for a, v in enumerate(im_idx):
                    self.viewer.dims.set_point(a, v)

            except KeyError:  # add the new layer to the viewer
                seq = event.sequence
                _image = image[(np.newaxis,) * len(seq.shape)]
                layer = self.viewer.add_image(
                    _image, name=layer_name, blending="additive"
                )

                # dimensions labels
                labels = [i for i in seq.axis_order if i in event.index] + ["y", "x"]
                self.viewer.dims.axis_labels = labels

                # add metadata to layer
                layer.metadata["useq_sequence"] = seq
                layer.metadata["uid"] = seq.uid
                # storing event.index in addition to channel.config because it's
                # possible to have two of the same channel in one sequence.
                layer.metadata[
                    "ch_id"
                ] = f'{event.channel.config}_idx{event.index["c"]}'
        elif meta.mode == "explorer":

            seq = event.sequence

            meta = _mda.SEQUENCE_META.get(seq) or _mda.SequenceMeta()
            if meta.mode != "explorer":
                return

            x = event.x_pos / self.tab_wdg.explorer.pixel_size
            y = event.y_pos / self.tab_wdg.explorer.pixel_size * (-1)

            pos_idx = event.index["p"]
            file_name = meta.file_name if meta.should_save else "Exp"
            ch_name = event.channel.config
            ch_id = event.index["c"]
            layer_name = f"Pos{pos_idx:03d}_{file_name}_{ch_name}_idx{ch_id}"

            meta = dict(
                useq_sequence=seq,
                uid=seq.uid,
                scan_coord=(y, x),
                scan_position=f"Pos{pos_idx:03d}",
                ch_name=ch_name,
                ch_id=ch_id,
            )
            self.viewer.add_image(
                image,
                name=layer_name,
                blending="additive",
                translate=(y, x),
                metadata=meta,
            )

            zoom_out_factor = (
                self.tab_wdg.explorer.scan_size_r
                if self.tab_wdg.explorer.scan_size_r
                >= self.tab_wdg.explorer.scan_size_c
                else self.tab_wdg.explorer.scan_size_c
            )
            self.viewer.camera.zoom = 1 / zoom_out_factor
            self.viewer.reset_view()

    def _on_mda_finished(self, sequence: useq.MDASequence):
        """Save layer and add increment to save name."""
        meta = _mda.SEQUENCE_META.get(sequence) or _mda.SequenceMeta()
        seq_uid = sequence.uid
        if meta.mode == "explorer":

            layergroups = defaultdict(set)
            for lay in self.viewer.layers:
                if lay.metadata.get("uid") == seq_uid:
                    key = f"{lay.metadata['ch_name']}_idx{lay.metadata['ch_id']}"
                    layergroups[key].add(lay)
            for group in layergroups.values():
                link_layers(group)
        meta = _mda.SEQUENCE_META.pop(sequence, self._mda_meta)
        save_sequence(sequence, self.viewer.layers, meta)
        # reactivate gui when mda finishes.
        self._set_enabled(True)

    def _get_event_explorer(self, viewer, event):
        if not self.tab_wdg.explorer.isVisible():
            return
        if self._mmc.getPixelSizeUm() > 0:
            width = self._mmc.getROI(self._mmc.getCameraDevice())[2]
            height = self._mmc.getROI(self._mmc.getCameraDevice())[3]

            x = viewer.cursor.position[-1] * self._mmc.getPixelSizeUm()
            y = viewer.cursor.position[-2] * self._mmc.getPixelSizeUm() * (-1)

            # to match position coordinates with center of the image
            x = f"{x - ((width / 2) * self._mmc.getPixelSizeUm()):.1f}"
            y = f"{y - ((height / 2) * self._mmc.getPixelSizeUm() * (-1)):.1f}"

        else:
            x, y = "None", "None"

        self.tab_wdg.explorer.x_lineEdit.setText(x)
        self.tab_wdg.explorer.y_lineEdit.setText(y)

    def _update_live_exp(self, camera: str, exposure: float):
        if self.streaming_timer:
            self.streaming_timer.setInterval(int(exposure))
            self._mmc.stopSequenceAcquisition()
            self._mmc.startContinuousSequenceAcquisition(exposure)
