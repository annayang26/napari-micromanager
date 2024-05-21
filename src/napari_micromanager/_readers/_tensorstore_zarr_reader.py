import json
from pathlib import Path
from typing import Any

import zarr
from tqdm import tqdm
from useq import MDASequence
from zarr import Array


class TensorZarrReader:
    def __init__(self, path: str | Path):
        self._path = path

        # open the zarr file
        self._zarr: Array = zarr.open(self._path)

    @property
    def path(self) -> Path:
        """Return the path."""
        return Path(self._path)

    @property
    def zarr(self) -> Array:
        """Return the zarr file."""
        return self._zarr

    @property
    def sequence(self) -> MDASequence | None:
        """Return the MDASequence."""
        try:
            return MDASequence(**json.loads(self._zarr.attrs["useq_MDASequence"]))
        except KeyError:
            return None

    # ______________________Public Methods______________________

    def get_axis_data_and_metadata(
        self, axis: str, index: int
    ) -> tuple[Array, list[dict[str, Any]]]:
        """Return the data for the given axis and its metadata."""
        data = self._get_axis_data(axis, index)

        meta = self.zarr.attrs.get("frame_metadatas")
        if meta is None:
            return data, []

        axis_meta = []
        for i in self.zarr.attrs["frame_metadatas"]:
            event = i["Event"]
            event_index = event["index"]
            if axis in event_index and index == event_index.get(axis):
                axis_meta.append(i)

        return data, axis_meta

    def write_tiff(
        self, path: str | Path, axis: str | None = None, index: int | None = None
    ) -> None:
        """Write the data for the given axis to a tiff file.

        If 'axis' or 'index' is None, the data will be saved as a tiff file for each
        position, if any, or as a single tiff file.

        Parameters
        ----------
        path : str | Path
            The path to save the tiff file. If 'axis' or 'index' is None, the path
            should be a directory. Otherwise, the path should be a file (ending in
            '.tif').
        axis : str | None, optional
            The axis to save as a tiff file. If None, save all positions as tiff files.
            Default is None.
        index : int | None, optional
            The index of the axis to save as a tiff file. If None, save all positions as
            tiff files. Default is None.
        """
        from tifffile import imwrite

        # TODO: FIX ME!!! make ome-tiff

        if axis is None or index is None:
            self._save_all_as_tiff(path)
            return

        data, _ = self.get_axis_data_and_metadata(axis, index)
        imj = len(data.shape) <= 5
        imwrite(path, data, imagej=imj)

    # ______________________Private Methods______________________

    def _create_axis_tuple(self, axis: str) -> int:
        """Create a tuple with the correct slice for the given axis."""
        if self.sequence is None:
            raise ValueError("No sequence found in the metadata.")

        if axis not in self.sequence.axis_order:
            raise ValueError(f"Axis {axis} not found in the MDASequence")

        return self.sequence.axis_order.index(axis)

    def _get_axis_data(self, axis: str, index: int) -> Array:
        """Return the data for the given axis."""
        # e.g. axis = "p", index = 1)
        # get the correct tuple for the axis (e.g. axis_index = 1)
        axis_index = self._create_axis_tuple(axis)
        # get the correct tuple for the axis
        # e.g. axis_tuple = [slice(None), 1, slice(None), slice(None)]
        axis_tuple = [
            slice(None) if i != axis_index else 0 for i in range(len(self.zarr.shape))
        ]
        # update the axis_tuple with the requested index in the correct position
        axis_tuple[axis_index] = index
        # return the data for the given axis
        return self.zarr[tuple(axis_tuple)]

    def _save_all_as_tiff(self, path: str | Path) -> None:
        """Save the zarr file to a tiff file.

        If the MDASequence has positions, save each position as a tiff file. Otherwise,
        save the zarr data as a single tiff file.
        """
        from tifffile import imwrite

        # TODO: FIX ME!!! make ome-tiff

        if self.sequence is None:
            raise ValueError("No MDASequence found in the metadata.")

        if pos := len(self.sequence.stage_positions):
            with tqdm(total=pos) as pbar:
                for i in range(pos):
                    data, _ = self.get_axis_data_and_metadata("p", i)
                    imwrite(Path(path) / f"p{i}.tif", data, imagej=True)
                    pbar.update(1)

        else:
            imj = len(self.zarr.shape) <= 5
            imwrite(path, self.zarr, imagej=imj)
