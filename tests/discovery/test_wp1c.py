"""WP1c: new ATS parsers, pagination, dead-board skip, repost alias, health. No network.

Workable / SmartRecruiters / Recruitee fixtures are trimmed real responses recorded
2026-11-12. BambooHR / Breezy payloads are hand-written from the documented shape
(those two sources could not be verified live and are registered disabled).
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from jobai import db
from jobai.discovery import runner
from jobai.discovery.health import BoardHealth
from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError, JobPosting, Target
from jobai.discovery.sources import (
    DISABLED_ATS,
    SOURCES,
    ats_status,
    bamboohr,
    breezy,
    recruitee,
    smartrecruiters,
    workable,
)
from jobai.discovery.sources.smartrecruiters import SmartRecruitersSource
from jobai.discovery.store import Store

FX = Path(__file__).parent / "fixtures"


def _fx(name: str):
    return json.loads((FX / name).read_text(encoding="utf-8"))


def _t(ats: str, slug: str = "acme") -> Target:
    return Target(name="Acme", ats=ats, slug=slug)


def test_workable_parse():
    ps = workable.parse(_fx("workable_hf.json"), _t("workable", "huggingface"))
    assert len(ps) == 2 and ps[0].source == ps[0].ats == "workable"
    assert ps[0].external_id == "81B46579FE" and ps[0].url.startswith("https://apply.workable.com/")
    assert ps[0].remote is True and ps[0].location == "Paris, Île-de-France, France"
    assert ps[0].posted_at is not None and "<" not in ps[0].description_text


def test_workable_bad_payload_and_slug():
    with pytest.raises(FetchError):
        workable.parse({"nope": 1}, _t("workable"))
    with pytest.raises(FetchError):
        list(SOURCES["workable"](PoliteClient()).fetch(_t("workable", "../evil")))


def test_recruitee_parse_skips_samples_and_parses_utc_dates():
    data = _fx("recruitee_channable.json")
    data["offers"].append({**data["offers"][0], "id": 1, "title": "Demo role (Sample)"})
    ps = recruitee.parse(data, _t("recruitee", "channable"))
    assert len(ps) == 2
    p = ps[0]
    assert p.source == "recruitee" and p.url.startswith("https://") and p.remote is None
    assert p.posted_at == datetime(2026, 11, 3, 20, 8, 14, tzinfo=UTC)
    assert p.company_name == "Channable" and "<" not in p.description_text


def test_smartrecruiters_parse():
    ps = smartrecruiters.parse(_fx("smartrecruiters_freshworks.json"), _t("smartrecruiters"))
    assert len(ps) == 3 and ps[0].external_id == "744000161322320"
    assert ps[0].url.startswith("https://jobs.smartrecruiters.com/Freshworks/744000161322320-")
    assert ps[0].location == "San Mateo, CA, United States" and ps[0].posted_at is not None


def test_smartrecruiters_paginates_until_total():
    base = _fx("smartrecruiters_freshworks.json")
    seen: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        offset = int(req.url.params["offset"])
        seen.append(f"{req.url.params['limit']}/{offset}")
        n = 100 if offset < 200 else 7  # 207 postings in total
        content = [
            {**base["content"][0], "id": f"{offset + i}"} for i in range(n)
        ]
        return httpx.Response(200, json={"totalFound": 207, "content": content})

    client = PoliteClient(transport=httpx.MockTransport(handler), sleep=lambda s: None)
    out = list(SmartRecruitersSource(client).fetch(_t("smartrecruiters", "freshworks")))
    assert len(out) == 207 and seen == ["100/0", "100/100", "100/200"]


def test_bamboohr_parse_documented_shape():
    data = {"meta": {}, "result": [
        {"id": "12", "jobOpeningName": "Support Agent", "departmentLabel": "Support",
         "location": {"city": "Boise", "state": "ID"}, "isRemote": None},
        {"id": 13, "jobOpeningName": "Designer", "location": {"city": None, "state": None},
         "isRemote": True},
        {"id": "", "jobOpeningName": "No id"},
    ]}
    ps = bamboohr.parse(data, _t("bamboohr", "Acme"))
    assert [p.external_id for p in ps] == ["12", "13"]
    assert ps[0].url == "https://acme.bamboohr.com/careers/12" and ps[0].location == "Boise, ID"
    assert ps[1].remote is True and ps[1].location == "Remote"


def test_breezy_parse_documented_shape():
    data = [
        {"id": "abc123", "name": "Engineer", "url": "https://acme.breezy.hr/p/abc123-engineer",
         "published_date": "2026-10-01T10:00:00.000Z",
         "location": {"name": "Seattle, WA", "country": {"name": "United States"},
                      "is_remote": False}},
        {"name": "Remote dev", "url": "https://acme.breezy.hr/p/zzz9-remote-dev",
         "location": {"city": "Oslo", "is_remote": True}},
        {"name": "Bad url", "url": "http://nope"},
    ]
    ps = breezy.parse(data, _t("breezy"))
    assert [p.external_id for p in ps] == ["abc123", "zzz9-remote-dev"]
    assert ps[0].location == "Seattle, WA, United States" and ps[0].posted_at is not None
    assert ps[1].remote is True
    with pytest.raises(FetchError):
        breezy.parse({"x": 1}, _t("breezy"))


def test_unverified_sources_are_disabled_and_reported():
    assert set(DISABLED_ATS) == {"bamboohr", "breezy"}
    ok, why = ats_status("bamboohr")
    assert not ok and "NOT verified live" in why
    assert ats_status("workable") == (True, "keyless public API, verified live")
    assert {"workable", "smartrecruiters", "recruitee"} <= set(SOURCES)


def _dead_transport(dead_slug: str) -> httpx.MockTransport:
    calls: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.url.path)
        if dead_slug in str(req.url):
            return httpx.Response(404, json={})
        return httpx.Response(200, json=_fx("workable_hf.json"))

    t = httpx.MockTransport(handler)
    t.calls = calls  # type: ignore[attr-defined]
    return t


def test_dead_board_is_marked_then_skipped_then_retried(conn):
    targets = [_t("workable", "gone"), _t("workable", "alive"), _t("bamboohr", "x")]
    tr = _dead_transport("gone")
    client = PoliteClient(transport=tr, sleep=lambda s: None)
    store, health = Store(conn), BoardHealth(conn)

    def go(**kw):
        return runner.run(store, client, targets, SOURCES, health=health,
                          disabled_ats=DISABLED_ATS, **kw)

    first = go()
    assert first.newly_dead == ["workable/gone"] and first.fetched == 2
    assert first.skipped_disabled == ["bamboohr/x"]  # disabled ATS skipped when no --source
    n = len(tr.calls)  # type: ignore[attr-defined]
    second = go()
    assert second.skipped_dead == ["workable/gone"] and second.companies == 1
    assert len(tr.calls) == n + 1  # type: ignore[attr-defined]  # dead board not requested
    assert go(retry_dead=True).companies == 2  # explicit retry re-checks it
    rep = health.report()
    assert [(a, s) for a, s, *_ in rep.dead_boards] == [("workable", "gone")]


def test_board_recovering_clears_dead(conn):
    health = BoardHealth(conn)
    health.mark_dead("workable", "x", "HTTP 404")
    assert health.dead_set() == {("workable", "x")}
    health.mark_ok("workable", "x")
    assert health.dead_set() == set()


def _jp(ext: str, title: str = "Backend Engineer", **kw) -> JobPosting:
    base = dict(source="workable", external_id=ext, url=f"https://apply.workable.com/j/{ext}",
                title=title, company_name="Acme", company_slug="acme", ats="workable",
                location="Berlin")
    base.update(kw)
    return JobPosting(**base)


def test_repost_with_new_id_becomes_alias_not_new_job(conn):
    t0 = datetime(2026, 11, 1, tzinfo=UTC)
    clock = {"now": t0}
    store = Store(conn, now=lambda: clock["now"])
    assert store.upsert(_jp("A1"), frozenset({"A1"})) == "inserted"
    clock["now"] = t0 + timedelta(days=10)
    # A1 vanished from the board, the same title came back under a new id
    assert store.upsert(_jp("B2"), frozenset({"B2"})) == "alias"
    assert store.upsert(_jp("B2"), frozenset({"B2"})) == "alias"  # idempotent
    assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM job_aliases").fetchone()[0] == 1
    assert BoardHealth(conn).report().possible_reposts == 1


def test_same_title_both_live_stays_two_jobs_and_old_repost_not_matched(conn):
    t0 = datetime(2026, 11, 1, tzinfo=UTC)
    clock = {"now": t0}
    store = Store(conn, now=lambda: clock["now"])
    both = frozenset({"A1", "A2"})
    assert store.upsert(_jp("A1"), both) == "inserted"
    assert store.upsert(_jp("A2"), both) == "inserted"  # two real openings, same title
    clock["now"] = t0 + timedelta(days=45)  # older than the 30-day window
    assert store.upsert(_jp("C3", title="Backend Engineer"), frozenset({"C3"})) == "inserted"


def test_migration_0004_adds_board_status_and_is_idempotent(tmp_path):
    c = db.connect(tmp_path / "m.sqlite3")
    expected = [p.stem for p in sorted(db.DEFAULT_MIGRATIONS.glob("*.sql"))]
    assert "0004_board_status" in expected
    assert db.migrate(c) == expected and db.migrate(c) == []
    cols = [r[1] for r in c.execute("PRAGMA table_info(board_status)")]
    assert cols == ["ats", "slug", "status", "checked_at", "detail"]


def test_health_report_counts_stale_jobs(conn):
    t0 = datetime(2026, 10, 1, tzinfo=UTC)
    Store(conn, now=lambda: t0).upsert(_jp("S1"))
    rep = BoardHealth(conn).report(stale_days=14, now=t0 + timedelta(days=20))
    assert rep.stale_jobs == 1 and rep.dead_boards == []
    assert BoardHealth(conn).report(stale_days=30, now=t0 + timedelta(days=20)).stale_jobs == 0
