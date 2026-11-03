# 03 - Open-Source Landscape and Build-vs-Reuse

Status: research, 2026-10-22. Owner request: "check if already any opensource tools or apps that provide them or part of them so its easier to use or modify accordingly".
Companion docs: `00-product-brief-v2.md` (requirements), `02-sources-and-apply-feasibility.md` (ATS endpoint details; NOT repeated here).

## 0. Method and trust notes

- Stars / license / last push / archived / open-issue count come from the GitHub REST API (unauthenticated) queried 2026-10-22. "Last push" = `pushed_at`, not necessarily a release. Open-issue count from the API includes PRs.
- README/issue claims were read via page fetch on the same day. Anything I could not verify is marked UNVERIFIED.
- Licensing is judged only for personal, self-hosted, single-user use. AGPL/GPL obligations trigger on distribution or offering a network service to others, so they are mostly irrelevant here; flagged only where they limit later change of plan.
- Star counts are weak evidence. Several repos here have counts far out of line with their issue activity (noted inline). Treat README success claims (e.g. "1,000 applications in 2 days") as marketing unless independently reproduced.

## 1. Headline findings (read this first)

1. **No existing OSS tool does the whole brief.** The closest are `career-ops` (evaluate + tailor + track, but never submits, runs inside an AI CLI, not 24/7 headless) and `ApplyPilot` (full pipeline, but submits via the Claude Code CLI driving Chrome, optional CAPTCHA-solver, 45 open issues, AGPL).
2. **AIHawk is gone from its old URL.** `feder-cr/Jobs_Applier_AI_Agent_AIHawk` now redirects to `feder-cr/invisible_dots` (MIT, 32k stars, an unrelated "self-hosted agent VM" product; no job-applier mentioned in the README). Only low-star forks of the old code remain (best seen: 36 stars, 2024). Do not plan around AIHawk.
3. **LinkedIn Easy Apply bots are account-based.** They log in as the user. That directly conflicts with brief rule "no account of the owner is ever used" and rule "ATS passwords never stored". Verdict BORROW IDEAS only (question-answer config patterns).
4. **Discovery is the most reusable layer.** JobSpy (library) plus the ATS public-board approach (career-ops `portals.yml` scanner, `chrisdothtml/job-scraper`) cover most of it.
5. **Resume generation is a solved sub-problem.** RenderCV (YAML to Typst PDF) or Resume-Matcher (API + tailoring prompts + PDF) can be used as libraries/services; do not build a PDF renderer.
6. **Generic browser agents are unreliable for unattended submit.** Browser-use's own open issues include an agent that enabled a disabled button via JS, "placed the order" and reported success (#6068) and false-success regression cases (#6031, #5361). Skyvern self-reports 64.4% on WebBench. That is acceptable for pre-filling, not for unattended final submit.
7. **Scheduling does not need a platform.** GitHub Actions cron (or any tiny host cron) plus a DB is enough; Temporal is overkill.

## 2. Comparison table (all candidates)

Stars/push as of 2026-10-22. Verdicts: AS-IS / FORK / LIB (use as library) / IDEAS (borrow ideas/code snippets) / SKIP.

| # | Layer | Repo | License | Stars | Last push | Lang | Verdict |
|---|-------|------|---------|-------|-----------|------|---------|
| 1 | Discovery | speedyapply/JobSpy | MIT | 4,538 | 2026-10-20 | Python | **LIB** |
| 2 | Discovery | PaulMcInnis/JobFunnel | MIT | 2,196 | 2025-12-10 | Python | SKIP (archived) |
| 3 | Discovery | chrisdothtml/job-scraper | MIT | 1 | 2026-10-20 | TypeScript | IDEAS / maybe LIB (immature) |
| 4 | Discovery | rishilahoti/ashby-job-scraper | NOASSERTION | 54 | 2026-10-22 | TypeScript | IDEAS |
| 5 | Discovery+track | career-ops-hq/career-ops | MIT (name trademarked) | 76,571 | 2026-10-22 | JS (Node) | **IDEAS + vendor scanner modules** |
| 6 | Discovery | alpharomercoma/ts-jobspy | NOASSERTION | 17 | 2026-09-17 | TypeScript | SKIP |
| 7 | Auto-apply | Pickle-Pixel/ApplyPilot | AGPL-3.0 | 1,745 | 2026-03-08 | Python | IDEAS |
| 8 | Auto-apply | GodsScion/Auto_job_applier_linkedIn | MIT (AGPL before 2026-08) | 2,965 | 2026-09-11 | Python | IDEAS |
| 9 | Auto-apply | wodsuz/EasyApplyJobsBot | NOASSERTION | 832 | 2026-05-18 | Python | SKIP |
| 10 | Auto-apply | nicolomantini/LinkedIn-Easy-Apply-Bot | Apache-2.0 | 1,157 | 2026-10-07 | Python | SKIP |
| 11 | Auto-apply | suxrobGM/jobpilot | MIT | 97 | 2026-10-07 | TypeScript | IDEAS |
| 12 | Auto-apply | AIHawk (feder-cr/...AIHawk) | now redirects | n/a | n/a | n/a | SKIP (gone) |
| 13 | Browser agent | browser-use/browser-use | MIT | 118,867 | 2026-10-22 | Python | LIB (assist-prefill only) |
| 14 | Browser agent | browserbase/stagehand | MIT | 25,782 | 2026-10-22 | TypeScript | LIB (fallback) |
| 15 | Browser agent | Skyvern-AI/skyvern | AGPL-3.0 | 23,253 | 2026-10-22 | Python | IDEAS (maybe AS-IS later) |
| 16 | Browser agent | microsoft/playwright-mcp | Apache-2.0 | 38,509 | 2026-10-22 | TypeScript | SKIP for runtime (dev aid) |
| 17 | Browser agent | lavague-ai/LaVague | Apache-2.0 | 6,392 | 2025-01-21 | Python | SKIP (stale 21 mo) |
| 18 | Browser | microsoft/playwright | Apache-2.0 | 98,291 | 2026-10-22 | TS (Py/Node APIs) | **LIB (core)** |
| 19 | Browser | Kaliiiiiiiiii-Vinyzu/patchright | Apache-2.0 | 4,946 | 2026-10-20 | TypeScript | SKIP (stealth patch conflicts with no-bypass rule) |
| 20 | Resume | srbhr/Resume-Matcher | Apache-2.0 | 28,821 | 2026-10-22 | Py + Next.js | **LIB/service or IDEAS** |
| 21 | Resume | rendercv/rendercv | MIT | 17,807 | 2026-10-22 | Python | **LIB** |
| 22 | Resume | reactive-resume/reactive-resume | MIT | 44,713 | 2026-10-22 | TypeScript | SKIP (GUI builder) |
| 23 | Resume schema | jsonresume (schema now in jsonresume.org) | MIT | 338 (monorepo) | 2026-10-22 | JS | IDEAS (schema only) |
| 24 | Resume | xitanggg/open-resume | AGPL-3.0 | 8,941 | 2024-10-29 | TypeScript | SKIP (stale 2 yr) |
| 25 | Resume PDF | typst/typst | Apache-2.0 | 56,764 | 2026-10-22 | Rust | LIB (via RenderCV) |
| 26 | Resume PDF | gotenberg/gotenberg | MIT | 13,379 | 2026-10-16 | Go | SKIP (Playwright already present) |
| 27 | Typst templates | yunanwg/brilliant-CV | Apache-2.0 | 846 | 2026-10-20 | Typst | IDEAS |
| 28 | Tracker | Gsync/jobsync | MIT | 1,443 | 2026-10-19 | TypeScript (Next.js) | **IDEAS or FORK** |
| 29 | Tracker | makeplane/plane | AGPL-3.0 | 61,300 | 2026-10-22 | TypeScript | SKIP (general PM) |
| 30 | Orchestration | n8n-io/n8n | NOASSERTION (fair-code) | 208,340 | 2026-10-22 | TypeScript | SKIP for core |
| 31 | Orchestration | windmill-labs/windmill | NOASSERTION (AGPL core) | 18,247 | 2026-10-22 | Rust | SKIP |
| 32 | Orchestration | triggerdotdev/trigger.dev | Apache-2.0 | 16,604 | 2026-10-22 | TypeScript | Optional (cloud free tier) |
| 33 | Orchestration | inngest/inngest | NOASSERTION | 5,970 | 2026-10-22 | Go | Optional |
| 34 | Orchestration | hatchet-dev/hatchet | MIT | 8,165 | 2026-10-22 | Go | SKIP (needs always-on Postgres+engine) |
| 35 | Orchestration | temporalio/temporal | MIT | 23,920 | 2026-10-22 | Go | SKIP (too heavy) |
| 36 | Orchestration | dbos-inc/dbos-transact-py | MIT | 1,645 | 2026-10-22 | Python | Optional LIB (durable steps on plain Postgres) |
| 37 | Notify | binwiederhier/ntfy | Apache-2.0 | 34,995 | 2026-10-22 | Go | **AS-IS (service)** |
| 38 | Autofill ext. | Br1an67/OpenJobAutofill | MIT | 118 | 2026-05-13 | JavaScript | IDEAS |
| 39 | Autofill ext. | AhmadHassan-BTed/FormFilla | NOASSERTION | 2,385 | 2026-07-24 | none listed | SKIP (2.4k stars, 0 issues, no language: suspicious) |
| 40 | LinkedIn MCP | stickerdaniel/linkedin-mcp-server | Apache-2.0 | 3,985 | 2026-10-22 | Python | SKIP (logged-in scraping) |

## 3. Details per layer

### 3.1 Job discovery / scraping

**speedyapply/JobSpy** - https://github.com/speedyapply/JobSpy - MIT, 4,538 stars, pushed 2026-10-20, Python, 35 open issues (README says 13 issues + 22 PRs). Verdict: **USE AS LIBRARY**.
- Does: concurrent scrape of LinkedIn, Indeed, Glassdoor, ZipRecruiter, Bayt, Naukri, BDJobs, HelloWork into one DataFrame; salary, remote flag, description, company data; also CLI and an MCP server (`mcp-jobspy`).
- Good: Indeed described by the README as the best one with no rate limiting; LinkedIn works logged out; actively maintained (push 2 days ago); `proxies` param.
- Problems (from README + issues): LinkedIn returns HTTP 429 on bursts (clears ~1 min; proxies for volume); Glassdoor rate-limits above ~2 req/s; ZipRecruiter US/CA only and currently broken (#434 "0 results, no jobKeysMap in the page", opened 2026-10-22); Google Jobs "currently unavailable" (#284); ~1,000 result cap per search; descriptions need an extra request per job. Requests for Wellfound, Workable, company career pages (#378, #288, #368) are open and unimplemented, so JobSpy is NOT an ATS crawler.
- Fit: use for LinkedIn/Indeed/Glassdoor logged out, low rate, cached. Expect one or two boards to be broken at any time; design discovery as pluggable with per-source health flags.
- Note: ApplyPilot also depends on python-jobspy and documents a two-step install because of a numpy conflict, so pin versions in a lockfile.

**career-ops (scanner part)** - see 3.6; its `portals.yml` (100+ companies, 35+ queries) and 55+ provider modules (Ashby, Greenhouse, Lever, Wellfound, RSS/XML feeds) are the best existing source list and fetcher code. MIT so vendoring modules is fine. Endpoint specifics belong to doc 02.

**chrisdothtml/job-scraper** - https://github.com/chrisdothtml/job-scraper - MIT, 1 star, pushed 2026-10-20, TypeScript, 66 commits. Claims ~15k companies mapped across Greenhouse (4,250), Ashby (3,655), Workday (2,334), Lever (1,849), SmartRecruiters (1,250), Rippling (851), Workable (844), HTTP-only, no browser, infers board from company name or URL; company list from Bloomberry. Useful as a company-to-board resolver and as a reference implementation. Maturity is too low to depend on (1 star, 0 forks, undated). Verdict: IDEAS, possibly vendor the resolver after reading the code.

**rishilahoti/ashby-job-scraper** - 54 stars, license NOASSERTION (unclear terms), pulls 70k+ jobs from 2k+ Ashby companies. Useful only as a source list idea. IDEAS.

**PaulMcInnis/JobFunnel** - 2,196 stars, MIT, ARCHIVED (last push 2025-12-10). SKIP.

**ts-jobspy / jobspy-js ports** - 17 and 2 stars, unclear licenses. SKIP; call Python JobSpy instead.

### 3.2 Auto-apply / form-filling

**Pickle-Pixel/ApplyPilot** - https://github.com/Pickle-Pixel/ApplyPilot - AGPL-3.0, 1,745 stars, pushed 2026-03-08 (7 months stale), Python, 81 open issues per API (45 per issues page). Verdict: **BORROW IDEAS**.
- Does: 6-stage pipeline (discover, enrich, score 1-10, tailor, cover letter, auto-apply). Discovers from Indeed/LinkedIn/Glassdoor/ZipRecruiter/Google Jobs plus 48 Workday portals and ~30 direct career sites. Auto-apply launches Claude Code CLI + Playwright MCP per worker; optional CapSolver for hCaptcha/reCAPTCHA/Turnstile.
- Evidence it is demo-grade: headline "1,000 jobs in 2 days" has no success rate, no independent verification; README counts are inconsistent (48 vs 46 Workday, 30 vs 28 sites); open issues include "Scoring always returns 0" (#54), "Tailor Feature Not Working" (#74), "tailor does not create new tailored resume" (#103), "Keep getting 403" (#46), Workday URLs 404 (#91), "Too much HTML cleaning causing no job listings found" (#43), Gemini free-tier quota slashed (#107), "location_accept ... never read - every non-remote job silently filtered out" (#109). Last push in March suggests drift against live ATS.
- Conflicts with brief: optional CAPTCHA solving (forbidden), fully autonomous with no answers-bank gate, needs Claude Code CLI at submit time (cannot run on a cheap 24/7 host).
- Take: pipeline staging, Workday discovery notes, failure taxonomy.

**GodsScion/Auto_job_applier_linkedIn** - https://github.com/GodsScion/Auto_job_applier_linkedIn - MIT now (releases before Aug 2026 were AGPL), 2,965 stars, pushed 2026-09-11, Python, 72 open issues. Verdict: IDEAS.
- Does: LinkedIn Easy Apply only, via the user's logged-in Chrome; control panel; `stop_before_submit` dry-run; answers in `questions.py` / `personals.py` (experience, work authorization, salary, notice period, EEO); visa-sponsorship filter; optional AI answers.
- Problems: Chrome window must stay in the foreground (no headless 24/7); uses the owner's LinkedIn account (ban risk is the owner's; README disclaims responsibility and does not discuss bans); single-site.
- Take: its config schema for answers bank and filter keys is a good checklist.

**wodsuz/EasyApplyJobsBot** (832 stars, license NOASSERTION, pushed 2026-05-18; API shows 62 open issues, issues page showed 0 open) and **nicolomantini/LinkedIn-Easy-Apply-Bot** (1,157 stars, Apache-2.0, pushed 2026-10-07): Selenium/Easy Apply bots on a logged-in account. SKIP.

**suxrobGM/jobpilot** - 97 stars, MIT, TypeScript, pushed 2026-10-07, 21 open issues, "finds openings, tailors, applies". Small and recent; read for TS structure. IDEAS. UNVERIFIED beyond the description.

**Others seen in search (all <100 stars, mostly 0-70, mostly no license/unknown):** LuisMIguelFurlanettoSousa/auto-apply-bot (43, Gemini + Playwright MCP), AkbarDevop/ai-job-agent (67), Aditya-00a/Instaply (16, Ollama + Playwright, local-first), billmal071/job-agent (9). Treat as blog-grade demos; not worth reading except for one-off ideas.

**Site-specific note:** no maintained OSS Greenhouse/Lever/Ashby/Workday form submitter turned up. `simonfong6/auto-apply` (Greenhouse, 31 stars) last pushed 2019. This is the biggest gap; per-ATS submit code must be written by us (endpoint/form specifics in doc 02).

### 3.3 Browser-agent frameworks (for arbitrary forms)

| Repo | Fit for us | Evidence |
|------|-----------|----------|
| browser-use/browser-use (MIT, 118,867, Python) | Best general agent lib; good for the "assisted prefill" path where a human presses submit | Open issues include false-success reporting: #6068 (agent enables a disabled button via JS, places the order, reports success), #6031 (known-answer false-success cases), #5361 (failed actions reported as successes), #5796 (readonly/native listbox dropdowns). 595 open issues. Never let it press final Submit unattended. |
| browserbase/stagehand (MIT, 25,782, TS) | Good hybrid: deterministic Playwright with `act/extract/observe` LLM steps and caching of resolved actions. Best fit if the worker is TypeScript. | 383 open issues. Cloud features (Browserbase) are paid; library works with local Playwright. |
| Skyvern-AI/skyvern (AGPL-3.0, 23,253, Python) | Has a job-application example; vision-based; self-hostable via Docker | Anti-bot measures are cloud-only per README; self-reported 64.4% on WebBench; pip 1.0.31 has known install bugs; needs Rust/C++ build tools on Windows. AGPL is fine for personal use. Heavy for a free host. |
| microsoft/playwright-mcp (Apache-2.0, 38,509) | A tool for an LLM client, not a pipeline component. Useful while developing selectors with Claude Code. | n/a |
| lavague-ai/LaVague (Apache-2.0, 6,392) | SKIP: last push 2025-01-21, 106 open issues, effectively abandoned. | |
| Playwright itself (Apache-2.0) | The real core: deterministic per-ATS fill scripts, screenshot on every step, tracing for debugging. | |
| patchright, nodriver (stealth drivers) | SKIP: evasion tooling collides with the "no CAPTCHA/bot-wall bypass" guardrail and the stated risk posture. | |

Takeaway: use deterministic Playwright scripts for the 3-4 clean ATS forms (cheap, testable, no LLM per click) and reserve LLM agents for pre-filling unfamiliar forms in the assisted queue, with submit disabled.

### 3.4 Resume tailoring / generation

**rendercv/rendercv** - https://github.com/rendercv/rendercv - MIT, 17,807 stars, pushed 2026-10-22, Python, 102 open issues. Verdict: **USE AS LIBRARY**.
- YAML in, Typst-rendered PDF out; themes; Markdown in text fields; JSON-schema for the YAML (good for validation of LLM output); no headless Chromium needed so it works on tiny CI runners. Pairs naturally with the entity-diff guardrail because the master resume is structured data.
- Risk: opinionated layout; rapid releases (pin version).

**srbhr/Resume-Matcher** - https://github.com/srbhr/Resume-Matcher - Apache-2.0, 28,821 stars, pushed 2026-10-22, FastAPI + Next.js, SQLite, LiteLLM, PDF via headless Chromium, REST API under `/api` and an MCP server. Verdict: IDEAS (could run as a service later).
- Does: master resume (PDF/DOCX) + JD to tailored resume with prompts that forbid inventing skills, employers, metrics; cover letter; deterministic ATS score (non-LLM); background tailoring queue.
- Problems: needs Python 3.13+, Node, uv; Docker caveats; it is a GUI-first app with its own DB, so duplicating state vs. our tracker. Its fidelity guard is prompt-based only; we still need our own entity diff.
- Take: prompts, deterministic ATS-check idea, API shape.

**career-ops (resume part)**: HTML template to PDF via Playwright; has a fact-check step that blocks PDFs with numbers/facts absent from sources, but README admits it does not verify job titles or all rewording. Our entity diff must cover titles, dates, degrees, certs.

**Reactive Resume** (MIT, 44,713) is a polished GUI builder with a JSON schema; heavy and not headless-friendly. SKIP. **JSON Resume** schema (repo moved into jsonresume.org monorepo, standalone schema repo archived) is a fine neutral master-resume format; RenderCV's YAML is equally fine. Pick one source of truth (recommend RenderCV YAML to avoid conversion). **OpenResume** (AGPL, last push 2024-10) SKIP. **Typst templates**: brilliant-CV (846, Apache-2.0), modern-cv (633), imprecv (515) are options if RenderCV themes are insufficient.

### 3.5 Job tracking / CRM

**Gsync/jobsync** - https://github.com/Gsync/jobsync - MIT, 1,443 stars, pushed 2026-10-19, TypeScript (Next.js), 39 open issues. "Job application tracker and AI-powered job search assistant." Same stack family as our Next.js scaffold. Verdict: BORROW IDEAS, or FORK if our scaffold is still near-empty. Review its schema (jobs, statuses, resumes, activity) before designing ours. UNVERIFIED: auth model, DB (likely SQLite/Prisma), whether it supports API ingestion; check before forking.

**Muatasim-Aswad/job-tracker** (12 stars, MIT, "one record per job across reposts") and ~10 other kanban trackers (0-3 stars each, created in 2026) are too new/small to rely on; one idea worth noting is dedupe by canonical job identity across reposts. **Plane** (AGPL, 61k) is general PM. SKIP. Notion/Airtable templates: not evaluated (no automation-friendly API story needed since we own the DB); if the owner wants a phone view, a Notion mirror is a later add-on. UNVERIFIED.

Conclusion: the tracker is a small table + dashboard; writing our own is less risk than adopting a 2026-vintage hobby tracker. Reuse design, not code.

### 3.6 career-ops (cross-cutting)

**career-ops-hq/career-ops** - https://github.com/career-ops-hq/career-ops - MIT (code; name under separate trademark policy), 76,571 stars, 14.2k forks (page), pushed 2026-10-22, JS (Node) + Go TUI, 400 open issues/PRs per API (216 issues + 187 PRs on page). Verdict: **BORROW IDEAS and vendor MIT scanner/prompt modules**.
- Does: scores jobs 1-5 against CV; tailors ATS-friendly resume + cover letter; drafts application answers and outreach; interview prep; tracks in Markdown with canonical statuses; reply classification and rejection-pattern analysis; follow-up reminders; liveness check for stale postings; `portals.yml` with 100+ companies and 55+ provider modules (ATS APIs, RSS, web search).
- Does NOT submit: README states the apply script never sends a POST and has no email transport. Human presses Submit, which equals our "assisted" path.
- Runs inside AI coding CLIs (Claude Code, Codex, etc.), local, interactive; no scheduler or hosted worker. Not a 24/7 service.
- Caveats: popularity is unusually high relative to substance (author's own funnel: 740 evaluated, 68 applied, 12 interviews, 1 offer, self-reported); fact-check does not verify titles; stale postings persist without `--verify`; some fetches ignore proxy vars; an `ANTHROPIC_API_KEY` in env flips a subscription login to per-token billing.
- Take: portal list and fetchers, liveness check, status taxonomy, reply classifier prompts, fact-check concept.

### 3.7 Orchestration / scheduling on free infra

Requirement: run ~hourly discover and a few submit batches per day without the owner's laptop, at ~$0.

| Option | Verdict | Reason |
|--------|---------|--------|
| GitHub Actions `schedule:` cron | **Recommended default** | Zero infra, secrets store, logs, manual dispatch = kill switch. Caveats: cron is best-effort (delays of minutes), 6 h job cap, scheduled workflows in public repos auto-disable after 60 days of no repo activity, free minutes differ for public vs private repos - verify current limits on the GitHub docs before relying (UNVERIFIED here). Keep repo private (resume/answers!) and budget minutes. |
| Trigger.dev (Apache-2.0, 16,604, TS) | Optional | Cloud free tier exists (UNVERIFIED current limits); good retries/long tasks; adds vendor dependency. |
| Inngest (NOASSERTION, 5,970, Go) | Optional | Similar; function-as-a-service model. |
| DBOS Transact (MIT, 1,645, Python) | Optional LIB | Durable steps on plain Postgres, no extra server; suits a single Python worker. |
| n8n (fair-code "Sustainable Use", 208k) | SKIP core | Self-host needs an always-on host; license fine for personal internal use, but graph-based workflows are harder to test/version than code. Reasonable only as glue for notifications. |
| Windmill (AGPL core, 18k) | SKIP | Same always-on requirement, more platform than needed. |
| Hatchet (MIT, 8k) / Temporal (MIT, 24k) | SKIP | Need a server plus Postgres/Cassandra-class infra; Temporal is clearly too heavy. |
| Huginn (MIT, 50k) | SKIP | Ruby, aging model. |

Hosting choice itself is the hosting-research task's call; this doc only says nothing here forces an always-on server.

### 3.8 Email / application-status parsing

No credible maintained OSS project exists. Search hits are 0-star hobby repos (Gmail-to-sheet trackers, one Gmail add-on using Gemini). Best prior art is career-ops' reply classification and rejection-pattern analysis (MIT). Plan: write ~150 lines ourselves: Gmail API (read-only scope, label filter) or IMAP app-password stored as host secret, Haiku classifier with fixed labels (received, interview, assessment, rejection, offer, other), match to application via company + sender domain + job title. Note: this is a Google OAuth read scope the owner must grant; consider forwarding job mail to a dedicated mailbox to reduce blast radius.

### 3.9 Answers bank / form-question mapping

No standalone library. Existing patterns:
- GodsScion `questions.py` / `personals.py` / `search.py`: flat Python dicts keyed by question topic; string-match against labels; AI fallback. Good checklist of topics.
- Browser autofill extensions (OpenJobAutofill 118 stars MIT; job-autofiller, Autofill-Jobs <60): label-regex to profile-field maps for Greenhouse/Lever/Workday; useful for the field-synonym tables only. FormFilla (2,385 stars, 0 issues, no language) looks inflated; skip.
- career-ops drafts answers with an LLM and leaves submission to the human; no strict "unknown = stop" gate.
Our design (must write): YAML answers bank with canonical keys + synonym regexes + allowed-values constraints (e.g. sponsorship must be exact enum), Haiku maps an unseen question to a key or returns UNKNOWN; UNKNOWN or low confidence routes to assisted. Free-text questions get drafts only in assisted mode.

## 4. Build-vs-reuse recommendation

### 4.1 Minimal-custom-code architecture

```
GitHub Actions cron (hourly discover, batched submit, nightly email poll)
  |
  v
[Discover]  JobSpy (speedyapply)   +  ATS board fetchers vendored from career-ops
            + company list/resolver ideas from chrisdothtml/job-scraper
  v
[Normalize/dedupe/score]  OWN code (canonical job key, filters, Haiku fit score)
  v
[Tailor]    OWN prompts (idea: Resume-Matcher, career-ops) -> Sonnet -> RenderCV YAML
            -> OWN entity-diff guard -> RenderCV (Typst) -> PDF
  v
[Route]     OWN: answers-bank coverage + ATS type + CAPTCHA/login detection
  |-- auto -----> Playwright scripts per ATS (OWN, small) -> screenshots + trace
  |-- assisted -> prefilled link + PDF + answers; optional browser-use/Stagehand prefill (no submit)
  v
[Store/track]  small SQL DB (OWN schema; ideas from Gsync/jobsync, career-ops statuses)
  v
[Notify]    ntfy (binwiederhier) push; Next.js dashboard (existing scaffold)
  v
[Status]    Gmail read + Haiku classifier (OWN; labels from career-ops)
```

### 4.2 Component to repo map

| Component | Source | How used |
|-----------|--------|----------|
| Logged-out board scraping | speedyapply/JobSpy (MIT) | pip dependency, pinned; wrapper with rate limit, cache, health flags |
| ATS board fetchers + company list | career-ops-hq/career-ops (MIT) modules; chrisdothtml/job-scraper as reference | vendor with attribution, trim to needed ATS |
| Resume source + PDF | rendercv/rendercv (MIT) + Typst | pip dependency; YAML is the master resume format |
| Tailoring prompts / ATS-check idea | srbhr/Resume-Matcher (Apache-2.0), career-ops | read and adapt prompts; no runtime dependency |
| Browser engine | microsoft/playwright | core of auto-submit and screenshots |
| Unfamiliar-form prefill (later) | browser-use (MIT) or Stagehand (MIT) | phase 2, assisted only, submit blocked by code |
| Notifications | ntfy (Apache-2.0) | hosted or self-hosted topic; Telegram as alternative |
| Dashboard | existing Next.js scaffold; layout ideas from Gsync/jobsync | consider forking jobsync only if scaffold is trivial (check its DB/auth first) |
| Scheduler | GitHub Actions cron | workflow files; manual-dispatch kill switch |
| Optional durability | DBOS Transact or Trigger.dev | only if Actions' limits bite |

### 4.3 What we must still write ourselves

1. Canonical job identity, dedupe, caps (per company/day/global), kill switch, dry-run default.
2. Profile/visa/location filter and Haiku fit scoring; spend caps (daily and monthly) with hard stop.
3. Entity-diff fabrication guard (employers, titles, dates, degrees, certs, skills) against the master YAML.
4. Answers bank + question-to-key mapper with UNKNOWN gating.
5. Per-ATS submit scripts for the clean forms (details in doc 02) with CAPTCHA/login-wall detection that routes to assisted.
6. Assisted-queue UI: one-tap link, prefilled values, PDF download, mark-done.
7. Email status classifier and application matching.
8. Tests: recorded-fixture tests per ATS form so breakage is detected before live submit; a canary job that dry-runs each ATS weekly.

Rough size estimate (judgement, not measured): the custom part is a few thousand lines; the largest risk-bearing parts are item 5 and 8.

### 4.4 Risk list

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| JobSpy board breaks (ZipRecruiter already broken #434; Google Jobs dead) | High, recurring | Medium | Multi-source; per-source health check; ATS direct boards are the stable backbone |
| LinkedIn/Indeed/Glassdoor IP blocks or 429 | High at volume | Low-medium (no account to ban) | Low rate, cache, 1-2 queries/hour, optional rotating proxy later; fall back to ATS boards |
| Maintainer abandonment (LaVague stale; ApplyPilot last push March; OpenResume 2024) | Medium | Medium | Depend only on actively maintained MIT/Apache libs (JobSpy, RenderCV, Playwright); pin versions; vendor small modules instead of depending on tiny repos |
| Tiny-repo dependency (chrisdothtml/job-scraper 1 star, license/maintainer unknown longevity) | High if depended on | Low | Reference/vendor only |
| Repo redirected/repurposed (AIHawk precedent) | Seen | Low | Vendor with commit hash, record upstream SHA in NOTICE |
| License: AGPL (Skyvern, ApplyPilot, OpenResume, Plane, nodriver) | Low for personal use | Low | Avoid as dependencies; obligations only arise if later hosted for others (brief says no) |
| License: NOASSERTION repos (EasyApplyJobsBot, ts-jobspy, ashby-job-scraper, FormFilla) | n/a | Unknown rights to copy | Do not copy code from them |
| Trademark: career-ops name | Low | Low | Do not reuse the name |
| Auto-submit mistakes (wrong answer, false success like browser-use #6068) | Medium | High (bad applications under owner's name) | Deterministic scripts, post-submit confirmation-page assertion, screenshots, dry-run default, per-ATS enable, daily caps |
| LLM-agent cost blowup | Medium | Medium | Agents only in assisted prefill; Haiku for mapping; spend caps |
| ToS violations (LinkedIn scraping, automated applying) | Certain on some boards | Account/IP action | Logged-out only, no owner account, document per source; auto-apply only on ATS public forms |
| Free-infra limits (Actions cron delay/minutes, disabled schedules) | Medium | Low | Heartbeat check that notifies via ntfy when a run is missed |
| Email access scope (Gmail OAuth) | Low | Medium | Read-only scope, dedicated mailbox/forwarding |
| Self-reported claims in READMEs misleading planning | High | Medium | Treat any "N applications in M days" as unverified; build our own success metrics |

### 4.5 Alternative considered: adopt career-ops/ApplyPilot wholesale

Rejected. career-ops cannot submit and is an interactive CLI workflow (matches only the assisted half); ApplyPilot needs the Claude Code CLI plus optional CAPTCHA solving at submit time and shows signs of drift (open issues on scoring, tailoring, 403, Workday 404). Forking either would mean rewriting the parts the brief cares about (guardrails, answers bank, entity diff, 24/7 host) while inheriting their structure. Reusing their discovery modules and prompts captures most of the value.

## 5. Open items / UNVERIFIED

- GitHub Actions current free-tier limits and Trigger.dev/Inngest free-tier limits: verify on official pages when hosting is chosen.
- Gsync/jobsync schema, DB and auth: not inspected.
- career-ops provider modules' exact quality/currency: not run; inspect before vendoring.
- Notion/Airtable job-tracker templates: not evaluated.
- Stagehand Python support: not checked; TS is its primary language.
- Whether RenderCV themes pass ATS text extraction: test with Resume-Matcher's ATS-check idea.
