import json
import os

from uispec import exporter, store
from uispec.model import Project, Screen


def build_project(folder, sample_png):
    store.create_project(folder, "Shop")
    image = store.import_image(folder, sample_png, 1, "Login")
    screen = Screen(name="Login", image=image, leads_to="Home")
    e = screen.add_element("rect", [[20, 30], [120, 60]])
    e.name = "Submit"
    e.purpose = "Logs the user in"
    e.states = ["default", "disabled"]
    screen.add_element("ellipse", [[200, 200], [240, 240]])
    screen.arrows.append(__import__("uispec.model", fromlist=["Arrow"]).Arrow(from_number=1, to_number=2))
    project = Project(name="Shop", screens=[screen])
    project.brief["purpose"] = "Sell shoes"
    return project


def test_export_writes_bundle_and_current_pointer(tmp_path, qapp, sample_png):
    folder = tmp_path / "shop"
    project = build_project(folder, sample_png)
    store.save_project(folder, project)

    result = exporter.export(folder, project)

    export_dir = folder / "exports"
    assert list(export_dir.iterdir())
    current = folder / "current"
    assert current.is_symlink()
    assert os.path.realpath(current) == os.path.realpath(result["path"])

    spec = (current / "spec.md").read_text()
    assert "Sell shoes" in spec
    assert "### Element 1: Submit" in spec
    assert "Logs the user in" in spec
    assert "element 1 → element 2" in spec

    screen_dir = next((current / "screens").iterdir())
    assert (screen_dir / "original.png").exists()
    assert (screen_dir / "annotated.png").exists()
    data = json.loads((screen_dir / "elements.json").read_text())
    assert data["elements"][0]["name"] == "Submit"
    assert data["elements"][0]["number"] == 1


def test_validate_warns_on_missing_fields(tmp_path, qapp, sample_png):
    folder = tmp_path / "shop"
    project = build_project(folder, sample_png)
    project.screens[0].elements[1].name = ""
    warnings = exporter.validate(project)
    assert any("element 2: name is empty" in w for w in warnings)
    assert any("element 2: no states listed" in w for w in warnings)


def test_second_export_keeps_history_and_moves_current(tmp_path, qapp, sample_png):
    folder = tmp_path / "shop"
    project = build_project(folder, sample_png)
    store.save_project(folder, project)
    first = exporter.export(folder, project)
    second = exporter.export(folder, project)
    assert first["path"] != second["path"]
    assert os.path.realpath(folder / "current") == os.path.realpath(second["path"])
    assert os.path.isdir(first["path"])
