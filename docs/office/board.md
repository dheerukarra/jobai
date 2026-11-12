# Board

Owner: Chief of Staff. Estimates are weekly-limit points (see plan section 4). Status: TODO / IN_PROGRESS / IN_REVIEW / DONE / BLOCKED.

| WP | Scope | Owner role | Est | Status | Ticket |
|---|---|---|---|---|---|
| WP0 | Foundation: project reset, SQLite schema, config, LLM gateway (OpenAI-first, ladder, spend caps, PII redaction), CI, tests | Platform EM / Backend IC | 3 | DONE (44 tests, ruff + mypy clean; real OpenAI call unverified until key) | tickets/WP0.md, reviews/platform-em-WP0.md |
| OFF-1 | Office dashboard: Jira-style tracker generated from docs/office (offline HTML) | Experience EM / Web IC | 1.5 | DONE (54 tests; open dashboard/index.html) | tickets/OFF-1.md |
| WP1 | Discovery: ATS fetchers, aggregators, freehire API, JobSpy, dedupe (WP1a core + 3 ATS DONE and verified: 79 tests, 1,427 real jobs; WP1b aggregators next) | Platform EM / Backend IC | 5 | DONE (WP1a + WP1b verified: 132 tests, 1,607 real jobs from 8 live sources) | tickets/WP1.md |
| WP1b | Discovery sources: Remotive, RemoteOK, Arbeitnow, The Muse, HN, freehire API, optional JobSpy (live JobSpy query not run: blocked by classifier), board-slug harvesting | Platform EM / Backend IC | 2.5 | DONE | tickets/WP1b.md |
| OFF-2 | Live dashboard: auto-update on every change, show in-progress work from file activity | Experience EM / Web IC | 1.5 | DONE (93 tests; server at 127.0.0.1:8765 updates within ~3 s) | tickets/OFF-2.md |
| WP1c | More job sources: port selected career-ops providers (Workable, SmartRecruiters, Recruitee, BambooHR, Breezy, big-company APIs), bigger seed list, freshness checks | Platform EM / Backend IC | 2.5 | DONE (146 tests; 8 new+old ATS sources, 5 added, 3 live-verified; 30 verified seeds; 1,770 jobs) | tickets/WP1c.md |
| WP2 | Profile, filters, answers bank, fit scoring (1-5 with discard reasons, evaluation cache, golden-set calibration, visa/sponsorship filter) | Platform EM / Backend IC | 3.5 | TODO | — |
| WP3 | Tailoring: entity-diff guard (titles, dates, employers, degrees), CV PDF (compare career-ops HTML templates + Playwright vs RenderCV), cover note | Applier EM / Backend IC | 5 | TODO | — |
| WP4 | Route decision + Playwright submit (Greenhouse, Lever), wall detection, dry-run | Applier EM / Automation IC | 8 | TODO | — |
| WP5 | Assisted queue, ntfy, dashboard, kill switch | Experience EM / Web IC | 6 | TODO | — |
| WP6 | Deploy (Oracle/Hetzner), backups, health, runbook | Platform EM / DevOps IC | 3 | TODO | — |
| WP7 | Hardening, fixture e2e, 7-day dry run | QA and Security Lead | 4 | TODO | — |
| WP8 | Email status classifier, extra ATS prefill (post-MVP) | — | 5 | TODO | — |

Carry-over from the WP0 review: DRY_RUN is configured but not enforced anywhere yet; WP4 must enforce it at the submit step (default on). Job and application status values were chosen by the Backend IC (jobs: new, scored, shortlisted, skipped, applied, closed; applications: pending, tailored, ready, submitted, failed, skipped) and may need widening. Unfixed P2s from the review are listed in reviews/platform-em-WP0.md.

Blocked on owner: OpenAI key (needed by WP2/WP3 live checks), Oracle account (WP6), ntfy topic (WP5), master resume + answers bank + target companies (WP2/WP3), live-submit decision (end of WP7).
