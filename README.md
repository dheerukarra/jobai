# JobAi

Personal job-application automation (single user). Python 3.12+, SQLite, OpenAI-first LLM gateway
with a model ladder, hard spend caps, dry-run default and a kill switch.

## Setup
    scripts/dev.ps1            # Windows (venv at C:\Users\dheer\.venvs\jobai, outside OneDrive)
    scripts/dev.sh             # POSIX
    cp .env.example .env       # then add OPENAI_API_KEY (never commit it)

## Commands (set UV_PROJECT_ENVIRONMENT first, see scripts/)
    uv run python -m jobai migrate
    uv run python -m jobai spend
    uv run python -m jobai llm-smoke --yes   # one tiny paid call; needs a key
    uv run ruff check && uv run mypy && uv run pytest -q
