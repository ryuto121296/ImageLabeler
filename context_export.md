# ImageLabeler — Export Format Reference

All modes export a single `labels.json` file alongside an `img/` folder containing copies of the labeled images. The `model_type` field identifies which architecture the labels are intended for.

---

## 1. Image Classification

**`model_type`: `"image_classification"`**

Intended model: single-label image classifier (e.g. CNN, ViT).  
Each image is assigned exactly one class index.

### Output structure
```
export/
  labels.json
  img/
    photo1.jpg
    photo2.jpg
    ...
```

### `labels.json` schema
```json
{
  "model_type": "image_classification",
  "classes": [
    {"name": "cat"},
    {"name": "dog"}
  ],
  "images": [
    {"filename": "img/photo1.jpg", "class": 0},
    {"filename": "img/photo2.jpg", "class": 1}
  ]
}
```

### Field notes
| Field | Type | Description |
|---|---|---|
| `classes` | array | Ordered list of class names. Index position = class id. |
| `images[].filename` | string | Path relative to the export root (always `img/<name>`). |
| `images[].class` | int | Zero-based index into `classes`. |

Only images that were assigned a label appear in `images`. Unlabeled images are omitted.

---

## 2. Patch Classification

**`model_type`: `"patch_classification"`**

Intended model: dense patch / tile classifier (e.g. anomaly detection, material inspection).  
Each image is divided into a uniform `grid_rows × grid_cols` grid and every cell is labeled independently.

### Output structure
```
export/
  labels.json
  img/
    scan1.png
    scan2.png
    ...
```

### `labels.json` schema
```json
{
  "model_type": "patch_classification",
  "classes": [
    {"name": "normal", "color": [50, 180, 50]},
    {"name": "defect", "color": [220, 50, 50]}
  ],
  "grid_rows": 4,
  "grid_cols": 4,
  "images": [
    {
      "filename": "img/scan1.png",
      "grid": [
        [0, 0, 1, 0],
        [0, 1, 1, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 1]
      ]
    }
  ]
}
```

### Field notes
| Field | Type | Description |
|---|---|---|
| `classes` | array | Ordered class list. Each entry also carries the display `color` as `[R, G, B]` (0–255). |
| `grid_rows` / `grid_cols` | int | Grid dimensions, constant across all images in the export. |
| `images[].grid` | 2-D int array | Shape `[grid_rows][grid_cols]`. Value = zero-based class index. `-1` means the cell was not labeled (only present when exported without a default class). |

To extract a patch for cell `(row, col)` from an image of size `W × H`:
```
cell_w = W / grid_cols
cell_h = H / grid_rows
x = col * cell_w
y = row * cell_h
```

---

## 3. Object Detection

**`model_type`: `"object_detection"`**

Intended model: object detector (e.g. YOLO, Faster R-CNN, DETR).  
Each image can contain multiple labeled bounding boxes, each belonging to one class.

### Output structure
```
export/
  labels.json
  img/
    frame001.jpg
    frame002.jpg
    ...
```

### `labels.json` schema
```json
{
  "model_type": "object_detection",
  "classes": [
    {"name": "car"},
    {"name": "person"}
  ],
  "images": [
    {
      "filename": "img/frame001.jpg",
      "detected_classes": [
        {
          "label": "car",
          "bbox": {
            "xmin": 100,
            "ymin": 50,
            "xmax": 300,
            "ymax": 200,
            "angle": 0.0
          }
        },
        {
          "label": "person",
          "bbox": {
            "xmin": 420,
            "ymin": 80,
            "xmax": 470,
            "ymax": 210,
            "angle": 15.5
          }
        }
      ]
    }
  ]
}
```

### Field notes
| Field | Type | Description |
|---|---|---|
| `classes` | array | Ordered class list (names only). |
| `images[].detected_classes` | array | All labeled boxes for this image. Empty array `[]` means the image was labeled as containing no objects. Images with no annotation at all are omitted. |
| `detected_classes[].label` | string | Class name string (matches an entry in `classes`). |
| `bbox.xmin` / `ymin` | int | Top-left corner of the box in pixel coordinates (origin = image top-left). |
| `bbox.xmax` / `ymax` | int | Bottom-right corner: `xmax = xmin + width`, `ymax = ymin + height`. |
| `bbox.angle` | float | Clockwise rotation in degrees around the box center. `0.0` = axis-aligned. Non-zero values indicate an oriented bounding box (OBB). |

#### Axis-aligned vs. oriented bounding boxes
When `angle == 0.0` the box is a standard AABB and `(xmin, ymin, xmax, ymax)` is sufficient.  
When `angle != 0.0` reconstruct the four corners from the center + half-extents + rotation:
```python
cx = (xmin + xmax) / 2
cy = (ymin + ymax) / 2
hw = (xmax - xmin) / 2
hh = (ymax - ymin) / 2
rad = math.radians(angle)       # clockwise → negate for standard math convention
ca, sa = math.cos(-rad), math.sin(-rad)
local = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]   # TL TR BR BL
corners = [(ca*x - sa*y + cx, sa*x + ca*y + cy) for x, y in local]
```
