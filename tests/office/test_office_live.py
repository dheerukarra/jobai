"""Tests for OFF-2: change stamp, activity mapping, truth flags, live endpoints, poll logic.

Fixtures and tmp_path only; no live docs. Callers: pytest.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from jobai.office.activity import (
    build_activity,
    compute_truth,
    glob_to_regex,
    map_file,
    owned_globs,
    ticket_rules,
)
from jobai.office.render import JS_PARTS, TEMPLATES, render_html
from jobai.office.server import compute_stamp, make_server
from jobai.office.state import build_state

FIX = Path(__file__).parent / "fixtures"
NOW = 1_800_000_000.0

TICKET = """---
id: T-1
title: Demo
status: IN_PROGRESS
---
## Files owned
`src/jobai/demo/**`, `tests/demo/**`, `scripts/demo.ps1`, `docs/office/standups/<date>-demo.md`

## Activity log
- first
- second line
"""


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    shutil.copytree(FIX / "docs", tmp_path / "docs")
    (tmp_path / "src/jobai/demo").mkdir(parents=True)
    (tmp_path / "src/jobai/other").mkdir(parents=True)
    (tmp_path / "docs/office/tickets/T-1.md").write_text(TICKET, encoding="utf-8")
    (tmp_path / "src/jobai/demo/a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "src/jobai/other/b.py").write_text("y = 1\n", encoding="utf-8")
    return tmp_path


def touch(path: Path, age_s: float, now: float = NOW) -> None:
    os.utime(path, (now - age_s, now - age_s))


def test_stamp_changes_only_when_a_file_changes(proj: Path) -> None:
    first = compute_stamp(proj)
    assert compute_stamp(proj) == first  # nothing changed
    (proj / "src/jobai/demo/a.py").write_text("x = 22\n", encoding="utf-8")
    second = compute_stamp(proj)
    assert second != first
    new = proj / "tests/office_new.py"
    new.parent.mkdir(exist_ok=True)
    new.write_text("", encoding="utf-8")
    assert compute_stamp(proj) != second
    (proj / "dashboard").mkdir()
    before = compute_stamp(proj)
    (proj / "dashboard/index.html").write_text("rebuilt", encoding="utf-8")  # not watched
    (proj / "src/jobai/__pycache__").mkdir()
    (proj / "src/jobai/__pycache__/x.pyc").write_bytes(b"0")  # ignored
    assert compute_stamp(proj) == before


def test_stamp_is_fast(proj: Path) -> None:
    import time

    t = time.perf_counter()
    for _ in range(5):
        compute_stamp(proj)
    assert (time.perf_counter() - t) / 5 < 0.05


def test_glob_regex_and_owned_globs() -> None:
    assert glob_to_regex("src/jobai/demo/**").match("src/jobai/demo/sub/a.py")
    assert not glob_to_regex("src/jobai/demo/**").match("src/jobai/other/a.py")
    assert glob_to_regex("docs/office/standups/<date>-demo.md").match(
        "docs/office/standups/2026-11-04-demo.md"
    )
    assert glob_to_regex("src/jobai/office").match("src/jobai/office/x.py")  # bare directory
    deep = glob_to_regex("a/**/b.py")
    assert deep.match("a/b.py") and deep.match("a/x/y/b.py")
    assert owned_globs(TICKET) == [
        "src/jobai/demo/**", "tests/demo/**", "scripts/demo.ps1",
        "docs/office/standups/<date>-demo.md",
    ]


def test_owned_globs_fallback_infers_from_text() -> None:
    text = "---\nid: W\n---\n## Scope\nBuild `src/jobai/discovery/` and tests/discovery/t.py.\n"
    assert owned_globs(text) == ["src/jobai/discovery/**", "tests/discovery/t.py"]


def test_activity_maps_files_to_tickets(proj: Path) -> None:
    touch(proj / "src/jobai/demo/a.py", 60)  # active now (< 5 min)
    touch(proj / "src/jobai/other/b.py", 120)  # recent but no owner
    touch(proj / "docs/office/board.md", 700)  # recent, not active
    touch(proj / "docs/office/tickets/WP0.md", 4000)  # outside the 15 min window
    cards = build_state(proj)["cards"]
    act = build_activity(proj, cards, None, NOW)
    by_path = {f["path"]: f["ticket"] for f in act["files"]}
    assert by_path["src/jobai/demo/a.py"] == "T-1"
    assert by_path["src/jobai/other/b.py"] is None
    assert "docs/office/tickets/WP0.md" not in by_path
    assert [f["path"] for f in act["files"]][:2] == ["src/jobai/demo/a.py", "src/jobai/other/b.py"]
    assert act["tickets"]["T-1"]["active"] is True
    assert act["git"] is None  # tmp project is not a git repo


def test_ticket_with_only_older_changes_is_not_active(proj: Path) -> None:
    touch(proj / "src/jobai/demo/a.py", 400)
    act = build_activity(proj, build_state(proj)["cards"], None, NOW)
    assert act["tickets"]["T-1"]["active"] is False
    assert len(act["tickets"]["T-1"]["files"]) == 1


def test_map_prefers_longest_prefix_then_open_ticket(proj: Path) -> None:
    (proj / "docs/office/tickets/T-2.md").write_text(
        "---\nid: T-2\nstatus: DONE\n---\n## Files owned\n`src/jobai/**`, `src/jobai/demo/**`\n",
        encoding="utf-8",
    )
    rules = ticket_rules(proj)
    assert map_file("src/jobai/demo/a.py", rules) == "T-1"  # DONE T-2 ties on prefix; open wins
    assert map_file("src/jobai/zzz.py", rules) == "T-2"  # only T-2 covers it
    assert map_file("docs/office/tickets/T-1.md", rules) == "T-1"  # ticket's own file


def test_truth_flags() -> None:
    cards = [{"id": "A", "status": "IN_PROGRESS"}, {"id": "B", "status": "IN_PROGRESS"},
             {"id": "C", "status": "DONE"}]
    live = {"updated": "2026-11-04T00:00:00Z",
            "agents": [{"ticket": "A", "status": "running"}, {"ticket": "B", "status": "done"}]}
    base = 1_793_750_400.0  # 2026-11-04T00:00:00Z
    fresh = compute_truth(cards, live, base + 60)
    assert fresh["no_agent"] == ["B"] and fresh["status_stale"] is False
    stale = compute_truth(cards, live, base + 601)
    assert stale["status_stale"] is True and stale["status_age_s"] == 601
    idle = compute_truth([{"id": "C", "status": "DONE"}], live, base + 5000)
    assert idle["status_stale"] is False and idle["no_agent"] == []
    assert compute_truth(cards, None, base)["status_age_s"] is None


@pytest.fixture
def server(proj: Path) -> Iterator[tuple[str, Path]]:
    srv = make_server(proj, 0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}", proj
    srv.shutdown()
    srv.server_close()


def get(url: str) -> tuple[int, bytes, str]:
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.status, r.read(), r.headers.get("Content-Type", "")


def test_endpoints(server: tuple[str, Path]) -> None:
    base, proj = server
    code, body, ctype = get(base + "/api/stamp")
    s1 = json.loads(body)
    assert code == 200 and ctype == "application/json" and len(s1["stamp"]) > 8 and s1["time"] > 0
    (proj / "src/jobai/demo/a.py").write_text("x = 3\n", encoding="utf-8")
    assert json.loads(get(base + "/api/stamp")[1])["stamp"] != s1["stamp"]

    state = json.loads(get(base + "/api/state")[1])
    assert {"cards", "live", "feed", "ledger", "timeline", "warnings", "activity"} <= set(state)
    act = state["activity"]
    assert {"now", "window_s", "active_s", "files", "tickets", "git", "truth"} <= set(act)
    assert any(f["path"] == "src/jobai/demo/a.py" and f["ticket"] == "T-1" for f in act["files"])
    assert set(act["truth"]) == {"no_agent", "status_stale", "status_age_s"}

    code, body, ctype = get(base + "/")
    html = body.decode("utf-8")
    assert code == 200 and ctype.startswith("text/html") and 'id="data"' in html
    assert "/*__JS__*/" not in html.split('id="data"')[0]


def test_unknown_path_and_foreign_host_rejected(server: tuple[str, Path]) -> None:
    base, _ = server
    with pytest.raises(urllib.error.HTTPError) as e404:
        get(base + "/nope")
    assert e404.value.code == 404
    req = urllib.request.Request(base + "/api/stamp", headers={"Host": "evil.example"})
    with pytest.raises(urllib.error.HTTPError) as e403:
        urllib.request.urlopen(req, timeout=5)
    assert e403.value.code == 403


def test_server_binds_localhost_only(proj: Path) -> None:
    srv = make_server(proj, 0)
    try:
        assert srv.server_address[0] == "127.0.0.1"
    finally:
        srv.server_close()


def test_render_includes_all_script_parts() -> None:
    html = render_html(build_state(FIX))
    for name in JS_PARTS:
        first_line = (TEMPLATES / name).read_text(encoding="utf-8").splitlines()[0]
        assert first_line in html
    assert html.count('"use strict";') == 1 and html.rstrip().endswith("</html>")


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_poll_logic_pure_functions(tmp_path: Path) -> None:
    src = (TEMPLATES / "live.js").read_text(encoding="utf-8")
    block = src.split("// PURE-BEGIN")[1].split("// PURE-END")[0]
    script = block + """
const eq = (a, b) => {
  if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(a + " != " + b);
};
eq(needsFetch(null, "a", 0, 1, 30000), true);          // first poll always fetches
eq(needsFetch("a", "a", 0, 1000, 30000), false);       // unchanged stamp, recent fetch
eq(needsFetch("a", "b", 0, 1000, 30000), true);        // stamp changed
eq(needsFetch("a", "a", 0, 30000, 30000), true);       // periodic refresh for time decay
const x = { cards: [1], generated_at: "t1", activity: { now: 5, files: [] } };
const y = { cards: [1], generated_at: "t2", activity: { now: 99, files: [] } };
eq(stateSig(x) === stateSig(y), true);                 // volatile fields ignored
y.cards = [2]; eq(stateSig(x) === stateSig(y), false);
eq(x.activity.now, 5);                                 // input not mutated
eq(liveText(true, 2), "Live, updated 2 s ago");
eq(liveText(false, 40), "Offline, retrying");
"""
    f = tmp_path / "pure.js"
    f.write_text(script, encoding="utf-8")
    r = subprocess.run(["node", str(f)], capture_output=True, text=True, timeout=20, check=False)
    assert r.returncode == 0, r.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_concatenated_js_is_valid_syntax(tmp_path: Path) -> None:
    js = "\n".join((TEMPLATES / n).read_text(encoding="utf-8") for n in JS_PARTS)
    f = tmp_path / "all.js"
    f.write_text(js, encoding="utf-8")
    r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr
