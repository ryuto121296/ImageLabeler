import json
import os
import shutil
import cv2
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox,
    QListWidget, QSplitter, QTextEdit, QGroupBox, QScrollArea, QFileDialog, QColorDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPixmap

from core.project import Box, DetectionBox, ClassInfo, ObjectDetectionProject
from core.io import save_project, load_project
from ui.detection.image_viewer import ImageViewer


SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


class DetectionWindow(QMainWindow):
    closed = Signal()

    def __init__(self, project: ObjectDetectionProject, save_path: str = None):
        super().__init__()
        self._project = project
        self._save_path = save_path
        self._images: list[str] = []
        self._index = 0
        # flat dict format: {"x", "y", "width", "height", "angle", "class_idx"}
        self._box_data: dict[str, list[dict]] = self._labels_to_box_data(project.labels)

        self.setWindowTitle("Object Detection — Labeling")
        self.resize(1450, 900)

        self._scan_images()
        self._build_ui()

        if self._project.classes:
            self._select_class(0)

        if self._images:
            self._show()

        self.setFocus()

    def _scan_images(self):
        folder = self._project.dataset_path
        if not os.path.isdir(folder):
            return
        self._images = sorted(
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXT
        )

    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        top_panel = self._build_top_panel()
        main_layout.addWidget(top_panel, alignment=Qt.AlignmentFlag.AlignTop)

        self._viewer = ImageViewer()
        self._viewer.boxAdded.connect(self._on_box_added)
        self._viewer.boxSelected.connect(self._on_viewer_box_selected)
        main_layout.addWidget(self._viewer)

        splitter.addWidget(main_widget)

        sidebar_widget = self._build_sidebar_panel()
        splitter.addWidget(sidebar_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1120, 260])

        self.setCentralWidget(splitter)

    def _build_top_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 8, 6, 4)
        layout.setSpacing(6)

        action_row = QHBoxLayout()
        for text in ["Save", "Load", "Export"]:
            btn = QPushButton(text)
            btn.setFixedHeight(28)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            if text == "Save":
                btn.clicked.connect(self._save)
            elif text == "Load":
                btn.clicked.connect(self._load)
            elif text == "Export":
                btn.clicked.connect(self._export)
            action_row.addWidget(btn)

        path_lbl = QLabel(self._project.dataset_path)
        path_lbl.setStyleSheet("color: #888;")
        action_row.addWidget(path_lbl)
        action_row.addStretch()

        self._counter_lbl = QLabel()
        self._counter_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        action_row.addWidget(self._counter_lbl)

        layout.addLayout(action_row)

        class_row = QHBoxLayout()
        class_row.setSpacing(4)

        self._class_btns: list[QPushButton] = []
        self._class_color_btns: list[QPushButton] = []
        for i, cls in enumerate(self._project.classes):
            r, g, b = cls.color

            # Small colored square — click to change color
            color_btn = QPushButton()
            color_btn.setFixedSize(14, 14)
            color_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            color_btn.setToolTip(f"Change color for '{cls.name}'")
            color_btn.setStyleSheet(
                f"background-color: rgb({r},{g},{b}); border: 1px solid #888; border-radius: 2px;"
            )
            color_btn.clicked.connect(lambda checked, idx=i: self._pick_class_color(idx))
            self._class_color_btns.append(color_btn)

            # Class selection button
            btn = QPushButton(cls.name)
            btn.setCheckable(True)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setMinimumWidth(80)
            btn.setStyleSheet(
                f"QPushButton {{ border-left: 5px solid rgb({r},{g},{b}); background-color: #fafafa; padding: 4px 8px; font-size: 12px; }}"
                f"QPushButton:checked {{ background-color: #3d5a80; color: white; }}"
            )
            btn.clicked.connect(lambda checked, idx=i: self._select_class(idx))
            self._class_btns.append(btn)

            # Stack swatch + label button in a small column
            col = QVBoxLayout()
            col.setSpacing(2)
            col.setContentsMargins(0, 0, 0, 0)
            top_row = QHBoxLayout()
            top_row.setSpacing(3)
            top_row.setContentsMargins(0, 0, 0, 0)
            top_row.addWidget(color_btn)
            top_row.addWidget(btn)
            col.addLayout(top_row)
            class_row.addLayout(col)

        class_row.addStretch()
        layout.addLayout(class_row)

        tips = QTextEdit()
        tips.setPlainText(
            "Controls:\n"
            "• Left-drag: draw box\n"
            "• DEL key: delete selected box\n"
            "• 1-9 keys: quick class select\n"
            "• ← → : navigate images\n"
        )
        tips.setReadOnly(True)
        tips.setFixedHeight(80)
        tips.setStyleSheet(
            "font-size: 10px; color: #555; background-color: #f8f8f8; padding: 4px; "
            "border: 1px solid #ddd; border-radius: 3px;"
        )
        layout.addWidget(tips)

        return widget

    def _build_sidebar_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 10, 6, 6)
        layout.setSpacing(8)

        header = QLabel("Detected Boxes")
        header.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #333; padding-bottom: 4px; "
            "border-bottom: 2px solid #ddd;"
        )
        layout.addWidget(header)

        boxes_group = QGroupBox("Boxes")
        boxes_layout = QVBoxLayout(boxes_group)
        boxes_layout.setContentsMargins(6, 8, 6, 4)
        boxes_layout.setSpacing(3)

        class_swatches_row = QHBoxLayout()
        font = QFont("Arial", 10)
        for cls in self._project.classes:
            r, g, b = cls.color
            swatch = QLabel(cls.name)
            swatch.setStyleSheet(
                f"background-color: rgb({r},{g},{b}); border: 1px solid #999; "
                f"color: white; padding: 4px 6px; font-size: 10px;"
            )
            class_swatches_row.addWidget(swatch)
        class_swatches_row.addStretch()
        boxes_layout.addLayout(class_swatches_row)

        self._box_list = QListWidget()
        self._box_list.setFont(font)
        self._box_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._box_list.currentRowChanged.connect(self._on_box_selected)
        boxes_layout.addWidget(self._box_list, stretch=1)

        del_btn = QPushButton("Delete Selected")
        del_btn.setFixedHeight(26)
        del_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        del_btn.clicked.connect(self._delete_selected_box)
        boxes_layout.addWidget(del_btn)

        footer = QLabel("Or select a box and press DEL.")
        footer.setStyleSheet("font-size: 10px; color: #888; padding: 4px;")
        boxes_layout.addWidget(footer)

        layout.addWidget(boxes_group, stretch=1)
        return widget

    def _show(self):
        if not self._images:
            return
        path = self._images[self._index]
        img = cv2.imread(path)
        if img is None:
            self.statusBar().showMessage(f"Cannot read: {os.path.basename(path)}", 3000)
            return

        h, w = img.shape[:2]
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        qimage = QImage(img_rgb.data, w, h, w * 3, QImage.Format.Format_RGB888).copy()
        self._viewer.set_pixmap(QPixmap.fromImage(qimage))

        self._viewer.clear()
        filename = os.path.basename(path)
        for box in self._box_data.get(filename, []):
            class_idx = box["class_idx"]
            color = tuple(self._project.classes[class_idx].color)
            self._viewer.draw_box(box["x"], box["y"], box["width"], box["height"],
                                  box["angle"], class_idx, color)

        self._update_box_list()
        self._update_counter()
        self.setWindowTitle(f"Object Detection — {filename}")

    def _update_counter(self):
        if not self._images:
            return
        filename = os.path.basename(self._images[self._index])
        total = len(self._images)
        box_count = sum(len(b) for b in self._box_data.values())
        marked = "✓" if filename in self._box_data else "○"
        text = f"{marked} {self._index + 1}/{total}  |  {len(self._box_data)} labeled"
        if box_count:
            text += f"  ({box_count} boxes)"
        self._counter_lbl.setText(text)

    def _update_box_list(self):
        self._box_list.clear()
        if not self._images:
            return
        filename = os.path.basename(self._images[self._index])
        for i, b in enumerate(self._box_data.get(filename, [])):
            class_idx = b["class_idx"]
            name = self._project.classes[class_idx].name if class_idx < len(self._project.classes) else "?"
            self._box_list.addItem(f"[{i + 1}] {name}  {b['width']}×{b['height']}")

    def _select_class(self, idx: int):
        for i, btn in enumerate(self._class_btns):
            btn.setChecked(i == idx)
        cls = self._project.classes[idx]
        self._viewer.set_active_class(idx, tuple(cls.color))

    def _pick_class_color(self, idx: int):
        cls = self._project.classes[idx]
        r, g, b = cls.color
        color = QColorDialog.getColor(QColor(r, g, b), self, f"Color for '{cls.name}'")
        if not color.isValid():
            return
        new_color = (color.red(), color.green(), color.blue())
        r, g, b = new_color
        cls.color = new_color
        # Update class button border color
        self._class_btns[idx].setStyleSheet(
            f"QPushButton {{ border-left: 5px solid rgb({r},{g},{b}); background-color: #fafafa; padding: 4px 8px; font-size: 12px; }}"
            f"QPushButton:checked {{ background-color: #3d5a80; color: white; }}"
        )
        # Update swatch
        self._class_color_btns[idx].setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border: 1px solid #888; border-radius: 2px;"
        )
        # Repaint existing boxes of this class in the viewer
        self._viewer.update_class_color(idx, new_color)
        # Update active color if this class is currently selected
        if self._class_btns[idx].isChecked():
            self._viewer.set_active_class(idx, new_color)

    def _on_box_added(self):
        self._sync_viewer_to_box_data()
        self._update_box_list()
        self._update_counter()

    def _sync_viewer_to_box_data(self):
        if not self._images:
            return
        filename = os.path.basename(self._images[self._index])
        boxes = self._viewer.get_boxes_for_save()
        if boxes:
            self._box_data[filename] = boxes
        else:
            self._box_data.pop(filename, None)

    def _on_box_selected(self, row: int):
        """Sidebar list selection → sync viewer highlight."""
        if row >= 0:
            self._viewer.set_selected(row)

    def _on_viewer_box_selected(self, idx: int):
        """Viewer click → sync sidebar list selection."""
        self._box_list.blockSignals(True)
        self._box_list.setCurrentRow(idx)
        self._box_list.blockSignals(False)

    def _delete_selected_box(self):
        # Prefer sidebar selection; fall back to viewer selection
        idx = self._box_list.currentRow()
        if idx < 0:
            idx = self._viewer.selected_box_idx
        if idx < 0 or not self._images:
            return
        self._viewer.delete_box(idx)
        self._sync_viewer_to_box_data()
        self._update_box_list()
        self._update_counter()

    def _clear_boxes(self):
        if not self._images:
            return
        filename = os.path.basename(self._images[self._index])
        self._box_data.pop(filename, None)
        self._viewer.clear()
        self._update_box_list()
        self._update_counter()

    def _get_box_count_for_class(self, class_idx: int) -> int:
        return sum(
            1 for boxes in self._box_data.values()
            for b in boxes if b["class_idx"] == class_idx
        )

    # ── Navigation ───────────────────────────────────────────────────────

    def _prev(self):
        if self._images:
            self._sync_viewer_to_box_data()
            self._index = (self._index - 1) % len(self._images)
            self._show()

    def _next(self):
        if self._images:
            self._sync_viewer_to_box_data()
            self._index = (self._index + 1) % len(self._images)
            self._show()

    def keyPressEvent(self, event):
        key = event.key()
        if Qt.Key.Key_1 <= key <= Qt.Key.Key_9:
            idx = key - Qt.Key.Key_1
            if idx < len(self._project.classes):
                self._select_class(idx)
        elif key == Qt.Key.Key_Left:
            self._prev()
        elif key == Qt.Key.Key_Right:
            self._next()
        elif key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self._delete_selected_box()

    # ── File operations ──────────────────────────────────────────────────

    @staticmethod
    def _labels_to_box_data(labels: dict) -> dict:
        box_data = {}
        for filename, det_boxes in labels.items():
            box_data[filename] = [
                {
                    "x": det.box.x, "y": det.box.y,
                    "width": det.box.width, "height": det.box.height,
                    "angle": det.box.angle, "class_idx": det.class_idx,
                }
                for det in det_boxes
            ]
        return box_data

    def _box_data_to_project_labels(self) -> dict:
        labels = {}
        for filename, boxes in self._box_data.items():
            det_list = []
            for b in boxes:
                class_idx = b["class_idx"]
                color = list(self._project.classes[class_idx].color) if class_idx < len(self._project.classes) else [255, 0, 0]
                box_obj = Box(b["x"], b["y"], b["width"], b["height"], b["angle"])
                det_list.append(DetectionBox(class_idx, color, box_obj))
            labels[filename] = det_list
        return labels

    def _save(self):
        self._sync_viewer_to_box_data()
        self._project.labels = self._box_data_to_project_labels()
        if not self._save_path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Project", "", "Image Labeler Project (*.ilproj)"
            )
            if not path:
                return
            self._save_path = path
        try:
            save_project(self._project, self._save_path)
            self.statusBar().showMessage("Saved successfully.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save:\n{e}")

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Project", "", "Image Labeler Project (*.ilproj)"
        )
        if not path:
            return
        try:
            proj = load_project(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load:\n{e}")
            return
        if not isinstance(proj, ObjectDetectionProject):
            QMessageBox.critical(self, "Wrong type", "This file is not an Object Detection project.")
            return
        self._project = proj
        self._save_path = path
        self._box_data = self._labels_to_box_data(proj.labels)
        self._scan_images()
        self._index = 0
        if self._project.classes:
            self._select_class(0)
        if self._images:
            self._show()
        self.statusBar().showMessage("Loaded successfully.", 3000)

    def _export(self):
        self._sync_viewer_to_box_data()
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not folder:
            return

        img_dir = os.path.join(folder, "img")
        os.makedirs(img_dir, exist_ok=True)

        image_list = []
        for filename, boxes in self._box_data.items():
            src = os.path.join(self._project.dataset_path, filename)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(img_dir, filename))
                detected = []
                for b in boxes:
                    class_name = self._project.classes[b["class_idx"]].name
                    detected.append({
                        "label": class_name,
                        "bbox": {
                            "xmin": b["x"], "ymin": b["y"],
                            "xmax": b["x"] + b["width"], "ymax": b["y"] + b["height"],
                            "angle": round(b["angle"], 1),
                        },
                    })
                image_list.append({"filename": f"img/{filename}", "detected_classes": detected})

        payload = {
            "model_type": "object_detection",
            "classes": [{"name": c.name} for c in self._project.classes],
            "images": image_list,
        }
        export_path = os.path.join(folder, "labels.json")
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        self.statusBar().showMessage(f"Exported to: {folder}", 5000)

    def closeEvent(self, event):
        self._sync_viewer_to_box_data()
        self.closed.emit()
        super().closeEvent(event)
