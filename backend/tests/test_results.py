from datetime import timedelta

from alembic import command
from alembic.config import Config
from test_references import dataset as dataset
from test_references import login

from app.attempt_expiry import expire_batch
from app.db import get_engine
from app.demo import USERS
from app.results_demo import seed_results
from app.store import one


def test_demo_security_and_analytics(dataset):
    _, password, _ = dataset
    released, pending = seed_results()
    assert seed_results() == [released, pending]
    teacher = login(USERS[0], password)
    other = login("other", password)
    student = login(USERS[1], password)
    unstarted = login(USERS[6], password)
    outsider = login("outside", password)
    root = f"/api/lecturer/exams/{pending}/results"
    path = f"/api/student/exams/{pending}/result"
    assert other.get(root).status_code == 404
    assert other.post(root + "/release").status_code == 404
    assert outsider.get(path).status_code == 404
    assert student.get(path).json() == dict(status="submitted", released=False)
    assert student.get(root).status_code == 403
    stats = teacher.get(root).json()
    assert stats["totals"] == dict(
        assigned=6,
        started=5,
        finalized=5,
        graded=5,
        submitted=4,
        expired=1,
        average=2.2,
        lowest=0,
        highest=5,
    )
    assert [x["score"] for x in stats["distribution"]] == [0, 1, 2, 3, 5]
    first = stats["questions"][0]
    assert [first[k] for k in ("correct", "incorrect", "unanswered", "total")] == [
        4,
        0,
        1,
        5,
    ]
    assert dict(name="DBMS", correct=11, total=25) in stats["topics"]
    assert sum(group["total"] for group in stats["topics"]) == 50
    publication = teacher.post(root + "/release")
    assert publication.is_success
    assert teacher.post(root + "/release").json() == publication.json()
    details = student.get(path).json()["feedback"]
    assert details["score"] == details["maximum"] == 5
    assert details["questions"][0]["explanation"]
    assert unstarted.get(path).json() == dict(status="not_started", released=True)
    assert student.get(f"/api/student/exams/{released}/result").json()["released"]


def test_finalize_backfill_and_release_gate(dataset):
    demo, password, clock = dataset
    a = demo["exams"][0]
    top = f"/api/student/exams/{a}"
    root = f"/api/lecturer/exams/{a}/results"
    teacher = login(USERS[0], password)
    student = login(USERS[1], password)
    expires = login(USERS[2], password)
    empty = teacher.get(root).json()
    assert empty["totals"]["average"] is None and empty["distribution"] == []
    assert teacher.post(root + "/release").status_code == 409
    assert student.post(top + "/start").is_success
    assert expires.post(top + "/start").is_success
    endpoint = top + "/attempt"
    assert student.put(
        endpoint + "/questions/0", json=dict(revision=0, answer=0, flagged=True)
    ).is_success
    assert student.put(
        endpoint + "/questions/1", json=dict(revision=1, answer=0, flagged=False)
    ).is_success
    final = student.post(endpoint + "/submit", json={"revision": 2}).json()
    assert student.post(endpoint + "/submit", json={"revision": 2}).is_success
    with get_engine().connect() as db:
        score = one(
            db, "SELECT * FROM attempt_grade WHERE attempt_id=:a", a=final["id"]
        )
        assert [score[k] for k in ("score", "incorrect", "unanswered")] == [1, 1, 3]
    clock[0] += timedelta(days=3)
    assert teacher.post(root + "/release").status_code == 409
    assert expire_batch() == 1
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "0004")
    command.upgrade(cfg, "0005")
    assert teacher.get(root).json()["totals"]["graded"] == 2
    assert student.get(endpoint).json()["responses"] == final["responses"]
    assert teacher.post(root + "/release").is_success
    assert expires.get(top + "/result").json()["feedback"]["unanswered"] == 5
