from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from .model import Project

PROJECT_FILE = "project.json"
RECENT_LIMIT = 20

MIN_CANVAS = 64
MAX_CANVAS = 8000
CANVAS_DEFAULT = (1280, 800)


def ui_specs_root() -> Path:
    return Path.home() / "ui-specs"


def state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    path = Path(base) / "uispec"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_project_name(cwd: Path) -> str:
    try:
        top = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return Path(top).name
    except (subprocess.CalledProcessError, FileNotFoundError):
        return cwd.name


def save_project(folder: Path, project: Project) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / PROJECT_FILE
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(project.to_dict(), indent=2))
    tmp.replace(target)


def load_project(folder: Path) -> Project:
    data = json.loads((folder / PROJECT_FILE).read_text())
    return Project.from_dict(data)


def create_project(folder: Path, name: str) -> Project:
    if (folder / PROJECT_FILE).exists():
        raise FileExistsError(f"project already exists at {folder}")
    (folder / "screens").mkdir(parents=True, exist_ok=True)
    (folder / "exports").mkdir(parents=True, exist_ok=True)
    project = Project(name=name)
    save_project(folder, project)
    return project


def parse_size(text: str) -> tuple[int, int]:
    """Parse a 'WxH' pixel size such as '1280x800'."""
    parts = text.lower().replace(" ", "").split("x")
    if len(parts) != 2:
        raise ValueError("size must be WxH, e.g. 1280x800")
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        raise ValueError("size must be whole numbers, e.g. 1280x800") from None


def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in name).strip("-") or "screen"


def _screen_dest(folder: Path, index: int, name: str) -> Path:
    dest_dir = folder / "screens"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{index:02d}-{_safe_name(name)}.png"
    if dest.exists():  # never clobber another screen's image
        dest = dest_dir / f"{index:02d}-{_safe_name(name)}-{new_suffix()}.png"
    return dest


def import_image(folder: Path, source: Path, index: int, name: str) -> str:
    """Copy a source image into the project's screens/ folder and return its relative path."""
    dest = _screen_dest(folder, index, name)
    if source.suffix.lower() == ".png":
        shutil.copyfile(source, dest)
    else:
        _convert_to_png(source, dest)
    return str(dest.relative_to(folder))


def create_blank_image(folder: Path, index: int, name: str, width: int, height: int,
                       color: str = "#ffffff") -> str:
    """Write an empty canvas (a solid-color PNG) and return its relative path."""
    from PySide6.QtGui import QColor, QImage

    width, height = int(width), int(height)
    if not (MIN_CANVAS <= width <= MAX_CANVAS and MIN_CANVAS <= height <= MAX_CANVAS):
        raise ValueError(f"canvas must be {MIN_CANVAS}-{MAX_CANVAS}px on each side")
    dest = _screen_dest(folder, index, name)
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor(color))
    if not image.save(str(dest), "PNG"):
        raise OSError(f"cannot write {dest}")
    return str(dest.relative_to(folder))


def import_texture(folder: Path, source: Path, element_id: str) -> str:
    """Copy a texture image into the project's textures/ folder and return its relative path."""
    dest_dir = folder / "textures"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{element_id}-{new_suffix()}.png"
    if source.suffix.lower() == ".png":
        shutil.copyfile(source, dest)
    else:
        _convert_to_png(source, dest)
    return str(dest.relative_to(folder))


def new_suffix() -> str:
    import uuid

    return uuid.uuid4().hex[:6]


def _convert_to_png(source: Path, dest: Path) -> None:
    from PySide6.QtGui import QImage

    image = QImage(str(source))
    if image.isNull():
        raise ValueError(f"cannot read image: {source}")
    if not image.save(str(dest), "PNG"):
        raise OSError(f"cannot write {dest}")


def recent_path() -> Path:
    return state_dir() / "recent.json"


def list_recent() -> list[str]:
    path = recent_path()
    if not path.exists():
        return []
    return [p for p in json.loads(path.read_text()) if (Path(p) / PROJECT_FILE).exists()]


def add_recent(folder: Path) -> None:
    entries = [str(folder)] + [p for p in list_recent() if p != str(folder)]
    recent_path().write_text(json.dumps(entries[:RECENT_LIMIT], indent=2))
