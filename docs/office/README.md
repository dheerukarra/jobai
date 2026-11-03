# ApplyForge Office

File-based software office. Everything a real team would keep in Linear/Slack/Notion lives here so humans and agents share one source of truth. Specialists are stateless agents: they cannot message each other, so **all communication goes through these files and the lead (PM) reads and routes it.**

## Layout
| Path | Purpose |
|---|---|
| `board.md` | Kanban index of all tickets. Maintained by the lead only. |
| `team.md` | Roster, roles, ownership areas. |
| `tickets/AF-NNN.md` | One file per ticket. Owner edits only their own ticket. |
| `standups/YYYY-MM-DD-<role>.md` | Daily update, one file per person (no write conflicts). |
| `meetings/YYYY-MM-DD-<name>.md` | Minutes written by the lead: decisions, action items. |
| `inbox/<role>.md` | Messages from the lead to a role (answers, decisions, re-prioritisation). Read it first. |
| `reviews/` | Review reports (design, security, QA). |

## Ticket lifecycle
`TODO -> IN_PROGRESS -> IN_REVIEW -> DONE` (or `BLOCKED`). The owner updates the `status:` line in the ticket front matter and appends to its Activity Log. Only the lead moves tickets to DONE after verifying (build/tests/diff).

## Rules for specialists
1. Read `inbox/<your-role>.md` (if present), your ticket, and the docs it links before starting.
2. Touch ONLY the files listed under "Files owned" in your ticket. If you need a change elsewhere, write it under **Requests** in your standup; do not edit it.
3. Do not run `git commit`, `git push` or `git add -A`. The lead commits. (AF-001 may `git init`.)
4. Keep files under 500 lines, TypeScript strict, Zod at boundaries, no secrets, no invented statistics.
5. Verify before reporting: run the relevant checks (`npx tsc --noEmit`, `npx next lint`, `npx vitest run`) and paste the result summary into your ticket Activity Log.
6. Finish by writing `standups/<date>-<role>.md` using the template below.
7. If blocked, set `status: BLOCKED`, say why under **Blockers**, and stop; do not guess across ownership boundaries.
8. Policy of record (ADR-010): $10 evaluation fee never refunded; all refunds need admin approval, capped at prorated remaining unused days.
9. If a pre-write hook asks for facts, state callers, whether the file exists, data schema, and quote the ticket goal, then retry.

## Standup template
```
# Standup <date> — <role> (<ticket ids>)
Done: ...
Doing next: ...
Blockers: ...
Requests (changes needed outside my files): ...
Risks / decisions needed: ...
Verification: <commands and results>
```

## Rituals (run by the lead)
- **Kickoff** at sprint start (scope, owners, risks).
- **Standup** after each wave: lead reads all standups, writes minutes, updates board, writes inbox messages.
- **Review/Retro** at sprint end: demo what runs, what to change.
