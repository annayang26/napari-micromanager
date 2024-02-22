from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, cast

from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import (
    ChannelGroupWidget,
    ChannelWidget,
    # ConfigurationWidget,
    DefaultCameraExposureWidget,
    LiveButton,
    ObjectivesWidget,
    PropertyBrowser,
    SnapButton,
)

try:
    # this was renamed
    from pymmcore_widgets import ObjectivesPixelConfigurationWidget
except ImportError:
    from pymmcore_widgets import (
        PixelSizeWidget as ObjectivesPixelConfigurationWidget,  # noqa: F401
    )

from qtpy.QtCore import QEvent, QObject, QSize, Qt, Signal
from qtpy.QtWidgets import (
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QToolBar,
    QWidget,
)
from superqt.fonticon import icon

from ._dock_widgets import DOCK_WIDGETS
from ._min_max_widget import MinMax
from ._shutters_widget import MMShuttersWidget

if TYPE_CHECKING:
    import napari.viewer

TOOL_SIZE = 35


class MicroManagerToolbar(QMainWindow):
    """Create a QToolBar for the Main Window."""

    def __init__(self, viewer: napari.viewer.Viewer) -> None:
        super().__init__()

        self._mmc = CMMCorePlus.instance()
        self.viewer: napari.viewer.Viewer = getattr(viewer, "__wrapped__", viewer)

        # add variables to the napari console
        if console := getattr(self.viewer.window._qt_viewer, "console", None):
            from useq import MDAEvent, MDASequence

            console.push(
                {
                    "MDAEvent": MDAEvent,
                    "MDASequence": MDASequence,
                    "mmcore": self._mmc,
                }
            )

        # min max widget
        self.minmax = MinMax(parent=self)

        # to store all dock widgets in a dict
        self._dock_widgets: dict[str, QDockWidget] = {}

        if (win := getattr(self.viewer.window, "_qt_window", None)) is not None:
            # make the tabs of tabbed dockwidgets apprearing on top (North)
            areas = [
                Qt.DockWidgetArea.RightDockWidgetArea,
                Qt.DockWidgetArea.LeftDockWidgetArea,
                Qt.DockWidgetArea.TopDockWidgetArea,
                Qt.DockWidgetArea.BottomDockWidgetArea,
            ]
            for area in areas:
                cast(QMainWindow, win).setTabPosition(
                    area, QTabWidget.TabPosition.North
                )

        # add toolbar items
        toolbar_items = [
            # ConfigToolBar(self),
            ChannelsToolBar(self),
            ObjectivesToolBar(self),
            None,
            ShuttersToolBar(self),
            SnapLiveToolBar(self),
            ExposureToolBar(self),
            ToolsToolBar(self),
        ]
        for item in toolbar_items:
            if item:
                self.addToolBar(Qt.ToolBarArea.TopToolBarArea, item)
            else:
                self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)

        self._is_initialized = False
        self.installEventFilter(self)

    def _initialize(self) -> None:
        if self._is_initialized or not (
            win := getattr(self.viewer.window, "_qt_window", None)
        ):
            return
        win = cast(QMainWindow, win)
        if (
            isinstance(dw := self.parent(), QDockWidget)
            and win.dockWidgetArea(dw) is not Qt.DockWidgetArea.TopDockWidgetArea
        ):
            self._is_initialized = True
            was_visible = dw.isVisible()
            win.removeDockWidget(dw)
            dw.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea)
            win.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, dw)
            dw.setVisible(was_visible)  # necessary after using removeDockWidget
            self.removeEventFilter(self)

    def eventFilter(self, obj: QObject | None, event: QEvent | None) -> bool:
        """Event filter that ensures that this widget is shown at the top.

        npe2 plugins don't have a way to specify where they should be added, so this
        event filter listens for the event when this widget is docked in the main
        window, then redocks it at the top and assigns allowed areas.
        """
        # the move event is one of the first events that is fired when the widget is
        # docked, so we use it to re-dock this widget at the top
        if (
            event
            and event.type() == QEvent.Type.Move
            and obj is self
            and not self._is_initialized
        ):
            self._initialize()

        return False

    def _show_dock_widget(
        self,
        key: str = "",
        floating: bool = False,
        tabify: bool = True,
        area: str = "right",
    ) -> None:
        """Look up widget class in DOCK_WIDGETS and add/create or show/raise.

        `key` must be a key in the DOCK_WIDGETS dict or a `str` stored in
        the `whatsThis` property of a `sender` `QPushButton`.
        """
        if not key:
            # using QPushButton.whatsThis() property to get the key.
            btn = cast(QPushButton, self.sender())
            key = btn.whatsThis()

        if key in self._dock_widgets:
            # already exists
            dock_wdg = self._dock_widgets[key]
            dock_wdg.show()
            dock_wdg.raise_()
        else:
            # creating it for the first time
            # sourcery skip: extract-method
            try:
                wdg_cls = DOCK_WIDGETS[key][0]
            except KeyError as e:
                raise KeyError(
                    "Not a recognized dock widget key. "
                    f"Must be one of {list(DOCK_WIDGETS)} "
                    " or the `whatsThis` property of a `sender` `QPushButton`."
                ) from e
            wdg = wdg_cls(parent=self, mmcore=self._mmc)

            if isinstance(wdg, PropertyBrowser):
                wdg.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
                wdg._prop_table.setVerticalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAlwaysOff
                )
                floating = True
                tabify = False

            wdg = ScrollableWidget(self, title=key, widget=wdg)
            dock_wdg = self._add_dock_widget(
                wdg, key, floating=floating, tabify=tabify, area=area
            )
            self._dock_widgets[key] = dock_wdg

    def _add_dock_widget(
        self,
        widget: QWidget,
        name: str,
        floating: bool,
        tabify: bool,
        area: str,
    ) -> QDockWidget:
        """Add a docked widget using napari's add_dock_widget."""
        dock_wdg = self.viewer.window.add_dock_widget(
            widget,
            name=name,
            area=area,
            tabify=tabify,
        )
        # fix napari bug that makes dock widgets too large
        with contextlib.suppress(AttributeError):
            self.viewer.window._qt_window.resizeDocks(
                [dock_wdg], [widget.sizeHint().width() + 20], Qt.Orientation.Horizontal
            )
        with contextlib.suppress(AttributeError):
            dock_wdg._close_btn = False
        dock_wdg.setFloating(floating)
        return dock_wdg


class ScrollableWidget(QWidget):
    valueChanged = Signal()

    """A QWidget with a QScrollArea."""

    def __init__(self, parent: QWidget | None = None, *, title: str, widget: QWidget):
        super().__init__(parent)
        self.setWindowTitle(title)
        # create the scroll area and add the widget to it
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        layout = QHBoxLayout(self)
        layout.addWidget(self.scroll_area)
        # set the widget to the scroll area
        self.scroll_area.setWidget(widget)
        # resize the dock widget to the size hint of the widget
        self.resize(widget.minimumSizeHint())


# -------------- Toolbars --------------------


class MMToolBar(QToolBar):
    def __init__(self, title: str, parent: QWidget = None) -> None:
        super().__init__(title, parent)
        self.setMinimumHeight(48)
        self.setObjectName(f"MM-{title}")

        self.frame = QFrame()
        gb_layout = QHBoxLayout(self.frame)
        gb_layout.setContentsMargins(0, 0, 0, 0)
        gb_layout.setSpacing(2)
        self.addWidget(self.frame)

    def addSubWidget(self, wdg: QWidget) -> None:
        cast("QHBoxLayout", self.frame.layout()).addWidget(wdg)


# class ConfigToolBar(MMToolBar):
#     def __init__(self, parent: QWidget) -> None:
#         super().__init__("Configuration", parent)
#         self.addSubWidget(ConfigurationWidget())
#         self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class ObjectivesToolBar(MMToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Objectives", parent=parent)
        self._wdg = ObjectivesWidget()
        self.addSubWidget(self._wdg)


class ChannelsToolBar(MMToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Channels", parent)
        self.addSubWidget(QLabel(text="Channel:"))
        self.addSubWidget(ChannelGroupWidget())
        self.addSubWidget(ChannelWidget())


class ExposureToolBar(MMToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Exposure", parent)
        self.addSubWidget(QLabel(text="Exposure:"))
        self.addSubWidget(DefaultCameraExposureWidget())


class SnapLiveToolBar(MMToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Snap Live", parent)
        snap_btn = SnapButton()
        snap_btn.setText("")
        snap_btn.setToolTip("Snap")
        snap_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.addSubWidget(snap_btn)

        live_btn = LiveButton()
        live_btn.setText("")
        live_btn.setToolTip("Live Mode")
        live_btn.button_text_off = ""
        live_btn.button_text_on = ""
        live_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.addSubWidget(live_btn)


class ToolsToolBar(MMToolBar):
    """A QToolBar containing QPushButtons for pymmcore-widgets.

    e.g. Property Browser, GroupPresetTableWidget, ...

    QPushButtons are connected to the `_show_dock_widget` method.

    The QPushButton.whatsThis() property is used to store the key that
    will be used by the `_show_dock_widget` method.
    """

    def __init__(self, parent: MicroManagerToolbar) -> None:
        super().__init__("Tools", parent)

        if not isinstance(parent, MicroManagerToolbar):
            raise TypeError("parent must be a MicroManagerToolbar instance.")

        for key in DOCK_WIDGETS:
            btn_icon = DOCK_WIDGETS[key][1]
            if btn_icon is None:
                continue

            btn = QPushButton()
            btn.setToolTip(key)
            btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
            btn.setIcon(icon(btn_icon, color=(0, 255, 0)))
            btn.setIconSize(QSize(30, 30))
            btn.setWhatsThis(key)
            btn.clicked.connect(parent._show_dock_widget)
            self.addSubWidget(btn)

        btn = QPushButton("MDA")
        btn.setToolTip("MultiDimensional Acquisition")
        btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        btn.setWhatsThis("MDA")
        btn.clicked.connect(parent._show_dock_widget)
        self.addSubWidget(btn)


class ShuttersToolBar(MMToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Shutters", parent)
        self.addSubWidget(MMShuttersWidget())
