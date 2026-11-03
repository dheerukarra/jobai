"""Source registry. WP1b adds a module here and one entry in SOURCES; nothing else changes."""

from collections.abc import Callable
from dataclasses import dataclass

from jobai.discovery.http import PoliteClient
from jobai.discovery.models import Aggregator, Source
from jobai.discovery.sources import adzuna, jobspy_source
from jobai.discovery.sources.adzuna import AdzunaSource
from jobai.discovery.sources.arbeitnow import ArbeitnowSource
from jobai.discovery.sources.ashby import AshbySource
from jobai.discovery.sources.freehire import FreehireSource
from jobai.discovery.sources.greenhouse import GreenhouseSource
from jobai.discovery.sources.hn_hiring import HnHiringSource
from jobai.discovery.sources.jobspy_source import JobSpySource
from jobai.discovery.sources.lever import LeverSource
from jobai.discovery.sources.remoteok import RemoteOkSource
from jobai.discovery.sources.remotive import RemotiveSource
from jobai.discovery.sources.themuse import MuseSource

SOURCES: dict[str, Callable[[PoliteClient], Source]] = {
    "greenhouse": GreenhouseSource,
    "lever": LeverSource,
    "ashby": AshbySource,
}


@dataclass(frozen=True)
class AggSpec:
    """A feed-style source. in_all=False means it only runs when named explicitly."""

    factory: Callable[[PoliteClient], Aggregator]
    in_all: bool = True
    check: Callable[[], tuple[bool, str]] | None = None
    ok_note: str = "keyless public API"


def _jobspy_check() -> tuple[bool, str]:
    if jobspy_source.installed():
        return True, "installed; runs only with --source jobspy (ToS-forbidden scraping)"
    return False, "optional extra not installed (uv sync --extra jobspy); off by default"


AGGREGATORS: dict[str, AggSpec] = {
    "remotive": AggSpec(RemotiveSource, ok_note="keyless; link back, <=4 fetches/day, cached 6h"),
    "remoteok": AggSpec(RemoteOkSource, ok_note="keyless; must credit/link Remote OK"),
    "arbeitnow": AggSpec(ArbeitnowSource),
    "themuse": AggSpec(MuseSource),
    "hn_hiring": AggSpec(HnHiringSource, ok_note="HN Algolia API, latest Who-is-hiring thread"),
    "freehire": AggSpec(FreehireSource, ok_note="keyless, personal use, 120 req/min per address"),
    "adzuna": AggSpec(AdzunaSource, in_all=False, check=adzuna.availability),
    "jobspy": AggSpec(JobSpySource, in_all=False, check=_jobspy_check),
}
NOT_IMPLEMENTED = {
    "usajobs": "needs a free API key + registered email (USAJOBS_API_KEY); not implemented yet",
}


def agg_status(name: str) -> tuple[bool, str]:
    spec = AGGREGATORS[name]
    return spec.check() if spec.check else (True, spec.ok_note)
