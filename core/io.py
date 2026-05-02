import json
import os
import shutil

from .project import ClassificationProject, PatchProject


def save_project(project: ClassificationProject | PatchProject, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(project.to_dict(), f, indent=2, ensure_ascii=False)


def load_project(path: str) -> ClassificationProject | PatchProject:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    mode = d.get("mode")
    if mode == "classification":
        return ClassificationProject.from_dict(d)
    if mode == "patch_classification":
        return PatchProject.from_dict(d)
    raise ValueError(f"Unknown project mode: {mode!r}")


def export_classification(project: ClassificationProject, output_path: str) -> None:
    img_dir = os.path.join(output_path, "img")
    os.makedirs(img_dir, exist_ok=True)

    image_list = []
    for filename, class_idx in project.labels.items():
        src = os.path.join(project.dataset_path, filename)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(img_dir, filename))
            image_list.append({"filename": f"img/{filename}", "class": class_idx})

    payload = {
        "classes": [{"name": c.name} for c in project.classes],
        "images": image_list,
    }
    with open(os.path.join(output_path, "labels.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def export_patch(project: PatchProject, output_path: str, default_class: int = -1) -> None:
    img_dir = os.path.join(output_path, "img")
    os.makedirs(img_dir, exist_ok=True)

    image_list = []
    for filename, grid in project.labels.items():
        src = os.path.join(project.dataset_path, filename)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(img_dir, filename))
            if default_class >= 0:
                resolved = [[default_class if ci == -1 else ci for ci in row] for row in grid]
            else:
                resolved = grid
            image_list.append({"filename": f"img/{filename}", "grid": resolved})

    payload = {
        "classes": [{"name": c.name, "color": list(c.color)} for c in project.classes],
        "grid_rows": project.grid_rows,
        "grid_cols": project.grid_cols,
        "images": image_list,
    }
    with open(os.path.join(output_path, "labels.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
