import multiprocessing as mp
import random
import time

# from collections import deque
from multiprocessing import Process
from pathlib import Path

import numpy as np
import useq
from cellpose import io, models, plot
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

        self._cp_model: models.CellposeModel = None
        self._path: Path = None
        self._exp_name: str = ""
        self._pos: int = 0
        self._binning: int = None
        self._objective: int = None
        self._magnification: float = None
        self._pixel_size: float = None

        # self.roi_dict: dict = {}
        # self.labels: np.ndarray = None
        # self.area_dict: dict = {}

    def _on_sequence_started(self, sequence: useq.MDASequence) -> None:
        print("\nSEQUENCE STARTED")
        meta = sequence.metadata.get("pymmcore_widgets")
        num_pos = len(sequence.stage_positions)
        if meta is not None:
            self._exp_name = meta.get("save_name", "")
            self._path = meta.get("save_dir", "")
            self._total_pos = num_pos
        self._is_running = True
        self._load_model() ### <<< load CP model
        meta = sequence.metadata.get("pymmcore_widgets")
        # TODO: find a better way to get metadata
        self._path = Path(meta.get("save_dir", ""))
        self._exp_name = (meta.get("save_name", "")).split('.')[0]
        nap_mm = sequence.metadata.get("napari_micromanager")
        self._pixel_size = nap_mm.get("PixelSizeUm")

        # create a separate process for segmentation
        self._segmentation_process = Process(
            target=_segmentation_worker,
            args=(self._queue,
                  self._cp_model,
                  self._path,
                  self._exp_name,
                  )
        )
        self._segmentation_process.start()
        print("SEGMENTATION WORKER STARTED", self._segmentation_process)

    def _load_model(self):
        """Load CP model once the sequence started."""
        print("                Cellpose model is loaded.")
        dir_path = Path(__file__).parent
        model_path = Path.joinpath(dir_path, "CP_calcium")
        self._cp_model = models.CellposeModel(gpu=False,
                                                pretrained_model=model_path)

    def _on_frame_ready(self, image: np.ndarray, event: useq.MDAEvent) -> None:
        # start the segmentation process
        print("FRAME READY", event.index)
        t_index = event.index.get("t")
        p_index = event.index.get("p")
        if t_index is not None and t_index == 0:
            # send the image to the segmentation process
            self._queue.put([image, p_index])

    def _on_sequence_finished(self, sequence: useq.MDASequence) -> None:
        print("\nSEQUENCE FINISHED")
        self._is_running = False
        # stop the segmentation process
        self._queue.put(None)
        if self._segmentation_process is not None:
            self._segmentation_process.join()
        self._segmentation_process = None

        print("SEGMENTATION WORKER STOPPED", self._segmentation_process)

    # def _getROIpos(self, labels: np.ndarray, background_label: int
    #           ) -> tuple[dict, np.ndarray, dict]:
    #     """Get ROI positions."""
    #     # sort the labels and filter the unique ones
    #     u_labels = np.unique(labels)

    #     # create a dict for the labels
    #     roi_dict = {}
    #     for u in u_labels:
    #         roi_dict[u.item()] = []

    #     # record the coordinates for each label
    #     for x in range(labels.shape[0]):
    #         for y in range(labels.shape[1]):
    #             roi_dict[labels[x, y]].append([x, y])

    #     # delete any background labels
    #     del roi_dict[background_label]

    #     area_dict, roi_to_delete = self._get_ROI_area(roi_dict, 100)

    #     # delete roi in label layer and dict
    #     for r in roi_to_delete:
    #         coords_to_delete = np.array(roi_dict[r]).T.tolist()
    #         labels[tuple(coords_to_delete)] = 0
    #         roi_dict[r] = []

    #     # move roi in roi_dict after removing some labels
    #     for r in range(1, (len(roi_dict) - len(roi_to_delete) + 1)):
    #         i = 1
    #         while not roi_dict[r]:
    #             roi_dict[r] = roi_dict[r + i]
    #             roi_dict[r + i] = []
    #             i += 1

    #     # delete extra roi keys
    #     for r in range((len(roi_dict) - len(roi_to_delete) + 1), (len(roi_dict) + 1)):
    #         del roi_dict[r]

    #     # update label layer with new roi
    #     for r in roi_dict:
    #         roi_coords = np.array(roi_dict[r]).T.tolist()
    #         labels[tuple(roi_coords)] = r

    #     return roi_dict, labels, area_dict

    # def _get_ROI_area(self, roi_dict: dict, threshold: float) -> tuple[dict, list]:
    #     """Calculate the areas of each ROI in the ROI_dict."""
    #     area = {}
    #     small_roi = []
    #     for r in roi_dict:
    #         if len(roi_dict[r]) < threshold:
    #             small_roi.append(r)
    #             continue
    #         area[r] = len(roi_dict[r])

    #         # when including in the system
    #         # area, _ = self._calculate_cellsize(area, self._binning, self._pixel_size,
    #         #                                    self._objective, self._magnification)
    #     return area, small_roi

    # def _calculate_cellsize(self, roi_dict: dict, binning: int,
    #                     pixel_size: int, objective: int,
    #                     magnification: float) -> (dict):
    #     """Calculate the cell size in um."""
    #     cellsize = {}
    #     for r in roi_dict:
    #         cellsize[r]=(len(roi_dict[r])*binning*pixel_size)/(objective*magnification)

    #     cs_arr = np.array(list(cellsize.items()))

    #     return cellsize, cs_arr

    # def _send_roi_info(self):
    #     """Send the info for further analysis."""
    #     return self.roi_dict, self.labels, self.area_dict

# this must not be part of the SegmentNeurons class
def _segmentation_worker(queue: mp.Queue, cp_model: models.CellposeModel,
                         folder_path: Path, exp_name: str) -> None:
    """Segmentation worker running in a separate process."""
    while True:
        pack = queue.get()
        if pack is None:
            break
        image = pack[0]
        pos = pack[1]
        _segment_image(image, cp_model, folder_path, exp_name, pos)

def _segment_image(image: np.ndarray, cp_model: models.CellposeModel,
                   folder_path: Path, exp_name: str, pos: int) -> None:
        """Segment the image."""
        channels = [0, 0]
        print("     SEGMENTING IMAGE", image.shape)
        masks, flows, _ = cp_model.eval(image,
                                    diameter=None,
                                    flow_threshold=0.1,
                                    cellprob_threshold=0,
                                    channels=channels)

        save_path = folder_path.joinpath(f"{exp_name}_p{pos}")

        if not save_path.is_dir():
            save_path.mkdir()

        mask_path = save_path.joinpath(f"{exp_name}_p{pos}")
        _save_overlay(image, channels, masks, mask_path)
        rgb_mask = plot.mask_rgb(masks)
        io.save_masks(image, rgb_mask, flows, mask_path, tif=True)
        # bg_label = 0
        # self.roi_dict, self.labels, self.area_dict = self._getROIpos(masks, bg_label)

def _save_overlay(img: np.ndarray, channels: list,
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
    file_save_path = str(save_path) + "_overlay.jpg"
    io.imsave(file_save_path, overlay)
