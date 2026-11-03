"""OpenAIProvider against a mocked client. No network."""

import httpx
import openai
import pytest

from jobai.llm.errors import ProviderError, ProviderTimeout
from jobai.llm.providers.openai_provider import OpenAIProvider

REQ = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
MSG = [{"role": "user", "content": "hi"}]


class _Usage:
    prompt_tokens = 10
    completion_tokens = 5
    prompt_tokens_details = None


class _Message:
    content = "ok"


class _Choice:
    message = _Message()


class _Resp:
    usage = _Usage()
    choices = [_Choice()]


class _Client:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.calls += 1
        o = self.outcomes.pop(0)
        if isinstance(o, Exception):
            raise o
        return o


def _provider(outcomes):
    sleeps: list[float] = []
    p = OpenAIProvider("sk-test", sleep=sleeps.append)
    client = _Client(outcomes)
    p._client = client  # type: ignore[assignment]
    return p, client, sleeps


def test_429_then_success_retries():
    rl = openai.RateLimitError("rl", response=httpx.Response(429, request=REQ), body=None)
    p, client, sleeps = _provider([rl, _Resp()])
    out = p.complete("gpt-6-luna", MSG, None, 100)
    assert out.text == "ok" and out.in_tokens == 10 and client.calls == 2
    assert len(sleeps) == 1


def test_400_not_retried():
    err = openai.BadRequestError("bad", response=httpx.Response(400, request=REQ), body=None)
    p, client, sleeps = _provider([err, _Resp()])
    with pytest.raises(ProviderError):
        p.complete("gpt-6-luna", MSG, None, 100)
    assert client.calls == 1 and sleeps == []


def test_timeout_not_retried_and_typed():
    p, client, sleeps = _provider([openai.APITimeoutError(request=REQ), _Resp()])
    with pytest.raises(ProviderTimeout):
        p.complete("gpt-6-luna", MSG, None, 100)
    assert client.calls == 1 and sleeps == []
