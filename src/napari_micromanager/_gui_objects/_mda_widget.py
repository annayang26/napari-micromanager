from __future__ import annotations

from pathlib import Path
from typing import cast

from napari_micromanager._mda_meta import SEQUENCE_META_KEY, SequenceMeta
from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import MDAWidget
from pymmcore_widgets._mda import GridWidget, PositionTable
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSizePolicy,
    QSpacerItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from useq import MDASequence

from ._save_widget import SaveWidget


class MultiDWidget(MDAWidget):
    """Main napari-micromanager GUI."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(include_run_button=True, parent=parent, mmcore=mmcore)

        v_layout = cast(QVBoxLayout, self._central_widget.layout())
        self._save_groupbox = SaveWidget()
        self._save_groupbox.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self._save_groupbox.setChecked(False)
        v_layout.insertWidget(0, self._save_groupbox)

        self.channel_groupbox.setMinimumHeight(230)
        self.checkBox_split_channels = QCheckBox(text="Split Channels")
        self.checkBox_split_channels.toggled.connect(self._toggle_split_channel)
        g_layout = cast(QGridLayout, self.channel_groupbox.layout())
        g_layout.addWidget(self.checkBox_split_channels, 1, 0)

        self._save_groupbox.toggled.connect(self._toggle_checkbox_save_pos)

        self.channel_groupbox._table.model().rowsRemoved.connect(
            self._toggle_split_channel
        )

        # the self.position_groupbox variable will be then used to define if
        # the sequence will take positions info from single positions or grid
        # positions tab (see _on_tab_changed method). Maybe find a better way?
        self.position_groupbox: PositionTable
        self._update_position_widget()

    def _update_position_widget(self) -> None:
        self.single_position_groupbox = self.position_groupbox

        # create tab
        tab = QTabWidget()
        self._central_widget.layout().removeWidget(self.single_position_groupbox)
        self._central_widget.layout().addWidget(tab)

        # single positions tab
        pos_tab = self._create_single_position_tab()
        tab.addTab(pos_tab, "Single Positions")

        # grid tab
        grid_tab = self._create_grid_position_tab()
        tab.addTab(grid_tab, "Grid Positions")

        # connect tab signal
        tab.currentChanged.connect(self._on_tab_changed)

    def _create_grid_position_tab(self) -> QWidget:
        grid_tab = QWidget()
        grid_tab_layout = QVBoxLayout()
        grid_tab_layout.setSpacing(0)
        grid_tab_layout.setContentsMargins(10, 10, 10, 10)
        grid_tab.setLayout(grid_tab_layout)

        # Position table
        self.grid_position_groupbox = PositionTable("Grid Positions")
        self.grid_position_groupbox.stage_tableWidget.setMinimumHeight(175)
        self.grid_position_groupbox.layout().setSpacing(0)
        self.grid_position_groupbox.layout().setContentsMargins(0, 7, 0, 0)
        self.grid_position_groupbox.add_pos_button.hide()
        self.grid_position_groupbox.grid_button.hide()

        self.grid_position_groupbox.toggled.connect(self._on_grid_pos_toggled)
        self.grid_position_groupbox.remove_pos_button.clicked.connect(
            self._on_grid_pos_toggled
        )
        self.grid_position_groupbox.clear_pos_button.clicked.connect(
            self._on_grid_pos_toggled
        )

        # remove table, buttons from layout
        widgets = [
            self.grid_position_groupbox.layout().itemAt(i).widget()
            for i in range(self.single_position_groupbox.layout().count())
        ]
        _table, _btns = widgets[0], widgets[1]
        self.grid_position_groupbox.layout().removeWidget(_table)
        self.grid_position_groupbox.layout().removeWidget(_btns)

        # table_btns groupbox
        table_btns_group = QWidget()
        table_btns_group.setLayout(QHBoxLayout())
        table_btns_group.layout().setSpacing(15)
        table_btns_group.layout().setContentsMargins(0, 0, 0, 0)
        table_btns_group.layout().addWidget(_table)
        table_btns_group.layout().addWidget(_btns)

        # grid widget
        self.grid_control = GridWidget()
        self.grid_control.layout().setContentsMargins(0, 0, 0, 0)
        self.grid_control.clear_checkbox.setChecked(False)
        self.grid_control.clear_checkbox.hide()
        self.grid_control.sendPosList.connect(
            self.grid_position_groupbox._add_grid_positions_to_table
        )

        grid_wdgs = [
            self.grid_control.layout().itemAt(i).widget()
            for i in range(self.grid_control.layout().count())
        ]
        grid_wdgs[0].setTitle("")
        grid_wdgs[0].layout().setContentsMargins(5, 5, 5, 5)

        grid_wdgs[0].layout().removeWidget(self.grid_control.info_lbl)
        info_wdg = QWidget()
        info_wdg.setLayout(QHBoxLayout())
        info_wdg.layout().setSpacing(0)
        info_wdg.layout().setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Grid Size (mm):")
        lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        info_wdg.layout().addWidget(lbl)
        info_wdg.layout().addWidget(self.grid_control.info_lbl)
        grid_wdgs[0].layout().addWidget(info_wdg, 1, 1)

        # remove generate_position_btn from layout
        gen_btn = self.grid_control.generate_position_btn
        gen_btn.setText("Add")
        gen_btn.setMinimumWidth(100)
        grid_wdgs[1].layout().removeWidget(gen_btn)
        # add generate_position_btn to table buttons layout
        _btns.layout().insertWidget(0, gen_btn)

        # create new widget for grid_position_groupbox
        new_wdg = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(10, 0, 10, 10)
        new_wdg.setLayout(layout)

        layout.addWidget(self.grid_control)
        layout.addWidget(table_btns_group)
        display_options = self._create_radiobtn()
        layout.addWidget(display_options)

        self.grid_position_groupbox.layout().addWidget(new_wdg)

        grid_tab_layout.addWidget(self.grid_position_groupbox)

        return grid_tab

    def _create_single_position_tab(self) -> QWidget:
        pos_tab = QWidget()
        pos_tab_layout = QHBoxLayout()
        pos_tab_layout.setSpacing(0)
        pos_tab_layout.setContentsMargins(10, 10, 10, 10)
        pos_tab_layout.addWidget(self.single_position_groupbox)
        pos_tab.setLayout(pos_tab_layout)

        self.single_position_groupbox.grid_button.hide()
        self.single_position_groupbox.toggled.connect(self._toggle_checkbox_save_pos)
        self.single_position_groupbox.add_pos_button.clicked.connect(
            self._toggle_checkbox_save_pos
        )
        self.single_position_groupbox.remove_pos_button.clicked.connect(
            self._toggle_checkbox_save_pos
        )
        self.single_position_groupbox.clear_pos_button.clicked.connect(
            self._toggle_checkbox_save_pos
        )

        return pos_tab

    def _create_radiobtn(self) -> QGroupBox:

        group = QGroupBox()
        group_layout = QHBoxLayout()
        group_layout.setSpacing(15)
        group_layout.setContentsMargins(5, 5, 5, 5)
        group.setLayout(group_layout)

        fixed_policy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        lbl = QLabel("Dispaly as:")
        lbl.setSizePolicy(fixed_policy)
        group_layout.addWidget(lbl)

        self.radiobtn_grid = QRadioButton(text=" grid (layers translation)")
        self.radiobtn_grid.setSizePolicy(fixed_policy)
        self.radiobtn_grid.setChecked(True)
        self.radiobtn_multid_stack = QRadioButton(text=" multi-dimensional stack")
        self.radiobtn_multid_stack.setSizePolicy(fixed_policy)

        group_layout.addWidget(self.radiobtn_grid)

        group_layout.addWidget(self.radiobtn_multid_stack)

        spacer = QSpacerItem(
            10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        group_layout.addItem(spacer)

        return group

    def _on_tab_changed(self, idx: int) -> None:
        if idx == 0:
            self.position_groupbox = self.single_position_groupbox
            self.grid_position_groupbox.setChecked(False)
        elif idx == 1:
            self.position_groupbox = self.grid_position_groupbox
            self.single_position_groupbox.setChecked(False)
            self.checkBox_split_channels.setChecked(False)
            self._save_groupbox._split_pos_checkbox.setChecked(False)

    def _on_grid_pos_toggled(self) -> None:
        self._save_groupbox._split_pos_checkbox.setChecked(False)
        self.checkBox_split_channels.setChecked(False)

    def _toggle_split_channel(self) -> None:
        if (
            self.channel_groupbox._table.rowCount() <= 1
            or self.grid_position_groupbox.isChecked()
        ):
            self.checkBox_split_channels.setChecked(False)

    def _toggle_checkbox_save_pos(self) -> None:
        if (
            self.single_position_groupbox.isChecked()
            and self.single_position_groupbox.stage_tableWidget.rowCount() > 0
        ):
            self._save_groupbox._split_pos_checkbox.setEnabled(True)

        else:
            self._save_groupbox._split_pos_checkbox.setCheckState(
                Qt.CheckState.Unchecked
            )
            self._save_groupbox._split_pos_checkbox.setEnabled(False)

    def get_state(self) -> MDASequence:
        sequence = cast(MDASequence, super().get_state())

        # if grid, mode = explorer

        sequence.metadata[SEQUENCE_META_KEY] = SequenceMeta(
            mode="mda",
            split_channels=self.checkBox_split_channels.isChecked(),
            **self._save_groupbox.get_state(),
        )
        return sequence

    def set_state(self, state: dict | MDASequence | str | Path) -> None:
        super().set_state(state)
        meta = None
        if isinstance(state, dict):
            meta = state.get("metadata", {}).get(SEQUENCE_META_KEY)
        elif isinstance(state, MDASequence):
            meta = state.metadata.get(SEQUENCE_META_KEY)

        if meta is None:
            return
        if not isinstance(meta, SequenceMeta):
            raise TypeError(f"Expected {SequenceMeta}, got {type(meta)}")
        if meta.mode.lower() != "mda":
            raise ValueError(f"Expected mode 'mda', got {meta.mode}")

        self.checkBox_split_channels.setChecked(meta.split_channels)
        self._save_groupbox.set_state(meta)
