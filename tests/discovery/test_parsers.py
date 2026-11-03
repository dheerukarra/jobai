import json
from pathlib import Path

import pytest

from jobai.discovery.models import FetchError, Target, html_to_text
from jobai.discovery.sources import ashby, greenhouse, lever

FX = Path(__file__).parent / "fixtures"


def _load(name: str):
    return json.loads((FX / name).read_text(encoding="utf-8"))


def test_html_to_text_handles_escaped_html():
    raw = "&lt;p&gt;Hello &amp;amp; welcome&lt;/p&gt;&lt;ul&gt;&lt;li&gt;One&lt;/li&gt;&lt;/ul&gt;"
    text = html_to_text(raw)
    assert "<" not in text and "Hello & welcome" in text and "One" in text


def test_greenhouse_parse():
    t = Target(name="Discord", ats="greenhouse", slug="discord")
    jobs = greenhouse.parse(_load("greenhouse_discord.json"), t)
    assert len(jobs) == 3
    j = jobs[0]
    assert (j.source, j.ats, j.company_slug) == ("greenhouse", "greenhouse", "discord")
    assert j.external_id == "8917177002" and j.title == "Associate Commercial Counsel"
    assert j.url.startswith("https://job-boards.greenhouse.io/discord/jobs/")
    assert j.remote is True and j.posted_at is not None and "<" not in j.description_text
    assert j.raw_json is not None and "content" not in j.raw_json


def test_lever_parse():
    t = Target(name="Outreach", ats="lever", slug="outreach")
    jobs = lever.parse(_load("lever_outreach.json"), t)
    assert len(jobs) == 3
    assert jobs[0].remote is True and jobs[2].remote is False
    assert jobs[0].location == "Seattle, WA" and jobs[0].posted_at is not None
    assert jobs[0].apply_url and jobs[0].description_text


def test_ashby_parse_strips_title_and_skips_unlisted():
    data = _load("ashby_posthog.json")
    data["jobs"][1]["isListed"] = False
    t = Target(name="PostHog", ats="ashby", slug="posthog")
    jobs = ashby.parse(data, t)
    assert len(jobs) == 2
    assert jobs[0].title == "Technical Support Engineer"
    assert jobs[0].remote is True and (jobs[0].apply_url or "").endswith("/application")
    assert jobs[0].posted_at is not None and "<" not in jobs[0].description_text


def test_bad_payload_raises():
    t = Target(name="X", ats="lever", slug="x")
    with pytest.raises(FetchError):
        lever.parse({"oops": 1}, t)
    with pytest.raises(FetchError):
        greenhouse.parse([], t)
