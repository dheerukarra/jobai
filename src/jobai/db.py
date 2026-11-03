"""SQLite connection (WAL, foreign keys) and a tiny forward-only migration runner."""

import sqlite3
import time
from pathlib import Path

# Shipped inside the package so the wheel contains it.
DEFAULT_MIGRATIONS = Path(__file__).resolve().parent / "migrations"


class MigrationError(RuntimeError):
    pass


def connect(path: Path | str) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    for attempt in range(50):  # switching to WAL can race with another first-time opener
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            break
        except sqlite3.OperationalError:
            if attempt == 49:
                raise
            time.sleep(0.05)
    return conn


def _statements(sql: str) -> list[str]:
    """Split a SQL script into complete statements (executescript would COMMIT first)."""
    out: list[str] = []
    buf = ""
    for line in sql.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            out.append(buf)
            buf = ""
    if buf.strip():
        out.append(buf)
    return out


def migrate(conn: sqlite3.Connection, migrations_dir: Path = DEFAULT_MIGRATIONS) -> list[str]:
    """Apply unapplied NNNN_name.sql files in order. Returns versions applied now.

    Each file runs in its own BEGIN IMMEDIATE transaction (this serialises concurrent
    migrators); applied versions are re-read inside it. Failure rolls back and re-raises;
    the version is recorded only on success.
    """
    files = sorted(migrations_dir.glob("*.sql")) if migrations_dir.is_dir() else []
    if not files:
        raise MigrationError(f"no migrations found in {migrations_dir}")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL "
        "DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')))"
    )
    applied: list[str] = []
    for f in files:
        version = f.stem
        if not version.replace("_", "").isalnum():
            raise MigrationError(f"bad migration name: {f.name}")
        sql = f.read_text(encoding="utf-8")
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version=?", (version,)
            ).fetchone()
            if row is None:
                for stmt in _statements(sql):
                    conn.execute(stmt)
                conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
                applied.append(version)
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    return applied
