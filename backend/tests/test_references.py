from datetime import timedelta

import pytest
from conftest import client

from app.db import get_engine
from app.demo import USERS, seed
from app.demo_fixtures import CANONICAL, fixture
from app.pdf_files import path_for
from app.reference_worker import process_one
from app.store import one, rows


@pytest.fixture
def dataset(pilot, monkeypatch, tmp_path):
    password, clock = pilot
    monkeypatch.setenv("OPENBOOK_PDF_DIR", str(tmp_path))
    return seed(lambda: password), password, clock


def login(name, password):
    session = client()
    assert session.post(
        "/api/login", json=dict(username=name, password=password)
    ).is_success
    return session


def test_access_and_search(dataset):
    marker, password, clock = dataset
    a, b = [f"/api/student/exams/{eid}" for eid in marker["exams"]]
    versions = marker["versions"]
    for index, denied, vid in [
        (1, b, versions[2]),
        (3, a, versions[0]),
        (6, a, versions[0]),
        (6, b, versions[2]),
    ]:
        session = login(USERS[index], password)
        for suffix in ["", "/search?q=deadlock", f"/{vid}/file"]:
            url = denied + "/references" + suffix
            for headers in [{}, {"Range": "bytes=0-9"}]:
                assert session.get(url, headers=headers).status_code == 404

    session = login(USERS[5], password)

    def docs(path):
        return session.get(path + "/references")

    assert docs(a).status_code == 403
    assert [v["id"] for v in docs(b).json()] == list(reversed(versions[2:4]))
    attempt = session.post(a + "/start").json()
    assert sorted(v["id"] for v in docs(a).json()) == versions[:2]
    for term, (name, pages) in CANONICAL.items():
        path = a if name in {"indexing-guide", "transactions-guide"} else b
        hits = session.get(path + "/references/search", params={"q": term}).json()
        assert sorted(h["page"] for h in hits) == pages
        assert all(
            h["title"] == name.replace("-", " ").title() and h["snippet"] for h in hits
        )
        other = b if path == a else a
        assert (
            session.get(other + "/references/search", params={"q": term}).json() == []
        )
    for base, vid in [(a, versions[2]), (b, versions[0])]:
        assert (
            session.get(
                f"{base}/references/{vid}/file", headers={"Range": "bytes=-8"}
            ).status_code
            == 404
        )
    url = f"{a}/references/{versions[0]}/file"
    content = session.get(url).content
    partial = session.get(url, headers={"Range": "bytes=0-7"})
    assert partial.status_code == 206 and partial.content == content[:8]
    assert partial.headers["content-range"] == f"bytes 0-7/{len(content)}"
    assert session.get(url, headers={"Range": "bytes=99999999-"}).status_code == 416
    assert session.get(a + "/references/search?q=").json() == []
    assert (
        session.get(a + "/references/search", params={"q": "x" * 161}).status_code
        == 422
    )
    assert seed(lambda: pytest.fail("Existing passwords must survive")) == marker
    assert session.post(a + "/start").json()["id"] == attempt["id"]
    clock[0] += timedelta(hours=3)
    assert docs(a).status_code == 403
    assert session.get(url, headers={"Range": "bytes=-4"}).status_code == 403
    clock[0] += timedelta(hours=21)
    assert docs(b).status_code == 403
    assert session.post(b + "/start").is_success and docs(b).is_success


def test_upload_retry_and_freeze(dataset, monkeypatch, tmp_path):
    marker, password, _ = dataset
    cid = marker["course_id"]
    base = f"/api/lecturer/courses/{cid}/references"
    teacher = login(USERS[0], password)
    other = login("other", password)
    params = {"title": "Edition two", "filename": "../../outside.pdf"}
    notes = fixture("transactions-guide")
    assert other.post(base, params=params, content=notes).status_code == 404
    assert (
        login(USERS[1], password).post(base, params=params, content=notes).status_code
        == 403
    )
    assert (
        teacher.post(base, params=params, content=fixture("malformed")).status_code
        == 422
    )
    with monkeypatch.context() as m:
        m.setenv("OPENBOOK_PDF_MAX_BYTES", "10")
        assert teacher.post(base, params=params, content=notes).status_code == 413
    with monkeypatch.context() as m:
        m.setenv("OPENBOOK_PDF_MAX_PAGES", "1")
        assert teacher.post(base, params=params, content=notes).status_code == 422
    library = teacher.get(base).json()
    first = library[0]
    scan = library[-1]
    assert scan["status"] == "view-only"
    assert teacher.get(f"{base}/{scan['id']}/file").content == fixture("scan")
    assert len(list(tmp_path.iterdir())) == 5
    added = teacher.post(
        base, params=params | {"document_id": first["document_id"]}, content=notes
    )
    assert added.is_success, added.text
    vid = added.json()["id"]
    assert added.json()["number"] == 2
    with get_engine().begin() as db:
        record = one(db, "SELECT storage_key FROM reference_version WHERE id=:v", v=vid)
        path = path_for(record["storage_key"])
        assert path.parent == tmp_path and path.name != "outside.pdf"
        rows(
            db,
            "UPDATE reference_job SET lease_until=now()-interval '1 second' "
            "WHERE version_id=:v",
            v=vid,
        )
    path.write_bytes(fixture("malformed"))
    assert process_one(vid)
    assert other.post(f"{base}/{vid}/retry").status_code == 404
    assert (
        next(v for v in teacher.get(base).json() if v["id"] == vid)["status"]
        == "failed"
    )
    path.write_bytes(notes)
    assert teacher.post(f"{base}/{vid}/retry").is_success and process_one(vid)
    assert not process_one(vid)
    a, b = marker["exams"]
    exam = f"/api/lecturer/exams/{a}"
    current = teacher.get(exam).json()
    draft = current["draft"] | {"reference_versions": [vid]}
    assert (
        teacher.put(
            exam, json={"edit_number": current["edit_number"], "draft": draft}
        ).status_code
        == 409
    )
    student = login(USERS[1], password)
    assert student.post(f"/api/student/exams/{a}/start").is_success
    prefix = f"/api/student/exams/{a}/references"
    assert student.get(f"{prefix}/{first['id']}/file").content == fixture(
        "indexing-guide"
    )
    assert student.get(f"{prefix}/{vid}/file").status_code == 404
    # Explicitly release the image-only fixture in a new upcoming revision.
    exam = f"/api/lecturer/exams/{b}"
    current = teacher.get(exam).json()
    restricted = teacher.put(
        exam,
        json={
            "edit_number": current["edit_number"],
            "draft": current["draft"] | {"pre_release": False},
        },
    ).json()
    assert teacher.post(
        exam + "/publish", json={"edit_number": restricted["edit_number"]}
    ).is_success
    assigned_student = login(USERS[3], password)
    assert assigned_student.get(f"/api/student/exams/{b}/references").status_code == 403
    current = teacher.get(exam).json()
    other_course = other.post("/api/courses", json={"name": "Other course"}).json()[
        "id"
    ]
    alien = other.post(
        f"/api/lecturer/courses/{other_course}/references", params=params, content=notes
    ).json()["id"]
    assert (
        teacher.put(
            exam,
            json={
                "edit_number": current["edit_number"],
                "draft": current["draft"] | {"reference_versions": [alien]},
            },
        ).status_code
        == 422
    )
    updated = teacher.put(
        exam,
        json={
            "edit_number": current["edit_number"],
            "draft": current["draft"]
            | {
                "pre_release": True,
                "reference_versions": [scan["id"], vid, first["id"]],
            },
        },
    ).json()
    assert teacher.post(
        exam + "/publish", json={"edit_number": updated["edit_number"]}
    ).is_success
    student = login(USERS[3], password)
    prefix = f"/api/student/exams/{b}/references"
    assert student.get(f"{prefix}/{scan['id']}/file").content == fixture("scan")
    hits = student.get(prefix + "/search?q=the").json()
    assert {h["id"] for h in hits} == {vid, first["id"]}
