"""Small parsing helpers shared by ATS adapters (new WP1a file)."""

from datetime import UTC, datetime
from typing import Any

from jobai.discovery.models import RAW_MAX_CHARS


def parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, int | float):  # epoch milliseconds (Lever)
            return datetime.fromtimestamp(value / 1000, tz=UTC)
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (ValueError, OverflowError, OSError):
        return None


def is_remote_text(*parts: Any) -> bool | None:
    """True when text says remote; None (unknown) otherwise. Never guesses False."""
    text = " ".join(str(p) for p in parts if p).lower()
    return True if "remote" in text else None


def trim_raw(job: dict[str, Any], drop: tuple[str, ...] = ()) -> dict[str, Any]:
    """Keep the structured metadata, drop bulky description bodies, cap total size."""
    kept = {k: v for k, v in job.items() if k not in drop}
    import json

    if len(json.dumps(kept, default=str)) > RAW_MAX_CHARS:
        return {"id": job.get("id"), "trimmed": True}
    return kept


def slugify(text: str) -> str:
    """Lowercase ascii slug for company names (WP1b)."""
    import re
    import unicodedata

    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-") or "unknown"


def epoch_seconds(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OverflowError, OSError):
        return None
