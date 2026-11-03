"""Live work visibility for the office dashboard: recent file changes mapped to tickets, git
state and "truth over stale data" flags. Stdlib only.

New project file for ticket OFF-2 (owner request: "i need it to be updated after every change
even when task or tickets in progress"). Callers: jobai.office.state.build_state and
jobai.office.server (iter_files for the change stamp). Reads (never writes) files under
docs/office, src, tests, config, scripts and runs read-only `git` commands.

Data schema returned by build_activity (all times are epoch seconds):
  now, window_s, active_s, files [{path, mtime, ticket}], tickets {id: {active, files}},
  git {branch, dirty, last_commit} | None,
  truth {no_agent [ids], status_stale bool, status_age_s int | None}
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .parser import normalize_status, parse_front_matter, split_sections

WINDOW_S = 15 * 60  # files changed within this window count as recent activity
ACTIVE_S = 5 * 60  # a ticket with a change this recent is "active now"
STALE_STATUS_S = 10 * 60  # status.json older than this while work is in progress is suspect
MAX_FILES = 60
SCAN_DIRS = ("docs/office", "src", "tests", "config", "scripts")
SCAN_FILES = ("pyproject.toml",)
SKIP_DIRS = frozenset(
    {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules", ".venv", ".git"}
)
SKIP_SUFFIXES = (".pyc", ".pyo")
_RANK = {"DONE": 0, "IN_PROGRESS": 2}  # tie-break when several tickets own a path
_PATH_RE = re.compile(r"(?<![\w/])(?:src|tests|scripts|config|docs)/[\w./*<>{}-]+")
_TOKEN_RE = re.compile(r"`([^`]+)`")


def iter_files(root: Path) -> Iterator[tuple[str, float, int]]:
    """Yield (posix relative path, mtime seconds, size) for every watched file, sorted."""
    stack = [root / d for d in SCAN_DIRS if (root / d).is_dir()]
    out: list[tuple[str, float, int]] = []
    for name in SCAN_FILES:
        try:
            s = (root / name).stat()
        except OSError:
            continue
        out.append((name, s.st_mtime, s.st_size))
    while stack:
        d = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        for e in entries:
            try:
                if e.is_dir(follow_symlinks=False):
                    if e.name not in SKIP_DIRS:
                        stack.append(Path(e.path))
                elif e.name.endswith(SKIP_SUFFIXES):
                    continue
                elif e.is_file(follow_symlinks=False):
                    s = e.stat()
                    rel = Path(e.path).relative_to(root).as_posix()
                    out.append((rel, s.st_mtime, s.st_size))
            except (OSError, ValueError):
                continue
    out.sort()
    yield from out


def glob_to_regex(glob: str) -> re.Pattern[str]:
    """'src/x/**' or 'a/<date>-b.md' -> compiled regex over posix relative paths."""
    g = re.sub(r"<[^>]*>", "*", glob.strip()).lstrip("./")
    if "*" not in g and "?" not in g and "." not in g.rsplit("/", 1)[-1]:
        g = g.rstrip("/") + "/**"  # a bare directory means everything under it
    out, i = "", 0
    while i < len(g):
        if g.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif g.startswith("**", i):
            out, i = out + ".*", i + 2
        elif g[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif g[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(g[i]), i + 1
    return re.compile(out + r"\Z")


def _literal_len(glob: str) -> int:
    m = re.search(r"[*?<]", glob)
    return m.start() if m else len(glob)


def owned_globs(text: str) -> list[str]:
    """Globs from a ticket's '## Files owned' section; falls back to paths named in the text."""
    _, body = parse_front_matter(text)
    section = split_sections(body).get("files owned", "")
    globs: list[str] = []
    for tok in _TOKEN_RE.findall(section):
        for part in tok.split(","):
            p = part.strip()
            if p and re.fullmatch(r"[\w./*<>{}-]+", p) and ("/" in p or "." in p):
                globs.append(p)
    if not globs:
        for m in _PATH_RE.findall(body):
            p = m.rstrip(".,;:)")
            tail = p.rsplit("/", 1)[-1]
            globs.append(p if "*" in p or "." in tail else p.rstrip("/") + "/**")
    return list(dict.fromkeys(globs))


def ticket_rules(root: Path) -> dict[str, dict[str, Any]]:
    """{ticket id: {status, rules [(regex, literal length)]}} from docs/office/tickets."""
    rules: dict[str, dict[str, Any]] = {}
    tdir = root / "docs" / "office" / "tickets"
    for p in sorted(tdir.glob("*.md")) if tdir.is_dir() else []:
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        meta, _ = parse_front_matter(text)
        tid = meta.get("id") or p.stem
        globs = [*owned_globs(text), f"docs/office/tickets/{p.name}"]
        rules[tid] = {
            "status": normalize_status(meta.get("status", "TODO")),
            "rules": [(glob_to_regex(g), _literal_len(g)) for g in globs],
        }
    return rules


def map_file(path: str, rules: dict[str, dict[str, Any]]) -> str | None:
    """Best ticket for a path: longest literal prefix; ties go to IN_PROGRESS, open, then DONE."""
    best: tuple[int, int, str] | None = None
    for tid, info in rules.items():
        for rx, lit in info["rules"]:
            if rx.match(path):
                key = (lit, _RANK.get(info["status"], 1), tid)
                if best is None or key[:2] > best[:2]:
                    best = key
    return best[2] if best else None


def git_state(root: Path) -> dict[str, Any] | None:
    """Branch, uncommitted file count and last commit subject, or None if not a git repo."""
    if not (root / ".git").exists():
        return None
    flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW

    def run(*args: str) -> str | None:
        try:
            r = subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True, text=True, timeout=5, creationflags=flags, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout.strip() if r.returncode == 0 else None

    branch = run("rev-parse", "--abbrev-ref", "HEAD")
    if branch is None:
        return None
    status = run("status", "--porcelain")
    return {
        "branch": branch,
        "dirty": len(status.splitlines()) if status else 0,
        "last_commit": run("log", "-1", "--format=%s") or None,
    }


def _parse_iso(raw: object) -> float | None:
    try:
        dt = datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).timestamp()


def compute_truth(
    cards: list[dict[str, Any]], live: dict[str, Any] | None, now: float
) -> dict[str, Any]:
    """Flags for in-progress tickets without a registered agent and a stale status.json."""
    agents = (live or {}).get("agents", [])
    running = {a.get("ticket") for a in agents if a.get("status") == "running"}
    active = [c["id"] for c in cards if c["status"] == "IN_PROGRESS"]
    updated = _parse_iso((live or {}).get("updated")) if live else None
    age = int(now - updated) if updated is not None else None
    return {
        "no_agent": [i for i in active if i not in running],
        "status_stale": bool(active) and age is not None and age > STALE_STATUS_S,
        "status_age_s": age,
    }


def build_activity(
    root: Path, cards: list[dict[str, Any]], live: dict[str, Any] | None, now: float | None = None
) -> dict[str, Any]:
    t = time.time() if now is None else now
    rules = ticket_rules(root)
    recent = [(p, m) for p, m, _ in iter_files(root) if 0 <= t - m <= WINDOW_S]
    recent.sort(key=lambda x: x[1], reverse=True)
    files: list[dict[str, Any]] = [
        {"path": p, "mtime": round(m, 3), "ticket": map_file(p, rules)} for p, m in recent
    ]
    tickets: dict[str, dict[str, Any]] = {}
    for f in files:
        if f["ticket"]:
            entry: dict[str, Any] = tickets.setdefault(f["ticket"], {"active": False, "files": []})
            entry["files"].append({"path": f["path"], "mtime": f["mtime"]})
            entry["active"] = entry["active"] or t - f["mtime"] <= ACTIVE_S
    return {
        "now": round(t, 3),
        "window_s": WINDOW_S,
        "active_s": ACTIVE_S,
        "files": files[:MAX_FILES],
        "tickets": tickets,
        "git": git_state(root),
        "truth": compute_truth(cards, live, t),
    }
