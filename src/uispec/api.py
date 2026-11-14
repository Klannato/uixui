"""Localhost JSON API the running app exposes. The CLI and agents use it through the `uispec` command."""

from __future__ import annotations

import json
import os
import queue
import secrets
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from . import store
from .commands import dispatch
from .controller import Controller

REQUEST_TIMEOUT = 120


def api_file() -> Path:
    return store.state_dir() / "api.json"


class Bridge(QObject):
    """Moves API requests from the HTTP threads onto the GUI thread."""

    request = Signal(object)

    def __init__(self, ctrl: Controller, parent: QObject | None = None):
        super().__init__(parent)
        self.ctrl = ctrl
        self.request.connect(self._handle)

    @Slot(object)
    def _handle(self, req) -> None:
        name, args, box = req

        def reply(result=None, error=None):
            box.put({"result": result} if error is None else {"error": error})

        dispatch(self.ctrl, name, args, reply)


class _Handler(BaseHTTPRequestHandler):
    bridge: Bridge
    token: str

    def log_message(self, format, *args):  # keep the app's output quiet
        pass

    def _send(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.headers.get("X-Token") != self.token:
            self._send(401, {"error": "bad token"})
            return
        if not self.path.startswith("/api/"):
            self._send(404, {"error": "not found"})
            return
        name = self.path[len("/api/"):]
        length = int(self.headers.get("Content-Length", 0))
        try:
            args = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "body must be JSON"})
            return
        box: queue.Queue = queue.Queue(maxsize=1)
        self.bridge.request.emit((name, args, box))
        try:
            answer = box.get(timeout=REQUEST_TIMEOUT)
        except queue.Empty:
            self._send(504, {"error": "app did not answer in time"})
            return
        self._send(400 if "error" in answer else 200, answer)


def start_server(ctrl: Controller) -> tuple[ThreadingHTTPServer, Bridge]:
    bridge = Bridge(ctrl)
    token = secrets.token_urlsafe(24)

    class Handler(_Handler):
        pass

    Handler.bridge = bridge
    Handler.token = token
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()

    path = api_file()
    if path.exists():
        path.unlink()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"port": server.server_address[1], "token": token, "pid": os.getpid()}, f)
    return server, bridge


def stop_server(server: ThreadingHTTPServer) -> None:
    server.shutdown()
    server.server_close()
    if api_file().exists():
        api_file().unlink()


class AppUnreachable(Exception):
    pass


def read_api_file() -> dict | None:
    path = api_file()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def call(name: str, args: dict | None = None, timeout: float = REQUEST_TIMEOUT + 5) -> dict:
    info = read_api_file()
    if info is None:
        raise AppUnreachable("app is not running")
    req = urllib.request.Request(
        f"http://127.0.0.1:{info['port']}/api/{name}",
        data=json.dumps(args or {}).encode(),
        headers={"Content-Type": "application/json", "X-Token": info["token"]},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read() or b"{}")
    except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
        raise AppUnreachable(str(exc)) from exc
