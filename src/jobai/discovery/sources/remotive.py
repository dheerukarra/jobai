"""Remotive public API (keyless). New WP1b file; caller: sources registry.

Terms (from the API's own legal notice): link back to the Remotive URL and name Remotive as the
source; max ~4 fetches per day. We keep the Remotive URL as the posting url and cache 6 hours.
"""

from collections.abc import Iterable
from typing import Any

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, html_to_text
from jobai.discovery.sources.util import parse_dt, slugify, trim_raw

URL = "https://remotive.com/api/remote-jobs?limit={limit}"
CACHE_TTL_S = 6 * 3600


def parse(data: Any) -> list[JobPosting]:
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list):
        raise FetchError("unexpected Remotive payload")
    out: list[JobPosting] = []
    for j in jobs:
        if not isinstance(j, dict) or not j.get("id") or not j.get("title") or not j.get("url"):
            continue
        company = str(j.get("company_name") or "Unknown")
        out.append(
            JobPosting(
                source="remotive",
                external_id=str(j["id"]),
                url=str(j["url"]),
                apply_url=str(j["url"]),
                title=str(j["title"]),
                company_name=company,
                company_slug=slugify(company),
                location=j.get("candidate_required_location") or None,
                remote=True,
                posted_at=parse_dt(j.get("publication_date")),
                description_text=html_to_text(j.get("description")),
                ats="remotive",
                raw_json=trim_raw(j, drop=("description", "company_logo")),
            )
        )
    return out


class RemotiveSource:
    name = "remotive"
    attribution = "Jobs courtesy of Remotive (remotive.com); link back required."

    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch_all(self, limit: int) -> Iterable[JobPosting]:
        data = self._client.get_json(URL.format(limit=limit), cache_ttl=CACHE_TTL_S)
        return parse(data)[:limit]
