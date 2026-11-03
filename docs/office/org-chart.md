# JobAi Org Chart and Operating Model

Project: JobAi (personal, single-user job application automation). Plan: `docs/04-delivery-plan-and-usage-budget.md`. Brief: `docs/00-product-brief-v2.md`. Extends `README.md` (file protocol).

## Hierarchy
```
Owner (you): scope, keys, which ATS goes live, daily caps
└── Chief of Staff (the main Claude session): runs rounds, usage gate, ledger, commits, merges
    ├── CEO ........ goals, go/no-go per phase
    ├── CPO ........ product scope, guardrails (no fabrication, answers bank), backlog order
    ├── CTO ........ architecture, standards, risk, reuse decisions
    │   ├── Platform EM ........ WP0 foundation, WP1 discovery, WP2 scoring/answers bank, WP6 deploy
    │   │   ├── Backend IC (Python) ....... WP0, WP1, WP2
    │   │   └── DevOps IC ................. WP6
    │   ├── Applier EM ......... WP3 tailoring, WP4 route + submit
    │   │   ├── Backend IC (LLM/tailoring) . WP3
    │   │   └── Automation IC (Playwright) . WP4
    │   ├── Experience EM ...... WP5 assisted queue, dashboard, notifications
    │   │   └── Web IC (FastAPI/HTMX) ..... WP5
    │   └── QA and Security Lead ... WP7, gate reviews
    │       └── QA IC ..................... fixtures, e2e, failure injection
    └── COO ........ hosting, cost caps, runbooks, backups, kill switch
```
Execs and managers are real roles with charters but run as **short review passes per sprint** (one cheap agent pass each), not as always-on agents. ICs do the work. This keeps Claude usage under the 50% weekly rule.

## Rules (from the delivery plan)
1. Gate before every WP: `get_usage`; start only if weekly% + estimate <= 40. Hard stop at 45%/48% weekly. The 5-hour window has no cap (owner decision 2026-11-04); it is informational.
2. Up to 3 agents at once when file ownership is disjoint. Default model Haiku; Sonnet only for submit scripts, tailoring prompts, entity diff, route decision, the LLM gateway.
3. Brief each agent in <= 1.5k tokens and name <= 3 files to read.
4. **Graphify rule goes in every code-exploring agent prompt:** when `graphify-out/graph.json` exists, run `graphify query "<question>"` before the first grep or source read; after changing code run `graphify update .`. The `graphify` binary is `C:\Users\dheer\.local\bin\graphify.exe`.
5. Agents do not commit. The Chief of Staff commits after verification.
6. Log actual usage per WP in `budget-ledger.md`.

## Communication (files only)
`tickets/` (work), `standups/<date>-<role>.md` (up), `inbox/<role>.md` (down), `decisions/DR-NNN-*.md` (exec decisions), `reviews/` (manager/lead reviews), `meetings/` (minutes). Escalation: IC -> EM -> CTO/CPO/COO -> CEO -> Owner.

## Rituals
Sprint kickoff (Chief of Staff writes minutes), standup after each WP (IC file -> EM roll-up), exec review at sprint end (one Haiku pass producing `reviews/exec-<date>.md` and any DRs), retro.
