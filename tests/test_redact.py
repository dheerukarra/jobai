from jobai.llm.redact import Redactor


def test_round_trip_profile_fields():
    r = Redactor(name="Jane Doe", email="jane@x.com", phone="555-123-4567", address="1 Main St")
    t = "Jane Doe <jane@x.com> 555-123-4567, 1 Main St. Jane Doe again"
    red = r.redact(t)
    assert "Jane" not in red and "@" not in red and "555" not in red and "Main" not in red
    assert r.restore(red) == t


def test_round_trip_unknown_email_and_phone():
    r = Redactor()
    t = "contact bob@corp.io or +44 20 7946 0958 now"
    red = r.redact(t)
    assert "bob@corp.io" not in red and "7946" not in red
    assert r.restore(red) == t


def test_same_value_same_placeholder():
    r = Redactor()
    red = r.redact("a@b.co then a@b.co")
    assert red.count("[[EMAIL_1]]") == 2


def test_repr_and_str_do_not_expose_pii():
    r = Redactor(name="Jane Doe", email="jane@x.com", phone="+1 555 123 4567", address="1 Main St")
    r.redact("Jane Doe jane@x.com")
    for out in (repr(r), str(r)):
        for pii in ("Jane", "jane@x.com", "555", "Main St"):
            assert pii not in out
