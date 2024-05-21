from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import zarr

if TYPE_CHECKING:
    from zarr.core import Array
    from zarr.hierarchy import Group

EVENT = "Event"
FRAME_META = "frame_meta"


class OMEZarrReader:
    """Reads the ome-zarr file generated with the 'OMEZarrWriter'.

    Usage:
    >>> path = "/Users/fdrgsp/Desktop/test/test_hcs.ome.zarr"

    >>> z = ReadHCSZarr(path)

    # get the path
    >>> z.path

    # get the zarr file
    >>> z.zarr

    # get the MDASequence from the metadata
    >>> z.sequence

    # get the mapping of position to well
    >>> z.pos_to_well

    # get the mapping of well to position
    >>> z.well_to_pos

    # get the position keys (e.g. "p0", "p1", ...)
    >>> z.get_positions_keys()

    # for the methods below, the position can be an integer (0, 1, ...) or a string in
    # the form "p{int}" (e.g. "p0", "p1", ...) or a well name (e.g. "A1_000", "B2_000").

    # get the data for a given position
    >>> z.get_position_data("A1_000")

    # get the all the frames metadata for a given position
    >>> z.get_position_meta("A1_000")

    # get the metadata for a given frame for a given position
    >>> z.get_frame_meta("A1_000", 0)
    # if you only want the MDAEvent metadata
    >>> z.get_frame_meta("A1_000", 0, event_only=True)p
    """

    def __init__(self, path: str | Path):
        self._path = path

        # open the zarr file
        self._zarr: Group = zarr.open(self._path)

        # to map the position to the well name or vice versa
        self._pos_to_well: dict[str, str] = {}
        self._well_to_pos: dict[str, str] = {}

        self._init()

    # ___________________________Public Methods___________________________

    @property
    def path(self) -> Path:
        """Return the path."""
        return Path(self._path)

    @property
    def zarr(self) -> Group:
        """Return the zarr file."""
        return self._zarr

    @property
    def sequence(self) -> dict[str, Any]:
        """Return the MDASequence."""
        # getting the MDASequence from the first position if any
        try:
            return cast(dict, self._zarr["p0"].attrs["useq_MDASequence"])
        except KeyError:
            return {}

    @property
    def pos_to_well(self) -> dict[str, str]:
        """Return the mapping of position to well."""
        return self._pos_to_well

    @property
    def well_to_pos(self) -> dict[str, str]:
        """Return the mapping of well to position."""
        return self._well_to_pos

    def array_keys(self) -> list[str]:
        """Return the array position keys.

        Each position is stored as a separate array in the zarr file and the key is the
        name to access the array ("p0", "p1", ...).
        """
        return list(self._zarr.array_keys())

    def get_position_data(self, position: int | str) -> Array:
        """Return the data for a given position."""
        pos_key = self._get_position_key(position)
        return self._zarr[pos_key]

    def get_position_meta(self, position: int | str) -> list[dict[str, Any]]:
        """Return the frame meta for a given position."""
        pos_key = self._get_position_key(position)
        try:
            meta = cast(list, self._zarr[pos_key].attrs[FRAME_META])
        except KeyError as e:
            raise KeyError(f"Attrs {FRAME_META} not found!") from e
        return meta

    def get_frame_meta(
        self, position: int | str, frame: int, event_only: bool = False
    ) -> dict[str, Any]:
        """Return the frame meta for a given position and frame.

        If 'event_only' is True, return only the MDAEvent metadata.
        """
        pos_meta = self.get_position_meta(position)
        if event_only:
            try:
                return cast(dict[str, Any], pos_meta[frame][EVENT])
            except KeyError as e:
                raise KeyError(f"Key '{EVENT}' not found!") from e
        try:
            return pos_meta[frame]
        except KeyError as e:
            raise KeyError(f"Frame {frame} not found!") from e

    def to_ome_tiff(self, position: int | str | None = None) -> None:
        """Convert the zarr data to an OME-TIFF file.

        If 'position' is None, convert all the positions to OME-TIFF files.
        """
        ...

    # ___________________________Private Methods___________________________

    def _init(self) -> None:
        """Read the zarr file to get the mapping of well to position."""
        for p in self._zarr.array_keys():
            with contextlib.suppress(KeyError):
                # list of frame meta
                frames_meta: list[dict] = self._zarr[p].attrs[FRAME_META]
                # get event from the first frame meta
                event = cast(dict, frames_meta[0][EVENT])
                # get the pos_name from the event
                pos_name = event.get("pos_name", p)
                # update the mapping of well to position
                self._well_to_pos[pos_name] = p
                # update the mapping of position to well
                self._pos_to_well[p] = pos_name

    def _get_position_key(self, position: int | str) -> str:
        """Return the position key."""
        # if it is an integer, build the position key
        if isinstance(position, int):
            pos_key = f"p{position}"

        elif isinstance(position, str):
            # if it match the form "p{int}" it means it is a position key
            if position.startswith("p") and position[1:].isdigit():
                pos_key = position
            else:
                try:
                    pos_key = self._well_to_pos[position]
                except KeyError as e:
                    raise KeyError(f"Key '{position}' not found!") from e

        else:
            raise TypeError("Position must be an integer or a string.")

        if pos_key is None:
            raise KeyError(f"position '{position}' not found!")

        return pos_key
