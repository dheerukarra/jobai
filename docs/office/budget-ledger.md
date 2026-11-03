# Claude Code Usage Ledger

Rule: weekly all-models usage stays <= 50% (hard), planned <= 40%. Protocol in `docs/personal/04-delivery-plan-and-usage-budget.md` section 2. Append one row after every work package, read from `get_usage`.

| Date (UTC) | WP | Estimate (pts) | Weekly % before | Weekly % after | Actual (pts) | 5-hour % after | Agents / model | Notes |
|---|---|---|---|---|---|---|---|---|
| 2026-10-22 | Planning + research (SaaS detour, pivot, 7 research agents) | — | — | 15 | — | 57 | ~16 agents, mixed | Baseline at plan time. Weekly meter did not move after the last 3 research agents finished, so it is coarse or lagging; calibrate with larger WPs. Includes ~5 killed/archived SaaS work packages. |
| 2026-11-04 | New week reading | — | — | 2–3 | — | 12–15 | — | Weekly window reset on Nov 1; old 15% did not carry over. |
| 2026-11-04 | Setup: freehire check, OpenAI pricing, graphify install, JobAi move | — | 3 | 3 | ~0 | 15 | main session only | Cheap: web fetches and tool installs. |
| 2026-11-04 | WP0 Foundation (Sonnet build ~121k tokens) + Platform EM review (Haiku ~126k) + fix pass (Sonnet ~122k) + my verification | 3 | 3 | 4 | ~1 (meter is whole-percent, so 0.5–1.5) | 27 | backend-ic Sonnet, platform-em Haiku | Actual is about a third of the estimate. Do NOT cut later estimates yet: the meter is coarse and WP0 was a clean spec. Recheck after WP1. 5-hour window rose 7 points, so it is the tighter limit: at most 2 WP-sized agents per window. |
| 2026-11-04 | Setup 2: OpenAI key + smoke tests, claude-mem + Bun install, config change | — | 4 | 4 | ~0 | 27 | main session | claude-mem installed but not yet capturing (needs Claude restart). Its summariser uses the Claude subscription (Haiku): measure overhead on WP1 and disable if it costs more than it saves. |
| 2026-11-04 | OFF-1 Office dashboard (1 Sonnet agent ~143k tokens, 44 tool calls) + my verification and browser check | 1.5 | 4 | 5 | ~1 | 36 | web-ic Sonnet | 5-hour window +9 points for one WP-sized agent plus verification: at most 2 such agents per window, and wait for the reset before a third. Weekly estimate-to-actual ratio now ~0.4 over two WPs; still not trusting it until WP1. |
