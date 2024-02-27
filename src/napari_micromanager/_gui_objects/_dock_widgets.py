from __future__ import annotations

from typing import TYPE_CHECKING, Dict, NamedTuple, Tuple

from fonticon_mdi6 import MDI6
from pymmcore_widgets import (
    CameraRoiWidget,
    GroupPresetTableWidget,
    PropertyBrowser,
)

try:
    # this was renamed
    from pymmcore_widgets import ObjectivesPixelConfigurationWidget
except ImportError:
    from pymmcore_widgets import PixelSizeWidget as ObjectivesPixelConfigurationWidget


from ._illumination_widget import IlluminationWidget
from ._mda_widget import MultiDWidget
from ._stages_widget import MMStagesWidget

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget


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


class WidgetState(NamedTuple):
    """A simple state object for storing widget state."""

    name: str
    area: str
    floating: bool
    visible: bool
    tabify_with: list[str]
    geometry: tuple[int, int, int, int]
