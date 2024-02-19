from __future__ import annotations

import atexit
import contextlib
import logging
from typing import TYPE_CHECKING, Any, Callable
from warnings import warn

import napari
import napari.layers
import napari.viewer
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from ._core_link import CoreViewerLink
from ._gui_objects._toolbar import MicroManagerToolbar

if TYPE_CHECKING:
    from pathlib import Path

    from pymmcore_plus.core.events._protocol import PSignalInstance


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
            if hasattr(self.viewer.window._dock_widgets["MinMax"], "_close_btn"):
                self.viewer.window._dock_widgets["MinMax"]._close_btn = False

        # queue cleanup
        self.destroyed.connect(self._cleanup)
        atexit.register(self._cleanup)

        if config is not None:
            try:
                self._mmc.loadSystemConfiguration(config)
            except FileNotFoundError:
                # don't crash if the user passed an invalid config
                warn(f"Config file {config} not found. Nothing loaded.", stacklevel=2)

        else:
            self._startup = StartupDialog(self)
            if self._startup.exec_():
                cfg = self._startup.cfg_le.text()
                layout = self._startup.layout_le.text()
                if cfg:
                    self._mmc.loadSystemConfiguration(cfg)
                if layout:
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

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QGridLayout(self)

        cfg_lbl = QLabel("Configuration file:")
        self.cfg_le = QLineEdit()
        self.cfg_le.setObjectName("cfg")
        self.cfg_btn = QPushButton("Browse")
        self.cfg_btn.clicked.connect(lambda: self._on_browse_clicked(self.cfg_le))

        layyout_lbl = QLabel("Layout file:")
        self.layout_le = QLineEdit()
        self.layout_le.setObjectName("layout")
        self.layout_btn = QPushButton("Browse")
        self.layout_btn.clicked.connect(lambda: self._on_browse_clicked(self.layout_le))

        layout.addWidget(cfg_lbl, 0, 0)
        layout.addWidget(self.cfg_le, 0, 1)
        layout.addWidget(self.cfg_btn, 0, 2)

        layout.addWidget(layyout_lbl, 1, 0)
        layout.addWidget(self.layout_le, 1, 1)
        layout.addWidget(self.layout_btn, 1, 2)

        # Create OK and Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box, 2, 0, 1, 3)

    def _on_browse_clicked(self, le: QLineEdit) -> None:
        """Open a file dialog to select a file."""
        file_type = "cfg" if le.objectName() == "cfg" else "json"
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open file", "", f"MicroManager files (*.{file_type})"
        )
        if filename:
            le.setText(filename)
