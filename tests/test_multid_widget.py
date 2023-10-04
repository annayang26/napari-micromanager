from __future__ import annotations

from typing import TYPE_CHECKING

from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta
from useq import MDASequence

if TYPE_CHECKING:
    from napari_micromanager.main_window import MainWindow
    from pytestqt.qtbot import QtBot


def test_main_window_mda(main_window: MainWindow):
    assert not main_window.viewer.layers

    mda = MDASequence(
        time_plan={"loops": 4, "interval": 0.1},
        z_plan={"range": 3, "step": 1},
        channels=["DAPI", "FITC"],
        metadata={SEQUENCE_META_KEY: SequenceMeta(mode="mda")},
    )

    main_window._mmc.mda.run(mda)
    assert main_window.viewer.layers[-1].data.shape == (4, 2, 4, 512, 512)
    assert main_window.viewer.layers[-1].data.nchunks_initialized == 32


def test_script_initiated_mda(main_window: MainWindow, qtbot: QtBot):
    # we should show the mda even if it came from outside
    mmc = main_window._mmc
    sequence = MDASequence(
        channels=[{"config": "Cy5", "exposure": 1}, {"config": "FITC", "exposure": 1}],
        time_plan={"interval": 0.1, "loops": 2},
        z_plan={"range": 4, "step": 5},
        axis_order="tpcz",
        stage_positions=[(222, 1, 1), (111, 0, 0)],
        metadata={SEQUENCE_META_KEY: SequenceMeta(mode="mda")},
    )

    with qtbot.waitSignal(mmc.mda.events.sequenceFinished, timeout=5000):
        mmc.run_mda(sequence)

    layer_name = f"Exp_{sequence.uid}"
    viewer = main_window.viewer
    viewer_layer_names = [layer.name for layer in viewer.layers]
    assert layer_name in viewer_layer_names
    assert sequence.shape == viewer.layers[layer_name].data.shape[:-2]
