"""Assemble the single-file dashboard (inline CSS + JS + JSON data). Stdlib only.

New project file for ticket OFF-1. Callers: jobai.office.cli. Data schema: the dict from
jobai.office.parser.parse_office.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .parser import parse_office

TEMPLATES = Path(__file__).parent / "templates"


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
    js = (TEMPLATES / "app.js").read_text(encoding="utf-8")
    title = f"{data.get('project', 'Project')} dashboard"
    # Order matters: the data goes in last so user text can never be re-substituted.
    html = html.replace("/*__CSS__*/", css).replace("/*__JS__*/", js)
    html = html.replace("__TITLE__", title)
    return html.replace("__DATA__", _safe_json(data))


def build(root: Path, out: Path | None = None) -> Path:
    """Parse docs/office under root and write dashboard/index.html. Returns the path."""
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = parse_office(root, stamp)
    target = out or root / "dashboard" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_html(data), encoding="utf-8")
    return target
