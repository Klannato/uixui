from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from ..api import read_api_file, start_server, stop_server
from ..controller import Controller
from .. import APP_ID, APP_NAME, textures
from ..desktop import ICON_SVG
from . import theme
from .main_window import MainWindow


def _already_running() -> int | None:
    info = read_api_file()
    if info is None:
        return None
    try:
        os.kill(int(info["pid"]), 0)
    except (OSError, KeyError, ValueError):
        return None
    return int(info["pid"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"{APP_ID}-app", description=f"{APP_NAME} annotation app")
    parser.add_argument("--project", type=Path, help="project folder to open")
    args = parser.parse_args(argv)

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName(APP_NAME)
    app.setDesktopFileName(APP_ID)
    app.setWindowIcon(QIcon(str(ICON_SVG)))
    theme.load_mode()
    app.setStyleSheet(theme.stylesheet())

    pid = _already_running()
    if pid is not None:
        QMessageBox.information(None, APP_NAME, f"{APP_NAME} is already running (pid {pid}).")
        return 0

    ctrl = Controller()
    window = MainWindow(ctrl)
    server, _bridge = start_server(ctrl)
    app.aboutToQuit.connect(lambda: stop_server(server))
    app.aboutToQuit.connect(textures.clear_caches)
    ctrl.quit_requested.connect(app.quit)

    if args.project is not None:
        window.open_path(args.project.expanduser())
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
