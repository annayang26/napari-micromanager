import csv
import os
import pickle
import time
from collections import deque
from typing import Generator

import numpy as np
import pandas as pd
import useq
from pymmcore_plus import CMMCorePlus
from scipy import signal, stats
from superqt.utils import create_worker

from ._segment_neurons import SegmentNeurons


class AnalyzeNeurons:
    """Analyze calcium recording with masks."""

    def __init__(self, mmcore: CMMCorePlus, seg: SegmentNeurons):
        self._mmc = mmcore
        self.seg = seg

        self._is_running: bool = False
        self._deck: deque[np.ndarray] = deque()

        self._mmc.mda.events.sequenceStarted.connect(self._on_sequence_started)
        self._mmc.mda.events.frameReady.connect(self._on_frame_ready)
        self._mmc.mda.events.sequenceFinished.connect(self._on_sequence_finished)

        # self._roi_dict: dict = None
        # self._roi_signal: dict = None
        # self._dff: dict = None
        # self.spike_times: dict = None
        # self.roi_analysis: dict = None
        self._framerate: float = None

    def _on_sequence_started(self, sequence: useq.MDASequence) -> None:
        print("\nANALYSIS STARTED")
        self._deck.clear()
        self._is_running = True
        meta = sequence.metadata.get("pymmcore_widgets")
        self._path = meta.get("save_dir", "")
        self._exp_name = meta.get("save_name", "")
        # TODO: get framerate

        create_worker(
            self._watch_sequence,
            _start_thread=True,
            _connect={
                "yielded": self._analyze_roi,
                "finished": self._analyze_finished,
            },
        )

    def _watch_sequence(self) -> Generator[np.ndarray, None, None]:
        print("WATCHING SEQUENCE IN ANALYZE NEURONS")
        while self._is_running:
            if self._deck:
                yield self._deck.popleft()
            else:
                time.sleep(0.1)

    # TODO: check with Federico
    def _on_frame_ready(self, img: np.ndarray, event: useq.MDAEvent) -> None:
        print("FRAME READY", event.index)
        t_index = event.index.get("t")
        roi_dict, labels, area_dict = self.seg._send_roi_info()

        # NOTE: should wait for the recording of one FOV to finish
        if t_index is not None and roi_dict is not None:
            self._deck.append([img, roi_dict, labels, area_dict])

    def _analyze_roi(self, package: list):
        """Analyze ROIs."""
        img_stack, roi_dict, labels, area_dict = package

        raw_signal = self._calculate_ROI_intensity(roi_dict, img_stack)
        roi_dff, _, _ = self._calculateDFF(raw_signal)
        spk_times = self._find_peaks(roi_dff)
        roi_analysis = self._analyze_roi(roi_dff, spk_times, self._framerate)
        mean_connect = self._get_mean_connect(roi_dff, spk_times)

    def _calculate_ROI_intensity(self, roi_dict: dict, img_stack: np.ndarray) -> dict:
        """Calculate the raw signal of each ROI."""
        raw_signal = {}
        for r in roi_dict:
            raw_signal[r] = np.zeros(img_stack.shape[0])
            roi_coords = np.array(roi_dict[r]).T.tolist()
            for z in range(img_stack.shape[0]):
                img_frame = img_stack[z, :, :]
                raw_signal[r][z] = np.mean(img_frame[tuple(roi_coords)])
        return raw_signal

    def _calculateDFF(self, roi_signal: dict) -> tuple[dict, dict, dict]:
        """Calculate ∆F/F."""
        dff = {}
        median = {}
        bg = {}

        for n in roi_signal:
            background, median[n] = self._calculate_background(roi_signal[n], 200)
            bg[n] = background.tolist()
            dff[n] = (roi_signal[n] - background) / background
            dff[n] = dff[n] - np.min(dff[n])
        return dff, median, bg

    def _calculate_background(self, f: list,
                              window: int)->tuple[np.ndarray, np.ndarray]:
        """Calculate background."""
        background = np.zeros_like(f)
        background[0] = f[0]
        median = [background[0]]
        for y in range(1, len(f)):
            x = y - window
            if x < 0:
                x = 0

            lower_quantile = f[x:y] <= np.median(f[x:y])
            signal_in_frame = np.array(f[x:y])
            background[y] = np.mean(signal_in_frame[lower_quantile])
            median.append(np.median(f[x:y]))
        return background, median

    def _find_peaks(self, roi_dff: dict, prom_pctg: float = 0.25,
                    method: str = "mean") -> dict:
        """Find peaks."""
        spike_times = {}
        for roi in roi_dff:
            if method == "mean":
                prominence = np.mean(roi_dff[roi]) * prom_pctg
            elif method == "median":
                prominence = np.median(roi_dff[roi]) * prom_pctg

            peaks, _ = signal.find_peaks(roi_dff[roi], prominence=prominence)
            spike_times[roi] = list(peaks)

        return spike_times

    def _analyze_roi(self, roi_dff: dict, spk_times: dict, framerate: float):
        """Analyze activity of each ROI."""
        amplitude_info = self._get_amplitude(roi_dff, spk_times)
        time_to_rise = self._get_time_to_rise(amplitude_info, framerate)
        max_slope = self._get_max_slope(roi_dff, amplitude_info)
        iei = self._analyze_iei(spk_times, framerate)
        roi_analysis = amplitude_info

        for r in roi_analysis:
            # roi_analysis[r]['spike_times'] = spk_times[r]
            roi_analysis[r]['time_to_rise'] = time_to_rise[r]
            roi_analysis[r]['max_slope'] = max_slope[r]
            roi_analysis[r]['IEI'] = iei[r]

        return roi_analysis

    def _get_amplitude(self, roi_dff: dict, spk_times: dict,
                        deriv_threhold=0.01, reset_num=17,
                        neg_reset_num=2, total_dist=40) -> dict:
        """Get the amplitude."""
        amplitude_info = {}

        # for each ROI
        for r in spk_times:
            amplitude_info[r] = {}
            amplitude_info[r]['amplitudes'] = []
            amplitude_info[r]['peak_indices'] = []
            amplitude_info[r]['base_indices'] = []

            if len(spk_times[r]) > 0:
                dff_deriv = np.diff(roi_dff[r]) # the difference between each spike

                # for each spike in the ROI
                for i in range(len(spk_times[r])):
                    # Search for starting index for current spike
                    searching = True
                    under_thresh_count = 0
                    total_count = 0
                    start_index = spk_times[r][i] # the frame for the first spike

                    if start_index > 0:
                        while searching:
                            start_index -= 1
                            total_count += 1

                            # If collide with a new spike
                            if start_index in spk_times[r]:
                                subsearching = True
                                negative_count = 0

                                while subsearching:
                                    start_index += 1
                                    if start_index < len(dff_deriv):
                                        if dff_deriv[start_index] < 0:
                                            negative_count += 1

                                        else:
                                            negative_count = 0

                                        if negative_count == neg_reset_num:
                                            subsearching = False
                                    else:
                                        subsearching = False

                                break

                            # if the difference is below threshold
                            if dff_deriv[start_index] < deriv_threhold:
                                under_thresh_count += 1
                            else:
                                under_thresh_count = 0

                            # stop searching for starting index
                            if under_thresh_count >= reset_num or start_index == 0 or total_count == total_dist:
                                searching = False

                    # Search for ending index for current spike
                    searching = True
                    under_thresh_count = 0
                    total_count = 0
                    end_index = spk_times[r][i]

                    if end_index < (len(dff_deriv) - 1):
                        while searching:
                            end_index += 1
                            total_count += 1

                            # If collide with a new spike
                            if end_index in spk_times[r]:
                                subsearching = True
                                negative_count = 0
                                while subsearching:
                                    end_index -= 1
                                    if dff_deriv[end_index] < 0:
                                        negative_count += 1
                                    else:
                                        negative_count = 0
                                    if negative_count == neg_reset_num:
                                        subsearching = False
                                break
                            if dff_deriv[end_index] < deriv_threhold:
                                under_thresh_count += 1
                            else:
                                under_thresh_count = 0

                            # NOTE: changed the operator from == to >=
                            if under_thresh_count >= reset_num or end_index >= (len(dff_deriv) - 1) or \
                                    total_count == total_dist:
                                searching = False

                    # Save data
                    spk_to_end = roi_dff[r][spk_times[r][i]:(end_index + 1)]
                    start_to_spk = roi_dff[r][start_index:(spk_times[r][i] + 1)]
                    try:
                        amplitude_info[r]['amplitudes'].append(np.max(spk_to_end) - np.min(start_to_spk))
                        amplitude_info[r]['peak_indices'].append(int(spk_times[r][i] + np.argmax(spk_to_end)))
                        amplitude_info[r]['base_indices'].append(int(spk_times[r][i] -
                                                                    (len(start_to_spk) - (np.argmin(start_to_spk) + 1))))
                    except ValueError:
                        pass

        return amplitude_info

    def _get_time_to_rise(self, amplitude_info: dict, framerate: float) -> dict:
        """Get time to rise."""
        time_to_rise = {}
        for r in amplitude_info:
            time_to_rise[r] = []
            if len(amplitude_info[r]['peak_indices']) > 0:
                for i in range(len(amplitude_info[r]['peak_indices'])):
                    peak_index = amplitude_info[r]['peak_indices'][i]
                    base_index = amplitude_info[r]['base_indices'][i]
                    frames = peak_index - base_index + 1
                    if framerate:
                        time = frames / framerate  # frames * (seconds/frames) = seconds
                        time_to_rise[r].append(time)
                    else:
                        time_to_rise[r].append(frames)

        return time_to_rise

    def _get_max_slope(self, roi_dff: dict, amplitude_info: dict):
        """Get Max slope."""
        max_slope = {}
        for r in amplitude_info:
            max_slope[r] = []
            dff_deriv = np.diff(roi_dff[r])
            if len(amplitude_info[r]['peak_indices']) > 0:
                for i in range(len(amplitude_info[r]['peak_indices'])):
                    peak_index = amplitude_info[r]['peak_indices'][i]
                    base_index = amplitude_info[r]['base_indices'][i]
                    slope_window = dff_deriv[base_index:(peak_index + 1)]
                    max_slope[r].append(np.max(slope_window))

        return max_slope

    def _analyze_iei(self, spk_times: dict, framerate: float):
        """Analyze IEI."""
        iei = {}
        for r in spk_times:
            iei[r] = []

            if len(spk_times[r]) > 1:
                iei_frames = np.diff(np.array(spk_times[r]))
                if framerate:
                    iei[r] = iei_frames / framerate # in seconds
                else:
                    iei[r] = iei_frames
        return iei

    def _get_mean_connect(self, roi_dff: dict, spk_times: dict):
        """Calculate connectivity."""
        A = self._get_connect_matrix(roi_dff, spk_times)

        if A is not None:
            if len(A) > 1:
                mean_connect = np.median(np.sum(A, axis=0) - 1) / (len(A) - 1)
            else:
                mean_connect = 'N/A - Only one active ROI'
        else:
            mean_connect = 'No calcium events detected'

        return mean_connect

    def _get_connect_matrix(self, roi_dff: dict, spk_times: dict) -> np.ndarray:
        """Calculate the connectivity matrix."""
        active_roi = [r for r in spk_times if len(spk_times[r]) > 0]

        if len(active_roi) > 0:
            phases = {}
            for r in active_roi:
                phases[r] = self._get_phase(len(roi_dff[r]), spk_times[r])

            connect_matrix = np.zeros((len(active_roi), len(active_roi)))
            for i, r1 in enumerate(active_roi):
                for j, r2 in enumerate(active_roi):
                    connect_matrix[i, j] = self._get_sync_index(phases[r1], phases[r2])
        else:
            connect_matrix = None

        return connect_matrix

    def _get_phase(self, total_frames: int, spks: list) -> list:
        """Get Phase."""
        spikes = spks.copy()
        if len(spikes) == 0 or spikes[0] != 0:
            spikes.insert(0, 0)
        if spikes[-1] != (total_frames - 1):
            spikes.append(total_frames - 1)

        phase = []
        for k in range(len(spikes) - 1):
            t = spikes[k]

            while t < spikes[k + 1]:
                instant_phase = (2 * np.pi) * ((t - spikes[k]) / \
                                               (spikes[k+1]-spikes[k]))+(2 * np.pi * k)
                phase.append(instant_phase)
                t += 1
        phase.append(2 * np.pi * (len(spikes) - 1))

        return phase

    def _get_sync_index(self, x_phase: list, y_phase: list):
        """Calculate the pair-wise synchronization index of the two ROIs."""
        phase_diff = self._get_phase_diff(x_phase, y_phase)
        sync_index = np.sqrt((np.mean(np.cos(phase_diff)) ** 2)
                             + (np.mean(np.sin(phase_diff)) ** 2))

        return sync_index

    def _get_phase_diff(self, x_phase: list, y_phase: list) -> np.ndarray:
        """Calculate the absolute phase difference between two different ROIs."""
        x_phase = np.array(x_phase)
        y_phase = np.array(y_phase)
        phase_diff = np.mod(np.abs(x_phase - y_phase), (2 * np.pi))

        return phase_diff

    def _save_results(self, save_path: str, spk: dict, cell_size: dict,
                      roi_analysis: dict, framerate: float, total_frames: int,
                      dff: dict) -> None:
        """Save the analysis results."""
        # save spike times
        if not os.path.isdir(save_path):
            os.mkdir(save_path)

        with open(save_path + '/spike_times.pkl', 'wb') as spike_file:
            pickle.dump(spk, spike_file)

        dff_df = pd.DataFrame.from_dict(dff)
        path = save_path + '/del_frames_dff.csv'
        dff_df.to_csv(path, index=False)

        # save
        roi_data = self._all_roi_data(roi_analysis, cell_size, spk, framerate, total_frames)
        with open(save_path + '/roi_data.csv', 'w', newline='') as roi_data_file:
            writer = csv.DictWriter(roi_data_file, dialect='excel')
            fields = ['ROI', 'cell_size (um)', '# of events', 'frequency (num of events/s)',
                    'average amplitude', 'amplitude SEM', 'average time to rise', 'time to rise SEM',
                    'average max slope', 'max slope SEM',  'InterEvent Interval', 'IEI SEM']
            writer.writerow(fields)
            writer.writerows(roi_data)

    def _organize_roi_data(self, roi_analysis: dict, cell_size: dict, spk_times: dict,
                           framerate: float, total_frames: int) -> dict:
        """Organize ROI data into a dict."""
        if len(roi_analysis) == len(cell_size):
            roi_data = {}
            for r in roi_analysis:
                roi_data[r]["cell size (um)"] = cell_size[r]
                roi_data[r][""] = 



    def _analyze_finished(self) -> None:
        print("Analysis Done")

    def _on_sequence_finished(self, sequence: useq.MDASequence) -> None:
        print("\nSEQUENCE FINISHED IN ANALYSIS")
        self._is_running = False

