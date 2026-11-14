from pathlib import Path

from uispec.commands import CommandError, COMMANDS, dispatch
from uispec.controller import Controller


def run(ctrl, name, args=None):
    out = {}
    dispatch(ctrl, name, args or {}, lambda result=None, error=None: out.update(result=result, error=error))
    if out["error"]:
        raise CommandError(out["error"])
    return out["result"]


def test_full_flow_through_commands(tmp_path, qapp, sample_png):
    ctrl = Controller()
    run(ctrl, "project.new", {"folder": str(tmp_path / "shop"), "name": "Shop"})
    run(ctrl, "screen.add", {"path": str(sample_png), "name": "Login"})
    el = run(ctrl, "element.add", {"kind": "rect", "box": [10, 10, 80, 30]})
    assert el["number"] == 1
    run(ctrl, "element.edit", {"number": 1, "fields": {"name": "Submit", "purpose": "Log in",
                                                      "states": ["default", "hover"]}})
    listing = run(ctrl, "element.list")
    assert listing["elements"][0]["name"] == "Submit"

    run(ctrl, "undo")
    assert run(ctrl, "element.list")["elements"][0]["name"] == ""
    run(ctrl, "redo")
    assert run(ctrl, "element.list")["elements"][0]["name"] == "Submit"

    rendered = run(ctrl, "render", {"out": str(tmp_path / "out.png")})
    assert Path(rendered["path"]).exists()

    exported = run(ctrl, "export")
    assert (tmp_path / "shop" / "current" / "spec.md").exists()
    assert not [w for w in exported["warnings"] if "element" in w]


def test_arrow_needs_existing_source(tmp_path, qapp, sample_png):
    ctrl = Controller()
    run(ctrl, "project.new", {"folder": str(tmp_path / "shop"), "name": "Shop"})
    run(ctrl, "screen.add", {"path": str(sample_png), "name": "Login"})
    try:
        run(ctrl, "arrow.add", {"from": 1, "to_point": [5, 5]})
    except CommandError as exc:
        assert "no element 1" in str(exc)
    else:
        raise AssertionError("expected an error")


def test_unknown_field_rejected(tmp_path, qapp, sample_png):
    ctrl = Controller()
    run(ctrl, "project.new", {"folder": str(tmp_path / "shop"), "name": "Shop"})
    run(ctrl, "screen.add", {"path": str(sample_png), "name": "Login"})
    run(ctrl, "element.add", {"kind": "rect", "box": [1, 1, 10, 10]})
    try:
        run(ctrl, "element.edit", {"number": 1, "fields": {"color": "red"}})
    except CommandError as exc:
        assert "unknown fields" in str(exc)
    else:
        raise AssertionError("expected an error")


def test_commands_registered():
    for name in ["app.status", "project.new", "screen.add", "element.add", "element.edit",
                 "element.delete", "arrow.add", "label.add", "export", "render", "undo", "redo"]:
        assert name in COMMANDS


def test_resize_command_updates_box_and_undoes(tmp_path, qapp, sample_png):
    ctrl = Controller()
    run(ctrl, "project.new", {"folder": str(tmp_path / "shop"), "name": "Shop"})
    run(ctrl, "screen.add", {"path": str(sample_png), "name": "Login"})
    run(ctrl, "element.add", {"kind": "rect", "box": [10, 10, 40, 20]})
    out = run(ctrl, "element.resize", {"number": 1, "box": [5, 5, 100, 60]})
    assert out["element"]["points"] == [[5, 5], [105, 65]]
    run(ctrl, "undo")
    assert run(ctrl, "element.list")["elements"][0]["points"] == [[10, 10], [50, 30]]


def test_resize_command_rejects_tiny_box(tmp_path, qapp, sample_png):
    ctrl = Controller()
    run(ctrl, "project.new", {"folder": str(tmp_path / "shop"), "name": "Shop"})
    run(ctrl, "screen.add", {"path": str(sample_png), "name": "Login"})
    run(ctrl, "element.add", {"kind": "rect", "box": [10, 10, 40, 20]})
    try:
        run(ctrl, "element.resize", {"number": 1, "box": [0, 0, 1, 1]})
    except CommandError as exc:
        assert "at least" in str(exc)
    else:
        raise AssertionError("expected an error")
    assert run(ctrl, "element.list")["elements"][0]["points"] == [[10, 10], [50, 30]]
