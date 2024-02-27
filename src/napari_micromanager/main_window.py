from __future__ import annotations

import atexit
import contextlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, cast
from warnings import warn

import napari
import napari.layers
import napari.viewer
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QAction, QDockWidget, QFileDialog, QMenuBar

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
    "left": Qt.DockWidgetArea.LeftDockWidgetArea,
    "right": Qt.DockWidgetArea.RightDockWidgetArea,
    "top": Qt.DockWidgetArea.TopDockWidgetArea,
    "bottom": Qt.DockWidgetArea.BottomDockWidgetArea,
    Qt.DockWidgetArea.LeftDockWidgetArea: "left",
    Qt.DockWidgetArea.RightDockWidgetArea: "right",
    Qt.DockWidgetArea.TopDockWidgetArea: "top",
    Qt.DockWidgetArea.BottomDockWidgetArea: "bottom",
}

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
        self._add_menu()
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
        if layout is not None:
            self._load_layout(layout)

    def _add_menu(self) -> None:
        if (win := getattr(self.viewer.window, "_qt_window", None)) is None:
            return

        menubar = cast(QMenuBar, win.menuBar())

        # main Micro-Manager menu
        mm_menu = menubar.addMenu("Micro-Manager")

        # Layout Sub-Menu
        layout_menu = mm_menu.addMenu("Layout")
        self.act_save_layout = QAction("Save Layout", self)
        self.act_save_layout.triggered.connect(self._save_layout)
        layout_menu.addAction(self.act_save_layout)
        self.act_load_layout = QAction("Load Layout", self)
        self.act_load_layout.triggered.connect(self._load_layout)
        layout_menu.addAction(self.act_load_layout)


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
    ) -> list[WidgetState]:
        """Return the current state of the viewer layout.

        It loops through all the dock widgets in napari's main window and stores
        their state in a list of WidgetState objects.

        The list is sorted by the area of the widgets, so that the widgets in the same
        area are close grouped together.
        """
        if (getattr(self.viewer.window, "_qt_window", None)) is None:
            return []

        wdg_states: list[WidgetState] = []
        with contextlib.suppress(AttributeError):
            main_win = self.viewer.window._qt_window
            for dock_wdg in main_win.findChildren(QDockWidget):
                wdg_name = dock_wdg.objectName()
                area = main_win.dockWidgetArea(dock_wdg)
                area_name = DOCK_AREAS[area]
                wdg_states.append(
                    WidgetState(
                        name=wdg_name,
                        area=area_name,
                        floating=dock_wdg.isFloating(),
                        visible=dock_wdg.isVisible(),
                        tabify_with=[
                            wdg.objectName()
                            for wdg in main_win.tabifiedDockWidgets(dock_wdg)
                        ],
                        geometry=(
                            dock_wdg.geometry().x(),
                            dock_wdg.geometry().y(),
                            dock_wdg.geometry().width(),
                            dock_wdg.geometry().height(),
                        ),
                    )
                )

        return sorted(wdg_states, key=lambda x: x.area)

    def _save_layout(self) -> None:
        """Save the layout state to a json file."""
        wdg_states = self.get_layout_state()

        print()
        print(wdg_states)

        # store the state of the widgets in a dictionary per area
        states: dict[str, list[dict]] = {}
        for wdg_state in wdg_states:
            area = wdg_state.area
            if area not in states:
                states[area] = []
            states[area].append(wdg_state._asdict())

        layout_path, _ = QFileDialog.getSaveFileName(
            self, "Save layout file", "", "jSON (*.json)"
        )
        if layout_path:
            with open(layout_path, "w") as f:
                json.dump(states, f)

    def _load_layout(self, layout_path: str | Path | None = None) -> None:
        """Load the layout from a json file."""
        layout = self._get_layout_path(layout_path)

        if layout is None or not layout.exists():
            return

        try:
            with layout.open("r") as f:
                states = json.load(f)

            if not states:
                return

            self._process_widgets_states(states)

        except json.JSONDecodeError:
            warn(f"Could not load layout from {layout}.", stacklevel=2)

    def _get_layout_path(self, layout_path: str | Path | None = None) -> Path | None:
        """Get the layout path, either from the argument or from a file dialog."""
        if not layout_path:
            layout, _ = QFileDialog.getOpenFileName(
                self, "Open layout file", "", "jSON (*.json)"
            )
            return Path(layout) if layout else None

        elif isinstance(layout_path, str):
            return Path(layout_path)

        else:
            return layout_path

    def _process_widgets_states(self, states: dict) -> None:
        """Process the widgets states loaded from the layout file."""
        for area in states:
            # convert to WidgetState
            widget_states_per_area = [
                WidgetState(*wdg_state.values()) for wdg_state in states[area]
            ]
            # sorted by geometry.y() to select the topmost widget. We will
            # skip the widgets that have negative geometry, as they will be
            # tabified with the other widgets
            widget_states_per_area = sorted(
                widget_states_per_area, key=lambda g: g.geometry[1]
            )

            for wdg_state in widget_states_per_area:

                # skip widgets that will be tabbed
                if wdg_state.geometry[0] < 0 or wdg_state.geometry[1] < 0:
                    continue

                # TODO: fix and also include "Main Window (napari-micromanager)"
                if wdg_state.name == "Main Window (napari-micromanager)":
                    continue

                self._process_widget_state(wdg_state, area)

    def _process_widget_state(self, wdg_state: WidgetState, area: str) -> None:
        """Process a single widget state."""
        # this will load the pymmcore widgets that are not yet in napari
        if wdg_state.name in DOCK_WIDGETS and wdg_state.name not in self._dock_widgets:
            self._load_widget_state(wdg_state)
        # this will reload the napari widgets and the pymmcore widgets that have been
        # already added to napari
        else:
            self._update_widget_state(wdg_state)
        # if tabified, tabify it with the widgets in 'tabify_with'
        if wdg_state.tabify_with:
            self._tabify_widgets(wdg_state, area)

    def _load_widget_state(self, wdg_state: WidgetState) -> None:
        """Load the state of the new pymmcore widgets that are not yet in napari.

        Here we create the pymmcore widgets and add them to the napari window for the
        first time.
        """
        self._show_dock_widget(
            wdg_state.name, wdg_state.floating, False, wdg_state.area
        )
        wdg = self._dock_widgets[wdg_state.name]
        wdg.setVisible(wdg_state.visible)
        if wdg_state.floating:
            wdg.setGeometry(*wdg_state.geometry)

    def _update_widget_state(self, wdg_state: WidgetState) -> None:
        """Update the state of the widgets that are already in napari.

        Here we update the state of the widgets that are already in napari, for example
        the 'layer control', 'layer list' plus any pymmcore widgets that have been added
        to napari).
        """
        if (getattr(self.viewer.window, "_qt_window", None)) is None:
            return

        wdg = self._dock_widgets[wdg_state.name]

        # undock the widget to change its area
        self.viewer.window._qt_window.removeDockWidget(wdg)
        self.viewer.window._qt_window.addDockWidget(DOCK_AREAS[wdg_state.area], wdg)
        wdg.setFloating(wdg_state.floating)
        wdg.setGeometry(*wdg_state.geometry)
        wdg.setVisible(wdg_state.visible)

    def _tabify_widgets(self, wdg_state: WidgetState, area: str) -> None:
        """Tabify a widget with other widgets based on its state."""
        for wdg_name in wdg_state.tabify_with:
            # if it is not have been added to napari yet
            if wdg_name in DOCK_WIDGETS and wdg_name not in self._dock_widgets:
                self._show_dock_widget(wdg_name, wdg_state.floating, True, area)
            # if it has been added to napari before
            else:
                self._tabify_existing_widgets(wdg_state, wdg_name)

    def _tabify_existing_widgets(self, wdg_state: WidgetState, wdg_name: str) -> None:
        """Tabify an existing widget with another widget."""
        tabify_with = self._dock_widgets[wdg_state.name]
        current_wdg = self._dock_widgets[wdg_name]
        self.viewer.window._qt_window.removeDockWidget(current_wdg)
        self.viewer.window._qt_window.tabifyDockWidget(tabify_with, current_wdg)
        current_wdg.setVisible(True)
        tabify_with = current_wdg
