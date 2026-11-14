"""Element textures: built-in seamless patterns and image fills, clipped to the element's shape."""

from __future__ import annotations

import random
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QTransform

from .model import PATTERNS

PATTERN_SIZE = 64
_image_cache: dict[str, QImage] = {}
_pattern_cache: dict[tuple[str, str], QImage] = {}


def clear_caches() -> None:
    """Drop cached QImages. Call before the Qt application shuts down."""
    _image_cache.clear()
    _pattern_cache.clear()


def pattern_tile(name: str, color: str) -> QImage:
    """A seamless PATTERN_SIZE tile. Pixel rules use modulo arithmetic, so the edges always meet."""
    key = (name, color)
    if key in _pattern_cache:
        return _pattern_cache[key]
    if name not in PATTERNS:
        raise ValueError(f"unknown pattern {name!r}; use one of {', '.join(PATTERNS)}")
    base = QColor(color)
    size = PATTERN_SIZE
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    rng = random.Random(7)
    for y in range(size):
        for x in range(size):
            alpha = 0
            if name == "noise" and rng.random() < 0.35:
                alpha = rng.randint(40, 160)
            elif name == "grain" and rng.random() < 0.6:
                alpha = rng.randint(20, 70)
            elif name == "stripes" and (x + y) % 16 < 5:
                alpha = 170
            elif name == "hatch" and ((x - y) % 16 < 2 or (x + y) % 16 < 2):
                alpha = 170
            elif name == "dots" and ((x % 16) - 8) ** 2 + ((y % 16) - 8) ** 2 <= 9:
                alpha = 190
            if alpha:
                img.setPixelColor(x, y, QColor(base.red(), base.green(), base.blue(), alpha))
    _pattern_cache[key] = img
    return img


def _load(path: Path) -> QImage:
    key = str(path)
    if key not in _image_cache:
        image = QImage(key)
        if image.isNull():
            raise ValueError(f"cannot read texture image: {path}")
        _image_cache[key] = image
    return _image_cache[key]


def texture_image(texture: dict, folder: Path | None) -> QImage:
    if texture["kind"] == "pattern":
        image = pattern_tile(texture["pattern"], texture.get("color") or "#808080")
    else:
        if folder is None:
            raise ValueError("image textures need a project folder")
        image = _load(folder / texture["file"])
    tint = texture.get("tint")
    if tint:
        tinted = image.convertToFormat(QImage.Format.Format_ARGB32)
        painter = QPainter(tinted)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        painter.fillRect(tinted.rect(), QColor(tint))
        painter.end()
        image = tinted
    return image


def fill(p: QPainter, texture: dict, rect, shape, folder: Path | None) -> None:
    """Paint the texture inside `shape` (a QPainterPath) covering `rect` (a QRectF)."""
    image = texture_image(texture, folder)
    p.save()
    p.setClipPath(shape)
    p.setOpacity(float(texture.get("opacity", 1.0)))
    if texture.get("mode") == "stretch" and texture["kind"] == "image":
        p.drawImage(rect, image)
    else:
        scale = float(texture.get("scale", 1.0))
        brush = QBrush(image)
        brush.setTransform(QTransform().scale(scale, scale))
        p.setBrushOrigin(rect.topLeft())
        p.fillRect(rect, brush)
    p.restore()
