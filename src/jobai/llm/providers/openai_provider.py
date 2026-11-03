"""OpenAI Chat Completions with JSON-schema structured output, retries and 60 s timeout."""

import logging
import time
from collections.abc import Callable
from typing import Any

import openai

from jobai.llm.errors import ProviderError, ProviderTimeout
from jobai.llm.providers.base import ProviderResult

log = logging.getLogger(__name__)
# Retried inside the gateway's single spend reservation. These failures are not billed:
# connection errors never reached the model, 429 and 5xx are rejected before generation.
# APITimeoutError is deliberately NOT here (it subclasses APIConnectionError, so it is
# caught first below): a timed-out request may still be billed, so it is never retried.
RETRYABLE = (
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)


class OpenAIProvider:
    name = "openai"

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 60.0,
        max_attempts: int = 4,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = openai.OpenAI(api_key=api_key, timeout=timeout, max_retries=0)
        self._max_attempts = max_attempts
        self._sleep = sleep

    def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None,
        max_output_tokens: int,
    ) -> ProviderResult:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_completion_tokens": max_output_tokens,
        }
        if schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "result", "schema": schema, "strict": True},
            }
        resp = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                resp = self._client.chat.completions.create(**kwargs)
                break
            except openai.APITimeoutError as exc:
                raise ProviderTimeout("openai request timed out (may still be billed)") from exc
            except RETRYABLE as exc:
                if attempt == self._max_attempts:
                    raise ProviderError(f"openai failed after {attempt} attempts") from exc
                delay = min(2.0**attempt, 20.0)
                log.warning("openai transient (%s); retry in %.0fs", type(exc).__name__, delay)
                self._sleep(delay)
            except openai.OpenAIError as exc:
                raise ProviderError(f"openai error: {type(exc).__name__}") from exc
        if resp is None:
            raise ProviderError("openai returned no response")
        usage = resp.usage
        details = usage.prompt_tokens_details if usage else None
        return ProviderResult(
            text=resp.choices[0].message.content or "",
            in_tokens=usage.prompt_tokens if usage else 0,
            cached_tokens=(details.cached_tokens or 0) if details else 0,
            out_tokens=usage.completion_tokens if usage else 0,
        )
