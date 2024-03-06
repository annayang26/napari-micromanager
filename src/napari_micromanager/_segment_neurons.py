import os.path

from pathlib import Path
import numpy as np
import useq
from PIL import Image
from pymmcore_plus import CMMCorePlus
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
        self._model_size = 0
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
        # print(self._mmc.getPixelSizeUm())
        if model is not None:
            # img_norm = np.max(image, axis=0) / np.max(image)
            img_norm = self._normalize_img(image)
            img_predict = model.predict(img_norm[None, :, :])[:, :]

            # if np.max(img_predict) > 0.3:
            #     # the prediction layer shows the prediction of the NN
            #     self.prediction_layer = self.viewer.add_image(img_predict, name='Prediction')

            #     # use Otsu's method to find the cooridnates of the cell bodies
            #     th = filters.threshold_otsu(img_predict)
            #     img_predict_th = img_predict > th
            #     img_predict_remove_holes_th = morphology.remove_small_holes(img_predict_th, area_threshold=minsize * 0.3)
            #     img_predict_filtered_th = morphology.remove_small_objects(img_predict_remove_holes_th, min_size=minsize)
            #     distance = ndi.distance_transform_edt(img_predict_filtered_th)
            #     local_max = feature.peak_local_max(distance,
            #                                     min_distance=10,
            #                                     footprint=np.ones((15, 15)),
            #                                     labels=img_predict_filtered_th)

            #     # create masks over the predicted cell bodies and add a segmentation layer
            #     local_max_mask = np.zeros_like(img_predict_filtered_th, dtype=bool)
            #     local_max_mask[tuple(local_max.T)] = True
            #     markers = morphology.label(local_max_mask)
            #     labels = segmentation.watershed(-distance, markers, mask=img_predict_filtered_th)
            #     roi_dict, labels = self.getROIpos(labels, background_label)
            #     label_layer = self.viewer.add_labels(labels, name='Segmentation', opacity=1)
            # else:
            #     if self.batch_process:
            #         print(f'There were no cells detected in <{self.img_name}>')
            #     else:
            #         self.general_msg('No ROI', 'There were no cells detected')
            #     labels, label_layer, roi_dict = None, None, None

        # return labels, label_layer, roi_dict
        # save the prediction
        self._save_img(img_predict, exp_name)
        print("     Prediction Image saved!")

    def _normalize_img(self, img):
        '''
        '''
        g_max = np.max(img)
        g_min = np.min(img)
        img_norm = (img - g_min)/(g_max - g_min)
        return img_norm

    def _save_img(self, pred_img: np.ndarray, exp_name):
        pred_img = pred_img.reshape((pred_img.shape[1], pred_img.shape[2]))
        im_pred = Image.fromarray(np.uint8(pred_img*255), mode='L')
        exp_name += ("_Pos" + str(self._current_pos) + "_PREDICTION.png")
        pred_path = Path(self._path).joinpath(exp_name)
        im_pred.save(pred_path)
    
    def _change_position(self):
        self._current_pos += 1

    def _clear(self):
        self._path: str = ""
        self._exp_name: str = ""
        self._model_size = 0
        self._model_unet = None

        self._current_pos = 0
        self._total_pos = 0

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