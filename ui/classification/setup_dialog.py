from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox,
    QScrollArea, QWidget, QFileDialog, QDialogButtonBox, QMessageBox,
)
from PySide6.QtCore import Qt

from core.project import ClassInfo, ClassificationProject, DEFAULT_COLORS


class ClassificationSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Classification — Setup")
        self.setMinimumWidth(420)
        self._name_edits: list[QLineEdit] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Dataset folder
        folder_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select dataset folder…")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse)
        folder_row.addWidget(QLabel("Dataset Folder:"))
        folder_row.addWidget(self._path_edit, 1)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        # Number of classes
        count_row = QHBoxLayout()
        self._count_spin = QSpinBox()
        self._count_spin.setRange(2, 9)
        self._count_spin.setValue(2)
        self._count_spin.valueChanged.connect(self._update_class_rows)
        count_row.addWidget(QLabel("Number of Classes:"))
        count_row.addWidget(self._count_spin)
        count_row.addStretch()
        layout.addLayout(count_row)

        # Scrollable class list
        self._classes_widget = QWidget()
        self._classes_layout = QVBoxLayout(self._classes_widget)
        self._classes_layout.setContentsMargins(0, 0, 0, 0)
        self._classes_layout.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidget(self._classes_widget)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(160)
        layout.addWidget(QLabel("Class Names:"))
        layout.addWidget(scroll)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._update_class_rows(2)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Dataset Folder")
        if folder:
            self._path_edit.setText(folder)

    def _update_class_rows(self, count: int):
        while len(self._name_edits) < count:
            i = len(self._name_edits)
            row = QHBoxLayout()
            label = QLabel(f"Class {i + 1}:")
            label.setFixedWidth(55)
            edit = QLineEdit(f"Class {i + 1}")
            row.addWidget(label)
            row.addWidget(edit)
            container = QWidget()
            container.setLayout(row)
            self._classes_layout.addWidget(container)
            self._name_edits.append(edit)

        while len(self._name_edits) > count:
            edit = self._name_edits.pop()
            widget = self._classes_layout.itemAt(self._classes_layout.count() - 1).widget()
            self._classes_layout.removeWidget(widget)
            widget.deleteLater()

    def _accept(self):
        if not self._path_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Please select a dataset folder.")
            return
        for i, edit in enumerate(self._name_edits):
            if not edit.text().strip():
                QMessageBox.warning(self, "Validation", f"Class {i + 1} name cannot be empty.")
                return
        self.accept()

    def get_project(self) -> ClassificationProject:
        classes = [
            ClassInfo(edit.text().strip(), DEFAULT_COLORS[i % len(DEFAULT_COLORS)])
            for i, edit in enumerate(self._name_edits)
        ]
        return ClassificationProject(self._path_edit.text().strip(), classes)
