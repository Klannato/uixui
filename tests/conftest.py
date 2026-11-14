import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    return tmp_path


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication([])
    return app


@pytest.fixture
def sample_png(tmp_path):
    from PySide6.QtGui import QColor, QImage

    path = tmp_path / "source.png"
    img = QImage(400, 300, QImage.Format.Format_ARGB32)
    img.fill(QColor("#f5f5f5"))
    img.save(str(path), "PNG")
    return path


_exit = {"code": 0}


def pytest_sessionfinish(session, exitstatus):
    from uispec import textures

    textures.clear_caches()
    _exit["code"] = exitstatus


def pytest_unconfigure(config):
    # On CPython 3.10, PySide6 can abort while the interpreter shuts down, after every test has
    # passed (seen in CI as "Fatal Python error: none_dealloc"). Results are final by this point,
    # so exit directly with the test status instead of letting that teardown run.
    import os
    import sys

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_exit["code"])
