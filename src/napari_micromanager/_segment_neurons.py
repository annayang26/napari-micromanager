import random
from pathlib import Path

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

    def _on_frame_ready(self, image: np.ndarray, event: useq.MDAEvent) -> None:
        print("FRAME READY", event.index)
        t_index = event.index.get("t")
        # perform segmentation every first timepoint
        if t_index is not None and t_index == 0:
            print("     PERFORM IMAGE SEGMENTATION")

            # if the model is not loaded or the size doesn't match the image size
            if self._model_size != image.shape[0]:
                import tensorflow as tf
                import tensorflow.keras.backend as K

                img_size = image.shape[0]
                self._model_size = img_size

                dir_path = Path(__file__).parent
                path = Path.joinpath(dir_path, f'unet_calcium_{img_size}')
                self._model_unet = tf.keras.models.load_model(path,
                                                              custom_objects={"K": K})

            create_worker(
                self._segment_image,
                image,
                self._model_unet,
                self._exp_name,
                _start_thread=True,
                _connect={"finished": self._segmentation_finished},
            )

    def _on_sequence_finished(self, sequence: useq.MDASequence) -> None:
        print("\nSEQUENCE FINISHED")

    def _segment_image(self, image: np.ndarray, model, exp_name: str) -> None:
        """Segment the image."""
        print("     SEGMENTING IMAGE", image.shape)

        # predict the cells
        img_predict = self._predict_px(image, model)
        self._save_pred_img(img_predict, exp_name, "_PREDICTION.png")

        # label the cells
        minsize = 100
        background_label = 0
        labels, roi_dict = self._segment(img_predict, minsize, background_label)
        self._save_label_img(labels, exp_name, "_Seg.png")

    def _predict_px(self, image: np.ndarray, model):
        """Predict the cells."""
        if model is not None:
            # img_norm = np.max(image, axis=0) / np.max(image)
            img_norm = self._normalize_img(image)
            img_predict = model.predict(img_norm[None, :, :])[:, :]
            return img_predict
        print("Model failed to load")

    def _save_pred_img(self, img: np.ndarray, exp_name: str, filename: str) -> None:
        """Save the image."""
        save_img = img.reshape((img.shape[-2], img.shape[-1]))
        im_save = Image.fromarray(np.uint8(save_img*255), mode='L')
        exp_name += ("_Pos" + str(self._current_pos) + filename)
        pred_path = Path(self._path).joinpath(exp_name)
        im_save.save(pred_path)

    def _normalize_img(self, img: np.ndarray) -> np.ndarray:
        """Normalize the raw image with max/min normalization method."""
        g_max = np.max(img)
        g_min = np.min(img)
        img_norm = (img - g_min)/(g_max - g_min)
        return img_norm

    def _segment(
            self, img_predict: np.ndarray, minsize: int, background_label: int
            ) -> tuple[np.ndarray, dict]:
        """Predict the cell bodies, removing small holes and objects."""
        if np.max(img_predict) > 0.3:
            # use Otsu's method to find the cooridnates of the cell bodies
            th = filters.threshold_otsu(img_predict)
            img_predict_th = img_predict > th
            img_predict_remove_holes_th = morphology.remove_small_holes(
                img_predict_th, area_threshold=minsize * 0.3)
            img_predict_filtered_th = morphology.remove_small_objects(
                img_predict_remove_holes_th, min_size=minsize)
            distance = ndi.distance_transform_edt(img_predict_filtered_th)
            local_max = feature.peak_local_max(distance,
                                                min_distance=10,
                                                footprint=np.ones((15, 15)),
                                                labels=img_predict_filtered_th)

            # create masks over the predicted cell bodies and add a segmentation layer
            local_max_mask = np.zeros_like(img_predict_filtered_th, dtype=bool)
            local_max_mask[tuple(local_max.T)] = True
            markers = morphology.label(local_max_mask)
            labels = segmentation.watershed(-distance, markers,
                                            mask=img_predict_filtered_th)
            labels, roi_dict = self.getROIpos(labels, background_label)
        else:
            # TODO: should send signal to the MDA and go for another FOV
            labels, roi_dict = None, None

        return labels, roi_dict

    def getROIpos(self, labels: np.ndarray, background_label: int
                  ) -> tuple[np.ndarray, dict]:
        """Get the positions of the labels without the background labels."""
        # sort the labels and filter the unique ones
        u_labels = np.unique(labels)

        # create a dict for the labels
        roi_dict = {}
        for u in u_labels:
            roi_dict[u.item()] = []

        labels = np.squeeze(labels)
        print(labels.shape)
        # record the coordinates for each label
        for x in range(labels.shape[0]):
            for y in range(labels.shape[1]):
                roi_dict[labels[x, y]].append([x, y])

        # delete any background labels
        del roi_dict[background_label]

        _, roi_to_delete = self.get_ROI_area(roi_dict, 100)

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
        return labels, roi_dict

    def get_ROI_area(self, roi_dict: dict, threshold: float) -> tuple[dict, list[int]]:
        """Get the areas of each ROI in the ROI_dict."""
        area = {}
        small_roi = []
        for r in roi_dict:
            area[r] = len(roi_dict[r])
            if area[r] < threshold:
                small_roi.append(r)
        return area, small_roi

    def _save_label_img(
            self, img: np.ndarray, roi_dict: dict,
            exp_name: str, filename: str
            ) -> dict:
        """Save the label image."""
        label_array = np.stack((img,) * 4, axis=-1).astype(float)
        for i in range(1, np.max(img) + 1):
            color_list = {}
            color = (random.randint(0, 255),  # noqa: S311
                     random.randint(0, 255),  # noqa: S311
                     random.randint(0, 255))  # noqa: S311
            color_list[i] = color
            i_coords = np.asarray(label_array == [i, i, i, i]).nonzero()
            label_array[(i_coords[0], i_coords[1])] = color_list[i - 1]

        im = Image.fromarray((label_array*255).astype(np.uint8))
        bk_im = Image.new(im.mode, im.size, "black")
        bk_im.paste(im, im.split()[-1])
        bk_im_num = self.add_num_to_img(bk_im, roi_dict)
        exp_name += ("_Pos" + str(self._current_pos))
        save_path = Path(self._path).joinpath(exp_name)
        bk_im_num.save(save_path + filename)

        return color_list

    def add_num_to_img(self, img: np.ndarray, roi_dict: dict):
        """Add labels to ROIs."""
        # the centers of each ROI
        roi_centers = {}

        for roi_number, roi_coords in roi_dict.items():
            center = np.mean(roi_coords, axis=0)
            roi_centers[roi_number] = (int(center[1]), int(center[0]))

        img_w_num = img.copy()
        for r in roi_dict:
            draw = ImageDraw.Draw(img_w_num)
            font = ImageFont.truetype('segoeui.ttf', 12)
            pos = roi_centers[r]
            bbox = draw.textbbox(pos, str(r), font=font)
            draw.rectangle(bbox, fill="grey")
            draw.text(pos, str(r), font=font, fill="white")

        return img_w_num

    def _change_position(self):
        """To change the position number."""
        self._current_pos += 1

    def _clear(self):
        """Clear the global variable for the next recording."""
        self._path: str = ""
        self._exp_name: str = ""
        self._model_size = 0
        self._model_unet = None

        self._current_pos: int = 0
        self._total_pos: int = 0

    def _segmentation_finished(self) -> None:
        print("     SEGMENTATION FINISHED")
        self._change_position()
        if self._current_pos == self._total_pos:
            self._clear()

'''
TODO list (03/06):
    1. figure out how to get the save path and the file name --- done
    2. make sure that the segmentation is working well. 
        changes:
        - the way to normalize the image (from divided by a global 
            max to min-max normalization)
        - the shape of the prediction image
    3. the output wanted after segmentation. just image? roi_dict? 

'''