"""Deterministic provider for tests. No network."""

from collections.abc import Callable
from typing import Any

from jobai.llm.providers.base import ProviderResult


class FakeProvider:
    name = "fake"

    def __init__(self, responder: Callable[[str, int], str] | list[str] | str = "ok") -> None:
        self._responder = responder
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None,
        max_output_tokens: int,
    ) -> ProviderResult:
        idx = len(self.calls)
        self.calls.append((model, messages))
        r = self._responder
        if callable(r):
            text = r(model, idx)
        elif isinstance(r, list):
            text = r[min(idx, len(r) - 1)]
        else:
            text = r
        in_tokens = sum(len(m["content"]) for m in messages) // 4 + 1
        return ProviderResult(text, in_tokens, 0, len(text) // 4 + 1)
