import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QListWidget,
    QGroupBox, QInputDialog, QColorDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor


_DEFAULT_COLORS = [
    "#FF0000", "#00FF00", "#0000FF", "#FFFF00",
    "#FF00FF", "#00FFFF", "#FFA500", "#800080",
]


class DetectionSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Object Detection - Setup")
        self.resize(700, 500)

        self._folder_path = ""
        self._classes: list[dict] = []
        self._current_color: tuple[int, int, int] = (220, 50, 50)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # Folder selection
        folder_group = QGroupBox("Image Folder")
        folder_layout = QVBoxLayout(folder_group)

        self._folder_label = QLabel("Select the folder containing images:")
        folder_layout.addWidget(self._folder_label)

        self._folder_btn = QPushButton("Browse...")
        self._folder_btn.clicked.connect(self._select_folder)
        folder_layout.addWidget(self._folder_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._folder_path_lbl = QLabel("")
        self._folder_path_lbl.setStyleSheet("color: #888; padding-top: 4px;")
        folder_layout.addWidget(self._folder_path_lbl)

        layout.addWidget(folder_group)

        # Classes setup
        classes_group = QGroupBox("Classes")
        classes_layout = QVBoxLayout(classes_group)

        class_label = QLabel("Add classes to label:")
        class_label.setStyleSheet("margin-top: 6px;")
        classes_layout.addWidget(class_label)

        self._class_list = QListWidget()
        self._class_list.setFont(QFont("Arial", 10))
        classes_layout.addWidget(self._class_list)

        class_btn_group = QHBoxLayout()
        self._add_btn = QPushButton("+ Add")
        self._edit_btn = QPushButton("Edit")
        self._del_btn = QPushButton("Remove")
        for btn in [self._add_btn, self._edit_btn, self._del_btn]:
            btn.setFixedHeight(28)
        self._add_btn.clicked.connect(self._on_add)
        self._edit_btn.clicked.connect(self._on_edit)
        self._del_btn.clicked.connect(self._on_delete)
        class_btn_group.addWidget(self._add_btn)
        class_btn_group.addWidget(self._edit_btn)
        class_btn_group.addWidget(self._del_btn)
        class_btn_group.addStretch()
        classes_layout.addLayout(class_btn_group)

        # Class color selection
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Color for next class:"))
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(36, 26)
        self._color_btn.setToolTip("Click to pick a color")
        self._color_btn.clicked.connect(self._pick_color)
        color_row.addWidget(self._color_btn)
        color_row.addStretch()
        classes_layout.addLayout(color_row)
        self._refresh_color_btn()

        layout.addWidget(classes_group)

        info_label = QLabel(
            "Tips:\n"
            "- Click and drag to draw bounding boxes\n"
            "- Right-click on a box to rotate it\n"
            "- Drag corners to resize\n"
            "- Press Delete or click delete button in the sidebar to remove boxes\n"
            "- Use 1-9 keys for quick class selection"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "color: #666; font-size: 12px; background-color: #f5f5f5; padding: 8px; border-radius: 4px;"
        )
        layout.addWidget(info_label)

        save_btn = QPushButton("Start Labeling")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self.accept)
        layout.addWidget(save_btn)

    def _refresh_color_btn(self):
        r, g, b = self._current_color
        self._color_btn.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border: 1px solid #999; border-radius: 3px;"
        )

    def _pick_color(self):
        r, g, b = self._current_color
        color = QColorDialog.getColor(QColor(r, g, b), self, "Pick Color")
        if color.isValid():
            self._current_color = (color.red(), color.green(), color.blue())
            self._refresh_color_btn()

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder", "")
        if folder:
            self._folder_path = folder
            self._folder_path_lbl.setText(folder)
            self._scan_and_populate_classes()

    def _scan_and_populate_classes(self):
        folder = self._folder_path
        if not os.path.isdir(folder):
            return

        supported_ext = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
        found_exts: set[str] = set()

        for f in os.listdir(folder):
            ext = os.path.splitext(f)[1].lower()
            if ext in supported_ext:
                found_exts.add(ext)

        self._class_list.clear()
        self._classes = []

        ext_to_name = {
            ".jpg": "photo", ".jpeg": "photo", ".png": "png", ".bmp": "bmp",
            ".tiff": "tiff", ".tif": "tiff", ".webp": "webp",
        }
        seen: set[str] = set()
        for ext in sorted(found_exts):
            name = ext_to_name.get(ext, ext)
            if name not in seen:
                seen.add(name)
                color = _DEFAULT_COLORS[len(self._classes) % len(_DEFAULT_COLORS)]
                self._class_list.addItem(name)
                self._classes.append({"name": name, "color": color})

        if not self._classes:
            self._class_list.addItem("object")
            self._classes = [{"name": "object", "color": _DEFAULT_COLORS[0]}]

    def _on_add(self):
        name, ok = QInputDialog.getText(self, "Class Name", "Enter class name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        existing = [self._class_list.item(i).text() for i in range(self._class_list.count())]
        if name in existing:
            return
        r, g, b = self._current_color
        self._class_list.addItem(name)
        self._classes.append({"name": name, "color": f"#{r:02x}{g:02x}{b:02x}"})

    def _on_edit(self):
        idx = self._class_list.currentRow()
        if idx < 0:
            return
        current = self._class_list.item(idx).text()
        name, ok = QInputDialog.getText(self, "Edit Class Name", f"Edit class {idx + 1}:", text=current)
        if ok and name.strip():
            name = name.strip()
            self._class_list.item(idx).setText(name)
            self._classes[idx]["name"] = name

    def _on_delete(self):
        idx = self._class_list.currentRow()
        if idx >= 0:
            self._class_list.takeItem(idx)
            self._classes.pop(idx)

    def get_project(self):
        from core.project import ClassInfo, ObjectDetectionProject

        classes = []
        for i in range(self._class_list.count()):
            name = self._class_list.item(i).text().strip()
            color_str = self._classes[i]["color"] if i < len(self._classes) else _DEFAULT_COLORS[0]
            r = int(color_str[1:3], 16)
            g = int(color_str[3:5], 16)
            b = int(color_str[5:7], 16)
            classes.append(ClassInfo(name, (r, g, b)))

        return ObjectDetectionProject(
            dataset_path=self._folder_path or "",
            classes=classes,
            labels={},
        )
