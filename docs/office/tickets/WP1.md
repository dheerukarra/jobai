---
id: WP1
title: Discovery — source adapters, dedupe, storage (WP1a core + ATS fetchers; WP1b aggregators later)
owner: Backend IC (under Platform EM)
status: IN_REVIEW
model: sonnet
estimate: 5 points total (WP1a ~2.5, WP1b ~2.5)
depends_on: [WP0]
---
## Goal
Collect job postings from many sources into SQLite, deduplicated, with no LLM calls. WP1a builds the framework plus the three biggest public ATS boards; WP1b (separate ticket pass) adds aggregators, freehire API, JobSpy wrapper and company-slug harvesting.

## WP1a scope
1. **Model and interface** `src/jobai/discovery/`: pydantic `JobPosting` (source, external_id, url, apply_url, title, company_name, company_slug, location, remote: bool|None, posted_at, description_text (HTML stripped), ats, raw_json trimmed) and a `Source` protocol (`name`, `fetch(target) -> Iterable[JobPosting]`). Sources must be pluggable so WP1b adds files, not edits.
2. **Dedupe** `dedupe.py`: `canonical_url()` (lowercase host, strip utm_*/gh_src/ref params and fragments and trailing slash), `canonical_key` = `ats:company_slug:external_id`, `fingerprint` = stable hash of normalised company + title + location + remote. Same canonical_key = update `last_seen_at`; same fingerprint from a different source = recorded as an alias, not a new job. Use the existing schema in `src/jobai/migrations/0001_init.sql`; add `0002_*.sql` only if needed (e.g. `last_seen_at`, alias table); migrations stay forward-only with tests.
3. **Fetchers (verified against the real endpoints, keyless, public):** Greenhouse (`boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`), Lever (`api.lever.co/v0/postings/{slug}?mode=json`), Ashby (`api.ashbyhq.com/posting-api/job-board/{slug}`). Confirm each with a real call and record what you actually saw; `docs/02-sources-and-apply-feasibility.md` (ATS section only) lists patterns but some are UNVERIFIED.
4. **Politeness:** per-host rate limit (>= 1 s between requests, injectable clock for tests), identifying User-Agent `JobAi/0.1 (personal use)`, 20 s timeout, retry only on 429/5xx with backoff and Retry-After, never parallel to one host. No login, no cookies.
5. **Company list** `config/companies.yaml` (owner-editable): name, ats, slug. Seed >= 15 companies with at least 4 per ATS, each VERIFIED live to return a board; do not invent slugs. `discover verify` re-checks the list and reports dead slugs.
6. **Storage and CLI:** upsert companies/jobs idempotently; mark jobs `closed` after not seen for N runs (`discover mark-stale --days N`). CLI additions in `src/jobai/cli.py`: `discover run [--source S] [--max-companies N]`, `discover verify`, `discover stats` (counts by source/ats/status). Keep the CLI edit minimal.
7. **Tests (no network):** recorded fixtures (trimmed, no personal data) for each ATS; parser, canonical_url, fingerprint, alias logic, idempotent upsert, stale marking, rate-limiter with fake clock, retry/backoff with a fake transport. Existing 54 tests must still pass.

## Files owned
`src/jobai/discovery/**`, `config/companies.yaml`, `tests/discovery/**` (+ fixtures), `src/jobai/migrations/0002_*.sql` if needed, minimal edit to `src/jobai/cli.py`, this ticket's Activity log, `docs/office/standups/<date>-backend-wp1a.md`.

## Acceptance (paste real output in the Activity log)
`uv run ruff check`, `uv run mypy src`, `uv run pytest -q` green; `uv run python -m jobai discover verify` run LIVE on the seed list (<= ~40 requests total) with the real result; `discover run --max-companies 3` live, then `discover stats` showing real counts; running `discover run` twice does not duplicate rows. State clearly anything not verified live.

## Rules
Follow docs/office/README.md. No git commit. No LLM calls. No secrets. No scraping of LinkedIn/Indeed here (WP1b). Graphify: if graph exists run `C:\Users\dheer\.local\bin\graphify.exe query "<question>"` before grepping; after code changes run `C:\Users\dheer\.local\bin\graphify.exe update .`. venv outside OneDrive (`UV_PROJECT_ENVIRONMENT=C:\Users\dheer\.venvs\jobai`). Files < 500 lines. Set status IN_REVIEW when done.

## Activity log

### 2026-11-04 Backend IC — WP1a complete (status IN_REVIEW for WP1a; WP1b still open)
Built: `src/jobai/discovery/{models,dedupe,http,store,runner,cli}.py`, `sources/{greenhouse,lever,ashby,util,__init__}.py` (registry `SOURCES`; WP1b adds a file plus one entry), migration `0002_discovery.sql` (jobs: company_slug, apply_url, last_seen_at, raw_json; new `job_aliases`), `config/companies.yaml` (16 verified boards: 5 greenhouse, 5 lever, 6 ashby), 25 new tests + 3 trimmed real fixtures in `tests/discovery/`. CLI: `discover run|verify|stats|mark-stale`.
Outside owned files (needed): `pyproject.toml` (+pyyaml, +types-pyyaml dev), `tests/test_db.py` (3 hard-coded "one migration" assertions updated to two: lines 10, 13, 102). `src/jobai/cli.py` got 3 added lines.

Checks (actual output):
- `uv run ruff check` -> All checks passed!
- `uv run mypy src` -> Success: no issues found in 33 source files
- `uv run pytest -q` -> 79 passed (54 existing + 25 new)

Live `discover verify` (first pass, 16 requests): OK greenhouse stripe 748, airbnb 212, cloudflare 467, discord 34, databricks 913; lever palantir 305, spotify 86; ashby ramp 169, notion 146, openai 808, linear 32, posthog 10, supabase 69. DEAD (removed from list): lever plaid = HTTP 404; lever mistral and kraken = 200 but 0 jobs.
Second pass for replacement Lever slugs (4 requests): OK binance 5, outreach 19, zoox 224; DEAD kong = HTTP 404 (not added).
Final `companies.yaml` = only boards seen returning 200 with jobs. I did NOT re-run a full verify on the final file (would cost 16 more requests, over the ~40 cap); every entry was individually verified in the two passes above.

Live `discover run --max-companies 3` x2 (6 requests; first 3 companies = stripe, airbnb, cloudflare, all Greenhouse):
```
run 1: companies=3 fetched=1427 inserted=1427 updated=0 aliases=0 errors=0 requests=3
run 2: companies=3 fetched=1427 inserted=0 updated=1427 aliases=0 errors=0 requests=3
discover stats:
source: greenhouse=1427 | ats: greenhouse=1427 | status: new=1427
totals: aliases=0, companies=3, jobs=1427
discover mark-stale --days 7 -> closed 0 stale jobs
```
No duplicates after the second run. Live requests total: 29 (+3 for fixture capture = 32).

NOT verified live: Lever and Ashby parsing against the live DB through `discover run` (only their `verify` fetch+parse path was exercised live; parsers are covered by trimmed real fixtures). Alias path and stale marking are tested with fixtures only (no cross-source data exists yet). Politeness/backoff verified with fake clock/transport, not against a real 429. Lever EU tenants (`api.eu.lever.co`) unsupported. Greenhouse jobs whose location text lacks "remote" get `remote=None` -> stored 0 (unknown is not asserted as on-site in the model, but the DB column is NOT NULL so it stores 0).
graphify update: Rebuilt: 660 nodes, 1397 edges, 49 communities.
