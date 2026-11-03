---
id: OFF-2
title: Live dashboard — auto-updates on every change, shows in-progress work
owner: Web IC (under Experience EM)
status: IN_REVIEW
model: sonnet
estimate: 1.5 points
depends_on: [OFF-1]
---
## Problem (owner report)
The dashboard only changes when someone runs `python -m jobai.office build`, so it is stale during work. The owner wants it updated after EVERY change, including while a task or ticket is in progress.

## Goal
Open `http://127.0.0.1:8765/` once and watch the project update by itself within ~3 seconds of any file change, with no manual rebuild and no full-page flash.

## Scope
1. **Server** (`src/jobai/office/cli.py` + new `server.py`): ThreadingHTTPServer on 127.0.0.1 only. `GET /` fresh HTML; `GET /api/state` fresh parsed JSON; `GET /api/stamp` cheap change token (hash of mtimes+sizes under `docs/office`, `src`, `tests`, `config`, `pyproject.toml`, and `.git` HEAD/index mtime), computed in < 50 ms. Rebuild `dashboard/index.html` whenever the stamp changes so the file:// copy stays current too. New command `python -m jobai.office up` (start detached if not already running on the port, then open the browser) and `scripts/office-up.ps1`.
2. **In-place updates:** refactor `templates/app.js` so rendering is a function of the current data and can be re-run; the page polls `/api/stamp` every 3 s and, on change, fetches `/api/state` and re-renders WITHOUT reloading: keep the active tab, open ticket drawer, filters/search text and scroll position. Header shows a live indicator ("Live, updated 2 s ago", or "Offline, retrying" in amber if the server is gone). When opened via file:// (no server), fall back to reloading every 10 s and show "static copy".
3. **In-progress visibility (the key part):** new `activity.py`: collect files changed in the last 15 minutes (path, mtime, ago) and map each to a ticket using the ticket's `## Files owned` globs (fallback: infer paths such as `src/jobai/discovery/**` from the ticket text). A ticket with changes in the last 5 min gets a pulsing "active now" badge on its board card and in the drawer with the files and times; "Now" tab gets a "Recent file activity" list. Also show the git state (branch, number of uncommitted files, last commit subject).
4. **Truth over stale data:** if a ticket is IN_PROGRESS but `status.json` lists no running agent, show "work in progress (agent not registered)"; if `status.json` `updated` is older than 10 minutes while any ticket is IN_PROGRESS, show an amber "status file may be stale" note. Parse ticket Activity-log lines so the newest line is visible on the card.
5. **Tests:** fixtures only: stamp changes when a file changes and not otherwise; activity mapping from globs; state endpoint JSON shape; poll/re-render logic can be tested by extracting pure functions. Existing 79 tests must pass.

## Files owned
`src/jobai/office/**`, `tests/office/**`, `scripts/office-up.ps1`, this ticket's Activity log, `docs/office/standups/<date>-web-off2.md`. Do not edit `.claude/settings.json` (the Chief of Staff will add the auto-start hook).

## Acceptance (paste real output)
`uv run ruff check`, `uv run mypy src`, `uv run pytest -q` green. Then prove it live: start the server, open it in the built-in browser pane (`mcp__Claude_Browser__*`; load via ToolSearch if deferred), append a line to a scratch ticket file or touch a file under `src/`, and confirm in a screenshot that the page updated within ~5 s without reload and kept the open tab; take a mobile (375 px) screenshot too. Report only what you actually saw. NOTE: a dashboard server is already running on port 8765 from the old code: stop it (find the python process listening on 8765 and end only that process) and restart your new one.

## Rules
Follow docs/office/README.md. No git commit. No network calls except localhost. No secrets. Graphify: run `C:\Users\dheer\.local\bin\graphify.exe query "<question>"` before grepping; after code changes run `C:\Users\dheer\.local\bin\graphify.exe update .`. venv outside OneDrive (`UV_PROJECT_ENVIRONMENT=C:\Users\dheer\.venvs\jobai`). Files < 500 lines. Set status IN_REVIEW when done.

## Activity log
- 2026-11-04 Web IC: built live dashboard. New: `server.py` (ThreadingHTTPServer 127.0.0.1, `/`, `/api/state`, `/api/stamp`, Host-header guard, background rebuild of dashboard/index.html on stamp change), `activity.py` (recent files to ticket via `## Files owned` globs with text fallback, git state, stale/unregistered flags), `state.py`, `up` command + `scripts/office-up.ps1`. Front end split into app.js / views.js / live.js (one closure): in-place re-render keeping tab, drawer, filters, focus, scroll; 3 s stamp poll, 30 s refresh for time decay; "Live, updated N s ago" / amber "Offline, retrying" / "Static copy" (file://, reload 10 s); pulsing "Active now" badge, latest log line on cards, "Recent file activity" on Now tab.
- Verification (real output): `uv run ruff check` -> All checks passed!; `uv run mypy src` -> Success: no issues found in 36 source files; `uv run pytest -q` -> 93 passed (79 existing + 14 new, incl. node-based poll-logic and JS syntax checks). `/api/stamp` round trip 31 ms.
- Live browser proof (built-in browser, http://127.0.0.1:8765/): opened the Now tab, set `window.__marker`, created `src/jobai/office/zz_live_proof.txt`; about 5 s later the same page (marker intact, no reload, tab still Now, scroll kept) listed the file under "Recent file activity" mapped to a ticket and uncommitted count rose 34 to 35. Second proof on Board with the OFF-2 drawer open: appended to a scratch file; within 4 s the OFF-2 card showed the pulsing "Active now" badge, the drawer stayed open and listed the new file with "20 s ago". 375 px screenshots taken: no horizontal overflow (scrollWidth 375). Scratch files deleted afterwards. WP1 card shows "Work in progress (agent not registered)".
- Not verified: the amber "Offline, retrying" state and the file:// static fallback were not exercised in a browser (covered only by code and the pure-function test); the "status file may be stale" note was only unit-tested (status.json is not older than 10 min right now). `.claude/settings.json` auto-start hook is left to the Chief of Staff (command: `uv run python -m jobai.office up --no-browser`).
- Server left running on 127.0.0.1:8765 (new code; old process on that port stopped).
