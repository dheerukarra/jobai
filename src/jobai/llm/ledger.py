"""Every LLM call is recorded in llm_calls. Totals are integer micro-USD."""

import sqlite3
from datetime import UTC, datetime


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def record(
    conn: sqlite3.Connection,
    *,
    provider: str,
    model: str,
    purpose: str,
    in_tokens: int,
    cached_tokens: int,
    out_tokens: int,
    cost_micro_usd: int,
    ref: str | None = None,
    ts: str | None = None,
) -> int:
    cur = conn.execute(
        "INSERT INTO llm_calls(ts, provider, model, purpose, in_tokens, cached_tokens, "
        "out_tokens, cost_micro_usd, ref) VALUES (?,?,?,?,?,?,?,?,?)",
        (ts or now_iso(), provider, model, purpose, in_tokens, cached_tokens, out_tokens,
         cost_micro_usd, ref),
    )
    assert cur.lastrowid is not None
    return cur.lastrowid


def _total(conn: sqlite3.Connection, prefix: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(cost_micro_usd),0) AS t FROM llm_calls WHERE substr(ts,1,?) = ?",
        (len(prefix), prefix),
    ).fetchone()
    return int(row["t"])


def day_total(conn: sqlite3.Connection, now: datetime | None = None) -> int:
    return _total(conn, (now or datetime.now(UTC)).strftime("%Y-%m-%d"))


def month_total(conn: sqlite3.Connection, now: datetime | None = None) -> int:
    return _total(conn, (now or datetime.now(UTC)).strftime("%Y-%m"))
