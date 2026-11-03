"""Ashby public job-board API (keyless GET). New WP1a file; caller: sources registry."""

from collections.abc import Iterable
from typing import Any

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, Target, html_to_text
from jobai.discovery.sources.util import is_remote_text, parse_dt, trim_raw

BASE = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


def parse(data: Any, target: Target) -> list[JobPosting]:
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise FetchError(f"unexpected Ashby payload for {target.slug}")
    out: list[JobPosting] = []
    for j in data["jobs"]:
        if not isinstance(j, dict) or not j.get("id") or not j.get("title"):
            continue
        if j.get("isListed") is False:
            continue
        url = str(j.get("jobUrl") or "")
        if not url:
            continue
        loc = j.get("location") or None
        remote = j.get("isRemote")
        if not isinstance(remote, bool):
            remote = is_remote_text(loc)
        desc = j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml"))
        out.append(
            JobPosting(
                source="ashby",
                external_id=str(j["id"]),
                url=url,
                apply_url=str(j.get("applyUrl") or url),
                title=str(j["title"]),
                company_name=target.name,
                company_slug=target.slug,
                location=loc,
                remote=remote,
                posted_at=parse_dt(j.get("publishedAt")),
                description_text=str(desc).strip(),
                ats="ashby",
                raw_json=trim_raw(j, drop=("descriptionHtml", "descriptionPlain")),
            )
        )
    return out


class AshbySource:
    name = "ashby"

    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch(self, target: Target) -> Iterable[JobPosting]:
        return parse(self._client.get_json(BASE.format(slug=target.slug)), target)
