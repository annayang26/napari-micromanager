from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pymmcore_widgets.mda import MDAWidget
from qtpy.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from napari_micromanager._util import NMM_METADATA_KEY

from ._arduino_led_stimulation import ArduinoLedControl, StimulationValues

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from useq import MDASequence
GREEN = "#00FF00"
RED = "#C33"
FIXED = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
STIMULATION = "stimulation"


class ArduinoLedWidget(QGroupBox):
    """Widget to enable LED stimulation with Arduino."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)

        self.setTitle("Arduino")

        self._arduino_led_control = ArduinoLedControl(self)

        self._settings_btn = QPushButton("Arduino LED Settings...")
        self._settings_btn.setSizePolicy(FIXED)
        self._settings_btn.clicked.connect(self._show_settings)

        self._enable_led = QCheckBox("Enable Arduino LED stimulation")
        self._enable_led.setSizePolicy(FIXED)

        self._arduino_connected_icon = QLabel()
        self._arduino_connected_icon.setSizePolicy(FIXED)
        self._arduino_connected_text = QLabel()
        self._arduino_connected_text.setSizePolicy(FIXED)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        layout.addWidget(self._enable_led)
        layout.addWidget(self._settings_btn)
        layout.addStretch(1)

    def value(self) -> StimulationValues | dict:
        """Return the current value of the widget."""
        if self._enable_led.isChecked() and self._arduino_led_control._arduino_board:
            return self._arduino_led_control.value()
        return {}

    def setValue(self, value: StimulationValues | dict) -> None:
        """Set the current value of the widget."""
        if value:
            self._enable_led.setChecked(True)
            self._arduino_led_control.setValue(value)
        else:
            self._enable_led.setChecked(False)

    def _show_settings(self) -> None:
        """Show the settings dialog."""
        if self._arduino_led_control.isVisible():
            self._arduino_led_control.raise_()
        else:
            self._arduino_led_control.show()


class MultiDWidget(MDAWidget):
    """Main napari-micromanager GUI."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        # add split channel checkbox
        self.checkBox_split_channels = QCheckBox(text="Split channels in viewer")
        super().__init__(parent=parent, mmcore=mmcore)

        # setContentsMargins
        pos_layout = cast("QVBoxLayout", self.stage_positions.layout())
        pos_layout.setContentsMargins(10, 10, 10, 10)
        time_layout = cast("QVBoxLayout", self.time_plan.layout())
        time_layout.setContentsMargins(10, 10, 10, 10)
        ch_layout = cast("QVBoxLayout", self.channels.layout())
        ch_layout.setContentsMargins(10, 10, 10, 10)
        ch_layout.addWidget(self.checkBox_split_channels)

        self._arduino_led_wdg = ArduinoLedWidget(self)
        self.layout().insertWidget(3, self._arduino_led_wdg)

    def value(self) -> MDASequence:
        """Return the current value of the widget."""
        # Overriding the value method to add the metadata necessary for the handler.
        sequence = super().value()
        split = self.checkBox_split_channels.isChecked() and len(sequence.channels) > 1
        sequence.metadata[NMM_METADATA_KEY] = {
            "split_channels": split,
            STIMULATION: self._arduino_led_wdg.value(),
        }
        return sequence  # type: ignore[no-any-return]

    def setValue(self, value: MDASequence) -> None:
        """Set the current value of the widget."""
        if nmm_meta := value.metadata.get(NMM_METADATA_KEY):
            # set split_channels checkbox
            self.checkBox_split_channels.setChecked(
                nmm_meta.get("split_channels", False)
            )
            # update arduino led widget
            if nmm_meta.get(STIMULATION):
                self._arduino_led_wdg.setValue(nmm_meta[STIMULATION])

        super().setValue(value)

    def run_mda(self) -> None:
        """Run the MDA sequence experiment."""
        # in case the user does not press enter after editing the save name.
        self.save_info.save_name.editingFinished.emit()

        # if autofocus has been requested, but the autofocus device is not engaged,
        # and position-specific offsets haven't been set, show a warning
        pos = self.stage_positions
        if (
            self.af_axis.value()
            and not self._mmc.isContinuousFocusLocked()
            and (not self.tab_wdg.isChecked(pos) or not pos.af_per_position.isChecked())
            and not self._confirm_af_intentions()
        ):
            return

        # this is just to make sure that the Arduino and the Pin are available
        # we also set which Arduino and which Pin are being used
        self._arduino_led_wdg._arduino_led_control.hide()
        if self._arduino_led_wdg._enable_led.isChecked():
            arduino = self._arduino_led_wdg._arduino_led_control._arduino_board
            led = self._arduino_led_wdg._arduino_led_control._led_pin
            if arduino is None or led is None:
                self._show_critical_led_message()
                return
            try:
                led.write(0.0)
                self._mmc.mda.engine.setArduinoBoard(arduino)
                self._mmc.mda.engine.setArduinoLedPin(led)
            except Exception as e:
                self._mmc.mda.engine.setArduinoBoard(None)
                self._mmc.mda.engine.setArduinoLedPin(None)
                print(e)
                self._show_critical_led_message()
                return
        else:
            self._mmc.mda.engine.setArduinoBoard(None)
            self._mmc.mda.engine.setArduinoLedPin(None)

        sequence = self.value()

        # technically, this is in the metadata as well, but isChecked is more direct
        if self.save_info.isChecked():
            save_path = self._update_save_path_from_metadata(
                sequence, update_metadata=True
            )
        else:
            save_path = None

        # run the MDA experiment asynchronously
        self._mmc.run_mda(sequence, output=save_path)

    def _show_critical_led_message(self) -> None:
        msg = (
            "'Arduino LED Stimulation' is selected but an error occurred while trying "
            "to communicate with the Arduino. \nPlease, verify that the device is "
            "connected and try again."
        )
        QMessageBox.critical(
            self,
            "Arduino Error",
            msg,
            QMessageBox.StandardButton.Ok,
            QMessageBox.StandardButton.Ok,
        )
        return
