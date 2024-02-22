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
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDockWidget, QToolBar

from ._core_link import CoreViewerLink
from ._gui_objects._dock_widgets import DOCK_WIDGETS, WidgetState
from ._gui_objects._toolbar import MicroManagerToolbar

if TYPE_CHECKING:

    from pymmcore_plus.core.events._protocol import PSignalInstance


DOCK_AREAS = {
    1: "left",  # "Qt.DockWidgetArea.LeftDockWidgetArea"
    2: "right",  # "Qt.DockWidgetArea.RightDockWidgetArea"
    4: "top",  # "Qt.DockWidgetArea.TopDockWidgetArea"
    8: "bottom",  # Qt.DockWidgetArea.BottomDockWidgetArea"
    # 0: "Qt.NoDockWidgetArea"
}
DOCK_AREA_NAMES = list(DOCK_AREAS.values())
QT_DOCK_AREAS = {
    "left": Qt.DockWidgetArea.LeftDockWidgetArea,
    "right": Qt.DockWidgetArea.RightDockWidgetArea,
    "top": Qt.DockWidgetArea.TopDockWidgetArea,
    "bottom": Qt.DockWidgetArea.BottomDockWidgetArea,
}
DEFAULT_LAYOUT = Path(__file__).parent / "layouts" / "default_layout.json"
TEST_LAYOUT = Path(__file__).parent / "layouts" / "test_layout.json"

# this is very verbose
logging.getLogger("napari.loader").setLevel(logging.WARNING)


class MainWindow(MicroManagerToolbar):
    """The main napari-micromanager widget that gets added to napari."""

    def __init__(
        self,
        viewer: napari.viewer.Viewer,
        config: str | Path | None = None,
        layout: str | Path | None = None,
    ) -> None:
        super().__init__(viewer)

        # temporary toolbar to test saving layout_________________________________
        save_layout_toolbar = QToolBar("Save Layout")
        save_layout_toolbar.addAction("Save Layout", self._save_layout)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, save_layout_toolbar)
        # ________________________________________________________________________

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

        # add alredy present napari dockwidgets to internal '_dock_widgets'
        if (win := getattr(self.viewer.window, "_qt_window", None)) is not None:
            for dock_wdg in win.findChildren(QDockWidget):
                self._dock_widgets[dock_wdg.objectName()] = dock_wdg

        # queue cleanup
        self.destroyed.connect(self._cleanup)
        atexit.register(self._cleanup)

        if config is not None:
            try:
                self._mmc.loadSystemConfiguration(config)
            except FileNotFoundError:
                # don't crash if the user passed an invalid config
                warn(f"Config file {config} not found. Nothing loaded.", stacklevel=2)

        # load provided layout or the default one stored in the package
        self._load_layout(layout)

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

    def get_layout_state(
        self,
    ) -> dict[str, dict[str, WidgetState]]:
        """Return the current state of the viewer layout.

        It loops through all the dock widgets in napari's main window and stores
        their state in a dict per area.

        Within each area, the widgets are ordered from top to bottom. Note that if the
        widgets are tabified, the one in the background will be the first in the list
        and their x and y geometry coordinates are negative. Using this information, we
        can discriminate between tabified and non-tabified widgets.

        For example:
        {
            'right': {
                'dw1': WidgetState(floating=False, visible=True, geometry=(1,2,3,4)),
                'dw2': WidgetState(floating=False, visible=True, geometry=(3,4,5,6)),
            },
            'left': {
                # dw3 is tabified with dw4 and is behind it
                'dw3': WidgetState(floating=False, visible=True, geometry=(-7,-6,3,2))
                'dw4': WidgetState(floating=False, visible=True, geometry=(8,9,3,7))
                # dw5 is not tabified, so it is below dw4
                'dw5': WidgetState(floating=False, visible=True, geometry=(9,10,3,1))
            }
        }
        """
        if (getattr(self.viewer.window, "_qt_window", None)) is None:
            return {}

        _widget_states: dict[str, dict[str, WidgetState]] = {}
        last_widget_geometry: dict[str, tuple[int, int]] = {}
        with contextlib.suppress(AttributeError):
            for dock_wdg in self.viewer.window._qt_window.findChildren(QDockWidget):
                wdg_name = dock_wdg.objectName()
                area = self.viewer.window._qt_window.dockWidgetArea(dock_wdg)
                area_name = DOCK_AREAS[area]
                if area_name not in _widget_states:
                    _widget_states[area_name] = {}

                # Check if the last widget's x and y were negative or positive
                tabify = False
                if area_name in last_widget_geometry:
                    last_x, last_y = last_widget_geometry[area_name]
                    # if the previous x and y were negative, it means that the last
                    # widget was tabified with the current one
                    if last_x < 0 and last_y < 0:
                        tabify = True
                    # otherwise, if the previous x and y were positive, it means that
                    # this new widget is not tabified
                    elif last_x >= 0 and last_y >= 0:
                        tabify = False

                _widget_states[area_name][wdg_name] = WidgetState(
                    floating=dock_wdg.isFloating(),
                    visible=dock_wdg.isVisible(),
                    tabify=tabify,
                    geometry=(
                        dock_wdg.geometry().x(),
                        dock_wdg.geometry().y(),
                        dock_wdg.geometry().width(),
                        dock_wdg.geometry().height(),
                    ),
                )

                # Update last_widget_geometry
                last_widget_geometry[area_name] = (
                    dock_wdg.geometry().x(),
                    dock_wdg.geometry().y(),
                )

        return _widget_states

    def _save_layout(self) -> None:
        """Save the layout state to a json file."""
        import json

        wdg_states = self.get_layout_state()

        from rich import print

        print()
        print(wdg_states)

        # WidgetState as dict
        states = {
            dock_area: {
                widget_name: wdg_state._asdict()
                for widget_name, wdg_state in widgets.items()
            }
            for dock_area, widgets in wdg_states.items()
        }

        # layout = Path(__file__).parent / "layouts" / "layout.json"
        layout = TEST_LAYOUT
        with open(layout, "w") as f:
            json.dump(states, f)

    def _load_layout(self, layout_path: str | Path | None = None) -> None:
        """Load the layout state from the last time the viewer was closed."""
        import json

        if isinstance(layout_path, str):
            layout_path = Path(layout_path)
        # get layout.json filepath

        # TO BE CHANGED, THIS IS ONLY FOR TESTING
        # layout = layout_path or DEFAULT_LAYOUT
        layout = layout_path or TEST_LAYOUT
        # if the file doesn't exist, return
        if not layout.exists():
            return
        # open the json file
        try:
            with layout.open("r") as f:
                state_list = json.load(f)

                if not state_list:
                    return

                for area_name in DOCK_AREA_NAMES:
                    if area_name not in state_list:
                        continue
                    for idx, wdg_key in enumerate(state_list[area_name]):
                        wdg_state = WidgetState(
                            *state_list[area_name][wdg_key].values()
                        )
                        # this will reload only our widgets, not the napari ones
                        if wdg_key in DOCK_WIDGETS and wdg_state.visible:
                            self._show_dock_widget(
                                wdg_key,
                                wdg_state.floating,
                                wdg_state.tabify,
                                area_name,
                            )
                            if wdg_state.floating:
                                wdg = self._dock_widgets[wdg_key]
                                wdg.setGeometry(*wdg_state.geometry)

                        elif wdg_key in self._dock_widgets:
                            if (
                                getattr(self.viewer.window, "_qt_window", None)
                            ) is None:
                                continue

                            wdg = self._dock_widgets[wdg_key]

                            # undock the widget to change its area
                            self.viewer.window._qt_window.removeDockWidget(wdg)
                            self.viewer.window._qt_window.addDockWidget(
                                QT_DOCK_AREAS[area_name], wdg
                            )
                            # if is tabified, tabify it with the previous widget
                            if wdg_state.tabify and idx > 0:
                                if previous_key := list(state_list[area_name].keys())[
                                    idx - 1
                                ]:
                                    self.viewer.window._qt_window.tabifyDockWidget(
                                        self._dock_widgets[previous_key], wdg
                                    )

                            wdg.setFloating(wdg_state.floating)
                            wdg.setGeometry(*wdg_state.geometry)
                            wdg.setVisible(wdg_state.visible)

        except json.JSONDecodeError:
            warn(f"Could not load layout from {layout}.", stacklevel=2)
