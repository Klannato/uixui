"""Region capture through the freedesktop screenshot portal (works on Wayland).

The portal shows the desktop's own picker, so the user always chooses the region.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QObject, Slot
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage

PORTAL_SERVICE = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
SCREENSHOT_IFACE = "org.freedesktop.portal.Screenshot"
REQUEST_IFACE = "org.freedesktop.portal.Request"

_pending: list["_Responder"] = []


class _Responder(QObject):
    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    @Slot(int, "QVariantMap")
    def response(self, code: int, results: dict) -> None:
        if code != 0:
            self._finish(None, "capture cancelled" if code == 1 else "capture failed")
            return
        uri = str(results.get("uri", ""))
        parsed = urlparse(uri)
        if parsed.scheme != "file":
            self._finish(None, "portal returned no image")
            return
        self._finish(Path(unquote(parsed.path)), None)

    def _finish(self, path, error):
        if self in _pending:
            _pending.remove(self)
        self._callback(path, error)


def request_screenshot(callback) -> None:
    """Ask the portal for an interactive region capture. callback(path, error) runs on the GUI thread."""
    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        callback(None, "no D-Bus session bus available")
        return
    iface = QDBusInterface(PORTAL_SERVICE, PORTAL_PATH, SCREENSHOT_IFACE, bus)
    if not iface.isValid():
        callback(None, "screenshot portal not available; install xdg-desktop-portal and a backend")
        return
    options = {"handle_token": f"uispec{uuid.uuid4().hex[:8]}", "interactive": True}
    reply = iface.call("Screenshot", "", options)
    if reply.type() == QDBusMessage.MessageType.ErrorMessage:
        callback(None, reply.errorMessage())
        return
    handle = str(reply.arguments()[0])
    responder = _Responder(callback)
    _pending.append(responder)
    bus.connect(PORTAL_SERVICE, handle, REQUEST_IFACE, "Response", responder, "1response(uint,QVariantMap)")
