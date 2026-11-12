"""SmartRecruiters public postings API (keyless GET, paginated). WP1c file.

The list payload carries no description body; one detail call per posting would multiply
requests, so descriptions stay empty here. Caller: sources registry.
"""

from collections.abc import Iterable
from typing import Any

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, Target
from jobai.discovery.sources.util import join_location, parse_dt, safe_slug, slugify, trim_raw

BASE = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"
PAGE_SIZE = 100
MAX_PAGES = 10  # 1000 postings per board per run


def parse(data: Any, target: Target) -> list[JobPosting]:
    if not isinstance(data, dict) or not isinstance(data.get("content"), list):
        raise FetchError(f"unexpected SmartRecruiters payload for {target.slug}")
    out: list[JobPosting] = []
    for j in data["content"]:
        if not isinstance(j, dict) or not j.get("id") or not j.get("name"):
            continue
        comp = j["company"] if isinstance(j.get("company"), dict) else {}
        ident = str(comp.get("identifier") or target.slug)
        url = f"https://jobs.smartrecruiters.com/{ident}/{j['id']}-{slugify(str(j['name']))}"
        loc = j["location"] if isinstance(j.get("location"), dict) else {}
        location = loc.get("fullLocation") or join_location(
            loc.get("city"), loc.get("region"), str(loc.get("country") or "").upper() or None
        )
        out.append(
            JobPosting(
                source="smartrecruiters",
                external_id=str(j["id"]),
                url=url,
                apply_url=url,
                title=str(j["name"]),
                company_name=str(comp.get("name") or target.name),
                company_slug=target.slug,
                location=location,
                remote=True if loc.get("remote") is True else None,
                posted_at=parse_dt(j.get("releasedDate")),
                description_text="",
                ats="smartrecruiters",
                raw_json=trim_raw(j, drop=("customField",)),
            )
        )
    return out


class SmartRecruitersSource:
    name = "smartrecruiters"

    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch(self, target: Target) -> Iterable[JobPosting]:
        slug = safe_slug(target.slug, "smartrecruiters")
        out: list[JobPosting] = []
        for page in range(MAX_PAGES):
            offset = page * PAGE_SIZE
            data = self._client.get_json(
                f"{BASE.format(slug=slug)}?limit={PAGE_SIZE}&offset={offset}&status=PUBLIC"
            )
            out.extend(parse(data, target))
            total = data.get("totalFound")
            if len(data["content"]) < PAGE_SIZE or (
                isinstance(total, int) and offset + PAGE_SIZE >= total
            ):
                break
        return out
