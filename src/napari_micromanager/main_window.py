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
from qtpy.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from ._core_link import CoreViewerLink
from ._gui_objects._toolbar import MicroManagerToolbar

if TYPE_CHECKING:

    from pymmcore_plus.core.events._protocol import PSignalInstance


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

        # queue cleanup
        self.destroyed.connect(self._cleanup)
        atexit.register(self._cleanup)

        # 'config=not config' and 'layout=no layout' to avoid showing the dialog
        # if the respective files were passed as a command line argument.
        # do not open if both config and layout are provided
        if not config or not layout:
            self._startup = StartupDialog(self, config=not config, layout=not layout)
            # make sure it is shown in the center of the screen
            self._startup.move(
                self.viewer.window.qt_viewer.geometry().center()
                - self._startup.rect().center()
            )
            # if the user pressed OK
            if self._startup.exec_():
                config = (
                    self._startup.cfg_combo.currentText() if config is None else config
                )
                layout = (
                    self._startup.layout_combo.currentText()
                    if layout is None
                    else layout
                )

        if config is not None:
            try:
                self._mmc.loadSystemConfiguration(config)
            except FileNotFoundError:
                # don't crash if the user passed an invalid config
                warn(f"Config file {config} not found. Nothing loaded.", stacklevel=2)

        if layout is not None:
            ...

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


class StartupDialog(QDialog):
    """A dialog to select the MicroManager configuration and layout files."""

    def __init__(
        self, parent: QWidget | None = None, *, config: bool = True, layout: bool = True
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configuration and Layout")

        # find .cfg files in every mm directory
        cfg_files = self._get_micromanager_cfg_files()

        wdg_layout = QGridLayout(self)

        cfg_lbl = QLabel("Configuration file:")
        self.cfg_combo = QComboBox()
        self.cfg_combo.setObjectName("cfg")
        self.cfg_combo.addItems([str(f) for f in cfg_files])
        self.cfg_btn = QPushButton("...")
        self.cfg_btn.clicked.connect(lambda: self._on_browse_clicked(self.cfg_combo))

        layout_lbl = QLabel("Layout file:")
        self.layout_combo = QComboBox()
        self.layout_combo.setObjectName("layout")
        self.layout_btn = QPushButton("...")
        self.layout_btn.clicked.connect(
            lambda: self._on_browse_clicked(self.layout_combo)
        )

        if config:
            wdg_layout.addWidget(cfg_lbl, 0, 0)
            wdg_layout.addWidget(self.cfg_combo, 0, 1)
            wdg_layout.addWidget(self.cfg_btn, 0, 2)
        if layout:
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
