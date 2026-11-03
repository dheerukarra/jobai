"""One call that returns everything the dashboard shows: parsed docs plus live activity.

New project file for ticket OFF-2. Callers: jobai.office.render.build and jobai.office.server.
Data schema: the dict from jobai.office.parser.parse_office plus key "activity" (see
jobai.office.activity).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .activity import build_activity
from .parser import parse_office


def build_state(root: Path) -> dict[str, Any]:
    now = datetime.now(UTC)
    data = parse_office(root, now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    data["activity"] = build_activity(root, data["cards"], data["live"], now.timestamp())
    return data
