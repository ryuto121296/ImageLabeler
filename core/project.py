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
