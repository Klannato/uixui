from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QInputDialog, QWidget

from ..commands import COMMANDS, CommandError
from ..controller import Controller
from ..model import Element
from ..render import ACCENT, PIN_RADIUS, draw_screen_marks

TOOLS = ("select", "rect", "ellipse", "freehand", "arrow", "text")
BACKGROUND = QColor("#1e1e1e")
HIT_MARGIN = 6


class Canvas(QWidget):
    selectionChanged = Signal(object)
    message = Signal(str)

    def __init__(self, ctrl: Controller, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.tool = "select"
        self.selected: int | None = None
        self._image: QImage | None = None
        self._image_key: str | None = None
        self._draft: dict | None = None
        self._drag: dict | None = None
        self.setMinimumSize(480, 360)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(False)

    # ---- state -----------------------------------------------------------

    def set_tool(self, tool: str) -> None:
        if tool not in TOOLS:
            raise ValueError(tool)
        self.tool = tool
        self._draft = None
        self.update()

    def screen(self):
        return self.ctrl.current_screen()

    def refresh(self) -> None:
        screen = self.screen()
        key = None
        if screen is not None:
            key = f"{self.ctrl.folder}/{screen.image}"
        if key != self._image_key:
            self._image_key = key
            self._image = QImage(key) if key else None
            self.selected = None
            self.selectionChanged.emit(None)
        if self.selected is not None and (screen is None or screen.element(self.selected) is None):
            self.selected = None
            self.selectionChanged.emit(None)
        self.update()

    def select(self, number: int | None) -> None:
        self.selected = number
        self.selectionChanged.emit(number)
        self.update()

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
        p.fillRect(self.rect(), BACKGROUND)
        if self._image is None or self._image.isNull():
            p.setPen(QColor("#aaaaaa"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Paste or drop a screenshot, or capture a region")
            p.end()
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.drawImage(self._image_rect(), self._image)
        scale, ox, oy = self._fit()
        p.translate(ox, oy)
        p.scale(scale, scale)
        screen = self.screen()
        if screen is not None:
            draw_screen_marks(p, screen, self.selected)
        self._paint_draft(p)
        p.end()

    def _paint_draft(self, p: QPainter) -> None:
        d = self._draft
        if not d:
            return
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

    # ---- mouse -----------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self._image is None:
            return
        self.setFocus()
        x, y = self.to_image(event.position())
        screen = self.screen()
        if self.tool == "select":
            hit = self._element_at(x, y)
            self.select(hit.number if hit else None)
            if hit:
                self._drag = {"number": hit.number, "origin": (x, y),
                              "original": [list(p) for p in hit.points]}
        elif self.tool in ("rect", "ellipse"):
            self._draft = {"kind": self.tool, "start": (x, y), "end": (x, y)}
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
                self._run("label.add", {"text": text.strip(), "x": x, "y": y})
        self.update()

    def mouseMoveEvent(self, event):
        x, y = self.to_image(event.position())
        if self._draft:
            d = self._draft
            if d["kind"] == "freehand":
                d["points"].append((x, y))
            else:
                d["end"] = (x, y)
            self.update()
        elif self._drag:
            self._move_selected(x, y)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._drag:
            self._finish_drag()
            return
        d, self._draft = self._draft, None
        if not d:
            return
        x, y = self.to_image(event.position())
        if d["kind"] in ("rect", "ellipse"):
            (x0, y0), (x1, y1) = d["start"], (x, y)
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

    def _move_selected(self, x: float, y: float) -> None:
        drag = self._drag
        screen = self.screen()
        e = screen.element(drag["number"]) if screen else None
        if e is None:
            return
        dx = x - drag["origin"][0]
        dy = y - drag["origin"][1]
        e.points = [[px + dx, py + dy] for px, py in drag["original"]]
        drag["moved"] = (dx, dy)

    def _finish_drag(self) -> None:
        drag, self._drag = self._drag, None
        if not drag.get("moved"):
            return
        screen = self.screen()
        e = screen.element(drag["number"])
        final = [list(p) for p in e.points]
        number = drag["number"]
        e.points = [list(p) for p in drag["original"]]
        self.ctrl.mutate(lambda project: setattr(
            project.screen(screen.id).element(number), "points", final))
        self.update()

    # ---- keys ------------------------------------------------------------

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self.selected is not None:
            self._run("element.delete", {"number": self.selected})
            self.select(None)
        elif event.key() == Qt.Key.Key_Escape:
            self._draft = None
            self._drag = None
            self.select(None)
        else:
            super().keyPressEvent(event)
        self.update()

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
            self.select(result.get("number"))
        return result
