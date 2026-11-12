"""Workable public widget API (keyless GET, whole board in one request). WP1c file.

Callers: sources registry. Endpoint shape learned from a MIT-licensed reference project
and re-verified live 2026-11-12; re-implemented here. Goal: WP1c more ATS sources.
"""

from collections.abc import Iterable
from typing import Any

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, Target, html_to_text
from jobai.discovery.sources.util import join_location, parse_dt, safe_slug, trim_raw

BASE = "https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true"


def parse(data: Any, target: Target) -> list[JobPosting]:
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise FetchError(f"unexpected Workable payload for {target.slug}")
    out: list[JobPosting] = []
    for j in data["jobs"]:
        if not isinstance(j, dict) or not j.get("shortcode") or not j.get("title"):
            continue
        url = str(j.get("shortlink") or j.get("url") or "")
        if not url.startswith("https://"):
            continue
        tele = j.get("telecommuting")
        out.append(
            JobPosting(
                source="workable",
                external_id=str(j["shortcode"]),
                url=url,
                apply_url=str(j.get("application_url") or url),
                title=str(j["title"]),
                company_name=target.name,
                company_slug=target.slug,
                location=join_location(j.get("city"), j.get("state"), j.get("country")),
                remote=True if tele in (True, "true", "True", 1) else None,
                posted_at=parse_dt(j.get("published_on") or j.get("created_at")),
                description_text=html_to_text(j.get("description")),
                ats="workable",
                raw_json=trim_raw(j, drop=("description", "locations")),
            )
        )
    return out


class WorkableSource:
    name = "workable"

    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch(self, target: Target) -> Iterable[JobPosting]:
        slug = safe_slug(target.slug, "workable")
        return parse(self._client.get_json(BASE.format(slug=slug)), target)
