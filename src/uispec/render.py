from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF

from .model import Element, Screen

ACCENT = QColor("#e11d2e")
WHITE = QColor("#ffffff")
LABEL_BG = QColor(20, 20, 20, 210)
PIN_RADIUS = 13
STROKE = 3


def _element_pen(selected: bool) -> QPen:
    pen = QPen(ACCENT, STROKE)
    if selected:
        pen.setStyle(Qt.PenStyle.DashLine)
    return pen


def draw_element(p: QPainter, e: Element, selected: bool = False) -> None:
    p.setPen(_element_pen(selected))
    p.setBrush(Qt.BrushStyle.NoBrush)
    x0, y0, x1, y1 = e.bbox()
    rect = QRectF(QPointF(x0, y0), QPointF(x1, y1))
    if e.kind == "rect":
        p.drawRect(rect)
    elif e.kind == "ellipse":
        p.drawEllipse(rect)
    else:
        p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in e.points]))
    draw_pin(p, e.number, x0, y0)


def draw_pin(p: QPainter, number: int, x: float, y: float) -> None:
    p.setPen(QPen(WHITE, 2))
    p.setBrush(QBrush(ACCENT))
    p.drawEllipse(QPointF(x, y), PIN_RADIUS, PIN_RADIUS)
    font = QFont()
    font.setPixelSize(15)
    font.setBold(True)
    p.setFont(font)
    p.setPen(WHITE)
    p.drawText(QRectF(x - PIN_RADIUS, y - PIN_RADIUS, PIN_RADIUS * 2, PIN_RADIUS * 2),
               Qt.AlignmentFlag.AlignCenter, str(number))


def _arrow_end(screen: Screen, arrow) -> tuple[float, float] | None:
    if arrow.to_number is not None:
        target = screen.element(arrow.to_number)
        return target.center() if target else None
    if arrow.to_point is not None:
        return tuple(arrow.to_point)
    return None


def draw_arrow(p: QPainter, screen: Screen, arrow) -> None:
    source = screen.element(arrow.from_number)
    end = _arrow_end(screen, arrow)
    if source is None or end is None:
        return
    x0, y0, _, _ = source.bbox()
    start = QPointF(x0, y0)
    tip = QPointF(*end)
    p.setPen(QPen(ACCENT, STROKE))
    p.setBrush(QBrush(ACCENT))
    p.drawLine(start, tip)
    angle = math.atan2(tip.y() - start.y(), tip.x() - start.x())
    size = 16
    left = QPointF(tip.x() - size * math.cos(angle - 0.4), tip.y() - size * math.sin(angle - 0.4))
    right = QPointF(tip.x() - size * math.cos(angle + 0.4), tip.y() - size * math.sin(angle + 0.4))
    p.drawPolygon(QPolygonF([tip, left, right]))
    if arrow.label:
        mid = QPointF((start.x() + tip.x()) / 2, (start.y() + tip.y()) / 2)
        draw_text_box(p, arrow.label, mid.x(), mid.y())


def draw_text_box(p: QPainter, text: str, x: float, y: float) -> None:
    font = QFont()
    font.setPixelSize(16)
    p.setFont(font)
    metrics = p.fontMetrics()
    width = metrics.horizontalAdvance(text) + 12
    height = metrics.height() + 6
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(LABEL_BG))
    p.drawRoundedRect(QRectF(x, y, width, height), 4, 4)
    p.setPen(WHITE)
    p.drawText(QRectF(x + 6, y + 3, width, height), Qt.AlignmentFlag.AlignLeft, text)


def draw_screen_marks(p: QPainter, screen: Screen, selected: int | None = None) -> None:
    for arrow in screen.arrows:
        draw_arrow(p, screen, arrow)
    for e in screen.elements:
        draw_element(p, e, selected=(e.number == selected))
    for label in screen.labels:
        draw_text_box(p, label.text, label.x, label.y)
