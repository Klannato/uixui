import pytest

from uispec.layout import align_deltas, snap


def apply(boxes, deltas):
    out = {}
    for n, (x0, y0, x1, y1) in boxes.items():
        dx, dy = deltas.get(n, (0, 0))
        out[n] = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
    return out


BOXES = {1: (10, 10, 50, 40), 2: (30, 60, 90, 100), 3: (100, 20, 120, 30)}


def test_snap_rounds_to_nearest_step():
    assert snap(13, 8) == 16
    assert snap(11, 8) == 8
    assert snap(5, 0) == 5


def test_align_left_and_right():
    moved = apply(BOXES, align_deltas(BOXES, "left"))
    assert {b[0] for b in moved.values()} == {10}
    moved = apply(BOXES, align_deltas(BOXES, "right"))
    assert {b[2] for b in moved.values()} == {120}


def test_align_centers_on_selection_middle():
    moved = apply(BOXES, align_deltas(BOXES, "hcenter"))
    centers = {(b[0] + b[2]) / 2 for b in moved.values()}
    assert len(centers) == 1


def test_align_top_and_bottom():
    moved = apply(BOXES, align_deltas(BOXES, "top"))
    assert {b[1] for b in moved.values()} == {10}
    moved = apply(BOXES, align_deltas(BOXES, "bottom"))
    assert {b[3] for b in moved.values()} == {100}


def test_distribute_equalises_gaps():
    deltas = align_deltas(BOXES, "dist_h")
    moved = apply(BOXES, deltas)
    ordered = sorted(moved.values(), key=lambda b: b[0])
    gaps = [ordered[i + 1][0] - ordered[i][2] for i in range(len(ordered) - 1)]
    assert gaps[0] == pytest.approx(gaps[1])
    assert ordered[0][0] == 10 and ordered[-1][2] == 120


def test_distribute_keeps_ends_fixed():
    deltas = align_deltas(BOXES, "dist_v")
    moved = apply(BOXES, deltas)
    assert min(b[1] for b in moved.values()) == 10
    assert max(b[3] for b in moved.values()) == 100


def test_align_needs_two_and_distribute_needs_three():
    with pytest.raises(ValueError):
        align_deltas({1: (0, 0, 1, 1)}, "left")
    with pytest.raises(ValueError):
        align_deltas({1: (0, 0, 1, 1), 2: (2, 0, 3, 1)}, "dist_h")
    with pytest.raises(ValueError):
        align_deltas(BOXES, "sideways")
