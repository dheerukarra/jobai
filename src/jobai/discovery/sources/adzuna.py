"""Adzuna API (needs a free key; NOT enabled until ADZUNA_APP_ID/ADZUNA_APP_KEY are set).

New WP1b file; caller: sources registry. Not exercised live: the owner has no keys yet.
The key is part of the query string, so error messages are redacted before they surface.
"""

import os
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlencode

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, html_to_text
from jobai.discovery.sources.util import is_remote_text, parse_dt, slugify, trim_raw

BASE = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
MAX_PER_REQUEST = 50
ENV_ID, ENV_KEY = "ADZUNA_APP_ID", "ADZUNA_APP_KEY"


def availability() -> tuple[bool, str]:
    if os.environ.get(ENV_ID) and os.environ.get(ENV_KEY):
        return True, "keys found in environment"
    return False, f"needs free API keys: set {ENV_ID} and {ENV_KEY}"


def parse(data: Any) -> list[JobPosting]:
    rows = data.get("results") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise FetchError("unexpected Adzuna payload")
    out: list[JobPosting] = []
    for j in rows:
        if not isinstance(j, dict) or not j.get("id") or not j.get("title"):
            continue
        url = str(j.get("redirect_url") or "")
        comp = j["company"] if isinstance(j.get("company"), dict) else {}
        loc_d = j["location"] if isinstance(j.get("location"), dict) else {}
        company = str(comp.get("display_name") or "Unknown")
        loc = loc_d.get("display_name") or None
        if not url:
            continue
        out.append(
            JobPosting(
                source="adzuna",
                external_id=str(j["id"]),
                url=url,
                apply_url=url,
                title=html_to_text(str(j["title"])),
                company_name=company,
                company_slug=slugify(company),
                location=loc,
                remote=is_remote_text(loc, j.get("title")),
                posted_at=parse_dt(j.get("created")),
                description_text=html_to_text(j.get("description")),
                ats="adzuna",
                raw_json=trim_raw(j, drop=("description",)),
            )
        )
    return out


class AdzunaSource:
    name = "adzuna"
    attribution = "Jobs powered by Adzuna (adzuna.com)."

    def __init__(self, client: PoliteClient, country: str = "us") -> None:
        self._client = client
        self._country = country

    def fetch_all(self, limit: int) -> Iterable[JobPosting]:
        ok, why = availability()
        if not ok:
            raise FetchError(why)
        app_id, app_key = os.environ[ENV_ID], os.environ[ENV_KEY]
        qs = urlencode({
            "app_id": app_id, "app_key": app_key, "content-type": "application/json",
            "results_per_page": min(max(limit, 1), MAX_PER_REQUEST),
            "what": "software engineer",
        })
        try:
            data = self._client.get_json(f"{BASE.format(country=self._country)}?{qs}")
        except FetchError as e:
            raise FetchError(str(e).replace(app_key, "***").replace(app_id, "***")) from None
        return parse(data)[:limit]
