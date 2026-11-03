"""Reserve worst-case cost BEFORE each call, inside a write transaction (concurrency-safe).

A reservation is a llm_calls row holding the worst-case cost; settle() rewrites it to the
actual cost, release() deletes it if the call failed.
"""

import logging
import sqlite3
from datetime import UTC, datetime

from jobai import db
from jobai.config import Settings
from jobai.llm import ledger
from jobai.llm.errors import KillSwitchActive, SpendCapExceeded
from jobai.llm.pricing import format_usd

log = logging.getLogger(__name__)
WARN_PCT = 80


class SpendGuard:
    def __init__(self, settings: Settings) -> None:
        self.s = settings

    def _conn(self) -> sqlite3.Connection:
        conn = db.connect(self.s.database_path)
        db.migrate(conn)
        return conn

    def reserve(
        self,
        *,
        provider: str,
        model: str,
        purpose: str,
        worst_case_micro: int,
        ref: str | None = None,
        now: datetime | None = None,
    ) -> int:
        if self.s.kill_switch:
            raise KillSwitchActive("KILL_SWITCH is on; LLM calls are blocked")
        now = now or datetime.now(UTC)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                day = ledger.day_total(conn, now) + worst_case_micro
                month = ledger.month_total(conn, now) + worst_case_micro
                if day > self.s.daily_cap_micro:
                    raise SpendCapExceeded(
                        f"daily cap {format_usd(self.s.daily_cap_micro)} would be exceeded "
                        f"({format_usd(day)})"
                    )
                if month > self.s.monthly_cap_micro:
                    raise SpendCapExceeded(
                        f"monthly cap {format_usd(self.s.monthly_cap_micro)} would be exceeded "
                        f"({format_usd(month)})"
                    )
                rid = ledger.record(
                    conn,
                    provider=provider,
                    model=model,
                    purpose=purpose,
                    in_tokens=0,
                    cached_tokens=0,
                    out_tokens=0,
                    cost_micro_usd=worst_case_micro,
                    ref=ref,
                    ts=now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            if day * 100 >= self.s.daily_cap_micro * WARN_PCT:
                log.warning("daily spend at/over 80%% of cap (%s)", format_usd(day))
            if month * 100 >= self.s.monthly_cap_micro * WARN_PCT:
                log.warning("monthly spend at/over 80%% of cap (%s)", format_usd(month))
            return rid
        finally:
            conn.close()

    def settle(
        self, rid: int, *, in_tokens: int, cached_tokens: int, out_tokens: int, cost_micro: int
    ) -> None:
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE llm_calls SET in_tokens=?, cached_tokens=?, out_tokens=?, "
                "cost_micro_usd=? WHERE id=?",
                (in_tokens, cached_tokens, out_tokens, cost_micro, rid),
            )
        finally:
            conn.close()

    def release(self, rid: int) -> None:
        conn = self._conn()
        try:
            conn.execute("DELETE FROM llm_calls WHERE id=?", (rid,))
        finally:
            conn.close()
