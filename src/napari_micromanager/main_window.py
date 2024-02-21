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


DOCK_AREA_NAMES = {
    1: "left",  # "Qt.LeftDockWidgetArea"
    2: "right",  # "Qt.RightDockWidgetArea"
    4: "top",  # "Qt.TopDockWidgetArea"
    8: "bottom",  # Qt.BottomDockWidgetArea"
    # 0: "Qt.NoDockWidgetArea"
}

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
        self._get_layout_state()

        # queue cleanup
        self.destroyed.connect(self._cleanup)
        atexit.register(self._save_layout)
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

    def _save_layout(self) -> None:
        """Save the layout state to a json file."""
        import json

        state = [self._widget_state[key].asdict() for key in self._widget_state]
        layout = Path(__file__).parent / "layout.json"
        with open(layout, "w") as f:
            json.dump(state, f)

    def _load_layout(self) -> None:
        """Load the layout state from the last time the viewer was closed."""
        import json

        from rich import print

        # get layout.json filepath
        layout = Path(__file__).parent / "layout.json"
        # if the file doesn't exist, return
        if not layout.exists():
            return
        # open the json file
        with layout.open("r") as f:
            state_list = json.load(f)
            print(state_list)

            if not state_list:
                return

            # TODO: also add "Main Window (napari-micromanager)" and "MinMax"
            for state in state_list:
                ws = WidgetState(**state)
                if ws.widget_key in DOCK_WIDGETS and ws.visible:
                    area = DOCK_AREA_NAMES[ws.dock_area]
                    self._show_dock_widget(ws.widget_key, ws.floating, ws.tabbed, area)
                    wdg = self._dock_widgets[ws.widget_key]
                    if ws.floating:
                        wdg.move(*ws.position)
