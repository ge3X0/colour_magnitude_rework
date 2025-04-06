from PySide6.QtWidgets import QGraphicsView
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtCore import Qt, QPoint, Signal

from star_ellipse import StarStatus, StarEllipse

from typing import Optional, Iterator


class StarGraphicsView(QGraphicsView):

    # Signal emitted when parameters of a star should be set
    star_chosen = Signal(StarEllipse)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def stars(self) -> Iterator[StarEllipse]:
        """Returns all StarEllipse instances in the currently held scene"""
        return filter(lambda x: isinstance(x, StarEllipse), self.scene().items())


    def get_star_at(self, pos: QPoint) -> Optional[StarEllipse]:
        """Returns the StarEllipse instance at position pos or None"""
        if (star := self.itemAt(pos)) and isinstance(star, StarEllipse):
            return star

        return None


    def mousePressEvent(self, event: QMouseEvent):
        # TODO: manual drag?
        match event.button():
            # Select or deselect a star to be part of the star-accumulation
            case Qt.MouseButton.LeftButton:
                self.toggle_selection(event.pos())

            # Signal MainWindow that we would like to set parameters for this particular star
            case Qt.MouseButton.RightButton:
                if star := self.get_star_at(event.pos()):
                    self.star_chosen.emit(star)

            case _:
                pass

    def wheelEvent(self, event: QWheelEvent):
        """Implement zoom functionality"""
        z = 1 + (0.2 if event.angleDelta().y() > 0 else -0.2)
        self.setTransform(self.transform().scale(z, z))


    def toggle_selection(self, pos: QPoint):
        """Toggles selection of a star. star.status is a property, handling everything concerning graphics etc."""
        if star := self.get_star_at(pos):
            star.status ^= StarStatus.Selected