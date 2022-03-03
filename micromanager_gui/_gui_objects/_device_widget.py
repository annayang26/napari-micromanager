from dataclasses import dataclass
from typing import Any, Iterator, Optional, Sequence, Tuple, TypeVar

from magicgui.widgets import ComboBox, FloatSlider, LineEdit, Slider, Table, Widget
from pymmcore_plus import DeviceType, PropertyType
from qtpy import QtWidgets as QtW
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QVBoxLayout, QWidget
from superqt.utils import signals_blocked

from .._core import get_core_singleton

T = TypeVar("T", bound="DeviceWidget")


class DeviceWidget(QWidget):
    """Base Device Widget.

    Use `DeviceWidget.for_device('someLabel')` to create the device-type
    appropriate subclass.
    """

    def __init__(self, device_label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._device_label = device_label
        self._mmc = get_core_singleton()

    def deviceName(self) -> str:
        return self._mmc.getDeviceName(self._device_label)

    def deviceLabel(self) -> str:
        return self._device_label

    @classmethod
    def for_device(cls, label: str):
        core = get_core_singleton()
        dev_type = core.getDeviceType(label)
        _map = {
            DeviceType.StateDevice: StateDeviceWidget,
            DeviceType.CameraDevice: CameraDeviceWidget,
        }
        return _map[dev_type](label)


class StateDeviceWidget(DeviceWidget):
    """Widget to control a StateDevice."""

    def __init__(self, device_label: str, parent: Optional[QWidget] = None):
        super().__init__(device_label, parent)
        assert self._mmc.getDeviceType(device_label) == DeviceType.StateDevice

        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(self._on_combo_changed)
        self._refresh_combo_choices()
        self._combo.setCurrentText(self._mmc.getStateLabel(self._device_label))

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self._combo)

        self._mmc.events.propertyChanged.connect(self._on_prop_change)
        self.destroyed.connect(self._disconnect)

    def _on_combo_changed(self, index: int) -> None:
        # TODO: add hook here for pre change/post change?
        # e.g. if you wanted to drop the objective before changing
        self._mmc.setState(self._device_label, index)

    def _disconnect(self):
        self._mmc.events.propertyChanged.disconnect(self._on_prop_change)

    def _on_prop_change(self, dev_label: str, prop: str, value: Any):
        # TODO: hmmm... it appears that not all state devices emit
        # a property change event?
        print("PROP CHANGE", locals())
        if dev_label == self._device_label:
            with signals_blocked(self._combo):
                self._combo.setCurrentText(value)

    def _refresh_combo_choices(self):
        with signals_blocked(self._combo):
            self._combo.clear()
            self._combo.addItems(self.stateLabels())

    def state(self) -> int:
        return self._mmc.getState(self._device_label)

    def data(self):
        return self._mmc.getData(self._device_label)

    def stateLabel(self) -> str:
        return self._mmc.getStateLabel(self._device_label)

    def stateLabels(self) -> Tuple[str]:
        return self._mmc.getStateLabels(self._device_label)


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


class PropertyTableWidget(Table):
    def __init__(self) -> None:
        super().__init__()
        hdr = self.native.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        vh = self.native.verticalHeader()
        vh.setSectionResizeMode(vh.Fixed)
        vh.setDefaultSectionSize(25)
        vh.setVisible(False)
        self.native.setEditTriggers(QtW.QTableWidget.NoEditTriggers)
        self.min_width = 500


class CameraDeviceWidget(DeviceWidget):
    """Widget to control a CameraDevice."""

    def __init__(self, device_label: str, parent: Optional[QWidget] = None):
        super().__init__(device_label, parent)
        assert self._mmc.getDeviceType(device_label) == DeviceType.CameraDevice

        self.mmc = get_core_singleton()
        self.mmc.loadSystemConfiguration()

        self.device_label = "Camera"

        self.make_tabler_wdg()

    def iter_dev_props(self, dev) -> Iterator[PropertyItem]:
        for prop in self.mmc.getDevicePropertyNames(dev):
            yield PropertyItem(
                device=dev,
                name=prop,
                dev_type=self.mmc.getDeviceType(dev),
                value=self.mmc.getProperty(dev, prop),
                read_only=self.mmc.isPropertyReadOnly(dev, prop),
                pre_init=self.mmc.isPropertyPreInit(dev, prop),
                has_range=self.mmc.hasPropertyLimits(dev, prop),
                lower_lim=self.mmc.getPropertyLowerLimit(dev, prop),
                upper_lim=self.mmc.getPropertyUpperLimit(dev, prop),
                prop_type=self.mmc.getPropertyType(dev, prop),
                allowed=self.mmc.getAllowedPropertyValues(dev, prop),
            )

    def _set_widget(self, prop: PropertyItem) -> Widget:

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
            else:
                wdg = Slider(
                    value=int(prop.value),
                    min=int(prop.lower_lim),
                    max=int(prop.upper_lim),
                    label=f"{prop.device} {prop.name}",
                )
        else:
            wdg = LineEdit(value=prop.value)

        @wdg.changed.connect
        def _on_change(value: Any):
            self.mmc.setProperty(prop.device, prop.name, wdg.value)
            print(
                f"{prop.device} device {prop.name} property , changed to -> {wdg.value}"
            )

        return wdg

    def make_tabler_wdg(self):

        self.table = PropertyTableWidget()
        data = []
        for p in self.iter_dev_props(self.device_label):
            val = p.value if p.read_only else self._set_widget(p)
            data.append([p.read_only, f"{p.device}-{p.name}", val])
        self.table.value = {
            "data": data,
            "index": [],
            "columns": ["Read_only", "Device-Property", "Value"],
        }
        self.table.native.hideColumn(0)
        for i, (ro, _, _) in enumerate(self.table.data):
            if ro:
                self.table.native.hideRow(i)

        self.setLayout(QVBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.table.native)
