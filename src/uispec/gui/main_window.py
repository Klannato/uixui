from __future__ import annotations

import datetime as dt
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QAction, QActionGroup, QDragEnterEvent, QDropEvent, QGuiApplication, QKeySequence,
)
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSplitter, QStackedWidget,
    QTabWidget, QToolBar, QVBoxLayout, QWidget,
)

from .. import store
from ..commands import ASYNC, COMMANDS, CommandError, add_screen_from_file
from ..controller import Controller
from . import theme
from .canvas import TOOLS, Canvas
from .help import TIPS
from .panels import ElementPanel, ProjectPanel, ScreenPanel, card, section

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
TOOL_KEYS = {"select": "V", "rect": "R", "ellipse": "E", "freehand": "F", "arrow": "A", "text": "T"}
TOOL_LABELS = {"select": "Select", "rect": "Rectangle", "ellipse": "Ellipse",
               "freehand": "Freehand", "arrow": "Arrow", "text": "Text note"}
TOOL_ICONS = {"select": "mdi6.cursor-default-outline", "rect": "mdi6.rectangle-outline",
              "ellipse": "mdi6.ellipse-outline", "freehand": "mdi6.gesture",
              "arrow": "mdi6.arrow-top-right", "text": "mdi6.format-text"}


class StartPage(QWidget):
    def __init__(self, window: "MainWindow"):
        super().__init__()
        self.window = window
        self.recent = QListWidget()
        self.recent.setToolTip("Double-click a project to open it.")
        self.recent.itemDoubleClicked.connect(self._open_item)
        new_btn = QPushButton("New project")
        new_btn.setProperty("variant", "filled")
        new_btn.setToolTip(TIPS["new_project"])
        new_btn.clicked.connect(window.new_project)
        open_btn = QPushButton("Open folder")
        open_btn.setToolTip(TIPS["open_project"])
        open_btn.clicked.connect(window.open_folder)
        buttons = QHBoxLayout()
        buttons.addWidget(new_btn)
        buttons.addWidget(open_btn)
        buttons.addStretch(1)

        title = QLabel("uispec")
        title.setObjectName("sectionTitle")
        title.setStyleSheet("font-size: 22pt; font-weight: 600;")
        tagline = QLabel("Annotate screenshots and hand the spec to your coding agent.")
        tagline.setObjectName("hint")

        body = QVBoxLayout()
        body.setSpacing(12)
        body.addWidget(title)
        body.addWidget(tagline)
        body.addSpacing(12)
        body.addWidget(section("Recent projects", "Projects you have opened lately."))
        body.addWidget(self.recent, 1)
        body.addLayout(buttons)

        wrapper = QWidget()
        wrapper.setObjectName("card")
        wrapper.setLayout(body)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(120, 60, 120, 60)
        outer.addWidget(wrapper)

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
        self._themed: list[tuple[QAction, str, str]] = []

        self.start_page = StartPage(self)
        self.canvas = Canvas(ctrl)
        self.screens = ScreenPanel(ctrl)
        self.elements = ElementPanel(ctrl)
        self.project = ProjectPanel(ctrl)

        canvas_frame = QWidget()
        canvas_frame.setObjectName("canvasFrame")
        frame_layout = QVBoxLayout(canvas_frame)
        frame_layout.setContentsMargins(12, 12, 12, 12)
        frame_layout.addWidget(self.canvas)

        left = card(self.screens)
        right_tabs = QTabWidget()
        right_tabs.setDocumentMode(True)
        right_tabs.addTab(self._scroll_page(self.elements), "Element")
        right_tabs.addTab(self._scroll_page(self.project), "Project")
        right_tabs.setToolTip("Element: describe the selected element.\nProject: brief and design tokens.")
        right = card(right_tabs)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(left)
        splitter.addWidget(canvas_frame)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 760, 460])

        workspace = QWidget()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(12, 12, 12, 12)
        workspace_layout.addWidget(splitter)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.start_page)
        self.stack.addWidget(workspace)
        self.setCentralWidget(self.stack)

        self._build_actions()
        self.statusBar().showMessage("Ready. Hover any control for a short explanation.")

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

    @staticmethod
    def _scroll_page(widget: QWidget) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(widget)
        area = QScrollArea()
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setWidget(page)
        area.viewport().setAutoFillBackground(False)
        page.setAutoFillBackground(False)
        return area

    # ---- actions and toolbar ------------------------------------------------

    def _action(self, text: str, icon: str, tip: str, slot, shortcut: str | None = None,
                color_key: str = "on_variant") -> QAction:
        act = QAction(text, self)
        act.setToolTip(tip)
        act.setStatusTip(tip.replace("<br>", " ").replace("<b>", "").replace("</b>", ""))
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(slot)
        act.setIcon(theme.icon(icon, color_key))
        self._themed.append((act, icon, color_key))
        self.addAction(act)
        return act

    def _build_actions(self) -> None:
        top = QToolBar("Project")
        top.setObjectName("topBar")
        top.setMovable(False)
        top.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(top)

        top.addAction(self._action("New project", "mdi6.plus", TIPS["new_project"], self.new_project))
        top.addAction(self._action("Open", "mdi6.folder-open-outline", TIPS["open_project"], self.open_folder))
        top.addSeparator()
        top.addAction(self._action("Paste", "mdi6.content-paste", TIPS["paste"], self.paste_image, "Ctrl+V"))
        top.addAction(self._action("Add image", "mdi6.image-plus", TIPS["add_image"], self.add_image_file))
        top.addAction(self._action("Capture", "mdi6.monitor-screenshot", TIPS["capture"], self.capture_region))

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top.addWidget(spacer)

        top.addAction(self._action("Copy prompt", "mdi6.robot-outline", TIPS["copy_prompt"], self.copy_prompt))
        export_action = self._action("Export", "mdi6.export-variant", TIPS["export"], self.export,
                                     color_key="on_primary")
        top.addAction(export_action)
        top.widgetForAction(export_action).setObjectName("primaryAction")
        top.addSeparator()
        top.addAction(self._action("Theme", "mdi6.theme-light-dark", TIPS["theme"], self.toggle_theme))

        tools = QToolBar("Tools")
        tools.setObjectName("toolBar")
        tools.setMovable(False)
        tools.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBarBreak()
        self.addToolBar(tools)

        group = QActionGroup(self)
        group.setExclusive(True)
        for tool in TOOLS:
            act = QAction(f"{TOOL_LABELS[tool]} ({TOOL_KEYS[tool]})", self)
            act.setCheckable(True)
            act.setShortcut(QKeySequence(TOOL_KEYS[tool]))
            act.setToolTip(TIPS[f"tool_{tool}"])
            act.setStatusTip(f"{TOOL_LABELS[tool]} tool ({TOOL_KEYS[tool]})")
            act.setChecked(tool == "select")
            act.setIcon(theme.icon(TOOL_ICONS[tool]))
            self._themed.append((act, TOOL_ICONS[tool], "on_variant"))
            act.triggered.connect(lambda _checked=False, t=tool: self.canvas.set_tool(t))
            group.addAction(act)
            self.addAction(act)
            tools.addAction(act)
        tools.addSeparator()

        self.undo_action = self._action("Undo", "mdi6.undo", TIPS["undo"], self.undo, "Ctrl+Z")
        self.redo_action = self._action("Redo", "mdi6.redo", TIPS["redo"], self.redo, "Ctrl+Shift+Z")
        tools.addAction(self.undo_action)
        tools.addAction(self.redo_action)

    def toggle_theme(self) -> None:
        theme.toggle()
        QApplication.instance().setStyleSheet(theme.stylesheet())
        self._restyle()
        self.show_message(f"{theme.mode().capitalize()} theme")

    def _restyle(self) -> None:
        for act, icon, color_key in self._themed:
            act.setIcon(theme.icon(icon, color_key))
        self.canvas.update()

    # ---- refresh -----------------------------------------------------------

    def refresh(self) -> None:
        if not self.ctrl.is_open:
            self.start_page.refresh()
            self.stack.setCurrentWidget(self.start_page)
            self.setWindowTitle("uispec")
            return
        self.stack.setCurrentIndex(1)
        self.setWindowTitle(f"{self.ctrl.project.name} — uispec")
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
        path, _ = QFileDialog.getOpenFileName(self, "Add screenshot", "",
                                              "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)")
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
