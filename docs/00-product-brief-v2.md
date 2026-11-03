# ApplyForge Personal — Product Brief v2 (supersedes the SaaS docs)

**Decision (2026-10-22, owner):** this is a tool for one user (the owner), not a product to sell. No customers, no pricing, no Stripe, no refunds, no specialists, no public marketing site, no legal exposure from selling. The only running cost is AI/API usage, paid by the owner. The SaaS docs 00–05 and the office tickets for billing/refunds/marketing are archived under `docs/archive-saas/`.

## Goal
Apply to as many **relevant, qualified** jobs as possible, every day, with a tailored resume per job, running 24/7 without the owner's laptop, at near-zero fixed cost.

## Requirements (from the owner)
1. **Hybrid apply:** if the application can be submitted automatically (simple ATS form, no CAPTCHA/login wall, all questions answerable from the answers bank), submit it. Otherwise queue it as **assisted apply**: pre-tailored resume + prefilled answers + one-tap link, owner finishes it (phone friendly) and gets a notification.
2. **Sources:** as many as possible. Job boards, **company career pages** (ATS public boards: Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee, Workday where feasible), aggregator APIs, and existing scraping tools/libraries for LinkedIn/Indeed-type sites used **logged out** (no account of the owner is ever used for scraping, so there is no account to ban; worst case is an IP block, mitigated with low rate, caching and rotating fallback).
3. **24/7 and cheap or free:** no always-on laptop. Prefer free tiers; the final choice comes from the hosting research.
4. **AI cost only:** tailoring/triage via the Anthropic API (Haiku for triage and form-question mapping, Sonnet for resume tailoring, prompt caching of the master resume, Batch for overnight work). A daily and monthly spend cap is a hard feature.

## Non-negotiable guardrails (they protect the owner's job search)
- **No fabrication.** Tailoring may reorder, emphasise and rephrase real experience only. An entity diff (employers, titles, dates, degrees, certifications, skills claimed) against the master resume blocks submission if anything new appears.
- **Answers bank.** Work authorization, sponsorship, salary, EEO/demographics, relocation, notice period etc. come only from a file the owner writes. Unknown or ambiguous question = do not guess, send to assisted queue.
- **No CAPTCHA bypass, no solving services.** CAPTCHA/bot wall = assisted queue.
- **Dedup and caps.** Never apply twice to the same job/company role; per-company, per-day and global daily caps; polite rate limits per site; respect robots/ToS where practical and document where not.
- **Secrets** only in the host secret store; no ATS passwords in the database. Sites that require an account go to the assisted queue.
- **Kill switch** and dry-run mode (default on) until the owner enables live submit per ATS.

## Scope of the system
Pipeline: `discover -> normalize/dedupe -> filter/score (profile fit, visa/location rules) -> tailor resume + cover note -> decide route (auto | assisted | skip) -> submit or queue -> track outcomes (email/status) -> report`.
Surfaces: a small private dashboard (queue, tracker, spend, settings) and push notifications (Telegram or ntfy). Config in files (profile, master resume, answers bank, target companies, filters).

## Out of scope
Payments, multi-user, auth beyond a single-owner secret, marketing pages, recruiter portal, public insights, DSR flows, specialist console.

## Salvage from the earlier build
Next.js scaffold (dashboard), Zod env pattern, tailoring pipeline design (entity diff, 60 s timeout, JSON-schema output), the cost model's AI figures. Drop: Prisma/Postgres multi-tenant schema (replace with a small schema), Stripe, marketing components, policy/refund code.
