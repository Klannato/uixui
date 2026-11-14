"""Per-user desktop integration: an application-launcher entry and its icon."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from . import APP_ID, APP_NAME, APP_SCRIPT

ASSET_DIR = Path(__file__).parent / "gui" / "assets"
ICON_SVG = ASSET_DIR / f"{APP_ID}.svg"
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
DESKTOP_FILE = f"{APP_ID}.desktop"


def data_home() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base)


def icon_dir() -> Path:
    return data_home() / "icons" / "hicolor"


def applications_dir() -> Path:
    return data_home() / "applications"


def desktop_file() -> Path:
    return applications_dir() / DESKTOP_FILE


def scalable_icon() -> Path:
    return icon_dir() / "scalable" / "apps" / f"{APP_ID}.svg"


def png_icon(size: int) -> Path:
    return icon_dir() / f"{size}x{size}" / "apps" / f"{APP_ID}.png"


def exec_command() -> str:
    """Absolute path to the app executable, preferring the one beside this command."""
    beside = Path(sys.argv[0]).resolve().with_name(APP_SCRIPT)
    if beside.exists():
        return str(beside)
    found = shutil.which(APP_SCRIPT)
    if found:
        return found
    return str(Path(sys.executable).with_name(APP_SCRIPT))


def desktop_entry(command: str | None = None) -> str:
    return "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        f"Name={APP_NAME}",
        "GenericName=UI Spec Annotator",
        "Comment=Annotate UI screenshots and hand specs to coding agents",
        f"Exec={command or exec_command()}",
        f"Icon={APP_ID}",
        "Terminal=false",
        "Categories=Development;",
        "Keywords=ui;spec;annotation;design;agent;screenshot;",
        f"StartupWMClass={APP_ID}",
        "",
    ])


def _render_pngs() -> list[Path]:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(str(ICON_SVG))
    if not renderer.isValid():
        raise RuntimeError(f"cannot read icon {ICON_SVG}")
    written = []
    for size in ICON_SIZES:
        target = png_icon(size)
        target.parent.mkdir(parents=True, exist_ok=True)
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        if not image.save(str(target), "PNG"):
            raise RuntimeError(f"cannot write icon {target}")
        written.append(target)
    return written


def install(command: str | None = None) -> dict:
    """Write the launcher entry and icons for the current user. Returns what was written."""
    scalable = scalable_icon()
    scalable.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ICON_SVG, scalable)
    icons = [scalable, *_render_pngs()]
    applications_dir().mkdir(parents=True, exist_ok=True)
    target = desktop_file()
    target.write_text(desktop_entry(command))
    return {
        "desktop": str(target),
        "icons": [str(p) for p in icons],
        "exec": command or exec_command(),
    }


def uninstall() -> dict:
    removed = []
    for path in (desktop_file(), scalable_icon(), *(png_icon(s) for s in ICON_SIZES)):
        if path.exists():
            path.unlink()
            removed.append(str(path))
    return {"removed": removed}
