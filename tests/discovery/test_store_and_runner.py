import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from jobai import db
from jobai.discovery import runner
from jobai.discovery.http import PoliteClient
from jobai.discovery.models import JobPosting, Target
from jobai.discovery.sources import SOURCES
from jobai.discovery.store import Store

FX = Path(__file__).parent / "fixtures"


def _p(**kw) -> JobPosting:
    base = dict(
        source="greenhouse",
        external_id="1",
        url="https://boards.greenhouse.io/acme/jobs/1?gh_src=x",
        title="Backend Engineer",
        company_name="Acme Inc",
        company_slug="acme",
        location="Berlin",
        remote=False,
        ats="greenhouse",
        description_text="d",
    )
    base.update(kw)
    return JobPosting(**base)


def _alias_posting() -> JobPosting:
    return _p(
        source="adzuna",
        external_id="zz",
        ats="adzuna",
        url="https://adzuna.example/j/zz",
        company_name="ACME",
    )


def test_migration_0002_applies_and_is_forward_only(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(jobs)")}
    assert {"company_slug", "apply_url", "last_seen_at", "raw_json"} <= cols
    assert conn.execute("SELECT 1 FROM job_aliases").fetchall() == []
    assert db.migrate(conn) == []


def test_upsert_is_idempotent_and_updates_last_seen(conn):
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    now = [t0]
    s = Store(conn, now=lambda: now[0])
    assert s.upsert(_p()) == "inserted"
    now[0] = t0 + timedelta(days=1)
    assert s.upsert(_p(title="Backend Engineer II")) == "updated"
    rows = conn.execute("SELECT * FROM jobs").fetchall()
    assert len(rows) == 1 and rows[0]["last_seen_at"].startswith("2026-01-02")
    assert rows[0]["canonical_key"] == "greenhouse:acme:1"
    assert rows[0]["url"] == "https://boards.greenhouse.io/acme/jobs/1"
    assert conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0] == 1


def test_same_fingerprint_other_source_becomes_alias(conn):
    s = Store(conn)
    s.upsert(_p())
    assert s.upsert(_alias_posting()) == "alias"
    assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    a = conn.execute("SELECT * FROM job_aliases").fetchall()
    assert len(a) == 1 and a[0]["source"] == "adzuna"
    assert s.upsert(_alias_posting()) == "alias"
    assert conn.execute("SELECT COUNT(*) FROM job_aliases").fetchone()[0] == 1


def test_mark_stale_closes_old_and_reopens_on_return(conn):
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    now = [t0]
    s = Store(conn, now=lambda: now[0])
    s.upsert(_p(external_id="old"))
    now[0] = t0 + timedelta(days=10)
    s.upsert(_p(external_id="new", title="Other role"))
    assert s.mark_stale(7) == 1
    st = {r["external_id"]: r["status"] for r in conn.execute("SELECT * FROM jobs")}
    assert st == {"old": "closed", "new": "new"}
    assert s.mark_stale(7) == 0
    s.upsert(_p(external_id="old"))
    row = conn.execute("SELECT status FROM jobs WHERE external_id='old'").fetchone()
    assert row[0] == "new"


def _fixture(name: str):
    return json.loads((FX / name).read_text("utf-8"))


def _transport() -> httpx.MockTransport:
    def h(req: httpx.Request) -> httpx.Response:
        host, path = req.url.host, req.url.path
        if host == "boards-api.greenhouse.io" and path.endswith("/discord/jobs"):
            return httpx.Response(200, json=_fixture("greenhouse_discord.json"))
        if host == "api.lever.co" and path.endswith("/outreach"):
            return httpx.Response(200, json=_fixture("lever_outreach.json"))
        return httpx.Response(404)

    return httpx.MockTransport(h)


def _targets():
    return [
        Target(name="Discord", ats="greenhouse", slug="discord"),
        Target(name="Outreach", ats="lever", slug="outreach"),
        Target(name="Ghost", ats="ashby", slug="ghost"),
    ]


def _client() -> PoliteClient:
    return PoliteClient(transport=_transport(), sleep=lambda s: None)


def test_run_twice_no_duplicates_and_errors_reported(conn):
    c = _client()
    s = Store(conn)
    first = runner.run(s, c, _targets(), SOURCES)
    assert (first.fetched, first.inserted, len(first.errors)) == (6, 6, 1)
    second = runner.run(s, c, _targets(), SOURCES)
    assert (second.inserted, second.updated) == (0, 6)
    assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 6
    st = s.stats()
    assert st["totals"]["jobs"] == 6 and st["ats"]["lever"] == 3 and st["status"]["new"] == 6


def test_run_filters_source_and_max_companies(conn):
    r = runner.run(Store(conn), _client(), _targets(), SOURCES, source="lever")
    assert r.companies == 1 and r.fetched == 3
    r = runner.run(Store(conn), _client(), _targets(), SOURCES, max_companies=1)
    assert r.companies == 1


def test_verify_reports_dead():
    res = runner.verify(_client(), _targets(), SOURCES)
    assert [r.ok for r in res] == [True, True, False]
    assert res[2].detail.startswith("HTTP 404")


def test_load_targets_validates_and_dedupes(tmp_path):
    f = tmp_path / "c.yaml"
    f.write_text(
        "companies:\n - {name: A, ats: lever, slug: a}\n - {name: A2, ats: lever, slug: a}\n"
    )
    assert len(runner.load_targets(f, SOURCES)) == 1
    f.write_text("companies:\n - {name: A, ats: nope, slug: a}\n")
    with pytest.raises(ValueError):
        runner.load_targets(f, SOURCES)


def test_shipped_company_list_is_valid_and_sized():
    ts = runner.load_targets(Path(__file__).parents[2] / "config" / "companies.yaml", SOURCES)
    by = {a: sum(1 for t in ts if t.ats == a) for a in ("greenhouse", "lever", "ashby")}
    assert len(ts) >= 15 and all(n >= 4 for n in by.values())
