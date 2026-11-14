"""Command handlers shared by the local API, the CLI, and the GUI. Each handler runs on the GUI thread."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import datetime as dt

from . import capture, exporter, store
from .controller import Controller
from .model import BRIEF_FIELDS, FIELD_NAMES, TOKEN_FIELDS, Arrow, Screen, TextLabel

Reply = Callable[..., None]


class CommandError(Exception):
    pass


COMMANDS: dict[str, Callable[[Controller, dict], object]] = {}
ASYNC: dict[str, Callable[[Controller, dict, Reply], None]] = {}


def command(name: str):
    def wrap(fn):
        COMMANDS[name] = fn
        return fn
    return wrap


def resolve_screen(ctrl: Controller, ref: str | None) -> Screen:
    project = ctrl.require_project()
    if ref is None:
        screen = ctrl.current_screen()
        if screen is None:
            raise CommandError("no screen selected; add a screen first")
        return screen
    for s in project.screens:
        if s.id == ref or s.name == ref:
            return s
    raise CommandError(f"no screen {ref!r}")


def _number(args: dict, key: str = "number") -> int:
    if key not in args:
        raise CommandError(f"missing {key}")
    return int(args[key])


def dispatch(ctrl: Controller, name: str, args: dict, reply: Reply) -> None:
    if name in ASYNC:
        try:
            ASYNC[name](ctrl, args, reply)
        except Exception as exc:
            reply(error=str(exc))
        return
    try:
        if name not in COMMANDS:
            raise CommandError(f"unknown command {name!r}")
        reply(result=COMMANDS[name](ctrl, args))
    except Exception as exc:
        reply(error=str(exc))


# ---- app and project -------------------------------------------------------

@command("app.status")
def app_status(ctrl: Controller, args: dict):
    return {
        "project": str(ctrl.folder) if ctrl.is_open else None,
        "screen": ctrl.current_screen_id,
    }


@command("app.quit")
def app_quit(ctrl: Controller, args: dict):
    ctrl.quit_requested.emit()
    return {"quitting": True}


@command("project.info")
def project_info(ctrl: Controller, args: dict):
    project = ctrl.require_project()
    return {"folder": str(ctrl.folder), **project.to_dict()}


@command("project.list")
def project_list(ctrl: Controller, args: dict):
    return {"projects": store.list_recent()}


@command("project.new")
def project_new(ctrl: Controller, args: dict):
    folder = Path(args["folder"]).expanduser()
    name = args.get("name") or folder.name
    ctrl.create_project(folder, name)
    return {"folder": str(folder), "name": name}


@command("project.open")
def project_open(ctrl: Controller, args: dict):
    folder = Path(args["folder"]).expanduser()
    if not (folder / store.PROJECT_FILE).exists():
        raise CommandError(f"no project at {folder}")
    ctrl.open_project(folder)
    return {"folder": str(folder)}


@command("project.set_brief")
def project_set_brief(ctrl: Controller, args: dict):
    fields = args.get("fields", {})
    _check_fields(fields, BRIEF_FIELDS)

    def apply(project):
        project.brief.update(fields)
    ctrl.mutate(apply)
    return {"brief": dict(ctrl.project.brief)}


@command("project.set_tokens")
def project_set_tokens(ctrl: Controller, args: dict):
    fields = args.get("fields", {})
    _check_fields(fields, TOKEN_FIELDS)

    def apply(project):
        project.tokens.update(fields)
    ctrl.mutate(apply)
    return {"tokens": dict(ctrl.project.tokens)}


def _check_fields(fields: dict, allowed) -> None:
    unknown = set(fields) - set(allowed)
    if unknown:
        raise CommandError(f"unknown fields: {', '.join(sorted(unknown))}")


# ---- screens ---------------------------------------------------------------

def _screen_summary(index: int, s: Screen) -> dict:
    return {"index": index, "id": s.id, "name": s.name, "image": s.image,
            "leads_to": s.leads_to, "elements": len(s.elements)}


@command("screen.list")
def screen_list(ctrl: Controller, args: dict):
    project = ctrl.require_project()
    return {"screens": [_screen_summary(i, s) for i, s in enumerate(project.screens, 1)]}


@command("screen.add")
def screen_add(ctrl: Controller, args: dict):
    return add_screen_from_file(ctrl, Path(args["path"]).expanduser(), args.get("name"))


def add_screen_from_file(ctrl: Controller, source: Path, name: str | None = None) -> dict:
    project_folder = ctrl.folder
    if not source.exists():
        raise CommandError(f"no such image: {source}")
    ctrl.require_project()
    index = len(ctrl.project.screens) + 1
    screen_name = name or source.stem
    image = store.import_image(project_folder, source, index, screen_name)
    screen = Screen(name=screen_name, image=image)

    def apply(project):
        project.screens.append(screen)
    ctrl.mutate(apply)
    ctrl.current_screen_id = screen.id
    ctrl.changed.emit()
    return {"id": screen.id, "name": screen.name, "image": image}


def _capture(ctrl: Controller, args: dict, reply: Reply) -> None:
    ctrl.require_project()

    def done(path: Path | None, error: str | None):
        if error:
            reply(error=error)
            return
        try:
            reply(result=add_screen_from_file(ctrl, path, args.get("name")))
        except Exception as exc:
            reply(error=str(exc))

    capture.request_screenshot(done)


ASYNC["screen.capture"] = _capture


@command("screen.select")
def screen_select(ctrl: Controller, args: dict):
    screen = resolve_screen(ctrl, args.get("screen"))
    ctrl.current_screen_id = screen.id
    ctrl.changed.emit()
    return {"id": screen.id}


@command("screen.set")
def screen_set(ctrl: Controller, args: dict):
    screen = resolve_screen(ctrl, args.get("screen"))
    sid = screen.id
    leads_to = args.get("leads_to", screen.leads_to)

    def apply(project):
        project.screen(sid).leads_to = leads_to
    ctrl.mutate(apply)
    return {"id": sid, "leads_to": leads_to}


@command("screen.reorder")
def screen_reorder(ctrl: Controller, args: dict):
    screen = resolve_screen(ctrl, args.get("screen"))
    index = int(args["index"])

    def apply(project):
        project.screens.remove(screen)
        project.screens.insert(max(0, min(index - 1, len(project.screens))), screen)
    ctrl.mutate(apply)
    return screen_list(ctrl, {})


@command("screen.remove")
def screen_remove(ctrl: Controller, args: dict):
    screen = resolve_screen(ctrl, args.get("screen"))
    sid = screen.id

    def apply(project):
        project.screens = [s for s in project.screens if s.id != sid]
    ctrl.mutate(apply)
    return {"removed": sid}


# ---- elements, arrows, labels ----------------------------------------------

def _points_from_args(kind: str, args: dict) -> list[list[float]]:
    if kind == "freehand":
        points = args.get("points")
        if not points or len(points) < 2:
            raise CommandError("freehand needs at least two points")
        return [[float(x), float(y)] for x, y in points]
    box = args.get("box")
    if not box or len(box) != 4:
        raise CommandError("rect and ellipse need box [x, y, w, h]")
    x, y, w, h = (float(v) for v in box)
    return [[x, y], [x + w, y + h]]


@command("element.add")
def element_add(ctrl: Controller, args: dict):
    screen = resolve_screen(ctrl, args.get("screen"))
    kind = args.get("kind", "rect")
    points = _points_from_args(kind, args)
    sid = screen.id
    created = {}

    def apply(project):
        e = project.screen(sid).add_element(kind, points)
        created["number"] = e.number
        created["id"] = e.id
    ctrl.mutate(apply)
    return {"screen": sid, **created}


@command("element.list")
def element_list(ctrl: Controller, args: dict):
    screen = resolve_screen(ctrl, args.get("screen"))
    return {"screen": screen.id, "elements": [e.to_dict() for e in screen.elements]}


@command("element.edit")
def element_edit(ctrl: Controller, args: dict):
    screen = resolve_screen(ctrl, args.get("screen"))
    number = _number(args)
    fields = args.get("fields", {})
    unknown = set(fields) - set(FIELD_NAMES)
    if unknown:
        raise CommandError(f"unknown fields: {', '.join(sorted(unknown))}")
    if screen.element(number) is None:
        raise CommandError(f"no element {number} on {screen.name}")
    sid = screen.id

    def apply(project):
        e = project.screen(sid).element(number)
        for key, value in fields.items():
            setattr(e, key, list(value) if key == "states" else str(value))
    ctrl.mutate(apply)
    return {"element": ctrl.project.screen(sid).element(number).to_dict()}


@command("element.resize")
def element_resize(ctrl: Controller, args: dict):
    screen = resolve_screen(ctrl, args.get("screen"))
    number = _number(args)
    if screen.element(number) is None:
        raise CommandError(f"no element {number} on {screen.name}")
    box = args.get("box")
    if not box or len(box) != 4:
        raise CommandError("resize needs box [x, y, w, h]")
    x, y, w, h = (float(v) for v in box)
    sid = screen.id

    def apply(project):
        project.screen(sid).element(number).resize(x, y, x + w, y + h)
    try:
        ctrl.mutate(apply)
    except ValueError as exc:
        raise CommandError(str(exc)) from exc
    return {"element": ctrl.project.screen(sid).element(number).to_dict()}


@command("element.delete")
def element_delete(ctrl: Controller, args: dict):
    screen = resolve_screen(ctrl, args.get("screen"))
    number = _number(args)
    sid = screen.id

    def apply(project):
        project.screen(sid).delete_element(number)
    ctrl.mutate(apply)
    return {"deleted": number}


@command("arrow.add")
def arrow_add(ctrl: Controller, args: dict):
    screen = resolve_screen(ctrl, args.get("screen"))
    source = _number(args, "from")
    if screen.element(source) is None:
        raise CommandError(f"no element {source} on {screen.name}")
    target = args.get("to")
    to_point = args.get("to_point")
    if (target is None) == (to_point is None):
        raise CommandError("give exactly one of --to <number> or --to-point x,y")
    if target is not None and screen.element(int(target)) is None:
        raise CommandError(f"no element {target} on {screen.name}")
    arrow = Arrow(from_number=source, to_number=int(target) if target is not None else None,
                  to_point=[float(v) for v in to_point] if to_point is not None else None,
                  label=args.get("label", ""))
    sid = screen.id

    def apply(project):
        project.screen(sid).arrows.append(arrow)
    ctrl.mutate(apply)
    return {"id": arrow.id}


@command("label.add")
def label_add(ctrl: Controller, args: dict):
    screen = resolve_screen(ctrl, args.get("screen"))
    label = TextLabel(text=args["text"], x=float(args.get("x", 10)), y=float(args.get("y", 10)))
    sid = screen.id

    def apply(project):
        project.screen(sid).labels.append(label)
    ctrl.mutate(apply)
    return {"id": label.id}


# ---- export, render, history -----------------------------------------------

@command("export")
def export_project(ctrl: Controller, args: dict):
    project = ctrl.require_project()
    return exporter.export(ctrl.folder, project)


@command("render")
def render(ctrl: Controller, args: dict):
    screen = resolve_screen(ctrl, args.get("screen"))
    out = Path(args["out"]).expanduser() if args.get("out") else None
    if out is None:
        stamp = dt.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        out = ctrl.folder / "renders" / f"{stamp}-{exporter.slug(screen.name)}.png"
    path = exporter.render_screen(ctrl.folder, screen, out, selected=None)
    return {"path": str(path)}


@command("undo")
def undo(ctrl: Controller, args: dict):
    return {"undone": ctrl.undo()}


@command("redo")
def redo(ctrl: Controller, args: dict):
    return {"redone": ctrl.redo()}
