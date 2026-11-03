"""Single entry point for LLM calls. Never logs prompts or completions."""

import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from jobai.config import Settings
from jobai.llm import pricing
from jobai.llm.caps import SpendGuard
from jobai.llm.errors import LadderExhausted, LLMParseError, ProviderTimeout
from jobai.llm.providers.base import Provider
from jobai.llm.redact import Redactor

log = logging.getLogger(__name__)
Messages = list[dict[str, str]]


@dataclass(frozen=True)
class LLMResult:
    text: str
    parsed: Any
    model: str
    in_tokens: int
    cached_tokens: int
    out_tokens: int
    cost_micro_usd: int


class Gateway:
    def __init__(
        self, settings: Settings, provider: Provider, redactor: Redactor | None = None
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.redactor = redactor
        self.guard = SpendGuard(settings)

    def complete(
        self,
        purpose: str,
        messages: Messages,
        schema: dict[str, Any] | None = None,
        ladder: Sequence[str] | None = None,
        max_output_tokens: int = 1024,
        ref: str | None = None,
    ) -> LLMResult:
        """One call on the first model of `ladder` (default: triage model)."""
        model = (ladder or [self.settings.triage_model])[0]
        return self._call(purpose, messages, schema, model, max_output_tokens, ref)

    def complete_with_ladder(
        self,
        purpose: str,
        messages: Messages,
        validator: Callable[[LLMResult], bool],
        schema: dict[str, Any] | None = None,
        ladder: Sequence[str] | None = None,
        max_output_tokens: int = 1024,
        ref: str | None = None,
    ) -> LLMResult:
        """Escalate to the next model only when the caller's validator rejects the result."""
        models = list(ladder or self.settings.tailor_models)
        for i, model in enumerate(models):
            try:
                res = self._call(purpose, messages, schema, model, max_output_tokens, ref)
            except LLMParseError:
                # Unparseable output counts as a rejected result; cost is already recorded.
                log.info("ladder: %s returned unparseable output; escalating (%s)", model, purpose)
                continue
            if validator(res):
                return res
            if i + 1 < len(models):
                log.info("ladder: %s rejected by validator; escalating (%s)", model, purpose)
        raise LadderExhausted(f"no model in {models} passed validation for {purpose}")

    def _call(
        self,
        purpose: str,
        messages: Messages,
        schema: dict[str, Any] | None,
        model: str,
        max_output_tokens: int,
        ref: str | None,
    ) -> LLMResult:
        sent = messages
        if self.redactor:
            sent = [{**m, "content": self.redactor.redact(m["content"])} for m in messages]
        chars = sum(len(m["content"]) for m in sent)
        if schema is not None:
            chars += len(json.dumps(schema))  # response_format is billed as prompt tokens
        est_in = -(-chars // 3) + 10 * len(sent) + 50  # ceil(chars/3) + framing overhead
        worst = pricing.worst_case_micro(model, est_in, max_output_tokens)
        rid = self.guard.reserve(
            provider=self.provider.name,
            model=model,
            purpose=purpose,
            worst_case_micro=worst,
            ref=ref,
        )
        try:
            out = self.provider.complete(model, sent, schema, max_output_tokens)
        except ProviderTimeout:
            # A timed-out request may still be billed: treat the worst case as spent.
            self.guard.settle(
                rid,
                in_tokens=est_in,
                cached_tokens=0,
                out_tokens=max_output_tokens,
                cost_micro=worst,
            )
            log.warning("llm timeout purpose=%s model=%s; charged worst %d", purpose, model, worst)
            raise
        except BaseException:
            self.guard.release(rid)
            raise
        cost = pricing.cost_micro(model, out.in_tokens, out.cached_tokens, out.out_tokens)
        self.guard.settle(
            rid,
            in_tokens=out.in_tokens,
            cached_tokens=out.cached_tokens,
            out_tokens=out.out_tokens,
            cost_micro=cost,
        )
        text = self.redactor.restore(out.text) if self.redactor else out.text
        log.info(
            "llm call purpose=%s model=%s in=%d cached=%d out=%d cost_micro=%d",
            purpose, model, out.in_tokens, out.cached_tokens, out.out_tokens, cost,
        )
        parsed = None
        if schema is not None:
            try:
                parsed = json.loads(text)
            except ValueError as exc:
                raise LLMParseError(f"model {model} returned invalid JSON for {purpose}") from exc
        return LLMResult(
            text, parsed, model, out.in_tokens, out.cached_tokens, out.out_tokens, cost
        )
