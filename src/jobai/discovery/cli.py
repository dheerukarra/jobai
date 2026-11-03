"""`jobai discover ...` subcommands (new WP1a file; wired in by jobai.cli)."""

import argparse
import functools
import sqlite3
from collections.abc import Callable
from pathlib import Path

from jobai import db
from jobai.config import get_settings
from jobai.discovery import boards as boards_mod
from jobai.discovery import runner
from jobai.discovery.http import PoliteClient
from jobai.discovery.models import Aggregator, Target
from jobai.discovery.sources import AGGREGATORS, NOT_IMPLEMENTED, SOURCES, agg_status
from jobai.discovery.sources.freehire import FreehireSource
from jobai.discovery.sources.jobspy_source import WARNING as JOBSPY_WARNING
from jobai.discovery.store import Store


def _targets(args: argparse.Namespace) -> list[Target]:
    return runner.load_targets(Path(args.companies), SOURCES)


def _open_conn() -> sqlite3.Connection:
    conn = db.connect(get_settings().database_path)
    db.migrate(conn)
    return conn


def _open_store() -> Store:
    return Store(_open_conn())


def _client() -> PoliteClient:
    return PoliteClient(cache_dir=get_settings().database_path.parent / "http_cache")


def _known(args: argparse.Namespace) -> list[tuple[str, str]]:
    try:
        return [(t.ats, t.slug) for t in _targets(args)]
    except (OSError, ValueError):
        return []


def _line(label: str, s: runner.RunSummary, requests: int) -> str:
    return (
        f"{label}: fetched={s.fetched} inserted={s.inserted} updated={s.updated} "
        f"aliases={s.aliases} boards_new={s.boards_found} errors={len(s.errors)} "
        f"(requests so far={requests})"
    )


def _cmd_run(args: argparse.Namespace) -> int:
    src: str | None = args.source
    agg_names: list[str] = []
    if src == "all":
        agg_names = [n for n, sp in AGGREGATORS.items() if sp.in_all and agg_status(n)[0]]
    elif src in AGGREGATORS:
        ok, why = agg_status(src)
        if not ok:
            print(f"skipped {src}: {why}")
            return 2
        agg_names = [src]
    conn = _open_conn()
    store, boards = Store(conn), boards_mod.BoardStore(conn)
    client = _client()
    rc = 0
    try:
        if src is None or src == "all" or src in SOURCES:
            targets = _targets(args)
            s = runner.run(
                store, client, targets, SOURCES,
                source=None if src in (None, "all") else src,
                max_companies=args.max_companies, boards=boards,
            )
            print(
                f"companies={s.companies} fetched={s.fetched} inserted={s.inserted} "
                f"updated={s.updated} aliases={s.aliases} boards_new={s.boards_found} "
                f"errors={len(s.errors)} requests={client.request_count}"
            )
            for e in s.errors:
                print(f"  error: {e}")
            rc = 1 if s.errors and not s.fetched else 0

        def make(name: str) -> Aggregator:
            if name == "freehire" and args.query:
                return FreehireSource(client, args.query)
            return AGGREGATORS[name].factory(client)

        if agg_names:
            if "jobspy" in agg_names:
                print(f"WARNING: {JOBSPY_WARNING}")
            factories: dict[str, Callable[[], Aggregator]] = {
                n: functools.partial(make, n) for n in agg_names
            }
            res = runner.run_aggregators(
                store, agg_names, factories, limit=args.limit, boards=boards
            )
            for name, s in res.items():
                print(_line(name, s, client.request_count))
                for e in s.errors:
                    print(f"  error: {e}")
                attr = getattr(make(name), "attribution", "")
                if s.fetched and attr:
                    print(f"  attribution: {attr}")
            if all(r.errors and not r.fetched for r in res.values()):
                rc = 1
    finally:
        client.close()
    return rc


def _cmd_sources(args: argparse.Namespace) -> int:
    for n in sorted(SOURCES):
        print(f"{n:<10} ATS board   enabled   needs companies in {args.companies}")
    for n, sp in AGGREGATORS.items():
        ok, why = agg_status(n)
        print(f"{n:<10} aggregator {'enabled ' if ok else 'DISABLED'}  {why}"
              f"{'' if sp.in_all else '  [not in --source all]'}")
    for n, why in NOT_IMPLEMENTED.items():
        print(f"{n:<10} aggregator DISABLED  {why}")
    return 0


def _cmd_harvest(args: argparse.Namespace) -> int:
    bs = boards_mod.BoardStore(_open_conn())
    cands = bs.candidates(_known(args))
    print(f"{len(cands)} harvested boards not in {args.companies}")
    for c in cands:
        print(f"  {c.status:<5} {c.ats:<10} {c.slug:<30} via {c.source}")
    return 0


def _cmd_verify_harvested(args: argparse.Namespace) -> int:
    bs = boards_mod.BoardStore(_open_conn())
    client = _client()
    try:
        done = bs.verify(client, SOURCES, _known(args), max_checks=args.max)
    finally:
        client.close()
    for c in done:
        print(f"{c.status.upper():<5} {c.ats:<10} {c.slug:<30} {c.detail or ''}")
    alive = boards_mod.yaml_snippet(done)
    print(f"checked={len(done)} requests={client.request_count}")
    if alive:
        print("# ready to paste under 'companies:' in config/companies.yaml (not edited for you)")
        print(alive)
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    targets = [t for t in _targets(args) if not args.name or args.name.lower() in t.name.lower()]
    client = PoliteClient()
    try:
        results = runner.verify(client, targets, SOURCES)
    finally:
        client.close()
    for r in results:
        print(f"{'OK  ' if r.ok else 'DEAD'} {r.target.ats:<10} {r.target.slug:<20} "
              f"jobs={r.jobs:<5} {r.detail}")
    dead = [r for r in results if not r.ok]
    print(f"checked={len(results)} ok={len(results) - len(dead)} dead={len(dead)} "
          f"requests={client.request_count}")
    return 1 if dead else 0


def _cmd_stats(_: argparse.Namespace) -> int:
    for label, counts in _open_store().stats().items():
        body = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "(none)"
        print(f"{label}: {body}")
    return 0


def _cmd_stale(args: argparse.Namespace) -> int:
    print(f"closed {_open_store().mark_stale(args.days)} stale jobs (not seen for {args.days}d)")
    return 0


def add_discover_parser(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    d = sub.add_parser("discover", help="job discovery from public ATS boards")
    ds = d.add_subparsers(dest="discover_cmd", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--companies", default=str(runner.DEFAULT_COMPANIES))

    r = ds.add_parser("run")
    common(r)
    r.add_argument("--source", choices=[*sorted(SOURCES), *AGGREGATORS, "all"])
    r.add_argument("--max-companies", type=int)
    r.add_argument("--limit", type=int, default=50, help="max postings per aggregator")
    r.add_argument("--query", help="search text (freehire only)")
    r.set_defaults(fn=_cmd_run)
    v = ds.add_parser("verify")
    common(v)
    v.add_argument("--name", help="only companies whose name contains this text")
    v.set_defaults(fn=_cmd_verify)
    so = ds.add_parser("sources")
    common(so)
    so.set_defaults(fn=_cmd_sources)
    h = ds.add_parser("harvest")
    common(h)
    h.set_defaults(fn=_cmd_harvest)
    vh = ds.add_parser("verify-harvested")
    common(vh)
    vh.add_argument("--max", type=int, default=10, help="max boards to check this run")
    vh.set_defaults(fn=_cmd_verify_harvested)
    ds.add_parser("stats").set_defaults(fn=_cmd_stats)
    m = ds.add_parser("mark-stale")
    m.add_argument("--days", type=int, required=True)
    m.set_defaults(fn=_cmd_stale)
