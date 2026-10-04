"""Loopback HTTP server for the browser GUI. Standard library only."""

from __future__ import annotations

import base64
import json
import platform
import secrets
import subprocess
import threading
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import cv2
import numpy as np

from .detect import Box, Detection, detect_file
from .pipeline import IMAGE_EXTENSIONS, Result, export_detection, find_images, process
from .render import LAYOUTS, render_all

STATIC = Path(__file__).resolve().parent.parent.parent / "static"
STATIC_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}
PREVIEW_WIDTH = 1600
THUMB_WIDTH = 216
MAX_SESSIONS = 4  # each holds a full-resolution page in memory


class Session:
    def __init__(self, source: Path, detection: Detection):
        self.id = secrets.token_hex(8)
        self.source = source
        self.detection = detection
        scale = PREVIEW_WIDTH / detection.render_image.shape[1]
        small = cv2.resize(detection.render_image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        self.preview = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 80])[1].tobytes()

    def payload(self) -> dict:
        h, w = self.detection.render_image.shape[:2]
        return {"status": "review", "name": self.source.name, "path": str(self.source), "id": self.id,
                "w": w, "h": h, "boxes": [b.as_dict() for b in self.detection.boxes],
                "panels": len(self.detection.boxes), "reasons": self.detection.reasons,
                "angle": round(self.detection.angle, 2), "layouts": list(LAYOUTS)}


def exported_payload(result: Result) -> dict:
    return {"status": "exported", "name": result.source.name, "path": str(result.source),
            "panels": result.panel_count, "dir": str(result.exported), "dir_name": result.exported.name,
            "files": [f.name for f in result.files], "layout": result.layout, "reasons": result.detection.reasons}


# ---------------------------------------------------------------- native file picker

def pick_files() -> list[str]:
    system = platform.system()
    if system == "Darwin":
        script = ('set chosen to choose file of type {"public.image"} with prompt "Choose scanned comics" '
                  'with multiple selections allowed\nset out to ""\nrepeat with f in chosen\n'
                  'set out to out & POSIX path of f & linefeed\nend repeat\nreturn out')
        run = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    elif system == "Windows":
        script = ("Add-Type -AssemblyName System.Windows.Forms; $d = New-Object System.Windows.Forms.OpenFileDialog; "
                  "$d.Multiselect = $true; $d.Title = 'Choose scanned comics'; "
                  "$d.Filter = 'Images|*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.webp'; "
                  "if ($d.ShowDialog() -eq 'OK') { $d.FileNames }")
        run = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", script], capture_output=True, text=True)
    else:
        run = subprocess.run(["zenity", "--file-selection", "--multiple", "--separator=\n",
                              "--title=Choose scanned comics",
                              "--file-filter=Images | *.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp"],
                             capture_output=True, text=True)
    return [line for line in run.stdout.splitlines() if line.strip()]  # cancel = nothing chosen


def pick_folder() -> str:
    system = platform.system()
    if system == "Darwin":
        run = subprocess.run(["osascript", "-e", 'POSIX path of (choose folder with prompt "Choose a folder of scans")'],
                             capture_output=True, text=True)
    elif system == "Windows":
        script = ("Add-Type -AssemblyName System.Windows.Forms; $d = New-Object System.Windows.Forms.FolderBrowserDialog; "
                  "$d.Description = 'Choose a folder of scans'; if ($d.ShowDialog() -eq 'OK') { $d.SelectedPath }")
        run = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", script], capture_output=True, text=True)
    else:
        run = subprocess.run(["zenity", "--file-selection", "--directory", "--title=Choose a folder of scans"],
                             capture_output=True, text=True)
    return run.stdout.strip()  # cancel = empty


def reveal(folder: Path) -> None:
    system = platform.system()
    command = ["open", str(folder)] if system == "Darwin" else ["explorer", str(folder)] if system == "Windows" else ["xdg-open", str(folder)]
    subprocess.Popen(command)


# ---------------------------------------------------------------- validation

def image_path(value) -> Path:
    path = Path(str(value)).expanduser()
    if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError("That is not an image file I can open.")
    return path


def parent_dir(value) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text).expanduser()
    if not path.is_dir():
        raise ValueError(f"That folder does not exist: {text}")
    return path


def boxes_from(value, width: int, height: int) -> list[Box]:
    if not isinstance(value, list) or len(value) > 20:
        raise ValueError("Boxes must be a list of at most 20 rectangles.")
    boxes = []
    for item in value:
        x, y = int(item["x"]), int(item["y"])
        w, h = int(item["w"]), int(item["h"])
        x0, y0 = max(0, min(x, width - 1)), max(0, min(y, height - 1))
        x1, y1 = max(x0 + 1, min(x + w, width)), max(y0 + 1, min(y + h, height))
        boxes.append(Box(x0, y0, x1 - x0, y1 - y0))
    return boxes


def layout_from(value) -> str:
    return value if value in LAYOUTS else "auto"


def thumbnail(canvas: np.ndarray) -> str:
    scale = THUMB_WIDTH / canvas.shape[1]
    small = cv2.resize(canvas, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    data = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")


# ---------------------------------------------------------------- app

class App:
    def __init__(self):
        self.token = secrets.token_urlsafe(24)
        self.sessions: OrderedDict[str, Session] = OrderedDict()
        self.lock = threading.Lock()
        self.server: ThreadingHTTPServer | None = None

    def remember(self, session: Session) -> Session:
        with self.lock:
            self.sessions[session.id] = session
            while len(self.sessions) > MAX_SESSIONS:
                self.sessions.popitem(last=False)
        return session

    def session(self, session_id) -> Session:
        with self.lock:
            session = self.sessions.get(str(session_id))
        if session is None:
            raise ValueError("That scan is no longer loaded. Open it again.")
        return session

    # --- actions
    def act_pick(self, _body: dict) -> dict:
        return {"paths": pick_files()}

    def act_pick_folder(self, _body: dict) -> dict:
        folder = pick_folder()
        if not folder:
            return {"folder": "", "paths": []}
        return {"folder": folder, "paths": [str(p) for p in find_images(folder)]}

    def act_process(self, body: dict) -> dict:
        source = image_path(body.get("path"))
        parent = parent_dir(body.get("parent"))
        if body.get("review"):
            return self.remember(Session(source, detect_file(source))).payload()
        result = process(source, parent, export_when_unsure=False)
        if result.exported:
            return exported_payload(result)
        return self.remember(Session(source, result.detection)).payload()

    def act_render(self, body: dict) -> dict:
        session = self.session(body.get("id"))
        h, w = session.detection.render_image.shape[:2]
        boxes = boxes_from(body.get("boxes", []), w, h)
        panels, summary, chosen = render_all(session.detection.render_image, boxes, layout_from(body.get("layout")))
        return {"panels": [thumbnail(p) for p in panels], "summary": thumbnail(summary), "layout": chosen}

    def act_export(self, body: dict) -> dict:
        session = self.session(body.get("id"))
        h, w = session.detection.render_image.shape[:2]
        boxes = boxes_from(body.get("boxes", []), w, h)
        if not boxes:
            raise ValueError("There are no boxes to export.")
        result = export_detection(session.source, session.detection, boxes,
                                  parent_dir(body.get("parent")), layout_from(body.get("layout")))
        session.detection.boxes = boxes
        return exported_payload(result)

    def act_reveal(self, body: dict) -> dict:
        folder = Path(str(body.get("dir", ""))).expanduser()
        if not folder.is_dir():
            raise ValueError("That folder does not exist any more.")
        reveal(folder)
        return {"ok": True}

    def act_quit(self, _body: dict) -> dict:
        threading.Thread(target=self.server.shutdown, daemon=True).start()
        return {"ok": True}


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quiet; the launcher captures stdout anyway
            pass

        def send_json(self, status: int, payload: dict) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def send_bytes(self, data: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                page = (STATIC / "index.html").read_text(encoding="utf-8").replace("{{TOKEN}}", app.token)
                return self.send_bytes(page.encode("utf-8"), STATIC_TYPES[".html"])
            if path == "/health/ready":
                return self.send_json(200, {"ok": True})
            if path.startswith("/static/"):
                name = Path(path).name
                target = STATIC / name
                if name in STATIC_TYPES or target.suffix not in STATIC_TYPES or not target.is_file():
                    return self.send_json(404, {"error": "not found"})
                return self.send_bytes(target.read_bytes(), STATIC_TYPES[target.suffix])
            if path.startswith("/api/preview/"):
                try:
                    session = app.session(Path(path).stem)
                except ValueError as error:
                    return self.send_json(404, {"error": str(error)})
                return self.send_bytes(session.preview, "image/jpeg")
            self.send_json(404, {"error": "not found"})

        def do_POST(self):
            path = urlparse(self.path).path
            if self.headers.get("X-Token") != app.token:
                return self.send_json(403, {"error": "missing or wrong session token"})
            action = getattr(app, "act_" + path.removeprefix("/api/"), None) if path.startswith("/api/") else None
            if action is None:
                return self.send_json(404, {"error": "not found"})
            try:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("Expected a JSON object.")
                self.send_json(200, action(body))
            except (ValueError, KeyError, TypeError) as error:
                self.send_json(400, {"error": str(error)})
            except Exception as error:  # surface, never hide, but sanitized
                self.send_json(500, {"error": f"{type(error).__name__}: {error}"})

    return Handler


def serve(host: str, preferred_port: int) -> tuple[App, ThreadingHTTPServer]:
    app = App()
    handler = make_handler(app)
    try:
        server = ThreadingHTTPServer((host, preferred_port), handler)
    except OSError:
        server = ThreadingHTTPServer((host, 0), handler)  # preferred port taken: let the OS choose
    app.server = server
    return app, server
