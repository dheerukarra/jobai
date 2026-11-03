"""freehire public API (keyless, personal use, IT jobs). New WP1b file; caller: registry.

Per its OpenAPI (github.com/strelov1/freehire web/static/openapi.yaml): base
https://freehire.me/api/v1, GET /jobs/search, 120 req/min and 2000/day per address, 429 carries
Retry-After (honoured by PoliteClient). Keyless use is personal/non-commercial only. Cached 1h.
"""

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlencode

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, html_to_text
from jobai.discovery.sources.util import is_remote_text, parse_dt, slugify, trim_raw

BASE = "https://freehire.me/api/v1/jobs/search"
MAX_PER_REQUEST = 50
CACHE_TTL_S = 3600


def parse(data: Any) -> list[JobPosting]:
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise FetchError("unexpected freehire payload")
    out: list[JobPosting] = []
    for j in rows:
        if not isinstance(j, dict):
            continue
        slug, url, title = j.get("public_slug"), j.get("url"), j.get("title")
        if not slug or not url or not title:
            continue
        company = str(j.get("company") or "Unknown")
        loc = j.get("location") or None
        out.append(
            JobPosting(
                source="freehire",
                external_id=str(slug),
                url=str(url),
                apply_url=str(url),
                title=str(title),
                company_name=company,
                company_slug=str(j.get("company_slug") or slugify(company)),
                location=loc,
                remote=is_remote_text(loc),
                posted_at=parse_dt(j.get("posted_at")),
                description_text=html_to_text(j.get("description")),
                ats="freehire",
                raw_json=trim_raw(
                    j, drop=("description", "enrichment", "reality", "perks", "collections")
                ),
            )
        )
    return out


class FreehireSource:
    name = "freehire"
    attribution = "Jobs via freehire.me public API (personal, non-commercial use)."

    def __init__(self, client: PoliteClient, query: str | None = None) -> None:
        self._client = client
        self._query = query

    def fetch_all(self, limit: int) -> Iterable[JobPosting]:
        params: dict[str, str | int] = {"limit": min(max(limit, 1), MAX_PER_REQUEST)}
        if self._query:
            params["q"] = self._query
        data = self._client.get_json(f"{BASE}?{urlencode(params)}", cache_ttl=CACHE_TTL_S)
        return parse(data)[:limit]
