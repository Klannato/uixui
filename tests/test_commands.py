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


def _setup_with_three(tmp_path, sample_png):
    ctrl = Controller()
    run(ctrl, "project.new", {"folder": str(tmp_path / "shop"), "name": "Shop"})
    run(ctrl, "screen.add", {"path": str(sample_png), "name": "Login"})
    run(ctrl, "element.add", {"kind": "rect", "box": [10, 10, 40, 20]})
    run(ctrl, "element.add", {"kind": "rect", "box": [60, 50, 40, 20]})
    run(ctrl, "element.add", {"kind": "rect", "box": [120, 30, 30, 20]})
    return ctrl


def test_align_command_moves_elements_and_undoes(tmp_path, qapp, sample_png):
    ctrl = _setup_with_three(tmp_path, sample_png)
    out = run(ctrl, "element.align", {"numbers": [1, 2], "mode": "top"})
    assert set(out["moved"]) == {"1", "2"}
    tops = {min(p[1] for p in e["points"]) for e in run(ctrl, "element.list")["elements"][:2]}
    assert tops == {10}
    run(ctrl, "undo")
    assert min(p[1] for p in run(ctrl, "element.list")["elements"][1]["points"]) == 50


def test_align_command_rejects_single_element(tmp_path, qapp, sample_png):
    ctrl = _setup_with_three(tmp_path, sample_png)
    try:
        run(ctrl, "element.align", {"numbers": [1], "mode": "left"})
    except CommandError as exc:
        assert "at least two" in str(exc)
    else:
        raise AssertionError("expected an error")


def test_grid_command_validates_and_saves(tmp_path, qapp, sample_png):
    ctrl = _setup_with_three(tmp_path, sample_png)
    assert run(ctrl, "project.set_grid", {"size": 16, "snap": "off"})["grid"] == {"size": 16.0, "snap": False}
    assert ctrl.project.grid == {"size": 16.0, "snap": False}
    try:
        run(ctrl, "project.set_grid", {"size": 0})
    except CommandError:
        pass
    else:
        raise AssertionError("expected an error")


def test_texture_pattern_then_adjust_then_clear(tmp_path, qapp, sample_png):
    ctrl = _setup_with_three(tmp_path, sample_png)
    out = run(ctrl, "element.texture", {"number": 1, "pattern": "dots", "color": "#ffcc00", "opacity": 0.5})
    assert out["texture"] == {"kind": "pattern", "pattern": "dots", "color": "#ffcc00",
                              "scale": 1.0, "opacity": 0.5}
    run(ctrl, "element.texture", {"number": 1, "scale": 2})
    assert run(ctrl, "element.list")["elements"][0]["texture"]["scale"] == 2.0
    run(ctrl, "element.texture", {"number": 1, "clear": True})
    assert run(ctrl, "element.list")["elements"][0]["texture"] is None


def test_texture_image_is_copied_into_project(tmp_path, qapp, sample_png):
    ctrl = _setup_with_three(tmp_path, sample_png)
    out = run(ctrl, "element.texture", {"number": 2, "file": str(sample_png), "mode": "stretch"})
    rel = out["texture"]["file"]
    assert rel.startswith("textures/")
    assert (tmp_path / "shop" / rel).exists()
    assert out["texture"]["mode"] == "stretch"


def test_texture_validation(tmp_path, qapp, sample_png):
    ctrl = _setup_with_three(tmp_path, sample_png)
    cases = [
        {"number": 1, "pattern": "waves"},
        {"number": 1, "pattern": "dots", "opacity": 2},
        {"number": 1, "pattern": "dots", "scale": 0},
        {"number": 1, "file": str(tmp_path / "missing.png")},
        {"number": 1},
    ]
    for args in cases:
        try:
            run(ctrl, "element.texture", args)
        except CommandError:
            continue
        raise AssertionError(f"expected an error for {args}")


def test_screen_remove_deletes_screen_and_undoes(tmp_path, qapp, sample_png):
    ctrl = Controller()
    run(ctrl, "project.new", {"folder": str(tmp_path / "shop"), "name": "Shop"})
    run(ctrl, "screen.add", {"path": str(sample_png), "name": "Login"})
    run(ctrl, "screen.add", {"path": str(sample_png), "name": "Dashboard"})
    run(ctrl, "element.add", {"kind": "rect", "box": [1, 1, 10, 10]})
    assert ctrl.current_screen().name == "Dashboard"

    sids = [s["id"] for s in run(ctrl, "screen.list")["screens"]]
    run(ctrl, "screen.remove", {"screen": sids[1]})

    names = [s["name"] for s in run(ctrl, "screen.list")["screens"]]
    assert names == ["Login"]
    assert ctrl.current_screen().name == "Login"
    run(ctrl, "undo")
    assert [s["name"] for s in run(ctrl, "screen.list")["screens"]] == ["Login", "Dashboard"]


def test_element_edit_persists_across_screen_switch(tmp_path, qapp, sample_png):
    ctrl = Controller()
    run(ctrl, "project.new", {"folder": str(tmp_path / "shop"), "name": "Shop"})
    run(ctrl, "screen.add", {"path": str(sample_png), "name": "Login"})
    run(ctrl, "element.add", {"kind": "rect", "box": [1, 1, 10, 10]})
    run(ctrl, "element.edit", {"number": 1, "fields": {"name": "Submit", "purpose": "Log in"}})
    run(ctrl, "screen.add", {"path": str(sample_png), "name": "Dashboard"})
    run(ctrl, "screen.select", {"screen": "Login"})
    assert run(ctrl, "element.list")["elements"][0]["name"] == "Submit"
