"""Local live server for the office dashboard (127.0.0.1 only, stdlib only).

New project file for ticket OFF-2 (owner request: "i need it to be updated after every change
even when task or tickets in progress"). Callers: jobai.office.cli (serve, up) and the tests.

Endpoints: GET / (fresh HTML), GET /api/state (fresh JSON, schema of
jobai.office.state.build_state), GET /api/stamp ({"stamp": token, "time": epoch}). The stamp is
a hash of path/mtime/size of every watched file plus the git HEAD/index mtimes; a background
thread rebuilds dashboard/index.html whenever it changes so the file:// copy stays current.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .activity import iter_files
from .render import build, render_html
from .state import build_state

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
REBUILD_EVERY_S = 1.0


def _git_dir(root: Path) -> Path | None:
    dot = root / ".git"
    if dot.is_dir():
        return dot
    try:
        first = dot.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    if first.startswith("gitdir:"):
        target = Path(first.split(":", 1)[1].strip())
        return target if target.is_absolute() else (root / target).resolve()
    return None


def compute_stamp(root: Path) -> str:
    """Cheap change token: changes iff a watched file or the git HEAD/index changed."""
    h = hashlib.blake2b(digest_size=12)
    for rel, mtime, size in iter_files(root):
        h.update(f"{rel}|{mtime!r}|{size}\n".encode())
    gd = _git_dir(root)
    for name in ("HEAD", "index"):
        try:
            h.update(f"git:{name}|{(gd / name).stat().st_mtime_ns}\n".encode() if gd else b"")
        except OSError:
            h.update(f"git:{name}|none\n".encode())
    return h.hexdigest()


def _handler(root: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, ctype: str, code: int = 200) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            # Reject foreign Host headers (DNS-rebinding guard); the server is localhost-only.
            port = getattr(self.server, "server_port", 0)
            if self.headers.get("Host", "") not in {f"{HOST}:{port}", f"localhost:{port}"}:
                self.send_error(403)
                return
            path = self.path.split("?")[0]
            try:
                if path in ("/", "/index.html"):
                    html = render_html(build_state(root)).encode("utf-8")
                    self._send(html, "text/html; charset=utf-8")
                elif path == "/api/state":
                    body = json.dumps(build_state(root), ensure_ascii=False).encode("utf-8")
                    self._send(body, "application/json; charset=utf-8")
                elif path == "/api/stamp":
                    payload = {"stamp": compute_stamp(root), "time": time.time()}
                    self._send(json.dumps(payload).encode(), "application/json")
                else:
                    self.send_error(404)
            except (BrokenPipeError, ConnectionResetError):
                return

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


class OfficeServer(ThreadingHTTPServer):
    daemon_threads = True


def make_server(root: Path, port: int = DEFAULT_PORT) -> OfficeServer:
    return OfficeServer((HOST, port), _handler(root))


def _rebuild_loop(root: Path, stop: threading.Event) -> None:
    last = ""
    while not stop.is_set():
        try:
            stamp = compute_stamp(root)
            if stamp != last:
                build(root)
                last = stamp
        except Exception as exc:  # keep the watcher alive whatever a half-written file does
            print(f"rebuild failed: {exc}", file=sys.stderr)
        stop.wait(REBUILD_EVERY_S)


def serve(root: Path, port: int = DEFAULT_PORT) -> int:
    server = make_server(root, port)
    stop = threading.Event()
    threading.Thread(target=_rebuild_loop, args=(root, stop), daemon=True).start()
    print(f"serving http://{HOST}:{port}/ (live: updates itself on every change; Ctrl+C stops)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
    return 0


def is_running(port: int) -> bool:
    """True if a dashboard answers on 127.0.0.1:<port>."""
    try:
        with urllib.request.urlopen(f"http://{HOST}:{port}/api/stamp", timeout=1.5) as r:
            return bool(json.load(r).get("stamp"))
    except (OSError, urllib.error.URLError, ValueError):
        return False


def port_free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex((HOST, port)) != 0


def start_detached(root: Path, port: int = DEFAULT_PORT, wait_s: float = 8.0) -> bool:
    """Start `serve` in a detached background process unless one is already up."""
    if is_running(port):
        return True
    if not port_free(port):
        return False  # something else owns the port
    kwargs: dict[str, object] = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
                                 "stderr": subprocess.DEVNULL, "cwd": str(root)}
    if os.name == "nt":
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
        kwargs["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000
    else:
        kwargs["start_new_session"] = True
    cmd = [sys.executable, "-m", "jobai.office", "serve", "--root", str(root), "--port", str(port)]
    subprocess.Popen(cmd, **kwargs)  # type: ignore[call-overload]
    deadline = time.time() + wait_s
    while time.time() < deadline:
        if is_running(port):
            return True
        time.sleep(0.25)
    return False
