"""Tests de seguridad: sanitización de nombres, path traversal, job_id."""

from backend.app.job_store import JOB_ID_RE, new_job_id, sanitize_name


def test_sanitize_removes_traversal():
    # Path traversal: sólo conserva el basename seguros
    assert sanitize_name("../../etc/passwd") == "passwd"
    s = sanitize_name("..\\..\\windows\\system32")
    assert "\\" not in s and "/" not in s


def test_sanitize_strips_to_basename():
    assert sanitize_name("/tmp/secret/x.jpg") == "x.jpg"


def test_sanitize_limits_length():
    long = "a" * 500 + ".jpg"
    s = sanitize_name(long)
    assert len(s) <= 120 and s.endswith(".jpg")


def test_job_id_format():
    jid = new_job_id()
    assert JOB_ID_RE.match(jid)


def test_job_id_rejects_traversal():
    assert not JOB_ID_RE.match("../../bad")
    assert not JOB_ID_RE.match("..%2f..%2f")
