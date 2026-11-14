from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from ..commands import COMMANDS, CommandError
from ..controller import Controller
from ..model import BRIEF_FIELDS, STATES, TOKEN_FIELDS
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section("Screens", "Drag to set the flow order."))
        layout.addWidget(self.list, 1)
        layout.addWidget(self.leads_to)

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
    selected = Signal(object)

    def __init__(self, ctrl: Controller, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctrl = ctrl
        self._number: int | None = None
        self.list = QListWidget()
        self.list.setToolTip(TIPS["element_list"])
        self.list.currentRowChanged.connect(self._on_user_row)
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
        self.save_btn.setToolTip(TIPS["save_element"])
        self.save_btn.clicked.connect(self.save)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setToolTip(TIPS["delete_element"])
        self.delete_btn.clicked.connect(self.delete)
        buttons = QHBoxLayout()
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.delete_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section("Elements"))
        layout.addWidget(self.list)
        layout.addWidget(self.empty_hint)
        layout.addSpacing(8)
        layout.addWidget(self.form_hint)
        layout.addLayout(self.form)
        layout.addLayout(buttons)
        layout.addStretch(1)
        self._set_form_enabled(False)

    def _set_form_enabled(self, enabled: bool) -> None:
        for w in (self.name, self.purpose, self.behavior, self.custom_states, self.content,
                  self.constraints, self.notes, self.reference, self.save_btn, self.delete_btn,
                  *self.state_boxes.values()):
            w.setEnabled(enabled)
        self.form_hint.setVisible(not enabled)

    def refresh(self, number: int | None = None) -> None:
        screen = self.ctrl.current_screen()
        self.list.blockSignals(True)
        self.list.clear()
        if screen is not None:
            for e in screen.elements:
                self.list.addItem(f"{e.number}. {e.name or '(unnamed)'}")
        self.list.blockSignals(False)
        self.empty_hint.setVisible(screen is None or not screen.elements)
        self.select_number(number)

    def select_number(self, number: int | None) -> None:
        screen = self.ctrl.current_screen()
        row = -1
        if screen is not None and number is not None:
            row = next((i for i, e in enumerate(screen.elements) if e.number == number), -1)
        self.list.blockSignals(True)
        self.list.setCurrentRow(row)
        self.list.blockSignals(False)
        self._on_row(row)

    def _on_user_row(self, row: int) -> None:
        self._on_row(row)
        self.selected.emit(self._number)

    def _on_row(self, row: int) -> None:
        screen = self.ctrl.current_screen()
        if screen is None or row < 0 or row >= len(screen.elements):
            self._number = None
            self._clear_form()
            self._set_form_enabled(False)
            return
        e = screen.elements[row]
        self._number = e.number
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
        self._set_form_enabled(True)

    def _clear_form(self) -> None:
        for w in (self.name, self.purpose, self.custom_states, self.reference):
            w.clear()
        for w in (self.behavior, self.content, self.constraints, self.notes):
            w.clear()
        for box in self.state_boxes.values():
            box.setChecked(False)

    def _states(self) -> list[str]:
        states = [s for s, box in self.state_boxes.items() if box.isChecked()]
        extra = [s.strip() for s in self.custom_states.text().split(",") if s.strip()]
        return states + extra

    def save(self) -> None:
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
            self.message.emit(f"Saved element {self._number}")
        except CommandError as exc:
            self.message.emit(str(exc))

    def delete(self) -> None:
        if self._number is None:
            return
        screen = self.ctrl.current_screen()
        try:
            run(self.ctrl, "element.delete", {"screen": screen.id, "number": self._number})
        except CommandError as exc:
            self.message.emit(str(exc))


class ProjectPanel(QWidget):
    message = Signal(str)

    def __init__(self, ctrl: Controller, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctrl = ctrl
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section("Project brief", HINTS["project"]))
        layout.addLayout(form)
        layout.addWidget(self.save_btn, 0, Qt.AlignmentFlag.AlignRight)
        layout.addStretch(1)

    def refresh(self) -> None:
        project = self.ctrl.project
        for key, widget in self.brief.items():
            widget.setText(project.brief.get(key, "") if project else "")
        for key, widget in self.tokens.items():
            widget.setPlainText(project.tokens.get(key, "") if project else "")
        enabled = project is not None
        for w in (*self.brief.values(), *self.tokens.values(), self.save_btn):
            w.setEnabled(enabled)

    def save(self) -> None:
        try:
            run(self.ctrl, "project.set_brief", {"fields": {k: w.text() for k, w in self.brief.items()}})
            run(self.ctrl, "project.set_tokens",
                {"fields": {k: w.toPlainText() for k, w in self.tokens.items()}})
            self.message.emit("Project brief saved")
        except CommandError as exc:
            self.message.emit(str(exc))
