"""Command line for the office dashboard: `python -m jobai.office build|serve|up`.

New project file for ticket OFF-1 (edited for OFF-2: live server and `up`). Callers:
jobai.office.__main__.
"""

from __future__ import annotations

import argparse
import time
import webbrowser
from pathlib import Path

from .render import build
from .server import DEFAULT_PORT, serve, start_detached

DEFAULT_ROOT = Path(__file__).resolve().parents[3]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m jobai.office", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    helps = {
        "build": "write dashboard/index.html once",
        "serve": "run the live server in the foreground",
        "up": "start the live server in the background if needed, then open the browser",
    }
    for name, helptext in helps.items():
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="project root")
        if name == "build":
            sp.add_argument("--out", type=Path, default=None, help="output file")
        else:
            sp.add_argument("--port", type=int, default=DEFAULT_PORT)
        if name == "up":
            sp.add_argument("--no-browser", action="store_true", help="do not open a browser")
    args = p.parse_args(argv)
    root: Path = args.root.resolve()
    if args.cmd == "build":
        start = time.perf_counter()
        path = build(root, args.out)
        print(f"wrote {path} ({path.stat().st_size} bytes, {time.perf_counter() - start:.3f}s)")
        return 0
    if args.cmd == "serve":
        return serve(root, args.port)
    url = f"http://127.0.0.1:{args.port}/"
    if not start_detached(root, args.port):
        print(f"could not start the dashboard on port {args.port} (is another program using it?)")
        return 1
    print(f"dashboard is live at {url}")
    if not args.no_browser:
        webbrowser.open(url)
    return 0
