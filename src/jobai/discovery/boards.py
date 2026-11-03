"""Board-slug harvesting + verification (new WP1b file; callers: discovery.runner, discovery.cli).

Finds Greenhouse/Lever/Ashby board slugs inside posting URLs/text, stores them in
discovered_boards and verifies them politely. Never edits config/companies.yaml.
"""

import html
import re
import sqlite3
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from jobai.discovery.http import HttpStatusError, PoliteClient
from jobai.discovery.models import FetchError, Source, Target

_SLUG = r"([A-Za-z0-9][A-Za-z0-9_.%-]{0,79})"
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("greenhouse", re.compile(
        r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_(?:board|app)\?for=)?"
        + _SLUG, re.I)),
    ("lever", re.compile(r"(?<![\w.-])jobs\.lever\.co/" + _SLUG, re.I)),
    ("ashby", re.compile(r"(?<![\w.-])jobs\.ashbyhq\.com/" + _SLUG, re.I)),
)
_RESERVED = {"embed", "www", "api", "static", "v1", "favicon.ico", "robots.txt", "jobs"}


def extract_boards(text: str | None) -> list[tuple[str, str]]:
    """Return unique (ats, slug) pairs found in text (URLs or HTML/escaped text)."""
    if not text:
        return []
    found: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for chunk in (text, html.unescape(text)):
        for ats, rx in _PATTERNS:
            for m in rx.finditer(chunk):
                slug = m.group(1).rstrip(".-_%")
                if not slug or slug.lower() in _RESERVED:
                    continue
                key = (ats, slug.lower())
                if key not in seen:
                    seen.add(key)
                    found.append((ats, slug))
    return found


def _iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class Candidate:
    ats: str
    slug: str
    source: str
    status: str
    detail: str | None = None


class BoardStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def record(self, source: str, *texts: str | None) -> int:
        """Store new slugs found in the given texts. Returns how many were new."""
        new = 0
        for text in texts:
            for ats, slug in extract_boards(text):
                cur = self._conn.execute(
                    "INSERT OR IGNORE INTO discovered_boards(ats, slug, first_seen, source) "
                    "VALUES (?,?,?,?)",
                    (ats, slug, _iso(), source),
                )
                new += cur.rowcount
        return new

    def candidates(
        self, known: Iterable[tuple[str, str]] = (), status: str | None = None
    ) -> list[Candidate]:
        skip = {(a, s.lower()) for a, s in known}
        sql = "SELECT ats, slug, source, status, detail FROM discovered_boards"
        args: tuple[str, ...] = ()
        if status:
            sql, args = sql + " WHERE status=?", (status,)
        rows = self._conn.execute(sql + " ORDER BY id", args).fetchall()
        return [
            Candidate(r["ats"], r["slug"], r["source"], r["status"], r["detail"])
            for r in rows
            if (r["ats"], r["slug"].lower()) not in skip
        ]

    def _mark(self, c: Candidate, status: str, detail: str) -> None:
        self._conn.execute(
            "UPDATE discovered_boards SET status=?, verified_at=?, detail=? "
            "WHERE ats=? AND slug=?",
            (status, _iso(), detail, c.ats, c.slug),
        )

    def verify(
        self,
        client: PoliteClient,
        sources: Mapping[str, Callable[[PoliteClient], Source]],
        known: Iterable[tuple[str, str]] = (),
        *,
        max_checks: int = 10,
    ) -> list[Candidate]:
        """Check up to max_checks not-yet-verified boards. 404 / 0 jobs = dead, >0 = alive.

        Transient errors (timeouts, 5xx) leave the board 'new' so it is retried next time.
        """
        todo = self.candidates(known, status="new")[: max(max_checks, 0)]
        for c in todo:
            try:
                fetcher: Source = sources[c.ats](client)
                n = len(list(fetcher.fetch(Target(name=c.slug, ats=c.ats, slug=c.slug))))
            except HttpStatusError as e:
                if e.status in (404, 410):
                    self._mark(c, "dead", f"HTTP {e.status}")
                    c.status, c.detail = "dead", f"HTTP {e.status}"
                else:
                    c.detail = f"retry later: {e}"
                continue
            except FetchError as e:
                c.detail = f"retry later: {e}"
                continue
            status = "alive" if n > 0 else "dead"
            c.status, c.detail = status, f"jobs={n}"
            self._mark(c, status, c.detail)
        return todo


def yaml_snippet(cands: Iterable[Candidate]) -> str:
    lines = [f"  - {{name: {c.slug.replace('-', ' ').title()}, ats: {c.ats}, slug: {c.slug}}}"
             for c in cands if c.status == "alive"]
    return "\n".join(lines)
