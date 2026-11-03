"""Parse docs/office files into one JSON-serialisable dict for the dashboard.

New project file (ticket OFF-1; owner request: "i need a web dashboard for tracking the
status of the project ... like jira"). Callers: jobai.office.render.build and the tests in
tests/office. Reads (never writes) board.md, status.json, tickets/*.md, standups/*.md,
reviews/*.md, budget-ledger.md, org-chart.md, team.md under <root>/docs/office. Every
section degrades to an empty value plus an entry in data["warnings"]; nothing raises on
missing or malformed input.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

STATUSES = ["TODO", "IN_PROGRESS", "IN_REVIEW", "DONE", "BLOCKED"]
_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _num(text: str) -> float | None:
    m = _NUM_RE.search(text or "")
    return float(m.group(0)) if m else None


def normalize_status(raw: str) -> str:
    """'DONE (44 tests ...)' -> 'DONE'; unknown -> 'TODO'."""
    token = re.sub(r"[^A-Za-z_ ]", " ", raw or "").strip().upper().replace(" ", "_")
    for s in STATUSES:
        if token == s or token.startswith(s + "_"):
            return s
    return "TODO"


def split_table_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def parse_table(text: str) -> list[dict[str, str]]:
    """First markdown table in text -> list of {header: cell} dicts."""
    rows: list[dict[str, str]] = []
    headers: list[str] | None = None
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            if headers is not None and rows:
                break
            continue
        cells = split_table_row(line)
        if headers is None:
            headers = [c.lower() for c in cells]
        elif all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        else:
            rows.append({h: (cells[i] if i < len(cells) else "") for i, h in enumerate(headers)})
    return rows


def split_sections(body: str) -> dict[str, str]:
    """Split on '## Heading' lines; keys are lower-cased headings."""
    out: dict[str, list[str]] = {}
    current = "_intro"
    out[current] = []
    for line in body.splitlines():
        m = re.match(r"^##\s+(.*?)\s*$", line)
        if m:
            current = m.group(1).lower()
            out.setdefault(current, [])
        else:
            out[current].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta: dict[str, str] = {}
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return meta, "\n".join(lines[i + 1 :])
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", lines[i])
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()
    return {}, text


def parse_list(raw: str) -> list[str]:
    s = (raw or "").strip().strip("[]")
    return [p.strip().strip("'\"") for p in s.split(",") if p.strip().strip("'\"")]


def parse_tasks(text: str) -> list[dict[str, Any]]:
    """Checklist items ('- [x] ...') carry done=True/False; numbered items done=None."""
    tasks: list[dict[str, Any]] = []
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]\s*\[([ xX])\]\s*(.*)$", line)
        if m:
            tasks.append({"text": m.group(2).strip(), "done": m.group(1).lower() == "x"})
            continue
        m = re.match(r"^\s*(?:\d+[.)]|[-*])\s+(.*)$", line)
        if m and not line.startswith("   "):
            tasks.append({"text": m.group(1).strip(), "done": None})
    return tasks


def parse_activity(text: str) -> list[str]:
    entries: list[str] = []
    for line in text.splitlines():
        if line.startswith("- "):
            entries.append(line[2:])
        elif entries and line.strip():
            entries[-1] += "\n" + line.strip()
    return entries


def parse_ticket(path: Path) -> dict[str, Any] | None:
    text = _read(path)
    if text is None:
        return None
    meta, body = parse_front_matter(text)
    sec = split_sections(body)
    tid = meta.get("id") or path.stem
    return {
        "id": tid,
        "title": meta.get("title", tid),
        "owner": meta.get("owner", ""),
        "status": normalize_status(meta.get("status", "TODO")),
        "model": meta.get("model", ""),
        "estimate": _num(meta.get("estimate", "")),
        "depends_on": parse_list(meta.get("depends_on", "")),
        "goal": sec.get("goal", ""),
        "tasks": parse_tasks(sec.get("tasks", "")),
        "acceptance": sec.get("acceptance", "") or next(
            (v for k, v in sec.items() if k.startswith("acceptance")), ""
        ),
        "activity": parse_activity(sec.get("activity log", "")),
        "source": f"tickets/{path.name}",
    }


def parse_board(text: str) -> tuple[list[dict[str, Any]], str]:
    rows = []
    for r in parse_table(text):
        wid = r.get("wp", "").strip()
        if not wid:
            continue
        status_raw = r.get("status", "")
        note = re.sub(r"^[A-Z_]+\s*", "", status_raw).strip(" ()")
        link = r.get("ticket", "")
        links = [x.strip() for x in link.split(",") if x.strip() and x.strip() != "—"]
        rows.append(
            {
                "id": wid,
                "scope": r.get("scope", ""),
                "owner": r.get("owner role", ""),
                "estimate": _num(r.get("est", "")),
                "status": normalize_status(status_raw),
                "status_note": note,
                "links": links,
            }
        )
    m = re.search(r"^Blocked on owner:\s*(.*)$", text, re.M)
    return rows, (m.group(1).strip() if m else "")


def parse_ledger(text: str) -> list[dict[str, Any]]:
    out = []
    for r in parse_table(text):
        wp = r.get("wp", "")
        m = re.match(r"(WP\d+|[A-Z]{2,5}-\d+)\b", wp)
        out.append(
            {
                "date": r.get("date (utc)", ""),
                "wp": wp,
                "wp_id": m.group(1) if m else "",
                "estimate": _num(r.get("estimate (pts)", "")),
                "weekly_before": r.get("weekly % before", ""),
                "weekly_after": r.get("weekly % after", ""),
                "actual": _num(r.get("actual (pts)", "")),
                "five_hour_after": r.get("5-hour % after", ""),
                "agents": r.get("agents / model", ""),
                "notes": r.get("notes", ""),
            }
        )
    return out


def parse_org(text: str) -> list[dict[str, Any]]:
    """Parse the box-drawing tree in the first fenced block into [{name, desc, depth}]."""
    m = re.search(r"```[^\n]*\n(.*?)```", text, re.S)
    if not m:
        return []
    nodes: list[dict[str, Any]] = []
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        cm = re.search(r"[├└]── ", line)
        if cm:
            depth = cm.start() // 4 + 1
            label = line[cm.end() :]
        else:
            depth, label = 0, line.strip()
        parts = re.split(r"\s\.{2,}\s*", label, maxsplit=1)
        if len(parts) == 2:
            name, desc = parts
        else:
            name, _, desc = label.partition(": ")
        nodes.append({"name": name.strip(), "desc": desc.strip(), "depth": depth})
    return nodes


def parse_status_json(text: str | None, warnings: list[str]) -> dict[str, Any] | None:
    if text is None:
        warnings.append("status.json is missing: live usage and agent data are unavailable.")
        return None
    try:
        data = json.loads(text)
    except ValueError:
        warnings.append("status.json is not valid JSON: live usage and agent data are unavailable.")
        return None
    if not isinstance(data, dict):
        warnings.append("status.json has an unexpected shape: live data unavailable.")
        return None
    for key in ("usage", "sprint"):
        if not isinstance(data.get(key), dict):
            warnings.append(f"status.json has no '{key}' section.")
            data[key] = {}
    for key in ("agents", "owner_blockers"):
        if not isinstance(data.get(key), list):
            warnings.append(f"status.json has no '{key}' list.")
            data[key] = []
    data["agents"] = [a for a in data["agents"] if isinstance(a, dict)]
    data["owner_blockers"] = [b for b in data["owner_blockers"] if isinstance(b, dict)]
    return data


def _feed_item(path: Path, kind: str) -> dict[str, Any] | None:
    text = _read(path)
    if text is None:
        return None
    lines = [ln for ln in text.splitlines()]
    title = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("#")), path.stem)
    dm = _DATE_RE.match(path.name)
    date = dm.group(1) if dm else ""
    if not date:
        m = re.search(r"^Date:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
        date = m.group(1) if m else ""
    vm = re.search(r"^#*\s*Verdict:\s*(.+)$", text, re.M | re.I)
    body = [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    return {
        "kind": kind,
        "title": title,
        "date": date,
        "file": f"{kind}s/{path.name}",
        "verdict": vm.group(1).strip() if vm else "",
        "excerpt": "\n".join(body[:4])[:900],
        "text": text,
    }


def _link_docs(tickets: list[dict[str, Any]], feed: list[dict[str, Any]]) -> None:
    for t in tickets:
        pat = re.compile(rf"(?<![\w-]){re.escape(t['id'])}(?![\w-])")
        t["linked"] = [
            {"kind": f["kind"], "title": f["title"], "file": f["file"], "date": f["date"]}
            for f in feed
            if pat.search(f["file"]) or pat.search(f["text"])
        ]


def _merge_cards(
    board: list[dict[str, Any]], tickets: list[dict[str, Any]], ledger: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_id = {t["id"]: t for t in tickets}
    actual: dict[str, float] = {}
    for r in ledger:
        if r["wp_id"] and r["actual"] is not None:
            actual[r["wp_id"]] = actual.get(r["wp_id"], 0.0) + r["actual"]
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    for b in board:
        t = by_id.get(b["id"], {})
        cards.append(
            {
                "id": b["id"],
                "title": t.get("title") or b["scope"],
                "scope": b["scope"],
                "owner": b["owner"] or t.get("owner", ""),
                "status": b["status"],
                "status_note": b["status_note"],
                "model": t.get("model", ""),
                "estimate": b["estimate"] if b["estimate"] is not None else t.get("estimate"),
                "actual": actual.get(b["id"]),
                "depends_on": t.get("depends_on", []),
                "goal": t.get("goal", ""),
                "tasks": t.get("tasks", []),
                "acceptance": t.get("acceptance", ""),
                "activity": t.get("activity", []),
                "linked": t.get("linked", []),
                "has_ticket": bool(t),
            }
        )
        seen.add(b["id"])
    for t in tickets:
        if t["id"] in seen:
            continue
        cards.append(
            {
                **{k: t[k] for k in ("id", "title", "owner", "status", "model", "estimate")},
                "scope": t["title"],
                "status_note": "",
                "actual": actual.get(t["id"]),
                "depends_on": t["depends_on"],
                "goal": t["goal"],
                "tasks": t["tasks"],
                "acceptance": t["acceptance"],
                "activity": t["activity"],
                "linked": t.get("linked", []),
                "has_ticket": True,
            }
        )
    return cards


def _timeline(cards: list[dict[str, Any]], live: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Planned bars. Uses status.json 'timeline' [{id, week_start, week_end}] when present;
    otherwise spreads WP cards over W0..W4 in order by cumulative estimate points."""
    wps = [c for c in cards if re.fullmatch(r"WP\d+", c["id"])]
    explicit = {}
    if live and isinstance(live.get("timeline"), list):
        explicit = {e.get("id"): e for e in live["timeline"] if isinstance(e, dict)}
    mvp = [c for c in wps if c["id"] != "WP8"]
    total = sum(c["estimate"] or 0 for c in mvp) or 1.0
    out, acc = [], 0.0
    for c in wps:
        e = explicit.get(c["id"])
        if e:
            ws, we, basis = float(e.get("week_start", 0)), float(e.get("week_end", 0)) + 1, "plan"
        elif c["id"] == "WP8":
            ws, we, basis = 5.0, 6.0, "post-MVP"
        else:
            ws = acc / total * 5
            acc += c["estimate"] or 0
            we = acc / total * 5
            basis = "spread by estimate"
        out.append(
            {"id": c["id"], "label": c["scope"].split(":")[0], "status": c["status"],
             "start": round(ws, 2), "end": round(we, 2), "basis": basis}
        )
    return out


def parse_office(root: Path, generated_at: str = "") -> dict[str, Any]:
    """Collect all dashboard data from <root>/docs/office."""
    office = root / "docs" / "office"
    warnings: list[str] = []
    if not office.is_dir():
        warnings.append(f"Folder not found: {office}. Nothing to show.")

    board_text = _read(office / "board.md")
    board: list[dict[str, Any]] = []
    blocked_text = ""
    if board_text is None:
        warnings.append("board.md is missing: no work packages to show.")
    else:
        board, blocked_text = parse_board(board_text)
        if not board:
            warnings.append("board.md has no work-package table.")

    tickets = [
        t for p in sorted((office / "tickets").glob("*.md")) if (t := parse_ticket(p)) is not None
    ]
    feed = [
        f
        for kind, folder in (("standup", "standups"), ("review", "reviews"))
        for p in sorted((office / folder).glob("*.md"))
        if (f := _feed_item(p, kind)) is not None
    ]
    _link_docs(tickets, feed)

    ledger_text = _read(office / "budget-ledger.md")
    ledger = parse_ledger(ledger_text) if ledger_text else []
    if not ledger:
        warnings.append("budget-ledger.md is missing or has no rows.")

    org_text = _read(office / "org-chart.md")
    org = parse_org(org_text) if org_text else []
    if not org:
        warnings.append("org-chart.md is missing or has no hierarchy block.")

    team_text = _read(office / "team.md")
    team = parse_table(team_text) if team_text else []
    if not team:
        warnings.append("team.md is missing or has no roster table.")

    live = parse_status_json(_read(office / "status.json"), warnings)
    cards = _merge_cards(board, tickets, ledger)
    for f in feed:
        del f["text"]
    return {
        "project": (live or {}).get("project") or "JobAi",
        "generated_at": generated_at,
        "statuses": STATUSES,
        "live": live,
        "cards": cards,
        "blocked_text": blocked_text,
        "feed": sorted(feed, key=lambda f: f["date"], reverse=True),
        "ledger": ledger,
        "org": org,
        "team": team,
        "timeline": _timeline(cards, live),
        "warnings": warnings,
    }
