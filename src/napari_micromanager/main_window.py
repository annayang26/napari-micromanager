from __future__ import annotations

import atexit
import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable
from warnings import warn

import napari
import napari.layers
import napari.viewer
from pymmcore_plus import CMMCorePlus

from ._core_link import CoreViewerLink
from ._gui_objects._dock_widgets import DOCK_WIDGETS, WidgetState
from ._gui_objects._toolbar import MicroManagerToolbar

if TYPE_CHECKING:

    from pymmcore_plus.core.events._protocol import PSignalInstance


DOCK_AREA_NAMES = ["left", "right", "top", "bottom"]

# this is very verbose
logging.getLogger("napari.loader").setLevel(logging.WARNING)


class MainWindow(MicroManagerToolbar):
    """The main napari-micromanager widget that gets added to napari."""

    def __init__(
        self, viewer: napari.viewer.Viewer, config: str | Path | None = None
    ) -> None:
        super().__init__(viewer)

        # get global CMMCorePlus instance
        self._mmc = CMMCorePlus.instance()
        # this object mediates the connection between the viewer and core events
        self._core_link = CoreViewerLink(viewer, self._mmc, self)

        # some remaining connections related to widgets ... TODO: unify with superclass
        self._connections: list[tuple[PSignalInstance, Callable]] = [
            (self.viewer.layers.events, self._update_max_min),
            (self.viewer.layers.selection.events, self._update_max_min),
            (self.viewer.dims.events.current_step, self._update_max_min),
        ]
        for signal, slot in self._connections:
            signal.connect(slot)

        # add minmax dockwidget
        if "MinMax" not in getattr(self.viewer.window, "_dock_widgets", []):
            self.viewer.window.add_dock_widget(self.minmax, name="MinMax", area="left")

        # load layout
        self._load_layout()

        # start storing the layout state
        self.get_layout_state()

        # queue cleanup
        self.destroyed.connect(self._cleanup)
        atexit.register(self._cleanup)

        if config is not None:
            try:
                self._mmc.loadSystemConfiguration(config)
            except FileNotFoundError:
                # don't crash if the user passed an invalid config
                warn(f"Config file {config} not found. Nothing loaded.", stacklevel=2)

    def _cleanup(self) -> None:
        for signal, slot in self._connections:
            with contextlib.suppress(TypeError, RuntimeError):
                signal.disconnect(slot)
        # Clean up temporary files we opened.
        self._core_link.cleanup()
        atexit.unregister(self._cleanup)  # doesn't raise if not connected

    def _update_max_min(self, *_: Any) -> None:
        visible = (x for x in self.viewer.layers.selection if x.visible)
        self.minmax.update_from_layers(
            lr for lr in visible if isinstance(lr, napari.layers.Image)
        )

    def _load_layout(self) -> None:
        """Load the layout state from the last time the viewer was closed."""
        import json

        # get layout.json filepath
        layout = Path(__file__).parent / "layout.json"
        # if the file doesn't exist, return
        if not layout.exists():
            return
        # open the json file
        try:
            with layout.open("r") as f:
                state_list = json.load(f)

                if not state_list:
                    return

                # TODO: also add "Main Window (napari-micromanager)" and "MinMax"
                for area_name in DOCK_AREA_NAMES:
                    if area_name not in state_list:
                        continue
                    for wdg_key in state_list[area_name]:
                        wdg_state = WidgetState(
                            *state_list[area_name][wdg_key].values()
                        )
                        # for now this will reload only our widgets, not the napari ones
                        if wdg_key in DOCK_WIDGETS and wdg_state.visible:
                            self._show_dock_widget(
                                wdg_key,
                                wdg_state.floating,
                                wdg_state.tabify,
                                area_name,
                            )
                            wdg = self._dock_widgets[wdg_key]
                            wdg.setGeometry(*wdg_state.geometry)

        except json.JSONDecodeError:
            warn(f"Could not load layout from {layout}.", stacklevel=2)
