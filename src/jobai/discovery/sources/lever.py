"""Lever public postings API (keyless GET). New WP1a file; caller: sources registry."""

from collections.abc import Iterable
from typing import Any

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, Target, html_to_text
from jobai.discovery.sources.util import is_remote_text, parse_dt, trim_raw

BASE = "https://api.lever.co/v0/postings/{slug}?mode=json"


def parse(data: Any, target: Target) -> list[JobPosting]:
    if not isinstance(data, list):
        raise FetchError(f"unexpected Lever payload for {target.slug}")
    out: list[JobPosting] = []
    for j in data:
        if not isinstance(j, dict) or not j.get("id") or not j.get("text"):
            continue
        url = str(j.get("hostedUrl") or "")
        if not url:
            continue
        cats: dict[str, Any] = j["categories"] if isinstance(j.get("categories"), dict) else {}
        loc = cats.get("location") or None
        wt = str(j.get("workplaceType") or "").lower()
        remote = True if wt == "remote" else (False if wt in ("on-site", "hybrid") else None)
        if remote is None:
            remote = is_remote_text(loc)
        desc = j.get("descriptionPlain") or html_to_text(j.get("description"))
        out.append(
            JobPosting(
                source="lever",
                external_id=str(j["id"]),
                url=url,
                apply_url=str(j.get("applyUrl") or url),
                title=str(j["text"]),
                company_name=target.name,
                company_slug=target.slug,
                location=loc,
                remote=remote,
                posted_at=parse_dt(j.get("createdAt")),
                description_text=str(desc).strip(),
                ats="lever",
                raw_json=trim_raw(
                    j, drop=("description", "descriptionPlain", "lists", "additional")
                ),
            )
        )
    return out


class LeverSource:
    name = "lever"

    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch(self, target: Target) -> Iterable[JobPosting]:
        return parse(self._client.get_json(BASE.format(slug=target.slug)), target)
