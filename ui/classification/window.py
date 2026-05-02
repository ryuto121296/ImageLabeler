import os
import cv2
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QSplitter, QButtonGroup, QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QKeyEvent, QPixmap

from core.project import ClassificationProject
from core.io import save_project, load_project, export_classification
from ui.image_viewer import ImageViewer

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


class ClassificationWindow(QMainWindow):
    closed = Signal()

    def __init__(self, project: ClassificationProject, save_path: str = None):
        super().__init__()
        self._project = project
        self._save_path = save_path
        self._images: list[str] = []
        self._index = 0

        self.setWindowTitle("Image Classification — Labeling")
        self.resize(1200, 800)

        self._scan_images()
        self._build_ui()
        if self._images:
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

        # ── top bar ──────────────────────────────────────────────────
        top = QHBoxLayout()
        for text, slot in [("Save", self._save), ("Load", self._load), ("Export", self._export)]:
            btn = QPushButton(text)
            btn.setFixedHeight(28)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.clicked.connect(slot)
            top.addWidget(btn)
        top.addSpacing(8)
        path_lbl = QLabel(self._project.dataset_path)
        path_lbl.setStyleSheet("color: #888;")
        top.addWidget(path_lbl)
        top.addStretch()
        self._counter_lbl = QLabel()
        self._counter_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self._counter_lbl)
        vbox.addLayout(top)

        # ── center: class panel + viewer ─────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        class_widget = QWidget()
        class_layout = QVBoxLayout(class_widget)
        class_layout.setContentsMargins(4, 4, 4, 4)
        class_layout.setSpacing(4)
        class_layout.addWidget(QLabel("<b>Classes</b>"))

        self._class_group = QButtonGroup(self)
        self._class_group.setExclusive(True)
        for i, cls in enumerate(self._project.classes):
            r, g, b = cls.color
            btn = QPushButton(f"  [{i + 1}]  {cls.name}")
            btn.setCheckable(True)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setFixedHeight(34)
            btn.setStyleSheet(
                f"QPushButton {{ border-left: 5px solid rgb({r},{g},{b}); text-align: left; padding-left: 6px; }}"
                f"QPushButton:checked {{ background-color: #3d5a80; }}"
            )
            btn.clicked.connect(lambda _c, idx=i: self._assign_class(idx))
            self._class_group.addButton(btn, i)
            class_layout.addWidget(btn)

        if self._class_group.buttons():
            self._class_group.buttons()[0].setChecked(True)
        class_layout.addStretch()

        self._stats_lbl = QLabel()
        self._stats_lbl.setStyleSheet("color: #888; font-size: 10px;")
        self._stats_lbl.setWordWrap(True)
        class_layout.addWidget(self._stats_lbl)

        class_widget.setMinimumWidth(180)
        class_widget.setMaximumWidth(240)
        splitter.addWidget(class_widget)

        self._viewer = ImageViewer()
        self._viewer.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        splitter.addWidget(self._viewer)
        splitter.setStretchFactor(1, 1)
        vbox.addWidget(splitter)

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
            self._index = (self._index - 1) % len(self._images)
            self._show()

    def _next(self):
        if self._images:
            self._index = (self._index + 1) % len(self._images)
            self._show()

    # ------------------------------------------------------------------
    # Labeling
    # ------------------------------------------------------------------

    def _assign_class(self, idx: int):
        if not self._images:
            return
        btn = self._class_group.button(idx)
        if btn:
            btn.setChecked(True)
        filename = os.path.basename(self._images[self._index])
        self._project.labels[filename] = idx
        self._update_counter()

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
            btn = self._class_group.button(self._project.labels[filename])
            if btn:
                btn.setChecked(True)

        self._update_counter()
        self.setWindowTitle(f"Classification — {filename}")

    def _update_counter(self):
        if not self._images:
            return
        filename = os.path.basename(self._images[self._index])
        labeled = len(self._project.labels)
        total = len(self._images)
        mark = "✓" if filename in self._project.labels else "○"
        cls_tag = ""
        if filename in self._project.labels:
            ci = self._project.labels[filename]
            if 0 <= ci < len(self._project.classes):
                cls_tag = f"  [{self._project.classes[ci].name}]"
        self._counter_lbl.setText(f"{mark} {self._index + 1}/{total}  |  {labeled} labeled{cls_tag}")
        self._stats_lbl.setText(f"Labeled: {labeled} / {total}")

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _save(self):
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
        if not isinstance(proj, ClassificationProject):
            QMessageBox.critical(self, "Wrong type", "This file is not a Classification project.")
            return
        self._project = proj
        self._save_path = path
        self._scan_images()
        self._index = 0
        if self._images:
            self._show()
        self.statusBar().showMessage("Loaded successfully.", 3000)

    def _export(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not folder:
            return
        try:
            export_classification(self._project, folder)
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
                self._assign_class(idx)
        elif key == Qt.Key.Key_Left:
            self._prev()
        elif key == Qt.Key.Key_Right:
            self._next()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
