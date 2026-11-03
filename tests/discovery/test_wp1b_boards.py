"""WP1b: board-slug harvesting, migration 0003, verify-harvested, JobSpy stub, CLI listing."""

import httpx
import pytest

from jobai import db
from jobai.discovery import cli as dcli
from jobai.discovery.boards import BoardStore, extract_boards, yaml_snippet
from jobai.discovery.http import PoliteClient
from jobai.discovery.sources import SOURCES, agg_status
from jobai.discovery.sources.jobspy_source import JobSpySource, parse


@pytest.mark.parametrize(
    "text,expected",
    [
        ("https://boards.greenhouse.io/stripe/jobs/123?gh_jid=1", [("greenhouse", "stripe")]),
        ("https://job-boards.greenhouse.io/Airbnb", [("greenhouse", "Airbnb")]),
        ("https://boards.greenhouse.io/embed/job_app?for=discord&token=1",
         [("greenhouse", "discord")]),
        ("https://boards.eu.greenhouse.io/acme-gmbh/jobs/9", [("greenhouse", "acme-gmbh")]),
        ("https://jobs.lever.co/palantir/abc-123/apply", [("lever", "palantir")]),
        ("see https://jobs.lever.co/my.co.", [("lever", "my.co")]),
        ("https://jobs.ashbyhq.com/ramp?utm_source=x", [("ashby", "ramp")]),
        ("https:&#x2F;&#x2F;jobs.ashbyhq.com&#x2F;notion&#x2F;abc", [("ashby", "notion")]),
        ('<a href="https://jobs.lever.co/zoox/1">https://jobs.lever.co/zoox/1...</a>',
         [("lever", "zoox")]),
        ("https://boards.greenhouse.io/embed/", []),
        ("https://evil-jobs.lever.co.attacker.com/x https://notjobs.lever.co/x", []),
        ("https://example.com/jobs.lever.co/x", [("lever", "x")]),  # path mention still a slug
        ("", []),
    ],
)
def test_extract_boards(text, expected):
    assert extract_boards(text) == expected


def test_extract_dedupes_case_insensitively():
    got = extract_boards("https://jobs.lever.co/Foo https://jobs.lever.co/foo/1")
    assert got == [("lever", "Foo")]


def test_migration_0003_creates_table_and_constraints(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(discovered_boards)")}
    assert {"ats", "slug", "first_seen", "source", "verified_at", "status"} <= cols
    conn.execute("INSERT INTO discovered_boards(ats, slug, source) VALUES ('lever','Foo','t')")
    with pytest.raises(Exception, match="UNIQUE"):
        conn.execute("INSERT INTO discovered_boards(ats, slug, source) VALUES ('lever','foo','t')")
    with pytest.raises(Exception, match="CHECK"):
        conn.execute("UPDATE discovered_boards SET status='bogus'")
    assert "0003_discovered_boards" in [
        r[0] for r in conn.execute("SELECT version FROM schema_migrations")
    ]
    assert db.migrate(conn) == []


def test_record_is_idempotent_and_candidates_exclude_known(conn):
    bs = BoardStore(conn)
    n = bs.record("remotive", "https://jobs.lever.co/a/1", None, "x https://jobs.ashbyhq.com/b")
    assert n == 2
    assert bs.record("remoteok", "https://jobs.lever.co/A/2") == 0
    cands = bs.candidates(known=[("lever", "a")])
    assert [(c.ats, c.slug) for c in cands] == [("ashby", "b")]


def _client(handler) -> PoliteClient:
    return PoliteClient(transport=httpx.MockTransport(handler), sleep=lambda s: None)


def test_verify_harvested_alive_dead_transient_and_cap(conn):
    bs = BoardStore(conn)
    bs.record(
        "t",
        "https://boards.greenhouse.io/alive https://boards.greenhouse.io/gone "
        "https://boards.greenhouse.io/empty https://boards.greenhouse.io/flaky "
        "https://boards.greenhouse.io/notchecked",
    )

    def h(req: httpx.Request) -> httpx.Response:
        slug = req.url.path.split("/")[3]
        if slug == "alive":
            return httpx.Response(200, json={"jobs": [{
                "id": 1, "title": "Eng", "absolute_url": "https://boards.greenhouse.io/alive/1",
                "location": {"name": "Remote"}, "content": "x",
                "updated_at": "2026-01-01T00:00:00Z",
            }]})
        if slug == "empty":
            return httpx.Response(200, json={"jobs": []})
        if slug == "flaky":
            return httpx.Response(503)
        return httpx.Response(404)

    c = _client(h)
    done = bs.verify(c, SOURCES, max_checks=4)
    got = {d.slug: d.status for d in done}
    assert got == {"alive": "alive", "gone": "dead", "empty": "dead", "flaky": "new"}
    q = conn.execute("SELECT slug, status FROM discovered_boards")
    rows = {r["slug"]: r["status"] for r in q}
    assert rows["notchecked"] == "new" and rows["flaky"] == "new" and rows["alive"] == "alive"
    assert conn.execute(
        "SELECT verified_at FROM discovered_boards WHERE slug='alive'"
    ).fetchone()[0]
    snippet = yaml_snippet(done)
    assert snippet == "  - {name: Alive, ats: greenhouse, slug: alive}"


def test_jobspy_stub_and_caps():
    seen = {}

    def scraper(term: str, n: int):
        seen["n"] = n
        return [
            {"id": "in-1", "site": "indeed", "job_url": "https://indeed.example/1",
             "title": "Dev", "company": "Acme", "location": "Austin, TX",
             "is_remote": False, "date_posted": "2026-11-01", "description": "d"},
            {"id": "x", "job_url": None, "title": "no url"},
            {"id": "in-2", "job_url": "https://indeed.example/2", "title": "T",
             "company": float("nan"), "is_remote": float("nan"), "date_posted": float("nan")},
        ]

    ps = list(JobSpySource(scraper=scraper).fetch_all(500))
    assert seen["n"] == 10  # hard cap
    assert [p.external_id for p in ps] == ["in-1", "in-2"]
    assert ps[0].apply_url is None and ps[0].remote is False
    assert ps[1].company_name == "nan" or ps[1].company_name == "Unknown"
    assert parse([]) == []


def test_jobspy_off_by_default_and_not_in_all():
    from jobai.discovery.sources import AGGREGATORS

    assert AGGREGATORS["jobspy"].in_all is False
    ok, why = agg_status("jobspy")
    assert ok or "not installed" in why


def test_cli_sources_lists_everything(capsys):
    import argparse

    rc = dcli._cmd_sources(argparse.Namespace(companies="config/companies.yaml"))
    out = capsys.readouterr().out
    assert rc == 0
    for name in ("remotive", "remoteok", "arbeitnow", "themuse", "hn_hiring", "freehire",
                 "adzuna", "jobspy", "usajobs", "greenhouse"):
        assert name in out
    assert "DISABLED" in out
