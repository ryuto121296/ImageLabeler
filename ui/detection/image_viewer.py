import math
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsRectItem, QGraphicsPolygonItem,
)
from PySide6.QtCore import Qt, Signal, QPointF, QRectF, QPoint
from PySide6.QtGui import QPixmap, QPen, QColor, QPolygonF, QBrush


_HANDLE_HIT_PX = 10   # viewport-pixel radius for corner click detection


class BoundingBox:
    def __init__(self, x, y, width, height, angle=0.0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.angle = angle


class ImageViewer(QGraphicsView):
    closed = Signal()
    boxAdded = Signal()
    boxSelected = Signal(int)   # -1 = deselected

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._item = QGraphicsPixmapItem()
        self._scene.addItem(self._item)

        # (BoundingBox, QGraphicsPolygonItem, class_idx, color)
        self._boxes: list[tuple[BoundingBox, QGraphicsPolygonItem, int, tuple]] = []

        self._active_class_idx = 0
        self._active_color: tuple[int, int, int] = (220, 50, 50)

        # Interaction state
        self._drawing = False
        self._dragging_box = False
        self._resizing = False
        self._resize_corner: int = -1          # 0=TL 1=TR 2=BR 3=BL
        self._drag_start: QPointF | None = None
        self._drag_box_origin: tuple = (0.0, 0.0, 0.0, 0.0)   # x, y, w, h
        self._temp_rect: QGraphicsRectItem | None = None

        # Selection
        self._selected_idx: int = -1

        # 4 corner handle squares (always in scene, shown/hidden)
        self._handles: list[QGraphicsRectItem] = []
        for _ in range(4):
            h = QGraphicsRectItem()
            h.setBrush(QBrush(QColor(255, 255, 255)))
            h.setPen(QPen(QColor(50, 50, 50), 1))
            h.setZValue(10)
            h.setVisible(False)
            self._scene.addItem(h)
            self._handles.append(h)

        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(Qt.GlobalColor.darkGray)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)

    # ── Public API ───────────────────────────────────────────────────────

    def set_active_class(self, class_idx: int, color: tuple[int, int, int]):
        self._active_class_idx = class_idx
        self._active_color = color

    @property
    def selected_box_idx(self) -> int:
        return self._selected_idx

    def set_selected(self, idx: int):
        self._apply_selection(idx)

    def set_pixmap(self, pixmap: QPixmap):
        self._item.setPixmap(pixmap)
        self._scene.setSceneRect(self._item.boundingRect())
        self.fitInView(self._item, Qt.AspectRatioMode.KeepAspectRatio)

    def clear(self):
        for _, item, _, _ in self._boxes:
            self._scene.removeItem(item)
        self._boxes = []
        self._selected_idx = -1
        self._dragging_box = False
        self._resizing = False
        self._drawing = False
        self._drag_start = None
        self._hide_handles()
        if self._temp_rect is not None:
            self._scene.removeItem(self._temp_rect)
            self._temp_rect = None

    def setup_detection(self, classes):
        self.clear()

    def draw_box(self, x, y, w, h, angle, class_idx: int, color: tuple[int, int, int]) -> int:
        bbox = BoundingBox(x, y, w, h, angle)
        poly_item = self._draw_box_polygon(bbox, color)
        self._scene.addItem(poly_item)
        self._boxes.append((bbox, poly_item, class_idx, color))
        return len(self._boxes) - 1

    def delete_box(self, idx: int):
        if 0 <= idx < len(self._boxes):
            _, item, _, _ = self._boxes[idx]
            self._scene.removeItem(item)
            del self._boxes[idx]
            if self._selected_idx == idx:
                self._selected_idx = -1
                self._hide_handles()
            elif self._selected_idx > idx:
                self._selected_idx -= 1

    def update_class_color(self, class_idx: int, new_color: tuple[int, int, int]):
        for i, (box, item, cidx, _) in enumerate(self._boxes):
            if cidx == class_idx:
                self._boxes[i] = (box, item, cidx, new_color)
                if i != self._selected_idx:
                    item.setPen(self._make_pen(new_color))

    def get_boxes_for_save(self) -> list[dict]:
        return [
            {
                "x": int(box.x),
                "y": int(box.y),
                "width": int(box.width),
                "height": int(box.height),
                "angle": round(box.angle, 1),
                "class_idx": class_idx,
            }
            for box, _, class_idx, _ in self._boxes
        ]

    # ── Geometry helpers ─────────────────────────────────────────────────

    def _get_corners(self, box: BoundingBox) -> list[tuple[float, float]]:
        """Return scene-space corners TL, TR, BR, BL."""
        if box.angle == 0.0:
            return [
                (box.x,              box.y),
                (box.x + box.width,  box.y),
                (box.x + box.width,  box.y + box.height),
                (box.x,              box.y + box.height),
            ]
        cx = box.x + box.width / 2
        cy = box.y + box.height / 2
        hw, hh = box.width / 2, box.height / 2
        rad = -math.radians(box.angle)
        ca, sa = math.cos(rad), math.sin(rad)
        local = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        return [(ca * p[0] - sa * p[1] + cx, sa * p[0] + ca * p[1] + cy) for p in local]

    def _get_polygon_from_rect(self, rect: QRectF, angle: float) -> QPolygonF:
        if angle == 0.0:
            return QPolygonF([rect.topLeft(), rect.topRight(),
                               rect.bottomRight(), rect.bottomLeft()])
        cx, cy = rect.center().x(), rect.center().y()
        hw, hh = rect.width() / 2, rect.height() / 2
        rad = -math.radians(angle)
        ca, sa = math.cos(rad), math.sin(rad)
        local = [QPointF(-hw, -hh), QPointF(hw, -hh), QPointF(hw, hh), QPointF(-hw, hh)]
        return QPolygonF([QPointF(ca * p.x() - sa * p.y() + cx,
                                  sa * p.x() + ca * p.y() + cy) for p in local])

    def _make_pen(self, color: tuple[int, int, int], width: int = 2) -> QPen:
        r, g, b = color
        pen = QPen(QColor(r, g, b))
        pen.setWidth(width)
        return pen

    def _draw_box_polygon(self, box: BoundingBox, color: tuple[int, int, int]) -> QGraphicsPolygonItem:
        rect = QRectF(box.x, box.y, box.width, box.height)
        item = QGraphicsPolygonItem(self._get_polygon_from_rect(rect, box.angle))
        item.setPen(self._make_pen(color))
        return item

    # ── Handle helpers ───────────────────────────────────────────────────

    def _handle_scene_size(self) -> float:
        p1 = self.mapToScene(QPoint(0, 0))
        p2 = self.mapToScene(QPoint(8, 0))
        return max(abs(p2.x() - p1.x()), 1.0)

    def _update_handles(self):
        if not (0 <= self._selected_idx < len(self._boxes)):
            self._hide_handles()
            return
        box = self._boxes[self._selected_idx][0]
        corners = self._get_corners(box)
        hs = self._handle_scene_size()
        for i, (cx, cy) in enumerate(corners):
            self._handles[i].setRect(QRectF(cx - hs / 2, cy - hs / 2, hs, hs))
            self._handles[i].setVisible(True)

    def _hide_handles(self):
        for h in self._handles:
            h.setVisible(False)

    def _corner_at(self, viewport_pos) -> int:
        """Return index of corner handle under viewport_pos, or -1."""
        if not (0 <= self._selected_idx < len(self._boxes)):
            return -1
        box = self._boxes[self._selected_idx][0]
        corners = self._get_corners(box)
        vp = QPointF(viewport_pos)
        r2 = _HANDLE_HIT_PX * _HANDLE_HIT_PX
        for i, (cx, cy) in enumerate(corners):
            vp_pt = QPointF(self.mapFromScene(QPointF(cx, cy)))
            dx = vp_pt.x() - vp.x()
            dy = vp_pt.y() - vp.y()
            if dx * dx + dy * dy <= r2:
                return i
        return -1

    def _box_at(self, viewport_pos) -> int:
        for item in self.items(viewport_pos):
            if isinstance(item, QGraphicsPolygonItem):
                for i, (_, poly, _, _) in enumerate(self._boxes):
                    if poly is item:
                        return i
        return -1

    # ── Selection ────────────────────────────────────────────────────────

    def _apply_selection(self, idx: int):
        # Restore previous
        if 0 <= self._selected_idx < len(self._boxes):
            _, item, _, color = self._boxes[self._selected_idx]
            item.setPen(self._make_pen(color))
        self._selected_idx = idx
        # Highlight new
        if 0 <= idx < len(self._boxes):
            _, item, _, _ = self._boxes[idx]
            pen = QPen(QColor(255, 220, 0))
            pen.setWidth(3)
            item.setPen(pen)
            self._update_handles()
        else:
            self._hide_handles()

    # ── Resize logic ─────────────────────────────────────────────────────

    def _apply_resize(self, scene_pos: QPointF):
        if not (0 <= self._selected_idx < len(self._boxes)):
            return
        box = self._boxes[self._selected_idx][0]
        ox, oy, ow, oh = self._drag_box_origin
        px, py = scene_pos.x(), scene_pos.y()

        c = self._resize_corner
        if c == 0:          # TL — opposite BR fixed
            br_x, br_y = ox + ow, oy + oh
            new_x = min(px, br_x - 1)
            new_y = min(py, br_y - 1)
            box.x, box.y = new_x, new_y
            box.width  = br_x - new_x
            box.height = br_y - new_y
        elif c == 1:        # TR — opposite BL fixed
            bl_x, bl_y = ox, oy + oh
            new_y = min(py, bl_y - 1)
            box.y      = new_y
            box.width  = max(px - bl_x, 1)
            box.height = bl_y - new_y
        elif c == 2:        # BR — opposite TL fixed
            box.width  = max(px - ox, 1)
            box.height = max(py - oy, 1)
        elif c == 3:        # BL — opposite TR fixed
            tr_x, tr_y = ox + ow, oy
            new_x = min(px, tr_x - 1)
            box.x      = new_x
            box.width  = tr_x - new_x
            box.height = max(py - tr_y, 1)

        _, item, _, _ = self._boxes[self._selected_idx]
        item.setPolygon(self._get_polygon_from_rect(
            QRectF(box.x, box.y, box.width, box.height), box.angle
        ))
        self._update_handles()

    # ── Mouse events ─────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            corner = self._corner_at(event.pos())
            if corner >= 0:
                # Resize mode
                self._resizing = True
                self._resize_corner = corner
                self._drag_start = self.mapToScene(event.pos())
                box = self._boxes[self._selected_idx][0]
                self._drag_box_origin = (box.x, box.y, box.width, box.height)
            else:
                hit = self._box_at(event.pos())
                if hit >= 0:
                    # Move mode
                    self._apply_selection(hit)
                    self.boxSelected.emit(hit)
                    self._dragging_box = True
                    self._drag_start = self.mapToScene(event.pos())
                    box = self._boxes[hit][0]
                    self._drag_box_origin = (box.x, box.y, box.width, box.height)
                else:
                    # Draw mode
                    self._apply_selection(-1)
                    self.boxSelected.emit(-1)
                    pos = self.mapToScene(event.pos())
                    self._drag_start = pos
                    self._drawing = True
                    self._temp_rect = QGraphicsRectItem(QRectF(pos, pos))
                    self._temp_rect.setPen(self._make_pen(self._active_color))
                    self._scene.addItem(self._temp_rect)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            self._apply_resize(self.mapToScene(event.pos()))
        elif self._dragging_box and self._selected_idx >= 0:
            pos = self.mapToScene(event.pos())
            delta = pos - self._drag_start
            box, item, _, _ = self._boxes[self._selected_idx]
            box.x = self._drag_box_origin[0] + delta.x()
            box.y = self._drag_box_origin[1] + delta.y()
            item.setPolygon(self._get_polygon_from_rect(
                QRectF(box.x, box.y, box.width, box.height), box.angle
            ))
            self._update_handles()
        elif self._drawing and self._drag_start is not None and self._temp_rect is not None:
            pos = self.mapToScene(event.pos())
            self._temp_rect.setRect(QRectF(self._drag_start, pos).normalized())
        else:
            # Cursor hint
            corner = self._corner_at(event.pos())
            if corner >= 0:
                self.setCursor([
                    Qt.CursorShape.SizeFDiagCursor, Qt.CursorShape.SizeBDiagCursor,
                    Qt.CursorShape.SizeFDiagCursor, Qt.CursorShape.SizeBDiagCursor,
                ][corner])
            elif self._box_at(event.pos()) >= 0:
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._resizing:
                self._resizing = False
                self._resize_corner = -1
                self._drag_start = None
                self.boxAdded.emit()
            elif self._dragging_box:
                self._dragging_box = False
                self._drag_start = None
                self.boxAdded.emit()
            elif self._drawing:
                pos = self.mapToScene(event.pos())
                rect = QRectF(self._drag_start, pos).normalized()
                if self._temp_rect is not None:
                    self._scene.removeItem(self._temp_rect)
                    self._temp_rect = None
                if rect.width() > 4 and rect.height() > 4:
                    idx = self.draw_box(
                        rect.x(), rect.y(), rect.width(), rect.height(),
                        0.0, self._active_class_idx, self._active_color,
                    )
                    self._apply_selection(idx)
                    self.boxSelected.emit(idx)
                    self.boxAdded.emit()
                self._drawing = False
                self._drag_start = None
        else:
            super().mouseReleaseEvent(event)
