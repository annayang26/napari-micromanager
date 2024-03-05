import numpy as np
import useq
from pymmcore_plus import CMMCorePlus
from superqt.utils import create_worker
from pathlib import Path

class SegmentNeurons:
    """Segment neurons."""

    def __init__(self, mmcore: CMMCorePlus):
        self._mmc = mmcore

        self._mmc.mda.events.sequenceStarted.connect(self._on_sequence_started)
        self._mmc.mda.events.frameReady.connect(self._on_frame_ready)
        self._mmc.mda.events.sequenceFinished.connect(self._on_sequence_finished)

        self._path = Path(r"C:\Users\CH167448\Desktop\test")

        self._fname: str = ""

    def _on_sequence_started(self, sequence: useq.MDASequence) -> None:
        print("\nSEQUENCE STARTED")
        meta = sequence.metadata.get("pymmcore_wigets")
        if meta is not None:
            self._fname = meta.get("save_name", "")

    def _on_frame_ready(self, image: np.ndarray, event: useq.MDAEvent) -> None:
        print("FRAME READY", event.index)
        t_index = event.index.get("t")
        # perform segmentation every first timepoint
        if t_index is not None and t_index == 0:
            print("     PERFORM IMAGE SEGMENTATION")
            create_worker(
                self._segment_image,
                image,
                _start_thread=True,
                _connect={"finished": self._segmentation_finished},
            )

    def _on_sequence_finished(self, sequence: useq.MDASequence) -> None:
        print("\nSEQUENCE FINISHED")

    def _segment_image(self, image: np.ndarray) -> None:
        """Segment the image."""
        print("     SEGMENTING IMAGE", image.shape)
        print(self._mmc.getPixelSizeUm())
        if self._fname:
            ...

    def _segmentation_finished(self) -> None:
        print("     SEGMENTATION FINISHED")
