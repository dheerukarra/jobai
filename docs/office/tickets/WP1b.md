---
id: WP1b
title: Discovery — keyless aggregators, freehire API, optional JobSpy, board-slug harvesting
owner: Backend IC (under Platform EM)
status: IN_REVIEW
model: sonnet
estimate: 2.5 points
depends_on: [WP1]
---
## Goal
More postings from many sources, using the WP1a framework (`Source` protocol, dedupe, polite HTTP client, store, runner). No LLM calls.

## Scope
1. **Keyless aggregator sources** (verify each against the real endpoint; if one is down, gated or against its stated terms, skip it and say so): Remotive (`remotive.com/api/remote-jobs`), RemoteOK (`remoteok.com/api`, honour its attribution/terms), Arbeitnow (`arbeitnow.com/api/job-board-api`), Hacker News "Who is hiring" (Algolia HN API: latest monthly thread comments), The Muse public API if keyless, and the **freehire public API** (per its OpenAPI at github.com/strelov1/freehire `web/static/openapi.yaml`; keyless, personal use, IT jobs only, per-address rate limit: read and respect `Retry-After`; keep requests minimal and cache). Each is a new file under `src/jobai/discovery/sources/`; normalise into `JobPosting`; the aggregator's own id becomes `external_id`, and fingerprint dedupe links duplicates across sources.
2. **Keyed sources (do NOT enable):** Adzuna and USAJobs need free API keys the owner does not have yet. Only read optional env vars `ADZUNA_APP_ID/ADZUNA_APP_KEY`; if unset the source is skipped with a clear message.
3. **Board-slug harvesting:** from fetched postings' apply/job URLs extract `boards.greenhouse.io|job-boards.greenhouse.io/{slug}`, `jobs.lever.co/{slug}`, `jobs.ashbyhq.com/{slug}` into a new table `discovered_boards` (ats, slug, first_seen, source, verified_at, status) via migration `0003_*.sql`. `discover harvest` lists new candidates; `discover verify-harvested` checks each with the polite client (cap per run) and marks alive/dead; NEVER edit `config/companies.yaml` automatically: print a ready-to-paste YAML snippet.
4. **JobSpy (optional, off by default):** wrapper `sources/jobspy_source.py` behind an optional dependency extra `[jobspy]` in pyproject (python-jobspy). First check the project's real maintenance status (PyPI release date, GitHub last push) and report it. Logged-out scraping only (no accounts, no cookies), strict rate limits, small result counts, clear warning that LinkedIn/Indeed/Glassdoor/ZipRecruiter terms forbid scraping, discovery only (never an apply target). Do one tiny live query (<= 2 requests) if the package installs cleanly and report exactly what happened; if it fails, record that honestly.
5. **CLI:** extend `discover run --source <name>` to accept the new sources and `all`; keep per-source polite limits; add `discover sources` (list sources, enabled/disabled and why).
6. **Tests (no network):** recorded trimmed fixtures per source; parser tests; harvest regex tests with tricky URLs; migration test; verify-harvested with a fake transport; JobSpy wrapper tested with a stub. Existing 93 tests must pass.

## Files owned
`src/jobai/discovery/**`, `src/jobai/migrations/0003_*.sql`, `tests/discovery/**`, `pyproject.toml` (optional extra only), minimal `src/jobai/cli.py` edit, this ticket's Activity log, `docs/office/standups/<date>-backend-wp1b.md`. Do not touch `config/companies.yaml` except by printing suggestions.

## Acceptance (paste real output)
`uv run ruff check`, `uv run mypy src`, `uv run pytest -q` green. Live runs, <= ~60 requests total across all hosts, one host at a time: `discover sources`; `discover run --source <each working source>` with small limits; `discover stats` before/after; `discover harvest` and one `discover verify-harvested --max 10`; second identical run adds no duplicates. State plainly which sources worked, which did not and why, and what was not verified.

## Rules
Follow docs/office/README.md. No git commit. No LLM calls. No secrets. Graphify: run `C:\Users\dheer\.local\bin\graphify.exe query "<question>"` before grepping; after code changes run `C:\Users\dheer\.local\bin\graphify.exe update .`. venv outside OneDrive (`UV_PROJECT_ENVIRONMENT=C:\Users\dheer\.venvs\jobai`). Files < 500 lines. Update the Activity log and standup as you go (the owner watches a live dashboard). Set status IN_REVIEW when done.

## Activity log
- 17:03 Backend IC: read spec + WP1a code; now probing live endpoints (curl, counted; budget 60) to capture trimmed fixtures.
- 17:05 Live probes OK (curl, 9 requests so far): remotive, remoteok, arbeitnow, themuse, hn-algolia, freehire all keyless 200. Now writing aggregator sources, migration 0003, harvest, CLI.
- 17:06 Done: remotive/remoteok/arbeitnow/themuse/freehire parsers, boards.py (harvest+verify), migration 0003, http cache. On: hn_hiring, adzuna, jobspy, registry, CLI, tests.
- 17:09 Done: all source modules, registry, runner.run_aggregators, CLI (sources/harvest/verify-harvested), ruff+mypy clean, 93 tests pass (test_db.py migration-count asserts made dynamic: new 0003 migration). On: fixtures + tests, then live runs.
- 17:10 Tests written (fixtures from real trimmed responses). Now running live CLI acceptance runs.
- 17:12 Live runs done (26 requests so far incl. probes): 6 aggregators OK, 6 boards harvested+verified alive. On: JobSpy install + one tiny query, then docs.
- Verification (real output):
  - `uv run ruff check` -> All checks passed!
  - `uv run mypy src` -> Success: no issues found in 45 source files
  - `uv run pytest -q` -> 132 passed (93 existing + 39 new; tests/test_db.py migration-count asserts made dynamic because 0003 is a new migration)
  - `graphify update .` -> code graph updated.
- Live (CLI, polite client, UA `JobAi/0.1 (personal use)`, one host at a time). Total ~26 HTTP requests incl. probes (limit ~60):
  - `discover sources` -> remotive/remoteok/arbeitnow/themuse/hn_hiring/freehire enabled; adzuna DISABLED (no keys); jobspy DISABLED (extra not installed, off by default); usajobs DISABLED (needs key, not implemented).
  - stats before: `greenhouse=1427, jobs=1607 after`. Runs: remotive fetched=10 (API returned only 10 despite limit=30), remoteok 30, arbeitnow 30, themuse 20, hn_hiring 60 (6 new boards), freehire 30. All inserted, errors=0.
  - The Muse: first attempt timed out (20 s, transient); retry fine, 200.
  - stats after: arbeitnow=30, freehire=30, greenhouse=1427, hn_hiring=60, remoteok=30, remotive=10, themuse=20; totals jobs=1607, aliases=0, companies=140.
  - Second identical runs: inserted=0 updated=N for every source, so no duplicates. CAVEAT: these were served from the 1h/6h on-disk cache (requests=0), so they prove dedupe, not that the live feed is stable.
  - `discover harvest` -> 6 candidates (all via hn_hiring). `discover verify-harvested --max 10` -> 6 checked, all ALIVE: lever apolloresearch 12 jobs, greenhouse controlplane 4, ashby proxima-fusion 55, ashby charge-robotics 13, greenhouse reddit 162, greenhouse justworks 105; YAML snippet printed, config/companies.yaml NOT edited.
- Source terms: Remotive (link back + name source, <=4 fetches/day, cached 6h; no resubmitting to third-party boards), Remote OK (link back with follow + name source), Arbeitnow (don't abuse, link back appreciated), freehire (keyless personal/non-commercial only, 120/min 2000/day, Retry-After honoured), The Muse (keyless, 500/h). Attribution lines are printed after each run.
- JobSpy: python-jobspy 1.4.1 released 2026-10-23, GitHub speedyapply/JobSpy last push 2026-10-27, not archived, MIT, 4.6k stars -> actively maintained. `uv run --extra jobspy` installs cleanly (pandas, curl-cffi, ...) and imports. The single tiny live query (Indeed, 3 results) was BLOCKED by the Claude Code auto-mode permission classifier (scraping a ToS-forbidden site); I did not work around it. So JobSpy live behaviour is NOT verified; the wrapper is tested with a stub only. The owner can run `uv run --extra jobspy python -m jobai discover run --source jobspy --limit 3` themselves.
- NOT verified live: Adzuna (no keys; parser tested on a minimal hand-written payload, endpoint format from Adzuna docs/memory, key redaction tested), JobSpy, USAJobs (not implemented), HN thread coverage beyond page 1 of comments (HN heuristic: "Company | Role | ..." first line; replies skipped; e.g. "Estuary | US-Based / Remote | Full-time" yields title "US-Based / Remote").
- Note: pyproject gained `[project.optional-dependencies] jobspy` and a mypy override for `jobspy`; uv.lock was re-resolved by `uv run --extra jobspy` (lead should review that diff). Status set to IN_REVIEW.
