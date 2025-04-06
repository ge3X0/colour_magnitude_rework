from PySide6.QtWidgets import QGraphicsView
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtCore import Qt, QPoint, Signal

from star_ellipse import StarStatus, StarEllipse

from typing import Optional


class StarGraphicsView(QGraphicsView):
    star_chosen = Signal(StarEllipse)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # canvas.bind("<Button-3>", lambda e: info_star(e, canvas, deselected, stars_mag_list, short_wave_colour,
    #                                               long_wave_colour))  # right click to type in magnitudes
    # canvas.bind("<Button-2>", lambda e: tag_info(e, canvas, deselected,
    #                                              stars_mag_list))  # middle mouse, just to see the tags of the selected star

    def get_star_at(self, pos: QPoint) -> Optional[StarEllipse]:
        if (star := self.itemAt(pos)) and isinstance(star, StarEllipse):
            return star
        return None

    def mousePressEvent(self, event: QMouseEvent):
        match event.button():
            case Qt.MouseButton.LeftButton:
                self.deselect_star(event.pos())

            case Qt.MouseButton.MiddleButton:
                pass

            case Qt.MouseButton.RightButton:
                if star := self.get_star_at(event.pos()):
                    self.star_chosen.emit(star)

            case _:
                pass

    def wheelEvent(self, event: QWheelEvent):
        z = 1 + (0.2 if event.angleDelta().y() > 0 else -0.2)
        self.setTransform(self.transform().scale(z, z))

    def deselect_star(self, pos: QPoint):
        if star := self.get_star_at(pos):
            star.status ^= StarStatus.Selected