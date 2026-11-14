from PySide6.QtGui import QImage


def _alpha_bytes(path):
    img = QImage(str(path)).convertToFormat(QImage.Format.Format_ARGB32)
    return memoryview(img.bits())[3::4]


def test_install_and_uninstall_launcher(tmp_path, monkeypatch, qapp):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    from uispec import desktop

    result = desktop.install("/usr/bin/uispec-app")

    entry = (tmp_path / "data" / "applications" / "uixui.desktop").read_text()
    assert "Name=UI X UI" in entry
    assert "Exec=/usr/bin/uispec-app" in entry
    assert "Icon=uixui" in entry
    assert "StartupWMClass=uixui" in entry
    assert "Terminal=false" in entry

    assert (tmp_path / "data" / "icons" / "hicolor" / "scalable" / "apps" / "uixui.svg").exists()
    png = tmp_path / "data" / "icons" / "hicolor" / "256x256" / "apps" / "uixui.png"
    assert png.exists() and max(_alpha_bytes(png)) > 0
    assert len(result["icons"]) == len(desktop.ICON_SIZES) + 1

    desktop.uninstall()
    assert not (tmp_path / "data" / "applications" / "uixui.desktop").exists()
    assert not png.exists()


def test_exec_command_is_an_absolute_path():
    from uispec import desktop

    command = desktop.exec_command()
    assert command.endswith("uispec-app")
    assert "/" in command
