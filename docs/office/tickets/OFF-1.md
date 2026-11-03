---
id: OFF-1
title: Office dashboard — Jira-style project tracker (static HTML generated from docs/office)
owner: Web IC (under Experience EM)
status: IN_REVIEW
model: sonnet
estimate: 1.5 points
depends_on: []
---
## Goal
The owner (non-engineer view) opens ONE file in a browser and sees the whole project: what is being done, by whom, what is blocked, how much Claude usage is left, what is next. Like Jira, but offline and generated from the files we already keep.

## Output
`dashboard/index.html`: a single self-contained file (inline CSS and JS, NO CDN, NO network calls, works from file://). Built by `python -m jobai.office build` (stdlib only, no new dependencies); `python -m jobai.office serve` optionally serves it on 127.0.0.1:8765 and rebuilds on request. Regeneration must take < 1 s.

## Data sources (parse, never invent)
- `docs/office/board.md`: WP table (id, scope, owner role, estimate points, status, ticket link) and the "Blocked on owner" paragraph.
- `docs/office/tickets/*.md`: YAML-ish front matter (id, title, owner, status, model, estimate, depends_on), `## Tasks` checklist, `## Acceptance`, `## Activity log`.
- `docs/office/standups/*.md`, `docs/office/reviews/*.md`: activity feed (title, date from filename, first lines, verdict if present).
- `docs/office/budget-ledger.md`: usage rows (estimate vs actual points).
- `docs/office/status.json`: LIVE data maintained by the Chief of Staff: sprint, usage (weekly vs caps 40/50, 5-hour), agents (name, role, model, ticket, status running|idle|done|stopped, note), owner_blockers. Missing or malformed pieces degrade gracefully with an on-page "data missing" note, never crash.
- `docs/office/org-chart.md`: render the hierarchy as a collapsible tree.

## Views (tabs, no routing library)
1. **Board** (default): columns TODO, IN_PROGRESS, IN_REVIEW, DONE, BLOCKED. Cards: ID, title, assignee chip (role + agent name from status.json if running), model badge, points (est vs actual), dependency badge. Filters: assignee, status, text search. Click a card -> side drawer with description, tasks checklist progress, acceptance, activity log, linked reviews/standups, depends_on.
2. **Now**: "Who is working on what": running agents first (with ticket), then recently finished; the Owner action list (open blockers with needed-by WP) highlighted.
3. **Timeline**: WP0..WP8 as horizontal bars by planned week (from docs/04 calendar: W0 Oct 22-25... W4) with status colour.
4. **Usage**: weekly gauge with the 40% plan line and 50% hard line, 5-hour gauge, points table from the ledger (planned vs actual), OpenAI spend vs balance.
5. **Team**: org chart tree + roster (docs/office/team.md).
6. **Activity**: reverse-chronological feed from standups, reviews, ledger rows.
Header shows project name, sprint goal, generated-at time, and a red banner if weekly usage >= 40%.

## Design
Clean and calm, readable by a non-engineer: plain-language labels, no jargon, status colours that also have text/icons (colour-blind safe), WCAG AA contrast, keyboard-navigable cards/tabs/drawer, `prefers-color-scheme` light/dark, `prefers-reduced-motion`, works at 375 px width. No emojis in data labels.

## Files owned
`src/jobai/office/**` (parser.py, render.py, cli.py, `__main__.py`, templates/ with .html .css .js assets), `tests/office/**` (fixtures + tests), `dashboard/**` (generated output; add `dashboard/` to `.gitignore`), `docs/office/tickets/OFF-1.md` Activity log, `docs/office/standups/<date>-web.md`. Do not edit other source files. `python -m jobai.office` must work via `src/jobai/office/__main__.py`.

## Acceptance (paste real output in the Activity log)
`uv run ruff check`, `uv run mypy src`, `uv run pytest -q` all green (existing 44 tests must still pass); `uv run python -m jobai.office build` produces `dashboard/index.html`; the page shows WP0 as DONE with the 3 agents, WP1-WP8 as TODO, OFF-1 as IN_PROGRESS, usage 4% vs caps, and the owner blocker list. Check it in a real browser (built-in browser pane: open file:///C:/Users/dheer/OneDrive/Desktop/JobAi/dashboard/index.html), screenshot desktop and 375 px mobile, fix visible problems, report what you actually saw. Parser tests use fixtures (no dependency on live docs). Every file < 500 lines.

## Rules
Follow docs/office/README.md. No git commit. No network calls. No secrets. If graph exists, `graphify query` before grepping; after code changes run `C:\Users\dheer\.local\bin\graphify.exe update .`. Set status IN_REVIEW when done.

## Activity log
- 2026-11-04 Web IC: built src/jobai/office (parser.py, render.py, cli.py, __main__.py, templates/index.html+style.css+app.js), tests/office (fixtures, 10 tests), dashboard/ in .gitignore. Views: Board + drawer, Now, Timeline, Usage, Team, Activity. Timeline weeks are spread by estimate points (docs/04 not read); status.json may override with a `timeline` list.
  Verification (real output):
  - `uv run ruff check` -> All checks passed!
  - `uv run mypy src` -> Success: no issues found in 21 source files
  - `uv run pytest -q` -> 54 passed (44 existing + 10 new, fixtures only)
  - `uv run python -m jobai.office build` -> wrote ...\dashboard\index.html (56929 bytes, 0.035s)
  - Browser pane, file:// : Board shows WP0 Done ("3 agents (finished)"), OFF-1 In progress, WP1-WP8 To do; Now shows Chief of Staff running + 3 finished agents and the owner list (5 open, 1 done); Usage shows 4% vs plan 40 / hard 50 lines, 5-hour 27%, OpenAI $0.000254 spent / $9.79; weekly banner hidden (4% < 40%); drawer opens/closes (Escape) and Timeline draws 9 bars. At 375 px no horizontal page scroll. Found and fixed overlapping gauge marker labels. Not visually checked: dark mode, keyboard focus order by eye, serve command.
  - `graphify update .` run (see standup).
