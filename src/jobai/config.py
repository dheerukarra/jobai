"""Settings from environment / .env. Money is Decimal in config, integer micro-USD elsewhere."""

from decimal import ROUND_FLOOR, Decimal
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

MICRO = 1_000_000
# Secrets live outside the project (the project folder syncs to OneDrive). Later files win.
SECRETS_ENV = Path.home() / ".jobai" / "secrets.env"


def usd_to_micro(value: Decimal) -> int:
    # Floor: a cap must never round up to allow more than configured.
    return int((value * MICRO).to_integral_value(rounding=ROUND_FLOOR))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", str(SECRETS_ENV)),
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    openai_api_key: SecretStr | None = None
    database_path: Path = Path("data/jobai.sqlite3")
    daily_cap_usd: Decimal = Decimal("1.00")
    monthly_cap_usd: Decimal = Decimal("8.00")
    kill_switch: bool = False
    dry_run: bool = True
    triage_model: str = "gpt-6-luna"
    tailor_models: list[str] = ["gpt-6-luna", "gpt-6.1-terra", "gpt-6.1-sol"]
    mapping_model: str = "gpt-6-luna"

    @property
    def daily_cap_micro(self) -> int:
        return usd_to_micro(self.daily_cap_usd)

    @property
    def monthly_cap_micro(self) -> int:
        return usd_to_micro(self.monthly_cap_usd)


def get_settings() -> Settings:
    return Settings()
