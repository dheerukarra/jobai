"""WP1b: aggregator parsers (recorded, trimmed real responses), no network."""

import json
from pathlib import Path

import httpx
import pytest

from jobai.discovery import runner
from jobai.discovery.http import PoliteClient
from jobai.discovery.models import FetchError
from jobai.discovery.sources import (
    AGGREGATORS,
    NOT_IMPLEMENTED,
    adzuna,
    agg_status,
    arbeitnow,
    freehire,
    hn_hiring,
    remoteok,
    remotive,
    themuse,
)
from jobai.discovery.store import Store

FX = Path(__file__).parent / "fixtures"


def _fx(name: str):
    return json.loads((FX / name).read_text(encoding="utf-8"))


def test_remotive_parse():
    ps = remotive.parse(_fx("remotive.json"))
    assert len(ps) == 3 and ps[0].source == "remotive" and ps[0].remote is True
    assert ps[0].url.startswith("https://remotive.com/") and ps[0].external_id == "2091165"
    assert ps[0].posted_at is not None and "<" not in ps[0].description_text


def test_remoteok_skips_legal_notice_and_keeps_link():
    ps = remoteok.parse(_fx("remoteok.json"))
    assert len(ps) == 2 and all(p.url.lower().startswith("https://remoteok.com/") for p in ps)
    assert ps[0].title == "AI ML Engineer" and ps[0].remote is True


def test_arbeitnow_parse_epoch_and_remote_flag():
    ps = arbeitnow.parse(_fx("arbeitnow.json"))
    assert len(ps) == 3 and ps[0].remote is False and ps[0].posted_at is not None
    assert ps[0].external_id == "senior-data-analyst-crm-munich-231256"


def test_themuse_parse():
    ps = themuse.parse(_fx("themuse.json"))
    assert len(ps) == 3 and ps[0].company_slug == "celonis"
    assert ps[0].location == "Madrid, Spain"


def test_freehire_parse():
    ps = freehire.parse(_fx("freehire.json"))
    assert len(ps) == 3 and ps[0].source == "freehire"
    assert ps[0].external_id.startswith("python-developer")
    assert "enrichment" not in (ps[0].raw_json or {})


def test_hn_thread_and_comments():
    assert hn_hiring.find_thread(_fx("hn_threads.json")) == "50338728"
    ps = hn_hiring.parse_comments(_fx("hn_comments.json"), "50338728")
    names = [p.company_name for p in ps]
    assert "Apollo Research" in names and "Tether" in names
    assert all(p.source == "hn_hiring" for p in ps)
    # replies (parent is another comment) are not postings
    assert not any(p.external_id in ("50358182", "50357688") for p in ps)
    apollo = next(p for p in ps if p.company_name == "Apollo Research")
    assert apollo.apply_url and "jobs.lever.co/apolloresearch" in apollo.apply_url
    tether = next(p for p in ps if p.company_name == "Tether")
    assert tether.remote is True


@pytest.mark.parametrize(
    "fn,payload",
    [
        (remotive.parse, {}), (remoteok.parse, {}), (arbeitnow.parse, []),
        (themuse.parse, []), (freehire.parse, []), (adzuna.parse, []),
    ],
)
def test_bad_payload_raises_fetch_error(fn, payload):
    with pytest.raises(FetchError):
        fn(payload)


def test_hn_no_thread():
    with pytest.raises(FetchError):
        hn_hiring.find_thread({"hits": [{"title": "Ask HN: Who wants to be hired?"}]})


def test_adzuna_disabled_without_keys(monkeypatch):
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)
    ok, why = agg_status("adzuna")
    assert not ok and "ADZUNA_APP_ID" in why
    with pytest.raises(FetchError, match="ADZUNA"):
        list(AGGREGATORS["adzuna"].factory(PoliteClient()).fetch_all(5))
    assert not AGGREGATORS["adzuna"].in_all and "usajobs" in NOT_IMPLEMENTED


def test_adzuna_redacts_key_on_error(monkeypatch):
    monkeypatch.setenv("ADZUNA_APP_ID", "myid123")
    monkeypatch.setenv("ADZUNA_APP_KEY", "mysecretkey")
    c = PoliteClient(transport=httpx.MockTransport(lambda r: httpx.Response(403)),
                     sleep=lambda s: None)
    with pytest.raises(FetchError) as e:
        list(adzuna.AdzunaSource(c).fetch_all(5))
    assert "mysecretkey" not in str(e.value) and "myid123" not in str(e.value)


def test_adzuna_parse_minimal():
    ps = adzuna.parse({"results": [{
        "id": "9", "title": "Dev", "redirect_url": "https://x.example/j/9",
        "company": {"display_name": "Acme"}, "location": {"display_name": "Remote, US"},
        "created": "2026-11-01T10:00:00Z", "description": "<p>hi</p>",
    }]})
    assert ps[0].remote is True and ps[0].description_text == "hi"


def _agg_transport() -> httpx.MockTransport:
    def h(req: httpx.Request) -> httpx.Response:
        host = req.url.host
        if host == "remotive.com":
            return httpx.Response(200, json=_fx("remotive.json"))
        if host == "remoteok.com":
            return httpx.Response(200, json=_fx("remoteok.json"))
        return httpx.Response(500)

    return httpx.MockTransport(h)


def test_run_aggregators_twice_no_dupes_and_isolated_errors(conn):
    c = PoliteClient(transport=_agg_transport(), sleep=lambda s: None)
    store = Store(conn)
    names = ["remotive", "remoteok", "arbeitnow"]
    fac = {n: (lambda n=n: AGGREGATORS[n].factory(c)) for n in names}
    first = runner.run_aggregators(store, names, fac, limit=50)
    assert first["remotive"].inserted == 3 and first["remoteok"].inserted == 2
    assert first["arbeitnow"].errors and first["arbeitnow"].fetched == 0
    second = runner.run_aggregators(store, names, fac, limit=50)
    assert second["remotive"].inserted == 0 and second["remotive"].updated == 3
    assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 5


def test_cross_source_fingerprint_alias(conn):
    store = Store(conn)
    a = remotive.parse(_fx("remotive.json"))[0]
    b = a.model_copy(update={"source": "remoteok", "ats": "remoteok", "external_id": "zz",
                             "company_slug": "other"})
    assert store.upsert(a) == "inserted"
    assert store.upsert(b) == "alias"


def test_http_cache_avoids_second_request(tmp_path):
    calls = []

    def h(req: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, json={"a": 1})

    c = PoliteClient(transport=httpx.MockTransport(h), sleep=lambda s: None, cache_dir=tmp_path)
    assert c.get_json("https://x.example/a", cache_ttl=60) == {"a": 1}
    assert c.get_json("https://x.example/a", cache_ttl=60) == {"a": 1}
    assert len(calls) == 1 and c.request_count == 1
    c.get_json("https://x.example/a")  # no ttl -> always network
    assert len(calls) == 2
