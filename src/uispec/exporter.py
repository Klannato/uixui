from __future__ import annotations

import datetime as dt
import json
import os
import shutil
from pathlib import Path

from PySide6.QtGui import QImage, QPainter

from .model import BRIEF_FIELDS, FIELD_NAMES, TOKEN_FIELDS, Element, Project, Screen
from .render import draw_screen_marks

BRIEF_LABELS = {"purpose": "Purpose", "audience": "Audience", "tone": "Tone"}
TOKEN_LABELS = {"colors": "Colors", "fonts": "Fonts", "spacing": "Spacing", "radii": "Radii"}


def validate(project: Project) -> list[str]:
    warnings = []
    if not project.brief.get("purpose", "").strip():
        warnings.append("project brief: purpose is empty")
    for s in project.screens:
        for e in s.elements:
            for missing in e.missing_fields():
                warnings.append(f"{s.name} element {e.number}: {missing} is empty")
            if not e.states:
                warnings.append(f"{s.name} element {e.number}: no states listed")
    return warnings


def slug(text: str) -> str:
    safe = "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")
    return safe or "screen"


def _screen_dir_name(index: int, screen: Screen) -> str:
    return f"{index:02d}-{slug(screen.name)}"


def _element_dict(e: Element) -> dict:
    x0, y0, x1, y1 = e.bbox()
    d = {"number": e.number, "id": e.id, "kind": e.kind, "bbox": [x0, y0, x1, y1]}
    for name in FIELD_NAMES:
        d[name] = getattr(e, name)
    d["texture"] = e.texture
    return d


def texture_summary(texture: dict | None) -> str:
    if not texture:
        return "-"
    opacity = f"{round(float(texture.get('opacity', 1.0)) * 100)}% opacity"
    if texture["kind"] == "pattern":
        what = (f"{texture['pattern']} pattern in {texture.get('color') or '#808080'} "
                f"at {texture.get('scale', 1)}x")
    else:
        what = f"image {Path(texture['file']).name}, {texture.get('mode', 'tile')} at {texture.get('scale', 1)}x"
    tint = f", tinted {texture['tint']}" if texture.get("tint") else ""
    return f"{what}, {opacity}{tint}"


def _element_markdown(e: Element) -> list[str]:
    lines = [f"### Element {e.number}: {e.name or '⚠ unnamed'}", ""]
    lines.append(f"- Kind: {e.kind}")
    lines.append(f"- Purpose: {e.purpose or '⚠ missing'}")
    lines.append(f"- Behavior: {e.behavior or '-'}")
    lines.append(f"- States: {', '.join(e.states) if e.states else '⚠ not specified'}")
    lines.append(f"- Content: {e.content or '-'}")
    lines.append(f"- Constraints: {e.constraints or '-'}")
    lines.append(f"- Notes: {e.notes or '-'}")
    lines.append(f"- Reference: {e.reference or '-'}")
    lines.append(f"- Texture: {texture_summary(e.texture)}")
    lines.append("")
    return lines


def spec_markdown(project: Project, screen_dirs: dict[str, str], stamp: str) -> str:
    lines = [f"# {project.name} — UI specification", "", f"Exported: {stamp}", ""]
    lines += ["## Project brief", ""]
    for key in BRIEF_FIELDS:
        lines.append(f"- {BRIEF_LABELS[key]}: {project.brief.get(key) or '-'}")
    lines += ["", "## Design tokens", ""]
    for key in TOKEN_FIELDS:
        lines.append(f"- {TOKEN_LABELS[key]}: {project.tokens.get(key) or '-'}")
    grid = project.grid
    snap = "snapping on" if grid.get("snap", True) else "snapping off"
    lines += ["", "## Layout grid", "", f"- Grid: {grid.get('size', 8)}px ({snap})", ""]
    lines += ["", "## Screen flow", ""]
    for i, s in enumerate(project.screens, 1):
        leads = f" → leads to: {s.leads_to}" if s.leads_to else ""
        lines.append(f"{i}. {s.name} (`{screen_dirs[s.id]}/`){leads}")
    lines.append("")
    for i, s in enumerate(project.screens, 1):
        lines += [f"## Screen {i}: {s.name}", ""]
        d = screen_dirs[s.id]
        if s.blank:
            background = f", background {s.canvas_color}" if s.canvas_color else ""
            lines.append(f"- Canvas: `{d}/original.png` (blank canvas drawn from scratch, no screenshot{background})")
        else:
            lines.append(f"- Original: `{d}/original.png`")
        lines.append(f"- Annotated: `{d}/annotated.png`")
        lines.append(f"- Machine-readable elements: `{d}/elements.json`")
        if s.leads_to:
            lines.append(f"- Leads to: {s.leads_to}")
        lines.append("")
        for e in s.elements:
            lines += _element_markdown(e)
        if s.arrows:
            lines += ["### Flow arrows", ""]
            for a in s.arrows:
                target = f"element {a.to_number}" if a.to_number is not None else "a point on the screen"
                label = f" ({a.label})" if a.label else ""
                lines.append(f"- element {a.from_number} → {target}{label}")
            lines.append("")
        if s.labels:
            lines += ["### Screen notes", ""]
            for t in s.labels:
                lines.append(f"- {t.text}")
            lines.append("")
    return "\n".join(lines)


def render_screen(folder: Path, screen: Screen, out: Path, selected=()) -> Path:
    image = QImage(str(folder / screen.image))
    if image.isNull():
        raise ValueError(f"cannot read screen image: {screen.image}")
    painter_target = image.convertToFormat(QImage.Format.Format_ARGB32)
    painter = QPainter(painter_target)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        draw_screen_marks(painter, screen, selected, folder)
    finally:
        painter.end()
    out.parent.mkdir(parents=True, exist_ok=True)
    if not painter_target.save(str(out), "PNG"):
        raise OSError(f"cannot write {out}")
    return out


def export(folder: Path, project: Project) -> dict:
    stamp = dt.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    export_dir = folder / "exports" / stamp
    suffix = 1
    while export_dir.exists():
        export_dir = folder / "exports" / f"{stamp}-{suffix}"
        suffix += 1
    export_dir.mkdir(parents=True)

    screen_dirs = {}
    for index, screen in enumerate(project.screens, 1):
        name = _screen_dir_name(index, screen)
        screen_dirs[screen.id] = f"screens/{name}"
        sdir = export_dir / "screens" / name
        sdir.mkdir(parents=True)
        shutil.copyfile(folder / screen.image, sdir / "original.png")
        render_screen(folder, screen, sdir / "annotated.png")
        elements = [_element_dict(e) for e in screen.elements]
        for d, e in zip(elements, screen.elements):
            if e.texture and e.texture["kind"] == "image":
                d["texture"] = {**e.texture, "file": f"textures/{Path(e.texture['file']).name}"}
        data = {
            "screen": screen.name,
            "leads_to": screen.leads_to,
            "blank": screen.blank,
            "background": screen.canvas_color or None,
            "elements": elements,
            "arrows": [{"from": a.from_number, "to": a.to_number, "to_point": a.to_point, "label": a.label}
                       for a in screen.arrows],
            "labels": [{"text": t.text, "x": t.x, "y": t.y} for t in screen.labels],
        }
        (sdir / "elements.json").write_text(json.dumps(data, indent=2))
        for e in screen.elements:
            if e.texture and e.texture["kind"] == "image":
                tdir = sdir / "textures"
                tdir.mkdir(exist_ok=True)
                shutil.copyfile(folder / e.texture["file"], tdir / Path(e.texture["file"]).name)

    (export_dir / "spec.md").write_text(spec_markdown(project, screen_dirs, stamp))

    current = folder / "current"
    if current.is_symlink() or current.is_file():
        current.unlink()
    elif current.exists():
        shutil.rmtree(current)
    os.symlink(os.path.relpath(export_dir, folder), current)

    return {"path": str(export_dir), "current": str(current), "warnings": validate(project)}
