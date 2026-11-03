"""Arbeitnow job-board API (keyless). New WP1b file; caller: sources registry.

Terms: free public API, do not abuse, link back appreciated. One page (<=300 jobs) per run.
"""

from collections.abc import Iterable
from typing import Any

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, html_to_text
from jobai.discovery.sources.util import epoch_seconds, slugify, trim_raw

URL = "https://www.arbeitnow.com/api/job-board-api"
CACHE_TTL_S = 3600


def parse(data: Any) -> list[JobPosting]:
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise FetchError("unexpected Arbeitnow payload")
    out: list[JobPosting] = []
    for j in rows:
        if not isinstance(j, dict) or not j.get("slug") or not j.get("title") or not j.get("url"):
            continue
        company = str(j.get("company_name") or "Unknown")
        remote = j.get("remote")
        out.append(
            JobPosting(
                source="arbeitnow",
                external_id=str(j["slug"]),
                url=str(j["url"]),
                apply_url=str(j["url"]),
                title=str(j["title"]),
                company_name=company,
                company_slug=slugify(company),
                location=j.get("location") or None,
                remote=remote if isinstance(remote, bool) else None,
                posted_at=epoch_seconds(j.get("created_at")),
                description_text=html_to_text(j.get("description")),
                ats="arbeitnow",
                raw_json=trim_raw(j, drop=("description",)),
            )
        )
    return out


class ArbeitnowSource:
    name = "arbeitnow"
    attribution = "Jobs courtesy of Arbeitnow (arbeitnow.com); link back appreciated."

    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch_all(self, limit: int) -> Iterable[JobPosting]:
        return parse(self._client.get_json(URL, cache_ttl=CACHE_TTL_S))[:limit]
