"""Grid snapping and alignment math. Pure functions, so the GUI and the CLI share one implementation."""

from __future__ import annotations

ALIGN_MODES = ("left", "hcenter", "right", "top", "vcenter", "bottom", "dist_h", "dist_v")
Box = tuple[float, float, float, float]


def snap(value: float, size: float) -> float:
    if size <= 0:
        return value
    return round(value / size) * size


def align_deltas(boxes: dict[int, Box], mode: str) -> dict[int, tuple[float, float]]:
    """Offset each box so it lines up with the selection's outer bounds. Returns {number: (dx, dy)}."""
    if mode not in ALIGN_MODES:
        raise ValueError(f"unknown align mode {mode!r}")
    if mode.startswith("dist_"):
        return _distribute(boxes, horizontal=(mode == "dist_h"))
    if len(boxes) < 2:
        raise ValueError("align needs at least two elements")
    x0 = min(b[0] for b in boxes.values())
    x1 = max(b[2] for b in boxes.values())
    y0 = min(b[1] for b in boxes.values())
    y1 = max(b[3] for b in boxes.values())
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    deltas = {}
    for number, (bx0, by0, bx1, by1) in boxes.items():
        dx = dy = 0.0
        if mode == "left":
            dx = x0 - bx0
        elif mode == "right":
            dx = x1 - bx1
        elif mode == "hcenter":
            dx = cx - (bx0 + bx1) / 2
        elif mode == "top":
            dy = y0 - by0
        elif mode == "bottom":
            dy = y1 - by1
        elif mode == "vcenter":
            dy = cy - (by0 + by1) / 2
        deltas[number] = (dx, dy)
    return deltas


def _distribute(boxes: dict[int, Box], horizontal: bool) -> dict[int, tuple[float, float]]:
    if len(boxes) < 3:
        raise ValueError("distribute needs at least three elements")
    lo, hi = (0, 2) if horizontal else (1, 3)
    items = sorted(boxes.items(), key=lambda kv: kv[1][lo])
    start = items[0][1][lo]
    end = max(b[hi] for _, b in items)
    total = sum(b[hi] - b[lo] for _, b in items)
    gap = (end - start - total) / (len(items) - 1)
    cursor = start
    deltas = {}
    for number, box in items:
        delta = cursor - box[lo]
        deltas[number] = (delta, 0.0) if horizontal else (0.0, delta)
        cursor += (box[hi] - box[lo]) + gap
    return deltas
