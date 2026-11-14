from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Signal

from . import store
from .model import Project, Screen


class Controller(QObject):
    """Owns the open project. Every change goes through mutate(), which records undo history and autosaves."""

    changed = Signal()
    opened = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.folder: Path | None = None
        self.project: Project | None = None
        self.current_screen_id: str | None = None
        self._undo: list[dict] = []
        self._redo: list[dict] = []

    @property
    def is_open(self) -> bool:
        return self.project is not None

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def require_project(self) -> Project:
        if self.project is None:
            raise RuntimeError("no project open; run `uispec project new` or open one in the app")
        return self.project

    def current_screen(self) -> Screen | None:
        if self.project is None or self.current_screen_id is None:
            return None
        try:
            return self.project.screen(self.current_screen_id)
        except KeyError:
            return None

    def open_project(self, folder: Path) -> None:
        self.project = store.load_project(folder)
        self.folder = folder
        self.current_screen_id = self.project.screens[0].id if self.project.screens else None
        self._undo.clear()
        self._redo.clear()
        store.add_recent(folder)
        self.opened.emit()

    def create_project(self, folder: Path, name: str) -> None:
        store.create_project(folder, name)
        self.open_project(folder)

    def mutate(self, fn: Callable[[Project], object]):
        project = self.require_project()
        snapshot = project.to_dict()
        try:
            result = fn(project)
        except Exception:
            self.project = Project.from_dict(snapshot)
            raise
        self._undo.append(snapshot)
        self._redo.clear()
        self._after_change()
        return result

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(self.project.to_dict())
        self.project = Project.from_dict(self._undo.pop())
        self._after_change()
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(self.project.to_dict())
        self.project = Project.from_dict(self._redo.pop())
        self._after_change()
        return True

    def _after_change(self) -> None:
        if self.current_screen_id is not None and self.current_screen() is None:
            self.current_screen_id = self.project.screens[0].id if self.project.screens else None
        store.save_project(self.folder, self.project)
        self.changed.emit()
