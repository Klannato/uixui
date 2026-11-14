"""Material-style palette, stylesheet, and icons for the editor.

Annotation marks (outlines, pins, arrows) keep a fixed accent color in render.py so they stay
readable over any screenshot, whatever the editor theme is.
"""

from __future__ import annotations

import json

import qtawesome as qta
from PySide6.QtGui import QIcon

from .. import store

PALETTES = {
    "dark": {
        "window": "#141218",
        "surface": "#1d1b20",
        "surface_high": "#2b2930",
        "canvas": "#0f0d13",
        "on_surface": "#e6e1e5",
        "on_variant": "#cac4d0",
        "outline": "#938f99",
        "outline_variant": "#49454f",
        "primary": "#d0bcff",
        "on_primary": "#381e72",
        "primary_container": "#4f378b",
        "on_primary_container": "#eaddff",
        "hover": "#2e2b36",
        "pressed": "#3a3644",
        "inverse_surface": "#e6e1e5",
        "inverse_on": "#313033",
    },
    "light": {
        "window": "#f4eff4",
        "surface": "#fef7ff",
        "surface_high": "#ece6f0",
        "canvas": "#e7e0ec",
        "on_surface": "#1d1b20",
        "on_variant": "#49454f",
        "outline": "#79747e",
        "outline_variant": "#cac4d0",
        "primary": "#6750a4",
        "on_primary": "#ffffff",
        "primary_container": "#eaddff",
        "on_primary_container": "#21005d",
        "hover": "#ede6f4",
        "pressed": "#e2d9ef",
        "inverse_surface": "#313033",
        "inverse_on": "#f4eff4",
    },
}

_mode = "dark"


def mode() -> str:
    return _mode


def colors() -> dict:
    return PALETTES[_mode]


def set_mode(name: str) -> None:
    global _mode
    if name not in PALETTES:
        raise ValueError(f"unknown theme {name!r}")
    _mode = name


def _settings_path():
    return store.state_dir() / "settings.json"


def load_mode() -> None:
    path = _settings_path()
    if path.exists():
        try:
            set_mode(json.loads(path.read_text()).get("theme", "dark"))
        except (json.JSONDecodeError, ValueError, OSError):
            set_mode("dark")


def save_mode() -> None:
    _settings_path().write_text(json.dumps({"theme": _mode}))


def toggle() -> str:
    set_mode("light" if _mode == "dark" else "dark")
    save_mode()
    return _mode


def icon(name: str, color_key: str = "on_variant") -> QIcon:
    return qta.icon(name, color=colors()[color_key])


def stylesheet() -> str:
    c = colors()
    return f"""
QWidget {{
    color: {c['on_surface']};
    font-size: 10pt;
}}
QMainWindow, QStackedWidget {{
    background: {c['window']};
}}
QWidget#card {{
    background: {c['surface']};
    border-radius: 16px;
}}
QWidget#canvasFrame {{
    background: {c['canvas']};
    border-radius: 16px;
}}
QToolBar {{
    background: {c['surface']};
    border: none;
    border-bottom: 1px solid {c['outline_variant']};
    padding: 6px 10px;
    spacing: 4px;
}}
QToolBar::separator {{
    background: {c['outline_variant']};
    width: 1px;
    margin: 6px 8px;
}}
QToolButton {{
    color: {c['on_variant']};
    background: transparent;
    border: none;
    border-radius: 16px;
    padding: 6px 12px;
}}
QToolButton:hover {{
    background: {c['hover']};
    color: {c['on_surface']};
}}
QToolButton:pressed {{
    background: {c['pressed']};
}}
QToolButton:checked {{
    background: {c['primary_container']};
    color: {c['on_primary_container']};
}}
QToolButton:disabled {{
    color: {c['outline_variant']};
}}
QToolButton#primaryAction {{
    background: {c['primary']};
    color: {c['on_primary']};
    font-weight: 600;
}}
QToolButton#primaryAction:hover {{
    background: {c['primary']};
    color: {c['on_primary']};
}}
QPushButton {{
    background: transparent;
    color: {c['primary']};
    border: 1px solid {c['outline']};
    border-radius: 18px;
    padding: 7px 18px;
}}
QPushButton:hover {{
    background: {c['hover']};
}}
QPushButton:pressed {{
    background: {c['pressed']};
}}
QPushButton[variant="filled"] {{
    background: {c['primary']};
    color: {c['on_primary']};
    border: none;
    font-weight: 600;
}}
QPushButton:disabled {{
    color: {c['outline']};
    border-color: {c['outline_variant']};
}}
QLineEdit, QPlainTextEdit {{
    background: {c['surface_high']};
    border: 1px solid {c['outline_variant']};
    border-radius: 10px;
    padding: 6px 10px;
    selection-background-color: {c['primary']};
    selection-color: {c['on_primary']};
}}
QLineEdit:focus, QPlainTextEdit:focus {{
    border: 2px solid {c['primary']};
    padding: 5px 9px;
}}
QLineEdit:disabled, QPlainTextEdit:disabled {{
    color: {c['outline']};
}}
QListWidget {{
    background: {c['surface_high']};
    border: none;
    border-radius: 12px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 7px 10px;
    border-radius: 8px;
}}
QListWidget::item:hover {{
    background: {c['hover']};
}}
QListWidget::item:selected {{
    background: {c['primary_container']};
    color: {c['on_primary_container']};
}}
QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {c['on_variant']};
    padding: 10px 18px;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {c['primary']};
    border-bottom: 2px solid {c['primary']};
}}
QTabBar::tab:hover:!selected {{
    color: {c['on_surface']};
}}
QCheckBox {{
    spacing: 8px;
    color: {c['on_surface']};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {c['outline']};
    border-radius: 4px;
    background: transparent;
}}
QCheckBox::indicator:checked {{
    background: {c['primary']};
    border-color: {c['primary']};
}}
QLabel#sectionTitle {{
    font-size: 12pt;
    font-weight: 600;
    color: {c['on_surface']};
}}
QLabel#hint {{
    color: {c['on_variant']};
    font-size: 9pt;
}}
QToolTip {{
    background: {c['inverse_surface']};
    color: {c['inverse_on']};
    border: none;
    padding: 1px 4px;
    margin: 0px;
    border-radius: 4px;
}}
QStatusBar {{
    background: {c['surface']};
    color: {c['on_variant']};
    border-top: 1px solid {c['outline_variant']};
}}
QSplitter::handle {{
    background: transparent;
}}
QSplitter::handle:horizontal {{
    width: 10px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: {c['outline']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
QMessageBox, QInputDialog, QFileDialog, QDialog {{
    background: {c['surface']};
    color: {c['on_surface']};
}}
QDialog QLabel, QFileDialog QLabel {{
    color: {c['on_surface']};
}}
QAbstractItemView, QTreeView, QListView, QTableView {{
    background: {c['surface_high']};
    color: {c['on_surface']};
    alternate-background-color: {c['surface']};
    selection-background-color: {c['primary_container']};
    selection-color: {c['on_primary_container']};
    border: 1px solid {c['outline_variant']};
    border-radius: 8px;
    outline: none;
}}
QHeaderView::section {{
    background: {c['surface']};
    color: {c['on_variant']};
    border: none;
    border-bottom: 1px solid {c['outline_variant']};
    padding: 6px 8px;
    font-weight: 600;
}}
QSpinBox, QDoubleSpinBox {{
    background: {c['surface_high']};
    color: {c['on_surface']};
    border: 1px solid {c['outline_variant']};
    border-radius: 10px;
    padding: 5px 8px;
    min-height: 22px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {c['primary']};
}}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 0;
    border: none;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {c['outline_variant']};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {c['primary']};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {c['primary']};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}
QComboBox {{
    background: {c['surface_high']};
    color: {c['on_surface']};
    border: 1px solid {c['outline_variant']};
    border-radius: 10px;
    padding: 5px 10px;
    min-height: 22px;
}}
QComboBox:focus {{
    border: 2px solid {c['primary']};
}}
QComboBox QAbstractItemView {{
    padding: 4px;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QMenu {{
    background: {c['surface_high']};
    color: {c['on_surface']};
    border: 1px solid {c['outline_variant']};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 7px 18px;
    border-radius: 8px;
}}
QMenu::item:selected {{
    background: {c['primary_container']};
    color: {c['on_primary_container']};
}}
QMenu::item:disabled {{
    color: {c['outline']};
}}
QMenu::separator {{
    height: 1px;
    background: {c['outline_variant']};
    margin: 6px 8px;
}}
"""
