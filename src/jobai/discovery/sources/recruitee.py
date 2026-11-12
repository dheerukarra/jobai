"""Recruitee public per-tenant offers API (keyless GET). WP1c file; caller: sources registry."""

import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, Target, html_to_text
from jobai.discovery.sources.util import is_remote_text, parse_dt, safe_slug, trim_raw

BASE = "https://{slug}.recruitee.com/api/offers/"
_SAMPLE = re.compile(r"\(sample\)\s*$", re.I)  # demo postings stamped by the platform itself


def _dt(value: Any) -> datetime | None:
    """Recruitee stamps '2026-11-03 20:08:14 UTC'."""
    if isinstance(value, str) and value.endswith(" UTC"):
        value = value[:-4].replace(" ", "T") + "+00:00"
    return parse_dt(value)


def parse(data: Any, target: Target) -> list[JobPosting]:
    if not isinstance(data, dict) or not isinstance(data.get("offers"), list):
        raise FetchError(f"unexpected Recruitee payload for {target.slug}")
    out: list[JobPosting] = []
    for j in data["offers"]:
        if not isinstance(j, dict) or j.get("id") is None or not j.get("title"):
            continue
        if j.get("status") not in (None, "published") or _SAMPLE.search(str(j["title"])):
            continue
        url = str(j.get("careers_url") or "")
        if not url.startswith("https://"):
            continue
        loc = j.get("location") or None
        if j.get("remote") is True:
            remote: bool | None = True
        elif j.get("on_site") is True:
            remote = False
        else:
            remote = is_remote_text(loc)
        body = "\n".join(str(j.get(k) or "") for k in ("description", "requirements"))
        out.append(
            JobPosting(
                source="recruitee",
                external_id=str(j["id"]),
                url=url,
                apply_url=str(j.get("careers_apply_url") or url),
                title=str(j["title"]),
                company_name=str(j.get("company_name") or target.name),
                company_slug=target.slug,
                location=loc,
                remote=remote,
                posted_at=_dt(j.get("published_at") or j.get("created_at")),
                description_text=html_to_text(body),
                ats="recruitee",
                raw_json=trim_raw(
                    j, drop=("description", "requirements", "translations", "open_questions")
                ),
            )
        )
    return out


class RecruiteeSource:
    name = "recruitee"

    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch(self, target: Target) -> Iterable[JobPosting]:
        slug = safe_slug(target.slug, "recruitee").lower()
        return parse(self._client.get_json(BASE.format(slug=slug)), target)
