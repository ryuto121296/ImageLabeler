from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Labeler")
        self.setFixedSize(380, 280)
        self._labeling_win = None
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Image Labeler")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; margin-bottom: 4px;")
        layout.addWidget(title)

        for text, slot in [
            ("Image Classification",  self._open_classification),
            ("Patch Classification",  self._open_patch),
            ("Load Existing Project", self._load_project),
        ]:
            btn = QPushButton(text)
            btn.setFixedHeight(44)
            btn.clicked.connect(slot)
            layout.addWidget(btn)

    # ------------------------------------------------------------------

    def _open_classification(self):
        from ui.classification.setup_dialog import ClassificationSetupDialog
        from ui.classification.window import ClassificationWindow
        dlg = ClassificationSetupDialog(self)
        if dlg.exec():
            self._launch(ClassificationWindow(dlg.get_project()))

    def _open_patch(self):
        from ui.patch.setup_dialog import PatchSetupDialog
        from ui.patch.window import PatchWindow
        dlg = PatchSetupDialog(self)
        if dlg.exec():
            self._launch(PatchWindow(dlg.get_project()))

    def _load_project(self):
        from core.io import load_project
        from core.project import ClassificationProject, PatchProject
        from ui.classification.window import ClassificationWindow
        from ui.patch.window import PatchWindow

        path, _ = QFileDialog.getOpenFileName(
            self, "Load Project", "", "Image Labeler Project (*.ilproj)"
        )
        if not path:
            return
        try:
            proj = load_project(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load project:\n{e}")
            return

        if isinstance(proj, ClassificationProject):
            self._launch(ClassificationWindow(proj, save_path=path))
        else:
            from ui.patch.window import PatchWindow
            self._launch(PatchWindow(proj, save_path=path))

    def _launch(self, win):
        self._labeling_win = win
        win.closed.connect(self.show)
        win.show()
        self.hide()
