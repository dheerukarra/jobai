import json
import threading
from datetime import UTC, datetime

import pytest

from jobai.config import Settings
from jobai.llm import ledger, pricing
from jobai.llm.caps import SpendGuard
from jobai.llm.errors import (
    KillSwitchActive,
    LadderExhausted,
    LLMParseError,
    ProviderTimeout,
    SpendCapExceeded,
)
from jobai.llm.gateway import Gateway
from jobai.llm.providers.fake import FakeProvider
from jobai.llm.redact import Redactor

MSG = [{"role": "user", "content": "hello"}]


def test_reserve_allows_below_and_denies_at_cap(settings, conn):
    g = SpendGuard(settings)
    g.reserve(provider="p", model="m", purpose="x", worst_case_micro=600_000)
    with pytest.raises(SpendCapExceeded):
        g.reserve(provider="p", model="m", purpose="x", worst_case_micro=500_000)
    g.reserve(provider="p", model="m", purpose="x", worst_case_micro=400_000)  # exactly cap
    assert ledger.day_total(conn) == 1_000_000


def test_monthly_cap(tmp_path):
    s = Settings(_env_file=None, database_path=tmp_path / "m.sqlite3",
                 daily_cap_usd="5.00", monthly_cap_usd="1.00")
    g = SpendGuard(s)
    g.reserve(provider="p", model="m", purpose="x", worst_case_micro=900_000)
    with pytest.raises(SpendCapExceeded):
        g.reserve(provider="p", model="m", purpose="x", worst_case_micro=200_000)


def test_cap_concurrency_safe(settings, conn):
    g = SpendGuard(settings)
    ok, denied = [], []

    def worker():
        try:
            g.reserve(provider="p", model="m", purpose="x", worst_case_micro=300_000)
            ok.append(1)
        except SpendCapExceeded:
            denied.append(1)

    ts = [threading.Thread(target=worker) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(ok) == 3 and len(denied) == 5
    assert ledger.day_total(conn) == 900_000


def test_eighty_percent_warning(settings, caplog):
    g = SpendGuard(settings)
    with caplog.at_level("WARNING"):
        g.reserve(provider="p", model="m", purpose="x", worst_case_micro=850_000)
    assert "80%" in caplog.text


def test_day_boundary_uses_utc_day(settings, conn):
    g = SpendGuard(settings)
    yesterday = datetime(2026, 1, 1, 12, tzinfo=UTC)
    g.reserve(provider="p", model="m", purpose="x", worst_case_micro=900_000, now=yesterday)
    today = datetime(2026, 1, 2, 0, 0, 1, tzinfo=UTC)
    assert ledger.day_total(conn, today) == 0  # yesterday's spend is not today's
    assert ledger.month_total(conn, today) == 900_000  # but is in the same month
    g.reserve(provider="p", model="m", purpose="x", worst_case_micro=900_000, now=today)
    assert ledger.day_total(conn, today) == 900_000
    with pytest.raises(SpendCapExceeded):  # same UTC day: second 900k breaches the 1.00 cap
        g.reserve(provider="p", model="m", purpose="x", worst_case_micro=900_000, now=today)


def test_kill_switch_blocks(tmp_path):
    s = Settings(_env_file=None, database_path=tmp_path / "k.sqlite3", kill_switch=True)
    fake = FakeProvider()
    with pytest.raises(KillSwitchActive):
        Gateway(s, fake).complete("t", MSG)
    assert fake.calls == []


def test_gateway_records_ledger_and_settles(settings, conn):
    fake = FakeProvider("hi")
    res = Gateway(settings, fake).complete("t", MSG, ref="job1")
    assert res.text == "hi" and res.cost_micro_usd >= 1
    row = conn.execute("SELECT * FROM llm_calls").fetchone()
    assert row["cost_micro_usd"] == res.cost_micro_usd and row["ref"] == "job1"
    assert conn.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0] == 1


def test_failed_call_releases_reservation(settings, conn):
    def boom(model, idx):
        raise RuntimeError("down")

    with pytest.raises(RuntimeError):
        Gateway(settings, FakeProvider(boom)).complete("t", MSG)
    assert ledger.day_total(conn) == 0


def test_no_prompt_or_completion_at_info(settings, caplog):
    fake = FakeProvider("SECRET-COMPLETION")
    msgs = [{"role": "user", "content": "SECRET-PROMPT"}]
    with caplog.at_level("INFO"):
        Gateway(settings, fake).complete("t", msgs)
    assert "SECRET" not in caplog.text


def test_ladder_escalates_only_on_validator_failure(settings, conn):
    fake = FakeProvider(lambda model, i: "good" if model == "gpt-6.1-terra" else "bad")
    gw = Gateway(settings, fake)
    res = gw.complete_with_ladder("t", MSG, validator=lambda r: r.text == "good")
    assert res.model == "gpt-6.1-terra"
    assert [m for m, _ in fake.calls] == ["gpt-6-luna", "gpt-6.1-terra"]


def test_ladder_no_escalation_when_valid(settings):
    fake = FakeProvider("good")
    Gateway(settings, fake).complete_with_ladder("t", MSG, validator=lambda r: True)
    assert len(fake.calls) == 1


def test_ladder_exhausted(settings):
    with pytest.raises(LadderExhausted):
        Gateway(settings, FakeProvider("bad")).complete_with_ladder(
            "t", MSG, validator=lambda r: False
        )


def test_schema_parsed(settings):
    fake = FakeProvider(json.dumps({"a": 1}))
    res = Gateway(settings, fake).complete("t", MSG, schema={"type": "object"})
    assert res.parsed == {"a": 1}


def test_redaction_round_trip_through_gateway(settings):
    r = Redactor(name="Jane Doe", email="jane@x.com", phone="+1 555 123 4567", address="1 Main St")
    seen = []

    def echo(model, i):
        return seen[-1]

    fake = FakeProvider(echo)
    orig = fake.complete

    def spy(model, messages, schema, mx):
        seen.append(messages[0]["content"])
        return orig(model, messages, schema, mx)

    fake.complete = spy  # type: ignore[method-assign]
    text = "I am Jane Doe, mail jane@x.com or call +1 555 123 4567, live at 1 Main St."
    res = Gateway(settings, fake, r).complete("t", [{"role": "user", "content": text}])
    for pii in ("Jane Doe", "jane@x.com", "555 123", "1 Main St"):
        assert pii not in seen[0]
    assert res.text == text


def test_timeout_is_charged_worst_case_and_raised(settings, conn):
    def boom(model, idx):
        raise ProviderTimeout("t")

    with pytest.raises(ProviderTimeout):
        Gateway(settings, FakeProvider(boom)).complete("t", MSG, max_output_tokens=1000)
    row = conn.execute("SELECT * FROM llm_calls").fetchone()
    assert row["cost_micro_usd"] > 0 and row["out_tokens"] == 1000
    assert ledger.day_total(conn) == row["cost_micro_usd"]


def test_reservation_counts_schema_and_message_overhead(settings, conn):
    gw = Gateway(settings, FakeProvider("{}"))
    seen = []
    orig = gw.guard.reserve

    def spy(**kw):
        seen.append(kw["worst_case_micro"])
        return orig(**kw)

    gw.guard.reserve = spy  # type: ignore[method-assign]
    gw.complete("t", MSG, schema=None)
    gw.complete("t", MSG, schema={"type": "object", "description": "x" * 30_000})
    assert seen[1] > seen[0]
    # "hello": ceil(5/3)=2 chars-tokens + 10 per message + 50 fixed = 62 input tokens
    assert seen[0] == pricing.worst_case_micro("gpt-6-luna", 62, 1024)


def test_invalid_json_raises_parse_error_and_keeps_cost(settings, conn):
    with pytest.raises(LLMParseError):
        Gateway(settings, FakeProvider("not json")).complete("t", MSG, schema={"type": "object"})
    row = conn.execute("SELECT * FROM llm_calls").fetchone()
    assert row["out_tokens"] > 0 and row["cost_micro_usd"] >= 1


def test_ladder_escalates_on_invalid_json(settings, conn):
    fake = FakeProvider(lambda model, i: "{}" if i == 1 else "")
    res = Gateway(settings, fake).complete_with_ladder(
        "t", MSG, validator=lambda r: True, schema={"type": "object"}
    )
    assert res.parsed == {} and [m for m, _ in fake.calls] == ["gpt-6-luna", "gpt-6.1-terra"]
    assert conn.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0] == 2
