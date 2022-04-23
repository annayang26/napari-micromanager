from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus, RemoteMMCore


class AutofocusDevice:
    def __init__(self, mmcore: CMMCorePlus | RemoteMMCore):
        super().__init__()
        self._mmc = mmcore

    @classmethod
    def create(cls, key, mmcore) -> AutofocusDevice:

        # if not key:
        #     raise

        if key == "Autofocus":
            return Test(mmcore)

        elif key == "TIPFSStatus":
            return NikonPFS(mmcore)

    def isEngaged(self) -> bool:
        return self._mmc.isContinuousFocusEnabled()

    def isLocked(self) -> bool:
        return self._mmc.isContinuousFocusLocked()

    def isFocusing(self, autofocus_device) -> bool:
        status = self._mmc.getProperty(autofocus_device, "State")
        return status == "Focusing"

    def set_offset(self, offset_device, offset: float) -> None:
        self._mmc.setProperty(offset_device, "Position", offset)

    def get_position(self, offset_device) -> float:
        return float(self._mmc.getProperty(offset_device, "Position"))


class Test(AutofocusDevice):
    """
    Micro-Manager demo 'Autofocus' device.

    To be used in combination with a demo 'Stage'
    that has to be renamed 'AF_Stage'.
    """

    offset_device: str = "AF_Stage"
    autofocus_device: str = "Autofocus"


class NikonPFS(AutofocusDevice):
    """
    Nikon Perfect Focus System (PFS) autofocus device.

    To be used when `mmcore.getAutoFocusDevice()` returns `"TIPFStatus"`.
    """

    offset_device: str = "TIPFSOffset"
    autofocus_device: str = "TIPFStatus"
