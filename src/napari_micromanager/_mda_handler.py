import contextlib
import os
import tempfile
import time
from collections import deque
from typing import Any, Generator, MutableMapping

import napari.viewer
import numpy as np
from fsspec import FSMap
from napari.layers import Image
from numpy import ndarray
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda.handlers import OMEZarrWriter
from pymmcore_widgets.useq_widgets._mda_sequence import PYMMCW_METADATA_KEY
from superqt.utils import create_worker, ensure_main_thread
from useq import MDAEvent, MDASequence

POS_PREFIX = "p"
EXP = "experiment"


class _MDAHandler(OMEZarrWriter):
    def __init__(
        self,
        viewer: napari.viewer.Viewer,
        store: MutableMapping | str | os.PathLike | FSMap | None = None,
        *,
        overwrite: bool = True,
        mmcore: CMMCorePlus | None = None,
        **kwargs: Any,
    ) -> None:

        self.tmp: tempfile.TemporaryDirectory | None = None
        if store is None:
            self.tmp = tempfile.TemporaryDirectory()
            store = self.tmp.name

        super().__init__(store=store, overwrite=overwrite, **kwargs)

        print()
        print("_________________")
        print(store)
        print("_________________")

        self.viewer = viewer

        self._mmc = mmcore or CMMCorePlus.instance()

        self._deck: deque[tuple[np.ndarray, MDAEvent, dict]] = deque()
        self._largest_idx: dict[str, tuple[int, ...]] = {}
        self._fname: str = ""
        self._mda_running: bool = False

        self._mmc.mda.events.sequenceStarted.connect(self.sequenceStarted)
        self._mmc.mda.events.sequenceFinished.connect(self.sequenceFinished)
        self._mmc.mda.events.frameReady.connect(self.frameReady)

    def _cleanup(self) -> None:
        with contextlib.suppress(TypeError, RuntimeError):
            self._disconnect()
        if self.tmp is not None:
            with contextlib.suppress(NotADirectoryError):
                self.tmp.cleanup()

    def _disconnect(self) -> None:
        self._mmc.mda.events.sequenceStarted.disconnect(self.sequenceStarted)
        self._mmc.mda.events.sequenceFinished.disconnect(self.sequenceFinished)
        self._mmc.mda.events.frameReady.disconnect(self.frameReady)

    def sequenceStarted(self, sequence: MDASequence) -> None:
        self._group.clear()
        self.position_arrays.clear()

        super().sequenceStarted(sequence)

        self._mmc.mda.toggle_pause()
        print("___________PAUSED___________")

        self._fname = self._get_file_name_from_metadata(sequence.metadata)

        # create the arrays and layers
        for pos, sizes in enumerate(self.position_sizes):
            fname = f"{self._fname}_{POS_PREFIX}{pos}"
            self._create_arrays_and_layers(fname, sizes)
            self._largest_idx[fname] = (-1,)

        self._deck = deque()
        self._mda_running = True

        self._io_t = create_worker(
            self._watch_mda,
            _start_thread=True,
            _connect={"yielded": self._update_viewer},
        )

        self._mmc.mda.toggle_pause()
        print("___________UNPAUSED___________")

    def _create_arrays_and_layers(self, fname: str, sizes: dict[str, int]) -> None:
        _dtype = np.dtype(f"u{self._mmc.getBytesPerPixel()}")
        x, y = (self._mmc.getImageWidth(), self._mmc.getImageHeight())

        sz = sizes.copy()
        sz["y"], sz["x"] = x, y
        _dtype = np.dtype(f"u{self._mmc.getBytesPerPixel()}")
        # create the new array
        self.position_arrays[fname] = self.new_array(fname, _dtype, sz)
        # get the scale for the layer
        scale = self._get_scale(fname)
        # add the new array to the viewer
        self.viewer.add_image(
            self.position_arrays[fname],
            name=fname,
            blending="opaque",
            visible=False,
            scale=scale,
        )

    def _get_file_name_from_metadata(self, metadata: dict) -> str:
        """Get the file name from the MDASequence metadata."""
        meta = metadata.get(PYMMCW_METADATA_KEY)
        fname = "" if meta is None else meta.get("save_name", "")
        return fname or EXP

    def _get_scale(self, fname: str) -> list[float]:
        """Get the scale for the layer."""
        if self.current_sequence is None:
            raise ValueError("Not a MDA sequence.")

        # add Z to layer scale
        arr = self.position_arrays[fname]
        if (pix_size := self._mmc.getPixelSizeUm()) != 0:
            scale = [1.0] * (arr.ndim - 2) + [pix_size] * 2
            if (index := self.current_sequence.used_axes.find("z")) > -1:
                scale[index] = getattr(self.current_sequence.z_plan, "step", 1)
        else:
            # return to default
            scale = [1.0, 1.0]
        return scale

    def frameReady(self, frame: ndarray, event: MDAEvent, meta: dict) -> None:
        self._deck.append((frame, event, meta))

    def _watch_mda(
        self,
    ) -> Generator[tuple[tuple[int, ...] | None, Image], None, None]:
        """Watch the MDA for new frames and process them as they come in."""
        while self._mda_running:
            if self._deck:
                index, layer = self._process_frame(*self._deck.pop())
                yield index, layer
            else:
                time.sleep(0.1)

    def _process_frame(
        self, frame: np.ndarray, event: MDAEvent, meta: dict
    ) -> tuple[tuple[int, ...] | None, Image]:

        p_index = event.index.get("p", 0)
        key = f"{POS_PREFIX}{p_index}"
        fname = f"{self._fname}_{key}"

        ary = self.position_arrays[fname]
        pos_sizes = self.position_sizes[p_index]

        index = tuple(event.index[k] for k in pos_sizes)
        self.write_frame(ary, index, frame)
        self.store_frame_metadata(fname, event, meta)

        if index > self._largest_idx[fname]:
            self._largest_idx[fname] = index
            return index, self.viewer.layers[fname]

        return None, self.viewer.layers[fname]

    @ensure_main_thread  # type: ignore [misc]
    def _update_viewer(self, args: tuple[tuple[int, ...] | None, Image]) -> None:
        index, layer = args

        if not layer.visible:
            layer.visible = True

        if index is None:
            return

        if self._mda_running:
            # update the slider position
            cs = list(self.viewer.dims.current_step)
            for a, v in enumerate(index):
                cs[a] = v
            self.viewer.dims.current_step = cs

    def sequenceFinished(self, sequence: MDASequence) -> None:
        self._mda_running = False
        self.finalize_metadata()

        self._reset_viewer_dims()
        while self._deck:
            self._process_frame(*self._deck.pop())

        self.frame_metadatas.clear()
        self.current_sequence = None
        self._fname = ""

        print()
        print("_________________")
        for pos in self.position_arrays:
            print(self.position_arrays[pos].info)
        print("_________________")

    def _reset_viewer_dims(self) -> None:
        """Reset the viewer dims to the first image."""
        self.viewer.dims.current_step = [0] * len(self.viewer.dims.current_step)
