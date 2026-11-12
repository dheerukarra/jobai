"""Breezy public board feed (keyless GET of the tenant's /json). WP1c file.

NOT verified live (no real tenant slug was available): registered as disabled.
Caller: sources registry.
"""

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlsplit

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, Target, html_to_text
from jobai.discovery.sources.util import join_location, parse_dt, safe_slug, trim_raw

BASE = "https://{slug}.breezy.hr/json"


def parse(data: Any, target: Target) -> list[JobPosting]:
    if not isinstance(data, list):
        raise FetchError(f"unexpected Breezy payload for {target.slug}")
    out: list[JobPosting] = []
    for j in data:
        if not isinstance(j, dict) or not j.get("name"):
            continue
        url = str(j.get("url") or "")
        if not url.startswith("https://"):
            continue
        ext = str(j.get("id") or urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1])
        loc = j["location"] if isinstance(j.get("location"), dict) else {}
        country = loc["country"] if isinstance(loc.get("country"), dict) else {}
        remote = True if loc.get("is_remote") else None
        name = loc.get("name") or join_location(loc.get("city"), loc.get("state"))
        out.append(
            JobPosting(
                source="breezy",
                external_id=ext,
                url=url,
                apply_url=url,
                title=str(j["name"]),
                company_name=target.name,
                company_slug=target.slug,
                location=join_location(name, country.get("name"), "Remote" if remote else None),
                remote=remote,
                posted_at=parse_dt(j.get("published_date")),
                description_text=html_to_text(j.get("description")),
                ats="breezy",
                raw_json=trim_raw(j, drop=("description",)),
            )
        )
    return out


class BreezySource:
    name = "breezy"

    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch(self, target: Target) -> Iterable[JobPosting]:
        slug = safe_slug(target.slug, "breezy").lower()
        return parse(self._client.get_json(BASE.format(slug=slug)), target)
