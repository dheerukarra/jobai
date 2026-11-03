"""Assemble the single-file dashboard (inline CSS + JS + JSON data). Stdlib only.

New project file for ticket OFF-1 (edited for OFF-2). Callers: jobai.office.cli and
jobai.office.server. Data schema: the dict from jobai.office.state.build_state.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .state import build_state

TEMPLATES = Path(__file__).parent / "templates"
# Concatenated into ONE script closure (app.js opens it, live.js closes it).
JS_PARTS = ("app.js", "views.js", "live.js")


def _safe_json(data: dict[str, Any]) -> str:
    """JSON safe to embed inside a <script> element."""
    return (
        json.dumps(data, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )


def render_html(data: dict[str, Any]) -> str:
    html = (TEMPLATES / "index.html").read_text(encoding="utf-8")
    css = (TEMPLATES / "style.css").read_text(encoding="utf-8")
    js = "\n".join((TEMPLATES / n).read_text(encoding="utf-8") for n in JS_PARTS)
    title = f"{data.get('project', 'Project')} dashboard"
    # Order matters: the data goes in last so user text can never be re-substituted.
    html = html.replace("/*__CSS__*/", css).replace("/*__JS__*/", js)
    html = html.replace("__TITLE__", title)
    return html.replace("__DATA__", _safe_json(data))


def build(root: Path, out: Path | None = None) -> Path:
    """Parse the project under root and write dashboard/index.html atomically. Returns the path."""
    target = out or root / "dashboard" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(render_html(build_state(root)), encoding="utf-8")
    os.replace(tmp, target)
    return target
