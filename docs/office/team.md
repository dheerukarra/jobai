# Team Roster

| Role | Charter | Model tier | Active in |
|---|---|---|---|
| Owner | Final say; supplies OpenAI key, resume, answers bank, targets; enables live submit per ATS | — | always |
| Chief of Staff | Runs rounds, usage gate, ledger, git commits, graphify upkeep | main session | always |
| CEO | Phase go/no-go, goals | Haiku pass | sprint end |
| CPO | Guardrails and scope; owns the no-fabrication and answers-bank rules | Haiku pass | sprint end |
| CTO | Architecture, standards, reuse decisions | Haiku pass | sprint end |
| COO | Hosting, cost caps, kill switch, runbooks | Haiku pass | before WP6 |
| Platform EM | Reviews WP0/1/2/6 | Haiku pass | after each WP |
| Applier EM | Reviews WP3/4 | Haiku pass | after each WP |
| Experience EM | Reviews WP5 | Haiku pass | after WP5 |
| QA and Security Lead | WP7, gate reviews, security pass | Haiku/Sonnet | WP7 |
| Backend IC | Python services: config, db, LLM gateway, discovery, scoring, tailoring | Sonnet (gateway, tailoring), Haiku (rest) | WP0-3 |
| Automation IC | Playwright submit scripts, wall detection, question mapping | Sonnet | WP4 |
| Web IC | FastAPI + HTMX dashboard, queue, ntfy | Haiku | WP5 |
| DevOps IC | Docker, VM runbook, backups | Haiku | WP6 |
| QA IC | Fixtures, e2e, failure injection | Haiku | WP7 |

Tooling: Python 3.13, uv 0.12 (venv kept OUTSIDE OneDrive via `UV_PROJECT_ENVIRONMENT`), graphify 0.9.101 (project-scoped, hooks in `.claude/settings.json`), git with its data dir at `C:\Users\dheer\.gitdirs\jobai` (outside OneDrive).
