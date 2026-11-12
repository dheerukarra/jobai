# JobAi

An open-source, self-hosted tool that finds jobs across many public sources, scores them against your profile, tailors a resume per job, and applies for you. It submits automatically only when a form is simple and every answer is known, and otherwise hands the application to a review queue so you finish it. Built for a single user, to run 24/7 on a small VM at near-zero fixed cost.

> **Status: early development.** Discovery and the LLM gateway work and are tested. Scoring, tailoring, auto-apply and deployment are planned and not built yet. Nothing in this repository submits an application today.

## What works today

- **Job discovery** from public sources into SQLite, deduplicated across sources:
  company boards on Greenhouse, Lever and Ashby, plus Remotive, Remote OK, Arbeitnow, The Muse, Hacker News "Who is hiring" and the freehire API. An optional, off-by-default JobSpy wrapper exists for sites whose terms forbid scraping; read the warning below before enabling it.
- **Board harvesting:** finds new company boards from the postings it fetches and prints suggestions. It never edits your company list on its own.
- **LLM gateway** (OpenAI first, other providers pluggable): a model ladder that escalates to a stronger model only when validation fails, worst-case cost reserved before every call, hard daily and monthly spend caps, a kill switch, and redaction of personal details before text leaves your machine.
- **Polite networking:** one request at a time per host, at least a second apart, identifying User-Agent, retry only on 429/5xx, and `Retry-After` respected.
- **Project dashboard:** a Jira-style board that updates itself as work happens (`python -m jobai.office serve`, then open http://127.0.0.1:8765/).

## Design rules

- **No fabrication.** Resume tailoring may reorder and rephrase real experience only. A check against your master resume will block anything new (employers, titles, dates, degrees).
- **Unknown means stop.** Work authorization, salary, demographics and similar answers come only from a file you write. If a form asks something the file does not cover, the application goes to the review queue, not a guess.
- **No CAPTCHA bypass.** A CAPTCHA or login wall always means human review.
- **Dry run by default**, with per-site opt-in for live submission, daily caps and a kill switch.
- **Spend is capped in code**, not just in a dashboard.

## Quick start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env          # optional: add OPENAI_API_KEY (never commit it)
uv run python -m jobai migrate
uv run python -m jobai discover verify        # check the company boards in config/companies.yaml
uv run python -m jobai discover run --max-companies 3
uv run python -m jobai discover stats
uv run python -m jobai spend                  # LLM spend against the daily/monthly caps
```

Secrets can also live outside the project in `~/.jobai/secrets.env`, which the app reads after `.env`. Tests make no network calls and need no key:

```bash
uv run ruff check && uv run mypy src && uv run pytest -q
```

## Repository layout

| Path | What it holds |
|---|---|
| `src/jobai/llm/` | LLM gateway: providers, pricing, spend ledger and caps, redaction |
| `src/jobai/discovery/` | Source adapters, dedupe, polite HTTP client, store, runner, board harvesting |
| `src/jobai/office/` | Self-updating project dashboard (stdlib only) |
| `src/jobai/migrations/` | Forward-only SQLite migrations |
| `config/companies.yaml` | Company boards to crawl, verified before use |
| `docs/` | Product brief, research notes, delivery plan and the project board |
| `tests/` | Unit tests with recorded fixtures (no network) |

## Roadmap

Discovery and the gateway are done. Next: more job sources, fit scoring with explicit "do not apply" reasons, resume tailoring with the no-fabrication check, the submit engine and review queue, then 24/7 deployment. The full plan is in [`docs/04-delivery-plan-and-usage-budget.md`](docs/04-delivery-plan-and-usage-budget.md).

## Responsible use

- You are responsible for following each site's terms of service and applicable law. Scraping LinkedIn, Indeed, Glassdoor or ZipRecruiter is against their terms; the JobSpy wrapper is disabled by default for that reason and is never used to submit applications.
- Automated applications can get you flagged by employers. Review what the tool sends in its early stages, keep volume reasonable, and keep the answers file accurate.
- This is hobby software provided as is, with no guarantee of interviews or jobs.

## Contributing

Issues and pull requests are welcome. Please keep tests offline (use recorded fixtures), run `ruff`, `mypy` and `pytest` before opening a PR, and do not commit secrets or personal data.

## License

[MIT](LICENSE). Third-party references and credits are listed in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) once present.
