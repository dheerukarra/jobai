"""Greenhouse public board API (keyless GET). New WP1a file; caller: sources registry."""

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, Target, html_to_text
from jobai.discovery.sources.util import is_remote_text, parse_dt, trim_raw

BASE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"


def parse(data: Any, target: Target) -> list[JobPosting]:
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise FetchError(f"unexpected Greenhouse payload for {target.slug}")
    out: list[JobPosting] = []
    for j in data["jobs"]:
        if not isinstance(j, dict) or "id" not in j or not j.get("title"):
            continue
        loc = (j.get("location") or {}).get("name") if isinstance(j.get("location"), dict) else None
        url = str(j.get("absolute_url") or "")
        if not url:
            continue
        posted: datetime | None = parse_dt(j.get("first_published") or j.get("updated_at"))
        out.append(
            JobPosting(
                source="greenhouse",
                external_id=str(j["id"]),
                url=url,
                apply_url=url,
                title=str(j["title"]),
                company_name=str(j.get("company_name") or target.name),
                company_slug=target.slug,
                location=loc,
                remote=is_remote_text(loc, j.get("title")),
                posted_at=posted,
                description_text=html_to_text(j.get("content")),
                ats="greenhouse",
                raw_json=trim_raw(j, drop=("content",)),
            )
        )
    return out


class GreenhouseSource:
    name = "greenhouse"

    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch(self, target: Target) -> Iterable[JobPosting]:
        return parse(self._client.get_json(BASE.format(slug=target.slug)), target)
