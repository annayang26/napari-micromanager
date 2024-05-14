import random
from pathlib import Path
import multiprocessing as mp
from multiprocessing import Process

import numpy as np
import useq
from PIL import Image, ImageDraw, ImageFont
from pymmcore_plus import CMMCorePlus
from scipy import ndimage as ndi
from skimage import feature, filters, morphology, segmentation
from superqt.utils import create_worker


class SegmentNeurons:
    """Segment neurons."""

    def __init__(self, mmcore: CMMCorePlus):
        self._mmc = mmcore

        self._is_running: bool = False

        self._segmentation_process: Process | None = None

        # Create a multiprocessing Queue
        self._queue: mp.Queue[np.ndarray | None] = mp.Queue()

        self._mmc.mda.events.sequenceStarted.connect(self._on_sequence_started)
        self._mmc.mda.events.frameReady.connect(self._on_frame_ready)
        self._mmc.mda.events.sequenceFinished.connect(self._on_sequence_finished)

        self._path: str = ""
        self._exp_name: str = ""
        self._model_size: int = 0
        self._model_unet = None

        self._current_pos: int = 0
        self._total_pos: int = 0

    def _on_sequence_started(self, sequence: useq.MDASequence) -> None:
        print("\nSEQUENCE STARTED")
        meta = sequence.metadata.get("pymmcore_widgets")
        num_pos = len(sequence.stage_positions)
        if meta is not None:
            self._exp_name = meta.get("save_name", "")
            self._path = meta.get("save_dir", "")
            self._total_pos = num_pos
        self._is_running = True

        # create a separate process for segmentation
        self._segmentation_process = Process(
            target=_segmentation_worker, args=(self._queue,)
        )

        # start the segmentation process
        self._segmentation_process.start()

        print("SEGMENTATION WORKER STARTED", self._segmentation_process)

    def _on_frame_ready(self, image: np.ndarray, event: useq.MDAEvent) -> None:
        print("FRAME READY", event.index)
        # if t=0, add the image to the queue
        t_index = event.index.get("t")
        if t_index is not None and t_index == 0:
            # send the image to the segmentation process
            self._queue.put(image)

    def _on_sequence_finished(self, sequence: useq.MDASequence) -> None:
        print("\nSEQUENCE FINISHED")
        self._is_running = False

        # stop the segmentation process
        self._queue.put(None)
        if self._segmentation_process is not None:
            self._segmentation_process.join()
        self._segmentation_process = None

        print("SEGMENTATION WORKER STOPPED", self._segmentation_process)


# this must not be part of the SegmentNeurons class
def _segmentation_worker(queue: mp.Queue) -> None:
    """Segmentation worker running in a separate process."""
    while True:
        image = queue.get()
        if image is None:
            break
        _segment_image(image)


def _segment_image(image: np.ndarray) -> None:
    """Segment the image."""
    print("     SEGMENTING IMAGE", image.shape)
