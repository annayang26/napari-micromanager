from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

from napari_micromanager._engine._mmcore_engine import ArduinoEngine
from pymmcore_plus import CMMCorePlus
from useq import MDASequence

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from pytestqt.qtbot import QtBot

try:
    import pytestqt
except ImportError:
    pytestqt = None


def test_stimulation_events(core: CMMCorePlus, qtbot: QtBot):
    mda = MDASequence(
        channels=["Cy5"],
        time_plan={"interval": 0, "loops": 8},
        axis_order="ptc",
        stage_positions=[(222, 1, 1), (111, 0, 0)],
        metadata={
            "pymmcore_widgets": {"stimulation": {"pulse_on_frame": {2: 100, 5: 100}}}
        },
    )

    EXPECTED_SEQUENCES = 6  # 0,1 - 2,3,4 - 5,6,7 (* 2 positions)

    core_mock = cast("CMMCorePlus", MagicMock(wraps=core))  # so we can spy on all_calls
    engine = ArduinoEngine(mmc=core_mock)

    assert engine.use_hardware_sequencing
    events = list(engine.event_iterator(mda))
    assert len(events) == EXPECTED_SEQUENCES
