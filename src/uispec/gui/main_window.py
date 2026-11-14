from __future__ import annotations

import datetime as dt
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QDragEnterEvent, QDropEvent, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPushButton, QSplitter, QStackedWidget, QTabWidget, QVBoxLayout, QWidget,
)

from .. import store
from ..commands import ASYNC, COMMANDS, CommandError, add_screen_from_file
from ..controller import Controller
from .canvas import TOOLS, Canvas
from .panels import ElementPanel, ProjectPanel, ScreenPanel

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
TOOL_KEYS = {"select": "V", "rect": "R", "ellipse": "E", "freehand": "F", "arrow": "A", "text": "T"}
TOOL_LABELS = {"select": "Select", "rect": "Rectangle", "ellipse": "Ellipse",
               "freehand": "Freehand", "arrow": "Arrow", "text": "Text note"}


class StartPage(QWidget):
    def __init__(self, window: "MainWindow"):
        super().__init__()
        self.window = window
        self.recent = QListWidget()
        self.recent.itemDoubleClicked.connect(self._open_item)
        new_btn = QPushButton("New project…")
        new_btn.clicked.connect(window.new_project)
        open_btn = QPushButton("Open folder…")
        open_btn.clicked.connect(window.open_folder)
        buttons = QHBoxLayout()
        buttons.addWidget(new_btn)
        buttons.addWidget(open_btn)
        layout = QVBoxLayout(self)
        title = QLabel("<h2>uispec</h2><p>Annotate screenshots and hand them to an agent.</p>")
        layout.addWidget(title)
        layout.addWidget(QLabel("Recent projects"))
        layout.addWidget(self.recent)
        layout.addLayout(buttons)

    def refresh(self) -> None:
        self.recent.clear()
        for path in store.list_recent():
            item = QListWidgetItem(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.recent.addItem(item)

    def _open_item(self, item: QListWidgetItem) -> None:
        self.window.open_path(Path(item.data(Qt.ItemDataRole.UserRole)))


class MainWindow(QMainWindow):
    def __init__(self, ctrl: Controller):
        super().__init__()
        self.ctrl = ctrl
        self.setAcceptDrops(True)
        self.setWindowTitle("uispec")
        self.resize(1400, 900)

        self.start_page = StartPage(self)
        self.canvas = Canvas(ctrl)
        self.screens = ScreenPanel(ctrl)
        self.elements = ElementPanel(ctrl)
        self.project = ProjectPanel(ctrl)

        right = QTabWidget()
        right.addTab(self.elements, "Element")
        right.addTab(self.project, "Project")

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self.screens)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.canvas)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 880, 360])

        self.stack = QStackedWidget()
        self.stack.addWidget(self.start_page)
        self.stack.addWidget(splitter)
        self.setCentralWidget(self.stack)

        self._build_actions()
        self.statusBar()

        self.canvas.selectionChanged.connect(self.elements.select_number)
        self.elements.selected.connect(self.canvas.select)
        self.screens.selected.connect(self._select_screen)
        self.canvas.message.connect(self.show_message)
        self.elements.message.connect(self.show_message)
        self.screens.message.connect(self.show_message)
        self.project.message.connect(self.show_message)

        ctrl.changed.connect(self.refresh)
        ctrl.opened.connect(self.refresh)
        self.refresh()

    # ---- actions ----------------------------------------------------------

    def _build_actions(self) -> None:
        bar = self.addToolBar("Main")
        bar.setMovable(False)

        def action(text, slot, shortcut=None):
            act = QAction(text, self)
            if shortcut:
                act.setShortcut(QKeySequence(shortcut))
            act.triggered.connect(slot)
            self.addAction(act)
            return act

        bar.addAction(action("New project", self.new_project))
        bar.addAction(action("Open", self.open_folder))
        bar.addSeparator()
        bar.addAction(action("Paste", self.paste_image, "Ctrl+V"))
        bar.addAction(action("Add image…", self.add_image_file))
        bar.addAction(action("Capture region", self.capture_region))
        bar.addSeparator()

        group = QActionGroup(self)
        group.setExclusive(True)
        for tool in TOOLS:
            act = QAction(f"{TOOL_LABELS[tool]} ({TOOL_KEYS[tool]})", self)
            act.setCheckable(True)
            act.setShortcut(QKeySequence(TOOL_KEYS[tool]))
            act.setChecked(tool == "select")
            act.triggered.connect(lambda _checked=False, t=tool: self.canvas.set_tool(t))
            group.addAction(act)
            self.addAction(act)
            bar.addAction(act)
        bar.addSeparator()
        self.undo_action = action("Undo", self.undo, "Ctrl+Z")
        self.redo_action = action("Redo", self.redo, "Ctrl+Shift+Z")
        bar.addAction(self.undo_action)
        bar.addAction(self.redo_action)
        bar.addSeparator()
        bar.addAction(action("Export", self.export))
        bar.addAction(action("Copy agent prompt", self.copy_prompt))

    # ---- refresh -----------------------------------------------------------

    def refresh(self) -> None:
        if not self.ctrl.is_open:
            self.start_page.refresh()
            self.stack.setCurrentWidget(self.start_page)
            self.setWindowTitle("uispec")
            return
        self.stack.setCurrentIndex(1)
        self.setWindowTitle(f"uispec — {self.ctrl.project.name}")
        self.screens.refresh()
        self.canvas.refresh()
        self.elements.refresh(self.canvas.selected)
        self.project.refresh()
        self.undo_action.setEnabled(self.ctrl.can_undo)
        self.redo_action.setEnabled(self.ctrl.can_redo)

    def show_message(self, text: str) -> None:
        self.statusBar().showMessage(text, 8000)

    # ---- project and screens ---------------------------------------------------

    def new_project(self) -> None:
        name, ok = QInputDialog.getText(self, "New project", "Project name:")
        if not ok or not name.strip():
            return
        folder = store.ui_specs_root() / name.strip()
        try:
            self.ctrl.create_project(folder, name.strip())
        except (FileExistsError, OSError) as exc:
            QMessageBox.warning(self, "New project", str(exc))

    def open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Open project folder", str(store.ui_specs_root()))
        if folder:
            self.open_path(Path(folder))

    def open_path(self, folder: Path) -> None:
        try:
            self.ctrl.open_project(folder)
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.warning(self, "Open project", f"Cannot open {folder}: {exc}")

    def _select_screen(self, screen_id: str) -> None:
        self.ctrl.current_screen_id = screen_id
        self.refresh()

    def _add_file(self, path: Path) -> None:
        try:
            add_screen_from_file(self.ctrl, path)
            self.show_message(f"Added {path.name}")
        except (CommandError, ValueError, OSError, RuntimeError) as exc:
            self.show_message(str(exc))

    def add_image_file(self) -> None:
        if not self.ctrl.is_open:
            return self.show_message("Open or create a project first")
        path, _ = QFileDialog.getOpenFileName(self, "Add screenshot", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)")
        if path:
            self._add_file(Path(path))

    def paste_image(self) -> None:
        if not self.ctrl.is_open:
            return self.show_message("Open or create a project first")
        image = QGuiApplication.clipboard().image()
        if image.isNull():
            return self.show_message("Clipboard has no image")
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        tmp = store.state_dir() / f"paste-{stamp}.png"
        image.save(str(tmp), "PNG")
        self._add_file(tmp)

    def capture_region(self) -> None:
        if not self.ctrl.is_open:
            return self.show_message("Open or create a project first")

        def done(result=None, error=None):
            self.show_message(error if error else f"Captured {result['name']}")

        ASYNC["screen.capture"](self.ctrl, {}, done)

    # ---- export and handoff ---------------------------------------------------

    def export(self) -> None:
        if not self.ctrl.is_open:
            return
        result = COMMANDS["export"](self.ctrl, {})
        self.show_message(f"Exported to {result['path']}")
        if result["warnings"]:
            QMessageBox.information(
                self, "Export warnings",
                "Exported, but some details are missing:\n\n" + "\n".join(result["warnings"]),
            )

    def copy_prompt(self) -> None:
        if not self.ctrl.is_open:
            return
        current = self.ctrl.folder / "current"
        text = (
            f"Implement or update the UI for {self.ctrl.project.name}. "
            f"Read {current}/spec.md first and follow it exactly. "
            f"The annotated screenshots are in {current}/screens/*/annotated.png. "
            "Use the ui-spec skill."
        )
        QGuiApplication.clipboard().setText(text)
        self.show_message("Prompt copied. Export first if no current spec exists.")

    def undo(self) -> None:
        self.ctrl.undo()

    def redo(self) -> None:
        self.ctrl.redo()

    # ---- drag and drop ----------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        if not self.ctrl.is_open:
            return self.show_message("Open or create a project first")
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in IMAGE_SUFFIXES:
                self._add_file(path)
        event.acceptProposedAction()
