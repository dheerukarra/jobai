# ApplyForge Personal - Hosting and Costs (v1, 2026-10-22)

Scope: run the single-user pipeline from `00-product-brief-v2.md` 24/7 without the owner's laptop, at the cheapest or free cost.
Labels: **FACT** = read from the cited page on 2026-10-22 (via a fetch summarizer, so re-check anything you will rely on for billing). **ESTIMATE** = my reasoning or unverified third-party reports.

## 1. Recommendation (short)

| | Primary | Fallback |
|---|---|---|
| Compute | Oracle Cloud Always Free Ampere A1 VM (2 OCPU / 12 GB), Docker Compose | Hetzner Cloud smallest plan (CAX11 ARM or CX23 x86, 2 vCPU / 4 GB), same Compose file |
| DB | SQLite (WAL) on the VM, nightly encrypted backup off-box | same |
| Dashboard | Same VM (Next.js or small server) exposed through Cloudflare Tunnel + Cloudflare Access | same |
| Notifications | Telegram bot (primary), email via free SMTP/Resend as backup | same |
| Fixed cost | **$0/month** (+ Anthropic usage) | **about EUR 4-6/month** (ESTIMATE, verify on Hetzner) |
| Anthropic usage | ~$12-60/month at 20-50 apps/day with Batch for tailoring (section 7) | same |

Rule: the app is packaged as ONE Docker image + one Compose file + one `.env`, with SQLite and a config directory as the only state. That makes the primary-to-fallback migration a 30-minute job (section 8).

## 2. Workload sizing (ESTIMATE)

- Browser worker: 1-2 GB RAM per Chromium, 2-5 min per application (page load, form fill, upload, confirm). 100 apps/day x ~4 min = ~400 browser-minutes/day (~6.7 h), so a single worker with 1-2 concurrent browsers is enough. Peak RAM: 2 browsers x 2 GB + app + OS = ~6 GB.
- Discovery: API + light scraping every 3-4 h, a few minutes each, low CPU.
- DB: tens of thousands of job rows per year, well under 1 GB.
- Conclusion: needs >= 4 GB RAM to be comfortable (2 browsers). 1 GB machines (OCI E2.1.Micro, GCP e2-micro) cannot run Chromium reliably.

## 3. Option-by-option findings

### (a) Oracle Cloud Always Free (primary)
- FACT: Ampere A1 Flex free allocation is 1,500 OCPU-hours and 9,000 GB-hours per month = **2 OCPU and 12 GB** total; one instance or up to two 1-OCPU instances. Also up to two E2.1.Micro (1/8 OCPU, 1 GB), 200 GB total boot+block storage, 10 TB/month outbound. Instances must be in the home region. https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm (2026-10-22)
- FACT (same page): idle reclamation: an Always Free instance may be reclaimed if over 7 days the 95th percentile CPU < 20%, network < 20%, and (A1 only) memory < 20%.
- FACT: "out of host capacity" errors are expected; Oracle's suggested remedies are another availability domain, retry later, or upgrade to a paid account. (same page)
- ESTIMATE/unverified: a Korean blog claims the A1 allowance was cut from 4 OCPU/24 GB to 2 OCPU/12 GB around June 2026; the official page above now says 2/12, consistent with that. Do not plan on more than 2/12. Community reports say Frankfurt/Singapore have more spare capacity (unverified); the home region is permanent, so choose it carefully at signup.
- ESTIMATE: signup friction is the main risk: card verification, occasional rejected signups, no region change later, and A1 capacity scarcity in popular regions. Accounts that sit unused or violate terms can be terminated.
- Gotchas:
  1. Idle reclaim: a mostly idle scheduler VM can trip the 20% rule on all three metrics. Mitigations: (i) upgrade the account to Pay As You Go (stays $0 inside Always Free limits; reportedly changes capacity allocation and reclaim exposure, unverified, so also set a $1 budget alert); (ii) keep the VM genuinely busy (Chromium sessions raise memory use; 20% of 12 GB is 2.4 GB, so a permanent in-memory cache or a Redis/worker pool that holds ~3 GB resident clears the memory test); (iii) never rely on reclaim being "a warning": back up off-box.
  2. Do not mix paid and free resources carelessly (Oracle says possible but not recommended).
  3. ARM: use `linux/arm64` Playwright images; Chromium ARM64 builds exist for Playwright, but test early. Some ATS pages behave differently with a datacenter IP; nothing to do with ARM.
  4. Datacenter IPs are more likely to hit bot walls; those jobs go to the assisted queue per the brief anyway.

### (b) GitHub Actions cron
- FACT: private repos on GitHub Free get **2,000 minutes/month** (Pro 3,000); standard GitHub-hosted runners are **free for public repos**. Linux x64 is 1x minutes. https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions (2026-10-22)
- FACT: job limit 6 h; workflow run limit 35 days; Free plan 20 concurrent jobs. https://docs.github.com/en/actions/reference/limits
- FACT: schedule minimum 5 min; runs can be delayed or dropped at high load (especially at the top of the hour); runs only on the default branch; in a **public** repo, scheduled workflows are auto-disabled after 60 days without repo activity. https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- ESTIMATE: Playwright works on `ubuntu-latest` (browsers installable, ~7 GB RAM runners). Secrets live in repo secrets (fine). No persistent disk, so state must live in an external DB (Neon/Turso).
- Fit: discovery every 4 h (6 runs/day x ~3 min x 30 = ~540 min/month) fits the private-repo allowance. Applying 30-100 apps/day x 3-5 min = 2,700-15,000 min/month does NOT fit a private repo; it would fit a public repo only, which means code and workflow logs are public (never log PII; resume and answers bank must not be in the repo). Also cold-start overhead per run and no human-takeover session.
- Verdict: good as a heartbeat/trigger or emergency discovery runner, not the primary apply worker.

### (c) Google Cloud / AWS / Azure
- FACT (GCP): one non-preemptible **e2-micro** per month in us-west1, us-central1 or us-east1, 30 GB standard disk, 1 GB egress/month. Cloud Run request-based: 2M requests, 360,000 GB-s, 180,000 vCPU-s. Firestore 1 GiB, 50k reads/20k writes/day. https://docs.cloud.google.com/free/docs/free-cloud-features (2026-10-22). e2-micro has 1 GB RAM: too small for Chromium (can run the scheduler/dashboard only). Cloud Run could host a browser job (see ESTIMATE below), but free vCPU-seconds (180k = 50 vCPU-hours) are thin for 6.7 browser-hours/day.
- FACT (AWS): new Free plan = up to $200 credits ($100 on signup + up to $100 for exploring), valid up to 6 months, then the account closes unless upgraded; 30+ services always free within limits. https://aws.amazon.com/free/ (2026-10-22). Not a permanent free host. The page did not confirm a t3.micro 12-month offer; treat as gone.
- FACT (Azure): 12 months of free monthly amounts for new customers plus "65+ always-free services"; the fetched page did not state VM/Container Apps allowances. https://azure.microsoft.com/en-us/pricing/free-services . Treat as time-limited credits, not a permanent host.
- Verdict: none gives a permanent >= 4 GB free box. Useful only as a 6-12 month bridge if Oracle signup fails (AWS/Azure credits), then migrate to Hetzner.

### (d) PaaS and edge options
- Fly.io. FACT: no free tier for new orgs; trial = 2 h runtime or 7 days. shared-cpu-1x 1 GB = $6.70/month; shared-cpu-2x 2 GB = $13.39/month; volumes $0.15/GB-month. https://docs.fly.io/about/pricing (2026-10-22). A 2 GB browser box ~ $13-14/month: dearer than Hetzner.
- Railway. FACT: Free plan = $1/month credit; Hobby = $5/month with $5 usage included; RAM $10/GB-month, vCPU $20/vCPU-month. https://docs.railway.com/reference/pricing/plans . ESTIMATE: a 2 GB + 1 vCPU always-on service ~ $40/month. Too expensive for 24/7 browsers; fine for tiny services only.
- Render. The pricing page fetch returned no figures. ESTIMATE: free web services sleep when idle and free Postgres expires, so unsuitable for a 24/7 worker. Not verified; not recommended.
- Koyeb. FACT: the pricing page lists a free tier only for Postgres ("Free 5h" database), no free compute; Pro plan $29/month incl. $10 compute; no small CPU-only instance listed. https://www.koyeb.com/pricing . Not suitable.
- Cloudflare Browser Rendering. FACT: Free = **10 browser minutes/day**, 3 concurrent; Paid = 10 browser-hours/month included, then $0.09/hour, 10 concurrent. https://developers.cloudflare.com/browser-rendering/platform/pricing/ . Paid plan ($5/month, Workers Paid; ESTIMATE from Cloudflare containers page below) gives only 10 h/month included; 100 apps/day needs ~200 h/month = ~$17 extra + $5. It is also a Cloudflare-managed browser (limited control for uploads, long form flows). Possible but not cheapest.
- Cloudflare Containers. FACT: requires Workers Paid ($5/month); included 25 GiB-hours memory, 375 vCPU-minutes, 200 GB-hours disk per month; overage $0.0000025/GiB-s memory, $0.00002/vCPU-s. https://developers.cloudflare.com/containers/pricing/ . ESTIMATE: 2 GiB x 6.7 h/day x 30 = 402 GiB-h; overage ~377 GiB-h x 3600 x $0.0000025 = ~$3.4, plus CPU overage (assume 25% active: 50 vCPU-h = 3,000 min; minus 375; ~2,600 min x 60 x $0.00002 = ~$3.2) so roughly **$11-13/month total** at 100 apps/day, less at 30/day (~$7-8). A credible managed fallback but more moving parts (Workers + Durable Objects) than a VPS.
- Hetzner Cloud. FACT (partial): Cost-Optimized plans start at EUR 5.99/month and Regular Performance EUR 6.49/month on the current hetzner.com/cloud page (these may be list prices for different tiers). https://www.hetzner.com/cloud/ (2026-10-22). Third-party reports (ESTIMATE, unverified): prices rose April 1 and again around June 2026; CX23 (x86, 2 vCPU, 4 GB) about EUR 3.99-4.49 and CAX11 (ARM, 2 vCPU, 4 GB) about EUR 4.49-4.99 before the June increase; CX22 was retired. Budget **EUR 5-6.5/month incl. IPv4** and confirm in the console.
- Other "free" 2026 options: none identified that give 24/7 >= 4 GB. Home hardware (Raspberry Pi) is "without the laptop" but depends on home power/internet; not researched.

### (e) Database
- SQLite on the VM: $0, zero latency, trivial backup (`sqlite3 .backup` or Litestream to object storage). Single-writer is fine for one user. Recommended.
- Neon. FACT: Free is permanent, no card; 1 GB/project (20 GB total), 100 CU-hours/project, compute suspends after 5 min idle (cold starts), up to 100 projects. https://neon.com/pricing . Good only if compute is serverless/ephemeral (GitHub Actions or Workers).
- Supabase. FACT: Free = 500 MB DB, 2 active projects, **pauses after one week of inactivity**, 5 GB egress; Pro $25/month. https://supabase.com/pricing . A pipeline that touches the DB constantly will not pause, but the pause rule is a risk if the worker dies; not needed.
- Turso. FACT: Free = 100 databases, 5 GB, 500M rows read/month, 10M rows written/month. https://turso.tech/pricing . Excellent fallback if you must run compute on GitHub Actions/Workers (libSQL over HTTP).
- Cloudflare D1: not fetched; ESTIMATE it has a free tier and fits a Workers architecture only. Not needed.
- Pick: SQLite on the VM; Turso if compute ever becomes ephemeral.

### (f) Dashboard
- Same VM + Cloudflare Tunnel (free) + Cloudflare Access (ESTIMATE: free for small teams; verify) gives a private HTTPS URL with owner-only login and no open ports. $0, no data leaves the box.
- Vercel Hobby. FACT: Hobby is restricted to **non-commercial personal use**; includes 1M function invocations, 100 GB transfer, 4 h Active CPU, 360 GB-hrs memory per month. https://vercel.com/docs/limits/fair-use-guidelines (updated 2026-09-14). A personal job-search tool is personal use, so it is allowed. But the dashboard would need to reach the DB (Turso/Neon) or the VM API; extra complexity for no gain unless the VM goes down and you want a status page.
- Cloudflare Pages: ESTIMATE free for static assets; only useful if the dashboard is a static SPA calling the VM API.
- Pick: serve from the VM behind Tunnel + Access. Add a static "status" page on Cloudflare Pages only if wanted.

### (g) Notifications
- Telegram Bot API: ESTIMATE free, no hard cost, supports inline buttons (Approve / Open assisted link) and works well on a phone. Primary.
- ntfy. FACT: the public ntfy.sh allows bursts of 60 requests then 1 per 10 s per IP, and without ACLs "the topic name is your password"; paid plans or self-hosting give higher limits. https://docs.ntfy.sh/faq/ . Fine for a handful of pushes/day with a long random topic; or self-host ntfy on the VM ($0).
- Email: ESTIMATE any free SMTP/Resend/Gmail app password for the daily digest.
- Pick: Telegram for actions and alerts, email for the daily digest.

## 4. Architecture (primary)

```
Oracle A1 VM (Ubuntu arm64, 2 OCPU / 12 GB), Docker Compose
  scheduler  (node-cron / systemd timers): discovery every 3-4 h, apply window
  api+ui     (dashboard, behind cloudflared tunnel + Access)
  llm        (Anthropic client with spend-cap guard, section 7)
  worker     (Playwright + Chromium, concurrency 1-2, per-run timeout, kill switch)
  sqlite     (WAL) + /config (profile, master resume, answers bank)
  backup     nightly: sqlite .backup -> age-encrypted -> Cloudflare R2 free tier (ESTIMATE 10 GB) or private GitHub repo
  notify     Telegram bot, email digest
Secrets: .env on the VM (chmod 600) or Docker secrets; ANTHROPIC key with a workspace spend limit as a second cap.
```

Design rules that reduce failure risk:
- Everything idempotent and resumable from SQLite state, so a VM rebuild is just restore + `docker compose up`.
- A "heartbeat": worker pings an external free monitor (Healthchecks.io free tier, ESTIMATE) every 15 min; missing ping sends a Telegram/email alert.
- Dry-run default, per-ATS enablement, kill switch file/flag, per-site rate limits (from the brief).

## 5. Monthly fixed cost

| Item | Primary | Fallback (Hetzner) |
|---|---|---|
| Compute | $0 | ~EUR 5-6.5 (ESTIMATE) |
| DB | $0 (SQLite) | $0 |
| Dashboard/tunnel/Access | $0 | $0 |
| Notifications | $0 | $0 |
| Backup storage | $0 (R2/GitHub, ESTIMATE) | $0 (or Hetzner backups +20%, ~EUR 1) |
| Domain (optional, for tunnel hostname) | ~$10-12/year (ESTIMATE) | same |
| **Total fixed** | **$0/month (~$1 with domain)** | **~EUR 5-7.5/month** |
| Anthropic API | variable, section 7 | same |

## 6. Failure modes and mitigations

| Failure | Likelihood | Mitigation |
|---|---|---|
| Oracle signup rejected / no A1 capacity | Medium (ESTIMATE) | Retry other ADs/regions at signup; if still blocked, go straight to Hetzner fallback (do not burn days on retry scripts) |
| Idle reclaim of the A1 VM | Medium | PAYG upgrade with $1 budget alert; keep memory/CPU use real; nightly off-box backup; alert if heartbeat stops |
| Account termination / policy change | Low-medium | Same Compose file runs on Hetzner; keep the restore runbook current |
| Datacenter IP blocked by an ATS | Medium | Route to assisted queue; never solve CAPTCHAs (brief); optional low-volume residential proxy only if the owner decides later |
| Chromium crash / OOM | Medium | Per-job timeout, container memory limit, restart policy, max 2 browsers, swap file 4 GB |
| Cron drift (VM down) | Low | systemd `Persistent=true` timers catch up; dedup guarantees no double-apply |
| Tunnel/Access outage | Low | SSH over Tailscale (free personal tier, ESTIMATE) as backdoor; Telegram still works |
| Anthropic runaway spend | Low with code caps | Section 7 caps + Anthropic workspace limit |
| Secrets exposure | Low | No ATS passwords stored (brief); `.env` 600; Cloudflare Access in front; no public ports |

## 7. Anthropic API cost model

### Current prices
FACT (https://claude.com/pricing, fetched 2026-10-22; the summarizer reported per-model rates, and batch rates were derived as 50% by the page note, so confirm on the console before committing). USD per million tokens (MTok):

| Model | Input | Output | Cache write (5 min) | Cache read | Batch in / out |
|---|---|---|---|---|---|
| Haiku 5.5 (<= 100K prompt) | $0.10 | $0.50 | $0.125 | $0.01 | $0.05 / $0.25 |
| Sonnet 5.5 | $2.00 | $10.00 | $2.50 | $0.10 | $1.00 / $5.00 |
| Opus 5.5 | $4.00 | $20.00 | $5.00 | $0.20 | $2.00 / $10.00 |

Discount rules used: cache read = 0.1x input; cache write (5 min) = 1.25x input; Batch = 50% off input and output. Whether cache and Batch discounts stack is not stated on the page; the model below assumes caching only in real-time calls and Batch (no cache) for overnight tailoring, which is conservative.

### Token assumptions (ESTIMATE)
- Triage (Haiku): job description ~2,500 tokens (uncached) + cached prefix (profile, rules, filters) ~3,000 tokens; output ~150 tokens (score + reason + route). Cost: 2,500 x 0.10 + 3,000 x 0.01 + 150 x 0.50 per MTok = $0.00025 + $0.00003 + $0.000075 = **~$0.00036 per triage**.
- Funnel: ~6 jobs triaged per job that is applied/queued (so ~$0.0022 per application).
- Tailored resume + cover note (Sonnet): JD 2,500 tokens + master resume and instructions ~4,000 tokens (cacheable) in; ~2,200 tokens out (JSON resume 1,800 + note 400). Real-time with cache hit: 2,500 x 2 + 4,000 x 0.10 + 2,200 x 10 per MTok = $0.005 + $0.0004 + $0.022 = **~$0.0274**; cache miss (write): ~$0.037. Add 20% for regeneration after entity-diff failure: **~$0.033-0.044**, call it $0.035. Batch (50%): **~$0.0175**.
- Form-question mapping (Haiku): ~2,000 in + 500 out = **~$0.00045**.
- Per application: real-time **~$0.038**; with Sonnet tailoring in Batch **~$0.020**.

### Monthly cost (30 days, every application tailored; includes assisted-queue items)

| Apps/day | Apps/month | Real-time | Tailoring in Batch |
|---|---|---|---|
| 20 | 600 | ~$23 | ~$12 |
| 50 | 1,500 | ~$57 | ~$30 |
| 100 | 3,000 | ~$114 | ~$61 |

Sensitivity (ESTIMATE): output length dominates; cutting the resume output from 1,800 to 1,000 tokens (edit-list/diff output instead of a full rewrite) saves ~$0.008 per app (~20%). Using Haiku for tailoring would be ~20x cheaper but is a quality decision for the owner; keep Sonnet for resumes, Haiku for everything else. Re-pricing risk: re-verify the table before building the cost UI; make prices a config file, not constants.

### Spend-cap design (enforced in code)
1. **Single gateway**: every model call goes through `llm.call({purpose, model, ...})`; no direct SDK use elsewhere (lint rule).
2. **Ledger table** `llm_spend(id, ts, purpose, model, in_tok, out_tok, cache_read_tok, cache_write_tok, batch, cost_usd, job_id)`; cost computed from the response `usage` object and a `prices.json`.
3. **Pre-flight reservation**: before a call, compute worst-case cost (input tokens counted + max_tokens x output price) and check `spent_today + reserved + worst_case <= DAILY_CAP` and same for `MONTHLY_CAP`; if not, refuse (throws `BudgetExceeded`), mark the job `deferred_budget`, notify once via Telegram.
4. **Caps** (suggested defaults, owner-editable): daily = 1.5x expected daily spend (e.g. $3 at 50 apps/day), monthly = $60; soft alert at 80% (notify), hard stop at 100% (no new LLM calls; discovery and already-prepared submissions continue).
5. **Priority under pressure**: reserve the last 20% of the daily budget for jobs with the highest fit score; below that threshold only triage with Haiku.
6. **Batch accounting**: reserve at submission time at Batch rates; reconcile on completion; unreconciled batches older than 24 h raise an alert.
7. **Per-call guardrails**: `max_tokens` set per purpose; 60 s timeout (salvaged design); max 2 retries; circuit breaker pauses the pipeline after 5 consecutive API errors.
8. **Second line of defence**: a monthly spend limit on the Anthropic console workspace for this key (set slightly above the in-code monthly cap) in case the ledger is bypassed or corrupted.
9. **Dashboard**: spend today / month / projected, cost per application, cache hit rate.

## 8. Migration path

1. Day 0: build and test the Compose stack locally (linux/arm64 and amd64 images via `docker buildx`).
2. Deploy to Oracle A1 (primary). If signup/capacity fails after a short attempt, deploy the same stack to Hetzner and skip Oracle.
3. Keep restore tested: nightly encrypted backup, monthly restore drill on a scratch box.
4. Oracle to Hetzner: provision VM, install Docker, copy `.env`, restore latest backup, switch the Cloudflare Tunnel to the new host (tunnel token swap), stop the old stack. Downtime ~15-30 min; dedup table prevents double applications.
5. If compute must become ephemeral later (GitHub Actions or Cloudflare Containers), move SQLite to Turso (libSQL is SQLite-compatible) so the schema and queries carry over.
6. Emergency zero-cost mode (ESTIMATE): public GitHub repo + scheduled Actions for discovery and notifications only, state in Turso, with the 60-day inactivity auto-disable handled by a monthly keepalive commit; no auto-apply in this mode, everything goes to the assisted queue.

## 9. Open items for the owner
- Choose the Oracle home region carefully (permanent). Decide whether to upgrade to PAYG to reduce reclaim risk.
- Confirm Hetzner current price in the console before committing to the fallback.
- Confirm Anthropic prices and Batch/cache stacking in the console; the summarizer output above is the only source read.
- Decide Telegram vs ntfy for the primary channel (Telegram recommended for buttons).
