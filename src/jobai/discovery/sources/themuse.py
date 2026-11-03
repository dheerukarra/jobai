"""The Muse public jobs API (keyless, 500 req/hour unregistered). New WP1b file."""

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlencode

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, html_to_text
from jobai.discovery.sources.util import is_remote_text, parse_dt, slugify, trim_raw

BASE = "https://www.themuse.com/api/public/jobs"
PAGE_SIZE = 20
MAX_PAGES = 3
CACHE_TTL_S = 3600


def _names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(x["name"]) for x in value if isinstance(x, dict) and x.get("name")]


def parse(data: Any) -> list[JobPosting]:
    rows = data.get("results") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise FetchError("unexpected The Muse payload")
    out: list[JobPosting] = []
    for j in rows:
        if not isinstance(j, dict) or not j.get("id") or not j.get("name"):
            continue
        refs = j["refs"] if isinstance(j.get("refs"), dict) else {}
        url = str(refs.get("landing_page") or "")
        company_d = j["company"] if isinstance(j.get("company"), dict) else {}
        company = str(company_d.get("name") or "")
        if not url or not company:
            continue
        loc = "; ".join(_names(j.get("locations"))) or None
        out.append(
            JobPosting(
                source="themuse",
                external_id=str(j["id"]),
                url=url,
                apply_url=url,
                title=str(j["name"]),
                company_name=company,
                company_slug=str(company_d.get("short_name") or slugify(company)),
                location=loc,
                remote=is_remote_text(loc),
                posted_at=parse_dt(j.get("publication_date")),
                description_text=html_to_text(j.get("contents")),
                ats="themuse",
                raw_json=trim_raw(j, drop=("contents",)),
            )
        )
    return out


class MuseSource:
    name = "themuse"
    attribution = "Jobs courtesy of The Muse (themuse.com)."

    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch_all(self, limit: int) -> Iterable[JobPosting]:
        out: list[JobPosting] = []
        pages = min(MAX_PAGES, max(1, -(-limit // PAGE_SIZE)))
        for page in range(1, pages + 1):
            qs = urlencode({"page": page, "category": "Software Engineering"})
            out.extend(parse(self._client.get_json(f"{BASE}?{qs}", cache_ttl=CACHE_TTL_S)))
        return out[:limit]
