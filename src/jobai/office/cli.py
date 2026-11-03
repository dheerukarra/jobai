"""Command line for the office dashboard: `python -m jobai.office build|serve`.

New project file for ticket OFF-1. Callers: jobai.office.__main__.
"""

from __future__ import annotations

import argparse
import contextlib
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .render import build

DEFAULT_ROOT = Path(__file__).resolve().parents[3]


def _handler(root: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.split("?")[0] not in ("/", "/index.html"):
                self.send_error(404)
                return
            body = build(root).read_bytes()  # rebuild on every request
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m jobai.office", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, helptext in (("build", "write dashboard/index.html"), ("serve", "serve it locally")):
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="project root")
        if name == "build":
            sp.add_argument("--out", type=Path, default=None, help="output file")
        else:
            sp.add_argument("--port", type=int, default=8765)
    args = p.parse_args(argv)
    root: Path = args.root.resolve()
    if args.cmd == "build":
        start = time.perf_counter()
        path = build(root, args.out)
        print(f"wrote {path} ({path.stat().st_size} bytes, {time.perf_counter() - start:.3f}s)")
        return 0
    server = HTTPServer(("127.0.0.1", args.port), _handler(root))
    print(f"serving http://127.0.0.1:{args.port}/ (rebuilds on each request; Ctrl+C to stop)")
    with contextlib.suppress(KeyboardInterrupt):
        server.serve_forever()
    return 0
