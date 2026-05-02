from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QComboBox,
    QScrollArea, QWidget, QFileDialog, QDialogButtonBox, QMessageBox, QColorDialog,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

from core.project import ClassInfo, PatchProject, DEFAULT_COLORS

GRID_PRESETS = [("8 × 8", 8, 8), ("10 × 10", 10, 10), ("16 × 16", 16, 16),
                ("25 × 25", 25, 25), ("32 × 32", 32, 32)]


class PatchSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Patch Classification — Setup")
        self.setMinimumWidth(460)
        self._name_edits: list[QLineEdit] = []
        self._color_btns: list[QPushButton] = []
        self._colors: list[tuple[int, int, int]] = []
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

        # Grid size
        grid_row = QHBoxLayout()
        self._grid_combo = QComboBox()
        for label, *_ in GRID_PRESETS:
            self._grid_combo.addItem(label)
        self._grid_combo.addItem("Custom…")
        self._grid_combo.currentIndexChanged.connect(self._on_grid_change)

        self._custom_rows = QSpinBox()
        self._custom_cols = QSpinBox()
        for sb in (self._custom_rows, self._custom_cols):
            sb.setRange(2, 100)
            sb.setValue(10)
            sb.setVisible(False)
        self._custom_x_lbl = QLabel("×")
        self._custom_x_lbl.setVisible(False)

        grid_row.addWidget(QLabel("Grid Size:"))
        grid_row.addWidget(self._grid_combo)
        grid_row.addWidget(self._custom_rows)
        grid_row.addWidget(self._custom_x_lbl)
        grid_row.addWidget(self._custom_cols)
        grid_row.addStretch()
        layout.addLayout(grid_row)

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
        scroll.setFixedHeight(180)
        layout.addWidget(QLabel("Class Names & Colors:"))
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

    def _on_grid_change(self, idx: int):
        is_custom = (idx == len(GRID_PRESETS))
        self._custom_rows.setVisible(is_custom)
        self._custom_x_lbl.setVisible(is_custom)
        self._custom_cols.setVisible(is_custom)

    def _grid_size(self) -> tuple[int, int]:
        idx = self._grid_combo.currentIndex()
        if idx < len(GRID_PRESETS):
            _, r, c = GRID_PRESETS[idx]
            return r, c
        return self._custom_rows.value(), self._custom_cols.value()

    def _update_class_rows(self, count: int):
        while len(self._name_edits) < count:
            i = len(self._name_edits)
            color = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
            self._colors.append(color)

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            label = QLabel(f"Class {i + 1}:")
            label.setFixedWidth(55)
            edit = QLineEdit(f"Class {i + 1}")

            r, g, b = color
            color_btn = QPushButton()
            color_btn.setFixedSize(28, 24)
            color_btn.setStyleSheet(f"background-color: rgb({r},{g},{b}); border: 1px solid #555; border-radius: 3px;")
            color_btn.clicked.connect(lambda _checked, idx=i: self._pick_color(idx))

            row_layout.addWidget(label)
            row_layout.addWidget(edit, 1)
            row_layout.addWidget(color_btn)
            self._classes_layout.addWidget(row_widget)

            self._name_edits.append(edit)
            self._color_btns.append(color_btn)

        while len(self._name_edits) > count:
            self._name_edits.pop()
            self._color_btns.pop()
            self._colors.pop()
            widget = self._classes_layout.itemAt(self._classes_layout.count() - 1).widget()
            self._classes_layout.removeWidget(widget)
            widget.deleteLater()

    def _pick_color(self, idx: int):
        r, g, b = self._colors[idx]
        color = QColorDialog.getColor(QColor(r, g, b), self, f"Color for Class {idx + 1}")
        if color.isValid():
            self._colors[idx] = (color.red(), color.green(), color.blue())
            r, g, b = self._colors[idx]
            self._color_btns[idx].setStyleSheet(
                f"background-color: rgb({r},{g},{b}); border: 1px solid #555; border-radius: 3px;"
            )

    def _accept(self):
        if not self._path_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Please select a dataset folder.")
            return
        for i, edit in enumerate(self._name_edits):
            if not edit.text().strip():
                QMessageBox.warning(self, "Validation", f"Class {i + 1} name cannot be empty.")
                return
        self.accept()

    def get_project(self) -> PatchProject:
        classes = [
            ClassInfo(edit.text().strip(), self._colors[i])
            for i, edit in enumerate(self._name_edits)
        ]
        rows, cols = self._grid_size()
        return PatchProject(self._path_edit.text().strip(), classes, rows, cols)
