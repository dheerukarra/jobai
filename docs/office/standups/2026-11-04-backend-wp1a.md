# Standup 2026-11-04 — Backend IC (WP1a)
Done: discovery framework (JobPosting, Source protocol, registry), dedupe (canonical_url/key/fingerprint, alias table), polite HTTP client, Greenhouse/Lever/Ashby adapters, idempotent store + stale marking, CLI `discover run|verify|stats|mark-stale`, migration 0002, 16 live-verified companies, 25 tests.
Doing next: WP1b (aggregators, freehire, JobSpy wrapper, slug harvesting) when scheduled.
Blockers: none.
Requests (changes needed outside my files): (1) `pyproject.toml` got pyyaml + types-pyyaml (dev) by me, please accept. (2) `tests/test_db.py` assertions hard-coded one migration; I updated lines 10, 13, 102 to two. Future migrations will need the same; consider asserting on the file count. (3) `remote` column is NOT NULL, so unknown remote is stored as 0.
Risks / decisions needed: Lever/Ashby only exercised live via `verify`; Lever EU host unsupported; mistral/kraken Lever boards return 0 jobs (probably moved ATS).
Verification: ruff clean; mypy src clean (33 files); pytest 79 passed; live verify 12/16 first pass then replacements (details in WP1 ticket log); `discover run --max-companies 3` x2 -> 1427 inserted then 0 inserted/1427 updated; ~32 live requests total.
