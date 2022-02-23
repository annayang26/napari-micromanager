import re
from dataclasses import dataclass
from typing import Any, Sequence

from magicgui.widgets import (
    ComboBox,
    Container,
    FloatSlider,
    LineEdit,
    PushButton,
    Slider,
    Widget,
)
from pymmcore_plus import DeviceType, PropertyType
from qtpy.QtWidgets import QDialog, QVBoxLayout

from .prop_browser import iter_dev_props

LIGHT_LIST = re.compile("(Intensity|Power|test)s?", re.IGNORECASE)  # for testing


@dataclass
class PropertyItem:
    device: str
    dev_type: DeviceType
    name: str
    value: Any
    read_only: bool
    pre_init: bool
    has_range: bool
    lower_lim: float
    upper_lim: float
    prop_type: PropertyType
    allowed: Sequence[str]


class IlluminationDialog(QDialog):
    def __init__(self, mmcore=None, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self._container = Container(
            widgets=[
                self.get_editor_widget(prop, mmcore)
                for prop in iter_dev_props(mmcore)
                if LIGHT_LIST.search(prop.name) and prop.has_range
            ],
            labels=True,
        )
        self.layout().addWidget(self._container.native)

    def get_editor_widget(self, prop: PropertyItem, mmc) -> Widget:
        wdg = None
        if prop.allowed:
            wdg = ComboBox(value=prop.value, choices=prop.allowed)
        elif prop.has_range:
            if PropertyType(prop.prop_type).name == "Float":
                wdg = FloatSlider(
                    value=float(prop.value),
                    min=float(prop.lower_lim),
                    max=float(prop.upper_lim),
                    label=f"{prop.device} {prop.name}",
                )

                push_button = PushButton(text="TEST")

            else:
                wdg = Slider(
                    value=int(prop.value),
                    min=int(prop.lower_lim),
                    max=int(prop.upper_lim),
                    label=f"{prop.device} {prop.name}",
                )

                push_button = PushButton(text="TEST")
        else:
            wdg = LineEdit(value=prop.value)

        widget = Container(layout="horizontal", widgets=[wdg, push_button], labels=True)

        @wdg.changed.connect
        def _on_change(value: Any):
            mmc.setProperty(prop.device, prop.name, value)

        @push_button.clicked.connect
        def _on_click():
            print("clicked!")

        return widget
