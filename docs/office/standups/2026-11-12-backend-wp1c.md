# Standup 2026-11-12 — Backend IC (WP1c)
Done:
- New ATS adapters: Workable, SmartRecruiters (paginated), Recruitee (live-verified, enabled); BambooHR, Breezy (implemented, registered DISABLED: no real tenant to verify).
- 30 live-verified companies appended to config/companies.yaml (2 dead candidates rejected; 50 candidates left for a later run, listed in the ticket).
- Freshness: migration 0004_board_status.sql, discovery/health.py (dead-board tracking, skipped by `discover run`, `--retry-dead`), `discover health` (dead boards / stale jobs / possible reposts), repost alias in Store.upsert (same source+company+title, new id, <=30 days, old id gone from board).
- `discover sources` shows enabled/disabled + reason; `--source all` skips disabled ATSs.
- THIRD_PARTY_NOTICES.md (credit + MIT text). 14 new tests, fixtures are trimmed recorded responses.
Doing next: nothing pending; Personio/Teamtailor/Atlassian/Amazon/Apple not started (optional per spec, skipped for budget).
Blockers: none. BambooHR/Breezy need one real public tenant slug each to be verified and enabled (remove from DISABLED_ATS in sources/__init__.py).
Requests (changes needed outside my files): none. Note: docs/office/status.json and graphify-out/* show as modified (graphify update, other agents).
Risks / decisions needed: SmartRecruiters descriptions are empty (list endpoint carries none; detail calls would multiply requests). Repost detection only runs for board sources (needs the live id set).
Verification: ruff check -> All checks passed; mypy src -> no issues in 51 files; pytest -> 146 passed. Live: ~42 requests total; second identical runs inserted 0 for all three new sources; stats 1607 -> 1770 jobs.
