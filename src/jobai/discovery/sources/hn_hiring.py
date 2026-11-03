"""Hacker News "Ask HN: Who is hiring?" via the public Algolia HN API (keyless). New WP1b file.

Finds the latest monthly thread (posted by user whoishiring), then reads its top-level comments.
Top-level comments conventionally start "Company | Role | Location | REMOTE | ...".
Algolia HN API: https://hn.algolia.com/api. Comments are user content; we only link to the HN item.
"""

import re
from collections.abc import Iterable
from typing import Any

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, html_to_text
from jobai.discovery.sources.util import parse_dt, slugify

THREAD_URL = "https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=5"
COMMENTS_URL = (
    "https://hn.algolia.com/api/v1/search_by_date?tags=comment,story_{sid}"
    "&hitsPerPage={n}&page={page}"
)
PAGE_SIZE = 100
MAX_PAGES = 2
CACHE_TTL_S = 3600
_URL = re.compile(r"https?://[^\s<>\"')]+")
_NOISE = re.compile(
    r"^(remote|onsite|on-site|hybrid|full[- ]?time|part[- ]?time|contract|interns?|visa|"
    r"relocation|salary|\$|http)", re.I)


def find_thread(data: Any) -> str:
    hits = data.get("hits") if isinstance(data, dict) else None
    if not isinstance(hits, list):
        raise FetchError("unexpected HN thread-search payload")
    for h in hits:
        if isinstance(h, dict) and str(h.get("title", "")).lower().startswith(
            "ask hn: who is hiring"
        ) and h.get("objectID"):
            return str(h["objectID"])
    raise FetchError("no 'Who is hiring' thread found")


def parse_comments(data: Any, story_id: str) -> list[JobPosting]:
    hits = data.get("hits") if isinstance(data, dict) else None
    if not isinstance(hits, list):
        raise FetchError("unexpected HN comments payload")
    out: list[JobPosting] = []
    for h in hits:
        if not isinstance(h, dict) or str(h.get("parent_id")) != story_id:
            continue  # replies are not postings
        oid, raw = h.get("objectID"), h.get("comment_text")
        if not oid or not raw:
            continue
        text = html_to_text(str(raw))
        first = text.split("\n", 1)[0]
        parts = [p.strip() for p in first.split("|")]
        if len(parts) < 2 or not parts[0] or not parts[1] or len(first) > 400:
            continue
        company, title = parts[0][:100], parts[1][:200]
        rest = parts[2:]
        loc = next((p for p in rest if p and not _NOISE.match(p)), None)
        hn_url = f"https://news.ycombinator.com/item?id={oid}"
        link = _URL.search(str(raw).replace("&#x2F;", "/"))
        remote = True if "remote" in first.lower() else None
        out.append(
            JobPosting(
                source="hn_hiring",
                external_id=str(oid),
                url=hn_url,
                apply_url=link.group(0).rstrip(".,;") if link else hn_url,
                title=title,
                company_name=company,
                company_slug=slugify(company),
                location=loc,
                remote=remote,
                posted_at=parse_dt(h.get("created_at")),
                description_text=text,
                ats="hn_hiring",
                raw_json={"story_id": story_id, "author": h.get("author")},
            )
        )
    return out


class HnHiringSource:
    name = "hn_hiring"
    attribution = "Postings from Hacker News 'Who is hiring?' (news.ycombinator.com)."

    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch_all(self, limit: int) -> Iterable[JobPosting]:
        sid = find_thread(self._client.get_json(THREAD_URL, cache_ttl=CACHE_TTL_S))
        out: list[JobPosting] = []
        for page in range(MAX_PAGES):
            url = COMMENTS_URL.format(sid=sid, n=PAGE_SIZE, page=page)
            out.extend(parse_comments(self._client.get_json(url, cache_ttl=CACHE_TTL_S), sid))
            if len(out) >= limit:
                break
        return out[:limit]
