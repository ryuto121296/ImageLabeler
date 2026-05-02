import os
import cv2
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QFrame, QButtonGroup, QMessageBox, QColorDialog, QComboBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QImage, QKeyEvent, QPixmap

from core.project import ClassInfo, PatchProject
from core.io import save_project, load_project, export_patch
from .patch_viewer import PatchViewer

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


class PatchWindow(QMainWindow):
    closed = Signal()

    def __init__(self, project: PatchProject, save_path: str = None):
        super().__init__()
        self._project = project
        self._save_path = save_path
        self._images: list[str] = []
        self._index = 0

        self.setWindowTitle(
            f"Patch Classification — {project.grid_rows}×{project.grid_cols} grid"
        )
        self.resize(1300, 850)

        self._scan_images()
        self._build_ui()

        if self._images:
            self._viewer.setup_grid(project.grid_rows, project.grid_cols, project.classes)
            self._show()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

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
        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(6)

        # ── top panel (fixed 200 px) ──────────────────────────────────
        top_widget = QWidget()
        top_widget.setFixedHeight(200)
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 4, 0, 4)
        top_layout.setSpacing(8)

        # Row 1: action bar
        action_bar = QHBoxLayout()
        for text, slot in [("Save", self._save), ("Load", self._load), ("Export", self._export)]:
            btn = QPushButton(text)
            btn.setFixedHeight(28)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.clicked.connect(slot)
            action_bar.addWidget(btn)
        action_bar.addSpacing(8)
        path_lbl = QLabel(self._project.dataset_path)
        path_lbl.setStyleSheet("color: #888;")
        action_bar.addWidget(path_lbl)
        action_bar.addStretch()
        self._counter_lbl = QLabel()
        self._counter_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        action_bar.addWidget(self._counter_lbl)
        top_layout.addLayout(action_bar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #444;")
        top_layout.addWidget(sep)

        # Row 2: class buttons (horizontal, each with color swatch)
        class_bar = QHBoxLayout()
        class_bar.setSpacing(4)
        self._class_group = QButtonGroup(self)
        self._class_group.setExclusive(True)
        self._color_btns: list[QPushButton] = []

        for i, cls in enumerate(self._project.classes):
            r, g, b = cls.color
            cell = QWidget()
            cell_l = QHBoxLayout(cell)
            cell_l.setContentsMargins(0, 0, 0, 0)
            cell_l.setSpacing(2)

            cls_btn = QPushButton(f"[{i + 1}]  {cls.name}")
            cls_btn.setCheckable(True)
            cls_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            cls_btn.setFixedHeight(38)
            cls_btn.setMinimumWidth(100)
            cls_btn.setStyleSheet(
                f"QPushButton {{ border-left: 5px solid rgb({r},{g},{b}); text-align: left; padding-left: 6px; }}"
                f"QPushButton:checked {{ background-color: #3d5a80; }}"
            )
            cls_btn.clicked.connect(lambda _c, idx=i: self._select_class(idx))
            self._class_group.addButton(cls_btn, i)

            color_btn = QPushButton()
            color_btn.setFixedSize(22, 38)
            color_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            color_btn.setStyleSheet(
                f"background-color: rgb({r},{g},{b}); border: 1px solid #555; border-radius: 3px;"
            )
            color_btn.clicked.connect(lambda _c, idx=i: self._edit_color(idx))
            self._color_btns.append(color_btn)

            cell_l.addWidget(cls_btn)
            cell_l.addWidget(color_btn)
            class_bar.addWidget(cell)

        if self._class_group.buttons():
            self._class_group.buttons()[0].setChecked(True)
        class_bar.addStretch()
        top_layout.addLayout(class_bar)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #444;")
        top_layout.addWidget(sep2)

        # Row 3: default class for unlabeled cells (export only)
        default_bar = QHBoxLayout()
        default_bar.addWidget(QLabel("Default for unlabeled cells (export only):"))
        self._default_class_combo = QComboBox()
        self._default_class_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._default_class_combo.addItem("— none  (keep as -1)")
        for cls in self._project.classes:
            self._default_class_combo.addItem(cls.name)
        default_bar.addWidget(self._default_class_combo)
        default_bar.addStretch()
        top_layout.addLayout(default_bar)

        top_layout.addStretch()
        vbox.addWidget(top_widget)

        # ── viewer ────────────────────────────────────────────────────
        self._viewer = PatchViewer()
        self._viewer.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._viewer.set_current_class(0)
        vbox.addWidget(self._viewer)

        # ── bottom nav ────────────────────────────────────────────────
        nav = QHBoxLayout()
        self._prev_btn = QPushButton("◀  Previous")
        self._next_btn = QPushButton("Next  ▶")
        for btn in (self._prev_btn, self._next_btn):
            btn.setFixedWidth(120)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._prev_btn.clicked.connect(self._prev)
        self._next_btn.clicked.connect(self._next)
        self._prev_btn.setEnabled(bool(self._images))
        self._next_btn.setEnabled(bool(self._images))
        nav.addStretch()
        nav.addWidget(self._prev_btn)
        nav.addWidget(self._next_btn)
        nav.addStretch()
        vbox.addLayout(nav)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _prev(self):
        if self._images:
            self._save_grid()
            self._index = (self._index - 1) % len(self._images)
            self._show()

    def _next(self):
        if self._images:
            self._save_grid()
            self._index = (self._index + 1) % len(self._images)
            self._show()

    def _save_grid(self):
        if self._images:
            filename = os.path.basename(self._images[self._index])
            self._project.labels[filename] = self._viewer.get_grid_data()

    # ------------------------------------------------------------------
    # Class selection & color
    # ------------------------------------------------------------------

    def _select_class(self, idx: int):
        btn = self._class_group.button(idx)
        if btn:
            btn.setChecked(True)
        self._viewer.set_current_class(idx)

    def _edit_color(self, idx: int):
        cls = self._project.classes[idx]
        r, g, b = cls.color
        color = QColorDialog.getColor(QColor(r, g, b), self, f"Color for {cls.name}")
        if not color.isValid():
            return
        new_color = (color.red(), color.green(), color.blue())
        self._project.classes[idx].color = new_color
        self._viewer.update_class_color(idx, new_color)

        r, g, b = new_color
        self._color_btns[idx].setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border: 1px solid #555; border-radius: 3px;"
        )
        cls_btn = self._class_group.button(idx)
        if cls_btn:
            cls_btn.setStyleSheet(
                f"QPushButton {{ border-left: 5px solid rgb({r},{g},{b}); text-align: left; padding-left: 6px; }}"
                f"QPushButton:checked {{ background-color: #3d5a80; }}"
            )

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def _show(self):
        if not self._images:
            return
        path = self._images[self._index]
        img = cv2.imread(path)
        if img is None:
            self.statusBar().showMessage(f"Cannot read: {os.path.basename(path)}", 3000)
            return

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        qimg = QImage(img_rgb.data, w, h, w * ch, QImage.Format.Format_RGB888).copy()
        self._viewer.set_pixmap(QPixmap.fromImage(qimg))

        filename = os.path.basename(path)
        if filename in self._project.labels:
            self._viewer.load_grid_data(self._project.labels[filename])

        self._update_counter()
        self.setWindowTitle(f"Patch Classification — {filename}")

    def _update_counter(self):
        if not self._images:
            return
        filename = os.path.basename(self._images[self._index])
        labeled = len(self._project.labels)
        total = len(self._images)
        mark = "✓" if filename in self._project.labels else "○"
        self._counter_lbl.setText(f"{mark} {self._index + 1}/{total}  |  {labeled} labeled")

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _save(self):
        self._save_grid()
        if not self._save_path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Project", "", "Image Labeler Project (*.ilproj)"
            )
            if not path:
                return
            self._save_path = path
        save_project(self._project, self._save_path)
        self.statusBar().showMessage("Saved successfully.", 3000)

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
        if not isinstance(proj, PatchProject):
            QMessageBox.critical(self, "Wrong type", "This file is not a Patch Classification project.")
            return
        self._project = proj
        self._save_path = path
        self._scan_images()
        self._index = 0
        if self._images:
            self._viewer.setup_grid(proj.grid_rows, proj.grid_cols, proj.classes)
            self._show()
        self.statusBar().showMessage("Loaded successfully.", 3000)

    def _export(self):
        self._save_grid()
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not folder:
            return
        # combo index 0 = no default (-1), index 1 = class 0, index 2 = class 1, …
        default_class = self._default_class_combo.currentIndex() - 1
        try:
            export_patch(self._project, folder, default_class=default_class)
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))
            return
        self.statusBar().showMessage(f"Exported to: {folder}", 5000)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if Qt.Key.Key_1 <= key <= Qt.Key.Key_9:
            idx = key - Qt.Key.Key_1
            if idx < len(self._project.classes):
                self._select_class(idx)
        elif key == Qt.Key.Key_Left:
            self._prev()
        elif key == Qt.Key.Key_Right:
            self._next()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self._save_grid()
        self.closed.emit()
        super().closeEvent(event)
