import time
from collections import deque
from pathlib import Path
from typing import Generator

import numpy as np
import useq
from cellpose import io, models, plot
from pymmcore_plus import CMMCorePlus
from superqt.utils import create_worker

from ._analyze_neurons import AnalyzeNeurons


class SegmentNeurons:
    """Segment neurons."""

    def __init__(self, mmcore: CMMCorePlus):
        self._mmc = mmcore

        self._is_running: bool = False
        self._deck: deque[np.ndarray] = deque()

        self._mmc.mda.events.sequenceStarted.connect(self._on_sequence_started)
        self._mmc.mda.events.frameReady.connect(self._on_frame_ready)
        self._mmc.mda.events.sequenceFinished.connect(self._on_sequence_finished)

        self._cp_model: models.CellposeModel = None
        self._path: str = ""
        self._exp_name: str = ""
        self._binning: int = None
        self._objective: int = None
        self._magnification: float = None
        self._pixel_size: float = None

        self.roi_dict: dict = {}
        self.labels: np.ndarray = None
        self.area_dict: dict = {}

    def _on_sequence_started(self, sequence: useq.MDASequence) -> None:
        print("\nSEQUENCE STARTED")
        self._deck.clear()
        self._is_running = True
        self._load_model() ### <<< load CP model
        meta = sequence.metadata.get("pymmcore_widgets") # TODO: find a better way to get metadata
        self._path = meta.get("save_dir", "")
        self._exp_name = meta.get("save_name", "")

        create_worker(
            self._watch_sequence,
            _start_thread=True,
            _connect={
                "yielded": self._segment_image,
                "finished": self._segmentation_finished,
            },
        )

    def _load_model(self):
        """Load CP model once the sequence started."""
        print("                Cellpose model is loaded.")
        dir_path = Path(__file__).parent
        model_path = Path.joinpath(dir_path, "CP_calcium")
        self._cp_model = models.CellposeModel(gpu=False,
                                                pretrained_model=model_path)

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

    def _segment_image(self, image: np.ndarray, channels: list| None) -> None:
        """Segment the image."""
        if channels is None:
            channels = [0, 0]
        print("     SEGMENTING IMAGE", image.shape)
        masks, flows, _ = self._cp_model.eval(image,
                                    diameter=None,
                                    flow_threshold=0.1,
                                    cellprob_threshold=0,
                                    channels=channels)

        path = Path(self._path)

        if not path.is_dir():
            path.mkdir()

        self._save_overlay(image, channels, masks, path)
        rgb_mask = plot.mask_rgb(masks)
        save_path = path / "masks.tif"
        io.save_masks(image, rgb_mask, flows, save_path, tif=True)
        print("                   Cellpose finished")
        bg_label = 0
        self.roi_dict, self.labels, self.area_dict = self._getROIpos(masks, bg_label)
        print("              READY TO SEND ROI INFO TO ANALYZE NEURONS")

    def _save_overlay(self, img: np.ndarray, channels: list,
                      masks: np.ndarray, save_path: Path) -> None:
        """Save the overlay image of masks over original image."""
        img0 = img.copy()

        if img0.shape[0] < 4:
            img0 = np.transpose(img0, (1, 2, 0))
        if img0.shape[-1] < 3 or img0.ndim < 3:
            img0 = plot.image_to_rgb(img0, channels=channels)
        else:
            if img0.max() <= 50.0:
                img0 = np.uint8(np.clip(img0, 0, 1) * 255)

        # generate mask over original image
        overlay = plot.mask_overlay(img0, masks)
        io.imsave((save_path / "overlay.jpg"), overlay)

    def _getROIpos(self, labels: np.ndarray, background_label: int
              ) -> tuple[dict, np.ndarray, dict]:
        """Get ROI positions."""
        # sort the labels and filter the unique ones
        u_labels = np.unique(labels)

        # create a dict for the labels
        roi_dict = {}
        for u in u_labels:
            roi_dict[u.item()] = []

        # record the coordinates for each label
        for x in range(labels.shape[0]):
            for y in range(labels.shape[1]):
                roi_dict[labels[x, y]].append([x, y])

        # delete any background labels
        del roi_dict[background_label]

        area_dict, roi_to_delete = self._get_ROI_area(roi_dict, 100)

        # delete roi in label layer and dict
        for r in roi_to_delete:
            coords_to_delete = np.array(roi_dict[r]).T.tolist()
            labels[tuple(coords_to_delete)] = 0
            roi_dict[r] = []

        # move roi in roi_dict after removing some labels
        for r in range(1, (len(roi_dict) - len(roi_to_delete) + 1)):
            i = 1
            while not roi_dict[r]:
                roi_dict[r] = roi_dict[r + i]
                roi_dict[r + i] = []
                i += 1

        # delete extra roi keys
        for r in range((len(roi_dict) - len(roi_to_delete) + 1), (len(roi_dict) + 1)):
            del roi_dict[r]

        # update label layer with new roi
        for r in roi_dict:
            roi_coords = np.array(roi_dict[r]).T.tolist()
            labels[tuple(roi_coords)] = r

        return roi_dict, labels, area_dict

    def _get_ROI_area(self, roi_dict: dict, threshold: float) -> tuple[dict, list]:
        """Calculate the areas of each ROI in the ROI_dict."""
        area = {}
        small_roi = []
        for r in roi_dict:
            if len(roi_dict[r]) < threshold:
                small_roi.append(r)
                continue
            area[r] = len(roi_dict[r])

            # when including in the system
            # area, _ = self._calculate_cellsize(area, self._binning, self._pixel_size,
            #                                    self._objective, self._magnification)
        return area, small_roi

    def _calculate_cellsize(self, roi_dict: dict, binning: int,
                        pixel_size: int, objective: int,
                        magnification: float) -> (dict):
        """Calculate the cell size in um."""
        cellsize = {}
        for r in roi_dict:
            cellsize[r]=(len(roi_dict[r])*binning*pixel_size)/(objective*magnification)

        cs_arr = np.array(list(cellsize.items()))

        return cellsize, cs_arr

    def _send_roi_info(self, mask: np.ndarray):
        """Send the info for further analysis."""
        return self.roi_dict, self.labels, self.area_dict

    def _segmentation_finished(self) -> None:
        print("     SEGMENTATION FINISHED")
        self.roi_dict: dict = {}
        self.labels: np.ndarray = None
        self.area_dict: dict = {}
        print(f"            {len(self.roi_dict)}")
