"""JobSpy wrapper: OPTIONAL and OFF by default. New WP1b file; caller: sources registry.

WARNING: LinkedIn, Indeed, Glassdoor and ZipRecruiter terms of service forbid scraping. This
wrapper is for personal discovery only (never an apply target), logged-out only (no accounts,
no cookies), with a hard cap of a handful of results. It runs only when you pass
`--source jobspy` explicitly and the optional extra is installed: `uv sync --extra jobspy`.
"""

from collections.abc import Callable, Iterable
from typing import Any

from jobai.discovery.models import FetchError, JobPosting
from jobai.discovery.sources.util import parse_dt, slugify

WARNING = (
    "JobSpy scrapes job boards whose terms of service forbid scraping (LinkedIn, Indeed, "
    "Glassdoor, ZipRecruiter). Discovery only, logged-out, tiny result counts. Your risk."
)
MAX_RESULTS = 10
DEFAULT_SITES = ("indeed",)
Scraper = Callable[[str, int], list[dict[str, Any]]]


def installed() -> bool:
    try:
        import jobspy  # noqa: F401
    except ImportError:
        return False
    return True


def _default_scraper(term: str, n: int) -> list[dict[str, Any]]:
    try:
        from jobspy import scrape_jobs
    except ImportError as e:
        raise FetchError("python-jobspy not installed: uv sync --extra jobspy") from e
    try:
        df = scrape_jobs(
            site_name=list(DEFAULT_SITES), search_term=term, results_wanted=n,
            hours_old=72, country_indeed="USA", verbose=0,
        )
    except Exception as e:  # third-party scraper: any failure is just "this source failed"
        raise FetchError(f"jobspy failed: {type(e).__name__}: {e}"[:300]) from e
    return [dict(r) for r in df.to_dict("records")]


def _clean(v: Any) -> Any:
    """pandas NaN/NaT/None -> None."""
    return None if v is None or (isinstance(v, float) and v != v) or str(v) == "NaT" else v


def parse(rows: list[dict[str, Any]]) -> list[JobPosting]:
    out: list[JobPosting] = []
    for r in rows:
        r = {k: _clean(v) for k, v in r.items()}
        url, title = r.get("job_url"), r.get("title")
        if not url or not title:
            continue
        company = str(r.get("company") or "Unknown")
        site = str(r.get("site") or "jobspy")
        remote = r.get("is_remote")
        out.append(
            JobPosting(
                source="jobspy",
                external_id=str(r.get("id") or url),
                url=str(url),
                apply_url=None,  # discovery only: never an apply target
                title=str(title),
                company_name=company,
                company_slug=slugify(company),
                location=r.get("location") or None,
                remote=bool(remote) if remote is not None else None,
                posted_at=parse_dt(str(r["date_posted"])) if r.get("date_posted") else None,
                description_text=str(r.get("description") or "")[:20_000],
                ats="jobspy",
                raw_json={"site": site, "discovery_only": True},
            )
        )
    return out


class JobSpySource:
    name = "jobspy"
    attribution = WARNING

    def __init__(self, client: object = None, scraper: Scraper | None = None) -> None:
        self._scraper = scraper or _default_scraper

    def fetch_all(self, limit: int) -> Iterable[JobPosting]:
        n = min(max(limit, 1), MAX_RESULTS)
        return parse(self._scraper("software engineer", n))[:n]
