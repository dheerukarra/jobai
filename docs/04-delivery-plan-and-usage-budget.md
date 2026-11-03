# Delivery Plan and Claude Usage Budget

Inputs: `00-product-brief-v2.md`, `01-hosting-and-costs.md`, `02-sources-and-apply-feasibility.md`, `03-open-source-landscape.md`. Measured 2026-10-22 via `get_usage`: plan **Pro**; weekly all-models **15% used** (resets Oct 25 10:59 UTC); 5-hour window 55% used (resets 21:59 UTC).

## 1. Two different budgets (do not confuse)
| Budget | What it pays for | Limit | Owner rule |
|---|---|---|---|
| **Claude Code subscription** (weekly + 5-hour windows) | Me and my agents *building* the tool | **Weekly total must stay <= 50%** (hard), planned <= 40% | This plan |
| **OpenAI API key** (prepaid, $10 loaded; Anthropic stays a pluggable option) | The finished tool *running* (triage, tailoring, form mapping) | Prepaid credit is a native hard cap; plus daily/monthly $ caps in code | See decision 7: about $0.005–$0.034 per application depending on the tailoring model (ESTIMATE) |

Running the finished app never touches the Claude Code weekly limit.

## 2. Usage control protocol (strict)
Unit = **points** = percentage points of the weekly all-models limit. Estimates below are guesses (+/-50%) until calibrated.
1. **Gate before every work package (WP):** call `get_usage`. Start only if `weekly% + WP estimate <= 40` AND `5-hour% <= 60` (or the WP is < 1 point). Otherwise defer to the next window.
2. **Hard stops:** weekly >= 45% -> launch nothing new, finish the in-flight agent, write a handoff note. Weekly >= 48% -> stop everything now.
3. **Ledger:** after each WP append to `docs/office/budget-ledger.md`: WP id, estimate, measured weekly% before/after, agents, model tier. After WP0 recalibrate every estimate by the measured ratio.
4. **Concurrency <= 2 agents.** Parallel agents burn the 5-hour window fastest.
5. **Cheap by default:** Haiku for scaffolding, tests, docs, fixtures, reviews; Sonnet only for submit scripts, tailoring prompts, entity diff, route decision. No agent re-reads the full doc set: each brief is <= 1.5k tokens and names <= 3 files to read.
6. **No research repeats.** Research is done; agents get the decisions below, not the reports.
7. **Idle costs nothing.** If a gate fails, stop and say when the window resets; resume then (can be automated with a scheduled wake-up if the owner wants).

## 3. Decisions (changeable by the owner)
1. **Single-language Python stack**, because the reusable pieces are Python (JobSpy, RenderCV, Playwright-python, Anthropic SDK): FastAPI + HTMX dashboard, SQLite, APScheduler in one service, Docker Compose. The Next.js scaffold and SaaS code are archived, not extended.
2. **Hosting:** Oracle Always Free ARM VM (2 OCPU/12 GB) primary, Hetzner CAX11 fallback; scheduler runs on the VM (GitHub Actions cron is too small for a browser worker, per `01`; it may be used for a discovery-only fallback). Dashboard behind Cloudflare Tunnel + Access. ntfy for notifications. Encrypted nightly SQLite backup off-box.
3. **Reuse:** JobSpy (library, logged out), career-ops ATS fetchers (vendored, MIT), RenderCV + its YAML as the master resume format, Playwright for deterministic per-ATS submit scripts, browser-use/Stagehand only for assisted prefill (submit blocked). No AGPL code copied (ApplyPilot = ideas only). No CAPTCHA solving. LinkedIn/Indeed: discovery only, never submit, never logged in.
4. **Route:** AUTO-LIKELY (Greenhouse, Lever without CAPTCHA) -> dry-run first, then live per ATS after the owner enables it; everything else -> assisted queue. Expect only 15–30% auto (ESTIMATE); the assisted queue is the main path and must be great on a phone.
5. **Guardrails from the brief are acceptance tests**, not prose: entity-diff blocks fabrication, answers bank with UNKNOWN gating, dedupe + caps, kill switch, dry-run default, spend caps.

6. **freehire (github.com/strelov1/freehire, MIT, checked 2026-11-03):** use its keyless public read API as an extra discovery source (personal/non-commercial use is allowed by its OpenAPI text; per-address rate limit; **IT jobs only**; confirm https://freehire.me/terms#data-licence before relying). Do NOT adopt its auto-apply code wholesale (about 3.5k lines of Go coupled to 12 internal packages) and do NOT pay for its Pro: Pro auto-apply is capped at **3 per day**, Ultra at 100/day. Borrow its design notes for WP4 (`docs/superpowers/specs/2026-09-02-auto-apply-worker-design.md`, `2026-09-09-lever-fill-and-submit-design.md`, `2026-09-09-screening-answer-bank-design.md`): scan the rendered DOM at fill time because Greenhouse renders ~36 fields while its question API declares ~17 (country, location and the whole EEOC block are undeclared); park the application when any required field can't be resolved; verify success by a text marker; refuse on CAPTCHA. A reference clone sits in the session scratchpad (untrusted, never executed).

7. **LLM provider = OpenAI first (owner decision 2026-11-03, $10 prepaid credit).** The WP0 gateway is provider-agnostic (OpenAI default, Anthropic optional) with a **model ladder** in config and a price table stamped with its verified date. Prices checked on developers.openai.com/api/docs/pricing 2026-11-03 (USD per 1M tokens, input / cached input / output): `gpt-6-luna` 0.10/0.01/0.50, `gpt-5-nano` 0.05/0.005/0.40, `gpt-6.1-terra` 1.00/0.05/5.00, `gpt-5.4-mini` 0.75/0.075/4.50, `gpt-6.1-sol` 2.00/0.10/10.00; Batch is about half. Ladder: triage and form-question mapping on the cheapest model (luna or nano); tailoring starts on luna and escalates to terra, then sol, only when the entity-diff guard or schema validation fails; WP3's golden-set eval picks the cheapest model that passes. Rough cost per applied job (ESTIMATE; ~5 jobs triaged per application, ~8k tokens in / 1.5k out for tailoring): about $0.005 on luna, $0.019 on terra, $0.034 on sol. So $10 covers roughly 2,100 / 540 / 290 applications, i.e. about 70 / 18 / 10 days at 30 a day. To verify in WP0: structured outputs (JSON schema) on the chosen models, and account rate-limit tier. Privacy: OpenAI docs say API data is not used for training by default and abuse-monitoring logs are kept up to 30 days; we still strip name, phone, email and address before each call and re-insert them afterwards. Key handling: the key goes only into a git-ignored `.env` (later the server's environment); it is never pasted into chat; keep auto-recharge off.

## 4. Work packages
Points = Claude Code weekly-limit cost estimate incl. ~25% coordination overhead. Tickets are created just in time (saves budget).
| WP | Scope | Hat (org role) | Model | Pts |
|---|---|---|---|---|
| WP0 | Reset repo, Python project, SQLite schema + migrations, config (pydantic), **LLM gateway with spend ledger and daily/monthly caps**, CI, tests | Platform EM + backend IC | Sonnet | 3 |
| WP1 | Discovery: ATS fetchers (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee), Adzuna + remote feeds, JobSpy wrapper, dedupe + fingerprint, company-slug harvesting | Backend IC | Sonnet/Haiku | 5 |
| WP2 | Profile + filters + **answers bank** + fit scoring (Haiku) + caps | Backend IC | Haiku | 3 |
| WP3 | Tailoring: RenderCV master resume, tailor prompt (Sonnet, cached, Batch), **entity-diff guard**, PDF, cover note | Backend IC + QA | Sonnet | 5 |
| WP4 | Route decision + **Playwright submit** for Greenhouse and Lever, wall detection (CAPTCHA/login/email-verify), LLM question mapping with confidence gates, dry-run, HTML fixture tests | Backend IC (hard) | Sonnet | 8 |
| WP5 | Assisted queue (prefilled answers, one-tap links), ntfy, dashboard (queue, tracker, spend, kill switch), Cloudflare Access hand-off | Web EM + frontend IC | Haiku | 6 |
| WP6 | Deploy: Dockerfile/Compose, Oracle/Hetzner runbook, restart policy, backups, health, alerts | DevOps IC | Haiku | 3 |
| WP7 | Hardening: fixture e2e, failure injection, security pass (secrets, rate limits), docs, 7-day dry-run review | QA + Security leads | Haiku/Sonnet | 4 |
| WP8 (post-MVP) | Email status classifier (Gmail + Haiku); extra ATS prefill (Ashby, Recruitee, ...) | IC | Sonnet | 5 |
| Reviews | Sprint-boundary "exec/manager" reviews as one cheap Haiku pass each (CEO/CPO/CTO/COO collapsed into a single exec review) | Execs, EMs | Haiku | 1 per sprint |
Core MVP (WP0–WP7 + 3 reviews) ~ **40 points** total; WP8 +5.

## 5. Calendar (weekly window resets Sat 10:59 UTC)
Budget is not the bottleneck (about 10–15 points per week against a 40-point planning cap); the 5-hour window, live verification and owner steps are.
| Week | Dates | Work | Planned usage added | Weekly total target |
|---|---|---|---|---|
| 0 | Oct 22–25 | Plan done; WP0, start WP1 after the 5-hour reset | +8 (to ~23%) | <= 30% |
| 1 | Oct 25–Nov 1 | WP1 finish, WP2, WP3 | +13 | <= 30% |
| 2 | Nov 1–8 | WP4, WP5 | +14 | <= 30% |
| 3 | Nov 8–15 | WP6 deploy, WP7, start 7-day dry run; owner enables live submit for Greenhouse/Lever per ATS | +7 | <= 20% |
| 4 | Nov 15–22 | Buffer, tuning from dry-run, WP8 if wanted | +5–10 | <= 25% |
**Ready product (MVP live, assisted + limited auto): about 3 weeks, by ~Nov 12–15; 4 weeks with slip.** If calibration shows estimates are 2x too low the plan still stays under 40%.

## 6. Owner tasks (nobody can do these for you)
Put your OpenAI API key in the git-ignored `.env` when WP2 needs it (auto-recharge off; the $10 prepaid balance is the cap); open the Oracle Cloud account (card verification; Hetzner if capacity errors); create an ntfy topic (and Telegram bot if wanted); write the master resume (RenderCV YAML), answers bank (work authorization, sponsorship, salary, demographics: your choices), target-company list and filters; decide which ATS to enable live and cap per day.

## 7. Risks
Estimates wrong (calibrate after WP0); Oracle capacity/reclaim (fallback Hetzner, ~EUR 5–6.5/mo, ESTIMATE); ATS markup drift (fixture tests + canary dry-runs); IP blocks from logged-out scraping (low rate, caching, source fallbacks); auto-submit wrong answers (UNKNOWN gating, dry-run, caps); 5-hour window exhaustion mid-package (gate + handoff notes).
