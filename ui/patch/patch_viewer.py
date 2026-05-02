from PySide6.QtWidgets import QGraphicsRectItem
from PySide6.QtGui import QColor, QPen, QPixmap
from PySide6.QtCore import Qt

from ui.image_viewer import ImageViewer
from core.project import ClassInfo

_UNLABELED_ALPHA = 0
_LABELED_ALPHA = 110
_GRID_PEN_COLOR = QColor(220, 220, 220, 90)


class PatchViewer(ImageViewer):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = 0
        self._cols = 0
        self._classes: list[ClassInfo] = []
        self._current_class = 0
        self._grid_items: list[list[QGraphicsRectItem]] = []
        self._grid_data: list[list[int]] = []
        self._painting = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def setup_grid(self, rows: int, cols: int, classes: list[ClassInfo]) -> None:
        self._rows = rows
        self._cols = cols
        self._classes = classes
        if not self._item.pixmap().isNull():
            self._rebuild_grid()

    def set_current_class(self, idx: int) -> None:
        self._current_class = idx

    def update_class_color(self, class_idx: int, color: tuple[int, int, int]) -> None:
        if 0 <= class_idx < len(self._classes):
            self._classes[class_idx].color = color
        r, g, b = color
        for ri, row in enumerate(self._grid_data):
            for ci, ci_val in enumerate(row):
                if ci_val == class_idx:
                    self._grid_items[ri][ci].setBrush(QColor(r, g, b, _LABELED_ALPHA))

    def load_grid_data(self, data: list[list[int]]) -> None:
        for ri in range(min(len(data), self._rows)):
            for ci in range(min(len(data[ri]), self._cols)):
                self._grid_data[ri][ci] = data[ri][ci]
                self._refresh_cell(ri, ci)

    def get_grid_data(self) -> list[list[int]]:
        return [row[:] for row in self._grid_data]

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    def set_pixmap(self, pixmap: QPixmap) -> None:
        super().set_pixmap(pixmap)
        if self._rows > 0:
            self._rebuild_grid()

    # ------------------------------------------------------------------
    # Grid internals
    # ------------------------------------------------------------------

    def _rebuild_grid(self) -> None:
        for row in self._grid_items:
            for item in row:
                self._scene.removeItem(item)
        self._grid_items = []
        self._grid_data = []

        if self._item.pixmap().isNull() or self._rows == 0:
            return

        iw = self._item.pixmap().width()
        ih = self._item.pixmap().height()
        cw = iw / self._cols
        ch = ih / self._rows

        pen = QPen(_GRID_PEN_COLOR)
        pen.setCosmetic(True)
        pen.setWidthF(0.8)

        for r in range(self._rows):
            row_items = []
            row_data = []
            for c in range(self._cols):
                item = QGraphicsRectItem(c * cw, r * ch, cw, ch)
                item.setPen(pen)
                item.setBrush(QColor(0, 0, 0, _UNLABELED_ALPHA))
                self._scene.addItem(item)
                row_items.append(item)
                row_data.append(-1)
            self._grid_items.append(row_items)
            self._grid_data.append(row_data)

    def _refresh_cell(self, r: int, c: int) -> None:
        ci = self._grid_data[r][c]
        if ci < 0 or ci >= len(self._classes):
            self._grid_items[r][c].setBrush(QColor(0, 0, 0, _UNLABELED_ALPHA))
        else:
            rr, g, b = self._classes[ci].color
            self._grid_items[r][c].setBrush(QColor(rr, g, b, _LABELED_ALPHA))

    def _cell_at(self, view_pos) -> tuple[int, int] | None:
        if not self._grid_items:
            return None
        px = self._item.pixmap()
        if px.isNull():
            return None
        sp = self.mapToScene(view_pos)
        x, y = sp.x(), sp.y()
        if x < 0 or y < 0 or x >= px.width() or y >= px.height():
            return None
        c = min(int(x / px.width() * self._cols), self._cols - 1)
        r = min(int(y / px.height() * self._rows), self._rows - 1)
        return r, c

    def _paint_at(self, view_pos) -> None:
        cell = self._cell_at(view_pos)
        if cell:
            r, c = cell
            self._grid_data[r][c] = self._current_class
            self._refresh_cell(r, c)

    # ------------------------------------------------------------------
    # Mouse events (override base class)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._painting = True
            self._paint_at(event.position().toPoint())
        elif event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_origin = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.RightButton:
            self._fit()

    def mouseMoveEvent(self, event):
        if self._painting:
            self._paint_at(event.position().toPoint())
        elif self._panning and self._pan_origin is not None:
            delta = event.position().toPoint() - self._pan_origin
            self._pan_origin = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._painting = False
        elif event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
