"""Discovery data model and the pluggable Source protocol (WP1a)."""

import html
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, field_validator

_TAG = re.compile(r"<[^>]+>")
_BLOCK = re.compile(r"</?(p|div|br|li|ul|ol|h[1-6]|tr)[^>]*>", re.I)
_WS = re.compile(r"[ \t\r\f\v]+")
_NL = re.compile(r"\n\s*\n+")
RAW_MAX_CHARS = 20_000


def html_to_text(value: str | None) -> str:
    """Strip HTML (also entity-escaped HTML as Greenhouse returns) to plain text."""
    if not value:
        return ""
    text = value
    for _ in range(2):  # Greenhouse content is HTML escaped once: unescape, then strip
        text = html.unescape(text)
        text = _BLOCK.sub("\n", text)
        text = _TAG.sub("", text)
    text = _WS.sub(" ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return _NL.sub("\n\n", text).strip()


class JobPosting(BaseModel):
    source: str
    external_id: str
    url: str
    apply_url: str | None = None
    title: str
    company_name: str
    company_slug: str
    location: str | None = None
    remote: bool | None = None
    posted_at: datetime | None = None
    description_text: str = ""
    ats: str
    raw_json: dict[str, Any] | None = None

    @field_validator("title", "company_name", "location", mode="before")
    @classmethod
    def _strip(cls, v: Any) -> Any:
        return v.strip() if isinstance(v, str) else v


class FetchError(RuntimeError):
    """A board could not be fetched (HTTP error, bad JSON). Message is safe to print."""


class Target(BaseModel):
    """One company board to fetch."""

    name: str
    ats: str
    slug: str


class Source(Protocol):
    name: str

    def fetch(self, target: Target) -> Iterable[JobPosting]: ...


class Aggregator(Protocol):
    """A feed-style source (no per-company target): returns up to `limit` postings (WP1b)."""

    name: str

    def fetch_all(self, limit: int) -> Iterable[JobPosting]: ...
