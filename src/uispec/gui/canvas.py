from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QImage, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QInputDialog, QWidget

from .. import layout
from ..commands import COMMANDS, CommandError
from ..controller import Controller
from ..model import MIN_SIZE, Element, bounds, fit_points
from ..render import ACCENT, PIN_RADIUS, draw_screen_marks
from . import theme
from .help import HINTS

TOOLS = ("select", "rect", "ellipse", "freehand", "arrow", "text")
HIT_MARGIN = 6
HANDLE_PX = 10
HANDLE_CURSORS = {
    "n": Qt.CursorShape.SizeVerCursor, "s": Qt.CursorShape.SizeVerCursor,
    "e": Qt.CursorShape.SizeHorCursor, "w": Qt.CursorShape.SizeHorCursor,
    "ne": Qt.CursorShape.SizeBDiagCursor, "sw": Qt.CursorShape.SizeBDiagCursor,
    "se": Qt.CursorShape.SizeFDiagCursor, "nw": Qt.CursorShape.SizeFDiagCursor,
}
BAND_THRESHOLD = 3


class Canvas(QWidget):
    selectionChanged = Signal(list)
    message = Signal(str)
    interacted = Signal()

    def __init__(self, ctrl: Controller, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.tool = "select"
        self.selection: list[int] = []
        self.grid_visible = False
        self._image: QImage | None = None
        self._image_key: str | None = None
        self._draft: dict | None = None
        self._drag: dict | None = None
        self.setMinimumSize(480, 360)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    # ---- state -----------------------------------------------------------

    @property
    def selected(self) -> int | None:
        return self.selection[-1] if self.selection else None

    def set_tool(self, tool: str) -> None:
        if tool not in TOOLS:
            raise ValueError(tool)
        self.tool = tool
        self._draft = None
        self.update()

    def screen(self):
        return self.ctrl.current_screen()

    def toggle_grid(self) -> bool:
        self.grid_visible = not self.grid_visible
        self.update()
        return self.grid_visible

    def refresh(self) -> None:
        screen = self.screen()
        key = f"{self.ctrl.folder}/{screen.image}" if screen is not None else None
        if key != self._image_key:
            self._image_key = key
            self._image = QImage(key) if key else None
            self._set_selection([])
        numbers = {e.number for e in screen.elements} if screen is not None else set()
        kept = [n for n in self.selection if n in numbers]
        if kept != self.selection:
            self._set_selection(kept)
        self.update()

    def select(self, numbers) -> None:
        if numbers is None:
            numbers = []
        elif isinstance(numbers, int):
            numbers = [numbers]
        self._set_selection(list(numbers))
        self.update()

    def _set_selection(self, numbers: list[int]) -> None:
        self.selection = numbers
        self.selectionChanged.emit(list(numbers))

    def _grid(self) -> tuple[float, bool]:
        project = self.ctrl.project
        if project is None:
            return 8.0, False
        return float(project.grid.get("size", 8)), bool(project.grid.get("snap", True))

    def _sn(self, value: float) -> float:
        size, on = self._grid()
        return layout.snap(value, size) if on else value

    # ---- coordinates -------------------------------------------------------

    def _fit(self) -> tuple[float, float, float]:
        if self._image is None or self._image.isNull():
            return 1.0, 0.0, 0.0
        iw, ih = self._image.width(), self._image.height()
        scale = min(self.width() / iw, self.height() / ih)
        ox = (self.width() - iw * scale) / 2
        oy = (self.height() - ih * scale) / 2
        return scale, ox, oy

    def to_image(self, pos: QPointF) -> tuple[float, float]:
        scale, ox, oy = self._fit()
        return (pos.x() - ox) / scale, (pos.y() - oy) / scale

    def _image_rect(self) -> QRectF:
        scale, ox, oy = self._fit()
        if self._image is None:
            return QRectF()
        return QRectF(ox, oy, self._image.width() * scale, self._image.height() * scale)

    # ---- painting --------------------------------------------------------

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.colors()["canvas"]))
        if self._image is None or self._image.isNull():
            p.setPen(QColor(theme.colors()["on_variant"]))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, HINTS["canvas_empty"])
            p.end()
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.drawImage(self._image_rect(), self._image)
        scale, ox, oy = self._fit()
        p.translate(ox, oy)
        p.scale(scale, scale)
        if self.grid_visible:
            self._paint_grid(p)
        screen = self.screen()
        if screen is not None:
            draw_screen_marks(p, screen, self.selection, self.ctrl.folder)
        self._paint_group_box(p)
        self._paint_draft(p)
        self._paint_handles(p)
        p.end()

    def _paint_grid(self, p: QPainter) -> None:
        size, _ = self._grid()
        w, h = self._image.width(), self._image.height()
        p.setPen(QPen(QColor(0, 180, 255, 90), 1 / self._fit()[0]))
        x = 0.0
        while x <= w:
            p.drawLine(QPointF(x, 0), QPointF(x, h))
            x += size
        y = 0.0
        while y <= h:
            p.drawLine(QPointF(0, y), QPointF(w, y))
            y += size

    def _paint_group_box(self, p: QPainter) -> None:
        screen = self.screen()
        if screen is None or len(self.selection) < 2:
            return
        boxes = [screen.element(n).bbox() for n in self.selection if screen.element(n)]
        if not boxes:
            return
        x0 = min(b[0] for b in boxes)
        y0 = min(b[1] for b in boxes)
        x1 = max(b[2] for b in boxes)
        y1 = max(b[3] for b in boxes)
        p.setPen(QPen(QColor(ACCENT), 1.5 / self._fit()[0], Qt.PenStyle.DotLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(QPointF(x0 - 4, y0 - 4), QPointF(x1 + 4, y1 + 4)))

    def _paint_draft(self, p: QPainter) -> None:
        d = self._draft
        if d:
            pen = QPen(ACCENT, 3, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            if d["kind"] in ("rect", "ellipse"):
                rect = QRectF(QPointF(*d["start"]), QPointF(*d["end"])).normalized()
                if d["kind"] == "rect":
                    p.drawRect(rect)
                else:
                    p.drawEllipse(rect)
            elif d["kind"] == "freehand":
                p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in d["points"]]))
            elif d["kind"] == "arrow":
                p.setPen(QPen(ACCENT, 3))
                p.drawLine(QPointF(*d["start"]), QPointF(*d["end"]))
        if self._drag and self._drag["mode"] == "band":
            band = self._drag
            p.setPen(QPen(ACCENT, 1.5 / self._fit()[0], Qt.PenStyle.DashLine))
            p.setBrush(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 40))
            p.drawRect(QRectF(QPointF(*band["start"]), QPointF(*band["end"])).normalized())

    def _handle_points(self, e: Element) -> dict[str, tuple[float, float]]:
        x0, y0, x1, y1 = e.bbox()
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        return {
            "n": (mx, y0), "ne": (x1, y0), "e": (x1, my), "se": (x1, y1),
            "s": (mx, y1), "sw": (x0, y1), "w": (x0, my),
        }

    def _single_element(self) -> Element | None:
        screen = self.screen()
        if screen is None or len(self.selection) != 1 or self.tool != "select":
            return None
        return screen.element(self.selection[0])

    def _paint_handles(self, p: QPainter) -> None:
        e = self._single_element()
        if e is None:
            return
        scale, _, _ = self._fit()
        size = HANDLE_PX / scale
        p.setPen(QPen(QColor(ACCENT), 1.5 / scale))
        p.setBrush(QColor("#ffffff"))
        for hx, hy in self._handle_points(e).values():
            p.drawRect(QRectF(hx - size / 2, hy - size / 2, size, size))

    # ---- hit testing -----------------------------------------------------

    def _element_at(self, x: float, y: float) -> Element | None:
        screen = self.screen()
        if screen is None:
            return None
        for e in reversed(screen.elements):
            x0, y0, x1, y1 = e.bbox()
            if x0 - HIT_MARGIN <= x <= x1 + HIT_MARGIN and y0 - HIT_MARGIN <= y <= y1 + HIT_MARGIN:
                return e
        return None

    def _pin_at(self, x: float, y: float) -> Element | None:
        screen = self.screen()
        if screen is None:
            return None
        scale, _, _ = self._fit()
        radius = (PIN_RADIUS + 4) / scale
        for e in reversed(screen.elements):
            px, py, _, _ = e.bbox()
            if math.hypot(x - px, y - py) <= radius:
                return e
        return None

    def _handle_at(self, x: float, y: float) -> str | None:
        e = self._single_element()
        if e is None:
            return None
        scale, _, _ = self._fit()
        px, py, _, _ = e.bbox()
        if math.hypot(x - px, y - py) <= (PIN_RADIUS + 2) / scale:
            return "nw"
        radius = (HANDLE_PX / 2 + 4) / scale
        for name, (hx, hy) in self._handle_points(e).items():
            if abs(x - hx) <= radius and abs(y - hy) <= radius:
                return name
        return None

    # ---- mouse -----------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self._image is None:
            return
        self.setFocus()
        self.interacted.emit()
        x, y = self.to_image(event.position())
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        screen = self.screen()
        if self.tool == "select":
            self._press_select(x, y, shift)
        elif self.tool in ("rect", "ellipse"):
            self._draft = {"kind": self.tool, "start": (self._sn(x), self._sn(y)),
                           "end": (self._sn(x), self._sn(y))}
        elif self.tool == "freehand":
            self._draft = {"kind": "freehand", "points": [(x, y)]}
        elif self.tool == "arrow":
            source = self._pin_at(x, y)
            if source is not None:
                self._draft = {"kind": "arrow", "from": source.number,
                               "start": source.bbox()[:2], "end": (x, y)}
        elif self.tool == "text" and screen is not None:
            text, ok = QInputDialog.getText(self, "Note", "Text for this screen:")
            if ok and text.strip():
                self._run("label.add", {"text": text.strip(), "x": self._sn(x), "y": self._sn(y)})
        self.update()

    def _press_select(self, x: float, y: float, shift: bool) -> None:
        handle = self._handle_at(x, y)
        if handle is not None:
            e = self._single_element()
            self._drag = {"mode": "resize", "handle": handle, "origin": (x, y),
                          "originals": {e.number: [list(p) for p in e.points]}}
            return
        hit = self._element_at(x, y)
        if hit is None:
            self._drag = {"mode": "band", "start": (x, y), "end": (x, y),
                          "base": list(self.selection) if shift else []}
            if not shift:
                self.select([])
            return
        if shift:
            if hit.number in self.selection:
                self.select([n for n in self.selection if n != hit.number])
                return
            self.select([*self.selection, hit.number])
        elif hit.number not in self.selection:
            self.select([hit.number])
        screen = self.screen()
        originals = {n: [list(p) for p in screen.element(n).points] for n in self.selection}
        self._drag = {"mode": "move", "origin": (x, y), "originals": originals}

    def mouseMoveEvent(self, event):
        x, y = self.to_image(event.position())
        if self._draft:
            d = self._draft
            if d["kind"] == "freehand":
                d["points"].append((x, y))
            else:
                d["end"] = (self._sn(x), self._sn(y)) if d["kind"] in ("rect", "ellipse") else (x, y)
        elif self._drag:
            mode = self._drag["mode"]
            if mode == "resize":
                self._resize_selected(x, y)
            elif mode == "move":
                self._move_selected(x, y)
            else:
                self._drag["end"] = (x, y)
        else:
            self.setCursor(self._cursor_for(self._handle_at(x, y)))
        self.update()

    def _cursor_for(self, handle: str | None) -> QCursor:
        if handle is None:
            return QCursor(Qt.CursorShape.ArrowCursor)
        if handle == "nw":
            return QCursor(Qt.CursorShape.SizeFDiagCursor)
        return QCursor(HANDLE_CURSORS[handle])

    def _resize_selected(self, x: float, y: float) -> None:
        drag = self._drag
        screen = self.screen()
        number = next(iter(drag["originals"]))
        e = screen.element(number) if screen else None
        if e is None:
            return
        original = drag["originals"][number]
        ox0, oy0, ox1, oy1 = bounds(original)
        h = drag["handle"]
        x0, y0, x1, y1 = ox0, oy0, ox1, oy1
        if "w" in h or h == "nw":
            x0 = min(self._sn(x), ox1 - MIN_SIZE)
        if "e" in h:
            x1 = max(self._sn(x), ox0 + MIN_SIZE)
        if "n" in h or h == "nw":
            y0 = min(self._sn(y), oy1 - MIN_SIZE)
        if "s" in h:
            y1 = max(self._sn(y), oy0 + MIN_SIZE)
        e.points = fit_points(original, e.kind, (ox0, oy0, ox1, oy1), (x0, y0, x1, y1))
        drag["moved"] = True

    def _move_selected(self, x: float, y: float) -> None:
        drag = self._drag
        screen = self.screen()
        if screen is None:
            return
        dx = x - drag["origin"][0]
        dy = y - drag["origin"][1]
        anchor = bounds(next(iter(drag["originals"].values())))
        dx = self._sn(anchor[0] + dx) - anchor[0]
        dy = self._sn(anchor[1] + dy) - anchor[1]
        for number, original in drag["originals"].items():
            e = screen.element(number)
            if e is not None:
                e.points = [[px + dx, py + dy] for px, py in original]
        drag["moved"] = (dx, dy)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._drag:
            self._finish_drag()
            self.update()
            return
        d, self._draft = self._draft, None
        if not d:
            self.update()
            return
        x, y = self.to_image(event.position())
        if d["kind"] in ("rect", "ellipse"):
            (x0, y0), (x1, y1) = d["start"], (self._sn(x), self._sn(y))
            w, h = abs(x1 - x0), abs(y1 - y0)
            if w >= 3 and h >= 3:
                box = [min(x0, x1), min(y0, y1), w, h]
                self._run("element.add", {"kind": d["kind"], "box": box}, select_new=True)
        elif d["kind"] == "freehand":
            pts = d["points"]
            if len(pts) >= 2:
                self._run("element.add", {"kind": "freehand", "points": pts}, select_new=True)
        elif d["kind"] == "arrow":
            target = self._element_at(x, y)
            if target is not None and target.number != d["from"]:
                self._run("arrow.add", {"from": d["from"], "to": target.number})
            elif target is None:
                self._run("arrow.add", {"from": d["from"], "to_point": [x, y]})
        self.update()

    def _finish_drag(self) -> None:
        drag, self._drag = self._drag, None
        if drag["mode"] == "band":
            self._finish_band(drag)
            return
        if not drag.get("moved"):
            return
        screen = self.screen()
        if screen is None:
            return
        finals = {}
        for number, original in drag["originals"].items():
            e = screen.element(number)
            if e is None:
                continue
            finals[number] = [[round(px, 2), round(py, 2)] for px, py in e.points]
            e.points = [list(p) for p in original]
        sid = screen.id

        def apply(project):
            target = project.screen(sid)
            for number, points in finals.items():
                target.element(number).points = points
        try:
            self.ctrl.mutate(apply)
        except Exception as exc:
            self.message.emit(str(exc))

    def _finish_band(self, band: dict) -> None:
        (x0, y0), (x1, y1) = band["start"], band["end"]
        if abs(x1 - x0) < BAND_THRESHOLD and abs(y1 - y0) < BAND_THRESHOLD:
            return
        rect = QRectF(QPointF(x0, y0), QPointF(x1, y1)).normalized()
        screen = self.screen()
        hits = []
        for e in screen.elements if screen else []:
            bx0, by0, bx1, by1 = e.bbox()
            if rect.intersects(QRectF(QPointF(bx0, by0), QPointF(bx1, by1))):
                hits.append(e.number)
        base = [n for n in band["base"] if n not in hits]
        self.select(base + hits)

    # ---- keys ------------------------------------------------------------

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self.selection:
            for number in sorted(self.selection, reverse=True):
                self._run("element.delete", {"number": number})
            self.select([])
        elif key == Qt.Key.Key_Escape:
            self._draft = None
            self._drag = None
            self.select([])
        elif key == Qt.Key.Key_A and mods & Qt.KeyboardModifier.ControlModifier:
            screen = self.screen()
            self.select([e.number for e in screen.elements] if screen else [])
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down) and self.selection:
            step, on = self._grid()
            amount = step if on else 1.0
            if mods & Qt.KeyboardModifier.ShiftModifier:
                amount *= 5
            dx = {Qt.Key.Key_Left: -amount, Qt.Key.Key_Right: amount}.get(key, 0.0)
            dy = {Qt.Key.Key_Up: -amount, Qt.Key.Key_Down: amount}.get(key, 0.0)
            self._nudge(dx, dy)
        else:
            super().keyPressEvent(event)
        self.update()

    def _nudge(self, dx: float, dy: float) -> None:
        screen = self.screen()
        if screen is None:
            return
        sid = screen.id
        numbers = list(self.selection)

        def apply(project):
            target = project.screen(sid)
            for number in numbers:
                e = target.element(number)
                e.points = [[x + dx, y + dy] for x, y in e.points]
        try:
            self.ctrl.mutate(apply)
        except Exception as exc:
            self.message.emit(str(exc))

    # ---- commands --------------------------------------------------------

    def _run(self, name: str, args: dict, select_new: bool = False):
        screen = self.screen()
        if screen is not None:
            args = {"screen": screen.id, **args}
        try:
            result = COMMANDS[name](self.ctrl, args)
        except (CommandError, RuntimeError, ValueError, KeyError) as exc:
            self.message.emit(str(exc))
            return None
        if select_new and result:
            self.select([result.get("number")])
        return result
