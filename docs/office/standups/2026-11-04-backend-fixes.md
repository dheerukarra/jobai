# Standup 2026-11-04 — Backend IC (WP0 review fixes)
Done: P1-1 (timeout not retried, charged worst-case), P1-2 (schema + per-message overhead in reservation), P1-3 (LLMParseError, ladder escalates), P1-5 (verified_at 2026-11-03 kept as the real date; stale-warn test added), P1-6 (transactional, serialised migrations), P1-7 (migrations moved into the package, fail loudly if missing), P2: Redactor repr, cap rounding (floor), CHECK constraints in 0001_init.sql, real day-boundary test. 44 tests pass; ruff, mypy clean.
Doing next: nothing; awaiting re-review.
Blockers: none.
Requests: none.
Risks / decisions: status enums in CHECKs are my proposal (jobs: new/scored/shortlisted/skipped/applied/closed; applications: pending/tailored/ready/submitted/failed/skipped); later WPs must edit 0001 or add 0002 if they need more. Migrations now live at src/jobai/migrations/ (old top-level migrations/ removed). Remaining review P2s (2, 4, 5, 7-10, 12-14) untouched.
TODO(WP4): P1-4 DRY_RUN is still not enforced in Gateway/provider; WP4 must refuse real calls when dry_run is true.
Verification: see WP0 ticket Activity log.
