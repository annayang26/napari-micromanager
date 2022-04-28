from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_plus import CMMCorePlus, DeviceType

if TYPE_CHECKING:
    from pymmcore_plus import RemoteMMCore


class AutofocusDevice:
    def __init__(self, mmcore: CMMCorePlus | RemoteMMCore):
        super().__init__()
        self._mmc = mmcore

    @classmethod
    def create(cls, key, mmcore: CMMCorePlus | RemoteMMCore) -> AutofocusDevice:

        if key == "TIPFSStatus":
            return NikonTiPFS(mmcore)

        if key == "ZeissDefiniteFocus":
            return ZeissDefiniteFocus(mmcore)

        dtype = mmcore.getDeviceType(key)
        if dtype is DeviceType.AutoFocus:
            raise NameError(f"{key} is not yet implemented.")
        else:
            raise NameError(f"{key} is not of type 'AutoFocus'.")

    def getState(self, autofocus_device) -> bool:
        state = self._mmc.getProperty(autofocus_device, "State")
        return state == "On" 

    def setState(self, autofocus_device, state: bool):
        on_off = "On" if state else "Off"
        return self._mmc.setProperty(autofocus_device, "State", on_off)

    def isEnabled(self) -> bool:
        return self._mmc.isContinuousFocusEnabled()

    def isLocked(self) -> bool:
        return self._mmc.isContinuousFocusLocked()
    
    def inRange(self, autofocus_device) -> bool:
       status = self._mmc.getProperty(autofocus_device, "State")
       return status == "Within range of focus search"

    def isFocusing(self, autofocus_device) -> bool:
        status = self._mmc.getProperty(autofocus_device, "State")
        return status == "Focusing"

    def set_offset(self, offset_device, offset: float) -> None:
        self._mmc.setProperty(offset_device, "Position", offset)

    def get_position(self, offset_device) -> float:
        return float(self._mmc.getProperty(offset_device, "Position"))


class NikonTiPFS(AutofocusDevice):
    """
    Nikon Ti Perfect Focus System (PFS) autofocus device.

    To be used when `mmcore.getAutoFocusDevice()` returns `"TIPFStatus"`.
    """

    offset_device: str = "TIPFSOffset"
    autofocus_device: str = "TIPFSStatus"


class ZeissDefiniteFocus(AutofocusDevice):
    # NOT TESTED
    """
    Zeiss DefiniteFocus System autofocus device.

    To be used when `mmcore.getAutoFocusDevice()` returns `"ZeissDefiniteFocus"`.
    """

    offset_device: str = "ZeissDefiniteFocusOffset"
    autofocus_device: str = "ZeissDefiniteFocus"
