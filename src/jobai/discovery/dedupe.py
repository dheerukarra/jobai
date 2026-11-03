"""Canonical URL, canonical key and fingerprint (new WP1a file; callers: store)."""

import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_DROP_PARAMS = {
    "gh_src", "ref", "refid", "source", "lever-source", "lever-origin", "fbclid", "gclid",
}
_SUFFIX = re.compile(r"\b(inc|llc|ltd|corp|corporation|co|gmbh|plc|limited)\b\.?")


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if parts.port and parts.port not in (80, 443):
        host = f"{host}:{parts.port}"
    kept = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _DROP_PARAMS
    ]
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), host, path, urlencode(kept), ""))


def canonical_key(ats: str, company_slug: str, external_id: str) -> str:
    return f"{ats.lower()}:{company_slug.lower()}:{external_id}"


def _norm(text: str | None) -> str:
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-z0-9]+", " ", t.lower())
    return t.strip()


def normalise_company(name: str) -> str:
    return _norm(_SUFFIX.sub(" ", name.lower()))


def fingerprint(company: str, title: str, location: str | None, remote: bool | None) -> str:
    basis = "|".join(
        [
            normalise_company(company),
            _norm(title),
            _norm(location),
            "r" if remote else ("o" if remote is False else "?"),
        ]
    )
    return hashlib.sha256(basis.encode()).hexdigest()[:32]
