import json
from pathlib import Path

import pytest
from PySide6.QtGui import QImage

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
    for name in ["app.status", "project.new", "screen.add", "screen.add_blank", "element.add",
                 "element.edit", "element.delete", "arrow.add", "label.add", "export", "render",
                 "undo", "redo"]:
        assert name in COMMANDS


def test_blank_canvas_screen_needs_no_screenshot(tmp_path, qapp):
    """A new UI can be drawn on empty canvases with textured elements and no screenshot."""
    ctrl = Controller()
    run(ctrl, "project.new", {"folder": str(tmp_path / "fresh"), "name": "Fresh"})

    info = run(ctrl, "screen.add_blank", {"name": "Home", "width": 1024, "height": 768})
    assert info["blank"] is True
    assert info["canvas_color"] == "#1c1b1f"
    image = tmp_path / "fresh" / info["image"]
    assert image.exists()
    canvas = QImage(str(image))
    assert (canvas.width(), canvas.height()) == (1024, 768)
    assert canvas.pixelColor(0, 0).name() == "#1c1b1f"

    assert run(ctrl, "screen.list")["screens"][0]["blank"] is True

    el = run(ctrl, "element.add", {"kind": "rect", "box": [40, 40, 300, 160]})
    run(ctrl, "element.edit", {"number": el["number"],
                               "fields": {"name": "Summary card", "purpose": "Shows today's totals",
                                          "states": ["default", "loading"]}})
    run(ctrl, "element.texture", {"number": el["number"], "pattern": "grain",
                                  "color": "#eeeeee", "opacity": 0.2})

    exported = run(ctrl, "export")
    assert not [w for w in exported["warnings"] if "element" in w]
    spec = (tmp_path / "fresh" / "current" / "spec.md").read_text()
    assert "blank canvas drawn from scratch" in spec
    assert "background #1c1b1f" in spec
    elements = json.loads((tmp_path / "fresh" / "current" / "screens" / "01-home" / "elements.json").read_text())
    assert elements["blank"] is True
    assert elements["background"] == "#1c1b1f"
    assert (tmp_path / "fresh" / "current" / "screens" / "01-home" / "annotated.png").exists()


def test_blank_canvas_color_is_set_and_validated(tmp_path, qapp):
    ctrl = Controller()
    run(ctrl, "project.new", {"folder": str(tmp_path / "ink"), "name": "Ink"})
    info = run(ctrl, "screen.add_blank", {"name": "Ink", "width": 200, "height": 200,
                                          "color": "#0b5fff"})
    assert info["canvas_color"] == "#0b5fff"
    assert QImage(str(tmp_path / "ink" / info["image"])).pixelColor(0, 0).name() == "#0b5fff"
    try:
        run(ctrl, "screen.add_blank", {"name": "Bad", "color": "not-a-color"})
    except CommandError as exc:
        assert "not a color" in str(exc)
    else:
        raise AssertionError("expected an error")


def test_blank_canvas_rejects_absurd_size(tmp_path, qapp):
    ctrl = Controller()
    run(ctrl, "project.new", {"folder": str(tmp_path / "fresh"), "name": "Fresh"})
    try:
        run(ctrl, "screen.add_blank", {"name": "Huge", "width": 99999, "height": 99999})
    except CommandError as exc:
        assert "canvas" in str(exc)
    else:
        raise AssertionError("expected an error")


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


def test_texture_export_writes_scaled_pattern(tmp_path, qapp, sample_png):
    ctrl = _setup_with_three(tmp_path, sample_png)
    run(ctrl, "element.texture", {"number": 1, "pattern": "dots", "color": "#ffcc00",
                                  "scale": 2, "opacity": 0.5})
    out = run(ctrl, "element.texture_export", {"number": 1, "out": str(tmp_path / "baked.png")})
    assert out["size"] == [128, 128]
    assert Path(out["path"]).exists()
    img = QImage(out["path"]).convertToFormat(QImage.Format.Format_ARGB32)
    assert (img.width(), img.height()) == (128, 128)
    # Dots peak at alpha 190; at half opacity the strongest pixel lands at 95.
    assert max(memoryview(img.bits())[3::4]) == 95


def test_texture_export_writes_tinted_image_at_natural_size(tmp_path, qapp, sample_png):
    ctrl = _setup_with_three(tmp_path, sample_png)
    run(ctrl, "element.texture", {"number": 2, "file": str(sample_png), "mode": "stretch",
                                  "tint": "#3366ff"})
    out = run(ctrl, "element.texture_export", {"number": 2, "out": str(tmp_path / "baked.png")})
    assert out["size"] == [400, 300]
    c = QImage(out["path"]).pixelColor(10, 10)
    assert (c.red(), c.green(), c.blue()) == (0x33, 0x66, 0xFF)


def test_texture_export_needs_a_texture_and_a_path(tmp_path, qapp, sample_png):
    ctrl = _setup_with_three(tmp_path, sample_png)
    with pytest.raises(CommandError):
        run(ctrl, "element.texture_export", {"number": 1, "out": str(tmp_path / "x.png")})
    run(ctrl, "element.texture", {"number": 1, "pattern": "noise"})
    with pytest.raises(CommandError):
        run(ctrl, "element.texture_export", {"number": 1})
