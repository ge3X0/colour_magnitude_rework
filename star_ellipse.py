from PySide6.QtWidgets import QGraphicsEllipseItem
from PySide6.QtGui import QPen

from enum import IntFlag


class StarStatus(IntFlag):
    Deselected = 0b00
    Selected = 0b01
    Labeled = 0b10


class Pens:
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

    @property
    def status(self) -> StarStatus:
        return self.__status

    @status.setter
    def status(self, value):
        self.__status = value
        self.setPen(Pens.from_status(self.__status))