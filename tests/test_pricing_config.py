from datetime import date
from decimal import Decimal

import pytest

from jobai.config import Settings
from jobai.llm import pricing


def test_cost_integer_exact():
    # luna: 1M in @0.10 = 100_000 micro; 1M out @0.50 = 500_000 micro
    assert pricing.cost_micro("gpt-6-luna", 1_000_000, 0, 0) == 100_000
    assert pricing.cost_micro("gpt-6-luna", 0, 0, 1_000_000) == 500_000
    assert pricing.cost_micro("gpt-6-luna", 1_000_000, 1_000_000, 0) == 10_000


def test_cost_no_float_drift_and_rounds_up():
    total = sum(pricing.cost_micro("gpt-6-luna", 1000, 0, 0) for _ in range(1000))
    assert isinstance(total, int)
    assert total == 100_000  # 1000 tokens @0.10/1M = 100 micro, exact
    assert pricing.cost_micro("gpt-6-luna", 1, 0, 0) == 1  # ceil of 0.1


def test_unknown_model_refused():
    with pytest.raises(KeyError):
        pricing.cost_micro("nope", 1, 0, 1)


def test_stale_price_warns(caplog):
    with caplog.at_level("WARNING"):
        pricing.get_price("gpt-6-luna", today=date(2027, 1, 1))
    assert "STALE" in caplog.text


def test_format_usd():
    assert pricing.format_usd(1_500_000) == "$1.500000"


def test_config_defaults():
    s = Settings(_env_file=None)
    assert s.daily_cap_usd == Decimal("1.00") and s.monthly_cap_usd == Decimal("8.00")
    assert s.daily_cap_micro == 1_000_000 and s.monthly_cap_micro == 8_000_000
    assert s.kill_switch is False and s.dry_run is True
    assert s.triage_model == "gpt-6-luna" and s.mapping_model == "gpt-6-luna"
    assert s.tailor_models == ["gpt-6-luna", "gpt-6.1-terra", "gpt-6.1-sol"]
    assert str(s.database_path).replace("\\", "/") == "data/jobai.sqlite3"


def test_secret_not_in_repr():
    s = Settings(_env_file=None, openai_api_key="sk-test-123")
    assert "sk-test-123" not in repr(s) and "sk-test-123" not in str(s)
    assert s.openai_api_key.get_secret_value() == "sk-test-123"


def test_verified_at_is_real_and_stale_after_30_days(caplog):
    assert date(2026, 11, 3) == pricing.VERIFIED_AT
    with caplog.at_level("WARNING"):
        pricing.get_price("gpt-6-luna", today=date(2026, 12, 3))  # 30 days: ok
    assert "STALE" not in caplog.text
    with caplog.at_level("WARNING"):
        pricing.get_price("gpt-6-luna", today=date(2026, 12, 4))  # 31 days: warns
    assert "STALE" in caplog.text


def test_cap_rounding_never_rounds_up():
    assert Settings(_env_file=None, daily_cap_usd="1.0000015").daily_cap_micro == 1_000_001
    assert Settings(_env_file=None, daily_cap_usd="1.0000025").daily_cap_micro == 1_000_002
