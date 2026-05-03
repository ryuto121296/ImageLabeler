from dataclasses import dataclass, field

DEFAULT_COLORS: list[tuple[int, int, int]] = [
    (220,  50,  50),
    ( 50, 180,  50),
    ( 50, 100, 220),
    (220, 200,  50),
    (200,  50, 200),
    ( 50, 200, 200),
    (220, 130,  50),
    (130,  50, 200),
    ( 50, 200, 130),
]


@dataclass
class ClassInfo:
    name: str
    color: tuple[int, int, int]


@dataclass
class ClassificationProject:
    dataset_path: str
    classes: list[ClassInfo]
    labels: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "mode": "classification",
            "dataset_path": self.dataset_path,
            "classes": [{"name": c.name, "color": list(c.color)} for c in self.classes],
            "labels": self.labels,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ClassificationProject":
        classes = [ClassInfo(c["name"], tuple(c["color"])) for c in d["classes"]]
        return cls(d["dataset_path"], classes, d.get("labels", {}))


@dataclass
class Box:
    """Bounding box for object detection."""
    x: int      # left coordinate (0 to img_width)
    y: int      # top coordinate (0 to img_height)
    width: int  # box width in pixels
    height: int # box height in pixels
    angle: float = 0.0   # rotation angle in degrees, clockwise positive
    label: str | None = None  # optional custom label text


@dataclass
class DetectionBox:
    """Detection result for one object instance."""
    class_idx: int      # index into project.classes
    color: tuple[int, int, int]  # RGB color from class definition
    box: Box            # bounding box with optional rotation
    id: int = 0         # unique identifier for the box


@dataclass
class PatchProject:
    dataset_path: str
    classes: list[ClassInfo]
    grid_rows: int
    grid_cols: int
    labels: dict[str, list[list[int]]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "mode": "patch_classification",
            "dataset_path": self.dataset_path,
            "classes": [{"name": c.name, "color": list(c.color)} for c in self.classes],
            "grid_rows": self.grid_rows,
            "grid_cols": self.grid_cols,
            "labels": self.labels,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PatchProject":
        classes = [ClassInfo(c["name"], tuple(c["color"])) for c in d["classes"]]
        return cls(d["dataset_path"], classes, d["grid_rows"], d["grid_cols"], d.get("labels", {}))


@dataclass
class ObjectDetectionProject:
    """Project for object detection labeling mode."""
    dataset_path: str
    classes: list[ClassInfo]
    labels: dict[str, list[DetectionBox]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        boxes_data = []
        for filename, detections in self.labels.items():
            for det in detections:
                boxes_data.append({
                    "filename": filename,
                    "class_idx": det.class_idx,
                    "box": {
                        "x": det.box.x,
                        "y": det.box.y,
                        "width": det.box.width,
                        "height": det.box.height,
                        "angle": det.box.angle,
                        "label": det.box.label,
                    },
                    "color": det.color,
                })
        return {
            "mode": "object_detection",
            "dataset_path": self.dataset_path,
            "classes": [{"name": c.name, "color": list(c.color)} for c in self.classes],
            "boxes": boxes_data,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ObjectDetectionProject":
        classes = [ClassInfo(c["name"], tuple(c["color"])) for c in d["classes"]]
        labels: dict[str, list[DetectionBox]] = {}
        for box_data in d.get("boxes", []):
            class_idx = box_data["class_idx"]
            color = box_data.get("color", (0, 0, 0))
            box_dict = box_data["box"]
            b = Box(
                x=box_dict["x"],
                y=box_dict["y"],
                width=box_dict["width"],
                height=box_dict["height"],
                angle=box_dict.get("angle", 0.0),
                label=box_dict.get("label"),
            )
            det = DetectionBox(class_idx, color, b)
            filename = box_data.get("filename") or ""
            if filename not in labels:
                labels[filename] = []
            labels[filename].append(det)
        return cls(d["dataset_path"], classes, labels)
