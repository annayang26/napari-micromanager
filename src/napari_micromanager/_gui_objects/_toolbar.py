from __future__ import annotations

import contextlib
from functools import partial
from typing import TYPE_CHECKING, Any, Dict, Tuple, cast

from fonticon_mdi6 import MDI6
from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import (
    CameraRoiWidget,
    ChannelGroupWidget,
    ChannelWidget,
    ConfigurationWidget,
    DefaultCameraExposureWidget,
    GroupPresetTableWidget,
    LiveButton,
    ObjectivesWidget,
    PropertyBrowser,
    SnapButton,
)
from qtpy.QtGui import QFont

try:
    # this was renamed
    from pymmcore_widgets import ObjectivesPixelConfigurationWidget
except ImportError:
    from pymmcore_widgets import PixelSizeWidget as ObjectivesPixelConfigurationWidget

from qtpy.QtCore import QEvent, QObject, QSize, Qt
from qtpy.QtWidgets import (
    QAction,
    QDockWidget,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QToolBar,
    QToolButton,
    QWidget,
)
from superqt.fonticon import icon

from ._illumination_widget import IlluminationWidget
from ._mda_widget import MultiDWidget
from ._min_max_widget import MinMax
from ._shutters_widget import MMShuttersWidget
from ._stages_widget import MMStagesWidget

if TYPE_CHECKING:
    import napari.viewer

TOOL_SIZE = 35


# Dict for QObject and its QPushButton icon
DOCK_WIDGETS: Dict[str, Tuple[type[QWidget], str | None]] = {  # noqa: U006
    "Device Property Browser": (PropertyBrowser, MDI6.table_large),
    "Groups and Presets Table": (GroupPresetTableWidget, MDI6.table_large_plus),
    "Illumination Control": (IlluminationWidget, MDI6.lightbulb_on),
    "Stages Control": (MMStagesWidget, MDI6.arrow_all),
    "Camera ROI": (CameraRoiWidget, MDI6.crop),
    "Pixel Size Table": (ObjectivesPixelConfigurationWidget, MDI6.ruler),
    "MDA": (MultiDWidget, None),
}


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

        self._dock_widgets: dict[str, QDockWidget] = {}

        # __________Menu Toolbar____________________________________________________
        menu_toolbar = QToolBar("Main Toolbar", self)
        menu_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, menu_toolbar)
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)

        # __________Separator_______________________________________________________
        # NOTE: it does not work in napari, why?
        # separator_toolbar = QToolBar("Separator", self)
        # separator_toolbar.setMovable(False)
        # self.addToolBar(Qt.ToolBarArea.TopToolBarArea, separator_toolbar)
        # self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        # self.sep = QFrame()
        # self.sep.setFrameShape(QFrame.Shape.HLine)
        # self.sep.setFrameShadow(QFrame.Shadow.Plain)
        # separator_toolbar.addWidget(self.sep)

        # __________Configurations__________________________________________________
        self._config_btn = self._create_toolbutton("Configurations")
        menu_toolbar.addWidget(self._config_btn)

        config_menu = QMenu("Configurations", self)
        self._config_btn.setMenu(config_menu)

        self.act_load_cfg = QAction("Load System Configuration", self)
        config_menu.addAction(self.act_load_cfg)
        self.act_load_cfg.triggered.connect(self._browse_cfg)

        self.act_config_wizard = QAction("Hardware Configuration Wizard", self)
        config_menu.addAction(self.act_config_wizard)

        # __________Layout__________________________________________________________
        self._layout_btn = self._create_toolbutton("Layout")
        menu_toolbar.addWidget(self._layout_btn)

        layout_menu = QMenu("Layout", self)
        self._layout_btn.setMenu(layout_menu)

        self.act_save_layout = QAction("Save Layout", self)
        layout_menu.addAction(self.act_save_layout)
        self.act_save_layout.triggered.connect(self.get_layout_state)

        self.act_load_layout = QAction("Load Layout", self)
        layout_menu.addAction(self.act_load_layout)

        # __________Toolsbar_________________________________________________________
        self._toolbar_btn = self._create_toolbutton("Toolbar")
        menu_toolbar.addWidget(self._toolbar_btn)

        toolbar_menu = QMenu("Toolbar", self)
        self._toolbar_btn.setMenu(toolbar_menu)

        toolbar_items: list[QWidget] = [
            ChannelsToolBar(self),
            ExposureToolBar(self),
            SnapLiveToolBar(self),
            ShuttersToolBar(self),
            Widgets(self),
        ]

        for item in toolbar_items:
            if item:
                checked = True
                if isinstance(item, Widgets):
                    item.hide()
                    checked = False
                act = QAction(item.windowTitle(), self, checkable=True, checked=checked)
                act.triggered.connect(partial(self._toggle_toolbar, item))
                toolbar_menu.addAction(act)

        # __________Widgets__________________________________________________________

        self._widgets_btn = self._create_toolbutton("Widgets")
        menu_toolbar.addWidget(self._widgets_btn)

        widgets_menu = QMenu("Widgets", self)
        self._widgets_btn.setMenu(widgets_menu)

        for wdg in DOCK_WIDGETS:
            act = QAction(wdg, self)
            act.triggered.connect(partial(self._show_dock_widget, wdg))
            widgets_menu.addAction(act)

        for item in toolbar_items:
            if item:
                self.addToolBar(Qt.ToolBarArea.TopToolBarArea, item)
            else:
                self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)

        # if "Groups and Presets Table" not in list(viewer.window._dock_widgets):
        #     self._show_dock_widget("Groups and Presets Table")

        # __________________________________________________________________________

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

    def contextMenuEvent(self, event: Any) -> None:
        """Remove actions from the context menu."""
        menu = self.createPopupMenu()
        for action in menu.actions():
            menu.removeAction(action)
        menu.exec_(event.globalPos())

    def _toggle_toolbar(self, toolbar: QToolBar) -> None:
        if toolbar.isVisible():
            toolbar.hide()
        else:
            toolbar.show()

    def _browse_cfg(self) -> None:
        """Open file dialog to select a config file."""
        (config, _) = QFileDialog.getOpenFileName(
            self, "Select a Micro-Manager configuration file", "", "cfg(*.cfg)"
        )
        if config:
            self._mmc.unloadAllDevices()
            self._mmc.loadSystemConfiguration(config)

    def _create_toolbutton(self, text: str) -> QToolButton:
        tool_btn = QToolButton()
        tool_btn.setText(text)
        tool_btn.setFont(QFont("Arial", 14))
        tool_btn.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        tool_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        tool_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        return tool_btn

    def get_layout_state(self) -> None:  # -> dict[str, Any]:
        """Return the current state of the viewer layout."""
        print()
        for dk in self.viewer.window._dock_widgets:
            wdg = self.viewer.window._dock_widgets[dk]
            print(dk, wdg.pos(), wdg.isFloating(), wdg.isVisible(), wdg.area)

    def _show_dock_widget(self, key: str = "") -> None:
        """Look up widget class in DOCK_WIDGETS and add/create or show/raise.

        `key` must be a key in the DOCK_WIDGETS dict or a `str` stored in
        the `whatsThis` property of a `sender` `QPushButton`.
        """
        floating = False
        tabify = True
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
            dock_wdg = self._add_dock_widget(wdg, key, floating=floating, tabify=tabify)
            self._dock_widgets[key] = dock_wdg

    def _add_dock_widget(
        self, widget: QWidget, name: str, floating: bool = False, tabify: bool = False
    ) -> QDockWidget:
        """Add a docked widget using napari's add_dock_widget."""
        dock_wdg = self.viewer.window.add_dock_widget(
            widget,
            name=name,
            area="right",
            tabify=tabify,
        )
        # fix napari bug that makes dock widgets too large
        with contextlib.suppress(AttributeError):
            self.viewer.window._qt_window.resizeDocks(
                [dock_wdg], [widget.sizeHint().width()], Qt.Orientation.Horizontal
            )
        with contextlib.suppress(AttributeError):
            dock_wdg._close_btn = False
        dock_wdg.setFloating(floating)
        return dock_wdg


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


class ConfigToolBar(MMToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Configuration", parent)
        self.addSubWidget(ConfigurationWidget())
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


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
        snap_btn.setIcon(icon(MDI6.camera_outline))
        snap_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.addSubWidget(snap_btn)

        live_btn = LiveButton()
        live_btn.setText("")
        live_btn.setToolTip("Live Mode")
        live_btn.button_text_off = ""
        live_btn.button_text_on = ""
        live_btn.icon_color_on = ""
        live_btn.icon_color_off = "magenta"
        live_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.addSubWidget(live_btn)


class Widgets(MMToolBar):
    """A QToolBar containing QPushButtons for pymmcore-widgets.

    e.g. Property Browser, GroupPresetTableWidget, ...

    QPushButtons are connected to the `_show_dock_widget` method.

    The QPushButton.whatsThis() property is used to store the key that
    will be used by the `_show_dock_widget` method.
    """

    def __init__(self, parent: MicroManagerToolbar) -> None:
        super().__init__("Widgets", parent)

        if not isinstance(parent, MicroManagerToolbar):
            raise TypeError("parent must be a MicroManagerToolbar instance.")

        for key in DOCK_WIDGETS:
            btn_icon = DOCK_WIDGETS[key][1]
            if btn_icon is None:
                continue

            btn = QPushButton()
            btn.setToolTip(key)
            btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
            btn.setIcon(icon(btn_icon))
            btn.setIconSize(QSize(30, 30))
            btn.setWhatsThis(key)
            btn.clicked.connect(parent._show_dock_widget)
            self.addSubWidget(btn)

        btn = QPushButton("MDA")
        btn.setStyleSheet("color: black;")
        btn.setToolTip("MultiDimensional Acquisition")
        btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        btn.setWhatsThis("MDA")
        btn.clicked.connect(parent._show_dock_widget)
        self.addSubWidget(btn)


class ShuttersToolBar(MMToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Shutters", parent)
        self.addSubWidget(MMShuttersWidget())
