import sqlite3

import pytest

from jobai import db


def test_migrations_idempotent(tmp_path):
    c = db.connect(tmp_path / "a.sqlite3")
    expected = [p.stem for p in sorted(db.DEFAULT_MIGRATIONS.glob("*.sql"))]
    assert db.migrate(c) == expected
    assert db.migrate(c) == []
    n = c.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    assert n == len(expected)
    assert c.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def _job(conn, key="k1", ext="e1", source="s"):
    conn.execute(
        "INSERT INTO jobs(source, external_id, url, canonical_key, fingerprint, title) "
        "VALUES (?,?,?,?,?,?)",
        (source, ext, "http://x", key, "fp", "T"),
    )


def test_canonical_key_unique(conn):
    _job(conn)
    with pytest.raises(sqlite3.IntegrityError):
        _job(conn, ext="e2")


def test_source_external_id_unique(conn):
    _job(conn)
    with pytest.raises(sqlite3.IntegrityError):
        _job(conn, key="k2")


def test_application_job_unique_and_route_check(conn):
    _job(conn)
    conn.execute("INSERT INTO applications(job_id, route) VALUES (1, 'auto')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO applications(job_id, route) VALUES (1, 'assisted')")
    _job(conn, key="k2", ext="e2")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO applications(job_id, route) VALUES (2, 'bogus')")


def test_foreign_keys_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO applications(job_id, route) VALUES (999, 'auto')")


def test_migration_failure_rolls_back_and_records_nothing(tmp_path):
    d = tmp_path / "m"
    d.mkdir()
    (d / "0001_ok.sql").write_text("CREATE TABLE a(x INTEGER);")
    (d / "0002_bad.sql").write_text("CREATE TABLE b(x INTEGER);\nINSERT INTO nope VALUES (1);")
    c = db.connect(tmp_path / "f.sqlite3")
    with pytest.raises(sqlite3.OperationalError):
        db.migrate(c, d)
    assert not c.in_transaction
    versions = [r[0] for r in c.execute("SELECT version FROM schema_migrations")]
    assert versions == ["0001_ok"]
    assert c.execute("SELECT name FROM sqlite_master WHERE name='b'").fetchone() is None
    c.execute("INSERT INTO a VALUES (1)")  # connection still usable for writes


def test_missing_or_empty_migrations_dir_fails_loudly(tmp_path):
    c = db.connect(tmp_path / "e.sqlite3")
    with pytest.raises(db.MigrationError):
        db.migrate(c, tmp_path / "does-not-exist")
    (tmp_path / "empty").mkdir()
    with pytest.raises(db.MigrationError):
        db.migrate(c, tmp_path / "empty")


def test_default_migrations_ship_inside_package():
    assert db.DEFAULT_MIGRATIONS.parent.name == "jobai"
    assert (db.DEFAULT_MIGRATIONS / "0001_init.sql").is_file()


def test_concurrent_migrate_applies_once(tmp_path):
    import threading

    path = tmp_path / "c.sqlite3"
    results: list[list[str]] = []
    errors: list[Exception] = []

    def worker():
        c = db.connect(path)
        try:
            results.append(db.migrate(c))
        except Exception as exc:
            errors.append(exc)
        finally:
            c.close()

    ts = [threading.Thread(target=worker) for _ in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert errors == []
    n_mig = len(list(db.DEFAULT_MIGRATIONS.glob("*.sql")))
    assert sorted(len(r) for r in results) == [0, 0, 0, 0, 0, n_mig]


def test_check_constraints(conn):
    _job(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE jobs SET status='bogus'")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO applications(job_id, route, status) VALUES (1,'auto','bogus')")
    for col in ("in_tokens", "cached_tokens", "out_tokens", "cost_micro_usd"):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"INSERT INTO llm_calls(provider, model, purpose, {col}) VALUES ('p','m','x',-1)"
            )
