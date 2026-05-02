from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QWheelEvent, QMouseEvent


class ImageViewer(QGraphicsView):
    ZOOM_STEP = 1.15

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._item = QGraphicsPixmapItem()
        self._scene.addItem(self._item)

        self._fitted = True
        self._panning = False
        self._pan_origin = None

        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(Qt.GlobalColor.darkGray)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def set_pixmap(self, pixmap: QPixmap):
        self._item.setPixmap(pixmap)
        self._scene.setSceneRect(self._item.boundingRect())
        self._fit()

    def clear(self):
        self._item.setPixmap(QPixmap())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fit(self):
        if not self._item.pixmap().isNull():
            self.fitInView(self._item, Qt.AspectRatioMode.KeepAspectRatio)
        self._fitted = True

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def wheelEvent(self, event: QWheelEvent):
        factor = self.ZOOM_STEP if event.angleDelta().y() > 0 else 1 / self.ZOOM_STEP
        self.scale(factor, factor)
        self._fitted = False

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = True
            self._pan_origin = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.RightButton:
            self._fit()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._panning and self._pan_origin is not None:
            delta = event.position().toPoint() - self._pan_origin
            self._pan_origin = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fitted:
            self._fit()
