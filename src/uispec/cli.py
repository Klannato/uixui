"""`uispec` command line. Every command talks to the running app over its local API, starting the app if needed."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import api, store

SKILL_SOURCE = Path(__file__).parent / "skill" / "ui-spec"
DEFAULT_SKILL_TARGET = Path.home() / ".config" / "opencode" / "skills" / "ui-spec"


class CliError(Exception):
    pass


def _ping() -> bool:
    try:
        api.call("app.status", timeout=2)
        return True
    except api.AppUnreachable:
        return False


def ensure_app(project: Path | None = None) -> None:
    if _ping():
        return
    cmd = [sys.executable, "-m", "uispec.gui"]
    if project is not None:
        cmd += ["--project", str(project)]
    log = store.state_dir() / "app.log"
    with open(log, "ab") as out:
        subprocess.Popen(cmd, start_new_session=True, stdin=subprocess.DEVNULL, stdout=out, stderr=out)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if _ping():
            return
        time.sleep(0.25)
    raise CliError(f"app did not start; see {log}")


def send(name: str, args: dict | None = None):
    try:
        answer = api.call(name, args or {})
    except api.AppUnreachable as exc:
        raise CliError(f"uispec app is not reachable ({exc}). Run `uispec app open`.") from exc
    if "error" in answer:
        raise CliError(answer["error"])
    return answer["result"]


def _kv(pairs: list[str] | None) -> dict:
    out = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise CliError(f"expected key=value, got {pair!r}")
        key, value = pair.split("=", 1)
        out[key.strip()] = value
    return out


def _box(text: str) -> list[float]:
    parts = [float(v) for v in text.split(",")]
    if len(parts) != 4:
        raise CliError("box must be x,y,w,h")
    return parts


def _point(text: str) -> list[float]:
    parts = [float(v) for v in text.split(",")]
    if len(parts) != 2:
        raise CliError("point must be x,y")
    return parts


def _emit(result, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result))
    else:
        print(json.dumps(result, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="uispec", description="Annotate UI screenshots for agents.")
    parser.add_argument("--json", action="store_true", help="compact JSON output")
    sub = parser.add_subparsers(dest="group", required=True)

    app = sub.add_parser("app", help="control the app window").add_subparsers(dest="cmd", required=True)
    app_open = app.add_parser("open", help="start the app if it is not running")
    app_open.add_argument("--project", type=Path)
    app.add_parser("status")
    app.add_parser("quit")

    project = sub.add_parser("project", help="projects").add_subparsers(dest="cmd", required=True)
    pnew = project.add_parser("new", help="create a project and open it")
    pnew.add_argument("--name")
    pnew.add_argument("--dir", type=Path, help="project folder (default ~/ui-specs/<name>)")
    project.add_parser("list")
    popen = project.add_parser("open")
    popen.add_argument("folder", type=Path)
    project.add_parser("info")
    pbrief = project.add_parser("brief", help="set brief fields: purpose, audience, tone")
    pbrief.add_argument("--set", action="append", metavar="KEY=VALUE")
    ptokens = project.add_parser("tokens", help="set token fields: colors, fonts, spacing, radii")
    ptokens.add_argument("--set", action="append", metavar="KEY=VALUE")

    screen = sub.add_parser("screen", help="screens").add_subparsers(dest="cmd", required=True)
    sadd = screen.add_parser("add", help="add a screenshot file")
    sadd.add_argument("path", type=Path)
    sadd.add_argument("--name")
    scap = screen.add_parser("capture", help="capture a region (the user picks it)")
    scap.add_argument("--name")
    screen.add_parser("list")
    sselect = screen.add_parser("select")
    sselect.add_argument("screen")
    sset = screen.add_parser("set")
    sset.add_argument("screen", nargs="?")
    sset.add_argument("--leads-to")
    sreorder = screen.add_parser("reorder")
    sreorder.add_argument("screen")
    sreorder.add_argument("--index", type=int, required=True)
    sremove = screen.add_parser("remove")
    sremove.add_argument("screen")

    element = sub.add_parser("element", help="numbered elements (shapes with pins)").add_subparsers(dest="cmd", required=True)
    eadd = element.add_parser("add")
    eadd.add_argument("--screen")
    eadd.add_argument("--kind", choices=["rect", "ellipse"], default="rect")
    eadd.add_argument("--box", required=True, help="x,y,w,h in image pixels")
    elist = element.add_parser("list")
    elist.add_argument("--screen")
    eedit = element.add_parser("edit")
    eedit.add_argument("number", type=int)
    eedit.add_argument("--screen")
    eedit.add_argument("--set", action="append", metavar="FIELD=VALUE",
                       help="name, purpose, behavior, content, constraints, notes, reference, or states "
                            "(comma-separated)")
    eresize = element.add_parser("resize", help="set an element's box to x,y,w,h")
    eresize.add_argument("number", type=int)
    eresize.add_argument("--screen")
    eresize.add_argument("--box", required=True, help="x,y,w,h in image pixels")
    edel = element.add_parser("delete")
    edel.add_argument("number", type=int)
    edel.add_argument("--screen")

    arrow = sub.add_parser("arrow", help="arrows from a pin").add_subparsers(dest="cmd", required=True)
    aadd = arrow.add_parser("add")
    aadd.add_argument("--screen")
    aadd.add_argument("--from", dest="source", type=int, required=True)
    target = aadd.add_mutually_exclusive_group(required=True)
    target.add_argument("--to", type=int)
    target.add_argument("--to-point", help="x,y")
    aadd.add_argument("--label", default="")

    label = sub.add_parser("label", help="free text notes on a screen").add_subparsers(dest="cmd", required=True)
    ladd = label.add_parser("add")
    ladd.add_argument("text")
    ladd.add_argument("--screen")
    ladd.add_argument("--x", type=float, default=10)
    ladd.add_argument("--y", type=float, default=10)

    sub.add_parser("export", help="write a timestamped bundle and update current/")
    render = sub.add_parser("render", help="render a screen with its annotations to PNG")
    render.add_argument("--screen")
    render.add_argument("--out")
    sub.add_parser("undo")
    sub.add_parser("redo")

    skill = sub.add_parser("skill", help="the ui-spec agent skill").add_subparsers(dest="cmd", required=True)
    sinstall = skill.add_parser("install")
    sinstall.add_argument("--target", type=Path, default=DEFAULT_SKILL_TARGET)
    return parser


def run(args: argparse.Namespace):
    g, c = args.group, getattr(args, "cmd", None)

    if g == "skill":
        target = args.target.expanduser()
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(SKILL_SOURCE, target)
        return {"installed": str(target)}

    if g == "app":
        if c == "open":
            ensure_app(args.project.expanduser() if args.project else None)
            return send("app.status")
        if c == "status":
            return send("app.status") if _ping() else {"running": False}
        if c == "quit":
            return send("app.quit") if _ping() else {"running": False}

    if g == "project":
        if c == "new":
            name = args.name or store.default_project_name(Path.cwd())
            folder = (args.dir or store.ui_specs_root() / name).expanduser()
            ensure_app()
            return send("project.new", {"folder": str(folder), "name": name})
        if c == "list":
            ensure_app()
            return send("project.list")
        if c == "open":
            ensure_app()
            return send("project.open", {"folder": str(args.folder.expanduser())})
        if c == "info":
            ensure_app()
            return send("project.info")
        if c == "brief":
            ensure_app()
            return send("project.set_brief", {"fields": _kv(args.set)})
        if c == "tokens":
            ensure_app()
            return send("project.set_tokens", {"fields": _kv(args.set)})

    if g == "screen":
        ensure_app()
        if c == "add":
            return send("screen.add", {"path": str(args.path.expanduser()), "name": args.name})
        if c == "capture":
            return send("screen.capture", {"name": args.name})
        if c == "list":
            return send("screen.list")
        if c == "select":
            return send("screen.select", {"screen": args.screen})
        if c == "set":
            payload = {"screen": args.screen}
            if args.leads_to is not None:
                payload["leads_to"] = args.leads_to
            return send("screen.set", payload)
        if c == "reorder":
            return send("screen.reorder", {"screen": args.screen, "index": args.index})
        if c == "remove":
            return send("screen.remove", {"screen": args.screen})

    if g == "element":
        ensure_app()
        if c == "add":
            return send("element.add", {"screen": args.screen, "kind": args.kind, "box": _box(args.box)})
        if c == "list":
            return send("element.list", {"screen": args.screen})
        if c == "edit":
            fields = {}
            for key, value in _kv(args.set).items():
                fields[key] = [s.strip() for s in value.split(",") if s.strip()] if key == "states" else value
            return send("element.edit", {"screen": args.screen, "number": args.number, "fields": fields})
        if c == "resize":
            return send("element.resize", {"screen": args.screen, "number": args.number, "box": _box(args.box)})
        if c == "delete":
            return send("element.delete", {"screen": args.screen, "number": args.number})

    if g == "arrow" and c == "add":
        ensure_app()
        payload = {"screen": args.screen, "from": args.source, "label": args.label}
        if args.to is not None:
            payload["to"] = args.to
        else:
            payload["to_point"] = _point(args.to_point)
        return send("arrow.add", payload)

    if g == "label" and c == "add":
        ensure_app()
        return send("label.add", {"screen": args.screen, "text": args.text, "x": args.x, "y": args.y})

    if g == "export":
        ensure_app()
        return send("export")
    if g == "render":
        ensure_app()
        return send("render", {"screen": args.screen, "out": args.out})
    if g == "undo":
        ensure_app()
        return send("undo")
    if g == "redo":
        ensure_app()
        return send("redo")

    raise CliError(f"unsupported command: {g} {c}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run(args)
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    _emit(result, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
