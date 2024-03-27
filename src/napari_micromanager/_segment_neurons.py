import time
from collections import deque
from typing import Generator

import numpy as np
import useq
from pymmcore_plus import CMMCorePlus
from superqt.utils import create_worker


class SegmentNeurons:
    """Segment neurons."""

    def __init__(self, mmcore: CMMCorePlus):
        self._mmc = mmcore

        self._is_running: bool = False
        self._deck: deque[np.ndarray] = deque()

        self._mmc.mda.events.sequenceStarted.connect(self._on_sequence_started)
        self._mmc.mda.events.frameReady.connect(self._on_frame_ready)
        self._mmc.mda.events.sequenceFinished.connect(self._on_sequence_finished)

    def _on_sequence_started(self, sequence: useq.MDASequence) -> None:
        print("\nSEQUENCE STARTED")
        self._deck.clear()
        self._is_running = True

        create_worker(
            self._watch_sequence,
            _start_thread=True,
            _connect={
                "yielded": self._segment_image,
                "finished": self._segmentation_finished,
            },
        )

    def _watch_sequence(self) -> Generator[np.ndarray, None, None]:
        print("WATCHING SEQUENCE")
        while self._is_running:
            if self._deck:
                yield self._deck.popleft()
            else:
                time.sleep(0.1)

    def _on_frame_ready(self, image: np.ndarray, event: useq.MDAEvent) -> None:
        print("FRAME READY", event.index)
        # if t=0, append to the deck
        t_index = event.index.get("t")
        if t_index is not None and t_index == 0:
            self._deck.append(image)

    def _on_sequence_finished(self, sequence: useq.MDASequence) -> None:
        print("\nSEQUENCE FINISHED")
        self._is_running = False

    def _segment_image(self, image: np.ndarray) -> None:
        """Segment the image."""
        print("     SEGMENTING IMAGE", image.shape)

    def _segmentation_finished(self) -> None:
        print("     SEGMENTATION FINISHED")
