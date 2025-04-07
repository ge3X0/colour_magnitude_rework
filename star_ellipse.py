from PySide6.QtWidgets import QGraphicsEllipseItem
from PySide6.QtGui import QPen

from enum import IntFlag


class StarStatus(IntFlag):
    Deselected = 0b00
    Selected = 0b01
    Labeled = 0b10


class Pens:
    """Used to color ellipse around stars depending on its status"""

    Deselected = QPen("red")
    Selected = QPen("green")
    DeselectedLabeled = QPen("orange")
    SelectedLabeled = QPen("blue")

    @staticmethod
    def from_status(star_status: StarStatus) -> QPen:
        return [Pens.Deselected, Pens.Selected,
                Pens.DeselectedLabeled, Pens.SelectedLabeled][star_status]


class StarEllipse(QGraphicsEllipseItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__status = StarStatus.Selected
        self.setPen(Pens.from_status(self.__status))

        self.index = 0
        self.vmag1 = 0.0
        self.vmag2 = 0.0
        self.flux1 = 0.0
        self.flux2 = 0.0

    @property
    def status(self) -> StarStatus:
        return self.__status

    @status.setter
    def status(self, value):
        """Set pen automatically according to new status"""

        self.__status = value
        self.setPen(Pens.from_status(self.__status))