"""Remote OK public API (keyless). New WP1b file; caller: sources registry.

Terms (first element of the feed): link back to the Remote OK URL with follow, and mention
Remote OK as the source. We keep their url as the posting url. Cached 1 hour.
"""

from collections.abc import Iterable
from typing import Any

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, html_to_text
from jobai.discovery.sources.util import parse_dt, slugify, trim_raw

URL = "https://remoteok.com/api"
CACHE_TTL_S = 3600


def parse(data: Any) -> list[JobPosting]:
    if not isinstance(data, list):
        raise FetchError("unexpected Remote OK payload")
    out: list[JobPosting] = []
    for j in data:
        # element 0 is the legal notice (no id/position)
        if not isinstance(j, dict) or not j.get("id") or not j.get("position"):
            continue
        url = str(j.get("url") or j.get("apply_url") or "")
        if not url:
            continue
        company = str(j.get("company") or "Unknown")
        out.append(
            JobPosting(
                source="remoteok",
                external_id=str(j["id"]),
                url=url,
                apply_url=str(j.get("apply_url") or url),
                title=str(j["position"]),
                company_name=company,
                company_slug=slugify(company),
                location=j.get("location") or None,
                remote=True,
                posted_at=parse_dt(j.get("date")),
                description_text=html_to_text(j.get("description")),
                ats="remoteok",
                raw_json=trim_raw(j, drop=("description", "logo", "company_logo")),
            )
        )
    return out


class RemoteOkSource:
    name = "remoteok"
    attribution = "Jobs courtesy of Remote OK (remoteok.com); link back required."

    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch_all(self, limit: int) -> Iterable[JobPosting]:
        return parse(self._client.get_json(URL, cache_ttl=CACHE_TTL_S))[:limit]
