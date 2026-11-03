import httpx
import pytest

from jobai.discovery.http import USER_AGENT, HttpStatusError, PoliteClient
from jobai.discovery.models import FetchError


class Fake:
    """Fake clock: sleep advances time."""

    def __init__(self) -> None:
        self.t = 100.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s


def _client(handler, fake):
    return PoliteClient(transport=httpx.MockTransport(handler), clock=fake.clock, sleep=fake.sleep)


def test_same_host_requests_spaced_and_user_agent_sent():
    fake, seen = Fake(), []

    def h(req):
        seen.append(req.headers["user-agent"])
        return httpx.Response(200, json={"ok": True})

    c = _client(h, fake)
    c.get_json("https://api.lever.co/a")
    c.get_json("https://api.lever.co/b")
    assert seen == [USER_AGENT, USER_AGENT] and USER_AGENT == "JobAi/0.1 (personal use)"
    assert len(fake.sleeps) == 1 and fake.sleeps[0] == pytest.approx(1.0)


def test_different_hosts_not_delayed():
    fake = Fake()
    c = _client(lambda r: httpx.Response(200, json=[]), fake)
    c.get_json("https://a.example/x")
    c.get_json("https://b.example/x")
    assert fake.sleeps == []


def test_retry_429_honours_retry_after_then_succeeds():
    fake, calls = Fake(), []

    def h(req):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "7"})
        return httpx.Response(200, json={"a": 1})

    assert _client(h, fake).get_json("https://x.example/") == {"a": 1}
    assert 7.0 in fake.sleeps and len(calls) == 2


def test_5xx_exponential_backoff_then_gives_up():
    fake, calls = Fake(), []

    def h(req):
        calls.append(1)
        return httpx.Response(503)

    with pytest.raises(HttpStatusError) as ei:
        _client(h, fake).get_json("https://x.example/")
    assert ei.value.status == 503 and len(calls) == 3
    assert 2.0 in fake.sleeps and 4.0 in fake.sleeps


def test_404_not_retried():
    fake, calls = Fake(), []

    def h(req):
        calls.append(1)
        return httpx.Response(404)

    with pytest.raises(HttpStatusError) as ei:
        _client(h, fake).get_json("https://x.example/")
    assert ei.value.status == 404 and len(calls) == 1


def test_timeout_and_bad_json_are_fetch_errors():
    fake = Fake()

    def boom(req):
        raise httpx.ReadTimeout("t", request=req)

    with pytest.raises(FetchError):
        _client(boom, fake).get_json("https://x.example/")
    with pytest.raises(FetchError):
        _client(lambda r: httpx.Response(200, text="<html>"), fake).get_json("https://y.example/")
