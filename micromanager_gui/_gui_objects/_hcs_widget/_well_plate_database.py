from __future__ import annotations

from pathlib import Path
from typing import Tuple

import yaml

PLATE_DATABASE = Path(__file__).parent / "_well_plate.yaml"


class WellPlate:
    def __init__(self):
        super().__init__()

        self.id = ""
        self.circular = True
        self.rows = 0
        self.cols = 0
        self.well_spacing_x = 0
        self.well_spacing_y = 0
        self.well_size_x = 0
        self.well_size_y = 0

    @classmethod
    def set_format(cls, key: str) -> WellPlate:
        return PlateFromDatabase(key)

    def get_id(self) -> str:
        return self.id

    def get_well_type(self):
        return "round" if self.circular else "squared/rectangular"

    def get_n_wells(self) -> int:
        return self.rows * self.cols

    def get_n_rows(self) -> int:
        return self.rows

    def get_n_columns(self) -> int:
        return self.cols

    def get_well_distance(self) -> Tuple[float, float]:
        return self.well_spacing_x, self.well_spacing_y

    def get_well_size(self) -> Tuple[float, float]:
        return self.well_size_x, self.well_size_y

    def getAllInfo(self):
        return {
            "id": self.get_id(),
            "well_type": self.get_well_type(),
            "n_wells": self.get_n_wells(),
            "rows": self.get_n_rows(),
            "cols": self.get_n_columns(),
            "well_distance": self.get_well_distance(),
            "well_size": self.get_well_size(),
        }


class PlateFromDatabase(WellPlate):
    """Standard well plates from the yaml database"""

    def __init__(self, plate_name: str):
        super().__init__()

        with open(PLATE_DATABASE) as file:
            plate_db = yaml.safe_load(file)

            plate = plate_db[plate_name]

            self.id = plate.get("id")
            self.circular = plate.get("circular")
            self.rows = plate.get("rows")
            self.cols = plate.get("cols")
            self.well_spacing_x = plate.get("well_spacing_x")
            self.well_spacing_y = plate.get("well_spacing_y")
            self.well_size_x = plate.get("well_size_x")
            self.well_size_y = plate.get("well_size_y")
