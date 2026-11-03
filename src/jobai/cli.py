"""`python -m jobai` commands: migrate, spend, llm-smoke."""

import argparse
import logging
import sys

from jobai import db
from jobai.config import get_settings
from jobai.llm import ledger
from jobai.llm.pricing import format_usd


def _cmd_migrate(_: argparse.Namespace) -> int:
    s = get_settings()
    conn = db.connect(s.database_path)
    applied = db.migrate(conn)
    print(f"database: {s.database_path}")
    print("applied: " + (", ".join(applied) if applied else "nothing (up to date)"))
    return 0


def _cmd_spend(_: argparse.Namespace) -> int:
    s = get_settings()
    conn = db.connect(s.database_path)
    db.migrate(conn)
    day, month = ledger.day_total(conn), ledger.month_total(conn)
    print(f"today : {format_usd(day)} / cap {format_usd(s.daily_cap_micro)}")
    print(f"month : {format_usd(month)} / cap {format_usd(s.monthly_cap_micro)}")
    print(f"kill_switch={s.kill_switch} dry_run={s.dry_run}")
    return 0


def _cmd_smoke(args: argparse.Namespace) -> int:
    s = get_settings()
    if s.openai_api_key is None:
        print("refusing: OPENAI_API_KEY is not set", file=sys.stderr)
        return 2
    if not args.yes:
        print("refusing: this makes one real (tiny, paid) call; pass --yes", file=sys.stderr)
        return 2
    from jobai.llm.gateway import Gateway
    from jobai.llm.providers.openai_provider import OpenAIProvider

    gw = Gateway(s, OpenAIProvider(s.openai_api_key.get_secret_value()))
    res = gw.complete(
        "smoke",
        [{"role": "user", "content": "Reply with the single word: ok"}],
        ladder=[s.triage_model],
        max_output_tokens=16,
    )
    print(f"model={res.model} cost={format_usd(res.cost_micro_usd)} reply_chars={len(res.text)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="jobai")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate").set_defaults(fn=_cmd_migrate)
    sub.add_parser("spend").set_defaults(fn=_cmd_spend)
    sm = sub.add_parser("llm-smoke")
    sm.add_argument("--yes", action="store_true")
    sm.set_defaults(fn=_cmd_smoke)
    args = p.parse_args(argv)
    return int(args.fn(args))
