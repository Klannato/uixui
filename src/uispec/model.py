from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field

GRID_DEFAULT = {"size": 8, "snap": True}
TEXTURE_MODES = ("tile", "stretch")
PATTERNS = ("noise", "grain", "stripes", "dots", "hatch")
STATES = ["default", "hover", "pressed", "focused", "disabled", "error", "empty", "loading"]
SHAPE_KINDS = ("rect", "ellipse", "freehand")
FIELD_NAMES = ("name", "purpose", "behavior", "states", "content", "constraints", "notes", "reference")
BRIEF_FIELDS = ("purpose", "audience", "tone")
TOKEN_FIELDS = ("colors", "fonts", "spacing", "radii")


MIN_SIZE = 4.0


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def bounds(points: list[list[float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def fit_points(points: list[list[float]], kind: str, old: tuple, new: tuple) -> list[list[float]]:
    """Map a shape from its old bounding box onto a new one. Rectangles and ellipses stay two corners."""
    x0, y0, x1, y1 = new
    if kind in ("rect", "ellipse"):
        return [[x0, y0], [x1, y1]]
    ox0, oy0, ox1, oy1 = old
    ow = (ox1 - ox0) or 1.0
    oh = (oy1 - oy0) or 1.0
    nw, nh = x1 - x0, y1 - y0
    return [[x0 + (x - ox0) / ow * nw, y0 + (y - oy0) / oh * nh] for x, y in points]


@dataclass
class Element:
    number: int
    kind: str
    points: list[list[float]]
    id: str = field(default_factory=new_id)
    name: str = ""
    purpose: str = ""
    behavior: str = ""
    states: list[str] = field(default_factory=list)
    content: str = ""
    constraints: str = ""
    notes: str = ""
    reference: str = ""
    texture: dict | None = None

    def bbox(self) -> tuple[float, float, float, float]:
        return bounds(self.points)

    def resize(self, x0: float, y0: float, x1: float, y1: float) -> None:
        if x1 - x0 < MIN_SIZE or y1 - y0 < MIN_SIZE:
            raise ValueError(f"elements must be at least {MIN_SIZE:g}px on each side")
        self.points = fit_points(self.points, self.kind, self.bbox(), (x0, y0, x1, y1))

    def center(self) -> tuple[float, float]:
        x0, y0, x1, y1 = self.bbox()
        return (x0 + x1) / 2, (y0 + y1) / 2

    def missing_fields(self) -> list[str]:
        missing = []
        if not self.name.strip():
            missing.append("name")
        if not self.purpose.strip():
            missing.append("purpose")
        return missing

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Element:
        return cls(**d)


@dataclass
class Arrow:
    from_number: int
    id: str = field(default_factory=new_id)
    to_number: int | None = None
    to_point: list[float] | None = None
    label: str = ""


@dataclass
class TextLabel:
    text: str
    x: float
    y: float
    id: str = field(default_factory=new_id)


@dataclass
class Screen:
    name: str
    image: str
    id: str = field(default_factory=new_id)
    leads_to: str = ""
    blank: bool = False
    canvas_color: str = ""
    elements: list[Element] = field(default_factory=list)
    arrows: list[Arrow] = field(default_factory=list)
    labels: list[TextLabel] = field(default_factory=list)

    def element(self, number: int) -> Element | None:
        for e in self.elements:
            if e.number == number:
                return e
        return None

    def add_element(self, kind: str, points: list[list[float]]) -> Element:
        if kind not in SHAPE_KINDS:
            raise ValueError(f"unknown shape kind: {kind}")
        e = Element(number=len(self.elements) + 1, kind=kind, points=points)
        self.elements.append(e)
        return e

    def delete_element(self, number: int) -> None:
        if self.element(number) is None:
            raise KeyError(f"no element {number}")
        self.elements = [e for e in self.elements if e.number != number]
        self.arrows = [a for a in self.arrows if a.from_number != number and a.to_number != number]
        self.renumber()

    def renumber(self) -> None:
        mapping = {}
        for i, e in enumerate(self.elements, 1):
            mapping[e.number] = i
            e.number = i
        for a in self.arrows:
            a.from_number = mapping.get(a.from_number, a.from_number)
            if a.to_number is not None:
                a.to_number = mapping.get(a.to_number, a.to_number)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "image": self.image,
            "leads_to": self.leads_to,
            "blank": self.blank,
            "canvas_color": self.canvas_color,
            "elements": [e.to_dict() for e in self.elements],
            "arrows": [asdict(a) for a in self.arrows],
            "labels": [asdict(t) for t in self.labels],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Screen:
        return cls(
            id=d["id"],
            name=d["name"],
            image=d["image"],
            leads_to=d.get("leads_to", ""),
            blank=bool(d.get("blank", False)),
            canvas_color=d.get("canvas_color", ""),
            elements=[Element.from_dict(e) for e in d.get("elements", [])],
            arrows=[Arrow(**a) for a in d.get("arrows", [])],
            labels=[TextLabel(**t) for t in d.get("labels", [])],
        )


@dataclass
class Project:
    name: str
    brief: dict = field(default_factory=lambda: {k: "" for k in BRIEF_FIELDS})
    tokens: dict = field(default_factory=lambda: {k: "" for k in TOKEN_FIELDS})
    grid: dict = field(default_factory=lambda: dict(GRID_DEFAULT))
    screens: list[Screen] = field(default_factory=list)

    def screen(self, screen_id: str) -> Screen:
        for s in self.screens:
            if s.id == screen_id:
                return s
        raise KeyError(f"no screen {screen_id}")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "brief": dict(self.brief),
            "tokens": dict(self.tokens),
            "grid": dict(self.grid),
            "screens": [s.to_dict() for s in self.screens],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Project:
        return cls(
            name=d["name"],
            brief={k: d.get("brief", {}).get(k, "") for k in BRIEF_FIELDS},
            tokens={k: d.get("tokens", {}).get(k, "") for k in TOKEN_FIELDS},
            grid={**GRID_DEFAULT, **d.get("grid", {})},
            screens=[Screen.from_dict(s) for s in d.get("screens", [])],
        )
