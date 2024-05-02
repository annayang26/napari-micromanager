import os
import time
from collections import deque
from typing import Generator

import numpy as np
import tifffile as tff
import useq
from pymmcore_plus import CMMCorePlus
from superqt.utils import create_worker


class AnalyzeNeurons:
    """Analyze calcium recording with masks."""

    def __init__(self, mmcore: CMMCorePlus):
        self._mmc = mmcore

        self._is_running: bool = False
        self._deck: deque[np.ndarray] = deque()

        self._mmc.mda.events.sequenceStarted.connect(self._on_sequence_started)
        # self._mmc.mda.events.frameReady.connect(self._on_frame_ready)
        # self._mmc.mda.events.frameReady.connect(self._on_frame_ready)
        self._mmc.mda.events.sequenceFinished.connect(self._on_frame_ready)

        self._roi_dict: dict = None
        self._roi_signal: dict = None
        self._dff: dict = None
        self.spike_times: dict = None
        self.roi_analysis: dict = None

    def _on_sequence_started(self, sequence: useq.MDASequence) -> None:
        print("\nANALYSIS STARTED")
        self._deck.clear()
        self._is_running = True
        meta = sequence.metadata.get("pymmcore_widgets")
        self._path = meta.get("save_dir", "")
        self._exp_name = meta.get("save_name", "")

        create_worker(
            self._watch_sequence,
            _start_thread=True,
            _connect={
                "yielded": self._analyze_roi,
                "finished": self._analyze_finished,
            },
        )

    def _watch_sequence(self) -> Generator[np.ndarray, None, None]:
        print("WATCHING SEQUENCE")
        while self._is_running:
            if self._deck:
                yield self._deck.popleft()
            else:
                time.sleep(0.1)

    # TODO: can i re-use this?
    def _on_frame_ready(self, img_stack: np.ndarray, event: useq.MDAEvent) -> None:
        print("FRAME READY", event.index)
        # should take the entire recording after one position is done
        t_index = event.index.get("t")
        if t_index is not None and t_index == 100:
            print("                 its the 100th frame, add")
            self._deck.append(img_stack)

    def _receive_roi_dict(self, roi_dict: dict, labels: np.ndarray, area_dict: dict):
        """Receive ROI info from Segmented Neurons."""
        print("Received info.........")
        return roi_dict, labels, area_dict

    def _analyze_roi(self):
        """Analyze ROIs."""
        roi_dict, labels, area_dict = self._receive_roi_dict

    def _analyze_finished(self) -> None:
        print("Analysis Done")

    def _on_sequence_finished(self, sequence: useq.MDASequence) -> None:
        print("\nSEQUENCE FINISHED")
        self._is_running = False

