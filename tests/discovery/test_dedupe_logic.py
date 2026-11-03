from jobai.discovery.dedupe import canonical_key, canonical_url, fingerprint


def test_canonical_url_strips_tracking_fragment_slash_and_lowercases_host():
    u = "HTTPS://Boards.Greenhouse.IO/acme/jobs/123/?utm_source=x&gh_src=abc&keep=1#apply"
    assert canonical_url(u) == "https://boards.greenhouse.io/acme/jobs/123?keep=1"


def test_canonical_url_idempotent_and_ref_dropped():
    u = "https://jobs.lever.co/acme/1?ref=twitter&lever-source=li"
    assert canonical_url(u) == "https://jobs.lever.co/acme/1"
    assert canonical_url(canonical_url(u)) == canonical_url(u)


def test_canonical_key_format():
    assert canonical_key("Greenhouse", "Acme", "99") == "greenhouse:acme:99"


def test_fingerprint_ignores_case_punctuation_company_suffix():
    a = fingerprint("Acme, Inc.", "Senior Engineer (Backend)", "New York, NY", False)
    b = fingerprint("ACME", "senior engineer backend", "new york ny", False)
    assert a == b


def test_fingerprint_differs_on_location_remote_title():
    base = fingerprint("Acme", "Engineer", "Berlin", False)
    assert base != fingerprint("Acme", "Engineer", "Paris", False)
    assert base != fingerprint("Acme", "Engineer", "Berlin", True)
    assert base != fingerprint("Acme", "Engineer II", "Berlin", False)
    assert fingerprint("Acme", "E", None, None) != fingerprint("Acme", "E", None, False)
