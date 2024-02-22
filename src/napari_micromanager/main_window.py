from __future__ import annotations

import atexit
import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, cast
from warnings import warn

import napari
import napari.layers
import napari.viewer
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolBar,
    QWidget,
)

from ._core_link import CoreViewerLink
from ._gui_objects._dock_widgets import DOCK_WIDGETS, WidgetState
from ._gui_objects._toolbar import MicroManagerToolbar

if TYPE_CHECKING:

    from pymmcore_plus.core.events._protocol import PSignalInstance

FIXED = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
DOCK_AREAS = {
    1: "left",  # "Qt.DockWidgetArea.LeftDockWidgetArea"
    2: "right",  # "Qt.DockWidgetArea.RightDockWidgetArea"
    4: "top",  # "Qt.DockWidgetArea.TopDockWidgetArea"
    8: "bottom",  # Qt.DockWidgetArea.BottomDockWidgetArea"
    "left": Qt.DockWidgetArea.LeftDockWidgetArea,
    "right": Qt.DockWidgetArea.RightDockWidgetArea,
    "top": Qt.DockWidgetArea.TopDockWidgetArea,
    "bottom": Qt.DockWidgetArea.BottomDockWidgetArea,
}
DEFAULT_LAYOUT = Path(__file__).parent / "layouts" / "default_layout.json"

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
        load_layout_toolbar = QToolBar("Load Layout")
        load_layout_toolbar.addAction("Load Layout", self._load_layout)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, load_layout_toolbar)
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
            if hasattr(self.viewer.window._dock_widgets["MinMax"], "_close_btn"):
                self.viewer.window._dock_widgets["MinMax"]._close_btn = False

        # add alredy present napari dockwidgets to internal '_dock_widgets'
        if (win := getattr(self.viewer.window, "_qt_window", None)) is not None:
            for dock_wdg in win.findChildren(QDockWidget):
                self._dock_widgets[dock_wdg.objectName()] = dock_wdg

        # queue cleanup
        self.destroyed.connect(self._cleanup)
        atexit.register(self._cleanup)

        # 'config=not config' and 'layout=no layout' to avoid showing the dialog
        # if the respective files were passed as a command line argument.
        # do not open if both config and layout are provided
        if not config or not layout:
            self._startup = StartupDialog(self, config=not config, layout=not layout)
            # make sure it is shown in the center of the viewer and resize it
            self._center_startup_dialog()
            # if the user pressed OK
            if self._startup.exec_():
                cfg, lay = self._startup.value()
                config = cfg if config is None else config
                layout = lay if layout is None else layout

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

    def _center_startup_dialog(self) -> None:
        """Center the startup dialog in the viewer window."""
        self._startup.move(
            self.viewer.window.qt_viewer.geometry().center()
            - self._startup.geometry().center()
        )
        self._startup.resize(
            int(self.viewer.window.qt_viewer.geometry().width() / 2),
            self._startup.sizeHint().height(),
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
        # TODO: add a dialog to select the file path
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

        layout_path, _ = QFileDialog.getSaveFileName(
            self, "Save layout file", "", "jSON (*.json)"
        )
        if layout_path:
            with open(layout_path, "w") as f:
                json.dump(states, f)

    def _load_layout(self, layout_path: str | Path | None = None) -> None:
        """Load the layout state from the last time the viewer was closed."""
        import json

        # open a file dialog if the layout path is not provided
        if not layout_path:
            layout, _ = QFileDialog.getOpenFileName(
                self, "Open layout file", "", "jSON (*.json)"
            )
            layout = Path(layout) if layout else DEFAULT_LAYOUT
        elif isinstance(layout_path, str):
            layout = Path(layout_path)
        else:
            layout = layout_path

        # if the file doesn't exist, return
        if not layout.exists():
            return
        # open the json file
        try:
            with layout.open("r") as f:
                states = json.load(f)

                if not states:
                    return

                for area_name in DOCK_AREAS.values():

                    if area_name not in states:
                        continue
                    states = cast(dict[str, dict[str, dict]], states)
                    for idx, wdg_key in enumerate(states[area_name]):
                        wdg_state = WidgetState(*states[area_name][wdg_key].values())
                        # this will reload pymmcore widgets
                        if wdg_key in DOCK_WIDGETS and wdg_state.visible:
                            self._update_pymmcore_widget(wdg_key, wdg_state, area_name)
                        # this will reload the napari widgets
                        elif wdg_key in self._dock_widgets:
                            self._update_napari_widget(
                                idx, states, wdg_key, wdg_state, area_name
                            )

        except json.JSONDecodeError:
            warn(f"Could not load layout from {layout}.", stacklevel=2)

    def _update_pymmcore_widget(
        self, wdg_key: str, wdg_state: WidgetState, area_name: str
    ) -> None:
        """Update the state of the pymmcore widgets."""
        self._show_dock_widget(
            wdg_key,
            wdg_state.floating,
            wdg_state.tabify,
            area_name,
        )
        if wdg_state.floating:
            wdg = self._dock_widgets[wdg_key]
            wdg.setGeometry(*wdg_state.geometry)

    def _update_napari_widget(
        self,
        idx: int,
        states: dict[str, dict[str, dict]],
        wdg_key: str,
        wdg_state: WidgetState,
        area_name: str,
    ) -> None:
        """Update the state of the napari widgets."""
        if (getattr(self.viewer.window, "_qt_window", None)) is None:
            return

        wdg = self._dock_widgets[wdg_key]

        # undock the widget to change its area
        self.viewer.window._qt_window.removeDockWidget(wdg)
        self.viewer.window._qt_window.addDockWidget(DOCK_AREAS[area_name], wdg)
        # if is tabified, tabify it with the previous widget
        if wdg_state.tabify and idx > 0:
            if previous_key := list(states[area_name].keys())[idx - 1]:
                self.viewer.window._qt_window.tabifyDockWidget(
                    self._dock_widgets[previous_key], wdg
                )

        wdg.setFloating(wdg_state.floating)
        wdg.setGeometry(*wdg_state.geometry)
        wdg.setVisible(wdg_state.visible)


class StartupDialog(QDialog):
    """A dialog to select the MicroManager configuration and layout files."""

    def __init__(
        self, parent: QWidget | None = None, *, config: bool = True, layout: bool = True
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configuration and Layout")

        self._config = config
        self._layout = layout

        wdg_layout = QGridLayout(self)

        cfg_lbl = QLabel("Configuration file:")
        cfg_lbl.setSizePolicy(FIXED)
        self.cfg_combo = QComboBox()
        self.cfg_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLength
        )
        self.cfg_combo.setObjectName("cfg")
        # find .cfg files in every mm directory
        cfg_files = self._get_micromanager_cfg_files()
        # TODO: once we have the database of configs, we can populate the combo box
        # with the stored configs too. remember to check their existance before adding
        # them
        self.cfg_combo.addItems([str(f) for f in cfg_files])
        self.cfg_btn = QPushButton("...")
        self.cfg_btn.setSizePolicy(FIXED)
        self.cfg_btn.clicked.connect(lambda: self._on_browse_clicked(self.cfg_combo))

        layout_lbl = QLabel("Layout file:")
        layout_lbl.setSizePolicy(FIXED)
        self.layout_combo = QComboBox()
        self.layout_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLength
        )
        self.layout_combo.setObjectName("layout")
        # TODO: once we have the database of layouts, we can populate the combo box
        # with the stored layouts too. remember to check their existance before adding
        # them
        self.layout_combo.addItems([str(DEFAULT_LAYOUT)])
        self.layout_btn = QPushButton("...")
        self.layout_btn.setSizePolicy(FIXED)
        self.layout_btn.clicked.connect(
            lambda: self._on_browse_clicked(self.layout_combo)
        )

        wdg_layout.addWidget(cfg_lbl, 0, 0)
        wdg_layout.addWidget(self.cfg_combo, 0, 1)
        wdg_layout.addWidget(self.cfg_btn, 0, 2)

        wdg_layout.addWidget(layout_lbl, 1, 0)
        wdg_layout.addWidget(self.layout_combo, 1, 1)
        wdg_layout.addWidget(self.layout_btn, 1, 2)

        # Create OK and Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        wdg_layout.addWidget(button_box, 2, 0, 1, 3)

        self.resize(self.sizeHint())

        # hide the cfg widgets if config is provided
        if not config:
            cfg_lbl.hide()
            self.cfg_combo.hide()
            self.cfg_btn.hide()

        # hide the layout widgets if layout is provided
        if not layout:
            layout_lbl.hide()
            self.layout_combo.hide()
            self.layout_btn.hide()

    def _get_micromanager_cfg_files(self) -> list[Path]:
        from pymmcore_plus import find_micromanager

        mm: list = find_micromanager(False)
        cfg_files: list[Path] = []
        for mm_dir in mm:
            cfg_files.extend(Path(mm_dir).glob("*.cfg"))

        return cfg_files

    def _on_browse_clicked(self, combo: QComboBox) -> None:
        """Open a file dialog to select a file."""
        file_type = "cfg" if combo.objectName() == "cfg" else "json"
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open file", "", f"MicroManager files (*.{file_type})"
        )
        if filename:
            combo.addItem(filename)
            combo.setCurrentText(filename)
            # TODO: keep a database of the created configes ands layouts with their
            # paths so we can update the comboboxes with the new files.

    def value(self) -> tuple[str | None, str | None]:
        """Return the selected configuration and layout files."""
        return self.cfg_combo.currentText(), self.layout_combo.currentText()
