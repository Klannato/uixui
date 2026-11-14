from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit,
    QPushButton, QSlider, QSpinBox, QToolButton, QVBoxLayout, QWidget,
)

from ..commands import COMMANDS, CommandError
from ..controller import Controller
from ..model import BRIEF_FIELDS, PATTERNS, STATES, TOKEN_FIELDS
from . import theme
from .help import HINTS, TIPS

ID_ROLE = Qt.ItemDataRole.UserRole


def run(ctrl: Controller, name: str, args: dict):
    return COMMANDS[name](ctrl, args)


def section(text: str, hint: str | None = None) -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    title = QLabel(text)
    title.setObjectName("sectionTitle")
    layout.addWidget(title)
    if hint:
        note = QLabel(hint)
        note.setObjectName("hint")
        note.setWordWrap(True)
        layout.addWidget(note)
    return box


def card(child: QWidget) -> QWidget:
    frame = QWidget()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.addWidget(child)
    return frame


class ScreenPanel(QWidget):
    """Flow-ordered screen list with a 'leads to' note for the selected screen."""

    selected = Signal(str)
    message = Signal(str)

    def __init__(self, ctrl: Controller, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.list = QListWidget()
        self.list.setToolTip(TIPS["screens_list"])
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.model().rowsMoved.connect(self._on_reordered)
        self.list.currentItemChanged.connect(self._on_current)
        self.leads_to = QLineEdit()
        self.leads_to.setPlaceholderText("Leads to…")
        self.leads_to.setToolTip(TIPS["leads_to"])
        self.leads_to.editingFinished.connect(self._save_leads_to)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        self.list.installEventFilter(self)
        self.delete_btn = QPushButton("Delete screen")
        self.delete_btn.setToolTip(TIPS["delete_screen"])
        self.delete_btn.clicked.connect(self.delete_current)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section("Screens", "Drag to set the flow order."))
        layout.addWidget(self.list, 1)
        layout.addWidget(self.leads_to)
        layout.addWidget(self.delete_btn)

    def refresh(self) -> None:
        project = self.ctrl.project
        self.list.blockSignals(True)
        self.list.clear()
        if project is not None:
            for i, s in enumerate(project.screens, 1):
                item = QListWidgetItem(f"{i}. {s.name}")
                item.setData(ID_ROLE, s.id)
                self.list.addItem(item)
                if s.id == self.ctrl.current_screen_id:
                    self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        screen = self.ctrl.current_screen()
        self.leads_to.setText(screen.leads_to if screen else "")
        self.leads_to.setEnabled(screen is not None)
        self.delete_btn.setEnabled(screen is not None)

    def eventFilter(self, obj, event):
        if obj is self.list and event.type() == QEvent.Type.KeyPress and event.key() in (
                Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_current()
            return True
        return super().eventFilter(obj, event)

    def _context_menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if item is None:
            return
        self.list.setCurrentItem(item)
        menu = QMenu(self)
        action = menu.addAction(theme.icon("mdi6.delete-outline"), "Delete screen")
        action.triggered.connect(self.delete_current)
        menu.exec(self.list.mapToGlobal(pos))

    def delete_current(self, confirm: bool = True) -> None:
        sid = self._current_screen_id()
        project = self.ctrl.project
        if sid is None or project is None:
            return
        screen = next((s for s in project.screens if s.id == sid), None)
        if screen is None:
            return
        count = len(screen.elements)
        detail = f" and its {count} element{'s' if count != 1 else ''}" if count else ""
        if confirm:
            answer = QMessageBox.question(
                self, "Delete screen",
                f'Delete screen "{screen.name}"{detail}?\n\nYou can undo this with Ctrl+Z.',
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            run(self.ctrl, "screen.remove", {"screen": sid})
            self.message.emit(f"Deleted screen {screen.name}")
        except CommandError as exc:
            self.message.emit(str(exc))

    def _current_screen_id(self) -> str | None:
        item = self.list.currentItem()
        return item.data(ID_ROLE) if item else None

    def _on_current(self, item, _previous):
        if item is None:
            return
        sid = item.data(ID_ROLE)
        if sid != self.ctrl.current_screen_id:
            self.selected.emit(sid)

    def _on_reordered(self, *_):
        ids = [self.list.item(i).data(ID_ROLE) for i in range(self.list.count())]
        order = {sid: i for i, sid in enumerate(ids, 1)}
        self.ctrl.mutate(lambda project: project.screens.sort(key=lambda s: order[s.id]))

    def _save_leads_to(self):
        screen = self.ctrl.current_screen()
        if screen is None or self.leads_to.text() == screen.leads_to:
            return
        try:
            run(self.ctrl, "screen.set", {"screen": screen.id, "leads_to": self.leads_to.text()})
        except CommandError as exc:
            self.message.emit(str(exc))


class ElementPanel(QWidget):
    message = Signal(str)
    selected = Signal(list)

    def __init__(self, ctrl: Controller, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctrl = ctrl
        self._number: int | None = None
        self._texture_file: str | None = None
        self._dirty = False
        self._loading = False
        self._flushing = False
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setToolTip(TIPS["element_list"])
        self.list.itemSelectionChanged.connect(self._on_user_selection)
        self.empty_hint = QLabel(HINTS["elements"])
        self.empty_hint.setObjectName("hint")
        self.empty_hint.setWordWrap(True)

        self.name = QLineEdit()
        self.name.setToolTip(TIPS["name"])
        self.purpose = QLineEdit()
        self.purpose.setToolTip(TIPS["purpose"])
        self.behavior = QPlainTextEdit()
        self.behavior.setToolTip(TIPS["behavior"])
        self.state_boxes = {s: QCheckBox(s.capitalize()) for s in STATES}
        for state, box in self.state_boxes.items():
            box.setToolTip(TIPS[f"state_{state}"])
        self.custom_states = QLineEdit()
        self.custom_states.setPlaceholderText("Custom states, comma-separated")
        self.custom_states.setToolTip(TIPS["custom_states"])
        self.content = QPlainTextEdit()
        self.content.setToolTip(TIPS["content"])
        self.constraints = QPlainTextEdit()
        self.constraints.setToolTip(TIPS["constraints"])
        self.notes = QPlainTextEdit()
        self.notes.setToolTip(TIPS["notes"])
        self.reference = QLineEdit()
        self.reference.setPlaceholderText("Link or file path")
        self.reference.setToolTip(TIPS["reference"])

        states_grid = QGridLayout()
        states_grid.setHorizontalSpacing(12)
        for i, box in enumerate(self.state_boxes.values()):
            states_grid.addWidget(box, i // 3, i % 3)
        states_widget = QWidget()
        states_layout = QVBoxLayout(states_widget)
        states_layout.setContentsMargins(0, 0, 0, 0)
        states_layout.addLayout(states_grid)
        states_layout.addWidget(self.custom_states)

        self.form = QFormLayout()
        self.form.setVerticalSpacing(10)
        self.form.addRow("Name *", self.name)
        self.form.addRow("Purpose *", self.purpose)
        self.form.addRow("Behavior", self.behavior)
        self.form.addRow("States", states_widget)
        self.form.addRow("Content", self.content)
        self.form.addRow("Constraints", self.constraints)
        self.form.addRow("Notes", self.notes)
        self.form.addRow("Reference", self.reference)
        self.form_hint = QLabel(HINTS["element_form"])
        self.form_hint.setObjectName("hint")
        self.form_hint.setWordWrap(True)

        self.save_btn = QPushButton("Save element")
        self.save_btn.setProperty("variant", "filled")
        self.save_btn.setToolTip(TIPS["save_element"] + "<br><br>" + TIPS["autosave"])
        self.save_btn.clicked.connect(self.save)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setToolTip(TIPS["delete_element"])
        self.delete_btn.clicked.connect(self.delete)
        buttons = QHBoxLayout()
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.delete_btn)

        self.align_bar = self._build_align_bar()
        self.texture_box = self._build_texture_section()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section("Elements", HINTS["multi_select"]))
        layout.addWidget(self.list)
        layout.addWidget(self.empty_hint)
        layout.addWidget(self.align_bar)
        layout.addSpacing(8)
        layout.addWidget(self.form_hint)
        layout.addLayout(self.form)
        layout.addLayout(buttons)
        layout.addSpacing(8)
        layout.addWidget(self.texture_box)
        layout.addStretch(1)
        for editor in (self.name, self.purpose, self.reference, self.custom_states,
                       self.behavior, self.content, self.constraints, self.notes):
            editor.textChanged.connect(self._mark_dirty)
        for state_box in self.state_boxes.values():
            state_box.toggled.connect(self._mark_dirty)
        self._set_form_enabled(False)
        self._form_widgets = (self.name, self.purpose, self.behavior, self.custom_states,
                              self.content, self.constraints, self.notes, self.reference)
        for editor in self._form_widgets:
            editor.installEventFilter(self)
            viewport = getattr(editor, "viewport", None)
            if viewport is not None:
                viewport().installEventFilter(self)

    def _build_align_bar(self) -> QWidget:
        bar = QWidget()
        grid = QGridLayout(bar)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(4)
        self.align_buttons = {}
        items = [
            ("left", "mdi6.align-horizontal-left", 0, 0), ("hcenter", "mdi6.align-horizontal-center", 0, 1),
            ("right", "mdi6.align-horizontal-right", 0, 2), ("dist_h", "mdi6.distribute-horizontal-center", 0, 3),
            ("top", "mdi6.align-vertical-top", 1, 0), ("vcenter", "mdi6.align-vertical-center", 1, 1),
            ("bottom", "mdi6.align-vertical-bottom", 1, 2), ("dist_v", "mdi6.distribute-vertical-center", 1, 3),
        ]
        for mode, icon, row, col in items:
            btn = QToolButton()
            btn.setIconSize(QSize(20, 20))
            btn.setIcon(theme.icon(icon))
            btn.setToolTip(TIPS[f"align_{mode}"])
            btn.setEnabled(False)
            btn.clicked.connect(lambda _c=False, m=mode: self.align(m))
            self.align_buttons[mode] = (btn, icon)
            grid.addWidget(btn, row, col)
        return bar

    def _build_texture_section(self) -> QWidget:
        box = QWidget()
        box.setObjectName("card")
        layout = QFormLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setVerticalSpacing(8)
        self.tex_source = QComboBox()
        self.tex_source.addItems(["None", "Image", "Pattern"])
        self.tex_source.setToolTip(TIPS["texture_source"])
        self.tex_source.currentIndexChanged.connect(self._texture_source_changed)
        self.tex_pick = QPushButton("Choose image…")
        self.tex_pick.setToolTip(TIPS["texture_pick"])
        self.tex_pick.clicked.connect(self._pick_texture_file)
        self.tex_file_label = QLabel("")
        self.tex_file_label.setObjectName("hint")
        self.tex_pattern = QComboBox()
        self.tex_pattern.addItems(list(PATTERNS))
        self.tex_pattern.setToolTip(TIPS["texture_pattern"])
        self.tex_color = QLineEdit("#808080")
        self.tex_color.setToolTip(TIPS["texture_color"])
        self.tex_mode = QComboBox()
        self.tex_mode.addItems(["tile", "stretch"])
        self.tex_mode.setToolTip(TIPS["texture_mode"])
        self.tex_scale = QDoubleSpinBox()
        self.tex_scale.setRange(0.05, 20)
        self.tex_scale.setSingleStep(0.25)
        self.tex_scale.setValue(1.0)
        self.tex_scale.setToolTip(TIPS["texture_scale"])
        self.tex_opacity = QSlider(Qt.Orientation.Horizontal)
        self.tex_opacity.setRange(0, 100)
        self.tex_opacity.setValue(100)
        self.tex_opacity.setToolTip(TIPS["texture_opacity"])
        self.tex_tint = QLineEdit()
        self.tex_tint.setPlaceholderText("Optional, e.g. #3366ff")
        self.tex_tint.setToolTip(TIPS["texture_tint"])
        self.tex_apply = QPushButton("Apply texture")
        self.tex_apply.setProperty("variant", "filled")
        self.tex_apply.setToolTip(TIPS["texture_apply"])
        self.tex_apply.clicked.connect(self.apply_texture)
        self.tex_clear = QPushButton("Remove")
        self.tex_clear.setToolTip(TIPS["texture_clear"])
        self.tex_clear.clicked.connect(self.clear_texture)
        buttons = QHBoxLayout()
        buttons.addWidget(self.tex_apply)
        buttons.addWidget(self.tex_clear)

        title = QLabel("Texture")
        title.setObjectName("sectionTitle")
        self.tex_hint = QLabel(HINTS["texture"])
        self.tex_hint.setObjectName("hint")
        self.tex_hint.setWordWrap(True)
        layout.addRow(title)
        layout.addRow(self.tex_hint)
        layout.addRow("Source", self.tex_source)
        layout.addRow("", self.tex_pick)
        layout.addRow("", self.tex_file_label)
        layout.addRow("Pattern", self.tex_pattern)
        layout.addRow("Color", self.tex_color)
        layout.addRow("Image fit", self.tex_mode)
        layout.addRow("Scale", self.tex_scale)
        layout.addRow("Opacity", self.tex_opacity)
        layout.addRow("Tint", self.tex_tint)
        layout.addRow(buttons)
        self._texture_source_changed()
        return box

    def _texture_source_changed(self) -> None:
        source = self.tex_source.currentText()
        self.tex_pick.setVisible(source == "Image")
        self.tex_file_label.setVisible(source == "Image")
        self.tex_pattern.setVisible(source == "Pattern")
        self.tex_color.setVisible(source == "Pattern")
        self.tex_mode.setVisible(source == "Image")
        self.tex_tint.setEnabled(source != "None")

    def _pick_texture_file(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self, "Choose texture image", "",
                                              "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)")
        if path:
            self._texture_file = path
            self.tex_file_label.setText(Path(path).name)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.FocusOut:
            widget = QApplication.focusWidget()
            if widget is None or not (widget is self or self.isAncestorOf(widget)):
                self.flush()
        return super().eventFilter(obj, event)

    def _set_form_enabled(self, enabled: bool) -> None:
        for w in (self.name, self.purpose, self.behavior, self.custom_states, self.content,
                  self.constraints, self.notes, self.reference, self.save_btn, self.delete_btn,
                  *self.state_boxes.values()):
            w.setEnabled(enabled)
        self.form_hint.setVisible(not enabled)
        self.texture_box.setEnabled(enabled)

    def _selected_numbers(self) -> list[int]:
        screen = self.ctrl.current_screen()
        if screen is None:
            return []
        rows = sorted({self.list.row(i) for i in self.list.selectedItems()})
        return [screen.elements[r].number for r in rows if r < len(screen.elements)]

    def refresh(self, numbers=()) -> None:
        screen = self.ctrl.current_screen()
        self.list.blockSignals(True)
        self.list.clear()
        if screen is not None:
            for e in screen.elements:
                self.list.addItem(f"{e.number}. {e.name or '(unnamed)'}")
        self.list.blockSignals(False)
        self.empty_hint.setVisible(screen is None or not screen.elements)
        self.select_numbers(list(numbers))

    def select_numbers(self, numbers: list[int]) -> None:
        screen = self.ctrl.current_screen()
        rows = []
        if screen is not None:
            rows = [i for i, e in enumerate(screen.elements) if e.number in numbers]
        self.list.blockSignals(True)
        self.list.clearSelection()
        for row in rows:
            self.list.item(row).setSelected(True)
        if rows:
            self.list.setCurrentRow(rows[-1])
        self.list.blockSignals(False)
        self._update_for_selection(numbers)

    def _on_user_selection(self) -> None:
        numbers = self._selected_numbers()
        self._update_for_selection(numbers)
        self.selected.emit(numbers)

    def _mark_dirty(self, *_) -> None:
        if not self._loading and self._number is not None:
            self._dirty = True

    def flush(self) -> bool:
        """Save any unsaved edits. Called when focus or selection leaves this panel."""
        if self._flushing or not self._dirty or self._number is None:
            return False
        self._flushing = True
        try:
            self.save(quiet=True)
        finally:
            self._flushing = False
        return True

    def _update_for_selection(self, numbers: list[int]) -> None:
        self.flush()
        screen = self.ctrl.current_screen()
        count = len(numbers)
        for mode, (btn, _icon) in self.align_buttons.items():
            needed = 3 if mode.startswith("dist_") else 2
            btn.setEnabled(count >= needed)
        if count == 1 and screen is not None:
            element = screen.element(numbers[0])
            self._load(element)
        else:
            self._number = None
            self._clear_form()
            self._set_form_enabled(False)
            self.form_hint.setText(HINTS["element_form"] if count == 0 else f"{count} elements selected.")

    def _load(self, e) -> None:
        self._loading = True
        try:
            self._load_fields(e)
        finally:
            self._loading = False
            self._dirty = False

    def _load_fields(self, e) -> None:
        self._number = e.number
        self.form_hint.setText(HINTS["element_form"])
        self.name.setText(e.name)
        self.purpose.setText(e.purpose)
        self.behavior.setPlainText(e.behavior)
        for state, box in self.state_boxes.items():
            box.setChecked(state in e.states)
        self.custom_states.setText(", ".join(s for s in e.states if s not in STATES))
        self.content.setPlainText(e.content)
        self.constraints.setPlainText(e.constraints)
        self.notes.setPlainText(e.notes)
        self.reference.setText(e.reference)
        self._load_texture(e.texture)
        self._set_form_enabled(True)

    def _load_texture(self, texture) -> None:
        self._texture_file = None
        self.tex_file_label.setText("")
        if not texture:
            self.tex_source.setCurrentIndex(0)
            self.tex_scale.setValue(1.0)
            self.tex_opacity.setValue(100)
            self.tex_tint.setText("")
        elif texture["kind"] == "pattern":
            self.tex_source.setCurrentIndex(2)
            self.tex_pattern.setCurrentText(texture["pattern"])
            self.tex_color.setText(texture.get("color") or "#808080")
        else:
            self.tex_source.setCurrentIndex(1)
            self.tex_mode.setCurrentText(texture.get("mode", "tile"))
            self.tex_file_label.setText(Path(texture["file"]).name)
        if texture:
            self.tex_scale.setValue(float(texture.get("scale", 1.0)))
            self.tex_opacity.setValue(round(float(texture.get("opacity", 1.0)) * 100))
            self.tex_tint.setText(texture.get("tint") or "")

    def _clear_form(self) -> None:
        self._loading = True
        try:
            for w in (self.name, self.purpose, self.custom_states, self.reference):
                w.clear()
            for w in (self.behavior, self.content, self.constraints, self.notes):
                w.clear()
            for box in self.state_boxes.values():
                box.setChecked(False)
            self._load_texture(None)
        finally:
            self._loading = False
            self._dirty = False

    def _states(self) -> list[str]:
        states = [s for s, box in self.state_boxes.items() if box.isChecked()]
        extra = [s.strip() for s in self.custom_states.text().split(",") if s.strip()]
        return states + extra

    def save(self, quiet: bool = False) -> None:
        if self._number is None:
            return
        screen = self.ctrl.current_screen()
        fields = {
            "name": self.name.text(),
            "purpose": self.purpose.text(),
            "behavior": self.behavior.toPlainText(),
            "states": self._states(),
            "content": self.content.toPlainText(),
            "constraints": self.constraints.toPlainText(),
            "notes": self.notes.toPlainText(),
            "reference": self.reference.text(),
        }
        try:
            run(self.ctrl, "element.edit", {"screen": screen.id, "number": self._number, "fields": fields})
            self._dirty = False
            if not quiet:
                self.message.emit(f"Saved element {self._number}")
        except CommandError as exc:
            self.message.emit(str(exc))

    def delete(self) -> None:
        numbers = self._selected_numbers()
        if not numbers:
            return
        screen = self.ctrl.current_screen()
        try:
            for number in sorted(numbers, reverse=True):
                run(self.ctrl, "element.delete", {"screen": screen.id, "number": number})
        except CommandError as exc:
            self.message.emit(str(exc))

    def align(self, mode: str) -> None:
        screen = self.ctrl.current_screen()
        numbers = self._selected_numbers()
        if screen is None or not numbers:
            return
        try:
            run(self.ctrl, "element.align", {"screen": screen.id, "numbers": numbers, "mode": mode})
        except CommandError as exc:
            self.message.emit(str(exc))

    def apply_texture(self) -> None:
        if self._number is None:
            return
        screen = self.ctrl.current_screen()
        source = self.tex_source.currentText()
        args = {
            "screen": screen.id,
            "number": self._number,
            "scale": self.tex_scale.value(),
            "opacity": self.tex_opacity.value() / 100,
            "tint": self.tex_tint.text().strip(),
        }
        if source == "None":
            args["clear"] = True
        elif source == "Image":
            if self._texture_file:
                args["file"] = self._texture_file
            elif self._current_texture_is_image():
                args["mode"] = self.tex_mode.currentText()
            else:
                self.message.emit("Choose an image file first")
                return
            args["mode"] = self.tex_mode.currentText()
        else:
            args["pattern"] = self.tex_pattern.currentText()
            args["color"] = self.tex_color.text().strip() or "#808080"
        try:
            run(self.ctrl, "element.texture", args)
            self._texture_file = None
            self.message.emit("Texture applied" if source != "None" else "Texture removed")
        except CommandError as exc:
            self.message.emit(str(exc))

    def _current_texture_is_image(self) -> bool:
        screen = self.ctrl.current_screen()
        element = screen.element(self._number) if screen and self._number is not None else None
        return bool(element and element.texture and element.texture["kind"] == "image")

    def clear_texture(self) -> None:
        self.tex_source.setCurrentIndex(0)
        self.apply_texture()


class ProjectPanel(QWidget):
    message = Signal(str)

    def __init__(self, ctrl: Controller, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctrl = ctrl
        self._dirty = False
        self._loading = False
        self._flushing = False
        self.brief = {k: QLineEdit() for k in BRIEF_FIELDS}
        for key, widget in self.brief.items():
            widget.setToolTip(TIPS[f"brief_{key}"])
        self.tokens = {k: QPlainTextEdit() for k in TOKEN_FIELDS}
        for key, widget in self.tokens.items():
            widget.setToolTip(TIPS[f"tokens_{key}"])
        self.tokens["colors"].setPlaceholderText("primary #0a6cff, surface #ffffff")
        self.tokens["fonts"].setPlaceholderText("Inter 14/20 body, Inter 20 bold headings")
        self.tokens["spacing"].setPlaceholderText("4, 8, 12, 16, 24")
        self.tokens["radii"].setPlaceholderText("4 for inputs, 12 for cards")
        self.brief["purpose"].setPlaceholderText("What the app is for")
        self.brief["audience"].setPlaceholderText("Who uses it")
        self.brief["tone"].setPlaceholderText("calm, plain, professional")

        self.grid_size = QSpinBox()
        self.grid_size.setRange(1, 512)
        self.grid_size.setSuffix(" px")
        self.grid_size.setToolTip(TIPS["grid_size"])
        self.grid_snap = QCheckBox("Snap elements to the grid")
        self.grid_snap.setToolTip(TIPS["grid_snap"])

        form = QFormLayout()
        form.setVerticalSpacing(10)
        for key, widget in self.brief.items():
            form.addRow(key.capitalize(), widget)
        for key, widget in self.tokens.items():
            form.addRow(key.capitalize(), widget)
        self.save_btn = QPushButton("Save brief")
        self.save_btn.setProperty("variant", "filled")
        self.save_btn.setToolTip(TIPS["save_brief"])
        self.save_btn.clicked.connect(self.save)

        grid_form = QFormLayout()
        grid_form.setVerticalSpacing(10)
        grid_form.addRow("Grid size", self.grid_size)
        grid_form.addRow("", self.grid_snap)
        self.grid_save = QPushButton("Save grid")
        self.grid_save.setToolTip(TIPS["save_grid"])
        self.grid_save.clicked.connect(self.save_grid)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section("Project brief", HINTS["project"]))
        layout.addLayout(form)
        layout.addWidget(self.save_btn, 0, Qt.AlignmentFlag.AlignRight)
        layout.addSpacing(12)
        layout.addWidget(section("Layout grid", HINTS["grid"]))
        layout.addLayout(grid_form)
        layout.addWidget(self.grid_save, 0, Qt.AlignmentFlag.AlignRight)
        layout.addStretch(1)
        for editor in (*self.brief.values(), *self.tokens.values()):
            editor.textChanged.connect(self._mark_dirty)
            editor.installEventFilter(self)
            viewport = getattr(editor, "viewport", None)
            if viewport is not None:
                viewport().installEventFilter(self)
        self.grid_size.valueChanged.connect(self._mark_dirty)
        self.grid_snap.toggled.connect(self._mark_dirty)

    def _mark_dirty(self, *_) -> None:
        if not self._loading:
            self._dirty = True

    def flush(self) -> bool:
        project = self.ctrl.project
        if self._flushing or not self._dirty or project is None:
            return False
        brief = {k: w.text() for k, w in self.brief.items()}
        tokens = {k: w.toPlainText() for k, w in self.tokens.items()}
        self._flushing = True
        try:
            if brief != project.brief:
                run(self.ctrl, "project.set_brief", {"fields": brief})
            if tokens != project.tokens:
                run(self.ctrl, "project.set_tokens", {"fields": tokens})
            if (int(project.grid.get("size", 8)) != self.grid_size.value()
                    or bool(project.grid.get("snap", True)) != self.grid_snap.isChecked()):
                run(self.ctrl, "project.set_grid",
                    {"size": self.grid_size.value(), "snap": self.grid_snap.isChecked()})
        finally:
            self._flushing = False
            self._dirty = False
        return True

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.FocusOut:
            widget = QApplication.focusWidget()
            if widget is None or not (widget is self or self.isAncestorOf(widget)):
                self.flush()
        return super().eventFilter(obj, event)

    def refresh(self) -> None:
        self._loading = True
        try:
            self._refresh_fields()
        finally:
            self._loading = False
            self._dirty = False

    def _refresh_fields(self) -> None:
        project = self.ctrl.project
        for key, widget in self.brief.items():
            widget.setText(project.brief.get(key, "") if project else "")
        for key, widget in self.tokens.items():
            widget.setPlainText(project.tokens.get(key, "") if project else "")
        grid = project.grid if project else {"size": 8, "snap": True}
        self.grid_size.setValue(int(grid.get("size", 8)))
        self.grid_snap.setChecked(bool(grid.get("snap", True)))
        enabled = project is not None
        for w in (*self.brief.values(), *self.tokens.values(), self.save_btn,
                  self.grid_size, self.grid_snap, self.grid_save):
            w.setEnabled(enabled)

    def save_grid(self) -> None:
        try:
            run(self.ctrl, "project.set_grid", {"size": self.grid_size.value(), "snap": self.grid_snap.isChecked()})
            self._dirty = False
            self.message.emit("Grid saved")
        except CommandError as exc:
            self.message.emit(str(exc))

    def save(self) -> None:
        try:
            run(self.ctrl, "project.set_brief", {"fields": {k: w.text() for k, w in self.brief.items()}})
            run(self.ctrl, "project.set_tokens",
                {"fields": {k: w.toPlainText() for k, w in self.tokens.items()}})
            self._dirty = False
            self.message.emit("Project brief saved")
        except CommandError as exc:
            self.message.emit(str(exc))
