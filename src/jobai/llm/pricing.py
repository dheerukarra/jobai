"""Price table in integer micro-USD per 1M tokens ($1.00 per 1M tokens == 1_000_000)."""

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime

log = logging.getLogger(__name__)

# Real verification date of the table below (docs/04 decision 7); do not bump without re-checking.
VERIFIED_AT = date(2026, 11, 3)
STALE_DAYS = 30
PER = 1_000_000


@dataclass(frozen=True)
class Price:
    input: int
    cached_input: int
    output: int
    verified_at: date = VERIFIED_AT


PRICES: dict[str, Price] = {
    "gpt-6-luna": Price(100_000, 10_000, 500_000),
    "gpt-5-nano": Price(50_000, 5_000, 400_000),
    "gpt-6.1-terra": Price(1_000_000, 50_000, 5_000_000),
    "gpt-5.4-mini": Price(750_000, 75_000, 4_500_000),
    "gpt-6.1-sol": Price(2_000_000, 100_000, 10_000_000),
}


def get_price(model: str, today: date | None = None) -> Price:
    try:
        price = PRICES[model]
    except KeyError:
        raise KeyError(f"no price for model {model!r}; refusing to spend blind") from None
    today = today or datetime.now(UTC).date()
    age = (today - price.verified_at).days
    if age > STALE_DAYS:
        log.warning("PRICE TABLE STALE: %s verified %d days ago; re-check prices", model, age)
    return price


def cost_micro(
    model: str, in_tokens: int, cached_tokens: int, out_tokens: int, today: date | None = None
) -> int:
    """in_tokens is total prompt tokens (cached included). Integer math, rounded up."""
    p = get_price(model, today)
    cached = min(cached_tokens, in_tokens)
    total = (in_tokens - cached) * p.input + cached * p.cached_input + out_tokens * p.output
    return -(-total // PER)


def worst_case_micro(model: str, est_in_tokens: int, max_out_tokens: int) -> int:
    return cost_micro(model, est_in_tokens, 0, max_out_tokens)


def format_usd(micro: int) -> str:
    return f"${micro // PER}.{micro % PER:06d}"
