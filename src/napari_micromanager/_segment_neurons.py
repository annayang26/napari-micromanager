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
        self._fname: str = ""
        self._model_size = 0
        self._model_unet = None

    def _on_sequence_started(self, sequence: useq.MDASequence) -> None:
        print("\nSEQUENCE STARTED")
        meta = sequence.metadata.get("pymmcore_wigets")
        if meta is not None:
            self._fname = meta.get("save_name", "")
            self._path = meta.get("path_name", "") ### TODO: Need to double check

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

                ### TODO: try os.path for now; change to Pathlib later
                dir_path = Path(__file__).parent
                path = Path.joinpath(dir_path, f'unet_calcium_{img_size}')
                # dir_path = os.path.dirname(os.path.realpath(__file__))
                # path = os.path.join(dir_path, f'unet_calcium_{img_size}.hdf5')
                self._model_unet = tf.keras.models.load_model(path,
                                                              custom_objects={"K": K})

            create_worker(
                self._segment_image,
                image,
                self._model_unet,
                _start_thread=True,
                _connect={"finished": self._segmentation_finished},
            )

    def _on_sequence_finished(self, sequence: useq.MDASequence) -> None:
        print("\nSEQUENCE FINISHED")

    def _segment_image(self, image: np.ndarray, model) -> None:
        """Segment the image."""
        print("     SEGMENTING IMAGE", image.shape)
        # print(self._mmc.getPixelSizeUm())
        if self._fname and model is not None:
            img_norm = np.max(image, axis=0) / np.max(image)
            img_predict = self.model_unet.predict(img_norm[np.newaxis, :, :])[0, :, :]

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
        print("prediction shape: ", img_predict.shape)
        # save the prediction
        self._save_img(img_predict)
        print("     Prediction Image saved!")

    def _save_img(self, pred_img: np.ndarray):
        im_pred = Image.fromarray(np.uint8(pred_img*255), mode='L')
        pred_path = Path.joinpath(self._path, self._fname, '_Prediction.png')
        im_pred.save(pred_path)

    def _segmentation_finished(self) -> None:
        print("     SEGMENTATION FINISHED")
