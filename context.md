# Image Labeler Object Detection Mode - Progress Summary (2026-05-03)

## Changes Made Today

### 1. Added Object Detection Labeling Window (`ui/detection/window.py`)
Created new `DetectionWindow` class with:
- **Main viewer area** (left, 80%): Displays images with rotating bounding boxes
- **Sidebar panel** (right, ~260px): Shows detected boxes with management controls
- **Class buttons row**: Color-coded checkable buttons for selecting classes to label
- **Per-box delete functionality**: Click a box in sidebar list and press DEL to remove

### 2. Fixed Image Viewer (`ui/detection/image_viewer.py`)
- Added `color` parameter to `_draw_box_polygon()` method (was incorrectly accessing non-existent `box.class_colors`)
- Updated `draw_box()` to pass color when creating boxes per class
- Removed unused imports (`QPainter`, `QFont`)

### 3. Fixed Import Errors in Setup Dialog (`ui/detection/setup_dialog.py`)
- Added missing `QGroupBox` import
- Added missing `Qt` import from PySide6.QtCore
- Fixed `_select_folder()` - removed incorrect tuple unpacking (PySide6 returns single value, not tuple)

### 4. Fixed Project Save (`ui/detection/window.py`)
- Simplified `_save_boxes()` logic since boxes are saved in class order (no need to look up by color)
- Added missing `cv2` import required by image display

### 5. Bug Fix Session — Class/Color Issues (`ui/detection/setup_dialog.py`, `ui/detection/window.py`)

#### `setup_dialog.py` fixes:
- **Lambda closure bug**: All 3 class buttons (Add/Edit/Remove) triggered Delete because lambda body used loop var `btn` instead of captured `b`. Refactored to separate `_on_add`, `_on_edit`, `_on_delete` methods.
- **`QListWidget.items()` crash**: `QListWidget` has no `.items()` — replaced with `range(count())` + `item(i)` pattern throughout.
- **`QListWidget.itemText()` crash**: Replaced with `item(idx).text()`.
- **Color always red on add**: Was hardcoded `"#FF0000"` — now reads `_color_combo.currentText()`.
- **Color preview never updated**: Connected `_color_combo.currentTextChanged` to `_update_color_preview()`.
- **`get_project()` assigned same color to all classes**: Now reads per-class color from `self._classes[i]["color"]`.
- **`_scan_and_populate_classes` loop variable names swapped**: `folders_seen` mapped dirname→set[ext] but loop destructured as `ext, dir_map` — rewrote to iterate file extensions directly.

#### `window.py` fixes:
- **`QScrollArea` not imported** — caused crash on window open.
- **`QImage` / `QPixmap` not imported** — caused crash in `_show()`.
- **`counter_lbl` local var** — was never stored as `self._counter_lbl`, causing `AttributeError` in `_update_counter()`.
- **`self._class_btns` never populated** — buttons created in loop but not appended; fixed.
- **`self._box_list` not added to layout** — widget was created but never placed in the scroll area layout.
- **`Qt.Key_Left/Right/Backspace` used old-style enum** — updated to `Qt.Key.Key_Left` etc.

## Current State
All files compile without errors. Object detection mode should now:
- Open from main window via "Object Detection" button
- Allow drawing rectangular bounding boxes that can be rotated
- Display class color swatches at top of sidebar for quick identification
- Show all drawn boxes in sidebar with DEL key to remove selected box
- Add/Edit/Remove classes in setup dialog with correct per-class colors
- Color preview updates live as user selects color in combo box

## Remaining Work (User Requested)
- [ ] Add count display showing total boxes per class
- [ ] Add button in sidebar list to delete/remove individual boxes from visual view
