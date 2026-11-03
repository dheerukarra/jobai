"""Company list loading plus the run/verify loops (new WP1a file; callers: discovery.cli)."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from jobai.discovery.boards import BoardStore
from jobai.discovery.http import PoliteClient
from jobai.discovery.models import Aggregator, FetchError, JobPosting, Source, Target
from jobai.discovery.store import Store

DEFAULT_COMPANIES = Path("config/companies.yaml")
SourceFactory = Callable[[PoliteClient], Source]


def load_targets(path: Path, known_ats: Mapping[str, object]) -> list[Target]:
    data: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = data.get("companies") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a top-level 'companies:' list")
    out: list[Target] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{path}: bad entry {row!r}")
        t = Target(name=str(row["name"]), ats=str(row["ats"]).lower(), slug=str(row["slug"]))
        if t.ats not in known_ats:
            raise ValueError(f"{path}: unknown ats {t.ats!r} for {t.name}")
        if (t.ats, t.slug) in seen:
            continue
        seen.add((t.ats, t.slug))
        out.append(t)
    return out


@dataclass
class RunSummary:
    companies: int = 0
    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    aliases: int = 0
    errors: list[str] = field(default_factory=list)
    boards_found: int = 0


def _ingest(
    store: Store, summary: "RunSummary", postings: list[JobPosting], boards: BoardStore | None
) -> None:
    for p in postings:
        summary.fetched += 1
        outcome = store.upsert(p)
        if boards is not None:
            summary.boards_found += boards.record(p.source, p.url, p.apply_url, p.description_text)
        if outcome == "inserted":
            summary.inserted += 1
        elif outcome == "alias":
            summary.aliases += 1
        else:
            summary.updated += 1


def run(
    store: Store,
    client: PoliteClient,
    targets: list[Target],
    sources: Mapping[str, SourceFactory],
    *,
    source: str | None = None,
    max_companies: int | None = None,
    boards: BoardStore | None = None,
) -> RunSummary:
    chosen = [t for t in targets if source is None or t.ats == source]
    if max_companies is not None:
        chosen = chosen[: max(max_companies, 0)]
    summary = RunSummary()
    for t in chosen:
        summary.companies += 1
        try:
            postings = list(sources[t.ats](client).fetch(t))
        except FetchError as e:
            summary.errors.append(f"{t.ats}/{t.slug}: {e}")
            continue
        _ingest(store, summary, postings, boards)
    return summary


def run_aggregators(
    store: Store,
    names: list[str],
    factories: Mapping[str, Callable[[], Aggregator]],
    *,
    limit: int,
    boards: BoardStore | None = None,
) -> dict[str, RunSummary]:
    """Run feed-style sources one after another (one host at a time). Errors are per-source."""
    out: dict[str, RunSummary] = {}
    for name in names:
        summary = out[name] = RunSummary()
        try:
            postings = list(factories[name]().fetch_all(limit))
        except FetchError as e:
            summary.errors.append(f"{name}: {e}")
            continue
        _ingest(store, summary, postings, boards)
    return out


@dataclass
class VerifyResult:
    target: Target
    ok: bool
    jobs: int
    detail: str


def verify(
    client: PoliteClient,
    targets: list[Target],
    sources: Mapping[str, SourceFactory],
) -> list[VerifyResult]:
    results: list[VerifyResult] = []
    for t in targets:
        try:
            n = len(list(sources[t.ats](client).fetch(t)))
        except FetchError as e:
            results.append(VerifyResult(t, False, 0, str(e)))
            continue
        results.append(VerifyResult(t, n > 0, n, "ok" if n > 0 else "board returned 0 jobs"))
    return results
