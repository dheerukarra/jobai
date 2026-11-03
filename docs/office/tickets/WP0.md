---
id: WP0
title: Foundation — Python project, SQLite schema, config, LLM gateway, CI, tests
owner: Backend IC (under Platform EM)
status: IN_REVIEW
model: sonnet
estimate: 3 points
depends_on: []
---
## Goal
A clean Python project in `C:\Users\dheer\OneDrive\Desktop\JobAi` that later WPs build on. No live network calls and no API key needed to pass tests.

## Decisions to honor (docs/04 section 3)
Python single stack, SQLite, FastAPI later, OpenAI-first provider with a model ladder, hard spend caps, dry-run default, kill switch, no secrets in the repo.

## Files owned
`pyproject.toml`, `src/jobai/**`, `migrations/**`, `tests/**`, `scripts/**`, `.github/workflows/ci.yml`, `.gitignore`, `.env.example`, `README.md`, `ruff` config. Do not edit `docs/**` except appending to this ticket's Activity log and writing `docs/office/standups/<date>-backend.md`.

## Tasks
1. **Project**: `pyproject.toml` (uv, Python >= 3.12), package `jobai` under `src/`, dev deps pytest, ruff, mypy. Runtime deps minimal: pydantic, pydantic-settings, httpx, openai. venv lives OUTSIDE OneDrive: provide `scripts/dev.ps1` and `scripts/dev.sh` that set `UV_PROJECT_ENVIRONMENT` to `C:\Users\dheer\.venvs\jobai` (or `~/.venvs/jobai`) then run `uv sync`. `.gitignore` covers `.env`, `.venv`, `__pycache__`, `graphify-out/cache`, `data/`, `*.sqlite3`.
2. **Config** `jobai/config.py` (pydantic-settings, reads `.env`): `OPENAI_API_KEY` (SecretStr, optional), `DATABASE_PATH` (default `data/jobai.sqlite3`), `DAILY_CAP_USD` (default 1.00), `MONTHLY_CAP_USD` (default 8.00), `KILL_SWITCH` (false), `DRY_RUN` (true), model ladder names with defaults (`triage=gpt-6-luna`, `tailor=[gpt-6-luna, gpt-6.1-terra, gpt-6.1-sol]`, `mapping=gpt-6-luna`). `.env.example` has placeholders only.
3. **DB** `jobai/db.py` + `migrations/0001_init.sql` + a tiny forward-only migration runner (applied versions in `schema_migrations`). Tables: `companies`, `jobs` (source, external_id, url, canonical_key UNIQUE, fingerprint, title, company_id, location, remote, posted_at, description, ats, status, first_seen_at), `job_scores`, `applications` (job_id UNIQUE, route auto|assisted|skip, status, resume_path, answers_json, submitted_at, error), `llm_calls` (ts, provider, model, purpose, in_tokens, cached_tokens, out_tokens, cost_micro_usd, ref), `settings`, `events`. WAL mode, foreign keys on.
4. **LLM gateway** `jobai/llm/`: `gateway.py` (single entry point `complete(purpose, messages, schema=None, ladder=...)`), `providers/base.py` protocol, `providers/openai_provider.py` (Chat Completions or Responses with JSON-schema structured output; retries with backoff; timeout 60 s), `providers/fake.py` for tests, `pricing.py` (price table keyed by model with `verified_at` and a loud warning when older than 30 days; initial values from docs/04 decision 7), `ledger.py` (records every call; computes day and month totals), `caps.py` (reserve worst-case cost BEFORE each call; refuse with `SpendCapExceeded` at the daily/monthly cap; 80% warning; respects `KILL_SWITCH`), `redact.py` (replace name, email, phone, address with placeholders before the call and restore after; round-trip tested). Never log prompts or completions at INFO. Escalation helper: `complete_with_ladder(...)` moves to the next model only when a caller-supplied validator fails.
5. **CLI** `jobai/cli.py` (`python -m jobai`): `migrate`, `spend` (prints today/month spend and caps), `llm-smoke` (one tiny call; refuses unless a key is set and `--yes`).
6. **Tests** (pytest, no network): migrations apply and are idempotent; schema constraints (dedupe unique keys); pricing math (integer micro-USD, no float drift); cap reservation (denies at cap, allows below, concurrency-safe via a DB transaction); kill switch blocks; redact round-trip; ladder escalation with fake provider; config defaults and secret not printed in `repr`.
7. **CI** `.github/workflows/ci.yml`: uv sync, ruff check, mypy on `src`, pytest.

## Acceptance (paste evidence into Activity log)
`uv run ruff check`, `uv run pytest -q` green; `python -m jobai migrate` creates the DB; `python -m jobai spend` prints caps; no secrets in files; every file < 500 lines.

## Rules
Follow `docs/office/README.md`. No git commit. No network calls in tests. Do not run `graphify install`. If graph exists, use `graphify query` before grepping; after finishing code run `C:\Users\dheer\.local\bin\graphify.exe update .`. Set `status: IN_REVIEW` when done.

## Activity log
- 2026-11-03 Backend IC: WP0 implemented (pyproject, config, db + 0001_init migration, llm gateway/providers/pricing/ledger/caps/redact, cli, 29 tests, CI, scripts). Venv at C:\Users\dheer\.venvs\jobai (outside OneDrive; no .venv in project).
  Verification (real output):
  - `uv run ruff check` -> All checks passed!
  - `uv run pytest -q` -> 29 passed (no network)
  - `uv run mypy src` -> Success: no issues found in 16 source files
  - `uv run python -m jobai migrate` -> applied: 0001_init (second run: nothing (up to date))
  - `uv run python -m jobai spend` -> today $0.000000 / cap $1.000000; month $0.000000 / cap $8.000000; kill_switch=False dry_run=True
  - Largest file 148 lines. `graphify update .` succeeded (286 nodes, 490 edges).
  - NOT verified: the real OpenAI provider and `llm-smoke` (no key, no network by design); structured-output support on gpt-6* models and rate-limit tier remain to verify with the owner's key.
- 2026-11-04 Backend IC: fixes for platform-em-WP0 review (P1-1,2,3,5,6,7 + P2-3,6,11, day-boundary test). P1-4 (DRY_RUN) left for WP4.
  Changes: timeout is never retried and is settled at worst-case (ProviderTimeout); other retryable errors (connection, 429, 5xx) retry inside the one reservation (unbilled; commented). est_in now = ceil(chars/3) + schema JSON + 10/message + 50. Invalid JSON -> LLMParseError (cost kept); ladder treats it as rejected and escalates. Migrations run per-file in BEGIN IMMEDIATE with rollback, version recorded on success, missing/empty dir raises MigrationError; moved to src/jobai/migrations/ (ships in wheel); 0001_init.sql edited in place with CHECKs (status enums, non-negative tokens/cost); local data/jobai.sqlite3 deleted and recreated. connect() sets busy_timeout before WAL and retries (found by concurrent-migrate test). Redactor repr/str hide PII. Cap rounding now explicit ROUND_FLOOR (a cap never rounds up). VERIFIED_AT stays 2026-11-03 (the actual verification date; the review's P1-5 concern was the stale-warning test, now added).
  Verification (real output):
  - `uv run ruff check` -> All checks passed!
  - `uv run pytest -q` -> 44 passed (3 consecutive runs, no network)
  - `uv run mypy src` -> Success: no issues found in 16 source files
  - `uv run python -m jobai migrate` (fresh DB) -> applied: 0001_init ; second run -> applied: nothing (up to date)
  - `uv run python -m jobai spend` -> today : $0.000000 / cap $1.000000; month : $0.000000 / cap $8.000000; kill_switch=False dry_run=True
  - Largest file 204 lines. `graphify update .` succeeded.
