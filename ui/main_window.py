import os
import cv2
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QKeyEvent, QPixmap

from .image_viewer import ImageViewer

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Labeler")
        self.resize(1100, 750)

        self._images: list[str] = []
        self._index: int = 0

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── top bar ──────────────────────────────────────────────────
        top = QHBoxLayout()
        self._select_btn = QPushButton("Select Image Folder")
        self._select_btn.clicked.connect(self._select_folder)
        self._counter_lbl = QLabel()
        self._counter_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self._select_btn)
        top.addStretch()
        top.addWidget(self._counter_lbl)
        layout.addLayout(top)

        # ── image viewer ──────────────────────────────────────────────
        self._viewer = ImageViewer()
        self._viewer.setMinimumSize(400, 300)
        layout.addWidget(self._viewer)

        # ── nav buttons ───────────────────────────────────────────────
        nav = QHBoxLayout()
        self._prev_btn = QPushButton("◀  Previous")
        self._next_btn = QPushButton("Next  ▶")
        self._prev_btn.setFixedWidth(120)
        self._next_btn.setFixedWidth(120)
        self._prev_btn.clicked.connect(self._prev)
        self._next_btn.clicked.connect(self._next)
        self._prev_btn.setEnabled(False)
        self._next_btn.setEnabled(False)
        self._prev_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._next_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._select_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._viewer.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        nav.addStretch()
        nav.addWidget(self._prev_btn)
        nav.addWidget(self._next_btn)
        nav.addStretch()
        layout.addLayout(nav)

    # ------------------------------------------------------------------
    # Folder selection
    # ------------------------------------------------------------------

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if not folder:
            return

        self._images = sorted(
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXT
        )
        self._index = 0

        has_images = bool(self._images)
        self._prev_btn.setEnabled(has_images)
        self._next_btn.setEnabled(has_images)

        if has_images:
            self._show()
        else:
            self._viewer.clear()
            self._counter_lbl.clear()

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
    # Image rendering
    # ------------------------------------------------------------------

    def _show(self):
        if not self._images:
            return

        path = self._images[self._index]
        img = cv2.imread(path)

        if img is None:
            self._counter_lbl.setText(f"Cannot load: {os.path.basename(path)}")
            return

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        qimg = QImage(img_rgb.data, w, h, w * ch, QImage.Format.Format_RGB888).copy()
        self._viewer.set_pixmap(QPixmap.fromImage(qimg))

        name = os.path.basename(path)
        self._counter_lbl.setText(f"{self._index + 1} / {len(self._images)}  |  {name}")
        self.setWindowTitle(f"Image Labeler — {name}")

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Left:
            self._prev()
        elif event.key() == Qt.Key.Key_Right:
            self._next()
        else:
            super().keyPressEvent(event)
