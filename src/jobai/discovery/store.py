"""Idempotent persistence for discovered jobs (new WP1a file; callers: runner, cli)."""

import json
import sqlite3
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from jobai.discovery.dedupe import canonical_key, canonical_url, fingerprint, normalise_company
from jobai.discovery.models import JobPosting

Clock = Callable[[], datetime]
REPOST_DAYS = 30


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class Store:
    def __init__(self, conn: sqlite3.Connection, now: Clock = _utcnow) -> None:
        self._conn = conn
        self._now = now

    def _company_id(self, name: str) -> int:
        canon = normalise_company(name) or name.lower()
        row = self._conn.execute(
            "SELECT id FROM companies WHERE canonical_name=?", (canon,)
        ).fetchone()
        if row:
            return int(row["id"])
        cur = self._conn.execute(
            "INSERT INTO companies(name, canonical_name) VALUES (?, ?)", (name, canon)
        )
        return int(cur.lastrowid or 0)

    def _known_alias(self, p: JobPosting) -> sqlite3.Row | None:
        row: sqlite3.Row | None = self._conn.execute(
            "SELECT job_id AS id FROM job_aliases WHERE source=? AND external_id=?",
            (p.source, p.external_id),
        ).fetchone()
        return row

    def _repost_of(
        self, p: JobPosting, key: str, live_ids: frozenset[str] | None, ts: str
    ) -> sqlite3.Row | None:
        """Same source+company+title, other external_id, seen within REPOST_DAYS and no longer
        on the board (not in live_ids): the new id is a repost, recorded as an alias (WP1c)."""
        if live_ids is None:
            return None
        now = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        cutoff = _iso(now - timedelta(days=REPOST_DAYS))
        rows = self._conn.execute(
            "SELECT id, external_id FROM jobs WHERE source=? AND company_slug=? "
            "AND lower(trim(title))=lower(trim(?)) AND canonical_key<>? AND last_seen_at>=? "
            "ORDER BY id",
            (p.source, p.company_slug, p.title, key, cutoff),
        ).fetchall()
        for r in rows:
            if r["external_id"] not in live_ids:
                found: sqlite3.Row = r
                return found
        return None

    def upsert(self, p: JobPosting, live_ids: frozenset[str] | None = None) -> str:
        """Returns 'inserted', 'updated' or 'alias'.

        live_ids: external_ids currently on the same board (enables repost detection)."""
        ts = _iso(self._now())
        key = canonical_key(p.ats, p.company_slug, p.external_id)
        url = canonical_url(p.url)
        fp = fingerprint(p.company_name, p.title, p.location, p.remote)
        c = self._conn
        c.execute("BEGIN IMMEDIATE")
        try:
            existing = c.execute(
                "SELECT id, status FROM jobs WHERE canonical_key=?", (key,)
            ).fetchone()
            if existing:
                reopen = existing["status"] == "closed"
                c.execute(
                    "UPDATE jobs SET last_seen_at=?, url=?, title=?, description=?, "
                    "status=? WHERE id=?",
                    (
                        ts, url, p.title, p.description_text,
                        "new" if reopen else existing["status"], existing["id"],
                    ),
                )
                result = "updated"
            else:
                twin = self._known_alias(p) or self._repost_of(p, key, live_ids, ts)
                if twin is None:
                    twin = c.execute(
                        "SELECT id FROM jobs WHERE fingerprint=? AND source<>? ORDER BY id LIMIT 1",
                        (fp, p.source),
                    ).fetchone()
                if twin:
                    c.execute(
                        "INSERT INTO job_aliases(job_id, source, external_id, url, "
                        "first_seen_at, last_seen_at) VALUES (?,?,?,?,?,?) "
                        "ON CONFLICT(source, external_id) DO UPDATE "
                        "SET last_seen_at=excluded.last_seen_at",
                        (twin["id"], p.source, p.external_id, url, ts, ts),
                    )
                    c.execute("UPDATE jobs SET last_seen_at=? WHERE id=?", (ts, twin["id"]))
                    result = "alias"
                else:
                    self._insert(p, key, url, fp, ts)
                    result = "inserted"
            c.execute("COMMIT")
            return result
        except BaseException:
            if c.in_transaction:
                c.execute("ROLLBACK")
            raise

    def _insert(self, p: JobPosting, key: str, url: str, fp: str, ts: str) -> None:
        company_id = self._company_id(p.company_name)
        self._conn.execute(
            "INSERT INTO jobs(source, external_id, url, canonical_key, fingerprint, title, "
            "company_id, location, remote, posted_at, description, ats, first_seen_at, "
            "company_slug, apply_url, last_seen_at, raw_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                p.source, p.external_id, url, key, fp, p.title, company_id, p.location,
                1 if p.remote else 0,
                _iso(p.posted_at) if p.posted_at else None,
                p.description_text, p.ats, ts, p.company_slug,
                canonical_url(p.apply_url) if p.apply_url else None,
                ts,
                json.dumps(p.raw_json, default=str) if p.raw_json is not None else None,
            ),
        )

    def mark_stale(self, days: int) -> int:
        cutoff = _iso(self._now() - timedelta(days=days))
        cur = self._conn.execute(
            "UPDATE jobs SET status='closed' WHERE last_seen_at < ? "
            "AND status NOT IN ('closed','applied')",
            (cutoff,),
        )
        return cur.rowcount

    def stats(self) -> dict[str, Counter[str]]:
        c = self._conn
        out: dict[str, Counter[str]] = {}
        for label, col in (("source", "source"), ("ats", "ats"), ("status", "status")):
            rows = c.execute(f"SELECT {col} AS k, COUNT(*) AS n FROM jobs GROUP BY {col}")  # noqa: S608
            out[label] = Counter({str(r["k"]): int(r["n"]) for r in rows})
        out["totals"] = Counter(
            jobs=int(c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]),
            aliases=int(c.execute("SELECT COUNT(*) FROM job_aliases").fetchone()[0]),
            companies=int(c.execute("SELECT COUNT(*) FROM companies").fetchone()[0]),
        )
        return out
