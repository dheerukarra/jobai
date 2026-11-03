"""Parser/render tests for jobai.office using fixtures only (no live docs)."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from jobai.office.cli import main
from jobai.office.parser import normalize_status, parse_office
from jobai.office.render import build, render_html

FIX = Path(__file__).parent / "fixtures"


def cards() -> dict[str, dict]:
    return {c["id"]: c for c in parse_office(FIX)["cards"]}


def test_normalize_status() -> None:
    assert normalize_status("DONE (44 tests)") == "DONE"
    assert normalize_status("in_review") == "IN_REVIEW"
    assert normalize_status("garbage") == "TODO"


def test_board_and_ticket_merge() -> None:
    c = cards()
    assert c["WP0"]["status"] == "DONE"  # board wins over ticket's IN_REVIEW
    assert c["WP0"]["status_note"] == "44 tests green"
    assert c["WP0"]["estimate"] == 3.0 and c["WP0"]["actual"] == 1.0
    assert c["WP1"]["status"] == "TODO" and not c["WP1"]["has_ticket"]
    assert c["X-2"]["status"] == "IN_PROGRESS"  # ticket not on board is still a card
    assert c["X-2"]["estimate"] == 1.5 and c["X-2"]["depends_on"] == ["WP0", "WP1"]


def test_tasks_activity_and_links() -> None:
    c = cards()
    assert [t["done"] for t in c["X-2"]["tasks"]] == [True, False]
    assert [t["done"] for t in c["WP0"]["tasks"]] == [None, None]
    assert len(c["WP0"]["activity"]) == 2 and "Verification" in c["WP0"]["activity"][0]
    assert [x["kind"] for x in c["X-2"]["linked"]] == ["standup"]
    assert [x["kind"] for x in c["WP0"]["linked"]] == ["review"]  # WP01/X-22 do not match


def test_feed_ledger_org_team() -> None:
    d = parse_office(FIX)
    review = next(f for f in d["feed"] if f["kind"] == "review")
    assert review["verdict"] == "APPROVE-WITH-FIXES" and review["date"] == "2026-11-03"
    assert d["feed"][0]["date"] == "2026-11-04"
    assert [r["wp_id"] for r in d["ledger"]] == ["", "WP0"]
    assert d["blocked_text"].startswith("Key")
    depths = [(n["name"], n["depth"]) for n in d["org"]]
    assert depths[0] == ("Owner (you)", 0) and ("Chief of Staff (main)", 1) in depths
    assert ("Backend IC (Python)", 4) in depths and ("COO", 2) in depths
    assert d["team"][1]["role"] == "Web IC"


def test_live_status_is_sanitised() -> None:
    d = parse_office(FIX)
    assert d["live"]["usage"]["weekly_pct"] == 4
    assert len(d["live"]["agents"]) == 1  # the junk string entry was dropped
    assert not d["warnings"]


def test_timeline_marks_post_mvp() -> None:
    tl = {t["id"]: t for t in parse_office(FIX)["timeline"]}
    assert tl["WP0"]["start"] == 0 and tl["WP1"]["end"] == 5.0
    assert tl["WP8"]["basis"] == "post-MVP"


def test_missing_everything_degrades(tmp_path: Path) -> None:
    d = parse_office(tmp_path)
    assert d["cards"] == [] and d["live"] is None and d["warnings"]
    assert "<script" in render_html(d)


def test_malformed_status_json(tmp_path: Path) -> None:
    shutil.copytree(FIX / "docs", tmp_path / "docs")
    (tmp_path / "docs/office/status.json").write_text("{not json", encoding="utf-8")
    d = parse_office(tmp_path)
    assert d["live"] is None and any("status.json" in w for w in d["warnings"])


def test_build_embeds_valid_json_and_is_offline(tmp_path: Path) -> None:
    shutil.copytree(FIX / "docs", tmp_path / "docs")
    nasty = tmp_path / "docs/office/standups/2026-11-05-x.md"
    nasty.write_text("# </script><b>x</b>\n__DATA__ /*__JS__*/", encoding="utf-8")
    out = build(tmp_path)
    html = out.read_text(encoding="utf-8")
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    assert m is not None
    data = json.loads(m.group(1))
    assert any(f["title"] == "</script><b>x</b>" for f in data["feed"])
    assert not re.search(r"https?://", html.replace("http://www.w3.org/2000/svg", ""))
    assert "/*__CSS__*/" not in html and "/*__JS__*/" not in html.split('id="data"')[0]


def test_cli_build(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    shutil.copytree(FIX / "docs", tmp_path / "docs")
    assert main(["build", "--root", str(tmp_path)]) == 0
    assert (tmp_path / "dashboard" / "index.html").is_file()
    assert "wrote" in capsys.readouterr().out
