"""BambooHR public careers list (keyless GET). WP1c file; caller: sources registry.

NOT verified live (no real tenant slug was available): registered as disabled.
The list carries no description or date.
"""

from collections.abc import Iterable
from typing import Any

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, Target
from jobai.discovery.sources.util import join_location, safe_slug, trim_raw

BASE = "https://{slug}.bamboohr.com/careers/list"


def parse(data: Any, target: Target) -> list[JobPosting]:
    if not isinstance(data, dict) or not isinstance(data.get("result"), list):
        raise FetchError(f"unexpected BambooHR payload for {target.slug}")
    out: list[JobPosting] = []
    for j in data["result"]:
        if not isinstance(j, dict) or not str(j.get("id") or "").strip():
            continue
        if not j.get("jobOpeningName"):
            continue
        ext = str(j["id"]).strip()
        loc = j["location"] if isinstance(j.get("location"), dict) else {}
        remote = True if j.get("isRemote") in (True, 1, "1") else None
        url = f"https://{target.slug.lower()}.bamboohr.com/careers/{ext}"
        out.append(
            JobPosting(
                source="bamboohr",
                external_id=ext,
                url=url,
                apply_url=url,
                title=str(j["jobOpeningName"]),
                company_name=target.name,
                company_slug=target.slug,
                location=join_location(
                    loc.get("city"), loc.get("state"), "Remote" if remote else None
                ),
                remote=remote,
                posted_at=None,
                description_text="",
                ats="bamboohr",
                raw_json=trim_raw(j),
            )
        )
    return out


class BambooHrSource:
    name = "bamboohr"

    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch(self, target: Target) -> Iterable[JobPosting]:
        slug = safe_slug(target.slug, "bamboohr").lower()
        return parse(self._client.get_json(BASE.format(slug=slug)), target)
