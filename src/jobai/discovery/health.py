"""Board liveness tracking and the `discover health` report (new WP1c file).

Callers: discovery.runner (skip dead boards), discovery.cli. Data: table board_status
(migration 0004) plus counts read from jobs / job_aliases.
"""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from jobai.discovery.http import HttpStatusError
from jobai.discovery.models import FetchError

DEAD_STATUSES = frozenset({404, 410})


def is_dead_error(e: FetchError) -> bool:
    """A board that is gone: 404/410, or a redirect away (we never follow redirects)."""
    return isinstance(e, HttpStatusError) and (e.status in DEAD_STATUSES or 300 <= e.status < 400)


def _iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class HealthReport:
    dead_boards: list[tuple[str, str, str, str]]  # ats, slug, checked_at, detail
    stale_jobs: int
    stale_days: int
    possible_reposts: int


class BoardHealth:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def mark_dead(self, ats: str, slug: str, detail: str) -> None:
        self._conn.execute(
            "INSERT INTO board_status(ats, slug, status, checked_at, detail) VALUES (?,?,?,?,?) "
            "ON CONFLICT(ats, slug) DO UPDATE SET status='dead', "
            "checked_at=excluded.checked_at, detail=excluded.detail",
            (ats, slug, "dead", _iso(), detail),
        )

    def mark_ok(self, ats: str, slug: str) -> None:
        self._conn.execute(
            "INSERT INTO board_status(ats, slug, status, checked_at, detail) VALUES (?,?,?,?,?) "
            "ON CONFLICT(ats, slug) DO UPDATE SET status='ok', "
            "checked_at=excluded.checked_at, detail=NULL",
            (ats, slug, "ok", _iso(), None),
        )

    def dead_set(self) -> set[tuple[str, str]]:
        rows = self._conn.execute("SELECT ats, slug FROM board_status WHERE status='dead'")
        return {(r["ats"], str(r["slug"]).lower()) for r in rows}

    def report(self, stale_days: int = 14, now: datetime | None = None) -> HealthReport:
        cutoff = ((now or datetime.now(UTC)) - timedelta(days=stale_days)).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3] + "Z"
        c = self._conn
        dead = [
            (r["ats"], r["slug"], r["checked_at"], r["detail"] or "")
            for r in c.execute(
                "SELECT ats, slug, checked_at, detail FROM board_status "
                "WHERE status='dead' ORDER BY ats, slug"
            )
        ]
        stale = c.execute(
            "SELECT COUNT(*) FROM jobs WHERE last_seen_at < ? "
            "AND status NOT IN ('closed','applied')",
            (cutoff,),
        ).fetchone()[0]
        reposts = c.execute(
            "SELECT COUNT(*) FROM job_aliases a JOIN jobs j ON j.id=a.job_id "
            "WHERE a.source = j.source"
        ).fetchone()[0]
        return HealthReport(dead, int(stale), stale_days, int(reposts))
